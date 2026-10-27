"""Handles Research Strategy Profile selection, validation, merging, and Snapshot generation."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from port_strategy_research.strategy_config_snapshot import (
    StrategyConfigSnapshot,
    create_strategy_config_snapshot,
)
from port_strategy_research.strategy_profile_schema import (
    resolve_strategy_profile,
)


DEFAULT_STRATEGY_CONFIG_VERSION = "RSCFG-0001"
STRATEGY_CONFIG_VERSION_PATTERN = re.compile(r"^RSCFG-[0-9]{4}$")


def get_strategy_profile_directory() -> Path:
    """Locates the Profile directory in both the Local Source and the Container."""
    module_dir = Path(__file__).resolve().parent
    candidates = [
        module_dir / "strategy_profiles",
        module_dir.parent / "strategy_profiles",
    ]

    for candidate in candidates:
        if candidate.is_dir():
            return candidate

    searched = ", ".join(str(path) for path in candidates)
    raise FileNotFoundError(
        f"STRATEGY_PROFILE_DIRECTORY_NOT_FOUND searched=[{searched}]"
    )


def resolve_strategy_profile_path(
    strategy_config_version: str,
) -> Path:
    """Validates the Version string and returns the corresponding JSON path."""
    if not STRATEGY_CONFIG_VERSION_PATTERN.fullmatch(
        strategy_config_version
    ):
        raise ValueError(
            "INVALID_STRATEGY_CONFIG_VERSION_FORMAT="
            f"{strategy_config_version}"
        )

    profile_dir = get_strategy_profile_directory()
    profile_path = profile_dir / f"{strategy_config_version}.json"

    if not profile_path.is_file():
        raise FileNotFoundError(
            f"STRATEGY_PROFILE_NOT_FOUND={profile_path}"
        )

    return profile_path


def _read_profile(profile_path: Path) -> dict[str, Any]:
    with profile_path.open("r", encoding="utf-8") as file:
        profile = json.load(file)

    if not isinstance(profile, dict):
        raise ValueError("STRATEGY_PROFILE_ROOT_MUST_BE_OBJECT")

    return profile


def load_strategy_profile(
    strategy_config_version: str,
) -> tuple[dict[str, Any], Path]:
    """Reads the Profile JSON, validates its Schema, and returns the original Profile."""
    profile_path = resolve_strategy_profile_path(
        strategy_config_version
    )
    profile = _read_profile(profile_path)

    resolve_strategy_profile(
        profile,
        requested_version=strategy_config_version,
    )

    return profile, profile_path


def load_resolved_strategy_profile(
    strategy_config_version: str,
) -> tuple[dict[str, Any], Path]:
    """Validates the Profile and returns the Config merged with the Common Defaults."""
    profile_path = resolve_strategy_profile_path(
        strategy_config_version
    )
    profile = _read_profile(profile_path)

    resolved = resolve_strategy_profile(
        profile,
        requested_version=strategy_config_version,
    )

    return resolved, profile_path


def load_strategy_config_snapshot(
    strategy_config_version: str,
) -> StrategyConfigSnapshot:
    """Generates the Resolved Config, Canonical JSON, and SHA-256 Hash in one step."""
    resolved_config, profile_path = load_resolved_strategy_profile(
        strategy_config_version
    )

    return create_strategy_config_snapshot(
        resolved_config=resolved_config,
        profile_path=profile_path,
    )
