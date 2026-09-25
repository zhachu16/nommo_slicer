from __future__ import annotations
import json
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED, BadZipFile

from nommo_slicer import NommoSlicerError
from nommo_slicer.inputs import TransformSpec
from nommo_slicer.metadata.three_mf_writer import STALE_GCODE_RE
from nommo_slicer.security.limits import LimitsConfig, default_limits

logger = logging.getLogger(__name__)

ENTRY_SCRIPT = Path(__file__).with_name("_blender_entry.py")
MACOS_BLENDER = Path("/Applications/Blender.app/Contents/MacOS/Blender")
STDERR_TAIL_CHARS = 4000


def find_blender(blender_path: Path | None = None) -> Path:
    """Resolve the Blender executable: explicit path, $NOMMO_BLENDER, PATH, then the macOS app bundle."""
    candidates = []
    if blender_path:
        candidates.append(Path(blender_path))
    if os.environ.get("NOMMO_BLENDER"):
        candidates.append(Path(os.environ["NOMMO_BLENDER"]))
    on_path = shutil.which("blender")
    if on_path:
        candidates.append(Path(on_path))
    candidates.append(MACOS_BLENDER)

    for c in candidates:
        if c.is_file() and os.access(c, os.X_OK):
            return c

    raise NommoSlicerError(
        "TRANSFORM_FAILED",
        "Blender executable not found; pass --blender or set NOMMO_BLENDER",
        {"reason": "BLENDER_NOT_FOUND"},
    )


def run_transform(
    script: Path,
    spec: TransformSpec,
    target_file: Path,
    work_dir: Path,
    blender_path: Path | None = None,
    limits: LimitsConfig = default_limits,
) -> None:
    """Run spec.function(target_file, spec.params) from the creator's transform.py inside Blender.

    target_file is modified in place. Raises NommoSlicerError("TRANSFORM_FAILED") on any failure;
    the caller is responsible for discarding target_file in that case.
    """
    script = Path(script)
    if not script.is_file():
        raise NommoSlicerError(
            "TRANSFORM_FAILED", f"transform.py not found: {script}", {"reason": "LOAD_FAILED"}
        )

    blender = find_blender(blender_path)

    params_path = work_dir / "transform_params.json"
    result_path = work_dir / "transform_result.json"
    params_path.write_text(json.dumps(spec.params), encoding="utf-8")
    if result_path.exists():
        result_path.unlink()

    cmd = [
        str(blender), "--background", "--factory-startup", "--python-exit-code", "1",
        "--python", str(ENTRY_SCRIPT), "--",
        str(script.resolve()), spec.function, str(target_file), str(params_path), str(result_path),
    ]
    logger.info("Running transform %s via %s", spec.function, blender)

    try:
        proc = subprocess.run(
            cmd, cwd=work_dir, capture_output=True, text=True,
            timeout=limits.max_transform_seconds,
        )
    except subprocess.TimeoutExpired:
        raise NommoSlicerError(
            "TRANSFORM_FAILED",
            f"Transform '{spec.function}' exceeded {limits.max_transform_seconds}s",
            {"reason": "TIMEOUT", "function": spec.function},
        )

    result = None
    if result_path.exists():
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            result = None

    if result is None:
        raise NommoSlicerError(
            "TRANSFORM_FAILED",
            f"Transform '{spec.function}' did not report a result (Blender exit code {proc.returncode})",
            {"reason": "NO_RESULT", "function": spec.function,
             "stderr": (proc.stderr or "")[-STDERR_TAIL_CHARS:]},
        )

    if not result.get("ok"):
        raise NommoSlicerError(
            "TRANSFORM_FAILED",
            f"Transform '{spec.function}' failed: {result.get('error')}",
            {"reason": result.get("reason", "EXCEPTION"), "function": spec.function,
             "traceback": result.get("traceback")},
        )

    if not target_file.is_file():
        raise NommoSlicerError(
            "TRANSFORM_FAILED",
            f"Transform '{spec.function}' removed the working file",
            {"reason": "INVALID_OUTPUT", "function": spec.function},
        )


def restore_missing_metadata(original: Path, working: Path) -> list[str]:
    """Copy Metadata/* entries that exist in `original` but not in `working` back into `working`.

    Blender's 3MF export usually drops Bambu project metadata. Entries the transform wrote are
    never overwritten, and embedded GCode (stale after a transform) is not restored.
    Returns the restored entry names.
    """
    try:
        with ZipFile(original, "r") as src, ZipFile(working, "r") as wk:
            present = set(wk.namelist())
            missing = [
                i for i in src.infolist()
                if i.filename.startswith("Metadata/")
                and i.filename not in present
                and not STALE_GCODE_RE.match(i.filename)
            ]
    except BadZipFile:
        raise NommoSlicerError(
            "TRANSFORM_FAILED",
            "Transform did not leave a valid .3mf archive",
            {"reason": "INVALID_OUTPUT"},
        )

    if not missing:
        return []

    fd, tmp_path = tempfile.mkstemp(suffix=".3mf", dir=working.parent)
    os.close(fd)
    try:
        with ZipFile(original, "r") as src, ZipFile(working, "r") as wk, \
                ZipFile(tmp_path, "w", ZIP_DEFLATED) as dst:
            for item in wk.infolist():
                dst.writestr(item, wk.read(item.filename))
            for item in missing:
                dst.writestr(item, src.read(item.filename))
        os.replace(tmp_path, working)
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    return [i.filename for i in missing]
