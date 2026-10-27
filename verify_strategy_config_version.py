"""Verifies the Strategy Config Version Runtime Identity contract."""

from __future__ import annotations

from pathlib import Path

from port_strategy_research.research_version_identity import (
    ResearchVersionIdentityError,
    get_metadata_strategy_config_version,
    get_snapshot_strategy_config_version,
    resolve_strategy_config_identity,
)
from port_strategy_research.strategy_config_snapshot import (
    StrategyConfigSnapshot,
)


def _expect_error(
    expected_marker: str,
    callback,
) -> None:
    try:
        callback()
    except ResearchVersionIdentityError as exc:
        assert expected_marker in str(exc), str(exc)
        return

    raise AssertionError(
        f"EXPECTED_RESEARCH_VERSION_IDENTITY_ERROR={expected_marker}"
    )


def _snapshot(
    *,
    snapshot_version: str = "RSCFG-0001",
    metadata_version: str = "RSCFG-0001",
) -> StrategyConfigSnapshot:
    return StrategyConfigSnapshot(
        strategy_config_version=snapshot_version,
        resolved_config={
            "metadata": {
                "strategy_config_version": metadata_version,
            },
        },
        canonical_json="{}",
        config_hash="0" * 64,
        profile_path=Path(
            f"strategy_profiles/{snapshot_version}.json"
        ),
    )


def main() -> None:
    snapshot = _snapshot()

    assert (
        get_snapshot_strategy_config_version(snapshot)
        == "RSCFG-0001"
    )

    print("STRATEGY_CONFIG_SNAPSHOT_VERSION_SOURCE=SUCCESS")

    assert (
        get_metadata_strategy_config_version(
            snapshot.resolved_config
        )
        == "RSCFG-0001"
    )

    print("STRATEGY_CONFIG_METADATA_VERSION_SOURCE=SUCCESS")

    identity = resolve_strategy_config_identity(snapshot)

    assert identity.snapshot_version == "RSCFG-0001"
    assert identity.metadata_version == "RSCFG-0001"

    print("STRATEGY_CONFIG_SNAPSHOT_METADATA_MATCH=SUCCESS")

    _expect_error(
        "STRATEGY_CONFIG_VERSION_MISMATCH",
        lambda: resolve_strategy_config_identity(
            _snapshot(metadata_version="RSCFG-0002")
        ),
    )

    print("STRATEGY_CONFIG_VERSION_MISMATCH_BLOCKED=SUCCESS")

    _expect_error(
        "STRATEGY_CONFIG_SNAPSHOT_VERSION_FORMAT_INVALID",
        lambda: get_snapshot_strategy_config_version(
            _snapshot(snapshot_version="INVALID")
        ),
    )

    _expect_error(
        "STRATEGY_CONFIG_PROFILE_VERSION_FORMAT_INVALID",
        lambda: get_metadata_strategy_config_version(
            {
                "metadata": {
                    "strategy_config_version": "INVALID",
                },
            }
        ),
    )

    print("STRATEGY_CONFIG_VERSION_FORMAT_VALIDATION=SUCCESS")

    _expect_error(
        "STRATEGY_CONFIG_PROFILE_METADATA_MISSING",
        lambda: get_metadata_strategy_config_version({}),
    )

    _expect_error(
        "STRATEGY_CONFIG_PROFILE_VERSION_MISSING",
        lambda: get_metadata_strategy_config_version(
            {"metadata": {}}
        ),
    )

    print("STRATEGY_CONFIG_METADATA_VALIDATION=SUCCESS")
    print(
        "STRATEGY_CONFIG_VERSION_CANONICAL_SOURCE="
        "StrategyConfigSnapshot.strategy_config_version"
    )
    print("STRATEGY_CONFIG_VERSION_CONTRACT_TEST=SUCCESS")


if __name__ == "__main__":
    main()
