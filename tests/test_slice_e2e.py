"""End-to-end tests for the slice pipeline.

These tests require the _nommo_native C++ extension to be built.
They use a minimal real .3mf test file."""
import tempfile
from pathlib import Path


class TestSliceE2E:
    """End-to-end slicing tests. These are integration tests that need a built native module."""

    def test_import_native(self):
        """Verify the native module can be imported."""
        try:
            from nommo_slicer import _native
            assert _native is not None
        except ImportError as e:
            import pytest
            pytest.skip(f"Native module not available: {e}")

    def test_load_3mf_minimal(self):
        """Load a minimal .3mf file. Requires a real .3mf test fixture."""
        import pytest
        test_file = Path(__file__).parent / "fixtures" / "minimal.3mf"
        if not test_file.exists():
            pytest.skip(f"Test fixture not found: {test_file}")

        from nommo_slicer import _native
        model, config, plates, presets, is_bbl, version = _native.Model.load_bbs_3mf(str(test_file))
        assert model is not None
        assert config is not None
