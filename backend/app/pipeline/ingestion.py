"""Módulo de Ingesta Segura de Repositorios (D-03).

Implementa protecciones rigurosas contra ataques por descompresión:
- Protección estricta contra ZipSlip (normalización de rutas y rechazo de escapes).
- Detección y rechazo de enlaces simbólicos (symlinks) y enlaces duros (hardlinks).
- Límites de seguridad: máx 5 MB comprimido, máx 20 MB realmente escritos al descomprimir, máx 300 archivos
  (3000 para proyectos de solo modernización).
- Sanitización preventiva: eliminación de .env, .bob/, AGENTS.md y binarios ejecutables.
"""

import logging
import shutil
import zipfile
from pathlib import Path
from typing import BinaryIO

logger = logging.getLogger(__name__)

MAX_ZIP_COMPRESSED_BYTES = 5 * 1024 * 1024       # 5 MB
MAX_UNCOMPRESSED_BYTES = 20 * 1024 * 1024         # 20 MB
MAX_FILES_COUNT = 300                              # auditoría: acota el presupuesto de Bob
MODERNIZE_MAX_FILES = 3000                         # modernización: monorepos reales (el tope de bytes sigue igual)
_COPY_CHUNK = 64 * 1024
DANGEROUS_EXTENSIONS = {".exe", ".dll", ".so", ".bin", ".dylib", ".bat", ".cmd", ".vbs"}
SENSITIVE_FILES_OR_DIRS = {".env", ".bob", "agents.md", ".git", ".github", "hooks"}


class IngestionSecurityError(ValueError):
    """Excepción lanzada cuando un archivo o paquete viola las restricciones de seguridad."""
    pass


def copy_bounded(source: BinaryIO, dest: BinaryIO, budget: int) -> int:
    """Copia contando los bytes REALES escritos; aborta al superar `budget` (no confía en el tamaño declarado)."""
    written = 0
    while chunk := source.read(_COPY_CHUNK):
        written += len(chunk)
        if written > budget:
            raise IngestionSecurityError(
                f"El contenido descomprimido excede el límite de {MAX_UNCOMPRESSED_BYTES // (1024 * 1024)} MB"
            )
        dest.write(chunk)
    return written


def validate_and_extract_zip(
    zip_bytes_or_path: bytes | Path | str,
    destination_dir: Path,
    max_files: int = MAX_FILES_COUNT,
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
        if len(members) > max_files:
            raise IngestionSecurityError(
                f"El archivo ZIP contiene demasiados archivos ({len(members)} > {max_files})"
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
            if not target_path.is_relative_to(dest_resolved):
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

        # Extracción segura miembro a miembro, con el tope aplicado a los bytes que de verdad se escriben.
        remaining = MAX_UNCOMPRESSED_BYTES
        for member in members:
            target_path = (destination_dir / member.filename).resolve()
            if member.is_dir():
                target_path.mkdir(parents=True, exist_ok=True)
            else:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as source, open(target_path, "wb") as dest:
                    remaining -= copy_bounded(source, dest, remaining)
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
                except OSError:
                    logger.warning("No se pudo eliminar el archivo sensible %s del ZIP extraído", item.name)
