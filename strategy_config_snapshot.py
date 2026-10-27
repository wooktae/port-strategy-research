"""Generates the Resolved Strategy Config Snapshot, Canonical JSON, and SHA-256 evidence."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence


SECRET_KEY_FRAGMENTS = (
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "access_key",
    "private_key",
    "client_secret",
    "credential",
    "webhook",
)

SECRET_VALUE_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)^aws_secret_access_key="),
    re.compile(r"(?i)^bearer\s+[A-Za-z0-9._~+/=-]+$"),
    re.compile(r"(?i)^postgres(?:ql)?://[^/\s:]+:[^@\s]+@"),
)


class StrategyConfigSecretError(ValueError):
    """A Secret candidate was found within the Resolved Config."""


@dataclass(frozen=True)
class StrategyConfigSnapshot:
    """Immutable Config evidence to be used for execution."""

    strategy_config_version: str
    resolved_config: dict[str, Any]
    canonical_json: str
    config_hash: str
    profile_path: Path


def _canonicalize(value: Any) -> Any:
    """Converts to a deterministic, JSON-serializable representation."""
    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, Mapping):
        return {
            str(key): _canonicalize(item)
            for key, item in sorted(
                value.items(),
                key=lambda pair: str(pair[0]),
            )
        }

    if isinstance(value, tuple):
        return [_canonicalize(item) for item in value]

    if isinstance(value, list):
        return [_canonicalize(item) for item in value]

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    raise TypeError(
        "STRATEGY_CONFIG_UNSUPPORTED_CANONICAL_TYPE="
        f"{type(value).__name__}"
    )


def to_canonical_json(resolved_config: Mapping[str, Any]) -> str:
    """Builds Canonical JSON using sorted Keys and fixed separators."""
    canonical_value = _canonicalize(resolved_config)

    return json.dumps(
        canonical_value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def calculate_config_hash(canonical_json: str) -> str:
    """Returns the SHA-256 Hex Digest of the Canonical UTF-8 JSON."""
    return hashlib.sha256(
        canonical_json.encode("utf-8")
    ).hexdigest()


def _looks_like_secret_key(key: str) -> bool:
    normalized = key.strip().lower().replace("-", "_")

    return any(
        fragment in normalized
        for fragment in SECRET_KEY_FRAGMENTS
    )


def _looks_like_secret_value(value: str) -> bool:
    stripped = value.strip()

    return any(
        pattern.search(stripped)
        for pattern in SECRET_VALUE_PATTERNS
    )


def find_secret_candidates(
    value: Any,
    *,
    path: str = "$",
) -> list[str]:
    """Collects Secret candidate paths using Key names and a limited set of value Patterns."""
    findings: list[str] = []

    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}"

            if _looks_like_secret_key(key_text):
                findings.append(
                    f"{child_path}:forbidden-key"
                )

            findings.extend(
                find_secret_candidates(
                    item,
                    path=child_path,
                )
            )

        return findings

    if isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray),
    ):
        for index, item in enumerate(value):
            findings.extend(
                find_secret_candidates(
                    item,
                    path=f"{path}[{index}]",
                )
            )

        return findings

    if isinstance(value, str) and _looks_like_secret_value(value):
        findings.append(f"{path}:suspicious-value")

    return findings


def assert_no_secrets(resolved_config: Mapping[str, Any]) -> None:
    """Blocks execution if the Resolved Config contains a Secret candidate."""
    findings = find_secret_candidates(resolved_config)

    if findings:
        raise StrategyConfigSecretError(
            "STRATEGY_CONFIG_SECRET_CANDIDATE="
            + ",".join(findings)
        )


def create_strategy_config_snapshot(
    *,
    resolved_config: dict[str, Any],
    profile_path: Path,
) -> StrategyConfigSnapshot:
    """Creates an immutable Snapshot and Hash from a validated Resolved Config."""
    assert_no_secrets(resolved_config)

    metadata = resolved_config.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("RESOLVED_CONFIG_METADATA_MISSING")

    strategy_config_version = metadata.get(
        "strategy_config_version"
    )
    if not isinstance(strategy_config_version, str):
        raise ValueError(
            "RESOLVED_CONFIG_STRATEGY_VERSION_MISSING"
        )

    canonical_json = to_canonical_json(resolved_config)
    config_hash = calculate_config_hash(canonical_json)

    return StrategyConfigSnapshot(
        strategy_config_version=strategy_config_version,
        resolved_config=resolved_config,
        canonical_json=canonical_json,
        config_hash=config_hash,
        profile_path=profile_path,
    )
