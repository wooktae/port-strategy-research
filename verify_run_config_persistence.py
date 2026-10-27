"""Verifies the Run / Trade Config Persistence contract without AWS RDS."""

from __future__ import annotations

import inspect
from pathlib import Path

from port_strategy_research.backtest_run_store import create_run
from port_strategy_research.backtest_trade_log import insert_trade_log
from port_strategy_research.strategy_profile_loader import (
    load_strategy_config_snapshot,
)


ROOT = Path(__file__).resolve().parent
snapshot = load_strategy_config_snapshot("RSCFG-0001")


class FakeCursor:
    def __init__(self, owner):
        self.owner = owner

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, sql, params=None):
        self.owner.calls.append((sql, params))


class FakeConnection:
    def __init__(self):
        self.calls = []
        self.commit_count = 0

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.commit_count += 1


run_conn = FakeConnection()
run_id = create_run(
    run_conn,
    run_mode="BACKTEST",
    config_snapshot=snapshot,
    run_note="contract-test",
)

assert run_id
assert run_conn.commit_count == 1
assert len(run_conn.calls) == 1

run_sql, run_params = run_conn.calls[0]
assert "strategy_config_version" in run_sql
assert "config_hash" in run_sql
assert "strategy_profile_path" in run_sql
assert "config_snapshot" in run_sql
assert snapshot.strategy_config_version in run_params
assert snapshot.config_hash in run_params
assert str(snapshot.profile_path) in run_params
assert snapshot.canonical_json in run_params

print("RUN_RESOLVED_CONFIG_SNAPSHOT_PERSISTENCE=SUCCESS")
print("RUN_STRATEGY_CONFIG_VERSION_PERSISTENCE=SUCCESS")
print("RUN_CONFIG_HASH_PERSISTENCE=SUCCESS")

trade_conn = FakeConnection()
insert_trade_log(
    trade_conn,
    {
        "ticker_code": "000001",
        "buy_date": "2026-08-01",
        "sell_date": "2026-08-02",
        "holding_period": 1,
        "return_pct": "1.00%",
        "buy_info": {"score": 0.8},
        "sell_info": {"reason": "test"},
    },
    {"000001": "TEST"},
    run_id,
    strategy_config_version=snapshot.strategy_config_version,
    config_hash=snapshot.config_hash,
)

assert len(trade_conn.calls) == 1
trade_sql, trade_params = trade_conn.calls[0]

assert "strategy_config_version" in trade_sql
assert "config_hash" in trade_sql
assert "config_snapshot" not in trade_sql
assert run_id in trade_params
assert snapshot.strategy_config_version in trade_params
assert snapshot.config_hash in trade_params
assert snapshot.canonical_json not in trade_params

print("TRADE_RUN_ID_SNAPSHOT_LINK=SUCCESS")
print("TRADE_CONFIG_VERSION_REFERENCE=SUCCESS")
print("TRADE_CONFIG_HASH_REFERENCE=SUCCESS")
print("TRADE_FULL_CONFIG_DUPLICATION_REMOVED=SUCCESS")

run_source = (ROOT / "backtest_run_store.py").read_text(
    encoding="utf-8"
)
trade_source = (ROOT / "backtest_trade_log.py").read_text(
    encoding="utf-8"
)
entry_source = (ROOT / "backtest_research_run.py").read_text(
    encoding="utf-8"
)

assert "get_config_snapshot" not in run_source
assert "get_config_snapshot" not in trade_source
assert "def save_config_snapshot" not in entry_source
assert "strategy_run_config" not in entry_source

print("COMMON_GLOBAL_SNAPSHOT_PERSISTENCE_REMOVED=SUCCESS")
print("LEGACY_DUPLICATE_RUN_CONFIG_WRITE_REMOVED=SUCCESS")

create_run_parameters = inspect.signature(create_run).parameters
assert "config_snapshot" in create_run_parameters

trade_parameters = inspect.signature(insert_trade_log).parameters
assert "strategy_config_version" in trade_parameters
assert "config_hash" in trade_parameters

print("CANONICAL_CONFIG_SOURCE=strategy_backtest_run.config_snapshot")
print("DERIVED_CONFIG_IDENTITY=strategy_config_version+config_hash")
print("RUN_CONFIG_PERSISTENCE_CONTRACT_TEST=SUCCESS")
