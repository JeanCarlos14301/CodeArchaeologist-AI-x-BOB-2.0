"""Pruebas de Ingesta Segura (anti-ZipSlip, límites) y Extractores de Código (D-03)."""

import io
import zipfile
from pathlib import Path
import pytest

from backend.app.extractors.code_inventory import analyze_repository_inventory
from backend.app.pipeline.ingestion import (
    IngestionSecurityError,
    validate_and_extract_zip,
    prepare_repository,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def test_zipslip_is_strictly_rejected(tmp_path: Path):
    """Verifica que un archivo ZIP que intenta escapar del sandbox sea rechazado con error de seguridad."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        # Miembro malicioso con ../
        zf.writestr("../../escape.txt", "contenido peligroso")

    buf.seek(0)
    dest = tmp_path / "sandbox_dest"

    with pytest.raises(IngestionSecurityError) as exc_info:
        validate_and_extract_zip(buf.getvalue(), dest)
    assert "ZipSlip" in str(exc_info.value) or "Ruta no permitida" in str(exc_info.value)


def test_dangerous_executable_extension_rejected(tmp_path: Path):
    """Verifica que ejecutables binarios (.exe, .dll, .so) sean bloqueados."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("trojan.exe", b"\x4d\x5a\x90\x00")

    buf.seek(0)
    dest = tmp_path / "sandbox_dest"

    with pytest.raises(IngestionSecurityError) as exc_info:
        validate_and_extract_zip(buf.getvalue(), dest)
    assert "Extensión binaria o ejecutable no permitida" in str(exc_info.value)


def test_valid_zip_extraction(tmp_path: Path):
    """Verifica la extracción limpia y sanitización de un archivo ZIP válido."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("module.py", "def foo(): return 42\n")
        zf.writestr(".env", "SECRET=test\n")

    buf.seek(0)
    dest = tmp_path / "extracted"
    validate_and_extract_zip(buf.getvalue(), dest)

    assert (dest / "module.py").exists()
    # .env debe haber sido eliminado en la fase de sanitización
    assert not (dest / ".env").exists()


def test_code_inventory_on_facturaya():
    """Verifica la extracción estática de rutas, SQL, radon y dependencias circulares en FacturaYa v1."""
    sample_dir = BASE_DIR / "samples" / "facturaya-v1"
    if not sample_dir.exists():
        pytest.skip("Directorio samples/facturaya-v1 no disponible")

    report = analyze_repository_inventory(sample_dir)

    # 1. Rutas Flask detectadas
    rules = [r.rule for r in report.routes]
    assert any("/invoices" in r for r in rules), f"Rutas detectadas: {rules}"

    # 2. Función monolítica detectada por radon
    fn_names = [f.function_name for f in report.complex_functions if f.is_monolithic]
    assert "invoice_new" in fn_names, f"Monolito no detectado en: {fn_names}"

    # 3. Consultas SQL detectadas
    assert len(report.sql_queries) > 0
    sql_types = {q.query_type for q in report.sql_queries}
    assert "SELECT" in sql_types

    # 4. Dependencia circular entre billing y customers
    found_circ = False
    for pair in report.circular_dependencies:
        names = [Path(p).stem for p in pair]
        if "billing" in names and "customers" in names:
            found_circ = True
            break
    assert found_circ, f"Dependencias circulares: {report.circular_dependencies}"
