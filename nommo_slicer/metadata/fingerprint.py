from __future__ import annotations
import logging
from pathlib import Path
from zipfile import ZipFile, BadZipFile

from nommo_slicer import NommoSlicerError
from nommo_slicer.inputs import FingerprintRequest
from nommo_slicer.metadata.three_mf_writer import FINGERPRINT_ENTRY

logger = logging.getLogger(__name__)

# Defensive: none of these may ever be embedded into the .3mf.
CREDENTIAL_KEYS = {"account_info", "email", "password", "user_name"}


def has_embedded_fingerprint(path: Path) -> bool:
    try:
        with ZipFile(path, "r") as zf:
            return FINGERPRINT_ENTRY in zf.namelist()
    except BadZipFile:
        raise NommoSlicerError("INVALID_3MF", "Not a valid ZIP archive")


def ensure_fingerprint_library():
    """Import nommo_fingerprint lazily so it stays an optional dependency."""
    try:
        import nommo_fingerprint
    except ImportError:
        raise NommoSlicerError(
            "FINGERPRINT_UNAVAILABLE",
            "fingerprint.json was supplied but nommo_fingerprint is not installed "
            "(pip install 'nommo_slicer[fingerprint]')",
        )
    return nommo_fingerprint


def build_fingerprint(request: FingerprintRequest) -> dict:
    """Create a fingerprint, and register it with Nommo when account_info is present.

    All creation/auth/registration/EAS logic lives in nommo_fingerprint.
    """
    lib = ensure_fingerprint_library()

    try:
        fingerprint = lib.create_fingerprint(message=request.message)
        if request.account_info is not None:
            logger.info("Registering fingerprint with Nommo")
            fingerprint = lib.register_fingerprint(
                fingerprint,
                request.account_info,
                asset_id=request.asset_id,
            )
    except lib.NommoFingerprintError as e:
        # nommo_fingerprint guarantees its messages never contain credentials.
        raise NommoSlicerError(
            "FINGERPRINT_FAILED",
            f"Fingerprint {'registration' if request.account_info else 'creation'} failed: {e.message}",
            {"fingerprint_code": e.code},
        )

    if not isinstance(fingerprint, dict):
        raise NommoSlicerError("FINGERPRINT_FAILED", "nommo_fingerprint returned a non-object fingerprint")
    leaked = CREDENTIAL_KEYS & fingerprint.keys()
    if leaked:
        raise NommoSlicerError(
            "FINGERPRINT_FAILED",
            "Refusing to embed a fingerprint containing credential fields",
            {"fields": sorted(leaked)},
        )
    return fingerprint
