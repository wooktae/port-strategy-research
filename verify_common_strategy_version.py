"""Verifies the Common Strategy Version Runtime Identity contract."""

from __future__ import annotations

from unittest.mock import patch

from port_strategy_research.research_version_identity import (
    ResearchVersionIdentityError,
    get_declared_common_strategy_version,
    get_runtime_common_strategy_version,
    resolve_common_strategy_identity,
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


def main() -> None:
    resolved_config = {
        "metadata": {
            "common_strategy_version": (
                "COMMON_STRATEGY_V1.0.0"
            ),
        },
    }

    with patch(
        "port_strategy_research.research_version_identity."
        "COMMON_STRATEGY_VERSION",
        "COMMON_STRATEGY_V1.0.0",
    ):
        runtime_version = get_runtime_common_strategy_version()

    assert runtime_version == "COMMON_STRATEGY_V1.0.0"

    print("COMMON_STRATEGY_RUNTIME_CONSTANT_SOURCE=SUCCESS")

    declared_version = get_declared_common_strategy_version(
        resolved_config
    )
    assert declared_version == "COMMON_STRATEGY_V1.0.0"

    print("COMMON_STRATEGY_PROFILE_DECLARATION_SOURCE=SUCCESS")

    with patch(
        "port_strategy_research.research_version_identity."
        "COMMON_STRATEGY_VERSION",
        "COMMON_STRATEGY_V1.0.0",
    ):
        identity = resolve_common_strategy_identity(
            resolved_config
        )

    assert (
        identity.declared_version
        == "COMMON_STRATEGY_V1.0.0"
    )
    assert (
        identity.runtime_version
        == "COMMON_STRATEGY_V1.0.0"
    )

    print("COMMON_STRATEGY_DECLARED_RUNTIME_MATCH=SUCCESS")

    with patch(
        "port_strategy_research.research_version_identity."
        "COMMON_STRATEGY_VERSION",
        "COMMON_STRATEGY_V1.0.1",
    ):
        _expect_error(
            "COMMON_STRATEGY_VERSION_MISMATCH",
            lambda: resolve_common_strategy_identity(
                resolved_config
            ),
        )

    print("COMMON_STRATEGY_VERSION_MISMATCH_BLOCKED=SUCCESS")

    _expect_error(
        "COMMON_STRATEGY_PROFILE_METADATA_MISSING",
        lambda: get_declared_common_strategy_version({}),
    )

    _expect_error(
        "COMMON_STRATEGY_PROFILE_VERSION_MISSING",
        lambda: get_declared_common_strategy_version(
            {"metadata": {}}
        ),
    )

    with patch(
        "port_strategy_research.research_version_identity."
        "COMMON_STRATEGY_VERSION",
        "",
    ):
        _expect_error(
            "COMMON_STRATEGY_RUNTIME_VERSION_EMPTY",
            get_runtime_common_strategy_version,
        )

    print("COMMON_STRATEGY_PROFILE_METADATA_VALIDATION=SUCCESS")
    print("COMMON_STRATEGY_RUNTIME_VALUE_VALIDATION=SUCCESS")
    print(
        "COMMON_STRATEGY_VERSION_CANONICAL_RUNTIME_SOURCE="
        "port_strategy_common.common_version."
        "COMMON_STRATEGY_VERSION"
    )
    print("COMMON_STRATEGY_VERSION_CONTRACT_TEST=SUCCESS")


if __name__ == "__main__":
    main()
