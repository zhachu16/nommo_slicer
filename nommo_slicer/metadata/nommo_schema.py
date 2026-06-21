from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Optional


@dataclass
class PlateInfo:
    plate_index: int
    expected_print_seconds: float
    expected_print_hours: float
    filament_grams_total: float
    filament_grams_by_material: dict[str, float]
    material_types: List[str]
    nommo_units: int

    @classmethod
    def from_dict(cls, d: dict) -> PlateInfo:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class NommoInfo:
    schema_version: str = "1"
    slicer: str = "NOMMO-Bambu"
    slicer_version: str = "0.1.0"
    source_3mf_sha256: str = ""
    printer_profile: str = ""
    printer_model: str = ""
    nozzle_size_mm: float = 0.4
    profile_bundle_version: str = ""
    pricing_formula_version: str = "v1"
    plate_count: int = 0
    plates: List[PlateInfo] = field(default_factory=list)
    total_nommo_units: int = 0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> NommoInfo:
        plates = [PlateInfo.from_dict(p) for p in d.get("plates", [])]
        kwargs = {k: v for k, v in d.items() if k != "plates"}
        return cls(plates=plates, **kwargs)
