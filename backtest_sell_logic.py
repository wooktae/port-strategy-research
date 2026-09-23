"""Wires the common sell decision logic to an explicit SELL Config."""

from __future__ import annotations

from typing import Any

from port_strategy_common.common_sell_decision import (
    common_evaluate_backtest_sell,
)


def evaluate_sell(
    pos,
    feature,
    decision,
    raw_today_ret,
    today_ret,
    *,
    sell_config: dict[str, Any],
):
    """Performs the common sell decision using the provided SELL Config."""
    return common_evaluate_backtest_sell(
        pos=pos,
        feature=feature,
        decision=decision,
        raw_today_ret=raw_today_ret,
        today_ret=today_ret,
        config=sell_config,
    )
