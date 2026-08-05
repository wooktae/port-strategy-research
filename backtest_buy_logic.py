"""백테스트 신규 매수 처리 로직 모듈."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import Any

from port_strategy_common.common_buy_guard import (
    common_decide_buy_guard,
)
from port_strategy_common.common_buy_sizing import (
    common_apply_backtest_buy_size_haircut,
)
from port_strategy_common.common_context import CommonStockContext
from port_strategy_common.common_result import CommonMarketDecision
from port_strategy_common.common_utils import common_safe_float
from port_strategy_research.backtest_trade_log import insert_trade_log
from port_strategy_research.research_backtest_sizing_adapter import (
    allocate_positions,
)


def normalize_return(
    value: float,
    *,
    backtest_policy: dict[str, Any],
) -> float:
    if backtest_policy["use_return_floor"]:
        return max(
            float(value),
            float(backtest_policy["return_floor"]),
        )
    return float(value)


def _valid_price(price: dict) -> bool:
    if not price:
        return False
    return (
        bool(price.get("open"))
        and bool(price.get("low"))
        and bool(price.get("close"))
    )


def build_buy_info(point: dict, decision) -> dict:
    def safe_float(value, default=0.0):
        try:
            return float(value) if value is not None else default
        except Exception:
            return default

    return {
        "score": safe_float(point.get("final_score")),
        "flow": safe_float(point.get("flow_score")),
        "info": safe_float(point.get("info_score")),
        "tape": safe_float(point.get("tape_score")),
        "short": safe_float(
            point.get("short_pressure_score")
        ),
        "vol": safe_float(point.get("volatility_20d")),
        "intraday_range": safe_float(
            point.get("intraday_range")
        ),
        "has_info_flag": bool(
            point.get("has_info_flag", False)
        ),
        "entry_market_signal": str(decision.signal_type),
    }


def _to_common_market_decision(decision) -> CommonMarketDecision:
    return CommonMarketDecision(
        market_signal=str(decision.signal_type),
        base_exposure=float(decision.base_exposure),
        max_positions=int(decision.max_positions),
        min_score=float(decision.min_score),
        min_flow=float(decision.min_flow),
        reason=str(decision.reason),
        detail={},
    )


def _to_common_stock_context(
    point: dict,
    today,
) -> CommonStockContext:
    return CommonStockContext(
        trade_date=str(today),
        ticker_code=str(point.get("ticker_code", "")),
        ticker_name=point.get(
            "ticker_name",
            point.get("stock_name"),
        ),
        final_score=common_safe_float(
            point.get("final_score"),
            0.0,
        ),
        flow_pressure_score=common_safe_float(
            point.get("flow_score"),
            0.0,
        ),
        tape_score=common_safe_float(
            point.get("tape_score"),
            0.0,
        ),
        short_pressure_score=common_safe_float(
            point.get("short_pressure_score"),
            0.0,
        ),
        volatility_score=common_safe_float(
            point.get("volatility_20d"),
            0.0,
        ),
        intraday_range=common_safe_float(
            point.get("intraday_range"),
            0.0,
        ),
        raw=dict(point),
    )


def process_buy(
    conn,
    positions,
    candidates,
    decision,
    sold_today,
    risk_off_flag,
    today,
    company_map,
    price_map,
    run_id,
    *,
    sizing_config: dict[str, Any],
    buy_guard_config: dict[str, Any],
    buy_config: dict[str, Any],
    backtest_policy: dict[str, Any],
    strategy_config_version: str,
    config_hash: str,
):
    """명시적으로 전달된 실행 Config로 신규 매수를 처리한다."""
    current_position_count = len(positions)
    available_slots = max(
        0,
        decision.max_positions - current_position_count,
    )

    current_exposure = sum(
        Decimal(str(position.get("size", 0)))
        for position in positions.values()
    )

    if risk_off_flag:
        adjusted_exposure = (
            decision.base_exposure
            * backtest_policy[
                "risk_off_exposure_multiplier"
            ]
        )
    else:
        adjusted_exposure = decision.base_exposure

    remaining_exposure = adjusted_exposure - current_exposure
    if remaining_exposure < Decimal("0"):
        remaining_exposure = Decimal("0")

    candidate_pool = []
    for row in candidates:
        ticker = row["ticker_code"]
        if ticker in positions:
            continue
        if (
            not backtest_policy[
                "allow_reentry_after_sell_same_day"
            ]
            and ticker in sold_today
        ):
            continue
        if not _valid_price(price_map.get(ticker)):
            continue
        candidate_pool.append(row)

    bought_count_today = 0
    bought_returns = []

    if (
        available_slots > 0
        and remaining_exposure > Decimal("0")
        and candidate_pool
    ):
        alloc_decision = replace(
            decision,
            base_exposure=remaining_exposure,
            max_positions=available_slots,
        )
        new_positions_today = allocate_positions(
            candidate_pool,
            alloc_decision,
            sizing_config=sizing_config,
        )

        for point in new_positions_today[:available_slots]:
            ticker = point["ticker_code"]
            price = price_map.get(ticker)

            open_price = float(price["open"])
            low_price = float(price["low"])
            close_price = float(price["close"])
            size = float(point["position_size"])

            buy_info = build_buy_info(point, decision)
            common_market_decision = _to_common_market_decision(
                decision
            )
            common_stock_context = _to_common_stock_context(
                point,
                today,
            )

            buy_guard = common_decide_buy_guard(
                stock=common_stock_context,
                market=common_market_decision,
                config=buy_guard_config,
            )

            size, haircut_info = (
                common_apply_backtest_buy_size_haircut(
                    size=size,
                    guard=buy_guard,
                    config=buy_guard_config,
                )
            )

            risk_flags = buy_guard.detail.get(
                "risk_flags",
                {},
            )

            buy_info["position_size"] = size
            buy_info["is_hot_chase"] = bool(
                risk_flags.get(
                    "is_hot_chase",
                    risk_flags.get("hot_chase", False),
                )
            )
            buy_info["is_buy_day_stop_risk"] = bool(
                risk_flags.get(
                    "is_buy_day_stop_risk",
                    risk_flags.get(
                        "buy_day_stop_risk",
                        False,
                    ),
                )
            )
            buy_info["is_mid_flow_tight_range_risk"] = bool(
                risk_flags.get(
                    "is_mid_flow_tight_range_risk",
                    risk_flags.get(
                        "mid_flow_tight_range_risk",
                        False,
                    ),
                )
            )
            buy_info["is_flow_0_9_plus_soft"] = bool(
                risk_flags.get(
                    "is_flow_0_9_plus_soft",
                    risk_flags.get(
                        "flow_0_9_plus_soft",
                        False,
                    ),
                )
            )
            buy_info["size_haircut_reason"] = (
                haircut_info.get("applied_reason")
            )
            buy_info["size_haircut_multiplier"] = (
                haircut_info.get("multiplier")
            )

            intraday_stop_loss = float(
                buy_config["buy_day_intraday_stop_loss"]
            )
            low_ret = (low_price / open_price) - 1
            raw_day_ret = (close_price / open_price) - 1
            day_ret = normalize_return(
                raw_day_ret,
                backtest_policy=backtest_policy,
            )
            bought_count_today += 1

            if low_ret <= intraday_stop_loss:
                insert_trade_log(
                    conn,
                    {
                        "ticker_code": ticker,
                        "buy_date": today,
                        "sell_date": today,
                        "holding_period": 0,
                        "return_pct": (
                            f"{intraday_stop_loss * 100:.2f}%"
                        ),
                        "buy_info": buy_info,
                        "sell_info": {
                            "reason": "buy_day_intraday_stop",
                            "low_ret": low_ret,
                            "raw_today_ret": raw_day_ret,
                            "cum_return": intraday_stop_loss,
                        },
                        "buy_open_price": open_price,
                        "buy_close_price": close_price,
                        "buy_low_price": low_price,
                        "sell_open_price": open_price,
                        "sell_close_price": close_price,
                        "sell_low_price": low_price,
                    },
                    company_map,
                    run_id,
                    strategy_config_version=strategy_config_version,
                    config_hash=config_hash,
                )

                bought_returns.append(
                    {
                        "ticker": ticker,
                        "ret": intraday_stop_loss,
                        "size": size,
                    }
                )
                continue

            bought_returns.append(
                {
                    "ticker": ticker,
                    "ret": day_ret,
                    "size": size,
                }
            )
            positions[ticker] = {
                "size": size,
                "buy_date": today,
                "holding_days": 0,
                "cum_return": day_ret,
                "entry_final_score": buy_info["score"],
                "entry_flow_score": buy_info["flow"],
                "entry_info_score": buy_info["info"],
                "entry_buy_info": buy_info,
                "entry_open_price": open_price,
                "entry_close_price": close_price,
                "entry_low_price": low_price,
                "prev_close": close_price,
            }

    return (
        positions,
        bought_count_today,
        bought_returns,
    )
