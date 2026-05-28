"""백테스트 거래 로그 기반 기본 분석 테이블을 생성하는 모듈.

매수 사유, 보유 기간, 시장 신호별 성과를 집계해 `strategy_backtest_*_analysis` 계열에 저장한다.
기존 run_id 분석 row 삭제 후 insert하는 DB write 경로이므로 실행 전 대상 DB 확인이 필요하다.
"""

import psycopg2

def run_analysis(conn, run_id):
    """단일 run_id의 기본 분석 row를 재생성한다."""
    cur = conn.cursor()

    # 1️⃣ exit reason 분석
    cur.execute("""
        INSERT INTO strategy_backtest_analysis (run_id, reason, trades, avg_return, win_rate)
        SELECT
            %s,
            sell_info->>'reason',
            COUNT(*),
            AVG((sell_info->>'cum_return')::numeric),
            SUM(CASE WHEN (sell_info->>'cum_return')::numeric > 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*)
        FROM strategy_trade_log
        WHERE run_id = %s
        GROUP BY 2
    """, (run_id, run_id))

    # 2️⃣ holding 분석
    cur.execute("""
        INSERT INTO strategy_backtest_holding_analysis (run_id, holding_period, trades, avg_return, win_rate)
        SELECT
            %s,
            holding_period,
            COUNT(*),
            AVG((sell_info->>'cum_return')::numeric),
            SUM(CASE WHEN (sell_info->>'cum_return')::numeric > 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*)
        FROM strategy_trade_log
        WHERE run_id = %s
        GROUP BY holding_period
    """, (run_id, run_id))

    # 3️⃣ market_block bad 상세
    cur.execute("""
        INSERT INTO strategy_backtest_mbweak_analysis (run_id, holding_period, trades, avg_return, avg_flow, avg_final)
        SELECT
            %s,
            holding_period,
            COUNT(*),
            AVG((sell_info->>'cum_return')::numeric),
            AVG((sell_info->>'flow')::numeric),
            AVG((sell_info->>'final')::numeric)
        FROM strategy_trade_log
        WHERE run_id = %s
        AND sell_info->>'reason' IN (
            'market_block_quality_drop',
            'market_block_weak_other'
        )
        GROUP BY holding_period
    """, (run_id, run_id))

    conn.commit()
    cur.close()
