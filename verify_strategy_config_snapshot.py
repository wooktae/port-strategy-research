"""DB-free contract verification of the Resolved Config Snapshot and its SHA-256."""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal

from port_strategy_research.strategy_config_snapshot import (
    StrategyConfigSecretError,
    assert_no_secrets,
    calculate_config_hash,
    to_canonical_json,
)
from port_strategy_research.strategy_profile_loader import (
    load_strategy_config_snapshot,
    load_strategy_profile,
)
from port_strategy_research.strategy_profile_schema import (
    resolve_strategy_profile,
)


snapshot_1 = load_strategy_config_snapshot("RSCFG-0001")
snapshot_2 = load_strategy_config_snapshot("RSCFG-0001")

assert snapshot_1.strategy_config_version == "RSCFG-0001"
assert snapshot_1.profile_path == snapshot_2.profile_path
assert snapshot_1.canonical_json == snapshot_2.canonical_json
assert snapshot_1.config_hash == snapshot_2.config_hash
assert len(snapshot_1.config_hash) == 64
assert snapshot_1.config_hash.isalnum()

resolved = snapshot_1.resolved_config

assert len(resolved["market"]) == 28
assert len(resolved["filter"]) == 10
assert len(resolved["sizing"]) == 7
assert len(resolved["buy_guard"]) == 25
assert len(resolved["buy"]) == 1
assert len(resolved["sell"]) == 64
assert len(resolved["backtest_policy"]) == 5
assert len(resolved["metrics"]) == 2

print("RESOLVED_CONFIG_FULL_SNAPSHOT=SUCCESS")
print("CANONICAL_JSON_DETERMINISM=SUCCESS")
print(f"CONFIG_HASH={snapshot_1.config_hash}")
print("SHA256_CONFIG_HASH=SUCCESS")

profile, _ = load_strategy_profile("RSCFG-0001")
partial = deepcopy(profile)
partial["market"] = {"neutral_exposure": "0.45"}
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

partial_json = to_canonical_json(partial_resolved)
partial_hash = calculate_config_hash(partial_json)

assert str(partial_resolved["market"]["neutral_exposure"]) == "0.45"
assert len(partial_resolved["market"]) == 28
assert partial_hash != snapshot_1.config_hash

print("COMMON_DEFAULT_OVERRIDE_SNAPSHOT=SUCCESS")
print("CONFIG_CHANGE_HASH_CHANGE=SUCCESS")

order_a = {
    "b": Decimal("2.0"),
    "a": {
        "y": 2,
        "x": 1,
    },
}
order_b = {
    "a": {
        "x": 1,
        "y": 2,
    },
    "b": Decimal("2.0"),
}

assert to_canonical_json(order_a) == to_canonical_json(order_b)

print("CANONICAL_KEY_ORDER=SUCCESS")

assert_no_secrets(resolved)
print("SECRET_ABSENCE_VERIFY=SUCCESS")

secret_case = deepcopy(resolved)
secret_case["metadata"]["api_token"] = "dummy"

try:
    assert_no_secrets(secret_case)
except StrategyConfigSecretError as exc:
    assert "STRATEGY_CONFIG_SECRET_CANDIDATE" in str(exc)
    assert "$.metadata.api_token" in str(exc)
    print("SECRET_KEY_BLOCK=SUCCESS")
else:
    raise AssertionError("SECRET_KEY_WAS_NOT_BLOCKED")

secret_value_case = deepcopy(resolved)
secret_value_case["metadata"]["description"] = (
    "postgresql://user:password@example.internal:5432/db"
)

try:
    assert_no_secrets(secret_value_case)
except StrategyConfigSecretError as exc:
    assert "STRATEGY_CONFIG_SECRET_CANDIDATE" in str(exc)
    print("SECRET_VALUE_BLOCK=SUCCESS")
else:
    raise AssertionError("SECRET_VALUE_WAS_NOT_BLOCKED")

print("RESOLVED_CONFIG_SNAPSHOT_TEST=SUCCESS")
