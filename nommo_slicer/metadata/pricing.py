from __future__ import annotations
from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class PricingFormulaV1:
    version: str = "v1"
    A: float = 35.0       # per hour
    B: float = 1.0        # per gram
    SETUP_UNITS: float = 15.0
    MIN_UNITS: float = 60.0

    def calculate(self, print_hours: float, filament_grams: float) -> int:
        units = max(
            self.MIN_UNITS,
            self.SETUP_UNITS
            + self.A * print_hours
            + self.B * filament_grams,
        )
        return round(units)


_formulas: Dict[str, PricingFormulaV1] = {
    "v1": PricingFormulaV1(),
}


def get_formula(version: str = "v1") -> PricingFormulaV1:
    if version not in _formulas:
        raise ValueError(f"Unknown pricing formula version: {version}")
    return _formulas[version]
