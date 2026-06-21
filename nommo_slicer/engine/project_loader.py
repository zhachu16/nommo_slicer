from __future__ import annotations
from pathlib import Path
from typing import List, Optional, Tuple

from nommo_slicer import _native
from nommo_slicer._native import config as native_config
from nommo_slicer.security.archive_validation import validate_3mf
from nommo_slicer.security.limits import LimitsConfig, default_limits


class ProjectLoadResult:
    def __init__(
        self,
        model,
        config,
        plates: List,
        project_presets: List,
        is_bbl_3mf: bool,
    ):
        self.model = model
        self.config = config
        self.plates = plates
        self.project_presets = project_presets
        self.is_bbl_3mf = is_bbl_3mf
        self.has_existing_gcode = any(
            p.gcode_prediction for p in plates
        )


def load_project(
    input_3mf: Path,
    limits: LimitsConfig = default_limits,
) -> ProjectLoadResult:
    """Load a .3mf project file. Returns model, config, plates, and presets."""
    validate_3mf(input_3mf, limits)

    model, config, plates, presets, is_bbl, _ = _native.Model.load_bbs_3mf(
        str(input_3mf)
    )

    return ProjectLoadResult(
        model=model,
        config=config,
        plates=plates,
        project_presets=presets,
        is_bbl_3mf=is_bbl,
    )
