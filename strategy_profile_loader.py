"""Research Strategy Profile 선택, 검증, 병합과 Snapshot 생성을 담당한다."""

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
    """Local Source와 Container 양쪽에서 Profile 디렉터리를 찾는다."""
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
    """Version 문자열을 검증하고 대응하는 JSON 경로를 반환한다."""
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
    """Profile JSON을 읽고 Schema를 검증한 뒤 원본 Profile을 반환한다."""
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
    """Profile을 검증하고 Common Default와 병합한 Config를 반환한다."""
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
    """Resolved Config, Canonical JSON과 SHA-256 Hash를 한 번에 생성한다."""
    resolved_config, profile_path = load_resolved_strategy_profile(
        strategy_config_version
    )

    return create_strategy_config_snapshot(
        resolved_config=resolved_config,
        profile_path=profile_path,
    )
