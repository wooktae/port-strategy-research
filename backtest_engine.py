"""백테스트 일자 루프를 실행하는 엔진 모듈.

시장 판단, 후보 필터, 기존 포지션 처리, 신규 매수 처리 결과를 일별 성과로 집계한다.
실행 시 DB에서 feature를 읽고 `strategy_backtest_daily` 및 일별 포지션 저장 경로에 기록하므로
운영 DB 대상과 run_id를 확인한 뒤에만 호출해야 한다.
"""

from port_strategy_research.backtest_buy_logic import process_buy
from port_strategy_research.backtest_position_manager import process_existing_positions
from port_strategy_common.config import ENGINE_VERSION, GENERAL_CONFIG
from port_strategy_research.backtest_loader import (
    get_dates,
    get_market,
    get_stocks,
    get_price,
    load_stock_universe,
)
from port_strategy_decision.backtest_market import evaluate_market
from port_strategy_decision.backtest_filter import filter_buy_candidates
from port_strategy_research.backtest_run_store import insert_daily_result, insert_daily_positions


def run_backtest(conn, run_id):
    """하나의 backtest run에 대해 전체 거래일 루프를 수행하고 일별 결과를 저장한다."""
    print("ENGINE VERSION =", ENGINE_VERSION, __file__)

    dates = get_dates(conn)
    total_return = 1.0
    history = []
    positions = {}
    risk_off_flag = False
    company_map = load_stock_universe(conn)

    for i in range(len(dates) - 1):
        today = str(dates[i])
        tomorrow = str(dates[i + 1])

        market = get_market(conn, today)
        stocks = get_stocks(conn, today)

        decision = evaluate_market(market)
        candidates = filter_buy_candidates(stocks, decision)

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

        if tomorrow >= "2026-05-01":
            print("\n[DEBUG POSITIONS]", tomorrow, "count=", len(positions))
            for ticker_code, pos in positions.items():
                print("  ticker=", ticker_code)
                print("  pos=", pos)

        row = {
            "date": tomorrow,
            "market_signal": decision.signal_type,
            "position_count": len(positions),
            "daily_return": daily_ret,
            "cum_return": total_return,
        }

        history.append(row)
        insert_daily_result(conn, run_id, row)
        insert_daily_positions(conn, run_id, tomorrow, positions, company_map)
        
        print(
            f"{today} -> {tomorrow} | "
            f"signal={decision.signal_type} | "
            f"buy={bought_count_today} | "
            f"sell={sold_count_today} | "
            f"pos={len(positions)} | "
            f"daily={daily_ret:.4f} | "
            f"cum={total_return:.4f}"
        )

        conn.commit()

    return history
