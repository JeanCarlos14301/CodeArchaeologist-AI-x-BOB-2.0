"""Detección de stack: lenguajes, frameworks, bases de datos, infraestructura y arquitectura."""

import json
from pathlib import Path

from app.modernization.stack_scan import scan_stack

REPO_ROOT = Path(__file__).resolve().parents[2]


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _ids(report, kind: str | None = None) -> set[str]:
    return {t.id for t in report.technologies if kind is None or t.kind == kind}


def test_flask_sqlite_sample_is_detected_with_evidence() -> None:
    report = scan_stack(REPO_ROOT / "samples" / "facturaya-v1")
    assert "python" in _ids(report, "language")
    assert "flask" in _ids(report, "backend")
    assert "sqlite" in _ids(report, "database")
    flask = next(t for t in report.technologies if t.id == "flask")
    assert flask.evidence and flask.evidence[0].path and flask.evidence[0].line
    assert report.architecture.kind == "monolith"
    assert "fastapi" in {t.id for t in report.targets["flask"]}


def test_backend_and_frontend_in_separate_folders_are_multi_app(tmp_path: Path) -> None:
    _write(tmp_path, "backend/requirements.txt", "fastapi==0.110.0\npsycopg2-binary>=2.9\n")
    _write(tmp_path, "backend/main.py", "from fastapi import FastAPI\n")
    _write(tmp_path, "frontend/package.json", json.dumps({"dependencies": {"react": "^18.2.0"}, "devDependencies": {"vite": "^5.0.0"}}))
    _write(tmp_path, "frontend/src/App.jsx", "export default function App() { return null }\n")
    report = scan_stack(tmp_path)
    assert {"fastapi", "react"} <= _ids(report)
    assert "postgresql" in _ids(report, "database")
    assert report.architecture.kind == "multi-app"
    react = next(t for t in report.technologies if t.id == "react")
    assert react.version == "^18.2.0" and react.service == "frontend"
    assert sum(lang.share for lang in report.languages) > 0.99


def test_compose_with_two_own_services_is_microservices(tmp_path: Path) -> None:
    _write(tmp_path, "docker-compose.yml", "services:\n  users:\n    build: ./users\n  orders:\n    build: ./orders\n  db:\n    image: postgres:16\n")
    _write(tmp_path, "users/pom.xml", "<project><parent><artifactId>spring-boot-starter-parent</artifactId><version>3.2.1</version></parent></project>")
    _write(tmp_path, "orders/package.json", json.dumps({"dependencies": {"express": "4.18.2"}}))
    _write(tmp_path, "users/Dockerfile", "FROM eclipse-temurin:17\n")
    report = scan_stack(tmp_path)
    assert report.architecture.kind == "microservices"
    assert {"spring-boot", "express", "postgresql", "docker-compose", "java"} <= _ids(report)
    spring = next(t for t in report.technologies if t.id == "spring-boot")
    assert spring.version == "3.2.1"


def test_nothing_is_invented_for_an_empty_project(tmp_path: Path) -> None:
    _write(tmp_path, "notes.txt", "hola")
    report = scan_stack(tmp_path)
    assert report.technologies == [] and report.architecture.kind == "unknown"


def test_dependency_directories_are_ignored(tmp_path: Path) -> None:
    _write(tmp_path, "node_modules/express/package.json", json.dumps({"dependencies": {"express": "4"}}))
    _write(tmp_path, "app.py", "import flask\n")
    report = scan_stack(tmp_path)
    assert "express" not in _ids(report) and "flask" in _ids(report)
