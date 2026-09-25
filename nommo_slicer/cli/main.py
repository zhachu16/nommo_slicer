from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

from nommo_slicer import slice_and_enrich, SliceOptions, NommoSlicerError


EXIT_CODES = {
    "INVALID_3MF": 10,
    "UNSUPPORTED_3MF": 11,
    "PROFILE_NOT_FOUND": 20,
    "UNSUPPORTED_PRINTER": 21,
    "UNSUPPORTED_MATERIAL": 22,
    "SLICE_FAILED": 30,
    "RESOURCE_LIMIT_EXCEEDED": 40,
    "OUTPUT_WRITE_FAILED": 50,
    "INVALID_CONFIG": 60,
    "TRANSFORM_FAILED": 61,
    "INVALID_FINGERPRINT_REQUEST": 70,
    "FINGERPRINT_ALREADY_EXISTS": 71,
    "FINGERPRINT_FAILED": 72,
    "FINGERPRINT_UNAVAILABLE": 73,
}


def _progress_printer(stage: str, data: dict):
    msg = f"[{stage}]"
    if "plate_index" in data and data["plate_index"] >= 0:
        msg += f" plate={data['plate_index']}"
    print(msg, file=sys.stderr, flush=True)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="nommo-slicer", description="NOMMO Slicing Library CLI")
    sub = p.add_subparsers(dest="command", required=True)

    slice_p = sub.add_parser("slice", help="Slice a .3mf project")
    slice_p.add_argument("input_3mf", type=Path, help="Input .3mf file")
    slice_p.add_argument("--output", "-o", type=Path, required=True, help="Output .3mf file")
    slice_p.add_argument("--profiles-dir", type=Path, default=None, help="Profiles directory")
    slice_p.add_argument("--printer-profile", type=str, default=None, help="Override printer profile")
    slice_p.add_argument("--process-profile", type=str, default=None, help="Override process profile")
    slice_p.add_argument("--filament-profile", type=str, default=None, help="Override filament profile")
    slice_p.add_argument("--plate", type=int, default=None, help="Slice only this plate index")
    slice_p.add_argument("--threads", type=int, default=None, help="Max threads")
    slice_p.add_argument("--temp-dir", type=Path, default=None, help="Temporary directory")
    slice_p.add_argument("--replace-existing-metadata", action="store_true", help="Replace existing nommo_info.json")
    slice_p.add_argument("--json", action="store_true", help="Output JSON (machine-readable)")
    slice_p.add_argument("--config", type=Path, default=None, help="Project config.json")
    slice_p.add_argument("--transform", type=Path, default=None, help="Creator transform.py (run in Blender)")
    slice_p.add_argument("--fingerprint", type=Path, default=None, help="fingerprint.json request")
    slice_p.add_argument("--blender", type=Path, default=None, help="Blender executable (default: $NOMMO_BLENDER or PATH)")

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "slice":
        _cmd_slice(args)
    else:
        parser.print_help()
        sys.exit(1)


def _cmd_slice(args):
    opts = SliceOptions(
        profiles_dir=args.profiles_dir,
        printer_profile=args.printer_profile,
        process_profile=args.process_profile,
        filament_profile=args.filament_profile,
        plate=args.plate,
        threads=args.threads,
        temp_dir=args.temp_dir,
        replace_existing_metadata=args.replace_existing_metadata,
        progress_callback=_progress_printer if not args.json else None,
        config=args.config,
        transform_script=args.transform,
        fingerprint=args.fingerprint,
        blender_path=args.blender,
    )

    try:
        result = slice_and_enrich(args.input_3mf, args.output, opts)
    except NommoSlicerError as e:
        print(f"Error [{e.code}]: {e.message}", file=sys.stderr)
        if e.details.get("traceback"):
            print(e.details["traceback"], file=sys.stderr)
        elif e.details.get("stderr"):
            print(e.details["stderr"], file=sys.stderr)
        sys.exit(EXIT_CODES.get(e.code, 1))
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

    print_info = result["print_info"]
    total_seconds = sum(p["expected_print_seconds"] for p in print_info["plates"])
    total_filament = sum(p["filament_grams_total"] for p in print_info["plates"])

    if args.json:
        out = {
            "status": "complete",
            "output_path": str(result["output_path"]),
            "plate_count": print_info["plate_count"],
            "total_print_seconds": total_seconds,
            "total_filament_grams": total_filament,
            "total_nommo_units": print_info["total_nommo_units"],
            "warnings": print_info["warnings"],
            "transform_function": result["transform_function"],
            "fingerprint": result["fingerprint"],
        }
        print(json.dumps(out, indent=2))
    else:
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        print(f"Processed: {args.input_3mf}")
        print(f"Output: {result['output_path']}")
        print(f"Plates: {print_info['plate_count']}")
        print(f"Estimated time: {hours:02d}:{minutes:02d}:{seconds:02d}")
        print(f"Filament: {total_filament:.1f} g")
        print(f"NOMMO units: {print_info['total_nommo_units']}")
        if result["transform_function"]:
            print(f"Transform: {result['transform_function']}")
        if result["fingerprint"]:
            registered = "eas_attestation_uid" in result["fingerprint"]
            print(f"Fingerprint: {'registered' if registered else 'local'}")


if __name__ == "__main__":
    main()
