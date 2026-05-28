"""백테스트 리포트 생성에 필요한 DB 조회 helper 모듈.

run 메타데이터, 일별 성과, 일별 포지션 snapshot, 거래 로그, 분석 테이블을 읽는다.
DB 연결은 `INTEREST_DB_*` 환경변수를 사용하는 `get_db_config()`를 통해 구성하며,
이 모듈은 조회 helper 중심이지만 실행 시 실제 DB 접속이 발생한다.
"""

import psycopg2
from decimal import Decimal
from typing import Any, Optional

from port_strategy_research.db_config import get_db_config


def get_conn():
    """리포트 조회용 PostgreSQL connection을 생성한다."""
    return psycopg2.connect(**get_db_config())


def to_float(v: Any, default: Optional[float] = 0.0) -> Optional[float]:
    if v is None:
        return default
    if isinstance(v, Decimal):
        return float(v)
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def get_latest_run_id(cur) -> Optional[str]:
    """가장 최근에 시작된 backtest run_id를 조회한다."""
    cur.execute(
        """
        SELECT run_id
        FROM strategy_backtest_run
        ORDER BY started_at DESC
        LIMIT 1
        """
    )
    row = cur.fetchone()
    return row[0] if row else None


def get_run_summary(cur, run_id: str) -> dict:
    """리포트 상단에 필요한 backtest run 요약 정보를 조회한다."""
    cur.execute(
        """
        SELECT
            strategy_name,
            strategy_version,
            started_at,
            finished_at,
            backtest_start_date,
            backtest_end_date,
            total_return,
            mdd,
            sharpe,
            trade_count,
            config_snapshot
        FROM strategy_backtest_run
        WHERE run_id = %s
        """,
        (run_id,),
    )
    row = cur.fetchone()
    if not row:
        raise ValueError(f"run_id not found: {run_id}")

    return {
        "strategy_name": row[0],
        "strategy_version": row[1],
        "started_at": row[2],
        "finished_at": row[3],
        "backtest_start_date": row[4],
        "backtest_end_date": row[5],
        "total_return": to_float(row[6], 0.0),
        "mdd": to_float(row[7], 0.0),
        "sharpe": to_float(row[8], 0.0),
        "trade_count": row[9],
        "config_snapshot": row[10] if isinstance(row[10], dict) else {},
    }


def get_run_inputs(cur, run_id: str) -> dict[str, str]:
    cur.execute(
        """
        SELECT input_key, input_value
        FROM strategy_run_input
        WHERE run_id = %s
        ORDER BY input_key
        """,
        (run_id,),
    )
    return {k: v for k, v in cur.fetchall()}


def get_dates(cur, run_id: str):
    cur.execute(
        """
        SELECT date, market_signal, position_count, daily_return, cum_return
        FROM strategy_backtest_daily
        WHERE run_id = %s
        ORDER BY date
        """,
        (run_id,),
    )
    return cur.fetchall()


def load_reason_stats(cur, run_id: str) -> dict[str, dict]:
    cur.execute(
        """
        SELECT reason, trades, avg_return, win_rate
        FROM strategy_backtest_analysis
        WHERE run_id = %s
        """,
        (run_id,),
    )
    rows = cur.fetchall()

    result: dict[str, dict] = {}
    for reason, trades, avg_return, win_rate in rows:
        result[str(reason)] = {
            "trades": int(trades or 0),
            "avg_return": to_float(avg_return, 0.0),
            "win_rate": to_float(win_rate, 0.0),
        }
    return result


def load_holding_stats(cur, run_id: str) -> dict[int, dict]:
    cur.execute(
        """
        SELECT holding_period, trades, avg_return, win_rate
        FROM strategy_backtest_holding_analysis
        WHERE run_id = %s
        """,
        (run_id,),
    )
    rows = cur.fetchall()

    result: dict[int, dict] = {}
    for holding_period, trades, avg_return, win_rate in rows:
        result[int(holding_period)] = {
            "trades": int(trades or 0),
            "avg_return": to_float(avg_return, 0.0),
            "win_rate": to_float(win_rate, 0.0),
        }
    return result


def load_mbweak_stats(cur, run_id: str) -> dict[int, dict]:
    cur.execute(
        """
        SELECT holding_period, trades, avg_return, avg_flow, avg_final
        FROM strategy_backtest_mbweak_analysis
        WHERE run_id = %s
        """,
        (run_id,),
    )
    rows = cur.fetchall()

    result: dict[int, dict] = {}
    for holding_period, trades, avg_return, avg_flow, avg_final in rows:
        result[int(holding_period)] = {
            "trades": int(trades or 0),
            "avg_return": to_float(avg_return, 0.0),
            "avg_flow": to_float(avg_flow, 0.0),
            "avg_final": to_float(avg_final, 0.0),
        }
    return result


def get_thresholds(config_snapshot: dict) -> dict:
    buy_cfg = config_snapshot.get("buy", {})
    sell_cfg = config_snapshot.get("sell", {})
    filter_cfg = config_snapshot.get("filter", {})
    market_cfg = config_snapshot.get("market", {})

    return {
        "buy_day_intraday_stop_loss": to_float(
            buy_cfg.get("buy_day_intraday_stop_loss"), -0.10
        ),
        "flow_min": to_float(filter_cfg.get("flow_min"), 0.62),
        "final_min": to_float(filter_cfg.get("final_min"), 0.05),
        "final_strong": to_float(filter_cfg.get("final_strong"), 0.08),
        "final_extreme": to_float(filter_cfg.get("final_extreme"), 0.13),
        "hard_stop_daily_return": to_float(sell_cfg.get("hard_stop_daily_return"), -0.12),
        "sell_short_pressure": to_float(sell_cfg.get("sell_short_pressure"), 1.30),
        "sell_flow_breakdown": to_float(sell_cfg.get("sell_flow_breakdown"), -0.10),
        "sell_final_breakdown": to_float(sell_cfg.get("sell_final_breakdown"), 0.00),
        "max_holding_days": int(to_float(sell_cfg.get("max_holding_days"), 15)),
        "profit_protect_cum_return": to_float(
            sell_cfg.get("profit_protect_cum_return"), 0.07
        ),
        "profit_protect_daily_drop": to_float(
            sell_cfg.get("profit_protect_daily_drop"), -0.04
        ),
        "early_risk_cut_daily_return": to_float(
            sell_cfg.get("early_risk_cut_daily_return"), -0.08
        ),
        "early_cut_cum_return": to_float(
            sell_cfg.get("early_cut_cum_return"), -0.07
        ),
        "stale_loser_cum_return": to_float(
            sell_cfg.get("stale_loser_cum_return"), -0.02
        ),
        "stale_loser_flow": to_float(
            sell_cfg.get("stale_loser_flow"), -0.05
        ),
        "market_block_min_keep_profit": to_float(
            sell_cfg.get("market_block_min_keep_profit"), 0.023
        ),
        "market_block_sell_min_holding_days": int(
            to_float(sell_cfg.get("market_block_sell_min_holding_days"), 3)
        ),
        "market_block_max_win_holding_days": int(
            to_float(sell_cfg.get("market_block_max_win_holding_days"), 8)
        ),
        "block_market_regime_score": to_float(
            market_cfg.get("block_market_regime_score"), -0.11
        ),
        "defensive_market_regime_score": to_float(
            market_cfg.get("defensive_market_regime_score"), -0.06
        ),
        "aggressive_market_regime_score": to_float(
            market_cfg.get("aggressive_market_regime_score"), 0.05
        ),
        "market_block_strong_min_flow": to_float(
            sell_cfg.get("market_block_strong_min_flow"), None
        ),
        "market_block_strong_min_final": to_float(
            sell_cfg.get("market_block_strong_min_final"), None
        ),
        "market_block_strong_keep_profit": to_float(
            sell_cfg.get("market_block_strong_keep_profit"), None
        ),
    }


def get_price_on_date(cur, ticker_code: str, price_date) -> Optional[float]:
    cur.execute(
        """
        SELECT close_price
        FROM interest_price_raw
        WHERE ticker_code = %s
          AND price_date = %s
        """,
        (ticker_code, price_date),
    )
    row = cur.fetchone()
    return to_float(row[0], None) if row else None

def get_holdings_for_date(cur, run_id: str, d):
    """일자별 보유 현황을 일별 포지션 snapshot 테이블에서 조회한다."""
    cur.execute(
        """
        SELECT
            ticker_code,
            company_name,
            buy_date,
            entry_open_price
        FROM strategy_backtest_daily_position
        WHERE run_id = %s
          AND date = %s
        ORDER BY company_name
        """,
        (run_id, d),
    )
    return cur.fetchall()

def load_trade_details(cur, run_id: str):
    """완료 거래 상세 리포트에 사용할 거래 로그를 조회한다."""
    cur.execute(
        """
        SELECT
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
        FROM strategy_trade_log
        WHERE run_id = %s
        ORDER BY buy_date, company_name
        """,
        (run_id,),
    )
    return cur.fetchall()


def get_buys_for_date(cur, run_id: str, d):
    """해당 일자에 신규 진입한 종목 정보를 일별 포지션 snapshot에서 조회한다."""
    cur.execute(
        """
        SELECT
            company_name,
            entry_buy_info
        FROM strategy_backtest_daily_position
        WHERE run_id = %s
          AND date = %s
          AND buy_date = %s
        ORDER BY company_name
        """,
        (run_id, d, d),
    )
    return cur.fetchall()


def get_sells_for_date(cur, run_id: str, d):
    cur.execute(
        """
        SELECT company_name, sell_info, holding_period
        FROM strategy_trade_log
        WHERE run_id = %s
          AND sell_date = %s
        ORDER BY company_name
        """,
        (run_id, d),
    )
    return cur.fetchall()


def load_signal_holding_stats(cur, run_id: str):
    cur.execute(
        """
        SELECT entry_market_signal, holding_bucket, exit_reason, trades, avg_return, win_rate, avg_holding
        FROM strategy_backtest_signal_holding_analysis
        WHERE run_id = %s
        ORDER BY entry_market_signal, holding_bucket, exit_reason
        """,
        (run_id,),
    )
    return cur.fetchall()


def load_ticker_stats(cur, run_id: str):
    cur.execute(
        """
        SELECT ticker_code, company_name, trades, avg_return, win_rate,
               total_pnl_contribution, avg_holding, major_exit_reason,
               avg_buy_flow, avg_buy_score
        FROM strategy_backtest_ticker_analysis
        WHERE run_id = %s
        ORDER BY total_pnl_contribution ASC
        """,
        (run_id,),
    )
    return cur.fetchall()

def load_entry_stats(cur, run_id: str):
    cur.execute(
        """
        SELECT metric_name, bucket_label, trades, avg_return, win_rate, avg_holding
        FROM strategy_backtest_entry_analysis
        WHERE run_id = %s
        ORDER BY metric_name, bucket_label
        """,
        (run_id,),
    )
    return cur.fetchall()

def load_exit_trigger_stats(cur, run_id: str):
    cur.execute(
        """
        SELECT exit_reason, trigger_name, trades, avg_return, win_rate, avg_holding
        FROM strategy_backtest_exit_trigger_analysis
        WHERE run_id = %s
        ORDER BY exit_reason, trades DESC, trigger_name
        """,
        (run_id,),
    )
    return cur.fetchall()


def load_entry_day_stats(cur, run_id: str):
    cur.execute(
        """
        SELECT
            metric_name,
            bucket_label,
            trades,
            avg_day1_return,
            day1_win_rate,
            avg_exit_open_return,
            exit_open_win_rate,
            avg_final_return,
            final_win_rate
        FROM strategy_backtest_entry_day_analysis
        WHERE run_id = %s
        ORDER BY metric_name, bucket_label
        """,
        (run_id,),
    )
    return cur.fetchall()

def load_sector_stats(cur, run_id: str):
    cur.execute(
        """
        SELECT
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
        FROM strategy_backtest_sector_analysis
        WHERE run_id = %s
        ORDER BY total_pnl_contribution ASC, trades DESC
        """,
        (run_id,),
    )
    return cur.fetchall()

def load_mbweak_bucket_rows(cur, run_id: str):
    cur.execute(
        """
        SELECT
            holding_bucket,
            candidate_type,
            flow_bucket,
            final_bucket,
            profit_bucket,
            trades,
            avg_return,
            win_rate,
            avg_flow,
            avg_final,
            avg_holding
        FROM strategy_backtest_mbweak_bucket_analysis
        WHERE run_id = %s
        ORDER BY holding_bucket, candidate_type, flow_bucket, final_bucket, profit_bucket
        """,
        (run_id,),
    )
    return cur.fetchall()


def load_mbweak_candidate_rows(cur, run_id: str, limit: int = 20):
    cur.execute(
        """
        SELECT
            ticker_code,
            company_name,
            buy_date,
            sell_date,
            holding_period,
            cum_return,
            flow_value,
            final_value,
            candidate_type,
            flow_bucket,
            final_bucket,
            profit_bucket
        FROM strategy_backtest_mbweak_candidate_analysis
        WHERE run_id = %s
        ORDER BY
            cum_return DESC,
            holding_period,
            candidate_type
        LIMIT %s
        """,
        (run_id, limit),
    )
    return cur.fetchall()

def load_mbweak_other_rows(cur, run_id: str):
    cur.execute(
        """
        SELECT
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
        FROM strategy_backtest_mbweak_other_analysis
        WHERE run_id = %s
        ORDER BY
            holding_bucket,
            combo_type,
            avg_return
        """,
        (run_id,),
    )
    return cur.fetchall()


