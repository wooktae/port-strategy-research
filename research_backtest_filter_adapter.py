"""Research Backtest Buy Candidate Filter Adapter."""

from __future__ import annotations

from typing import Any

from port_strategy_common.common_buy_filter import (
    common_filter_buy_candidates,
)
from port_strategy_common.common_result import CommonMarketDecision


def filter_buy_candidates(
    stock_rows,
    decision,
    *,
    filter_config: dict[str, Any],
):
    """명시적으로 받은 Filter Config로 공통 후보 필터를 호출한다."""
    common_decision = CommonMarketDecision(
        market_signal=decision.signal_type,
        base_exposure=float(decision.base_exposure),
        max_positions=decision.max_positions,
        min_score=float(decision.min_score),
        min_flow=float(decision.min_flow),
        reason=decision.reason,
        detail={},
    )

    return common_filter_buy_candidates(
        stock_rows=stock_rows,
        decision=common_decision,
        config=filter_config,
    )
