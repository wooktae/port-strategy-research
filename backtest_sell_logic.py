"""공통 매도 판단 로직을 백테스트 포지션 구조에 연결하는 wrapper 모듈."""

from __future__ import annotations

from port_strategy_common.config import SELL_CONFIG
from port_strategy_common.common_sell_decision import common_evaluate_backtest_sell


CFG = SELL_CONFIG


def evaluate_sell(
    pos,
    feature,
    decision,
    raw_today_ret,
    today_ret,
):
    """포지션과 당일 종목 feature를 common sell decision으로 평가한다."""
    return common_evaluate_backtest_sell(
        pos=pos,
        feature=feature,
        decision=decision,
        raw_today_ret=raw_today_ret,
        today_ret=today_ret,
        config=CFG,
    )
