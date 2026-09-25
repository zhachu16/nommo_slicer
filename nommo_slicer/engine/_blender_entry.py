"""
Runs inside Blender's bundled Python (`blender --background --python _blender_entry.py -- ...`).

Loads the creator's transform.py, resolves the requested function and calls
    function(target_file, params)
then reports the outcome to a result JSON file. Standard library only: this file
must not import nommo_slicer, which is not installed in Blender's interpreter.

Argv after "--": <transform.py> <function> <target_file> <params.json> <result.json>
"""
import importlib.util
import json
import os
import sys
import traceback


def _write_result(path, payload):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(argv) != 5:
        print("usage: -- <transform.py> <function> <target_file> <params.json> <result.json>",
              file=sys.stderr)
        sys.exit(2)
    script_path, function_name, target_file, params_path, result_path = argv

    def fail(reason, error, tb=None):
        _write_result(result_path, {"ok": False, "reason": reason, "error": error, "traceback": tb})
        sys.exit(1)

    try:
        with open(params_path, "r", encoding="utf-8") as f:
            params = json.load(f)
    except Exception as e:
        fail("EXCEPTION", f"Could not read params: {e}", traceback.format_exc())

    # Let transform.py import helper modules that sit next to it.
    script_dir = os.path.dirname(os.path.abspath(script_path))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    spec = importlib.util.spec_from_file_location("nommo_user_transform", script_path)
    if spec is None or spec.loader is None:
        fail("LOAD_FAILED", f"Cannot load transform script: {script_path}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except BaseException as e:  # includes a SystemExit raised by creator code
        fail("LOAD_FAILED", f"{type(e).__name__}: {e}", traceback.format_exc())

    if function_name.startswith("_") or not hasattr(module, function_name):
        fail("FUNCTION_NOT_FOUND", f"transform.py has no function '{function_name}'")
    fn = getattr(module, function_name)
    if not callable(fn):
        fail("NOT_CALLABLE", f"transform.py attribute '{function_name}' is not callable")

    try:
        fn(target_file, params)
    except BaseException as e:  # includes a SystemExit raised by creator code
        fail("EXCEPTION", f"{type(e).__name__}: {e}", traceback.format_exc())

    _write_result(result_path, {"ok": True})


if __name__ == "__main__":
    main()
