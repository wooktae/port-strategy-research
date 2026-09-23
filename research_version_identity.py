"""Common helper that assembles the Research execution Version Identity.

The Common Package Version is based on the Distribution Metadata actually installed in the current Python Runtime,
the Common Strategy Version on the public Version constant provided by the installed Common Wheel,
the Research Engine Version on a constant dedicated to the Research repository,
the Strategy Config Version on the Config Snapshot generated at execution time,
the Metrics Config Version on the Resolved Config Metadata,
and the Source SHA and Image Digest on the deployment Runtime environment variables.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import metadata
import os
import re
from typing import Any, Mapping

from port_strategy_common.common_version import COMMON_STRATEGY_VERSION
from port_strategy_research.research_engine_version import (
    RESEARCH_ENGINE_VERSION,
)
from port_strategy_research.strategy_config_snapshot import (
    StrategyConfigSnapshot,
)


COMMON_DISTRIBUTION_NAME = "port-strategy-common"
STRATEGY_CONFIG_VERSION_PATTERN = re.compile(r"^RSCFG-[0-9]{4}$")
METRICS_CONFIG_VERSION_PATTERN = re.compile(r"^RMETRICS-[0-9]{4}$")
SOURCE_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
IMAGE_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")

RESEARCH_SOURCE_SHA_ENV = "RESEARCH_SOURCE_SHA"
RESEARCH_IMAGE_DIGEST_ENV = "RESEARCH_IMAGE_DIGEST"


class ResearchVersionIdentityError(ValueError):
    """Raised when the Research Version Identity is missing or mismatched."""


@dataclass(frozen=True)
class CommonPackageIdentity:
    """Preserves both the Profile-declared value and the Runtime-installed value."""

    declared_version: str
    runtime_version: str
    distribution_name: str = COMMON_DISTRIBUTION_NAME


@dataclass(frozen=True)
class CommonStrategyIdentity:
    """Preserves both the Profile-declared value and the Common Runtime strategy Version."""

    declared_version: str
    runtime_version: str


@dataclass(frozen=True)
class ResearchEngineIdentity:
    """Preserves the Research Runtime Engine Version."""

    runtime_version: str


@dataclass(frozen=True)
class StrategyConfigIdentity:
    """Strategy Config Version from the execution Snapshot and the Resolved Metadata."""

    snapshot_version: str
    metadata_version: str


@dataclass(frozen=True)
class MetricsConfigIdentity:
    """Metrics Config Version from the execution Snapshot Metadata."""

    version: str


@dataclass(frozen=True)
class ResearchArtifactIdentity:
    """Execution evidence of the deployment Source and the Container Image."""

    source_sha: str | None
    image_digest: str | None
    status: str

    @property
    def is_complete(self) -> bool:
        return self.status == "COMPLETE"


def _get_metadata_mapping(
    resolved_config: Mapping[str, Any],
    *,
    missing_marker: str,
) -> Mapping[str, Any]:
    metadata_value = resolved_config.get("metadata")

    if not isinstance(metadata_value, Mapping):
        raise ResearchVersionIdentityError(missing_marker)

    return metadata_value


def _get_required_metadata_string(
    resolved_config: Mapping[str, Any],
    *,
    key: str,
    metadata_missing_marker: str,
    value_missing_marker: str,
) -> str:
    metadata_value = _get_metadata_mapping(
        resolved_config,
        missing_marker=metadata_missing_marker,
    )
    value = metadata_value.get(key)

    if not isinstance(value, str) or not value.strip():
        raise ResearchVersionIdentityError(value_missing_marker)

    return value.strip()


def get_installed_common_package_version() -> str:
    """Returns the Common Distribution Version installed in the current Runtime."""
    try:
        version = metadata.version(COMMON_DISTRIBUTION_NAME)
    except metadata.PackageNotFoundError as exc:
        raise ResearchVersionIdentityError(
            "COMMON_PACKAGE_DISTRIBUTION_NOT_INSTALLED="
            f"{COMMON_DISTRIBUTION_NAME}"
        ) from exc

    normalized = version.strip()
    if not normalized:
        raise ResearchVersionIdentityError(
            "COMMON_PACKAGE_RUNTIME_VERSION_EMPTY"
        )

    return normalized


def get_declared_common_package_version(
    resolved_config: Mapping[str, Any],
) -> str:
    """Returns the Common Package declared Version from the Resolved Config Metadata."""
    return _get_required_metadata_string(
        resolved_config,
        key="common_package_version",
        metadata_missing_marker=(
            "COMMON_PACKAGE_PROFILE_METADATA_MISSING"
        ),
        value_missing_marker=(
            "COMMON_PACKAGE_PROFILE_VERSION_MISSING"
        ),
    )


def resolve_common_package_identity(
    resolved_config: Mapping[str, Any],
) -> CommonPackageIdentity:
    """Verifies that the Profile-declared Version matches the actually installed Version."""
    declared_version = get_declared_common_package_version(
        resolved_config
    )
    runtime_version = get_installed_common_package_version()

    if declared_version != runtime_version:
        raise ResearchVersionIdentityError(
            "COMMON_PACKAGE_VERSION_MISMATCH "
            f"declared={declared_version} "
            f"runtime={runtime_version}"
        )

    return CommonPackageIdentity(
        declared_version=declared_version,
        runtime_version=runtime_version,
    )


def get_runtime_common_strategy_version() -> str:
    """Returns the Strategy Version provided by the installed Common Wheel."""
    if not isinstance(COMMON_STRATEGY_VERSION, str):
        raise ResearchVersionIdentityError(
            "COMMON_STRATEGY_RUNTIME_VERSION_TYPE_INVALID"
        )

    normalized = COMMON_STRATEGY_VERSION.strip()
    if not normalized:
        raise ResearchVersionIdentityError(
            "COMMON_STRATEGY_RUNTIME_VERSION_EMPTY"
        )

    return normalized


def get_declared_common_strategy_version(
    resolved_config: Mapping[str, Any],
) -> str:
    """Returns the Common Strategy declared Version from the Resolved Config Metadata."""
    return _get_required_metadata_string(
        resolved_config,
        key="common_strategy_version",
        metadata_missing_marker=(
            "COMMON_STRATEGY_PROFILE_METADATA_MISSING"
        ),
        value_missing_marker=(
            "COMMON_STRATEGY_PROFILE_VERSION_MISSING"
        ),
    )


def resolve_common_strategy_identity(
    resolved_config: Mapping[str, Any],
) -> CommonStrategyIdentity:
    """Verifies that the Profile-declared value matches the Common Runtime Strategy Version."""
    declared_version = get_declared_common_strategy_version(
        resolved_config
    )
    runtime_version = get_runtime_common_strategy_version()

    if declared_version != runtime_version:
        raise ResearchVersionIdentityError(
            "COMMON_STRATEGY_VERSION_MISMATCH "
            f"declared={declared_version} "
            f"runtime={runtime_version}"
        )

    return CommonStrategyIdentity(
        declared_version=declared_version,
        runtime_version=runtime_version,
    )


def get_runtime_research_engine_version() -> str:
    """Returns the Engine Version dedicated to the Research repository."""
    if not isinstance(RESEARCH_ENGINE_VERSION, str):
        raise ResearchVersionIdentityError(
            "RESEARCH_ENGINE_VERSION_TYPE_INVALID"
        )

    normalized = RESEARCH_ENGINE_VERSION.strip()
    if not normalized:
        raise ResearchVersionIdentityError(
            "RESEARCH_ENGINE_VERSION_EMPTY"
        )

    return normalized


def resolve_research_engine_identity() -> ResearchEngineIdentity:
    """Creates the Research Runtime Engine Identity."""
    return ResearchEngineIdentity(
        runtime_version=get_runtime_research_engine_version()
    )


def _validate_version_pattern(
    version: Any,
    *,
    pattern: re.Pattern[str],
    missing_marker: str,
    format_marker: str,
) -> str:
    if not isinstance(version, str) or not version.strip():
        raise ResearchVersionIdentityError(missing_marker)

    normalized = version.strip()

    if not pattern.fullmatch(normalized):
        raise ResearchVersionIdentityError(
            f"{format_marker}={normalized}"
        )

    return normalized


def get_snapshot_strategy_config_version(
    config_snapshot: StrategyConfigSnapshot,
) -> str:
    """Returns the Strategy Config Version held by the Config Snapshot."""
    return _validate_version_pattern(
        config_snapshot.strategy_config_version,
        pattern=STRATEGY_CONFIG_VERSION_PATTERN,
        missing_marker=(
            "STRATEGY_CONFIG_SNAPSHOT_VERSION_MISSING"
        ),
        format_marker=(
            "STRATEGY_CONFIG_SNAPSHOT_VERSION_FORMAT_INVALID"
        ),
    )


def get_metadata_strategy_config_version(
    resolved_config: Mapping[str, Any],
) -> str:
    """Returns the Strategy Config Version from the Resolved Config Metadata."""
    metadata_version = _get_required_metadata_string(
        resolved_config,
        key="strategy_config_version",
        metadata_missing_marker=(
            "STRATEGY_CONFIG_PROFILE_METADATA_MISSING"
        ),
        value_missing_marker=(
            "STRATEGY_CONFIG_PROFILE_VERSION_MISSING"
        ),
    )

    return _validate_version_pattern(
        metadata_version,
        pattern=STRATEGY_CONFIG_VERSION_PATTERN,
        missing_marker=(
            "STRATEGY_CONFIG_PROFILE_VERSION_MISSING"
        ),
        format_marker=(
            "STRATEGY_CONFIG_PROFILE_VERSION_FORMAT_INVALID"
        ),
    )


def resolve_strategy_config_identity(
    config_snapshot: StrategyConfigSnapshot,
) -> StrategyConfigIdentity:
    """Verifies that the Config Version of the Snapshot matches that of the Resolved Metadata."""
    snapshot_version = get_snapshot_strategy_config_version(
        config_snapshot
    )
    metadata_version = get_metadata_strategy_config_version(
        config_snapshot.resolved_config
    )

    if snapshot_version != metadata_version:
        raise ResearchVersionIdentityError(
            "STRATEGY_CONFIG_VERSION_MISMATCH "
            f"snapshot={snapshot_version} "
            f"metadata={metadata_version}"
        )

    return StrategyConfigIdentity(
        snapshot_version=snapshot_version,
        metadata_version=metadata_version,
    )


def get_metrics_config_version(
    resolved_config: Mapping[str, Any],
) -> str:
    """Returns the Metrics Config Version from the Resolved Config Metadata."""
    version = _get_required_metadata_string(
        resolved_config,
        key="metrics_config_version",
        metadata_missing_marker=(
            "METRICS_CONFIG_PROFILE_METADATA_MISSING"
        ),
        value_missing_marker=(
            "METRICS_CONFIG_PROFILE_VERSION_MISSING"
        ),
    )

    return _validate_version_pattern(
        version,
        pattern=METRICS_CONFIG_VERSION_PATTERN,
        missing_marker=(
            "METRICS_CONFIG_PROFILE_VERSION_MISSING"
        ),
        format_marker=(
            "METRICS_CONFIG_PROFILE_VERSION_FORMAT_INVALID"
        ),
    )


def resolve_metrics_config_identity(
    config_snapshot: StrategyConfigSnapshot,
) -> MetricsConfigIdentity:
    """Creates the Metrics Config Version Identity from the execution Snapshot."""
    return MetricsConfigIdentity(
        version=get_metrics_config_version(
            config_snapshot.resolved_config
        )
    )


def _normalize_optional_environment_value(
    name: str,
) -> str | None:
    raw_value = os.getenv(name)

    if raw_value is None:
        return None

    normalized = raw_value.strip()
    return normalized or None


def resolve_research_artifact_identity(
    *,
    require_complete: bool = False,
) -> ResearchArtifactIdentity:
    """Validates the Source SHA and Image Digest environment variables into execution evidence.

    In structural step 10, UNRESOLVED is allowed when both values are absent.
    If only one is present or the format is invalid, it is always blocked.
    In Candidate AWS Batch execution, require_complete=True is enforced.
    """
    source_sha = _normalize_optional_environment_value(
        RESEARCH_SOURCE_SHA_ENV
    )
    image_digest = _normalize_optional_environment_value(
        RESEARCH_IMAGE_DIGEST_ENV
    )

    if source_sha is None and image_digest is None:
        if require_complete:
            raise ResearchVersionIdentityError(
                "RESEARCH_ARTIFACT_IDENTITY_REQUIRED"
            )

        return ResearchArtifactIdentity(
            source_sha=None,
            image_digest=None,
            status="UNRESOLVED",
        )

    if source_sha is None or image_digest is None:
        raise ResearchVersionIdentityError(
            "RESEARCH_ARTIFACT_IDENTITY_PARTIAL "
            f"source_sha_present={source_sha is not None} "
            f"image_digest_present={image_digest is not None}"
        )

    normalized_source_sha = source_sha.lower()
    normalized_image_digest = image_digest.lower()

    if not SOURCE_SHA_PATTERN.fullmatch(normalized_source_sha):
        raise ResearchVersionIdentityError(
            "RESEARCH_SOURCE_SHA_FORMAT_INVALID="
            f"{source_sha}"
        )

    if not IMAGE_DIGEST_PATTERN.fullmatch(normalized_image_digest):
        raise ResearchVersionIdentityError(
            "RESEARCH_IMAGE_DIGEST_FORMAT_INVALID="
            f"{image_digest}"
        )

    return ResearchArtifactIdentity(
        source_sha=normalized_source_sha,
        image_digest=normalized_image_digest,
        status="COMPLETE",
    )
