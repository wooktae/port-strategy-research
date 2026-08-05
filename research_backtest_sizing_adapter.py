"""Research Backtest Buy Candidate Sizing Adapter."""

from __future__ import annotations

from typing import Any

from port_strategy_common.common_buy_sizing import (
    common_allocate_positions,
)
from port_strategy_common.common_result import CommonMarketDecision


def allocate_positions(
    buy_candidates,
    market_decision,
    *,
    sizing_config: dict[str, Any],
):
    """명시적으로 받은 Sizing Config로 포지션 크기를 산출한다."""
    common_decision = CommonMarketDecision(
        market_signal=market_decision.signal_type,
        base_exposure=float(market_decision.base_exposure),
        max_positions=market_decision.max_positions,
        min_score=float(market_decision.min_score),
        min_flow=float(market_decision.min_flow),
        reason=market_decision.reason,
        detail={},
    )

    return common_allocate_positions(
        buy_candidates=buy_candidates,
        market_decision=common_decision,
        config=sizing_config,
    )
