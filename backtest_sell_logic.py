"""공통 매도 판단 로직을 명시적 SELL Config로 연결한다."""

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
    """전달받은 SELL Config로 공통 매도 판단을 수행한다."""
    return common_evaluate_backtest_sell(
        pos=pos,
        feature=feature,
        decision=decision,
        raw_today_ret=raw_today_ret,
        today_ret=today_ret,
        config=sell_config,
    )
