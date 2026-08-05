"""Research 실행 Version Identity를 구성하는 공통 helper.

Common Package Version은 현재 Python Runtime에 실제 설치된 Distribution Metadata를,
Common Strategy Version은 설치된 Common Wheel이 제공하는 공개 Version 상수를,
Research Engine Version은 Research 저장소 전용 상수를,
Strategy Config Version은 실행 시 생성된 Config Snapshot을,
Metrics Config Version은 Resolved Config Metadata를,
Source SHA와 Image Digest는 배포 Runtime 환경변수를 기준으로 한다.
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
    """Research Version Identity가 누락되거나 불일치할 때 발생한다."""


@dataclass(frozen=True)
class CommonPackageIdentity:
    """Profile 선언값과 Runtime 설치값을 함께 보존한다."""

    declared_version: str
    runtime_version: str
    distribution_name: str = COMMON_DISTRIBUTION_NAME


@dataclass(frozen=True)
class CommonStrategyIdentity:
    """Profile 선언값과 Common Runtime 전략 Version을 함께 보존한다."""

    declared_version: str
    runtime_version: str


@dataclass(frozen=True)
class ResearchEngineIdentity:
    """Research Runtime Engine Version을 보존한다."""

    runtime_version: str


@dataclass(frozen=True)
class StrategyConfigIdentity:
    """실행 Snapshot과 Resolved Metadata의 Strategy Config Version."""

    snapshot_version: str
    metadata_version: str


@dataclass(frozen=True)
class MetricsConfigIdentity:
    """실행 Snapshot Metadata의 Metrics Config Version."""

    version: str


@dataclass(frozen=True)
class ResearchArtifactIdentity:
    """배포 Source와 Container Image의 실행 증적."""

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
    """현재 Runtime에 설치된 Common Distribution Version을 반환한다."""
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
    """Resolved Config Metadata의 Common Package 선언 Version을 반환한다."""
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
    """Profile 선언 Version과 실제 설치 Version의 일치를 검증한다."""
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
    """설치된 Common Wheel이 제공하는 Strategy Version을 반환한다."""
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
    """Resolved Config Metadata의 Common Strategy 선언 Version을 반환한다."""
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
    """Profile 선언값과 Common Runtime Strategy Version 일치를 검증한다."""
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
    """Research 저장소 전용 Engine Version을 반환한다."""
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
    """Research Runtime Engine Identity를 생성한다."""
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
    """Config Snapshot이 보유한 Strategy Config Version을 반환한다."""
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
    """Resolved Config Metadata의 Strategy Config Version을 반환한다."""
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
    """Snapshot과 Resolved Metadata의 Config Version 일치를 검증한다."""
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
    """Resolved Config Metadata의 Metrics Config Version을 반환한다."""
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
    """실행 Snapshot에서 Metrics Config Version Identity를 생성한다."""
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
    """Source SHA와 Image Digest 환경변수를 검증해 실행 증적으로 만든다.

    10번 구조 단계에서는 두 값이 모두 없으면 UNRESOLVED를 허용한다.
    둘 중 하나만 있거나 형식이 잘못되면 항상 차단한다.
    Candidate AWS Batch 실행에서는 require_complete=True로 강제한다.
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
