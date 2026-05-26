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
    return common_evaluate_backtest_sell(
        pos=pos,
        feature=feature,
        decision=decision,
        raw_today_ret=raw_today_ret,
        today_ret=today_ret,
        config=CFG,
    )