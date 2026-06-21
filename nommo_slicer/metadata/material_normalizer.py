from __future__ import annotations
from typing import Dict, Optional

# Mapping from filament profile identifiers to canonical NOMMO material types.
# Keys are substrings that match against filament type/name.
_CANONICAL_MAP: Dict[str, str] = {
    "PLA Basic": "PLA_BASIC",
    "PLA Matte": "PLA_MATTE",
    "PLA Silk": "PLA_SILK",
    "PLA Tough": "PLA_TOUGH",
    "PLA+": "PLA_PLUS",
    "PLA Meta": "PLA_META",
    "PLA Sparkle": "PLA_SPARKLE",
    "PLA Glow": "PLA_GLOW",
    "PLA": "PLA_BASIC",
    "PETG": "PETG",
    "PETG Translucent": "PETG_TRANSLUCENT",
    "ABS": "ABS",
    "ASA": "ASA",
    "PC": "PC",
    "PA": "PA",
    "PA-CF": "PA_CF",
    "PA-GF": "PA_GF",
    "PET-CF": "PET_CF",
    "PETG-CF": "PETG_CF",
    "TPU": "TPU",
    "TPU 95A": "TPU_95A",
    "PVA": "PVA",
    "HIPS": "HIPS",
    "PP": "PP",
    "PPS": "PPS",
    "PPS-CF": "PPS_CF",
}


def normalize_material_type(filament_type: str, filament_name: str = "") -> str:
    """Map a filament profile's type/name to a canonical NOMMO material type."""
    combined = f"{filament_type} {filament_name}".strip()
    for key, canonical in _CANONICAL_MAP.items():
        if key in combined:
            return canonical
    # Fall back to the raw type string, cleaned up
    raw = (filament_type or filament_name or "UNKNOWN").upper().replace(" ", "_")
    return raw[:32]
