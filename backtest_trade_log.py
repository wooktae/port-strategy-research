"""완료된 백테스트 거래를 `strategy_trade_log`에 저장하는 모듈.

매수/매도 가격, 보유 기간, 수익률, buy/sell metadata, config snapshot을 함께 기록한다.
DB insert 경로이므로 실제 실행 전 run_id와 대상 DB를 확인해야 한다.
"""

import json

from port_strategy_common.config import ENGINE_VERSION, STRATEGY_NAME, get_config_snapshot


def insert_trade_log(conn, row, company_map, run_id):
    """청산되었거나 당일 손절된 단일 거래 row를 trade log 테이블에 insert한다."""
    company_name = company_map.get(row["ticker_code"], "")

    sql = """
    INSERT INTO strategy_trade_log (
        run_id,
        strategy_name,
        strategy_version,
        ticker_code,
        company_name,
        buy_date,
        sell_date,
        holding_period,
        return_pct,
        buy_open_price,
        buy_close_price,
        buy_low_price,
        sell_open_price,
        sell_close_price,
        sell_low_price,
        buy_info,
        sell_info,
        config_snapshot
    )
    VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s,
        %s, %s, %s,
        %s, %s, %s::jsonb
    )
    """

    with conn.cursor() as cur:
        cur.execute(
            sql,
            (
                run_id,
                STRATEGY_NAME,
                ENGINE_VERSION,
                row["ticker_code"],
                company_name,
                row["buy_date"],
                row["sell_date"],
                row["holding_period"],
                row["return_pct"],
                row.get("buy_open_price"),
                row.get("buy_close_price"),
                row.get("buy_low_price"),
                row.get("sell_open_price"),
                row.get("sell_close_price"),
                row.get("sell_low_price"),
                json.dumps(row["buy_info"], ensure_ascii=False),
                json.dumps(row["sell_info"], ensure_ascii=False),
                json.dumps(get_config_snapshot(), ensure_ascii=False),
            ),
        )
