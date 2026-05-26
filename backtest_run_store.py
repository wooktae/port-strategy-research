from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from port_strategy_common.config import ENGINE_VERSION, STRATEGY_NAME, get_config_snapshot


def ensure_run_tables(conn) -> None:
    ddl = """
    CREATE TABLE IF NOT EXISTS strategy_backtest_run (
        run_id UUID PRIMARY KEY,
        strategy_name VARCHAR(100) NOT NULL,
        strategy_version VARCHAR(100) NOT NULL,
        run_mode VARCHAR(30) NOT NULL,
        run_note TEXT,
        run_date DATE,
        started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        finished_at TIMESTAMPTZ,
        backtest_start_date DATE,
        backtest_end_date DATE,
        total_return NUMERIC(20,8),
        mdd NUMERIC(20,8),
        sharpe NUMERIC(20,8),
        trade_count INT,
        config_snapshot JSONB NOT NULL
    );

    CREATE TABLE IF NOT EXISTS strategy_backtest_daily (
        id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        run_id UUID NOT NULL REFERENCES strategy_backtest_run(run_id) ON DELETE CASCADE,
        date DATE NOT NULL,
        market_signal VARCHAR(30),
        position_count INT,
        daily_return NUMERIC(20,8),
        cum_return NUMERIC(20,8),
        UNIQUE(run_id, date)
    );

    ALTER TABLE strategy_trade_log
        ADD COLUMN IF NOT EXISTS run_id UUID,
        ADD COLUMN IF NOT EXISTS config_snapshot JSONB;

    CREATE INDEX IF NOT EXISTS idx_strategy_trade_log_run_id
        ON strategy_trade_log(run_id);

    CREATE INDEX IF NOT EXISTS idx_strategy_backtest_run_started_at
        ON strategy_backtest_run(started_at DESC);

    CREATE INDEX IF NOT EXISTS idx_strategy_backtest_daily_run_id_date
        ON strategy_backtest_daily(run_id, date);
    """
    with conn.cursor() as cur:
        cur.execute(ddl)
    conn.commit()


def create_run(conn, run_mode: str, run_note: str | None = None, run_date: str | None = None) -> str:
    run_id = str(uuid.uuid4())
    snapshot = get_config_snapshot()

    sql = """
    INSERT INTO strategy_backtest_run (
        run_id,
        strategy_name,
        strategy_version,
        run_mode,
        run_note,
        run_date,
        config_snapshot
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
    """
    with conn.cursor() as cur:
        cur.execute(
            sql,
            (
                run_id,
                STRATEGY_NAME,
                ENGINE_VERSION,
                run_mode,
                run_note,
                run_date,
                json.dumps(snapshot, ensure_ascii=False),
            ),
        )
    conn.commit()
    return run_id


def insert_daily_result(conn, run_id: str, row: dict[str, Any]) -> None:
    sql = """
    INSERT INTO strategy_backtest_daily (
        run_id,
        date,
        market_signal,
        position_count,
        daily_return,
        cum_return
    )
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (run_id, date) DO UPDATE SET
        market_signal = EXCLUDED.market_signal,
        position_count = EXCLUDED.position_count,
        daily_return = EXCLUDED.daily_return,
        cum_return = EXCLUDED.cum_return
    """
    with conn.cursor() as cur:
        cur.execute(
            sql,
            (
                run_id,
                row["date"],
                row.get("market_signal"),
                row.get("position_count"),
                row.get("daily_return"),
                row.get("cum_return"),
            ),
        )


def finalize_run(
    conn,
    run_id: str,
    *,
    backtest_start_date: str | None,
    backtest_end_date: str | None,
    total_return: float,
    mdd: float,
    sharpe: float,
    trade_count: int,
) -> None:
    sql = """
    UPDATE strategy_backtest_run
    SET finished_at = now(),
        backtest_start_date = %s,
        backtest_end_date = %s,
        total_return = %s,
        mdd = %s,
        sharpe = %s,
        trade_count = %s
    WHERE run_id = %s
    """
    with conn.cursor() as cur:
        cur.execute(
            sql,
            (backtest_start_date, backtest_end_date, total_return, mdd, sharpe, trade_count, run_id),
        )
    conn.commit()
