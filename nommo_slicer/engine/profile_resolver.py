from __future__ import annotations
from pathlib import Path
from typing import Optional

from nommo_slicer import _native
from nommo_slicer._native import preset as native_preset


def resolve_profiles(
    profiles_dir: Path,
    vendor_name: str = "BBL",
    project_presets: Optional[list] = None,
) -> native_preset.PresetBundle:
    """Load system profiles and optionally merge project-embedded presets."""
    bundle = native_preset.PresetBundle()

    bundle.load_vendor_configs(str(profiles_dir), vendor_name)

    if project_presets:
        bundle.load_project_embedded_presets(project_presets)

    return bundle
