from port_strategy_research.backtest_sell_logic import evaluate_sell
from port_strategy_research.backtest_trade_log import insert_trade_log
from port_strategy_common.utils import to_float
from port_strategy_common.config import GENERAL_CONFIG, SELL_CONFIG


INTRADAY_STOP_LOSS = float(SELL_CONFIG["existing_position_intraday_stop_loss"])


def normalize_return(v: float) -> float:
    raw = to_float(v, 0.0)
    if GENERAL_CONFIG["use_return_floor"]:
        return max(raw, float(GENERAL_CONFIG["return_floor"]))
    return raw


def _valid_price(price: dict) -> bool:
    if not price:
        return False
    return bool(price.get("open")) and bool(price.get("low")) and bool(price.get("close"))


def build_entry_buy_info_from_position(pos: dict) -> dict:
    """
    신규 구조(entry_buy_info)를 우선 사용하고,
    과거 포지션/호환성을 위해 구형 3필드 구조로 fallback.
    """
    entry_buy_info = pos.get("entry_buy_info")
    if isinstance(entry_buy_info, dict) and entry_buy_info:
        return entry_buy_info

    return {
        "score": to_float(pos.get("entry_final_score"), 0.0),
        "flow": to_float(pos.get("entry_flow_score"), 0.0),
        "info": to_float(pos.get("entry_info_score"), 0.0),
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
):
    sold_returns = []
    held_returns = []

    prev_positions = set(positions.keys())
    new_positions = {}

    stock_map = {s["ticker_code"]: s for s in stocks}
    sold_count_today = 0

    for ticker, pos in positions.items():
        feature = stock_map.get(ticker)
        price = price_map.get(ticker)

        if not feature or not _valid_price(price):
            new_positions[ticker] = pos
            continue

        prev_close = to_float(pos.get("prev_close"), 0.0)
        close_price = to_float(price.get("close"), 0.0)
        low_price = to_float(price.get("low"), 0.0)

        if prev_close <= 0 or close_price <= 0 or low_price <= 0:
            new_positions[ticker] = pos
            continue

        raw_today_ret = (close_price / prev_close) - 1
        today_ret = normalize_return(raw_today_ret)
        low_ret = (low_price / prev_close) - 1

        prev_cum = to_float(pos.get("cum_return"), 0.0)
        next_holding_days = int(pos.get("holding_days", 0)) + 1

        buy_info = build_entry_buy_info_from_position(pos)

        if low_ret <= INTRADAY_STOP_LOSS:
            stop_ret = INTRADAY_STOP_LOSS
            stop_cum_return = ((1 + prev_cum) * (1 + stop_ret)) - 1

            insert_trade_log(
                conn,
                {
                    "ticker_code": ticker,
                    "buy_date": pos["buy_date"],
                    "sell_date": execution_date,
                    "holding_period": next_holding_days,
                    "return_pct": f"{stop_cum_return * 100:.2f}%",
                    "buy_info": buy_info,
                    "sell_info": {
                        "reason": "intraday_stop",
                        "low_ret": low_ret,
                        "raw_today_ret": raw_today_ret,
                        "cum_return": stop_cum_return,
                    },
                    "buy_open_price": pos.get("entry_open_price"),
                    "buy_close_price": pos.get("entry_close_price"),
                    "buy_low_price": pos.get("entry_low_price"),
                    "sell_open_price": to_float(price.get("open"), None),
                    "sell_close_price": close_price,
                    "sell_low_price": low_price,
                },
                company_map,
                run_id,
            )

            sold_returns.append(
                {"ticker": ticker, "ret": stop_ret, "size": pos.get("size", 0.0)}
            )
            sold_count_today += 1
            continue

        result = evaluate_sell(
            pos=pos,
            feature=feature,
            decision=decision,
            raw_today_ret=raw_today_ret,
            today_ret=today_ret,
        )

        if result["sell_flag"]:
            insert_trade_log(
                conn,
                {
                    "ticker_code": ticker,
                    "buy_date": pos["buy_date"],
                    "sell_date": execution_date,
                    "holding_period": result["holding_days"],
                    "return_pct": f"{result['cum_return'] * 100:.2f}%",
                    "buy_info": buy_info,
                    "sell_info": {
                        "reason": result["sell_reason"],
                        "flow": result["flow"],
                        "final": result["final_score"],
                        "short": result["short"],
                        "raw_today_ret": result["raw_today_ret"],
                        "cum_return": result["cum_return"],
                    },
                    "buy_open_price": pos.get("entry_open_price"),
                    "buy_close_price": pos.get("entry_close_price"),
                    "buy_low_price": pos.get("entry_low_price"),
                    "sell_open_price": to_float(price.get("open"), None),
                    "sell_close_price": close_price,
                    "sell_low_price": low_price,
                },
                company_map,
                run_id,
            )

            sold_returns.append(
                {"ticker": ticker, "ret": result["today_ret"], "size": pos.get("size", 0.0)}
            )
            sold_count_today += 1
            continue

        held_returns.append({"ticker": ticker, "ret": today_ret, "size": pos.get("size", 0.0)})

        new_positions[ticker] = {
            **pos,
            "holding_days": result["holding_days"],
            "cum_return": result["cum_return"],
            "prev_close": close_price,
        }

    positions = new_positions
    sold_today = prev_positions - set(positions.keys())

    return positions, sold_today, sold_count_today, sold_returns, held_returns