import json

from port_strategy_common.config import ENGINE_VERSION, STRATEGY_NAME, get_config_snapshot


def insert_trade_log(conn, row, company_map, run_id):
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