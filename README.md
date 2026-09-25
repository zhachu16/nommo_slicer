# nommo-slicer

Standalone C++ slicing backend extracted from Bambu Studio, wrapped in Python via pybind11.
Reads existing GCode from `.3mf` or re-slices, then enriches with `Metadata/nommo_info.json`.

## Requirements

- macOS (arm64; Intel untested) or Linux
- Python ≥ 3.10
- CMake ≥ 3.15
- Boost ≥ 1.83 (`filesystem`, `thread`, `log`, `locale`, `regex`, `chrono`, `atomic`, `date_time`, `iostreams`, `log_setup`)
- TBB, Eigen3, EXPAT, PNG, Zlib, Freetype, NLopt, OpenCV

On macOS with Homebrew:

```bash
brew install cmake boost tbb eigen expat libpng zlib freetype nlopt opencv
```

## Build

```bash
cd nommo_slicer
mkdir build && cd build
cmake .. -DCMAKE_PREFIX_PATH=$(brew --prefix)
cmake --build . -j$(nproc)
```

The native module is produced at `nommo_slicer/_nommo_native.cpython-*.so`.

## Run tests

```bash
cd nommo_slicer
pip install pytest
PYTHONPATH=. python3 -m pytest tests/ -v
```

## CLI usage

```
nommo-slicer slice <input.3mf> --output <output.3mf> [options]
```

| Flag | Description |
|------|-------------|
| `--output, -o` | Output .3mf path (required) |
| `--profiles-dir` | Override BBL profiles directory |
| `--plate N` | Slice only plate index N |
| `--threads N` | Max threads for slicing |
| `--json` | Machine-readable JSON output |
| `--replace-existing-metadata` | Overwrite existing nommo_info.json |
| `--config` | Optional `config.json` (project configuration) |
| `--transform` | Optional `transform.py` (geometry transform run in Blender before slicing) |
| `--fingerprint` | Optional `fingerprint.json` (create/register a Nommo fingerprint) |
| `--blender` | Blender executable (default: `$NOMMO_BLENDER`, then `blender` on PATH, then `/Applications/Blender.app`) |

Examples:

```bash
# Basic: slice and enrich
nommo-slicer slice input.3mf -o output.3mf

# Slice a specific plate with JSON output
nommo-slicer slice input.3mf -o output.3mf --plate 0 --json

# Override profiles directory
nommo-slicer slice input.3mf -o output.3mf --profiles-dir /path/to/profiles
```

## Optional inputs: config, transform, fingerprint

All three are optional and independent. Without them, slicing behaves exactly as before.

```bash
nommo-slicer slice ring.3mf -o ring_out.3mf \
  --config config.json --transform transform.py --fingerprint fingerprint.json
```

### config.json

Project configuration only. It must not contain fingerprint data or credentials.

```json
{
  "transform": {
    "function": "inner_radius",
    "params": { "radius_mm": 9.1 }
  }
}
```

### transform.py

Creator-defined geometry transforms, run with Blender's Python (`import bpy`) before slicing.
Every callable transform has this signature:

```python
def inner_radius(target_file: str, params: dict) -> None:
    ...  # open target_file, modify geometry with bpy, save back to target_file
```

- `target_file` is a temporary working copy of the input `.3mf`. Modify it in place and save it before returning.
- `params` is `transform.params` from `config.json`.
- Raise an exception on failure. Nothing is sliced, and the working copy is discarded.
- Functions whose names start with `_` are private helpers and can't be selected from `config.json`.

Nommo runs the transform in a separate Blender process:
`blender --background --factory-startup --python nommo_slicer/engine/_blender_entry.py`.
Blender must be installed; see `--blender` / `NOMMO_BLENDER`. The timeout is `LimitsConfig.max_transform_seconds` (600 s by default).

After a transform:
- Any `Metadata/*` entries the export dropped (e.g. Bambu project settings) are copied back from the original. Entries the transform wrote are never overwritten.
- Every plate is re-sliced, and embedded `Metadata/plate_N.gcode` (+ `.md5`) is removed from the output because it no longer matches the geometry.

> **Security:** `transform.py` is arbitrary code. Running it in a subprocess keeps it out of the slicer process, but it is **not** a sandbox. Only run transforms you trust, or sandbox the whole job.

### fingerprint.json

Creates a fingerprint with [`nommo_fingerprint`](../nommo_fingerprint) and embeds it as `Metadata/fingerprint.json`.
Install it with `pip install 'nommo_slicer[fingerprint]'`.

```json
{ "message": "Prototype ring — September 2026" }
```

With `account_info`, the fingerprint is also registered with the Nommo backend (EAS attestation):

```json
{
  "message": "Designed by Alice",
  "account_info": { "email": "alice@example.com", "password": "..." },
  "asset_id": "optional-nommo-asset-uuid"
}
```

- If the input already contains `Metadata/fingerprint.json`, the run fails with `FINGERPRINT_ALREADY_EXISTS`. Nothing is created or registered, and nothing is overwritten.
- The fingerprint is created and registered only after slicing succeeds, so a failed slice never leaves an orphan attestation.
- `account_info` is used at runtime only and is never written to the `.3mf`.

### Error codes

| Code | CLI exit |
|---|---|
| `INVALID_CONFIG` | 60 |
| `TRANSFORM_FAILED` (`details.reason`: `BLENDER_NOT_FOUND`, `LOAD_FAILED`, `FUNCTION_NOT_FOUND`, `NOT_CALLABLE`, `EXCEPTION`, `TIMEOUT`, `NO_RESULT`, `INVALID_OUTPUT`) | 61 |
| `INVALID_FINGERPRINT_REQUEST` | 70 |
| `FINGERPRINT_ALREADY_EXISTS` | 71 |
| `FINGERPRINT_FAILED` (`details.fingerprint_code` holds the `nommo_fingerprint` code) | 72 |
| `FINGERPRINT_UNAVAILABLE` (library not installed) | 73 |

## Python API

```python
from pathlib import Path
from nommo_slicer import slice_and_enrich, SliceOptions

result = slice_and_enrich(
    Path("input.3mf"),
    Path("output.3mf"),
    SliceOptions(plate=0),
)

print(result["success"])  # True
print(result["output_path"])  # Path("output.3mf")

print_info = result["print_info"]
print(f"Plates: {print_info['plate_count']}")
for p in print_info["plates"]:
    print(f"  Plate {p['plate_index']}: {p['expected_print_seconds']:.0f}s, {p['filament_grams_total']:.1f}g")
print(f"Total NOMMO units: {print_info['total_nommo_units']}")

# Optional inputs accept a dict or a path to the JSON file
result = slice_and_enrich(
    Path("ring.3mf"),
    Path("ring_out.3mf"),
    SliceOptions(
        config={"transform": {"function": "inner_radius", "params": {"radius_mm": 9.1}}},
        transform_script=Path("transform.py"),
        fingerprint={"message": "Prototype ring"},
    ),
)
print(result["transform_function"])  # "inner_radius"
print(result["fingerprint"])         # the embedded Metadata/fingerprint.json
```

### Output format

`slice_and_enrich` returns a dict:

```python
{
    "success": True,
    "output_path": Path("output.3mf"),
    "print_info": {
        # NommoInfo schema — JSON-serializable
        "schema_version": "1",
        "slicer": "NOMMO-Bambu",
        "slicer_version": "0.2.1",
        "printer_profile": "...",
        "printer_model": "...",
        "nozzle_size_mm": 0.4,
        "plate_count": 3,
        "plates": [
            {
                "plate_index": 0,
                "expected_print_seconds": 1234.5,
                "expected_print_hours": 0.34,
                "filament_grams_total": 12.3,
                "filament_grams_by_material": {"PLA_BASIC": 12.3},
                "material_types": ["PLA_BASIC"],
                "nommo_units": 60,
            },
            # ... more plates
        ],
        "total_nommo_units": 180,
        "warnings": [],
    },
    # New in 0.2.1; None unless requested
    "transform_function": "inner_radius",
    "fingerprint": {"spec": "nommo_fingerprint", "version": 1, "message": "..."},
}
```

## Project structure

```
nommo_slicer/
├── CMakeLists.txt              # Standalone CMake build
├── version.inc                 # Version macros (vendored)
├── pyproject.toml              # Python packaging
├── src/
│   ├── libslic3r/              # Core C++ slicer library (vendored from BambuStudio)
│   ├── admesh/ clipper/ eigen/ libigl/ qhull/ ...  # Bundled third-party deps
│   ├── bindings/               # pybind11 C++ → Python bindings
│   └── stubs/                  # Stubs for excluded subsystems
├── nommo_slicer/
│   ├── __init__.py             # slice_and_enrich + data classes
│   ├── _native.py              # Native module wrapper
│   ├── engine/                 # Slicing pipeline
│   ├── metadata/               # nommo_info schema + 3MF writer
│   ├── security/               # Resource limits
│   ├── profiles/BBL/           # Bambu printer/filament/process profiles
│   └── cli/main.py             # CLI entry point
└── tests/
    ├── fixtures/minimal.3mf    # E2E test fixture
    ├── test_slice_e2e.py
    ├── test_metadata.py
    ├── test_cli.py
    └── test_archive_validation.py
```
