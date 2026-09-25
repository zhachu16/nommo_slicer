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
    # Optional project inputs (each may be a parsed dict or a path to the JSON file)
    config: dict | Path | None = None               # config.json
    transform_script: Path | None = None            # transform.py
    fingerprint: dict | Path | None = None          # fingerprint.json (may carry runtime credentials)
    blender_path: Path | None = None                # Blender executable used to run transform.py


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
) -> dict:
    """Main entry point: load, optionally transform, slice (or read existing GCode), compute NOMMO units,
    optionally fingerprint, and write the enriched .3mf.

    Returns:
        dict: {"success": true, "output_path": Path, "print_info": dict,
               "transform_function": str | None, "fingerprint": dict | None}
              where print_info is the NommoInfo schema as a JSON-serializable dict, transform_function
              is the transform that was applied (if any) and fingerprint is the embedded
              Metadata/fingerprint.json (if one was requested; never contains credentials).
    """
    import tempfile
    from nommo_slicer.inputs import parse_fingerprint_request, parse_project_config
    from nommo_slicer.metadata.fingerprint import ensure_fingerprint_library, has_embedded_fingerprint
    from nommo_slicer.security.archive_validation import validate_3mf
    from nommo_slicer.security.limits import default_limits

    opts = options or SliceOptions()
    limits = opts.limits or default_limits

    def _progress(stage: str, data: dict):
        if opts.progress_callback:
            opts.progress_callback(stage, data)

    _progress("validating", {})

    # Parse optional inputs up front so bad files fail before any work is done.
    config = parse_project_config(opts.config)
    fingerprint_request = parse_fingerprint_request(opts.fingerprint)
    transform = config.transform if config else None
    warnings: List[str] = []

    if transform and opts.transform_script is None:
        raise NommoSlicerError(
            "INVALID_CONFIG",
            f"config.json requests transform '{transform.function}' but no transform.py was supplied",
        )
    if opts.transform_script is not None and not transform:
        warnings.append("transform.py supplied but config.json requests no transform; geometry unchanged")

    validate_3mf(input_3mf, limits)

    # Never create or register a second fingerprint.
    if fingerprint_request is not None:
        ensure_fingerprint_library()
        if has_embedded_fingerprint(input_3mf):
            raise NommoSlicerError(
                "FINGERPRINT_ALREADY_EXISTS",
                "Input .3mf already contains Metadata/fingerprint.json",
            )

    # The temp dir holds the transform working copy; it is discarded on any failure.
    with tempfile.TemporaryDirectory(dir=opts.temp_dir) as work_dir:
        slice_source = input_3mf
        if transform:
            from nommo_slicer.engine.transform_runner import restore_missing_metadata, run_transform
            import shutil

            _progress("transforming", {"function": transform.function})
            working = Path(work_dir) / "working.3mf"
            shutil.copyfile(input_3mf, working)
            run_transform(
                opts.transform_script, transform, working, Path(work_dir),
                blender_path=opts.blender_path, limits=limits,
            )
            restored = restore_missing_metadata(input_3mf, working)
            if restored:
                logger.info("Restored %d metadata entries dropped by the transform", len(restored))
            slice_source = working

        return _slice_and_write(
            input_3mf, slice_source, output_3mf, opts, limits, _progress,
            transform_function=transform.function if transform else None,
            fingerprint_request=fingerprint_request,
            warnings=warnings,
        )


def _slice_and_write(
    input_3mf: Path,
    slice_source: Path,
    output_3mf: Path,
    opts: SliceOptions,
    limits,
    _progress,
    transform_function: str | None,
    fingerprint_request,
    warnings: List[str],
) -> dict:
    import shutil
    import tempfile
    import zipfile
    # Lazy imports so pure-Python tests can load without the native module
    from nommo_slicer.engine.project_loader import load_project
    from nommo_slicer.engine.profile_resolver import resolve_profiles
    from nommo_slicer.engine.slice_runner import SliceRunner
    from nommo_slicer.engine.estimate_extractor import extract_plate_estimates
    from nommo_slicer.metadata.fingerprint import build_fingerprint
    from nommo_slicer.metadata.nommo_schema import NommoInfo, PlateInfo
    from nommo_slicer.metadata.three_mf_writer import sha256_file, write_enriched_3mf

    cb = opts.progress_callback
    transformed = transform_function is not None

    project = load_project(slice_source, limits)

    _progress("resolving_profiles", {})
    profiles_dir = opts.profiles_dir or Path(__file__).parent / "profiles"
    bundle = resolve_profiles(profiles_dir, project_presets=project.project_presets)

    runner = SliceRunner(progress_callback=cb)
    plate_results: List[PlateResult] = []
    all_warnings: List[str] = list(warnings)
    total_print_seconds = 0.0
    total_filament_grams = 0.0
    total_nommo_units = 0

    plates_to_slice = project.plates
    if opts.plate is not None:
        plates_to_slice = [p for p in plates_to_slice if p.plate_index == opts.plate]
        if not plates_to_slice:
            raise NommoSlicerError("INVALID_3MF", f"Plate {opts.plate} not found")

    with zipfile.ZipFile(slice_source) as zf:
        archive_entries = set(zf.namelist())

    for plate in plates_to_slice:
        # Bambu stores each sliced plate's GCode at Metadata/plate_<N>.gcode (N is 1-based).
        # Embedded GCode describes the pre-transform geometry, so always re-slice after a transform.
        gcode_entry = f"Metadata/plate_{plate.plate_index + 1}.gcode"
        if gcode_entry in archive_entries and not transformed:
            _progress("calculating_estimates", {"plate_index": plate.plate_index})
            with tempfile.TemporaryDirectory(dir=opts.temp_dir) as gcode_dir:
                gcode_path = Path(gcode_dir) / "plate.gcode"
                with zipfile.ZipFile(slice_source) as zf, zf.open(gcode_entry) as src, \
                        open(gcode_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                slice_result = runner.process_existing_gcode(
                    plate.plate_index,
                    gcode_path,
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

    # Created/registered only after slicing succeeds, so a failed slice never leaves an orphan attestation.
    fingerprint = None
    if fingerprint_request is not None:
        _progress("fingerprinting", {"register": fingerprint_request.account_info is not None})
        fingerprint = build_fingerprint(fingerprint_request)

    _progress("writing_metadata", {})
    printer_model = opts.printer_profile or ""

    nommo_info = NommoInfo(
        source_3mf_sha256=sha256_file(input_3mf),
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

    # slice_source is the transformed working copy when a transform ran, so its geometry ships in the output.
    write_enriched_3mf(
        slice_source, output_3mf, nommo_info,
        replace_existing=opts.replace_existing_metadata,
        fingerprint=fingerprint,
        drop_stale_gcode=transformed,
    )

    _progress("complete", {})

    return {
        "success": True,
        "output_path": output_3mf,
        "print_info": nommo_info.to_dict(),
        "transform_function": transform_function,
        "fingerprint": fingerprint,
    }
