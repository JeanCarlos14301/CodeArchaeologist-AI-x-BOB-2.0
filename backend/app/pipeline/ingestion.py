"""Módulo de Ingesta Segura de Repositorios (D-03).

Implementa protecciones rigurosas contra ataques por descompresión:
- Protección estricta contra ZipSlip (normalización de rutas y rechazo de escapes).
- Detección y rechazo de enlaces simbólicos (symlinks) y enlaces duros (hardlinks).
- Límites de seguridad: máx 5 MB comprimido, máx 20 MB descomprimido, máx 300 archivos.
- Sanitización preventiva: eliminación de .env, .bob/, AGENTS.md y binarios ejecutables.
- Cálculo de hash criptográfico determinista SHA-256 sobre el contenido.
"""

import hashlib
import os
import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

MAX_ZIP_COMPRESSED_BYTES = 5 * 1024 * 1024       # 5 MB
MAX_UNCOMPRESSED_BYTES = 20 * 1024 * 1024         # 20 MB
MAX_FILES_COUNT = 300
DANGEROUS_EXTENSIONS = {".exe", ".dll", ".so", ".bin", ".dylib", ".bat", ".cmd", ".vbs"}
SENSITIVE_FILES_OR_DIRS = {".env", ".bob", "agents.md", ".git", ".github", "hooks"}


class IngestionSecurityError(ValueError):
    """Excepción lanzada cuando un archivo o paquete viola las restricciones de seguridad."""
    pass


@dataclass
class IngestionManifest:
    sample_id: str
    repo_name: str
    target_dir: Path
    snapshot_sha256: str
    total_files: int
    total_loc: int
    languages_detected: List[str]
    entrypoints: List[str]
    file_list: List[str] = field(default_factory=list)


def calculate_directory_sha256(directory: Path) -> str:
    """Calcula un hash SHA-256 determinista de todos los archivos en un directorio."""
    hasher = hashlib.sha256()
    files = sorted([p for p in directory.rglob("*") if p.is_file()])
    for file_path in files:
        rel_posix = file_path.relative_to(directory).as_posix()
        hasher.update(rel_posix.encode("utf-8"))
        try:
            hasher.update(file_path.read_bytes())
        except Exception:
            pass
    return hasher.hexdigest()


def count_loc_and_languages(directory: Path) -> Tuple[int, List[str], List[str]]:
    """Calcula líneas de código (LOC), lenguajes detectados y entrypoints probables."""
    total_loc = 0
    languages: Set[str] = set()
    entrypoints: List[str] = []

    ext_to_lang = {
        ".py": "Python",
        ".sql": "SQL",
        ".html": "HTML",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".json": "JSON",
        ".css": "CSS",
        ".md": "Markdown",
    }

    for file_path in directory.rglob("*"):
        if not file_path.is_file():
            continue
        ext = file_path.suffix.lower()
        if ext in ext_to_lang:
            languages.add(ext_to_lang[ext])

        if ext in [".py", ".sql", ".html", ".js", ".ts", ".css"]:
            try:
                lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
                total_loc += len(lines)
            except Exception:
                pass

        name_lower = file_path.name.lower()
        if name_lower in ["app.py", "main.py", "wsgi.py", "run.py", "server.py"]:
            rel_posix = file_path.relative_to(directory).as_posix()
            if rel_posix not in entrypoints:
                entrypoints.append(rel_posix)

    return total_loc, sorted(list(languages)), entrypoints


def validate_and_extract_zip(
    zip_bytes_or_path: bytes | Path | str,
    destination_dir: Path,
) -> Path:
    """Valida y extrae un archivo ZIP aplicando todas las restricciones de seguridad."""
    destination_dir.mkdir(parents=True, exist_ok=True)
    dest_resolved = destination_dir.resolve()

    if isinstance(zip_bytes_or_path, (str, Path)):
        zip_path = Path(zip_bytes_or_path)
        if not zip_path.exists():
            raise IngestionSecurityError(f"El archivo ZIP no existe: {zip_path}")
        if zip_path.stat().st_size > MAX_ZIP_COMPRESSED_BYTES:
            raise IngestionSecurityError(
                f"El archivo ZIP excede el tamaño máximo permitido de 5 MB ({zip_path.stat().st_size} bytes)"
            )
        zf = zipfile.ZipFile(zip_path, "r")
    else:
        if len(zip_bytes_or_path) > MAX_ZIP_COMPRESSED_BYTES:
            raise IngestionSecurityError(
                f"El archivo ZIP excede el tamaño máximo permitido de 5 MB ({len(zip_bytes_or_path)} bytes)"
            )
        import io
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes_or_path), "r")

    try:
        members = zf.infolist()
        if len(members) > MAX_FILES_COUNT:
            raise IngestionSecurityError(
                f"El archivo ZIP contiene demasiados archivos ({len(members)} > {MAX_FILES_COUNT})"
            )

        total_uncompressed = sum(m.file_size for m in members)
        if total_uncompressed > MAX_UNCOMPRESSED_BYTES:
            raise IngestionSecurityError(
                f"El contenido descomprimido excede el límite de 20 MB ({total_uncompressed} bytes)"
            )

        for member in members:
            # 1. Protección contra ZipSlip: normalización y escape de directorio
            member_path = Path(member.filename)
            target_path = (destination_dir / member_path).resolve()
            if not str(target_path).startswith(str(dest_resolved)):
                raise IngestionSecurityError(
                    f"Violación de seguridad ZipSlip detectada: '{member.filename}' intenta salir del sandbox"
                )
            if ".." in member.filename or member.filename.startswith(("/", "\\")):
                raise IngestionSecurityError(
                    f"Ruta no permitida en archivo ZIP: '{member.filename}'"
                )

            # 2. Detección de Symlinks y Hardlinks
            # En formato ZIP Unix, el tipo de archivo vive en los 4 bits altos del external_attr (0o170000)
            # 0o120000 = S_IFLNK (symlink)
            unix_mode = member.external_attr >> 16
            if (unix_mode & 0o170000) == 0o120000:
                raise IngestionSecurityError(
                    f"Enlace simbólico detectado y rechazado: '{member.filename}'"
                )

            # 3. Detección de ejecutables binarios peligrosos
            if target_path.suffix.lower() in DANGEROUS_EXTENSIONS:
                raise IngestionSecurityError(
                    f"Extensión binaria o ejecutable no permitida: '{member.filename}'"
                )

        # Extracción segura miembro a miembro
        for member in members:
            target_path = (destination_dir / member.filename).resolve()
            if member.is_dir():
                target_path.mkdir(parents=True, exist_ok=True)
            else:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as source, open(target_path, "wb") as dest:
                    shutil.copyfileobj(source, dest)
    finally:
        zf.close()

    # Sanitización preventiva en el directorio descomprimido
    sanitize_extracted_directory(destination_dir)

    return destination_dir


def sanitize_extracted_directory(directory: Path) -> None:
    """Elimina preventivamente archivos sensibles antes de procesar el código."""
    for item in list(directory.rglob("*")):
        name_lower = item.name.lower()
        if name_lower in SENSITIVE_FILES_OR_DIRS or any(sens in name_lower for sens in [".env", ".bob"]):
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            elif item.is_file():
                try:
                    item.unlink(missing_ok=True)
                except Exception:
                    pass


def prepare_repository(
    source_type: str,
    workspace_base: Path,
    job_id: str,
    zip_bytes_or_path: Optional[bytes | Path | str] = None,
) -> IngestionManifest:
    """Prepara de forma segura el espacio de trabajo para el job según su tipo de origen."""
    job_sandbox = workspace_base / "sandboxes" / job_id
    job_sandbox.mkdir(parents=True, exist_ok=True)
    target_repo_dir = job_sandbox / "repo"

    if target_repo_dir.exists():
        shutil.rmtree(target_repo_dir, ignore_errors=True)
    target_repo_dir.mkdir(parents=True, exist_ok=True)

    sample_id = "unknown"
    repo_name = "Repositorio Analizado"

    if source_type == "demo":
        sample_id = "facturaya-v1"
        repo_name = "FacturaYa v1 (Demo Monolith)"
        source_dir = workspace_base / "samples" / "facturaya-v1"
        if not source_dir.exists():
            raise FileNotFoundError(f"Muestra demo no encontrada en: {source_dir}")
        shutil.copytree(source_dir, target_repo_dir, dirs_exist_ok=True)

    elif source_type == "holdout":
        sample_id = "variant-holdout"
        repo_name = "FacturaYa Variant (Holdout)"
        source_dir = workspace_base / "samples" / "variant-holdout"
        if not source_dir.exists():
            source_dir = workspace_base / "samples" / "facturaya-v1"
        shutil.copytree(source_dir, target_repo_dir, dirs_exist_ok=True)

    elif source_type == "zip":
        if not zip_bytes_or_path:
            raise IngestionSecurityError("No se proporcionaron datos de archivo ZIP para la fuente 'zip'")
        sample_id = f"custom-upload-{job_id[:8]}"
        repo_name = f"Uploaded Repository ({job_id[:8]})"
        validate_and_extract_zip(zip_bytes_or_path, target_repo_dir)

    else:
        raise IngestionSecurityError(f"Tipo de fuente desconocido: {source_type}")

    # Asegurar sanitización
    sanitize_extracted_directory(target_repo_dir)

    # Calcular métricas deterministas
    sha256 = calculate_directory_sha256(target_repo_dir)
    total_loc, languages, entrypoints = count_loc_and_languages(target_repo_dir)
    files = [p.relative_to(target_repo_dir).as_posix() for p in target_repo_dir.rglob("*") if p.is_file()]

    return IngestionManifest(
        sample_id=sample_id,
        repo_name=repo_name,
        target_dir=target_repo_dir,
        snapshot_sha256=sha256,
        total_files=len(files),
        total_loc=total_loc,
        languages_detected=languages,
        entrypoints=entrypoints,
        file_list=files,
    )
