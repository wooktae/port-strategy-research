"""Module that regenerates the extended backtest analysis tables by run_id.

It computes trade detail, signal/holding, ticker, entry/exit, sector, and MB weak candidate analyses.
Because this is a DB write path that includes analysis-table delete/insert, do not run it directly during report review.
"""

from port_strategy_research.report_data_loader import (
    get_conn,
    get_latest_run_id,
    get_run_summary,
    get_thresholds,
)

from port_strategy_common.config import REPORT_CONFIG


flow_b1, flow_b2 = REPORT_CONFIG["entry_buckets"]["buy_flow"]
score_b1, score_b2, score_b3 = REPORT_CONFIG["entry_buckets"]["buy_score"]
short_b1, short_b2 = REPORT_CONFIG["entry_buckets"]["buy_short"]
vol_b1, vol_b2 = REPORT_CONFIG["entry_buckets"]["buy_vol"]
range_b1, range_b2 = REPORT_CONFIG["entry_buckets"]["buy_intraday_range"]

sig_h1, sig_h2, sig_h3, sig_h4 = REPORT_CONFIG["holding_buckets"]["signal_holding"]
mb_h1, mb_h2, mb_h3 = REPORT_CONFIG["holding_buckets"]["mbweak_holding"]

p1, p2, p3, p4 = REPORT_CONFIG["mbweak"]["profit_bucket_edges"]


def _fmt_num(v: float) -> str:
    s = f"{float(v):.4f}"
    s = s.rstrip("0").rstrip(".")
    return s

FLOW_B1_LABEL = _fmt_num(flow_b1)
FLOW_B2_LABEL = _fmt_num(flow_b2)

SCORE_B1_LABEL = _fmt_num(score_b1)
SCORE_B2_LABEL = _fmt_num(score_b2)
SCORE_B3_LABEL = _fmt_num(score_b3)

SHORT_B1_LABEL = _fmt_num(short_b1)
SHORT_B2_LABEL = _fmt_num(short_b2)

VOL_B1_LABEL = _fmt_num(vol_b1)
VOL_B2_LABEL = _fmt_num(vol_b2)

RANGE_B1_LABEL = _fmt_num(range_b1)
RANGE_B2_LABEL = _fmt_num(range_b2)

P1_LABEL = f"{_fmt_num(abs(p1) * 100)}%%"
P2_LABEL = f"{_fmt_num(abs(p2) * 100)}%%"
P3_LABEL = f"{_fmt_num(abs(p3) * 100)}%%"
P4_LABEL = f"{_fmt_num(abs(p4) * 100)}%%"


def run_analysis_extended(conn, run_id: str):
    """Recomputes and saves the extended analysis tables for a single run_id."""
    cur = conn.cursor()

    run_summary = get_run_summary(cur, run_id)
    thresholds = get_thresholds(run_summary["config_snapshot"])

    sell_flow_breakdown = thresholds["sell_flow_breakdown"]
    sell_final_breakdown = thresholds["sell_final_breakdown"]
    sell_short_pressure = thresholds["sell_short_pressure"]

    flow_min_label = _fmt_num(thresholds["flow_min"])

    # Delete the existing analysis results
    cur.execute("DELETE FROM strategy_backtest_analysis WHERE run_id = %s", (run_id,))
    cur.execute("DELETE FROM strategy_backtest_holding_analysis WHERE run_id = %s", (run_id,))
    cur.execute("DELETE FROM strategy_backtest_mbweak_analysis WHERE run_id = %s", (run_id,))
    cur.execute("DELETE FROM strategy_backtest_entry_analysis WHERE run_id = %s", (run_id,))
    cur.execute("DELETE FROM strategy_backtest_signal_holding_analysis WHERE run_id = %s", (run_id,))
    cur.execute("DELETE FROM strategy_backtest_ticker_analysis WHERE run_id = %s", (run_id,))
    cur.execute("DELETE FROM strategy_backtest_exit_trigger_analysis WHERE run_id = %s", (run_id,))
    cur.execute("DELETE FROM strategy_backtest_entry_day_analysis WHERE run_id = %s", (run_id,))
    cur.execute("DELETE FROM strategy_backtest_sector_analysis WHERE run_id = %s", (run_id,))
    cur.execute("DELETE FROM strategy_backtest_mbweak_bucket_analysis WHERE run_id = %s", (run_id,))
    cur.execute("DELETE FROM strategy_backtest_mbweak_candidate_analysis WHERE run_id = %s", (run_id,))
    cur.execute("DELETE FROM strategy_backtest_mbweak_other_analysis WHERE run_id = %s", (run_id,))
    
    # 1) exit reason analysis
    cur.execute(
        """
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
        """,
        (run_id, run_id),
    )

    # 2) holding analysis
    cur.execute(
        """
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
        """,
        (run_id, run_id),
    )

    # 3) market_block bad details (quality_drop + weak_other)
    cur.execute(
        """
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
        """,
        (run_id, run_id),
    )

    # 4) entry analysis - buy_flow bucket
    cur.execute(
        f"""
        INSERT INTO strategy_backtest_entry_analysis
            (run_id, metric_name, bucket_label, trades, avg_return, win_rate, avg_holding)
        SELECT
            %s,
            'buy_flow',
            CASE
                WHEN (buy_info->>'flow')::numeric < {flow_b1} THEN '{flow_min_label}~{FLOW_B1_LABEL}'
                WHEN (buy_info->>'flow')::numeric < {flow_b2} THEN '{FLOW_B1_LABEL}~{FLOW_B2_LABEL}'
                ELSE '{FLOW_B2_LABEL}+'
            END AS bucket_label,
            COUNT(*),
            AVG((sell_info->>'cum_return')::numeric),
            SUM(CASE WHEN (sell_info->>'cum_return')::numeric > 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*),
            AVG(holding_period)
        FROM strategy_trade_log
        WHERE run_id = %s
          AND buy_info ? 'flow'
        GROUP BY 3
        """,
        (run_id, run_id),
    )

    # 5) entry analysis - buy_score bucket
    cur.execute(
        f"""
        INSERT INTO strategy_backtest_entry_analysis
            (run_id, metric_name, bucket_label, trades, avg_return, win_rate, avg_holding)
        SELECT
            %s,
            'buy_score',
            CASE
                WHEN (buy_info->>'score')::numeric < {score_b1} THEN 'score<{SCORE_B1_LABEL}'
                WHEN (buy_info->>'score')::numeric < {score_b2} THEN '{SCORE_B1_LABEL}~{SCORE_B2_LABEL}'
                WHEN (buy_info->>'score')::numeric < {score_b3} THEN '{SCORE_B2_LABEL}~{SCORE_B3_LABEL}'
                ELSE '{SCORE_B3_LABEL}+'
            END AS bucket_label,
            COUNT(*),
            AVG((sell_info->>'cum_return')::numeric),
            SUM(CASE WHEN (sell_info->>'cum_return')::numeric > 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*),
            AVG(holding_period)
        FROM strategy_trade_log
        WHERE run_id = %s
          AND buy_info ? 'score'
        GROUP BY 3
        """,
        (run_id, run_id),
    )

    # 6) entry analysis - buy_info bucket
    cur.execute(
        """
        INSERT INTO strategy_backtest_entry_analysis
            (run_id, metric_name, bucket_label, trades, avg_return, win_rate, avg_holding)
        SELECT
            %s,
            'buy_info',
            CASE
                WHEN (buy_info->>'info')::numeric < 0 THEN 'info<0'
                WHEN (buy_info->>'info')::numeric = 0 THEN 'info=0'
                ELSE 'info>0'
            END AS bucket_label,
            COUNT(*),
            AVG((sell_info->>'cum_return')::numeric),
            SUM(CASE WHEN (sell_info->>'cum_return')::numeric > 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*),
            AVG(holding_period)
        FROM strategy_trade_log
        WHERE run_id = %s
          AND buy_info ? 'info'
        GROUP BY 3
        """,
        (run_id, run_id),
    )

    # 7) entry analysis - buy_short bucket
    cur.execute(
        f"""
        INSERT INTO strategy_backtest_entry_analysis
            (run_id, metric_name, bucket_label, trades, avg_return, win_rate, avg_holding)
        SELECT
            %s,
            'buy_short',
            CASE
                WHEN (buy_info->>'short')::numeric < {short_b1} THEN 'short<{SHORT_B1_LABEL}'
                WHEN (buy_info->>'short')::numeric < {short_b2} THEN '{SHORT_B1_LABEL}~{SHORT_B2_LABEL}'
                ELSE '{SHORT_B2_LABEL}+'
            END AS bucket_label,
            COUNT(*),
            AVG((sell_info->>'cum_return')::numeric),
            SUM(CASE WHEN (sell_info->>'cum_return')::numeric > 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*),
            AVG(holding_period)
        FROM strategy_trade_log
        WHERE run_id = %s
          AND buy_info ? 'short'
        GROUP BY 3
        """,
        (run_id, run_id),
    )

    # 8) entry analysis - buy_vol bucket
    cur.execute(
        f"""
        INSERT INTO strategy_backtest_entry_analysis
            (run_id, metric_name, bucket_label, trades, avg_return, win_rate, avg_holding)
        SELECT
            %s,
            'buy_vol',
            CASE
                WHEN (buy_info->>'vol')::numeric < {vol_b1} THEN 'vol<{VOL_B1_LABEL}'
                WHEN (buy_info->>'vol')::numeric < {vol_b2} THEN '{VOL_B1_LABEL}~{VOL_B2_LABEL}'
                ELSE '{VOL_B2_LABEL}+'
            END AS bucket_label,
            COUNT(*),
            AVG((sell_info->>'cum_return')::numeric),
            SUM(CASE WHEN (sell_info->>'cum_return')::numeric > 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*),
            AVG(holding_period)
        FROM strategy_trade_log
        WHERE run_id = %s
          AND buy_info ? 'vol'
        GROUP BY 3
        """,
        (run_id, run_id),
    )

    # 9) entry analysis - buy_intraday_range bucket
    cur.execute(
        f"""
        INSERT INTO strategy_backtest_entry_analysis
            (run_id, metric_name, bucket_label, trades, avg_return, win_rate, avg_holding)
        SELECT
            %s,
            'buy_intraday_range',
            CASE
                WHEN (buy_info->>'intraday_range')::numeric < {range_b1} THEN 'range<{RANGE_B1_LABEL}'
                WHEN (buy_info->>'intraday_range')::numeric < {range_b2} THEN '{RANGE_B1_LABEL}~{RANGE_B2_LABEL}'
                ELSE '{RANGE_B2_LABEL}+'
            END AS bucket_label,
            COUNT(*),
            AVG((sell_info->>'cum_return')::numeric),
            SUM(CASE WHEN (sell_info->>'cum_return')::numeric > 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*),
            AVG(holding_period)
        FROM strategy_trade_log
        WHERE run_id = %s
          AND buy_info ? 'intraday_range'
        GROUP BY 3
        """,
        (run_id, run_id),
    )

    # 10) entry analysis - buy_has_info_flag
    cur.execute(
        """
        INSERT INTO strategy_backtest_entry_analysis
            (run_id, metric_name, bucket_label, trades, avg_return, win_rate, avg_holding)
        SELECT
            %s,
            'buy_has_info_flag',
            CASE
                WHEN COALESCE((buy_info->>'has_info_flag')::boolean, false) THEN 'true'
                ELSE 'false'
            END AS bucket_label,
            COUNT(*),
            AVG((sell_info->>'cum_return')::numeric),
            SUM(CASE WHEN (sell_info->>'cum_return')::numeric > 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*),
            AVG(holding_period)
        FROM strategy_trade_log
        WHERE run_id = %s
        GROUP BY 3
        """,
        (run_id, run_id),
    )

    # 11) entry analysis - buy_entry_signal
    cur.execute(
        """
        INSERT INTO strategy_backtest_entry_analysis
            (run_id, metric_name, bucket_label, trades, avg_return, win_rate, avg_holding)
        SELECT
            %s,
            'buy_entry_signal',
            COALESCE(buy_info->>'entry_market_signal', 'UNKNOWN') AS bucket_label,
            COUNT(*),
            AVG((sell_info->>'cum_return')::numeric),
            SUM(CASE WHEN (sell_info->>'cum_return')::numeric > 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*),
            AVG(holding_period)
        FROM strategy_trade_log
        WHERE run_id = %s
        GROUP BY 3
        """,
        (run_id, run_id),
    )

    # 12) entry analysis - score/flow combo
    cur.execute(
        f"""
        INSERT INTO strategy_backtest_entry_analysis
            (run_id, metric_name, bucket_label, trades, avg_return, win_rate, avg_holding)
        SELECT
            %s,
            'buy_score_flow_combo',
            CASE
                WHEN (buy_info->>'score')::numeric >= {score_b3} AND (buy_info->>'flow')::numeric >= {flow_b2}
                    THEN 'score>={SCORE_B3_LABEL} + flow>={FLOW_B2_LABEL}'
                WHEN (buy_info->>'score')::numeric >= {score_b2} AND (buy_info->>'flow')::numeric >= {flow_b1}
                    THEN 'score>={SCORE_B2_LABEL} + flow>={FLOW_B1_LABEL}'
                ELSE 'other'
            END AS bucket_label,
            COUNT(*),
            AVG((sell_info->>'cum_return')::numeric),
            SUM(CASE WHEN (sell_info->>'cum_return')::numeric > 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*),
            AVG(holding_period)
        FROM strategy_trade_log
        WHERE run_id = %s
          AND buy_info ? 'score'
          AND buy_info ? 'flow'
        GROUP BY 3
        """,
        (run_id, run_id),
    )

    # 13) signal_holding analysis
    cur.execute(
        f"""
        WITH entry_signal AS (
            SELECT
                t.id,
                t.run_id,
                t.ticker_code,
                t.company_name,
                t.buy_date,
                t.holding_period,
                t.sell_info->>'reason' AS exit_reason,
                (t.sell_info->>'cum_return')::numeric AS cum_return,
                d.market_signal AS entry_market_signal
            FROM strategy_trade_log t
            JOIN strategy_backtest_daily d
              ON t.run_id = d.run_id
             AND t.buy_date = d.date
            WHERE t.run_id = %s
        )
        INSERT INTO strategy_backtest_signal_holding_analysis
            (run_id, entry_market_signal, holding_bucket, exit_reason, trades, avg_return, win_rate, avg_holding)
        SELECT
            %s,
            entry_market_signal,
            CASE
                WHEN holding_period <= {sig_h1} THEN '0~{sig_h1}'
                WHEN holding_period <= {sig_h2} THEN '{sig_h1 + 1}~{sig_h2}'
                WHEN holding_period <= {sig_h3} THEN '{sig_h2 + 1}~{sig_h3}'
                WHEN holding_period <= {sig_h4} THEN '{sig_h3 + 1}~{sig_h4}'
                ELSE '{sig_h4 + 1}+'
            END AS holding_bucket,
            exit_reason,
            COUNT(*),
            AVG(cum_return),
            SUM(CASE WHEN cum_return > 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*),
            AVG(holding_period)
        FROM entry_signal
        GROUP BY entry_market_signal, holding_bucket, exit_reason
        """,
        (run_id, run_id),
    )

    # 14) ticker analysis
    cur.execute(
        """
        WITH reason_rank AS (
            SELECT
                run_id,
                ticker_code,
                sell_info->>'reason' AS exit_reason,
                COUNT(*) AS cnt,
                ROW_NUMBER() OVER (
                    PARTITION BY run_id, ticker_code
                    ORDER BY COUNT(*) DESC, sell_info->>'reason'
                ) AS rn
            FROM strategy_trade_log
            WHERE run_id = %s
            GROUP BY run_id, ticker_code, sell_info->>'reason'
        )
        INSERT INTO strategy_backtest_ticker_analysis
            (
                run_id, ticker_code, company_name, trades, avg_return, win_rate,
                total_pnl_contribution, avg_holding, major_exit_reason, avg_buy_flow, avg_buy_score
            )
        SELECT
            t.run_id,
            t.ticker_code,
            MAX(t.company_name),
            COUNT(*),
            AVG((t.sell_info->>'cum_return')::numeric),
            SUM(CASE WHEN (t.sell_info->>'cum_return')::numeric > 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*),
            SUM((t.sell_info->>'cum_return')::numeric),
            AVG(t.holding_period),
            rr.exit_reason,
            AVG((t.buy_info->>'flow')::numeric),
            AVG((t.buy_info->>'score')::numeric)
        FROM strategy_trade_log t
        LEFT JOIN reason_rank rr
          ON t.run_id = rr.run_id
         AND t.ticker_code = rr.ticker_code
         AND rr.rn = 1
        WHERE t.run_id = %s
        GROUP BY t.run_id, t.ticker_code, rr.exit_reason
        """,
        (run_id, run_id),
    )

    # 15) exit trigger overlap analysis
    cur.execute(
        """
        WITH base AS (
            SELECT
                run_id,
                holding_period,
                sell_info->>'reason' AS exit_reason,
                (sell_info->>'cum_return')::numeric AS cum_return,
                CASE WHEN sell_info ? 'flow' THEN (sell_info->>'flow')::numeric END AS flow_value,
                CASE WHEN sell_info ? 'final' THEN (sell_info->>'final')::numeric END AS final_value,
                CASE WHEN sell_info ? 'short' THEN (sell_info->>'short')::numeric END AS short_value
            FROM strategy_trade_log
            WHERE run_id = %s
        ),
        expanded AS (
            SELECT run_id, exit_reason, holding_period, cum_return, 'reason_self' AS trigger_name
            FROM base

            UNION ALL
            SELECT run_id, exit_reason, holding_period, cum_return, 'flow_breakdown_condition'
            FROM base
            WHERE flow_value IS NOT NULL
            AND flow_value < %s

            UNION ALL
            SELECT run_id, exit_reason, holding_period, cum_return, 'score_breakdown_condition'
            FROM base
            WHERE final_value IS NOT NULL
            AND final_value < %s

            UNION ALL
            SELECT run_id, exit_reason, holding_period, cum_return, 'short_pressure_condition'
            FROM base
            WHERE short_value IS NOT NULL
            AND short_value > %s

            UNION ALL
            SELECT run_id, exit_reason, holding_period, cum_return, 'early_holding_condition'
            FROM base
            WHERE holding_period <= 2

            UNION ALL
            SELECT run_id, exit_reason, holding_period, cum_return, 'mid_holding_condition'
            FROM base
            WHERE holding_period BETWEEN 3 AND 5

            UNION ALL
            SELECT run_id, exit_reason, holding_period, cum_return, 'late_holding_condition'
            FROM base
            WHERE holding_period >= 10
        )
        INSERT INTO strategy_backtest_exit_trigger_analysis
            (run_id, exit_reason, trigger_name, trades, avg_return, win_rate, avg_holding)
        SELECT
            %s,
            exit_reason,
            trigger_name,
            COUNT(*),
            AVG(cum_return),
            SUM(CASE WHEN cum_return > 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*),
            AVG(holding_period)
        FROM expanded
        GROUP BY exit_reason, trigger_name
        """,
        (
            run_id,
            sell_flow_breakdown,
            sell_final_breakdown,
            sell_short_pressure,
            run_id,
        ),
    )

    # 16) entry day analysis
    cur.execute(
        f"""
        WITH base AS (
            SELECT
                run_id,
                COALESCE(buy_info->>'entry_market_signal', 'UNKNOWN') AS entry_signal,
                CASE
                    WHEN buy_info ? 'flow' THEN
                        CASE
                            WHEN (buy_info->>'flow')::numeric < {flow_b1} THEN '{flow_min_label}~{FLOW_B1_LABEL}'
                            WHEN (buy_info->>'flow')::numeric < {flow_b2} THEN '{FLOW_B1_LABEL}~{FLOW_B2_LABEL}'
                            ELSE '{FLOW_B2_LABEL}+'
                        END
                    ELSE 'UNKNOWN'
                END AS flow_bucket,
                CASE
                    WHEN buy_info ? 'score' THEN
                        CASE
                            WHEN (buy_info->>'score')::numeric < {score_b1} THEN 'score<{SCORE_B1_LABEL}'
                            WHEN (buy_info->>'score')::numeric < {score_b2} THEN '{SCORE_B1_LABEL}~{SCORE_B2_LABEL}'
                            WHEN (buy_info->>'score')::numeric < {score_b3} THEN '{SCORE_B2_LABEL}~{SCORE_B3_LABEL}'
                            ELSE '{SCORE_B3_LABEL}+'
                        END
                    ELSE 'UNKNOWN'
                END AS score_bucket,
                CASE
                    WHEN buy_open_price IS NOT NULL
                    AND buy_close_price IS NOT NULL
                    AND buy_open_price <> 0
                    THEN (buy_close_price - buy_open_price) / buy_open_price
                END AS day1_return,
                CASE
                    WHEN buy_open_price IS NOT NULL
                    AND sell_open_price IS NOT NULL
                    AND buy_open_price <> 0
                    THEN (sell_open_price - buy_open_price) / buy_open_price
                END AS exit_open_return,
                CASE
                    WHEN sell_info ? 'cum_return'
                    THEN (sell_info->>'cum_return')::numeric
                END AS final_return
            FROM strategy_trade_log
            WHERE run_id = %s
        )
        INSERT INTO strategy_backtest_entry_day_analysis (
            run_id,
            metric_name,
            bucket_label,
            trades,
            avg_day1_return,
            day1_win_rate,
            avg_exit_open_return,
            exit_open_win_rate,
            avg_final_return,
            final_win_rate
        )
        SELECT
            %s,
            metric_name,
            bucket_label,
            COUNT(*),
            AVG(day1_return),
            SUM(CASE WHEN day1_return > 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*),
            AVG(exit_open_return),
            SUM(CASE WHEN exit_open_return > 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*),
            AVG(final_return),
            SUM(CASE WHEN final_return > 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*)
        FROM (
            SELECT 'entry_signal' AS metric_name, entry_signal AS bucket_label, day1_return, exit_open_return, final_return
            FROM base
            UNION ALL
            SELECT 'buy_flow', flow_bucket, day1_return, exit_open_return, final_return
            FROM base
            UNION ALL
            SELECT 'buy_score', score_bucket, day1_return, exit_open_return, final_return
            FROM base
        ) x
        GROUP BY metric_name, bucket_label
        """,
        (run_id, run_id),
    )

    # 17) sector analysis
    cur.execute(
        """
        WITH reason_rank AS (
            SELECT
                t.run_id,
                COALESCE(su.sector[1], 'UNKNOWN') AS sector_level1,
                su.sector[2] AS sector_level2,
                COALESCE(t.sell_info->>'reason', 'UNKNOWN') AS exit_reason,
                COUNT(*) AS cnt,
                ROW_NUMBER() OVER (
                    PARTITION BY
                        t.run_id,
                        COALESCE(su.sector[1], 'UNKNOWN'),
                        su.sector[2]
                    ORDER BY COUNT(*) DESC, COALESCE(t.sell_info->>'reason', 'UNKNOWN')
                ) AS rn
            FROM strategy_trade_log t
            JOIN stock_universe su
            ON t.ticker_code = su.ticker_code
            WHERE t.run_id = %s
            GROUP BY
                t.run_id,
                COALESCE(su.sector[1], 'UNKNOWN'),
                su.sector[2],
                COALESCE(t.sell_info->>'reason', 'UNKNOWN')
        )
        INSERT INTO strategy_backtest_sector_analysis (
            run_id,
            sector_level1,
            sector_level2,
            market,
            universe,
            trades,
            avg_return,
            win_rate,
            total_pnl_contribution,
            avg_holding,
            major_exit_reason,
            avg_buy_flow,
            avg_buy_score
        )
        SELECT
            t.run_id,
            COALESCE(su.sector[1], 'UNKNOWN') AS sector_level1,
            su.sector[2] AS sector_level2,
            su.market,
            su.universe,
            COUNT(*) AS trades,
            AVG((t.sell_info->>'cum_return')::numeric) AS avg_return,
            SUM(CASE WHEN (t.sell_info->>'cum_return')::numeric > 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS win_rate,
            SUM((t.sell_info->>'cum_return')::numeric) AS total_pnl_contribution,
            AVG(t.holding_period) AS avg_holding,
            rr.exit_reason AS major_exit_reason,
            AVG(CASE WHEN t.buy_info ? 'flow' THEN (t.buy_info->>'flow')::numeric END) AS avg_buy_flow,
            AVG(CASE WHEN t.buy_info ? 'score' THEN (t.buy_info->>'score')::numeric END) AS avg_buy_score
        FROM strategy_trade_log t
        JOIN stock_universe su
        ON t.ticker_code = su.ticker_code
        LEFT JOIN reason_rank rr
        ON t.run_id = rr.run_id
        AND COALESCE(su.sector[1], 'UNKNOWN') = rr.sector_level1
        AND COALESCE(su.sector[2], '') = COALESCE(rr.sector_level2, '')
        AND rr.rn = 1
        WHERE t.run_id = %s
        GROUP BY
            t.run_id,
            COALESCE(su.sector[1], 'UNKNOWN'),
            su.sector[2],
            su.market,
            su.universe,
            rr.exit_reason
        """,
        (run_id, run_id),
    )

    # 18) market_block bad bucket analysis
    cur.execute(
        f"""
        INSERT INTO strategy_backtest_mbweak_bucket_analysis
            (
                run_id, holding_bucket, candidate_type, flow_bucket, final_bucket,
                profit_bucket, trades, avg_return, win_rate, avg_flow, avg_final, avg_holding
            )
        SELECT
            %s,
            CASE
                WHEN holding_period <= {mb_h1} THEN '3이하'
                WHEN holding_period <= {mb_h2} THEN '4~5'
                WHEN holding_period <= {mb_h3} THEN '6~8'
                ELSE '9+'
            END AS holding_bucket,
            CASE
                WHEN sell_info->>'reason' = 'market_block_quality_drop' THEN 'quality_drop'
                WHEN sell_info->>'reason' = 'market_block_weak_other' THEN 'weak_other'
                ELSE 'other'
            END AS candidate_type,
            CASE
                WHEN (sell_info->>'flow')::numeric < 0.30 THEN 'flow<0.30'
                WHEN (sell_info->>'flow')::numeric < 0.50 THEN '0.30~0.50'
                WHEN (sell_info->>'flow')::numeric < 0.70 THEN '0.50~0.70'
                WHEN (sell_info->>'flow')::numeric < 0.85 THEN '0.70~0.85'
                ELSE '0.85+'
            END AS flow_bucket,
            CASE
                WHEN (sell_info->>'final')::numeric < 0.15 THEN 'final<0.15'
                WHEN (sell_info->>'final')::numeric < 0.30 THEN '0.15~0.30'
                WHEN (sell_info->>'final')::numeric < 0.50 THEN '0.30~0.50'
                ELSE '0.50+'
            END AS final_bucket,
            CASE
                WHEN (sell_info->>'cum_return')::numeric < {p1} THEN '< {P1_LABEL}'
                WHEN (sell_info->>'cum_return')::numeric < {p2} THEN '{P1_LABEL} ~ {P2_LABEL}'
                WHEN (sell_info->>'cum_return')::numeric < {p3} THEN '{P2_LABEL} ~ {P3_LABEL}'
                WHEN (sell_info->>'cum_return')::numeric < {p4} THEN '{P3_LABEL} ~ {P4_LABEL}'
                ELSE '>= {P4_LABEL}'
            END AS profit_bucket,
            COUNT(*),
            AVG((sell_info->>'cum_return')::numeric),
            SUM(CASE WHEN (sell_info->>'cum_return')::numeric > 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*),
            AVG((sell_info->>'flow')::numeric),
            AVG((sell_info->>'final')::numeric),
            AVG(holding_period)
        FROM strategy_trade_log
        WHERE run_id = %s
        AND sell_info->>'reason' IN (
            'market_block_quality_drop',
            'market_block_weak_other'
        )
        AND sell_info ? 'flow'
        AND sell_info ? 'final'
        AND sell_info ? 'cum_return'
        GROUP BY 2, 3, 4, 5, 6
        """,
        (run_id, run_id),
    )

    # 19) market_block bad candidate analysis
    cur.execute(
        f"""
        INSERT INTO strategy_backtest_mbweak_candidate_analysis
            (
                run_id, ticker_code, company_name, buy_date, sell_date, holding_period,
                cum_return, flow_value, final_value, candidate_type,
                flow_bucket, final_bucket, profit_bucket
            )
        SELECT
            %s,
            ticker_code,
            company_name,
            buy_date,
            sell_date,
            holding_period,
            (sell_info->>'cum_return')::numeric AS cum_return,
            (sell_info->>'flow')::numeric AS flow_value,
            (sell_info->>'final')::numeric AS final_value,
            CASE
                WHEN sell_info->>'reason' = 'market_block_quality_drop' THEN 'quality_drop'
                WHEN sell_info->>'reason' = 'market_block_weak_other' THEN 'weak_other'
                ELSE 'other'
            END AS candidate_type,
            CASE
                WHEN (sell_info->>'flow')::numeric < 0.30 THEN 'flow<0.30'
                WHEN (sell_info->>'flow')::numeric < 0.50 THEN '0.30~0.50'
                WHEN (sell_info->>'flow')::numeric < 0.70 THEN '0.50~0.70'
                WHEN (sell_info->>'flow')::numeric < 0.85 THEN '0.70~0.85'
                ELSE '0.85+'
            END AS flow_bucket,
            CASE
                WHEN (sell_info->>'final')::numeric < 0.15 THEN 'final<0.15'
                WHEN (sell_info->>'final')::numeric < 0.30 THEN '0.15~0.30'
                WHEN (sell_info->>'final')::numeric < 0.45 THEN '0.30~0.45'
                WHEN (sell_info->>'final')::numeric < 0.60 THEN '0.45~0.60'
                ELSE '0.60+'
            END AS final_bucket,
            CASE
                WHEN (sell_info->>'cum_return')::numeric < {p1} THEN '< -{P1_LABEL}'
                WHEN (sell_info->>'cum_return')::numeric < {p2} THEN '-{P1_LABEL} ~ -{P2_LABEL}'
                WHEN (sell_info->>'cum_return')::numeric < {p3} THEN '-{P2_LABEL} ~ {P3_LABEL}'
                WHEN (sell_info->>'cum_return')::numeric < {p4} THEN '{P3_LABEL} ~ {P4_LABEL}'
                ELSE '{P4_LABEL}+'
            END AS profit_bucket
        FROM strategy_trade_log
        WHERE run_id = %s
        AND sell_info->>'reason' IN (
            'market_block_quality_drop',
            'market_block_weak_other'
        )
        AND sell_info ? 'flow'
        AND sell_info ? 'final'
        AND sell_info ? 'cum_return'
        """,
        (run_id, run_id),
    )

    # 20) market_block_weak_other detailed analysis
    cur.execute(
        """
        INSERT INTO strategy_backtest_mbweak_other_analysis
            (
                run_id,
                holding_bucket,
                flow_bucket,
                final_bucket,
                combo_type,
                trades,
                avg_return,
                win_rate,
                avg_flow,
                avg_final,
                avg_holding
            )
        SELECT
            %s,
            CASE
                WHEN holding_period <= 3 THEN '3이하'
                WHEN holding_period <= 5 THEN '4~5'
                WHEN holding_period <= 8 THEN '6~8'
                ELSE '9+'
            END AS holding_bucket,
            CASE
                WHEN (sell_info->>'flow')::numeric < 0.30 THEN 'flow<0.30'
                WHEN (sell_info->>'flow')::numeric < 0.50 THEN '0.30~0.50'
                WHEN (sell_info->>'flow')::numeric < 0.70 THEN '0.50~0.70'
                ELSE '0.70+'
            END AS flow_bucket,
            CASE
                WHEN (sell_info->>'final')::numeric < 0.15 THEN 'final<0.15'
                WHEN (sell_info->>'final')::numeric < 0.30 THEN '0.15~0.30'
                WHEN (sell_info->>'final')::numeric < 0.50 THEN '0.30~0.50'
                ELSE '0.50+'
            END AS final_bucket,
            CASE
                WHEN (sell_info->>'flow')::numeric < 0.50
                AND (sell_info->>'final')::numeric < 0.30
                    THEN 'both_weak'
                WHEN (sell_info->>'flow')::numeric < 0.50
                AND (sell_info->>'final')::numeric >= 0.30
                    THEN 'flow_only_weak'
                WHEN (sell_info->>'flow')::numeric >= 0.50
                AND (sell_info->>'final')::numeric < 0.30
                    THEN 'final_only_weak'
                ELSE 'neither_clear'
            END AS combo_type,
            COUNT(*),
            AVG((sell_info->>'cum_return')::numeric),
            SUM(
                CASE
                    WHEN (sell_info->>'cum_return')::numeric > 0 THEN 1
                    ELSE 0
                END
            ) * 1.0 / COUNT(*),
            AVG((sell_info->>'flow')::numeric),
            AVG((sell_info->>'final')::numeric),
            AVG(holding_period)
        FROM strategy_trade_log
        WHERE run_id = %s
        AND sell_info->>'reason' = 'market_block_weak_other'
        AND sell_info ? 'flow'
        AND sell_info ? 'final'
        AND sell_info ? 'cum_return'
        GROUP BY 2, 3, 4, 5
        """,
        (run_id, run_id),
    )

    conn.commit()
    cur.close()


if __name__ == "__main__":
    conn = get_conn()
    cur = conn.cursor()
    try:
        run_id = get_latest_run_id(cur)
        if not run_id:
            raise RuntimeError("최신 run_id 없음")
    finally:
        cur.close()

    try:
        run_analysis_extended(conn, run_id)
        print("✅ analysis_extended 완료")
    finally:
        conn.close()
