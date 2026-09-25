from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class LimitsConfig:
    max_file_size_bytes: int = 500 * 1024 * 1024       # 500 MB
    max_decompressed_bytes: int = 2 * 1024 * 1024 * 1024  # 2 GB
    max_compressed_ratio: float = 250.0
    max_threads: int = 32
    max_execution_seconds: int = 3600
    max_transform_seconds: int = 600


default_limits = LimitsConfig()
