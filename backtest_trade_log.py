"""Saves completed backtest trades to `strategy_trade_log`.

A Trade does not duplicate the entire Config JSON.
It links to `strategy_backtest_run.config_snapshot` via `run_id`,
and denormalizes only the Strategy Config Version and Config Hash for query convenience.
"""

from __future__ import annotations

import json

from port_strategy_common.config import STRATEGY_NAME
from port_strategy_research.research_engine_version import (
    RESEARCH_ENGINE_VERSION,
)


def insert_trade_log(
    conn,
    row,
    company_map,
    run_id,
    *,
    strategy_config_version: str,
    config_hash: str,
):
    """Saves a single trade, linking it to the Run's Canonical Config Snapshot."""
    if not strategy_config_version:
        raise ValueError("TRADE_STRATEGY_CONFIG_VERSION_REQUIRED")

    if len(config_hash) != 64:
        raise ValueError("TRADE_CONFIG_HASH_INVALID")

    company_name = company_map.get(row["ticker_code"], "")

    sql = """
    INSERT INTO strategy_trade_log (
        run_id,
        strategy_name,
        strategy_version,
        strategy_config_version,
        config_hash,
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
        sell_info
    )
    VALUES (
        %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s,
        %s, %s, %s,
        %s, %s, %s,
        %s::jsonb, %s::jsonb
    )
    """

    with conn.cursor() as cur:
        cur.execute(
            sql,
            (
                run_id,
                STRATEGY_NAME,
                RESEARCH_ENGINE_VERSION,
                strategy_config_version,
                config_hash,
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
            ),
        )
