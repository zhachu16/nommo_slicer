from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path

from nommo_slicer import NommoSlicerError


# config.json holds project configuration only; these belong in fingerprint.json
# or must never be persisted at all.
FORBIDDEN_CONFIG_KEYS = {"fingerprint", "account_info", "email", "password", "asset_id"}
FINGERPRINT_REQUEST_KEYS = {"message", "account_info", "asset_id"}


@dataclass
class TransformSpec:
    function: str
    params: dict = field(default_factory=dict)


@dataclass
class ProjectConfig:
    transform: TransformSpec | None = None
    raw: dict = field(default_factory=dict)


@dataclass
class FingerprintRequest:
    message: str | None = None
    # Runtime-only credentials: kept out of repr so they never reach logs or tracebacks.
    account_info: dict | None = field(default=None, repr=False)
    asset_id: str | None = None


def load_json_input(value: dict | Path | str, error_code: str, label: str) -> dict:
    """Accept an already-parsed dict or a path to a JSON file; always return a dict."""
    if isinstance(value, dict):
        return value
    path = Path(value)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise NommoSlicerError(error_code, f"{label} not found: {path}")
    except (OSError, json.JSONDecodeError) as e:
        raise NommoSlicerError(error_code, f"Could not read {label} ({path}): {e}")
    if not isinstance(data, dict):
        raise NommoSlicerError(error_code, f"{label} must contain a JSON object")
    return data


def parse_project_config(value: dict | Path | str | None) -> ProjectConfig | None:
    if value is None:
        return None
    data = load_json_input(value, "INVALID_CONFIG", "config.json")

    forbidden = FORBIDDEN_CONFIG_KEYS & data.keys()
    if forbidden:
        raise NommoSlicerError(
            "INVALID_CONFIG",
            "config.json must not contain fingerprint or credential fields: "
            + ", ".join(sorted(forbidden)),
        )

    transform = None
    if "transform" in data and data["transform"] is not None:
        transform = _parse_transform(data["transform"])

    return ProjectConfig(transform=transform, raw=data)


def _parse_transform(t) -> TransformSpec:
    if not isinstance(t, dict):
        raise NommoSlicerError("INVALID_CONFIG", "config.json 'transform' must be an object")

    function = t.get("function")
    if not isinstance(function, str) or not function.isidentifier():
        raise NommoSlicerError(
            "INVALID_CONFIG", "config.json 'transform.function' must be a function name"
        )
    if function.startswith("_"):
        raise NommoSlicerError(
            "INVALID_CONFIG",
            f"config.json 'transform.function' cannot name a private function: {function}",
        )

    params = t.get("params", {})
    if params is None:
        params = {}
    if not isinstance(params, dict):
        raise NommoSlicerError("INVALID_CONFIG", "config.json 'transform.params' must be an object")
    try:
        json.dumps(params)
    except (TypeError, ValueError) as e:
        raise NommoSlicerError(
            "INVALID_CONFIG", f"config.json 'transform.params' must be JSON-compatible: {e}"
        )

    return TransformSpec(function=function, params=params)


def parse_fingerprint_request(value: dict | Path | str | None) -> FingerprintRequest | None:
    if value is None:
        return None
    data = load_json_input(value, "INVALID_FINGERPRINT_REQUEST", "fingerprint.json")

    unknown = data.keys() - FINGERPRINT_REQUEST_KEYS
    if unknown:
        raise NommoSlicerError(
            "INVALID_FINGERPRINT_REQUEST",
            "Unknown fields in fingerprint.json: " + ", ".join(sorted(unknown)),
        )

    message = data.get("message")
    if message is not None and not isinstance(message, str):
        raise NommoSlicerError("INVALID_FINGERPRINT_REQUEST", "'message' must be a string")

    account_info = data.get("account_info")
    if account_info is not None and not isinstance(account_info, dict):
        # Deliberately does not echo the value back.
        raise NommoSlicerError("INVALID_FINGERPRINT_REQUEST", "'account_info' must be an object")

    asset_id = data.get("asset_id")
    if asset_id is not None and not isinstance(asset_id, str):
        raise NommoSlicerError("INVALID_FINGERPRINT_REQUEST", "'asset_id' must be a string")

    return FingerprintRequest(message=message, account_info=account_info, asset_id=asset_id)
