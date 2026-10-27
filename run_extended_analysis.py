"""Entrypoint for running the extended analysis on the latest backtest run.

On execution it connects to the DB, finds the latest run_id, and regenerates the extended analysis tables.
In documentation work, perform static checks only and do not run it directly.
"""

from port_strategy_research.report_data_loader import get_conn, get_latest_run_id
from port_strategy_research.analysis_extended import run_analysis_extended


if __name__ == "__main__":
    conn = get_conn()
    cur = conn.cursor()
    try:
        run_id = get_latest_run_id(cur)
        if not run_id:
            raise RuntimeError("최신 run_id 없음")
        print(f"👉 latest run_id = {run_id}")
    finally:
        cur.close()

    try:
        run_analysis_extended(conn, run_id)
        print("✅ extended analysis 완료")
    finally:
        conn.close()
        
