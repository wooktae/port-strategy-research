"""Regression test for Research BUY Guard / Haircut Config forwarding and result preservation."""

from __future__ import annotations

import inspect
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from port_strategy_research import backtest_buy_logic
from port_strategy_research.research_backtest_market_adapter import (
    MarketDecision,
)
from port_strategy_research.strategy_profile_loader import (
    load_strategy_config_snapshot,
)
from port_strategy_research.strategy_profile_schema import (
    COMMON_DEFAULTS,
)


ROOT = Path(__file__).resolve().parent
snapshot = load_strategy_config_snapshot("RSCFG-0001")
resolved = snapshot.resolved_config

buy_guard_config = resolved["buy_guard"]
sizing_config = resolved["sizing"]
buy_config = resolved["buy"]
backtest_policy = resolved["backtest_policy"]

assert set(buy_guard_config) == set(COMMON_DEFAULTS["buy_guard"])
assert set(sizing_config) == set(COMMON_DEFAULTS["sizing"])
assert set(buy_config) == set(COMMON_DEFAULTS["buy"])
assert set(backtest_policy) == set(COMMON_DEFAULTS["backtest_policy"])

print("COMMON_DEFAULT_RUNTIME_KEY_ALIGNMENT=SUCCESS")

for key, default_value in COMMON_DEFAULTS["buy_guard"].items():
    assert key in buy_guard_config
    assert type(buy_guard_config[key]) is type(default_value), (
        f"BUY_GUARD_RUNTIME_TYPE_MISMATCH={key}:"
        f"{type(buy_guard_config[key]).__name__}!="
        f"{type(default_value).__name__}"
    )

print("COMMON_DEFAULT_RUNTIME_TYPE_ALIGNMENT=SUCCESS")

source = inspect.getsource(backtest_buy_logic)
assert "config={}" not in source
assert "config=buy_guard_config" in source
assert "sizing_config=sizing_config" in source

print("EMPTY_BUY_GUARD_CONFIG_REMOVED=SUCCESS")
print("BUY_GUARD_RUNTIME_CONFIG_SOURCE_WIRING=SUCCESS")

captured = {}


def fake_allocate_positions(
    buy_candidates,
    market_decision,
    *,
    sizing_config,
):
    captured["sizing_config"] = sizing_config

    candidate = dict(buy_candidates[0])
    candidate["position_size"] = 0.5
    return [candidate]


def fake_decide_buy_guard(
    *,
    stock,
    market,
    config,
):
    captured["buy_guard_config"] = config
    captured["guard_stock_ticker"] = stock.ticker_code
    captured["guard_market_signal"] = market.market_signal

    return SimpleNamespace(
        detail={
            "risk_flags": {
                "is_hot_chase": True,
                "is_buy_day_stop_risk": False,
                "is_mid_flow_tight_range_risk": True,
                "is_flow_0_9_plus_soft": True,
            }
        }
    )


def fake_apply_haircut(
    *,
    size,
    guard,
    config,
):
    captured["haircut_config"] = config
    captured["raw_size"] = size

    return (
        float(size) * 0.8,
        {
            "applied_reason": "high_flow_soft",
            "multiplier": 0.8,
        },
    )


backtest_buy_logic.allocate_positions = fake_allocate_positions
backtest_buy_logic.common_decide_buy_guard = fake_decide_buy_guard
backtest_buy_logic.common_apply_backtest_buy_size_haircut = (
    fake_apply_haircut
)

decision = MarketDecision(
    signal_type="AGGRESSIVE",
    base_exposure=Decimal("0.5"),
    max_positions=1,
    min_score=Decimal("0.1"),
    min_flow=Decimal("0.6"),
    reason="contract-test",
)

candidate = {
    "ticker_code": "000001",
    "ticker_name": "TEST",
    "final_score": 0.8,
    "flow_score": 0.95,
    "info_score": 0.7,
    "tape_score": 0.6,
    "short_pressure_score": 0.2,
    "volatility_20d": 0.02,
    "intraday_range": 0.03,
    "has_info_flag": True,
}

positions, bought_count, bought_returns = backtest_buy_logic.process_buy(
    conn=object(),
    positions={},
    candidates=[candidate],
    decision=decision,
    sold_today=set(),
    risk_off_flag=False,
    today="2026-08-05",
    company_map={"000001": "TEST"},
    price_map={
        "000001": {
            "open": 100,
            "low": 99,
            "close": 101,
        }
    },
    run_id=1,
    sizing_config=sizing_config,
    buy_guard_config=buy_guard_config,
    buy_config=buy_config,
    backtest_policy=backtest_policy,
    strategy_config_version=snapshot.strategy_config_version,
    config_hash=snapshot.config_hash,
)

assert captured["sizing_config"] is sizing_config
assert captured["buy_guard_config"] is buy_guard_config
assert captured["haircut_config"] is buy_guard_config

print("RESEARCH_BUY_GUARD_ACTUAL_CONFIG_IDENTITY=SUCCESS")
print("RESEARCH_BUY_HAIRCUT_ACTUAL_CONFIG_IDENTITY=SUCCESS")
print("RESEARCH_SIZING_CONFIG_IDENTITY=SUCCESS")

assert bought_count == 1
assert len(bought_returns) == 1
assert "000001" in positions

position = positions["000001"]
buy_info = position["entry_buy_info"]

assert abs(position["size"] - 0.4) < 1e-12
assert abs(bought_returns[0]["size"] - 0.4) < 1e-12

assert buy_info["is_hot_chase"] is True
assert buy_info["is_buy_day_stop_risk"] is False
assert buy_info["is_mid_flow_tight_range_risk"] is True
assert buy_info["is_flow_0_9_plus_soft"] is True
assert buy_info["size_haircut_reason"] == "high_flow_soft"
assert buy_info["size_haircut_multiplier"] == 0.8

print("GUARD_FLAG_PRESERVATION=SUCCESS")
print("HAIRCUT_RESULT_PRESERVATION=SUCCESS")
print("BUY_POSITION_SIZE_HAIRCUT_APPLIED=SUCCESS")
print("BUY_GUARD_CONFIG_REGRESSION_TEST=SUCCESS")
