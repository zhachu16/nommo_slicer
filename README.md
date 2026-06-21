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

Examples:

```bash
# Basic: slice and enrich
nommo-slicer slice input.3mf -o output.3mf

# Slice a specific plate with JSON output
nommo-slicer slice input.3mf -o output.3mf --plate 0 --json

# Override profiles directory
nommo-slicer slice input.3mf -o output.3mf --profiles-dir /path/to/profiles
```

## Python API

```python
from pathlib import Path
from nommo_slicer import slice_and_enrich, SliceOptions

result = slice_and_enrich(
    Path("input.3mf"),
    Path("output.3mf"),
    SliceOptions(plate=0),
)

print(f"Print time: {result.total_print_seconds:.0f}s")
print(f"Filament: {result.total_filament_grams:.1f}g")
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
