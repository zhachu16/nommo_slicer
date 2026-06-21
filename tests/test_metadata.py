"""Tests for the metadata/pricing modules (pure Python, no C++ needed)."""
import json
import tempfile
from pathlib import Path

from nommo_slicer.metadata.nommo_schema import NommoInfo, PlateInfo
from nommo_slicer.metadata.pricing import get_formula
from nommo_slicer.metadata.material_normalizer import normalize_material_type
from nommo_slicer.metadata.three_mf_writer import write_enriched_3mf


class TestPricing:
    def test_v1_formula(self):
        f = get_formula("v1")
        assert f.A == 35.0
        assert f.B == 1.0
        assert f.SETUP_UNITS == 15.0
        assert f.MIN_UNITS == 60.0

    def test_calculate_minimum(self):
        f = get_formula("v1")
        # Very small print: 0.1 hours, 1 gram
        units = f.calculate(0.1, 1.0)
        assert units == 60  # Minimum

    def test_calculate_normal(self):
        f = get_formula("v1")
        # 2 hours, 50 grams: 15 + 35*2 + 1*50 = 135
        units = f.calculate(2.0, 50.0)
        assert units == 135

    def test_calculate_rounding(self):
        f = get_formula("v1")
        units = f.calculate(3.0, 1.5)  # 15 + 35*3 + 1.5 = 121.5 -> round to 122
        assert units == 122


class TestMaterialNormalizer:
    def test_pla_basic(self):
        assert normalize_material_type("PLA Basic", "") == "PLA_BASIC"

    def test_petg(self):
        assert normalize_material_type("PETG", "") == "PETG"

    def test_tpu(self):
        assert normalize_material_type("TPU 95A", "") == "TPU"

    def test_unknown(self):
        assert normalize_material_type("SomeNewMaterial", "") == "SOMENEWMATERIAL"

    def test_fallback_name(self):
        assert normalize_material_type("", "PLA Matte") == "PLA_MATTE"


class TestNommoSchema:
    def test_minimal_plate(self):
        info = NommoInfo(
            source_3mf_sha256="abc123",
            printer_model="X1 Carbon",
            nozzle_size_mm=0.4,
            plate_count=1,
            plates=[
                PlateInfo(
                    plate_index=1,
                    expected_print_seconds=3600,
                    expected_print_hours=1.0,
                    filament_grams_total=50.0,
                    filament_grams_by_material={"PLA_BASIC": 50.0},
                    material_types=["PLA_BASIC"],
                    nommo_units=100,
                )
            ],
            total_nommo_units=100,
        )
        d = info.to_dict()
        assert d["schema_version"] == "1"
        assert d["plates"][0]["nommo_units"] == 100
        assert d["total_nommo_units"] == 100

    def test_roundtrip(self):
        info = NommoInfo(
            plates=[PlateInfo(
                plate_index=1, expected_print_seconds=5400,
                expected_print_hours=1.5, filament_grams_total=85.2,
                filament_grams_by_material={"PLA_BASIC": 85.2},
                material_types=["PLA_BASIC"], nommo_units=153,
            )],
            total_nommo_units=153,
            plate_count=1,
        )
        d = info.to_dict()
        restored = NommoInfo.from_dict(d)
        assert restored.plates[0].nommo_units == 153
        assert restored.total_nommo_units == 153


class TestThreeMfWriter:
    def test_write_enriched(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp = Path(tmp) / "input.3mf"
            out = Path(tmp) / "output.3mf"

            # Create a minimal valid .3mf (it's a zip with [Content_Types].xml)
            import zipfile
            with zipfile.ZipFile(inp, "w") as zf:
                zf.writestr("[Content_Types].xml",
                    '<?xml version="1.0" encoding="utf-8"?>'
                    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                    '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
                    '</Types>')

            info = NommoInfo(
                plate_count=1,
                plates=[PlateInfo(
                    plate_index=1, expected_print_seconds=3600,
                    expected_print_hours=1.0, filament_grams_total=50.0,
                    filament_grams_by_material={"PLA_BASIC": 50.0},
                    material_types=["PLA_BASIC"], nommo_units=100,
                )],
                total_nommo_units=100,
            )

            write_enriched_3mf(inp, out, info)

            # Verify output has the metadata entry
            with zipfile.ZipFile(out, "r") as zf:
                assert "Metadata/nommo_info.json" in zf.namelist()
                assert "[Content_Types].xml" in zf.namelist()
                data = json.loads(zf.read("Metadata/nommo_info.json"))
                assert data["total_nommo_units"] == 100

            # Verify input not modified
            with zipfile.ZipFile(inp, "r") as zf:
                assert "Metadata/nommo_info.json" not in zf.namelist()

    def test_reject_same_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp = Path(tmp) / "test.3mf"
            inp.touch()
            import pytest
            with pytest.raises(ValueError, match="must differ"):
                write_enriched_3mf(inp, inp, NommoInfo(plate_count=0, total_nommo_units=0))
