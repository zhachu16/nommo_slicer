from __future__ import annotations
from typing import Dict, List, Tuple

from nommo_slicer.metadata.material_normalizer import normalize_material_type
from nommo_slicer.metadata.pricing import get_formula


def extract_plate_estimates(
    slice_result: dict,
    pricing_version: str = "v1",
    filament_info: List = None,
) -> dict:
    """Convert slice result into plate metadata with NOMMO units."""
    filament_info = filament_info or []

    print_hours = slice_result["print_time_hours"]
    filament_grams = slice_result.get("filament_weight_g", 0.0)

    formula = get_formula(pricing_version)
    nommo_units = formula.calculate(print_hours, filament_grams)

    # Build per-material breakdown
    material_types = set()
    grams_by_material: Dict[str, float] = {}
    for fi in filament_info:
        mat = normalize_material_type(fi.type, fi.name)
        material_types.add(mat)
        grams_by_material[mat] = grams_by_material.get(mat, 0.0) + filament_grams / max(len(filament_info), 1)

    return {
        "plate_index": slice_result["plate_index"],
        "expected_print_seconds": slice_result["print_time_seconds"],
        "expected_print_hours": print_hours,
        "filament_grams_total": filament_grams,
        "filament_grams_by_material": grams_by_material,
        "material_types": sorted(material_types),
        "nommo_units": nommo_units,
    }
