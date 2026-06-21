"""Load the native _nommo_native shared library."""
import importlib
import os
import sys
from pathlib import Path


def _load_native():
    """Load the compiled _nommo_native extension module."""
    try:
        from nommo_slicer import _nommo_native as native
        return native
    except ImportError:
        pass

    pkg_dir = Path(__file__).parent
    ext = ".cpython-312-darwin.so" if sys.platform == "darwin" else ".so"

    for f in pkg_dir.glob(f"_nommo_native{ext}*"):
        if f.is_file():
            return importlib.import_module(f"nommo_slicer.{f.stem}")

    raise ImportError(
        "Cannot find _nommo_native shared library. "
        "Build it first: cmake --build build"
    )


_native = _load_native()

# Re-export
Model = _native.Model
config = _native.config
gcode = _native.gcode
preset = _native.preset
print = _native.print
DynamicPrintConfig = _native.config.DynamicPrintConfig
PresetBundle = _native.preset.PresetBundle
GCodeProcessor = _native.gcode.GCodeProcessor
