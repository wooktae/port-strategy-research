"""백테스트 기존 포지션 처리 모듈."""

from __future__ import annotations

from typing import Any

from port_strategy_common.utils import to_float
from port_strategy_research.backtest_sell_logic import evaluate_sell
from port_strategy_research.backtest_trade_log import insert_trade_log


def normalize_return(
    value: float,
    *,
    backtest_policy: dict[str, Any],
) -> float:
    raw = to_float(value, 0.0)
    if backtest_policy["use_return_floor"]:
        return max(
            raw,
            float(backtest_policy["return_floor"]),
        )
    return raw


def _valid_price(price: dict) -> bool:
    if not price:
        return False
    return (
        bool(price.get("open"))
        and bool(price.get("low"))
        and bool(price.get("close"))
    )


def build_entry_buy_info_from_position(
    position: dict,
) -> dict:
    """신규 Entry 정보 우선, 구형 3필드 구조를 Fallback한다."""
    entry_buy_info = position.get("entry_buy_info")
    if isinstance(entry_buy_info, dict) and entry_buy_info:
        return entry_buy_info

    return {
        "score": to_float(
            position.get("entry_final_score"),
            0.0,
        ),
        "flow": to_float(
            position.get("entry_flow_score"),
            0.0,
        ),
        "info": to_float(
            position.get("entry_info_score"),
            0.0,
        ),
    }


def process_existing_positions(
    conn,
    positions,
    stocks,
    decision,
    company_map,
    execution_date,
    price_map,
    run_id,
    *,
    sell_config: dict[str, Any],
    backtest_policy: dict[str, Any],
    strategy_config_version: str,
    config_hash: str,
):
    """명시적 SELL·Backtest Policy Config로 기존 포지션을 처리한다."""
    sold_returns = []
    held_returns = []

    prev_positions = set(positions.keys())
    new_positions = {}

    stock_map = {
        stock["ticker_code"]: stock
        for stock in stocks
    }
    sold_count_today = 0
    intraday_stop_loss = float(
        sell_config["existing_position_intraday_stop_loss"]
    )

    for ticker, position in positions.items():
        feature = stock_map.get(ticker)
        price = price_map.get(ticker)

        if not feature or not _valid_price(price):
            new_positions[ticker] = position
            continue

        prev_close = to_float(
            position.get("prev_close"),
            0.0,
        )
        close_price = to_float(
            price.get("close"),
            0.0,
        )
        low_price = to_float(
            price.get("low"),
            0.0,
        )

        if (
            prev_close <= 0
            or close_price <= 0
            or low_price <= 0
        ):
            new_positions[ticker] = position
            continue

        raw_today_ret = (close_price / prev_close) - 1
        today_ret = normalize_return(
            raw_today_ret,
            backtest_policy=backtest_policy,
        )
        low_ret = (low_price / prev_close) - 1

        prev_cum = to_float(
            position.get("cum_return"),
            0.0,
        )
        next_holding_days = (
            int(position.get("holding_days", 0)) + 1
        )

        buy_info = build_entry_buy_info_from_position(
            position
        )

        if low_ret <= intraday_stop_loss:
            stop_ret = intraday_stop_loss
            stop_cum_return = (
                (1 + prev_cum) * (1 + stop_ret)
            ) - 1

            insert_trade_log(
                conn,
                {
                    "ticker_code": ticker,
                    "buy_date": position["buy_date"],
                    "sell_date": execution_date,
                    "holding_period": next_holding_days,
                    "return_pct": (
                        f"{stop_cum_return * 100:.2f}%"
                    ),
                    "buy_info": buy_info,
                    "sell_info": {
                        "reason": "intraday_stop",
                        "low_ret": low_ret,
                        "raw_today_ret": raw_today_ret,
                        "cum_return": stop_cum_return,
                    },
                    "buy_open_price": position.get(
                        "entry_open_price"
                    ),
                    "buy_close_price": position.get(
                        "entry_close_price"
                    ),
                    "buy_low_price": position.get(
                        "entry_low_price"
                    ),
                    "sell_open_price": to_float(
                        price.get("open"),
                        None,
                    ),
                    "sell_close_price": close_price,
                    "sell_low_price": low_price,
                },
                company_map,
                run_id,
                strategy_config_version=strategy_config_version,
                config_hash=config_hash,
            )

            sold_returns.append(
                {
                    "ticker": ticker,
                    "ret": stop_ret,
                    "size": position.get("size", 0.0),
                }
            )
            sold_count_today += 1
            continue

        result = evaluate_sell(
            pos=position,
            feature=feature,
            decision=decision,
            raw_today_ret=raw_today_ret,
            today_ret=today_ret,
            sell_config=sell_config,
        )

        if result["sell_flag"]:
            insert_trade_log(
                conn,
                {
                    "ticker_code": ticker,
                    "buy_date": position["buy_date"],
                    "sell_date": execution_date,
                    "holding_period": result[
                        "holding_days"
                    ],
                    "return_pct": (
                        f"{result['cum_return'] * 100:.2f}%"
                    ),
                    "buy_info": buy_info,
                    "sell_info": {
                        "reason": result["sell_reason"],
                        "flow": result["flow"],
                        "final": result["final_score"],
                        "short": result["short"],
                        "raw_today_ret": result[
                            "raw_today_ret"
                        ],
                        "cum_return": result["cum_return"],
                    },
                    "buy_open_price": position.get(
                        "entry_open_price"
                    ),
                    "buy_close_price": position.get(
                        "entry_close_price"
                    ),
                    "buy_low_price": position.get(
                        "entry_low_price"
                    ),
                    "sell_open_price": to_float(
                        price.get("open"),
                        None,
                    ),
                    "sell_close_price": close_price,
                    "sell_low_price": low_price,
                },
                company_map,
                run_id,
                strategy_config_version=strategy_config_version,
                config_hash=config_hash,
            )

            sold_returns.append(
                {
                    "ticker": ticker,
                    "ret": result["today_ret"],
                    "size": position.get("size", 0.0),
                }
            )
            sold_count_today += 1
            continue

        held_returns.append(
            {
                "ticker": ticker,
                "ret": today_ret,
                "size": position.get("size", 0.0),
            }
        )

        new_positions[ticker] = {
            **position,
            "holding_days": result["holding_days"],
            "cum_return": result["cum_return"],
            "prev_close": close_price,
        }

    positions = new_positions
    sold_today = prev_positions - set(positions.keys())

    return (
        positions,
        sold_today,
        sold_count_today,
        sold_returns,
        held_returns,
    )
