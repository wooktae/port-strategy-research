"""DB-free contract verification of the Strategy Profile Validator."""

from __future__ import annotations

from copy import deepcopy

from port_strategy_research.strategy_profile_loader import (
    load_resolved_strategy_profile,
    load_strategy_profile,
)
from port_strategy_research.strategy_profile_schema import (
    StrategyProfileValidationError,
    resolve_strategy_profile,
)


def expect_error(
    profile,
    version: str,
    expected_code: str,
) -> None:
    try:
        resolve_strategy_profile(
            profile,
            requested_version=version,
        )
    except StrategyProfileValidationError as exc:
        message = str(exc)
        assert expected_code in message, message
        print(f"EXPECTED_ERROR={expected_code}")
        return

    raise AssertionError(
        f"EXPECTED_VALIDATION_ERROR_NOT_RAISED={expected_code}"
    )


profile, profile_path = load_strategy_profile("RSCFG-0001")
resolved, resolved_path = load_resolved_strategy_profile("RSCFG-0001")

assert profile_path == resolved_path
assert resolved["metadata"]["strategy_config_version"] == "RSCFG-0001"
assert len(resolved["market"]) == 28
assert len(resolved["filter"]) == 10
assert len(resolved["sizing"]) == 7
assert len(resolved["buy_guard"]) == 25
assert len(resolved["buy"]) == 1
assert len(resolved["sell"]) == 64
assert len(resolved["backtest_policy"]) == 5
assert len(resolved["metrics"]) == 2

print("BASELINE_PROFILE_VALIDATION=SUCCESS")
print("COMMON_DEFAULT_OVERRIDE_MERGE=SUCCESS")

case = deepcopy(profile)
case["unexpected"] = {}
expect_error(
    case,
    "RSCFG-0001",
    "STRATEGY_PROFILE_UNKNOWN_CATEGORY",
)

case = deepcopy(profile)
del case["metadata"]["description"]
expect_error(
    case,
    "RSCFG-0001",
    "STRATEGY_PROFILE_MISSING_METADATA_KEY",
)

case = deepcopy(profile)
case["market"]["unexpected_key"] = "0.1"
expect_error(
    case,
    "RSCFG-0001",
    "STRATEGY_PROFILE_UNKNOWN_CONFIG_KEY",
)

case = deepcopy(profile)
del case["sell"]
expect_error(
    case,
    "RSCFG-0001",
    "STRATEGY_PROFILE_MISSING_CATEGORY",
)

case = deepcopy(profile)
case["market"]["aggressive_max_positions"] = "4"
expect_error(
    case,
    "RSCFG-0001",
    "STRATEGY_PROFILE_TYPE_ERROR",
)

case = deepcopy(profile)
case["buy_guard"]["high_flow_high_score_soft_enabled"] = "false"
expect_error(
    case,
    "RSCFG-0001",
    "STRATEGY_PROFILE_TYPE_ERROR",
)

partial = deepcopy(profile)
partial["market"] = {
    "neutral_exposure": "0.45",
}
partial["filter"] = {}
partial["sizing"] = {}
partial["buy_guard"] = {}
partial["buy"] = {}
partial["sell"] = {}
partial["backtest_policy"] = {}
partial["metrics"] = {}

partial_resolved = resolve_strategy_profile(
    partial,
    requested_version="RSCFG-0001",
)

assert str(partial_resolved["market"]["neutral_exposure"]) == "0.45"
assert len(partial_resolved["market"]) == 28
assert len(partial_resolved["sell"]) == 64

print("PARTIAL_OVERRIDE_MERGE=SUCCESS")
print("STRATEGY_PROFILE_VALIDATOR_TEST=SUCCESS")
