import psycopg2

def run_analysis(conn, run_id):
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