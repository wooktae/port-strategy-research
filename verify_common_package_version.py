"""Verifies the Common Package Version Runtime Identity contract."""

from __future__ import annotations

from unittest.mock import patch

from port_strategy_research.research_version_identity import (
    COMMON_DISTRIBUTION_NAME,
    ResearchVersionIdentityError,
    get_declared_common_package_version,
    get_installed_common_package_version,
    resolve_common_package_identity,
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
            "common_package_version": "1.0.0",
        },
    }

    with patch(
        "port_strategy_research.research_version_identity."
        "metadata.version",
        return_value="1.0.0",
    ) as mocked_version:
        runtime_version = get_installed_common_package_version()
        assert runtime_version == "1.0.0"
        mocked_version.assert_called_once_with(
            COMMON_DISTRIBUTION_NAME
        )

    print("COMMON_PACKAGE_RUNTIME_METADATA_SOURCE=SUCCESS")

    declared_version = get_declared_common_package_version(
        resolved_config
    )
    assert declared_version == "1.0.0"

    print("COMMON_PACKAGE_PROFILE_DECLARATION_SOURCE=SUCCESS")

    with patch(
        "port_strategy_research.research_version_identity."
        "metadata.version",
        return_value="1.0.0",
    ):
        identity = resolve_common_package_identity(
            resolved_config
        )

    assert identity.declared_version == "1.0.0"
    assert identity.runtime_version == "1.0.0"
    assert (
        identity.distribution_name
        == COMMON_DISTRIBUTION_NAME
    )

    print("COMMON_PACKAGE_DECLARED_RUNTIME_MATCH=SUCCESS")

    with patch(
        "port_strategy_research.research_version_identity."
        "metadata.version",
        return_value="1.0.1",
    ):
        _expect_error(
            "COMMON_PACKAGE_VERSION_MISMATCH",
            lambda: resolve_common_package_identity(
                resolved_config
            ),
        )

    print("COMMON_PACKAGE_VERSION_MISMATCH_BLOCKED=SUCCESS")

    _expect_error(
        "COMMON_PACKAGE_PROFILE_METADATA_MISSING",
        lambda: get_declared_common_package_version({}),
    )

    _expect_error(
        "COMMON_PACKAGE_PROFILE_VERSION_MISSING",
        lambda: get_declared_common_package_version(
            {"metadata": {}}
        ),
    )

    print("COMMON_PACKAGE_PROFILE_METADATA_VALIDATION=SUCCESS")
    print(
        "COMMON_PACKAGE_VERSION_CANONICAL_RUNTIME_SOURCE="
        "importlib.metadata"
    )
    print("COMMON_PACKAGE_VERSION_CONTRACT_TEST=SUCCESS")


if __name__ == "__main__":
    main()
