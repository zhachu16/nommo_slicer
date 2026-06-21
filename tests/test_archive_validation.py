"""Tests for archive validation (pure Python)."""
import tempfile
import zipfile
from pathlib import Path

import pytest
from nommo_slicer.security.archive_validation import validate_3mf, ArchiveValidationError


class TestArchiveValidation:
    def test_valid_minimal_3mf(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "valid.3mf"
            with zipfile.ZipFile(path, "w") as zf:
                zf.writestr("[Content_Types].xml", "dummy")
            validate_3mf(path)

    def test_missing_content_types(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.3mf"
            with zipfile.ZipFile(path, "w") as zf:
                zf.writestr("some/entry", "data")
            with pytest.raises(ArchiveValidationError, match="Content_Types"):
                validate_3mf(path)

    def test_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "traversal.3mf"
            with zipfile.ZipFile(path, "w") as zf:
                zf.writestr("../../etc/passwd", "data")
                zf.writestr("[Content_Types].xml", "dummy")
            with pytest.raises(ArchiveValidationError, match="traversal"):
                validate_3mf(path)

    def test_file_not_found(self):
        with pytest.raises(ArchiveValidationError, match="not found"):
            validate_3mf(Path("/nonexistent/file.3mf"))

    def test_not_a_zip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "notazip.3mf"
            path.write_text("not a zip file")
            with pytest.raises(ArchiveValidationError, match="ZIP"):
                validate_3mf(path)
