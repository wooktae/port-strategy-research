"""Research Strategy Profile Schema and Resolved Config validation.

The Profile JSON expresses per-Strategy-Version Overrides.
At execution time it is merged with the Common 1.0.0 defaults to produce a complete Resolved Config.
"""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation
from typing import Any

from port_strategy_common import config as common_config
from port_strategy_common.common_version import COMMON_STRATEGY_VERSION


REQUIRED_TOP_LEVEL_CATEGORIES = (
    "metadata",
    "market",
    "filter",
    "sizing",
    "buy_guard",
    "buy",
    "sell",
    "backtest_policy",
    "metrics",
)

REQUIRED_METADATA_KEYS = {
    "profile_schema_version",
    "strategy_config_version",
    "common_package_version",
    "common_strategy_version",
    "metrics_config_version",
    "status",
    "created_at",
    "description",
}

ALLOWED_PROFILE_STATUSES = {
    "BASELINE",
    "CANDIDATE",
    "CHALLENGER",
    "REJECTED",
    "APPROVED",
    "ARCHIVED",
}

BUY_GUARD_HIDDEN_DEFAULTS: dict[str, Any] = {
    "hot_chase_flow_min": Decimal("0.9"),
    "hot_chase_score_min": Decimal("0.6"),
    "hot_chase_intraday_min": Decimal("0.05"),
    "hot_chase_vol_max": Decimal("0.04"),
    "hot_chase_haircut": Decimal("0.2"),
    "hot_chase_size_multiplier": Decimal("0.1"),
    "buy_day_stop_risk_flow_min": Decimal("0.85"),
    "buy_day_stop_risk_score_min": Decimal("0.6"),
    "buy_day_stop_risk_intraday_min": Decimal("0.07"),
    "buy_day_stop_risk_vol_max": Decimal("0.035"),
    "buy_day_stop_risk_haircut": Decimal("0.5"),
    "buy_day_stop_risk_size_multiplier": Decimal("0.1"),
    "mid_flow_tight_range_flow_min": Decimal("0.75"),
    "mid_flow_tight_range_flow_max": Decimal("0.85"),
    "mid_flow_tight_range_vol_min": Decimal("0.025"),
    "mid_flow_tight_range_intraday_max": Decimal("0.04"),
    "mid_flow_tight_range_haircut": Decimal("0.7"),
    "mid_flow_tight_range_size_multiplier": Decimal("0.1"),
    "flow_0_9_plus_soft_min": Decimal("0.9"),
    "flow_0_9_plus_soft_size_multiplier": Decimal("0.7"),
    "high_flow_soft_haircut": Decimal("0.8"),
}

BUY_GUARD_EXPLICIT_KEYS = {
    "high_flow_high_score_soft_enabled",
    "high_flow_high_score_flow_min",
    "high_flow_high_score_final_min",
    "high_flow_high_score_size_multiplier",
}


class StrategyProfileValidationError(ValueError):
    """Strategy Profile contract violation."""


def _build_common_defaults() -> dict[str, dict[str, Any]]:
    buy_guard = {
        key: deepcopy(common_config.SIZING_CONFIG[key])
        for key in BUY_GUARD_EXPLICIT_KEYS
    }
    buy_guard.update(deepcopy(BUY_GUARD_HIDDEN_DEFAULTS))

    sizing = {
        key: deepcopy(value)
        for key, value in common_config.SIZING_CONFIG.items()
        if key not in BUY_GUARD_EXPLICIT_KEYS
    }

    return {
        "market": deepcopy(common_config.MARKET_CONFIG),
        "filter": deepcopy(common_config.FILTER_CONFIG),
        "sizing": sizing,
        "buy_guard": buy_guard,
        "buy": deepcopy(common_config.BUY_CONFIG),
        "sell": deepcopy(common_config.SELL_CONFIG),
        "backtest_policy": deepcopy(common_config.GENERAL_CONFIG),
        "metrics": {
            "risk_free_rate": common_config.RISK_FREE_RATE,
            "trading_days_per_year": common_config.TRADING_DAYS_PER_YEAR,
        },
    }


COMMON_DEFAULTS = _build_common_defaults()

ALLOWED_CONFIG_KEYS = {
    category: frozenset(values)
    for category, values in COMMON_DEFAULTS.items()
}


def _fail(code: str, detail: str = "") -> None:
    suffix = f": {detail}" if detail else ""
    raise StrategyProfileValidationError(f"{code}{suffix}")


def _is_bool(value: Any) -> bool:
    return isinstance(value, bool)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_decimal_compatible(value: Any) -> bool:
    if isinstance(value, bool):
        return False

    if isinstance(value, (Decimal, int, float)):
        return True

    if isinstance(value, str):
        try:
            Decimal(value)
        except (InvalidOperation, ValueError):
            return False
        return True

    return False


def _validate_value_type(
    *,
    category: str,
    key: str,
    value: Any,
    default_value: Any,
) -> None:
    path = f"{category}.{key}"

    if isinstance(default_value, bool):
        if not _is_bool(value):
            _fail("STRATEGY_PROFILE_TYPE_ERROR", f"{path} expected=bool")
        return

    if isinstance(default_value, int) and not isinstance(default_value, bool):
        if not _is_int(value):
            _fail("STRATEGY_PROFILE_TYPE_ERROR", f"{path} expected=int")
        return

    if isinstance(default_value, (Decimal, float)):
        if not _is_decimal_compatible(value):
            _fail(
                "STRATEGY_PROFILE_TYPE_ERROR",
                f"{path} expected=decimal-compatible",
            )
        return

    if isinstance(default_value, str):
        if not isinstance(value, str):
            _fail("STRATEGY_PROFILE_TYPE_ERROR", f"{path} expected=str")
        return

    _fail(
        "STRATEGY_PROFILE_UNSUPPORTED_DEFAULT_TYPE",
        f"{path} default_type={type(default_value).__name__}",
    )


def _normalize_value(value: Any, default_value: Any) -> Any:
    if isinstance(default_value, bool):
        return value

    if isinstance(default_value, int) and not isinstance(default_value, bool):
        return int(value)

    if isinstance(default_value, Decimal):
        return Decimal(str(value))

    if isinstance(default_value, float):
        return float(value)

    if isinstance(default_value, str):
        return value

    return value


def validate_profile_metadata(
    metadata: Any,
    *,
    requested_version: str,
) -> None:
    if not isinstance(metadata, dict):
        _fail("STRATEGY_PROFILE_METADATA_MUST_BE_OBJECT")

    metadata_keys = set(metadata)

    unknown_keys = sorted(metadata_keys - REQUIRED_METADATA_KEYS)
    if unknown_keys:
        _fail(
            "STRATEGY_PROFILE_UNKNOWN_METADATA_KEY",
            ",".join(unknown_keys),
        )

    missing_keys = sorted(REQUIRED_METADATA_KEYS - metadata_keys)
    if missing_keys:
        _fail(
            "STRATEGY_PROFILE_MISSING_METADATA_KEY",
            ",".join(missing_keys),
        )

    for key in REQUIRED_METADATA_KEYS:
        if not isinstance(metadata[key], str) or not metadata[key].strip():
            _fail(
                "STRATEGY_PROFILE_METADATA_TYPE_ERROR",
                f"{key} expected=non-empty-str",
            )

    if metadata["strategy_config_version"] != requested_version:
        _fail(
            "STRATEGY_PROFILE_VERSION_MISMATCH",
            (
                f"requested={requested_version},"
                f"embedded={metadata['strategy_config_version']}"
            ),
        )

    if metadata["profile_schema_version"] != "1.0.0":
        _fail(
            "STRATEGY_PROFILE_SCHEMA_VERSION_UNSUPPORTED",
            metadata["profile_schema_version"],
        )

    if metadata["common_package_version"] != "1.0.0":
        _fail(
            "STRATEGY_PROFILE_COMMON_PACKAGE_VERSION_MISMATCH",
            metadata["common_package_version"],
        )

    if metadata["common_strategy_version"] != COMMON_STRATEGY_VERSION:
        _fail(
            "STRATEGY_PROFILE_COMMON_STRATEGY_VERSION_MISMATCH",
            metadata["common_strategy_version"],
        )

    if metadata["status"] not in ALLOWED_PROFILE_STATUSES:
        _fail(
            "STRATEGY_PROFILE_STATUS_INVALID",
            metadata["status"],
        )


def validate_strategy_profile(
    profile: Any,
    *,
    requested_version: str,
) -> None:
    if not isinstance(profile, dict):
        _fail("STRATEGY_PROFILE_ROOT_MUST_BE_OBJECT")

    top_level_keys = set(profile)
    required_categories = set(REQUIRED_TOP_LEVEL_CATEGORIES)

    unknown_categories = sorted(top_level_keys - required_categories)
    if unknown_categories:
        _fail(
            "STRATEGY_PROFILE_UNKNOWN_CATEGORY",
            ",".join(unknown_categories),
        )

    missing_categories = sorted(required_categories - top_level_keys)
    if missing_categories:
        _fail(
            "STRATEGY_PROFILE_MISSING_CATEGORY",
            ",".join(missing_categories),
        )

    validate_profile_metadata(
        profile["metadata"],
        requested_version=requested_version,
    )

    for category, allowed_keys in ALLOWED_CONFIG_KEYS.items():
        overrides = profile[category]

        if not isinstance(overrides, dict):
            _fail(
                "STRATEGY_PROFILE_CATEGORY_MUST_BE_OBJECT",
                category,
            )

        unknown_keys = sorted(set(overrides) - set(allowed_keys))
        if unknown_keys:
            _fail(
                "STRATEGY_PROFILE_UNKNOWN_CONFIG_KEY",
                f"{category}={','.join(unknown_keys)}",
            )

        for key, value in overrides.items():
            _validate_value_type(
                category=category,
                key=key,
                value=value,
                default_value=COMMON_DEFAULTS[category][key],
            )


def resolve_strategy_profile(
    profile: dict[str, Any],
    *,
    requested_version: str,
) -> dict[str, Any]:
    """Merges the Common Defaults with the Profile Overrides and returns a complete Config."""
    validate_strategy_profile(
        profile,
        requested_version=requested_version,
    )

    resolved: dict[str, Any] = {
        "metadata": deepcopy(profile["metadata"]),
    }

    for category, defaults in COMMON_DEFAULTS.items():
        merged = deepcopy(defaults)
        overrides = profile[category]

        for key, value in overrides.items():
            merged[key] = _normalize_value(
                value,
                defaults[key],
            )

        missing_keys = sorted(set(defaults) - set(merged))
        if missing_keys:
            _fail(
                "STRATEGY_PROFILE_RESOLVED_CONFIG_MISSING_KEY",
                f"{category}={','.join(missing_keys)}",
            )

        unknown_keys = sorted(set(merged) - set(defaults))
        if unknown_keys:
            _fail(
                "STRATEGY_PROFILE_RESOLVED_CONFIG_UNKNOWN_KEY",
                f"{category}={','.join(unknown_keys)}",
            )

        resolved[category] = merged

    return resolved
