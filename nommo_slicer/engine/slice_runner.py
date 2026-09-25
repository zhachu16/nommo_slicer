from __future__ import annotations
import logging
import tempfile
from pathlib import Path
from typing import Callable, Optional

from nommo_slicer import _native
from nommo_slicer._native import print as native_print

logger = logging.getLogger(__name__)


ProgressCallback = Callable[[str, dict], None]

STAGES = [
    "validating",
    "transforming",
    "loading_project",
    "resolving_profiles",
    "slicing_plate",
    "calculating_estimates",
    "fingerprinting",
    "writing_metadata",
    "complete",
]


def _make_progress_cb(user_cb: Optional[ProgressCallback], plate_index: int):
    def cb(stage: str, current: int, total: int):
        if user_cb:
            user_cb(stage, {"plate_index": plate_index, "current": current, "total": total})
    return cb


def _dhms_to_seconds(value: str) -> float:
    """Parse libslic3r get_time_dhms strings like '1h 2m 3s'."""
    total = 0.0
    for part in value.split():
        if part.endswith("d"):
            total += float(part[:-1]) * 86400
        elif part.endswith("h"):
            total += float(part[:-1]) * 3600
        elif part.endswith("m"):
            total += float(part[:-1]) * 60
        elif part.endswith("s") and part != "<1s":
            total += float(part[:-1])
    return total


class SliceRunner:
    def __init__(self, progress_callback: Optional[ProgressCallback] = None):
        self.progress_callback = progress_callback
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run_plate(
        self,
        plate_index: int,
        model,
        config,
        is_bbl: bool = False,
        temp_dir: Path | None = None,
        plate_data=None,
    ) -> dict:
        """Slice a single plate. Returns dict with time, filament, and warnings."""
        if self.progress_callback:
            self.progress_callback("slicing_plate", {"plate_index": plate_index})

        if plate_data is not None:
            model.prepare_for_plate(plate_data)

        print_job = native_print.Print()
        print_job.set_plate_index(plate_index)
        # Shift from global 3MF coordinates to plate-local coordinates
        if hasattr(model, "compute_plate_origin"):
            ox, oy, oz = model.compute_plate_origin()
            print_job.set_plate_origin(ox, oy, oz)
        print_job.apply_config(model, config)
        print_job.set_bbl_printer(bool(is_bbl))
        print_job.process()
        with tempfile.TemporaryDirectory(dir=temp_dir) as work_dir:
            gcode_path = Path(work_dir) / f"plate_{plate_index}.gcode"
            gcode_estimates = print_job.export_gcode_estimates(str(gcode_path))

        stats = print_job.print_statistics()
        total_time = float(gcode_estimates["total_time_seconds"])
        prepare_time = float(gcode_estimates["prepare_time_seconds"])
        print_time = float(
            gcode_estimates["model_time_seconds"] if is_bbl else total_time
        )

        return {
            "plate_index": plate_index,
            "print_time_seconds": print_time,
            "print_time_hours": print_time / 3600.0,
            "total_time_seconds": total_time,
            "prepare_time_seconds": prepare_time,
            "filament_weight_g": stats.total_weight,
            "filament_volume_mm3": stats.total_extruded_volume,
            "warnings": [],
            "print_statistics": stats,
            "gcode_statistics": gcode_estimates,
        }

    def process_existing_gcode(
        self,
        plate_index: int,
        gcode_path: Path,
        config,
        is_bbl: bool = False,
    ) -> dict:
        """Parse a plate's embedded GCode file and extract time/filament estimates (fast path)."""
        if self.progress_callback:
            self.progress_callback("calculating_estimates", {"plate_index": plate_index})

        result = _native.gcode.estimate_from_gcode_file(str(gcode_path))

        total_time = result.time_by_mode(_native.gcode.ETimeMode.NORMAL)
        prepare_time = result.prepare_time_by_mode(_native.gcode.ETimeMode.NORMAL)
        print_time = (
            result.model_time_by_mode(_native.gcode.ETimeMode.NORMAL)
            if is_bbl
            else total_time
        )
        volumes = dict(result.total_volumes_per_extruder)
        weight, warnings = _weight_from_volumes(volumes, config)
        return {
            "plate_index": plate_index,
            "print_time_seconds": print_time,
            "print_time_hours": print_time / 3600.0,
            "total_time_seconds": total_time,
            "prepare_time_seconds": prepare_time,
            "filament_weight_g": weight,
            "filament_volume_mm3": sum(volumes.values()),
            "warnings": warnings,
            "print_statistics": result,
        }


def _weight_from_volumes(volumes: dict, config) -> tuple[float, list]:
    """Grams from per-filament extruded volume (mm^3) and the project's filament_density (g/cm^3)."""
    try:
        densities = list(config.get_floats("filament_density"))
    except Exception:
        densities = []
    grams = 0.0
    missing = []
    for filament_idx, volume_mm3 in volumes.items():
        density = densities[filament_idx] if 0 <= filament_idx < len(densities) else 0.0
        if density <= 0:
            missing.append(filament_idx)
        grams += volume_mm3 / 1000.0 * density
    warnings = []
    if missing and any(volumes[i] > 0 for i in missing):
        warnings.append(f"filament_density missing for filament(s) {missing}; weight excludes them")
    return grams, warnings
