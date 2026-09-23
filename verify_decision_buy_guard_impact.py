"""Verifies, without a DB, whether the Decision BUY Guard is affected by Research Config changes."""

from __future__ import annotations

import ast
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from port_strategy_common.common_buy_guard import common_decide_buy_guard
from port_strategy_common.common_buy_sizing import (
    common_apply_backtest_buy_size_haircut,
)
from port_strategy_common.common_context import CommonStockContext
from port_strategy_common.common_result import CommonMarketDecision
from port_strategy_decision import daily_buy_signal_run
from port_strategy_research.strategy_profile_loader import (
    load_strategy_config_snapshot,
)


DECISION_SOURCE = Path(daily_buy_signal_run.__file__).resolve()
source_text = DECISION_SOURCE.read_text(encoding="utf-8-sig")
tree = ast.parse(source_text)

empty_config_calls = []

for node in ast.walk(tree):
    if not isinstance(node, ast.Call):
        continue

    function_name = None
    if isinstance(node.func, ast.Name):
        function_name = node.func.id
    elif isinstance(node.func, ast.Attribute):
        function_name = node.func.attr

    if function_name not in {
        "common_decide_buy_guard",
        "common_apply_backtest_buy_size_haircut",
    }:
        continue

    for keyword in node.keywords:
        if (
            keyword.arg == "config"
            and isinstance(keyword.value, ast.Dict)
            and not keyword.value.keys
        ):
            empty_config_calls.append(
                (function_name, node.lineno)
            )

assert len(empty_config_calls) == 2, (
    "DECISION_EMPTY_CONFIG_CALL_COUNT_MISMATCH="
    f"{empty_config_calls}"
)

print(f"DECISION_SOURCE={DECISION_SOURCE}")
print("DECISION_BUY_GUARD_EMPTY_CONFIG_FOUND=SUCCESS")
print("DECISION_BUY_HAIRCUT_EMPTY_CONFIG_FOUND=SUCCESS")

captured = {}


def fake_guard(*, stock, market, config):
    captured["guard_config"] = config
    return SimpleNamespace(
        detail={
            "risk_flags": {
                "is_hot_chase": False,
            }
        }
    )


def fake_haircut(*, size, guard, config):
    captured["haircut_config"] = config
    return size, {
        "applied_reason": None,
        "multiplier": 1.0,
    }


original_guard = daily_buy_signal_run.common_decide_buy_guard
original_haircut = (
    daily_buy_signal_run.common_apply_backtest_buy_size_haircut
)

daily_buy_signal_run.common_decide_buy_guard = fake_guard
daily_buy_signal_run.common_apply_backtest_buy_size_haircut = (
    fake_haircut
)

try:
    decision = SimpleNamespace(
        signal_type="AGGRESSIVE",
        base_exposure=Decimal("0.8"),
        max_positions=5,
        min_score=Decimal("0.1"),
        min_flow=Decimal("0.6"),
        reason="impact-test",
    )

    positions = [
        {
            "ticker_code": "000001",
            "company_name": "TEST",
            "position_size": Decimal("0.5"),
            "final_score": Decimal("0.8"),
            "flow_score": Decimal("0.95"),
            "info_score": Decimal("0.7"),
            "tape_score": Decimal("0.6"),
            "short_pressure_score": Decimal("0.2"),
            "volatility_20d": Decimal("0.02"),
            "intraday_range": Decimal("0.03"),
        }
    ]

    result = daily_buy_signal_run.apply_daily_buy_toxic_haircut(
        positions,
        decision,
        "2026-08-05",
    )
finally:
    daily_buy_signal_run.common_decide_buy_guard = original_guard
    daily_buy_signal_run.common_apply_backtest_buy_size_haircut = (
        original_haircut
    )

assert captured["guard_config"] == {}
assert captured["haircut_config"] == {}
assert len(result) == 1

print("DECISION_BUY_GUARD_RUNTIME_EMPTY_CONFIG=SUCCESS")
print("DECISION_BUY_HAIRCUT_RUNTIME_EMPTY_CONFIG=SUCCESS")

snapshot = load_strategy_config_snapshot("RSCFG-0001")
research_guard_config = snapshot.resolved_config["buy_guard"]

stock = CommonStockContext(
    trade_date="2026-08-05",
    ticker_code="000001",
    ticker_name="TEST",
    final_score=0.8,
    flow_pressure_score=0.95,
    tape_score=0.6,
    short_pressure_score=0.2,
    volatility_score=0.02,
    intraday_range=0.03,
    raw={},
)

market = CommonMarketDecision(
    market_signal="AGGRESSIVE",
    base_exposure=0.8,
    max_positions=5,
    min_score=0.1,
    min_flow=0.6,
    reason="impact-test",
    detail={},
)

decision_guard = common_decide_buy_guard(
    stock=stock,
    market=market,
    config={},
)
research_guard = common_decide_buy_guard(
    stock=stock,
    market=market,
    config=research_guard_config,
)

decision_size, decision_haircut = (
    common_apply_backtest_buy_size_haircut(
        size=0.5,
        guard=decision_guard,
        config={},
    )
)
research_size, research_haircut = (
    common_apply_backtest_buy_size_haircut(
        size=0.5,
        guard=research_guard,
        config=research_guard_config,
    )
)

decision_flags = decision_guard.detail.get(
    "risk_flags",
    {},
)
research_flags = research_guard.detail.get(
    "risk_flags",
    {},
)

same_flags = decision_flags == research_flags
same_size = abs(
    float(decision_size) - float(research_size)
) < 1e-12
same_haircut = decision_haircut == research_haircut

print(f"DECISION_GUARD_FLAGS={decision_flags}")
print(f"RESEARCH_GUARD_FLAGS={research_flags}")
print(f"DECISION_HAIRCUT={decision_haircut}")
print(f"RESEARCH_HAIRCUT={research_haircut}")
print(f"DECISION_SIZE={decision_size}")
print(f"RESEARCH_SIZE={research_size}")
print(f"DECISION_RESEARCH_FLAGS_EQUAL={same_flags}")
print(f"DECISION_RESEARCH_HAIRCUT_EQUAL={same_haircut}")
print(f"DECISION_RESEARCH_SIZE_EQUAL={same_size}")

assert DECISION_SOURCE.parent.name == "port_strategy_decision"
assert captured["guard_config"] is not research_guard_config
assert captured["haircut_config"] is not research_guard_config

print("RESEARCH_CHANGE_DOES_NOT_INJECT_CONFIG_INTO_DECISION=SUCCESS")
print("DECISION_REMAINS_COMMON_INTERNAL_DEFAULT_CONSUMER=SUCCESS")
print("DECISION_BUY_GUARD_IMPACT_VERIFY=SUCCESS")
