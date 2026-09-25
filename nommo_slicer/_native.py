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


def _load_native_quietly():
    """Load the extension with fd 1 pointed at stderr.

    libslic3r logs a trace line from a static initializer, before the module can install its
    stderr log sink, and boost.log's default sink writes to stdout. stdout belongs to the host
    process (e.g. `nommo-slicer --json`), so keep native load-time output off it.
    """
    try:
        sys.stdout.flush()
        saved_stdout = os.dup(1)
    except (AttributeError, OSError, ValueError):
        return _load_native()  # no real fd 1 (e.g. embedded interpreter)
    try:
        os.dup2(2, 1)
        return _load_native()
    finally:
        os.dup2(saved_stdout, 1)
        os.close(saved_stdout)


_native = _load_native_quietly()

# Re-export
Model = _native.Model
config = _native.config
gcode = _native.gcode
preset = _native.preset
print = _native.print
DynamicPrintConfig = _native.config.DynamicPrintConfig
PresetBundle = _native.preset.PresetBundle
GCodeProcessor = _native.gcode.GCodeProcessor
