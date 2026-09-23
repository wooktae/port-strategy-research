"""Analysis entrypoint that computes and stores the post-hoc returns of watch candidates after a block.

It reads watch candidates and future prices from the DB and updates the n-day-forward return columns.
Because it includes a DB update, do not run it directly in documentation work.
"""

from __future__ import annotations

import argparse
import traceback
from decimal import Decimal
from typing import Any

import psycopg2
import psycopg2.extras

from port_strategy_research.db_config import get_db_config


RETURN_DAYS = (1, 3, 5, 10)


def get_conn():
    return psycopg2.connect(**get_db_config())


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None

    try:
        return Decimal(str(value))
    except Exception:
        return None


def _calc_return(base_price: Any, future_price: Any) -> Decimal | None:
    base = _to_decimal(base_price)
    future = _to_decimal(future_price)

    if base is None or future is None:
        return None

    if base == 0:
        return None

    return (future / base) - Decimal("1")


def fetch_watch_candidates(conn, daily_run_id: int | None = None) -> list[dict]:
    sql = """
        SELECT
            id,
            daily_run_id,
            run_date,
            data_date,
            ticker_code,
            stock_name,
            close_price,
            return_1d,
            return_3d,
            return_5d,
            return_10d
        FROM strategy_block_watch_candidate
        WHERE (%(daily_run_id)s IS NULL OR daily_run_id = %(daily_run_id)s)
        ORDER BY run_date DESC, id DESC
    """

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, {"daily_run_id": daily_run_id})
        return list(cur.fetchall())


def fetch_future_prices(conn, ticker_code: str, data_date) -> dict[int, Decimal]:
    """
    Query the closing prices on the 1st/3rd/5th/10th trading days after data_date for the given stock.

    Example:
    data_date = 2026-05-19
    First trading day after = 2026-05-20; if that data exists, return_1d is computed
    If not yet available, it stays NULL
    """

    sql = """
        WITH future_prices AS (
            SELECT
                date,
                close_price,
                ROW_NUMBER() OVER (ORDER BY date ASC) AS rn
            FROM pre_total_stock_daily_feature
            WHERE ticker_code = %(ticker_code)s
              AND date > %(data_date)s
              AND close_price IS NOT NULL
        )
        SELECT
            rn,
            date,
            close_price
        FROM future_prices
        WHERE rn IN (1, 3, 5, 10)
        ORDER BY rn
    """

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            sql,
            {
                "ticker_code": ticker_code,
                "data_date": data_date,
            },
        )
        rows = cur.fetchall()

    return {
        int(row["rn"]): row["close_price"]
        for row in rows
    }


def update_watch_returns(
    conn,
    candidate_id: int,
    return_1d: Decimal | None,
    return_3d: Decimal | None,
    return_5d: Decimal | None,
    return_10d: Decimal | None,
):
    sql = """
        UPDATE strategy_block_watch_candidate
        SET
            return_1d = COALESCE(%(return_1d)s, return_1d),
            return_3d = COALESCE(%(return_3d)s, return_3d),
            return_5d = COALESCE(%(return_5d)s, return_5d),
            return_10d = COALESCE(%(return_10d)s, return_10d),
            updated_at = NOW()
        WHERE id = %(candidate_id)s
    """

    with conn.cursor() as cur:
        cur.execute(
            sql,
            {
                "candidate_id": candidate_id,
                "return_1d": return_1d,
                "return_3d": return_3d,
                "return_5d": return_5d,
                "return_10d": return_10d,
            },
        )


def fetch_summary(conn, daily_run_id: int | None = None) -> dict:
    sql = """
        SELECT
            COUNT(*) AS total_count,

            COUNT(return_1d) AS return_1d_count,
            AVG(return_1d) AS avg_return_1d,
            AVG(CASE WHEN return_1d > 0 THEN 1.0 ELSE 0.0 END)
                FILTER (WHERE return_1d IS NOT NULL) AS win_rate_1d,

            COUNT(return_3d) AS return_3d_count,
            AVG(return_3d) AS avg_return_3d,
            AVG(CASE WHEN return_3d > 0 THEN 1.0 ELSE 0.0 END)
                FILTER (WHERE return_3d IS NOT NULL) AS win_rate_3d,

            COUNT(return_5d) AS return_5d_count,
            AVG(return_5d) AS avg_return_5d,
            AVG(CASE WHEN return_5d > 0 THEN 1.0 ELSE 0.0 END)
                FILTER (WHERE return_5d IS NOT NULL) AS win_rate_5d,

            COUNT(return_10d) AS return_10d_count,
            AVG(return_10d) AS avg_return_10d,
            AVG(CASE WHEN return_10d > 0 THEN 1.0 ELSE 0.0 END)
                FILTER (WHERE return_10d IS NOT NULL) AS win_rate_10d
        FROM strategy_block_watch_candidate
        WHERE (%(daily_run_id)s IS NULL OR daily_run_id = %(daily_run_id)s)
    """

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, {"daily_run_id": daily_run_id})
        return dict(cur.fetchone())


def _fmt_pct(value: Any) -> str:
    decimal_value = _to_decimal(value)

    if decimal_value is None:
        return "-"

    return f"{decimal_value * Decimal('100'):.2f}%"


def run_block_watch_analysis(daily_run_id: int | None = None):
    """Computes and stores the future returns of watch candidates and prints a summary."""
    conn = get_conn()

    try:
        candidates = fetch_watch_candidates(conn, daily_run_id=daily_run_id)

        updated_count = 0
        waiting_count = 0

        print("========================================")
        print("[Block Watch Analysis]")
        print("========================================")
        print("daily_run_id:", daily_run_id or "ALL")
        print("candidate_count:", len(candidates))

        for candidate in candidates:
            future_prices = fetch_future_prices(
                conn,
                ticker_code=candidate["ticker_code"],
                data_date=candidate["data_date"],
            )

            return_1d = _calc_return(candidate["close_price"], future_prices.get(1))
            return_3d = _calc_return(candidate["close_price"], future_prices.get(3))
            return_5d = _calc_return(candidate["close_price"], future_prices.get(5))
            return_10d = _calc_return(candidate["close_price"], future_prices.get(10))

            has_any_return = any(
                value is not None
                for value in [return_1d, return_3d, return_5d, return_10d]
            )

            if has_any_return:
                update_watch_returns(
                    conn=conn,
                    candidate_id=candidate["id"],
                    return_1d=return_1d,
                    return_3d=return_3d,
                    return_5d=return_5d,
                    return_10d=return_10d,
                )
                updated_count += 1
            else:
                waiting_count += 1

            print(
                f"- {candidate['ticker_code']} {candidate.get('stock_name') or ''} "
                f"base={candidate['close_price']} "
                f"1D={_fmt_pct(return_1d)} "
                f"3D={_fmt_pct(return_3d)} "
                f"5D={_fmt_pct(return_5d)} "
                f"10D={_fmt_pct(return_10d)}"
            )

        conn.commit()

        summary = fetch_summary(conn, daily_run_id=daily_run_id)

        print("")
        print("========================================")
        print("[Summary]")
        print("========================================")
        print("total_count:", summary.get("total_count"))
        print("updated_count:", updated_count)
        print("waiting_count:", waiting_count)
        print("")
        print("return_1d_count:", summary.get("return_1d_count"))
        print("avg_return_1d:", _fmt_pct(summary.get("avg_return_1d")))
        print("win_rate_1d:", _fmt_pct(summary.get("win_rate_1d")))
        print("")
        print("return_3d_count:", summary.get("return_3d_count"))
        print("avg_return_3d:", _fmt_pct(summary.get("avg_return_3d")))
        print("win_rate_3d:", _fmt_pct(summary.get("win_rate_3d")))
        print("")
        print("return_5d_count:", summary.get("return_5d_count"))
        print("avg_return_5d:", _fmt_pct(summary.get("avg_return_5d")))
        print("win_rate_5d:", _fmt_pct(summary.get("win_rate_5d")))
        print("")
        print("return_10d_count:", summary.get("return_10d_count"))
        print("avg_return_10d:", _fmt_pct(summary.get("avg_return_10d")))
        print("win_rate_10d:", _fmt_pct(summary.get("win_rate_10d")))

        return {
            "candidate_count": len(candidates),
            "updated_count": updated_count,
            "waiting_count": waiting_count,
            "summary": summary,
        }

    except Exception:
        conn.rollback()
        print("========================================")
        print("[Block Watch Analysis Failed]")
        print("========================================")
        traceback.print_exc()
        raise

    finally:
        conn.close()


def parse_args():
    parser = argparse.ArgumentParser(description="Run Block Watch return analysis.")
    parser.add_argument(
        "--daily-run-id",
        required=False,
        type=int,
        help="Specific strategy_daily_run.id. Example: 21",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    run_block_watch_analysis(
        daily_run_id=args.daily_run_id,
    )
