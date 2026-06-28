from __future__ import annotations
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


class NommoSlicerError(Exception):
    def __init__(self, code: str, message: str, details: dict | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


@dataclass
class SliceOptions:
    profiles_dir: Path | None = None
    printer_profile: str | None = None
    process_profile: str | None = None
    filament_profile: str | None = None
    plate: int | None = None
    threads: int | None = None
    temp_dir: Path | None = None
    replace_existing_metadata: bool = False
    progress_callback: Callable[[str, dict], None] | None = None
    limits: "LimitsConfig" | None = None
    pricing_formula_version: str = "v1"


@dataclass
class PlateResult:
    plate_index: int
    expected_print_seconds: float
    expected_print_hours: float
    filament_grams_total: float
    filament_grams_by_material: dict[str, float]
    material_types: List[str]
    nommo_units: int


@dataclass
class SliceResult:
    output_path: Path | None
    plate_count: int
    plates: List[PlateResult]
    total_nommo_units: int
    total_print_seconds: float
    total_filament_grams: float
    warnings: List[str]
    printer_profile: str = ""
    printer_model: str = ""
    nozzle_size_mm: float = 0.4


def slice_and_enrich(
    input_3mf: Path,
    output_3mf: Path,
    options: SliceOptions | None = None,
) -> SliceResult:
    """Main entry point: load, slice (or read existing GCode), compute NOMMO units, write enriched .3mf."""
    # Lazy imports so pure-Python tests can load without the native module
    from nommo_slicer.engine.project_loader import load_project
    from nommo_slicer.engine.profile_resolver import resolve_profiles
    from nommo_slicer.engine.slice_runner import SliceRunner
    from nommo_slicer.engine.estimate_extractor import extract_plate_estimates
    from nommo_slicer.metadata.nommo_schema import NommoInfo, PlateInfo
    from nommo_slicer.metadata.three_mf_writer import write_enriched_3mf
    from nommo_slicer.security.limits import default_limits

    opts = options or SliceOptions()
    limits = opts.limits or default_limits
    cb = opts.progress_callback

    def _progress(stage: str, data: dict):
        if cb:
            cb(stage, data)

    _progress("validating", {})

    project = load_project(input_3mf, limits)

    _progress("resolving_profiles", {})
    profiles_dir = opts.profiles_dir or Path(__file__).parent / "profiles"
    bundle = resolve_profiles(profiles_dir, project_presets=project.project_presets)

    runner = SliceRunner(progress_callback=cb)
    plate_results: List[PlateResult] = []
    all_warnings: List[str] = []
    total_print_seconds = 0.0
    total_filament_grams = 0.0
    total_nommo_units = 0

    plates_to_slice = project.plates
    if opts.plate is not None:
        plates_to_slice = [p for p in plates_to_slice if p.plate_index == opts.plate]
        if not plates_to_slice:
            raise NommoSlicerError("INVALID_3MF", f"Plate {opts.plate} not found")

    for plate in plates_to_slice:
        if plate.gcode_prediction:
            _progress("calculating_estimates", {"plate_index": plate.plate_index})
            slice_result = runner.process_existing_gcode(
                plate.gcode_prediction,
                project.config,
                is_bbl=project.is_bbl_3mf,
            )
        else:
            _progress("slicing_plate", {"plate_index": plate.plate_index})
            slice_result = runner.run_plate(
                plate.plate_index,
                project.model,
                project.config,
                is_bbl=project.is_bbl_3mf,
                temp_dir=opts.temp_dir,
                plate_data=plate,
            )

        estimates = extract_plate_estimates(
            slice_result,
            pricing_version=opts.pricing_formula_version,
            filament_info=plate.slice_filaments_info,
        )

        pr = PlateResult(
            plate_index=estimates["plate_index"],
            expected_print_seconds=estimates["expected_print_seconds"],
            expected_print_hours=estimates["expected_print_hours"],
            filament_grams_total=estimates["filament_grams_total"],
            filament_grams_by_material=estimates["filament_grams_by_material"],
            material_types=estimates["material_types"],
            nommo_units=estimates["nommo_units"],
        )
        plate_results.append(pr)
        total_print_seconds += pr.expected_print_seconds
        total_filament_grams += pr.filament_grams_total
        total_nommo_units += pr.nommo_units
    all_warnings.extend(slice_result.get("warnings", []))

    _progress("writing_metadata", {})
    printer_model = opts.printer_profile or ""

    nommo_info = NommoInfo(
        printer_profile=opts.printer_profile or "",
        printer_model=printer_model,
        plate_count=len(plate_results),
        plates=[
            PlateInfo(
                plate_index=p.plate_index,
                expected_print_seconds=p.expected_print_seconds,
                expected_print_hours=p.expected_print_hours,
                filament_grams_total=p.filament_grams_total,
                filament_grams_by_material=p.filament_grams_by_material,
                material_types=p.material_types,
                nommo_units=p.nommo_units,
            ) for p in plate_results
        ],
        total_nommo_units=total_nommo_units,
        warnings=all_warnings,
    )

    write_enriched_3mf(
        input_3mf, output_3mf, nommo_info,
        replace_existing=opts.replace_existing_metadata,
    )

    _progress("complete", {})

    return SliceResult(
        output_path=output_3mf,
        plate_count=len(plate_results),
        plates=plate_results,
        total_nommo_units=total_nommo_units,
        total_print_seconds=total_print_seconds,
        total_filament_grams=total_filament_grams,
        warnings=all_warnings,
        printer_profile=opts.printer_profile or "",
        printer_model=printer_model,
    )
