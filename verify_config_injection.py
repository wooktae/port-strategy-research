"""DB-free contract verification of explicit Resolved Config injection."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pandas as pd

from port_strategy_research import backtest_engine
from port_strategy_research.backtest_metrics import (
    calculate_mdd,
    calculate_sharpe,
)
from port_strategy_research.strategy_profile_loader import (
    load_strategy_config_snapshot,
)


ROOT = Path(__file__).resolve().parent

FORBIDDEN_GLOBAL_CONFIG_IMPORTS = {
    "backtest_engine.py": {
        "GENERAL_CONFIG",
        "MARKET_CONFIG",
        "FILTER_CONFIG",
        "SIZING_CONFIG",
        "BUY_CONFIG",
        "SELL_CONFIG",
    },
    "backtest_loader.py": {
        "BACKTEST_START_DATE",
    },
    "backtest_buy_logic.py": {
        "GENERAL_CONFIG",
        "BUY_CONFIG",
        "SIZING_CONFIG",
    },
    "backtest_position_manager.py": {
        "GENERAL_CONFIG",
        "SELL_CONFIG",
    },
    "backtest_sell_logic.py": {
        "SELL_CONFIG",
    },
    "research_backtest_market_adapter.py": {
        "MARKET_CONFIG",
    },
    "research_backtest_filter_adapter.py": {
        "FILTER_CONFIG",
    },
    "research_backtest_sizing_adapter.py": {
        "SIZING_CONFIG",
    },
    "backtest_metrics.py": {
        "RISK_FREE_RATE",
        "TRADING_DAYS_PER_YEAR",
    },
}


def imported_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names.update(alias.name for alias in node.names)

    return names


for filename, forbidden in FORBIDDEN_GLOBAL_CONFIG_IMPORTS.items():
    imported = imported_names(ROOT / filename)
    overlap = sorted(imported & forbidden)
    assert not overlap, (
        f"FORBIDDEN_GLOBAL_CONFIG_IMPORT={filename}:{overlap}"
    )

print("GLOBAL_STRATEGY_CONFIG_IMPORT_REMOVED=SUCCESS")

required_parameters = {
    "run_backtest": {
        "resolved_config",
        "backtest_start_date",
    },
}

for name, required in required_parameters.items():
    parameters = set(
        inspect.signature(
            getattr(backtest_engine, name)
        ).parameters
    )
    assert required <= parameters, (
        f"MISSING_EXPLICIT_PARAMETER={name}:"
        f"{sorted(required - parameters)}"
    )

print("ENGINE_CONFIG_SIGNATURE=SUCCESS")

snapshot = load_strategy_config_snapshot("RSCFG-0001")
resolved = snapshot.resolved_config
captured = {}


class FakeConnection:
    def commit(self):
        captured["commit_count"] = (
            captured.get("commit_count", 0) + 1
        )


class FakePriceFrame:
    def iterrows(self):
        return iter([])


class FakeDecision:
    signal_type = "NEUTRAL"
    base_exposure = 0
    max_positions = 0
    min_score = 0
    min_flow = 0
    reason = "contract-test"


def fake_get_dates(conn, *, backtest_start_date):
    captured["backtest_start_date"] = backtest_start_date
    return ["2026-08-01", "2026-08-02"]


def fake_evaluate_market(market, *, market_config):
    captured["market_config"] = market_config
    return FakeDecision()


def fake_filter(stocks, decision, *, filter_config):
    captured["filter_config"] = filter_config
    return []


def fake_positions(**kwargs):
    captured["sell_config"] = kwargs["sell_config"]
    captured["position_backtest_policy"] = kwargs[
        "backtest_policy"
    ]
    return {}, set(), 0, [], []


def fake_buy(**kwargs):
    captured["sizing_config"] = kwargs["sizing_config"]
    captured["buy_guard_config"] = kwargs[
        "buy_guard_config"
    ]
    captured["buy_config"] = kwargs["buy_config"]
    captured["buy_backtest_policy"] = kwargs[
        "backtest_policy"
    ]
    return {}, 0, []


backtest_engine.get_dates = fake_get_dates
backtest_engine.load_stock_universe = lambda conn: {}
backtest_engine.get_market = lambda conn, date: {}
backtest_engine.get_stocks = lambda conn, date: []
backtest_engine.get_price = (
    lambda conn, date: FakePriceFrame()
)
backtest_engine.evaluate_market = fake_evaluate_market
backtest_engine.filter_buy_candidates = fake_filter
backtest_engine.process_existing_positions = fake_positions
backtest_engine.process_buy = fake_buy
backtest_engine.insert_daily_result = (
    lambda conn, run_id, row: None
)
backtest_engine.insert_daily_positions = (
    lambda conn, run_id, date, positions, company_map: None
)

history = backtest_engine.run_backtest(
    conn=FakeConnection(),
    run_id=1,
    resolved_config=resolved,
    backtest_start_date="2026-01-01",
    strategy_config_version=snapshot.strategy_config_version,
    config_hash=snapshot.config_hash,
)

assert len(history) == 1
assert captured["backtest_start_date"] == "2026-01-01"
assert captured["market_config"] is resolved["market"]
assert captured["filter_config"] is resolved["filter"]
assert captured["sizing_config"] is resolved["sizing"]
assert captured["buy_guard_config"] is resolved["buy_guard"]
assert captured["buy_config"] is resolved["buy"]
assert captured["sell_config"] is resolved["sell"]
assert (
    captured["position_backtest_policy"]
    is resolved["backtest_policy"]
)
assert (
    captured["buy_backtest_policy"]
    is resolved["backtest_policy"]
)

print("ENGINE_RUNTIME_CONFIG_IDENTITY=SUCCESS")
print("MARKET_CONFIG_INJECTION=SUCCESS")
print("FILTER_CONFIG_INJECTION=SUCCESS")
print("SIZING_CONFIG_INJECTION=SUCCESS")
print("BUY_GUARD_CONFIG_INJECTION=SUCCESS")
print("BUY_CONFIG_INJECTION=SUCCESS")
print("SELL_CONFIG_INJECTION=SUCCESS")
print("BACKTEST_POLICY_INJECTION=SUCCESS")
print("LOADER_EXECUTION_INPUT_INJECTION=SUCCESS")

metric_df = pd.DataFrame(
    [
        {
            "daily_return": 0.01,
            "cum_return": 1.01,
        },
        {
            "daily_return": -0.005,
            "cum_return": 1.00495,
        },
        {
            "daily_return": 0.002,
            "cum_return": 1.0069599,
        },
    ]
)

mdd = calculate_mdd(
    metric_df,
    metrics_config=resolved["metrics"],
)
sharpe = calculate_sharpe(
    metric_df,
    metrics_config=resolved["metrics"],
)

assert mdd <= 0
assert isinstance(float(sharpe), float)

print("METRICS_CONFIG_INJECTION=SUCCESS")

buy_source = (
    ROOT / "backtest_buy_logic.py"
).read_text(encoding="utf-8")
assert "config={}" not in buy_source
assert "config=buy_guard_config" in buy_source
assert "sizing_config=sizing_config" in buy_source

sell_source = (
    ROOT / "backtest_position_manager.py"
).read_text(encoding="utf-8")
assert "sell_config=sell_config" in sell_source

print("EMPTY_CONFIG_CALL_REMOVED=SUCCESS")
print("CONFIG_INJECTION_CONTRACT_TEST=SUCCESS")
