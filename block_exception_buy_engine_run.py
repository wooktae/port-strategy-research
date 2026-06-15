"""block 장세 예외 매수 전략을 백테스트 엔진 흐름으로 검증하는 연구 스크립트.

기존 백테스트 loader/position/buy 저장 흐름을 재사용하며 run 생성, daily 저장, 분석 저장이 가능하다.
실행 시 DB write와 commit이 발생할 수 있으므로 문서화 작업에서는 직접 실행하지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from port_strategy_common.config import ENGINE_VERSION, GENERAL_CONFIG
from port_strategy_common.utils import to_float

from port_strategy_research.backtest_loader import (
    get_dates,
    get_market,
    get_stocks,
    get_price,
    load_stock_universe,
)

from port_strategy_research.research_backtest_market_adapter import evaluate_market
from port_strategy_research.research_backtest_filter_adapter import filter_buy_candidates

from port_strategy_research.backtest_position_manager import process_existing_positions
from port_strategy_research.backtest_buy_logic import process_buy
from port_strategy_research.backtest_metrics import calculate_mdd, calculate_sharpe
from port_strategy_research.backtest_run_store import (
    ensure_run_tables,
    create_run,
    insert_daily_result,
    finalize_run,
)

from port_strategy_research.db_config import get_db_config
import psycopg2


# ============================================================
# Experiment Config
# ============================================================

EXPERIMENT_VERSION = "BLOCK_EXCEPTION_BUY_V1"

BLOCK_EXCEPTION_MIN_FLOW_SCORE = 0.90
BLOCK_EXCEPTION_MIN_FINAL_SCORE = 0.60
BLOCK_EXCEPTION_MAX_VOLATILITY_20D = 0.08
BLOCK_EXCEPTION_MIN_INTRADAY_RANGE = 0.05
BLOCK_EXCEPTION_MAX_INTRADAY_RANGE = 0.08

BLOCK_EXCEPTION_MAX_BUY_PER_DAY = 2
BLOCK_EXCEPTION_POSITION_SIZE = 0.10
BLOCK_EXCEPTION_MAX_OPEN_POSITIONS = 4


# ============================================================
# Utils
# ============================================================

def get_conn():
    return psycopg2.connect(**get_db_config())


def print_section(title: str) -> None:
    print()
    print("========================================")
    print(f"[{title}]")
    print("========================================")


def is_valid_price(price: Optional[dict]) -> bool:
    if not price:
        return False

    return bool(price.get("open")) and bool(price.get("low")) and bool(price.get("close"))


def as_float(value: Any, default: float = 0.0) -> float:
    return to_float(value, default)


def get_stock_value(stock: dict, key: str, default: float = 0.0) -> float:
    return as_float(stock.get(key), default)


# ============================================================
# BLOCK Exception Candidate Logic
# ============================================================

def is_block_exception_candidate(stock: dict) -> bool:
    flow_score = get_stock_value(stock, "flow_score")
    final_score = get_stock_value(stock, "final_score")
    volatility_20d = get_stock_value(stock, "volatility_20d")
    intraday_range = get_stock_value(stock, "intraday_range")

    if flow_score < BLOCK_EXCEPTION_MIN_FLOW_SCORE:
        return False

    if final_score < BLOCK_EXCEPTION_MIN_FINAL_SCORE:
        return False

    if volatility_20d > BLOCK_EXCEPTION_MAX_VOLATILITY_20D:
        return False

    if intraday_range < BLOCK_EXCEPTION_MIN_INTRADAY_RANGE:
        return False

    if intraday_range > BLOCK_EXCEPTION_MAX_INTRADAY_RANGE:
        return False

    return True


def build_block_exception_candidates(stocks: List[dict]) -> List[dict]:
    candidates = [
        stock for stock in stocks
        if is_block_exception_candidate(stock)
    ]

    # v0에서 후보 quality가 좋았던 구간을 그대로 사용하되,
    # 엔진 통합 v1에서는 final_score DESC, flow_score DESC 우선.
    return sorted(
        candidates,
        key=lambda s: (
            get_stock_value(s, "final_score"),
            get_stock_value(s, "flow_score"),
            get_stock_value(s, "intraday_range"),
        ),
        reverse=True,
    )


def build_entry_buy_info(stock: dict) -> dict:
    return {
        "source": EXPERIMENT_VERSION,
        "score": get_stock_value(stock, "final_score"),
        "flow": get_stock_value(stock, "flow_score"),
        "info": get_stock_value(stock, "info_score"),
        "volatility_20d": get_stock_value(stock, "volatility_20d"),
        "intraday_range": get_stock_value(stock, "intraday_range"),
        "short_pressure_score": get_stock_value(stock, "short_pressure_score"),
        "criteria": {
            "min_flow_score": BLOCK_EXCEPTION_MIN_FLOW_SCORE,
            "min_final_score": BLOCK_EXCEPTION_MIN_FINAL_SCORE,
            "max_volatility_20d": BLOCK_EXCEPTION_MAX_VOLATILITY_20D,
            "min_intraday_range": BLOCK_EXCEPTION_MIN_INTRADAY_RANGE,
            "max_intraday_range": BLOCK_EXCEPTION_MAX_INTRADAY_RANGE,
            "position_size": BLOCK_EXCEPTION_POSITION_SIZE,
            "max_buy_per_day": BLOCK_EXCEPTION_MAX_BUY_PER_DAY,
            "max_open_positions": BLOCK_EXCEPTION_MAX_OPEN_POSITIONS,
        },
    }


def process_block_exception_buy(
    *,
    positions: Dict[str, dict],
    candidates: List[dict],
    price_map: Dict[str, dict],
    sold_today: set,
    execution_date: str,
    company_map: Dict[str, str],
) -> Tuple[Dict[str, dict], int, List[dict]]:
    """
    BLOCK_EXCEPTION_BUY_V1 전용 매수 처리.

    기존 process_buy()를 직접 수정하지 않고,
    BLOCK일 때만 별도 예외 매수 포지션을 생성한다.

    주의:
    - 기존 process_existing_positions()는 그대로 사용한다.
    - 매도는 기존 sell logic / intraday stop을 그대로 탄다.
    - trade_log insert는 매도 시점에 process_existing_positions()가 처리한다.
    """
    bought_returns: List[dict] = []
    bought_count = 0

    if len(positions) >= BLOCK_EXCEPTION_MAX_OPEN_POSITIONS:
        return positions, bought_count, bought_returns

    for stock in candidates:
        ticker = stock["ticker_code"]

        if bought_count >= BLOCK_EXCEPTION_MAX_BUY_PER_DAY:
            break

        if len(positions) >= BLOCK_EXCEPTION_MAX_OPEN_POSITIONS:
            break

        if ticker in positions:
            continue

        if ticker in sold_today:
            continue

        price = price_map.get(ticker)

        if not is_valid_price(price):
            continue

        open_price = as_float(price.get("open"), 0.0)
        low_price = as_float(price.get("low"), 0.0)
        close_price = as_float(price.get("close"), 0.0)

        if close_price <= 0:
            continue

        entry_buy_info = build_entry_buy_info(stock)

        positions[ticker] = {
            "ticker_code": ticker,
            "buy_date": execution_date,
            "holding_days": 0,
            "cum_return": 0.0,
            "prev_close": close_price,
            "size": BLOCK_EXCEPTION_POSITION_SIZE,

            # 기존 position_manager / trade_log 호환용
            "entry_final_score": entry_buy_info["score"],
            "entry_flow_score": entry_buy_info["flow"],
            "entry_info_score": entry_buy_info["info"],
            "entry_buy_info": entry_buy_info,

            "entry_open_price": open_price,
            "entry_close_price": close_price,
            "entry_low_price": low_price,

            # 실험 추적용
            "entry_source": EXPERIMENT_VERSION,
            "company_name": company_map.get(ticker, ""),
        }

        # 기존 엔진과 동일하게 매수 당일 수익률은 0으로 처리
        bought_returns.append(
            {
                "ticker": ticker,
                "ret": 0.0,
                "size": BLOCK_EXCEPTION_POSITION_SIZE,
            }
        )

        bought_count += 1

    return positions, bought_count, bought_returns


# ============================================================
# Engine
# ============================================================

def run_block_exception_engine_backtest(conn, run_id: str) -> List[dict]:
    """block 예외 매수 조건을 적용한 백테스트 루프를 실행하고 history를 반환한다."""
    print_section("BLOCK_EXCEPTION_BUY_V1 Engine Backtest")
    print(f"ENGINE_VERSION     : {ENGINE_VERSION}")
    print(f"EXPERIMENT_VERSION : {EXPERIMENT_VERSION}")
    print(f"min_flow_score     : {BLOCK_EXCEPTION_MIN_FLOW_SCORE}")
    print(f"min_final_score    : {BLOCK_EXCEPTION_MIN_FINAL_SCORE}")
    print(f"max_volatility_20d : {BLOCK_EXCEPTION_MAX_VOLATILITY_20D}")
    print(f"range              : {BLOCK_EXCEPTION_MIN_INTRADAY_RANGE} ~ {BLOCK_EXCEPTION_MAX_INTRADAY_RANGE}")
    print(f"max_buy_per_day    : {BLOCK_EXCEPTION_MAX_BUY_PER_DAY}")
    print(f"position_size      : {BLOCK_EXCEPTION_POSITION_SIZE}")
    print(f"max_open_positions : {BLOCK_EXCEPTION_MAX_OPEN_POSITIONS}")

    dates = get_dates(conn)
    total_return = 1.0
    history: List[dict] = []
    positions: Dict[str, dict] = {}
    risk_off_flag = False
    company_map = load_stock_universe(conn)

    for i in range(len(dates) - 1):
        today = str(dates[i])
        tomorrow = str(dates[i + 1])

        market = get_market(conn, today)
        stocks = get_stocks(conn, today)

        decision = evaluate_market(market)

        price_tomorrow_df = get_price(conn, tomorrow)
        price_tomorrow_map = {
            row["ticker_code"]: {
                "open": row["open_price"],
                "low": row["low_price"],
                "close": row["close_price"],
            }
            for _, row in price_tomorrow_df.iterrows()
        }

        positions, sold_today, sold_count_today, sold_returns, held_returns = process_existing_positions(
            conn=conn,
            positions=positions,
            stocks=stocks,
            decision=decision,
            company_map=company_map,
            execution_date=tomorrow,
            price_map=price_tomorrow_map,
            run_id=run_id,
        )

        bought_count_today = 0
        exception_bought_count_today = 0
        bought_returns: List[dict] = []
        exception_bought_returns: List[dict] = []

        if decision.signal_type == "BLOCK":
            exception_candidates = build_block_exception_candidates(stocks)

            positions, exception_bought_count_today, exception_bought_returns = process_block_exception_buy(
                positions=positions,
                candidates=exception_candidates,
                price_map=price_tomorrow_map,
                sold_today=sold_today,
                execution_date=tomorrow,
                company_map=company_map,
            )

            bought_count_today = exception_bought_count_today
            bought_returns = exception_bought_returns

        else:
            # BLOCK이 아닐 때는 기존 전략 그대로 사용한다.
            candidates = filter_buy_candidates(stocks, decision)

            positions, bought_count_today, bought_returns = process_buy(
                conn=conn,
                positions=positions,
                candidates=candidates,
                decision=decision,
                sold_today=sold_today,
                risk_off_flag=risk_off_flag,
                today=tomorrow,
                company_map=company_map,
                price_map=price_tomorrow_map,
                run_id=run_id,
            )

        daily_ret = 0.0

        for r in held_returns:
            daily_ret += float(r["size"]) * float(r["ret"])

        for r in sold_returns:
            daily_ret += float(r["size"]) * float(r["ret"])

        for r in bought_returns:
            daily_ret += float(r["size"]) * float(r["ret"])

        total_return *= 1 + daily_ret
        risk_off_flag = daily_ret <= float(GENERAL_CONFIG["risk_off_trigger_daily_return"])

        row = {
            "date": tomorrow,
            "market_signal": (
                "BLOCK_EXCEPTION_BUY"
                if decision.signal_type == "BLOCK" and exception_bought_count_today > 0
                else decision.signal_type
            ),
            "position_count": len(positions),
            "daily_return": daily_ret,
            "cum_return": total_return,
        }

        history.append(row)
        insert_daily_result(conn, run_id, row)

        print(
            f"{today} -> {tomorrow} | "
            f"signal={decision.signal_type} | "
            f"exception_buy={exception_bought_count_today} | "
            f"buy={bought_count_today} | "
            f"sell={sold_count_today} | "
            f"pos={len(positions)} | "
            f"daily={daily_ret:.4f} | "
            f"cum={total_return:.4f}"
        )

        conn.commit()

    return history


# ============================================================
# Result
# ============================================================

def summarize_and_finalize(conn, run_id: str, history: List[dict]) -> None:
    if not history:
        print("history 없음")
        return

    df = pd.DataFrame(history)

    total_return = float(df.iloc[-1]["cum_return"])
    mdd = float(calculate_mdd(df))
    sharpe = float(calculate_sharpe(df))

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) 
            FROM strategy_trade_log
            WHERE run_id = %s
            """,
            (run_id,),
        )
        trade_count = cur.fetchone()[0]

    backtest_start_date = str(df.iloc[0]["date"])
    backtest_end_date = str(df.iloc[-1]["date"])

    finalize_run(
        conn=conn,
        run_id=run_id,
        backtest_start_date=backtest_start_date,
        backtest_end_date=backtest_end_date,
        total_return=total_return,
        mdd=mdd,
        sharpe=sharpe,
        trade_count=trade_count,
    )

    print_section("RESULT")
    print(df.tail(10).to_string(index=False))
    print()
    print(f"run_id       : {run_id}")
    print(f"total_return : {total_return:.6f}")
    print(f"mdd          : {mdd:.4f}")
    print(f"sharpe       : {sharpe:.2f}")
    print(f"trade_count  : {trade_count}")


# ============================================================
# Main
# ============================================================

def main() -> None:
    with get_conn() as conn:
        ensure_run_tables(conn)

        run_id = create_run(
            conn=conn,
            run_mode="BACKTEST_EXCEPTION",
            run_note=(
                "BLOCK_EXCEPTION_BUY_V1 | "
                "BLOCK 구간 예외매수 엔진 통합 실험 | "
                "flow>=0.90, final>=0.60, vol<=0.08, 0.05<=range<=0.08, "
                "max_buy_per_day=2, position_size=0.10"
            ),
        )

        print_section("Created Run")
        print(f"run_id   : {run_id}")
        print("run_mode : BACKTEST_EXCEPTION")
        print(f"note     : {EXPERIMENT_VERSION}")

        history = run_block_exception_engine_backtest(conn, run_id)
        summarize_and_finalize(conn, run_id, history)

    print_section("DONE")
    print("BLOCK_EXCEPTION_BUY_V1 엔진 통합 실험 완료.")


if __name__ == "__main__":
    main()
