from __future__ import annotations
import os
import zipfile
from pathlib import Path

from nommo_slicer.security.limits import LimitsConfig, default_limits


class ArchiveValidationError(Exception):
    def __init__(self, code: str, message: str, details: dict | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


def validate_3mf(
    path: Path,
    limits: LimitsConfig = default_limits,
) -> None:
    """Validate a .3mf archive before processing. Raises ArchiveValidationError on failure."""
    if not path.exists():
        raise ArchiveValidationError("INVALID_3MF", f"File not found: {path}")

    if path.stat().st_size > limits.max_file_size_bytes:
        raise ArchiveValidationError(
            "RESOURCE_LIMIT_EXCEEDED",
            f"File exceeds size limit ({path.stat().st_size} > {limits.max_file_size_bytes})",
        )

    try:
        with zipfile.ZipFile(path, "r") as zf:
            _check_zip_bomb(zf, limits)
            _check_path_traversal(zf)
            _check_encrypted(zf)
            _check_content_types(zf)
    except zipfile.BadZipFile:
        raise ArchiveValidationError("INVALID_3MF", "Not a valid ZIP archive")
    except ArchiveValidationError:
        raise


def _check_zip_bomb(zf: zipfile.ZipFile, limits: LimitsConfig) -> None:
    total_uncompressed = 0
    for info in zf.infolist():
        total_uncompressed += info.file_size
        if info.compress_size > limits.max_compressed_ratio * info.file_size:
            raise ArchiveValidationError(
                "INVALID_3MF",
                f"Compression ratio too high for entry: {info.filename}",
            )
    if total_uncompressed > limits.max_decompressed_bytes:
        raise ArchiveValidationError(
            "RESOURCE_LIMIT_EXCEEDED",
            f"Total decompressed size exceeds limit ({total_uncompressed} > {limits.max_decompressed_bytes})",
        )


def _check_path_traversal(zf: zipfile.ZipFile) -> None:
    for info in zf.infolist():
        path = info.filename
        if path.startswith("/") or ".." in path.split("/"):
            raise ArchiveValidationError(
                "INVALID_3MF",
                f"Path traversal detected in archive entry: {path}",
            )


def _check_encrypted(zf: zipfile.ZipFile) -> None:
    for info in zf.infolist():
        if info.flag_bits & 0x1:
            raise ArchiveValidationError(
                "INVALID_3MF",
                f"Encrypted archive entry: {info.filename}",
            )


def _check_content_types(zf: zipfile.ZipFile) -> None:
    if "[Content_Types].xml" not in zf.namelist():
        raise ArchiveValidationError(
            "INVALID_3MF",
            "Missing [Content_Types].xml required for .3mf format",
        )
