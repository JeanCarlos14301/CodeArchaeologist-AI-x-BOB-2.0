"""Safe repository ingestion (D-03).

Strict protections against decompression attacks:
- Strict ZipSlip protection (path normalization and rejection of escapes).
- Detection and rejection of symbolic links (symlinks) and hard links.
- Safety limits: max 5 MB compressed, max 20 MB actually written while extracting, max 300 files
  (3000 for modernization-only projects).
- Preventive sanitization: removal of .env, .bob/, AGENTS.md and executable binaries.
"""

import logging
import shutil
import zipfile
from pathlib import Path
from typing import BinaryIO

logger = logging.getLogger(__name__)

MAX_ZIP_COMPRESSED_BYTES = 5 * 1024 * 1024       # 5 MB
MAX_UNCOMPRESSED_BYTES = 20 * 1024 * 1024         # 20 MB
MAX_FILES_COUNT = 300                              # audit: bounds Bob's budget
MODERNIZE_MAX_FILES = 3000                         # modernization: real monorepos (the byte cap stays the same)
_COPY_CHUNK = 64 * 1024
DANGEROUS_EXTENSIONS = {".exe", ".dll", ".so", ".bin", ".dylib", ".bat", ".cmd", ".vbs"}
SENSITIVE_FILES_OR_DIRS = {".env", ".bob", "agents.md", ".git", ".github", "hooks"}


class IngestionSecurityError(ValueError):
    """Raised when a file or archive violates the security constraints."""
    pass


def copy_bounded(source: BinaryIO, dest: BinaryIO, budget: int) -> int:
    """Copies while counting the REAL bytes written; aborts past `budget` (never trusts the declared size)."""
    written = 0
    while chunk := source.read(_COPY_CHUNK):
        written += len(chunk)
        if written > budget:
            raise IngestionSecurityError(
                f"The uncompressed content exceeds the {MAX_UNCOMPRESSED_BYTES // (1024 * 1024)} MB limit"
            )
        dest.write(chunk)
    return written


def validate_and_extract_zip(
    zip_bytes_or_path: bytes | Path | str,
    destination_dir: Path,
    max_files: int = MAX_FILES_COUNT,
) -> Path:
    """Validates and extracts a ZIP file, applying every security constraint."""
    destination_dir.mkdir(parents=True, exist_ok=True)
    dest_resolved = destination_dir.resolve()

    if isinstance(zip_bytes_or_path, (str, Path)):
        zip_path = Path(zip_bytes_or_path)
        if not zip_path.exists():
            raise IngestionSecurityError(f"The ZIP file does not exist: {zip_path}")
        if zip_path.stat().st_size > MAX_ZIP_COMPRESSED_BYTES:
            raise IngestionSecurityError(
                f"The ZIP file exceeds the maximum allowed size of 5 MB ({zip_path.stat().st_size} bytes)"
            )
        zf = zipfile.ZipFile(zip_path, "r")
    else:
        if len(zip_bytes_or_path) > MAX_ZIP_COMPRESSED_BYTES:
            raise IngestionSecurityError(
                f"The ZIP file exceeds the maximum allowed size of 5 MB ({len(zip_bytes_or_path)} bytes)"
            )
        import io
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes_or_path), "r")

    try:
        members = zf.infolist()
        if len(members) > max_files:
            raise IngestionSecurityError(
                f"The ZIP file contains too many files ({len(members)} > {max_files})"
            )

        total_uncompressed = sum(m.file_size for m in members)
        if total_uncompressed > MAX_UNCOMPRESSED_BYTES:
            raise IngestionSecurityError(
                f"The uncompressed content exceeds the 20 MB limit ({total_uncompressed} bytes)"
            )

        for member in members:
            # 1. ZipSlip protection: normalization and directory escape
            member_path = Path(member.filename)
            target_path = (destination_dir / member_path).resolve()
            if not target_path.is_relative_to(dest_resolved):
                raise IngestionSecurityError(
                    f"ZipSlip security violation detected: '{member.filename}' tries to leave the sandbox"
                )
            if ".." in member.filename or member.filename.startswith(("/", "\\")):
                raise IngestionSecurityError(
                    f"Path not allowed in the ZIP file: '{member.filename}'"
                )

            # 2. Symlink and hard link detection
            # In the Unix ZIP format, the file type lives in the top 4 bits of external_attr (0o170000)
            # 0o120000 = S_IFLNK (symlink)
            unix_mode = member.external_attr >> 16
            if (unix_mode & 0o170000) == 0o120000:
                raise IngestionSecurityError(
                    f"Symbolic link detected and rejected: '{member.filename}'"
                )

            # 3. Detection of dangerous executable binaries
            if target_path.suffix.lower() in DANGEROUS_EXTENSIONS:
                raise IngestionSecurityError(
                    f"Binary or executable extension not allowed: '{member.filename}'"
                )

        # Safe member-by-member extraction, with the cap applied to the bytes actually written.
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

    # Preventive sanitization of the extracted directory
    sanitize_extracted_directory(destination_dir)

    return destination_dir


def sanitize_extracted_directory(directory: Path) -> None:
    """Preventively removes sensitive files before the code is processed."""
    for item in list(directory.rglob("*")):
        name_lower = item.name.lower()
        if name_lower in SENSITIVE_FILES_OR_DIRS or any(sens in name_lower for sens in [".env", ".bob"]):
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            elif item.is_file():
                try:
                    item.unlink(missing_ok=True)
                except OSError:
                    logger.warning("Could not remove the sensitive file %s from the extracted ZIP", item.name)
