"""Detección determinista del stack de un repositorio (solo análisis estático; nunca se ejecuta código).

Reconoce lenguajes (por extensión y líneas), frameworks, bases de datos e infraestructura a partir de
manifiestos de dependencias (Python, Node, Java, Go, Rust, PHP, Ruby, .NET), Dockerfile/compose,
CI e imports de Python. Cada tecnología lleva evidencia `archivo:línea`. También clasifica la arquitectura
(monolito, varias aplicaciones o microservicios) y dice en qué se basa.
"""

import json
import re
import tomllib
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from app.modernization.catalog import BY_ID, LANGUAGE_EXTENSIONS, TECHS, Tech, targets_for

IGNORED_DIRS = {
    ".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build", "target", ".next", ".bob",
    ".idea", ".gradle", "vendor", "bin", "obj", ".pytest_cache", ".mypy_cache", "site-packages",
}
MAX_FILES = 6000
MAX_TEXT_BYTES = 1_000_000
MAX_EVIDENCE = 3
MAX_PY_IMPORT_FILES = 400

MANIFESTS = {
    "requirements.txt", "pyproject.toml", "Pipfile", "package.json", "pom.xml", "build.gradle",
    "build.gradle.kts", "go.mod", "Cargo.toml", "composer.json", "Gemfile",
}


class Evidence(BaseModel):
    path: str
    line: int | None = None
    text: str = ""


class Language(BaseModel):
    id: str
    name: str
    files: int
    lines: int
    share: float  # fracción de las líneas de código medidas (0..1)


class Detected(BaseModel):
    id: str
    name: str
    kind: str
    icon: str | None
    version: str | None = None  # tal como lo declara el proyecto, sin resolver
    service: str | None = None  # carpeta del servicio/aplicación donde se detectó
    evidence: list[Evidence]


class Service(BaseModel):
    name: str
    path: str
    technologies: list[str]
    dockerfile: bool


class Architecture(BaseModel):
    kind: str  # monolith | multi-app | microservices | unknown
    basis: list[str]


class Target(BaseModel):
    id: str
    name: str
    kind: str
    language: str | None
    icon: str | None


class StackReport(BaseModel):
    languages: list[Language]
    technologies: list[Detected]
    services: list[Service]
    architecture: Architecture
    targets: dict[str, list[Target]]  # id detectado -> destinos posibles
    totals: dict[str, int]


@dataclass
class _Acc:
    """Acumula detecciones por (tecnología, servicio) con su evidencia."""

    found: dict[tuple[str, str], Detected] = field(default_factory=dict)

    def add(self, tech: Tech, service: str, path: str, line: int | None, text: str, version: str | None = None) -> None:
        key = (tech.id, service)
        detected = self.found.get(key)
        if detected is None:
            detected = Detected(id=tech.id, name=tech.name, kind=tech.kind, icon=tech.icon, version=version,
                                service=service, evidence=[])
            self.found[key] = detected
        if version and not detected.version:
            detected.version = version
        if len(detected.evidence) < MAX_EVIDENCE and not any(e.path == path and e.line == line for e in detected.evidence):
            detected.evidence.append(Evidence(path=path, line=line, text=text.strip()[:160]))


# ---------------------------------------------------------------- recorrido

def _walk(root: Path) -> list[Path]:
    files: list[Path] = []
    stack = [root]
    while stack and len(files) < MAX_FILES:
        directory = stack.pop()
        try:
            entries = sorted(directory.iterdir())
        except OSError:
            continue
        for entry in entries:
            if entry.is_symlink():
                continue
            if entry.is_dir():
                if entry.name not in IGNORED_DIRS:
                    stack.append(entry)
            elif entry.is_file():
                files.append(entry)
    return files


def _read(path: Path) -> str | None:
    try:
        if path.stat().st_size > MAX_TEXT_BYTES:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _line_of(lines: list[str], needle: str) -> int | None:
    lowered = needle.lower()
    for number, text in enumerate(lines, 1):
        if lowered in text.lower():
            return number
    return None


def _norm_pip(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name.strip().lower())


# ---------------------------------------------------------------- manifiestos
# Cada lector devuelve (ecosistema, paquete, versión declarada | None, línea | None).

Dep = tuple[str, str, str | None, int | None]
_REQ = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?\s*((?:==|>=|<=|~=|!=|>|<)[^;#\s]+)?")


def _requirements(text: str) -> list[Dep]:
    deps: list[Dep] = []
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#")[0].strip()
        if not line or line.startswith("-"):
            continue
        match = _REQ.match(line)
        if match:
            deps.append(("pip", _norm_pip(match.group(1)), match.group(2), number))
    return deps


def _pep508(spec: str) -> tuple[str, str | None]:
    match = _REQ.match(spec.strip())
    return (_norm_pip(match.group(1)), match.group(2)) if match else (_norm_pip(spec), None)


def _pyproject(text: str) -> list[Dep]:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return []
    lines = text.splitlines()
    deps: list[Dep] = []
    project = data.get("project", {})
    specs = list(project.get("dependencies", []))
    for group in project.get("optional-dependencies", {}).values():
        specs.extend(group)
    for spec in specs:
        name, version = _pep508(str(spec))
        deps.append(("pip", name, version, _line_of(lines, name)))
    poetry = data.get("tool", {}).get("poetry", {})
    for table in (poetry.get("dependencies", {}), poetry.get("dev-dependencies", {}),
                  *[g.get("dependencies", {}) for g in poetry.get("group", {}).values()]):
        for name, value in table.items():
            if name.lower() == "python":
                continue
            version = value if isinstance(value, str) else (value.get("version") if isinstance(value, dict) else None)
            deps.append(("pip", _norm_pip(name), version, _line_of(lines, name)))
    return deps


def _pipfile(text: str) -> list[Dep]:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return []
    lines = text.splitlines()
    return [("pip", _norm_pip(name), value if isinstance(value, str) and value != "*" else None, _line_of(lines, name))
            for table in (data.get("packages", {}), data.get("dev-packages", {})) for name, value in table.items()]


def _package_json(text: str) -> list[Dep]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, dict):
        return []
    lines = text.splitlines()
    deps: list[Dep] = []
    for section in ("dependencies", "devDependencies", "peerDependencies"):
        for name, version in (data.get(section) or {}).items():
            deps.append(("npm", name.lower(), str(version), _line_of(lines, f'"{name}"')))
    return deps


def _pom(text: str) -> list[Dep]:
    lines = text.splitlines()
    deps: list[Dep] = []
    for match in re.finditer(r"<artifactId>\s*([^<\s]+)\s*</artifactId>(?:\s*<version>\s*([^<\s]+)\s*</version>)?", text):
        line = text.count("\n", 0, match.start()) + 1
        deps.append(("maven", match.group(1).lower(), match.group(2), line))
    parent = re.search(r"<parent>.*?<artifactId>\s*spring-boot-starter-parent\s*</artifactId>\s*<version>\s*([^<\s]+)", text, re.S)
    if parent:
        deps.append(("maven", "spring-boot", parent.group(1), _line_of(lines, "spring-boot-starter-parent")))
    return deps


def _gradle(text: str) -> list[Dep]:
    deps: list[Dep] = []
    for number, line in enumerate(text.splitlines(), 1):
        for match in re.finditer(r"""['"]([\w.\-]+):([\w.\-]+)(?::([\w.\-+]+))?['"]""", line):
            deps.append(("maven", match.group(2).lower(), match.group(3), number))
        if "org.springframework.boot" in line:
            version = re.search(r"version\s*['\"]?([\w.\-]+)", line)
            deps.append(("maven", "spring-boot", version.group(1) if version else None, number))
    return deps


def _go_mod(text: str) -> list[Dep]:
    deps: list[Dep] = []
    for number, line in enumerate(text.splitlines(), 1):
        match = re.match(r"^\s*(?:require\s+)?([\w.\-]+\.[\w.\-]+/[\w./\-]+)\s+(v[\w.\-+]+)", line)
        if match:
            deps.append(("go", match.group(1).lower(), match.group(2), number))
    return deps


def _cargo(text: str) -> list[Dep]:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return []
    lines = text.splitlines()
    deps: list[Dep] = []
    for name, value in (data.get("dependencies") or {}).items():
        version = value if isinstance(value, str) else (value.get("version") if isinstance(value, dict) else None)
        deps.append(("cargo", name.lower(), version, _line_of(lines, name)))
    return deps


def _composer(text: str) -> list[Dep]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, dict):
        return []
    lines = text.splitlines()
    return [("composer", name.lower(), str(version), _line_of(lines, f'"{name}"'))
            for section in ("require", "require-dev") for name, version in (data.get(section) or {}).items()]


def _gemfile(text: str) -> list[Dep]:
    deps: list[Dep] = []
    for number, line in enumerate(text.splitlines(), 1):
        match = re.match(r"""^\s*gem\s+['"]([\w\-]+)['"](?:\s*,\s*['"]([^'"]+)['"])?""", line)
        if match:
            deps.append(("gem", match.group(1).lower(), match.group(2), number))
    return deps


def _csproj(text: str) -> list[Dep]:
    deps: list[Dep] = []
    for match in re.finditer(r'<PackageReference\s+Include="([^"]+)"(?:\s+Version="([^"]+)")?', text):
        deps.append(("nuget", match.group(1).lower(), match.group(2), text.count("\n", 0, match.start()) + 1))
    sdk = re.search(r'<Project\s+Sdk="Microsoft\.NET\.Sdk\.Web"', text)
    if sdk:
        deps.append(("nuget", "microsoft.aspnetcore.app", None, text.count("\n", 0, sdk.start()) + 1))
    return deps


READERS = {
    "requirements.txt": _requirements, "pyproject.toml": _pyproject, "Pipfile": _pipfile,
    "package.json": _package_json, "pom.xml": _pom, "build.gradle": _gradle, "build.gradle.kts": _gradle,
    "go.mod": _go_mod, "Cargo.toml": _cargo, "composer.json": _composer, "Gemfile": _gemfile,
}

_PACKAGE_INDEX: dict[tuple[str, str], Tech] = {
    (eco, name): tech for tech in TECHS for eco, names in tech.packages.items() for name in names
}
_IMAGE_INDEX: dict[str, Tech] = {image: tech for tech in TECHS for image in tech.images}

# Imágenes de runtime: nombre de imagen -> lenguaje.
_RUNTIME_IMAGES = {
    "python": "python", "node": "javascript", "openjdk": "java", "eclipse-temurin": "java", "amazoncorretto": "java",
    "golang": "go", "php": "php", "ruby": "ruby", "rust": "rust",
}
_PY_IMPORTS = {
    "flask": "flask", "django": "django", "fastapi": "fastapi", "sqlalchemy": "sqlalchemy", "pymongo": "mongodb",
    "psycopg2": "postgresql", "psycopg": "postgresql", "asyncpg": "postgresql", "pymysql": "mysql", "redis": "redis",
    "sqlite3": "sqlite", "pytest": "pytest",
}


def _service_of(rel: str, roots: list[str]) -> str:
    """Servicio dueño de un archivo: la raíz de manifiesto más específica que lo contiene."""
    best = "."
    for root in roots:
        if root != "." and (rel == root or rel.startswith(root + "/")) and len(root) > len(best if best != "." else ""):
            best = root
    return best


def _image_parts(image: str) -> tuple[str, str | None]:
    name, _, tag = image.strip().partition(":")
    return name.split("/")[-1].lower(), (tag or None)


# ---------------------------------------------------------------- análisis

def scan_stack(root: Path) -> StackReport:
    files = _walk(root)
    rels = {path: path.relative_to(root).as_posix() for path in files}
    acc = _Acc()

    # 1. Lenguajes por extensión y líneas
    by_language: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    extension_language = {ext: lang for lang, exts in LANGUAGE_EXTENSIONS.items() for ext in exts}
    for path in files:
        language = extension_language.get(path.suffix.lower())
        if not language:
            continue
        text = _read(path)
        if text is None or "\0" in text[:2000]:
            continue
        by_language[language][0] += 1
        by_language[language][1] += text.count("\n") + (0 if text.endswith("\n") or not text else 1)
    total_lines = sum(lines for _files, lines in by_language.values()) or 1
    languages = sorted(
        (Language(id=lang, name=BY_ID[lang].name, files=count, lines=lines, share=round(lines / total_lines, 4))
         for lang, (count, lines) in by_language.items() if lines > 0),
        key=lambda item: -item.lines,
    )

    # 2. Raíces de servicio = carpetas con manifiesto
    manifest_files = [p for p in files if p.name in MANIFESTS or p.suffix == ".csproj"]
    roots = sorted({Path(rels[p]).parent.as_posix() for p in manifest_files})
    roots = ["." if r in ("", ".") else r for r in roots]

    # 3. Dependencias declaradas
    for path in manifest_files:
        text = _read(path)
        if text is None:
            continue
        reader = READERS.get(path.name) or (_csproj if path.suffix == ".csproj" else None)
        if reader is None:
            continue
        rel = rels[path]
        service = _service_of(rel, roots)
        lines = text.splitlines()
        for ecosystem, name, version, line in reader(text):
            tech = _PACKAGE_INDEX.get((ecosystem, name))
            if tech is None and ecosystem == "maven":
                tech = next((t for t in TECHS if any(name == pkg or name.startswith(pkg + "-") for pkg in t.packages.get("maven", ()))), None)
            if tech:
                acc.add(tech, service, rel, line, lines[line - 1] if line and line <= len(lines) else name, version)
        if path.name == "pom.xml":
            acc.add(BY_ID["maven"], service, rel, 1, "pom.xml")
        elif path.name.startswith("build.gradle"):
            acc.add(BY_ID["gradle"], service, rel, 1, path.name)
        elif path.name == "package.json":
            acc.add(BY_ID["npm"], service, rel, 1, "package.json")

    # 4. Docker, compose, CI, Kubernetes, Terraform
    compose_services: list[tuple[str, str, str, dict[str, Any]]] = []  # (nombre, ruta, contexto, definición)
    for path in files:
        rel = rels[path]
        name = path.name
        service = _service_of(rel, roots)
        if name == "Dockerfile" or name.startswith("Dockerfile."):
            text = _read(path) or ""
            acc.add(BY_ID["docker"], service, rel, 1, "Dockerfile")
            for number, line in enumerate(text.splitlines(), 1):
                match = re.match(r"^\s*FROM\s+(?:--platform=\S+\s+)?(\S+)", line, re.I)
                if match:
                    image, tag = _image_parts(match.group(1))
                    language = _RUNTIME_IMAGES.get(image)
                    if language:
                        acc.add(BY_ID[language], service, rel, number, line, tag)
                    elif image in _IMAGE_INDEX:
                        acc.add(_IMAGE_INDEX[image], service, rel, number, line, tag)
        elif re.fullmatch(r"(docker-)?compose(\.[\w-]+)?\.ya?ml", name):
            text = _read(path) or ""
            acc.add(BY_ID["docker-compose"], service, rel, 1, name)
            try:
                data = yaml.safe_load(text) or {}
            except yaml.YAMLError:
                data = {}
            for svc_name, definition in ((data.get("services") or {}) if isinstance(data, dict) else {}).items():
                if not isinstance(definition, dict):
                    continue
                compose_services.append((str(svc_name), rel, str(_compose_context(definition)), definition))
                image = definition.get("image")
                if isinstance(image, str):
                    image_name, tag = _image_parts(image)
                    if image_name in _IMAGE_INDEX:
                        acc.add(_IMAGE_INDEX[image_name], service, rel, _line_of(text.splitlines(), image), image, tag)
        elif rel.startswith(".github/workflows/") and name.endswith((".yml", ".yaml")):
            acc.add(BY_ID["github-actions"], service, rel, 1, name)
        elif name.endswith(".tf"):
            acc.add(BY_ID["terraform"], service, rel, 1, name)
        elif name.endswith((".yml", ".yaml")) and ("k8s" in rel or "kubernetes" in rel or "deploy" in rel.lower()):
            text = _read(path) or ""
            if re.search(r"^apiVersion:", text, re.M) and re.search(r"^kind:\s*(Deployment|StatefulSet|Service|Ingress)\b", text, re.M):
                acc.add(BY_ID["kubernetes"], service, rel, 1, name)

    # 5. Imports de Python (donde falta manifiesto) y archivos SQLite
    py_files = [p for p in files if p.suffix == ".py"][:MAX_PY_IMPORT_FILES]
    for path in py_files:
        text = _read(path)
        if text is None:
            continue
        rel = rels[path]
        service = _service_of(rel, roots)
        for number, line in enumerate(text.splitlines(), 1):
            match = re.match(r"^\s*(?:from|import)\s+([A-Za-z0-9_]+)", line)
            if match and match.group(1).lower() in _PY_IMPORTS:
                acc.add(BY_ID[_PY_IMPORTS[match.group(1).lower()]], service, rel, number, line)
    for path in files:
        if path.suffix.lower() in {".sqlite", ".sqlite3", ".db"}:
            acc.add(BY_ID["sqlite"], _service_of(rels[path], roots), rels[path], None, "archivo de base de datos")

    # Los lenguajes van primero, con las cifras medidas como evidencia (sin archivo concreto).
    language_techs = [
        Detected(id=lang.id, name=lang.name, kind="language", icon=BY_ID[lang.id].icon, service=None,
                 evidence=[Evidence(path="", line=None, text=f"{lang.files} archivos · {lang.lines} líneas")])
        for lang in languages
    ]

    technologies = language_techs + sorted(acc.found.values(), key=lambda d: (d.kind, d.name, d.service or ""))

    # 6. Servicios y arquitectura
    services = _services(roots, technologies, files, rels, compose_services)
    architecture = _architecture(services, compose_services, technologies)
    targets = {
        tech.id: [Target(id=t.id, name=t.name, kind=t.kind, language=t.language, icon=t.icon) for t in targets_for(tech.id)]
        for tech in {d.id: d for d in technologies}.values() if targets_for(tech.id)
    }
    return StackReport(
        languages=languages,
        technologies=technologies,
        services=services,
        architecture=architecture,
        targets=targets,
        totals={"files": len(files), "lines": sum(lang.lines for lang in languages), "technologies": len({d.id for d in technologies})},
    )


def _compose_context(definition: dict[str, Any]) -> str:
    build = definition.get("build")
    if isinstance(build, str):
        return build
    if isinstance(build, dict):
        return str(build.get("context", "."))
    return ""


def _services(roots: list[str], technologies: list[Detected], files: list[Path], rels: dict[Path, str],
              compose_services: list[tuple[str, str, str, dict[str, Any]]]) -> list[Service]:
    dockerfiles = {Path(rels[p]).parent.as_posix() or "." for p in files if p.name == "Dockerfile" or p.name.startswith("Dockerfile.")}
    per_service: dict[str, list[str]] = defaultdict(list)
    for tech in technologies:
        if tech.service and tech.kind in {"backend", "frontend", "database", "orm"}:
            per_service[tech.service].append(tech.name)
    result: list[Service] = []
    for root in roots:
        techs = sorted(set(per_service.get(root, [])))
        if not techs and root not in dockerfiles:
            continue
        result.append(Service(name="raíz del proyecto" if root == "." else root, path=root, technologies=techs,
                              dockerfile=root in dockerfiles))
    return result


def _architecture(services: list[Service], compose_services: list[tuple[str, str, str, dict[str, Any]]],
                  technologies: list[Detected]) -> Architecture:
    backend_roots = sorted({t.service for t in technologies if t.kind == "backend" and t.service})
    frontend_roots = sorted({t.service for t in technologies if t.kind == "frontend" and t.service})
    own_code = [name for name, _rel, context, definition in compose_services if context]
    basis: list[str] = []
    if len(own_code) >= 2 or len(backend_roots) >= 2:
        if len(own_code) >= 2:
            basis.append(f"docker-compose define {len(own_code)} servicios con código propio: {', '.join(own_code)}")
        if len(backend_roots) >= 2:
            basis.append(f"hay {len(backend_roots)} carpetas con su propio backend: {', '.join(backend_roots)}")
        return Architecture(kind="microservices", basis=basis)
    apps = sorted(set(backend_roots) | set(frontend_roots))
    if len(apps) >= 2 and backend_roots and frontend_roots:
        basis.append(f"backend en {', '.join(backend_roots)} y frontend en {', '.join(frontend_roots)}, como aplicaciones separadas")
        return Architecture(kind="multi-app", basis=basis)
    if backend_roots or frontend_roots:
        basis.append(f"un solo servicio con {'backend' if backend_roots else 'frontend'} en {(backend_roots or frontend_roots)[0]}")
        return Architecture(kind="monolith", basis=basis)
    return Architecture(kind="unknown", basis=["no se detectó ningún framework de backend ni de frontend"])
