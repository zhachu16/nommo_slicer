from __future__ import annotations
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from nommo_slicer.metadata.nommo_schema import NommoInfo


NONMO_ENTRY = "Metadata/nommo_info.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def write_enriched_3mf(
    input_path: Path,
    output_path: Path,
    nommo_info: NommoInfo,
    replace_existing: bool = False,
) -> None:
    """
    Copy input .3mf, insert/replace Metadata/nommo_info.json.
    Uses atomic write via temp file + rename.
    """
    if input_path == output_path:
        raise ValueError("Input and output paths must differ")

    nommo_info.source_3mf_sha256 = sha256_file(input_path)

    fd, tmp_path = tempfile.mkstemp(suffix=".3mf")
    os.close(fd)

    try:
        with ZipFile(input_path, "r") as src, ZipFile(tmp_path, "w", ZIP_DEFLATED) as dst:
            for item in src.infolist():
                # Skip existing nommo_info.json unless replace_existing
                if item.filename == NONMO_ENTRY and not replace_existing:
                    continue
                dst.writestr(item, src.read(item.filename))

            # Write new nommo_info.json
            data = json.dumps(nommo_info.to_dict(), indent=2, ensure_ascii=False)
            dst.writestr(NONMO_ENTRY, data)

        os.replace(tmp_path, output_path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
