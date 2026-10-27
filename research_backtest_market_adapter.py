"""Research Backtest Market Decision Adapter."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from port_strategy_common.common_context import CommonMarketContext
from port_strategy_common.common_market import common_decide_market


@dataclass
class MarketDecision:
    signal_type: str
    base_exposure: Decimal
    max_positions: int
    min_score: Decimal
    min_flow: Decimal
    reason: str


def d(value):
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def evaluate_market(
    market: dict,
    *,
    market_config: dict[str, Any],
) -> MarketDecision:
    """Calls the common market decision using the explicitly provided Market Config."""
    context = CommonMarketContext(
        trade_date=str(market.get("date", "TEST")),
        market_regime_score=float(
            d(market.get("market_regime_score"))
        ),
        breadth_pressure_score=float(
            d(market.get("breadth_pressure_score"))
        ),
        flow_pressure_score=float(
            d(market.get("flow_pressure_score"))
        ),
        macro_pressure_score=float(
            d(market.get("macro_pressure_score"))
        ),
        program_pressure_score=float(
            d(market.get("program_pressure_score"))
        ),
        raw=dict(market),
    )

    decision = common_decide_market(
        context,
        market_config,
    )

    return MarketDecision(
        signal_type=decision.market_signal,
        base_exposure=Decimal(str(decision.base_exposure)),
        max_positions=decision.max_positions,
        min_score=Decimal(str(decision.min_score)),
        min_flow=Decimal(str(decision.min_flow)),
        reason=decision.reason,
    )
