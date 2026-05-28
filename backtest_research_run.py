"""표준 백테스트 research run 실행 진입점.

DB 연결, run 생성, 입력/config snapshot 저장, 엔진 실행, 기본 분석 저장을 순서대로 수행한다.
실행하면 DB DDL/DML과 commit이 발생하므로 문서화/리뷰 작업에서는 직접 실행하지 않는다.
"""

import warnings
import json

import pandas as pd
import psycopg2

from port_strategy_common.config import MARKET_CONFIG, FILTER_CONFIG

print("DEBUG neutral_min_score =", MARKET_CONFIG["neutral_min_score"])
print("DEBUG defensive_min_score =", MARKET_CONFIG["defensive_min_score"])
print("DEBUG flow_min =", FILTER_CONFIG["flow_min"])

from port_strategy_common.config import (
    BACKTEST_START_DATE,
    get_config_snapshot,
    DECISION_RUN_DATE,
    FILTER_CONFIG,
    SIZING_CONFIG,
)
from port_strategy_research.backtest_engine import run_backtest
from port_strategy_research.backtest_metrics import calculate_mdd, calculate_sharpe
from port_strategy_research.backtest_run_store import create_run, ensure_run_tables, finalize_run
from port_strategy_research.backtest_analysis_basic import run_analysis
from port_strategy_research.db_config import get_db_config

warnings.filterwarnings("ignore", category=UserWarning)


def get_conn():
    """백테스트 실행용 PostgreSQL connection을 생성한다."""
    return psycopg2.connect(**get_db_config())


# =========================================================
# CONFIG SNAPSHOT SAVE
# =========================================================
def save_config_snapshot(conn, run_id, config: dict):
    """run_id별 config snapshot key/value를 저장한다."""
    with conn.cursor() as cur:
        # 1. raw json 저장
        cur.execute(
            """
            INSERT INTO strategy_run_config (run_id, config_json)
            VALUES (%s, %s)
            """,
            (run_id, json.dumps(config)),
        )

        # 2. flatten 저장
        for category, values in config.items():
            if isinstance(values, dict):
                for k, v in values.items():
                    cur.execute(
                        """
                        INSERT INTO strategy_run_config_kv (run_id, category, key, value)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (run_id, category, k, str(v)),
                    )
            else:
                cur.execute(
                    """
                    INSERT INTO strategy_run_config_kv (run_id, category, key, value)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (run_id, "meta", category, str(values)),
                )

    conn.commit()


# =========================================================
# INPUT HISTORY SAVE
# =========================================================
def save_run_inputs(conn, run_id, inputs: dict):
    """run_id별 실행 입력값을 `strategy_run_input`에 저장한다."""
    with conn.cursor() as cur:
        for k, v in inputs.items():
            cur.execute(
                """
                INSERT INTO strategy_run_input (run_id, input_key, input_value)
                VALUES (%s, %s, %s)
                """,
                (run_id, k, str(v)),
            )

    conn.commit()


if __name__ == "__main__":
    conn = get_conn()

    try:
        ensure_run_tables(conn)

        # =========================================================
        # CREATE RUN
        # =========================================================
        run_id = create_run(
            conn,
            run_mode="BACKTEST",
            run_note="trade_log price columns + 3 report split",
        )

        # =========================================================
        # SAVE CONFIG SNAPSHOT
        # =========================================================
        config_snapshot = get_config_snapshot()
        save_config_snapshot(conn, run_id, config_snapshot)

        # =========================================================
        # SAVE INPUT HISTORY
        # =========================================================
        inputs = {
            "decision_run_date": DECISION_RUN_DATE,
            "backtest_start_date": BACKTEST_START_DATE,
            "flow_min": str(FILTER_CONFIG["flow_min"]),
            "vol_penalty_multiplier": str(SIZING_CONFIG["vol_penalty_multiplier"]),
        }
        save_run_inputs(conn, run_id, inputs)

        # =========================================================
        # BACKTEST
        # =========================================================
        history = run_backtest(conn, run_id)
        df = pd.DataFrame(history)

        if df.empty:
            raise RuntimeError("Backtest history is empty. Check engine/date loading.")

        print("\nRUN ID:", run_id)
        print("\n===== RESULT =====")
        print(df.tail())

        total_return = float(df.iloc[-1]["cum_return"])
        mdd = float(calculate_mdd(df))
        sharpe = float(calculate_sharpe(df))

        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM strategy_trade_log WHERE run_id = %s",
                (run_id,),
            )
            trade_count = cur.fetchone()[0]

        # =========================================================
        # FINALIZE RUN
        # =========================================================
        finalize_run(
            conn,
            run_id,
            backtest_start_date=BACKTEST_START_DATE,
            backtest_end_date=str(df.iloc[-1]["date"]),
            total_return=total_return,
            mdd=mdd,
            sharpe=sharpe,
            trade_count=trade_count,
        )

        # =========================================================
        # BASIC ANALYSIS
        # =========================================================
        # run_analysis(conn, run_id)

        # =========================================================
        # EXTENDED ANALYSIS
        # =========================================================
        from port_strategy_research.analysis_extended import run_analysis_extended

        run_analysis_extended(conn, run_id)

        print("\nTOTAL RETURN:", total_return)
        print(f"\nMDD: {mdd:.4f}")
        print(f"Sharpe Ratio: {sharpe:.2f}")

    finally:
        conn.close()
