"""block 장세 예외 매수 후보를 별도 규칙으로 검증하는 연구용 백테스트 스크립트.

CLI threshold를 받아 후보를 만들고 forward return, 거래 요약, 월별 요약을 출력한다.
DB 연결이 발생하며 backtest 유사 계산을 수행하므로 명시 승인 없이 실행하지 않는다.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd
import psycopg2
import psycopg2.extras

from port_strategy_research.backtest_metrics import calculate_mdd, calculate_sharpe
from port_strategy_research.db_config import get_db_config


# ============================================================
# Data Models
# ============================================================

@dataclass(frozen=True)
class BlockExceptionCriteria:
    min_flow_score: Decimal
    min_final_score: Decimal
    max_volatility_20d: Decimal
    min_intraday_range: Decimal
    max_intraday_range: Decimal

    def describe(self) -> Dict[str, str]:
        return {
            "min_flow_score": str(self.min_flow_score),
            "min_final_score": str(self.min_final_score),
            "max_volatility_20d": str(self.max_volatility_20d),
            "min_intraday_range": str(self.min_intraday_range),
            "max_intraday_range": str(self.max_intraday_range),
        }


@dataclass
class Candidate:
    signal_date: date
    ticker_code: str
    stock_name: Optional[str]
    close_price: Decimal
    flow_score: Decimal
    final_score: Decimal
    info_score: Optional[Decimal]
    volatility_20d: Decimal
    intraday_range: Decimal
    short_pressure_score: Optional[Decimal]


@dataclass
class Trade:
    ticker_code: str
    stock_name: Optional[str]
    buy_date: date
    sell_date: date
    holding_days: int
    position_size: Decimal
    buy_price: Decimal
    sell_price: Decimal
    raw_return: Decimal
    weighted_return: Decimal
    flow_score: Decimal
    final_score: Decimal
    volatility_20d: Decimal
    intraday_range: Decimal


# ============================================================
# Utils
# ============================================================

def to_decimal(value: Any) -> Optional[Decimal]:
    if value is None:
        return None

    if isinstance(value, Decimal):
        return value

    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def parse_decimal_arg(value: str, field_name: str) -> Decimal:
    parsed = to_decimal(value)

    if parsed is None:
        raise ValueError(f"{field_name} 값이 Decimal로 변환되지 않아: {value}")

    return parsed


def safe_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def pct(value: Optional[Decimal | float]) -> str:
    if value is None:
        return "-"

    return f"{float(value) * 100:.2f}%"


def get_conn():
    return psycopg2.connect(**get_db_config())


def dict_cursor(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def print_section(title: str) -> None:
    print()
    print("========================================")
    print(f"[{title}]")
    print("========================================")


# ============================================================
# Latest Backtest / Calendar
# ============================================================

def get_latest_backtest_run_id(conn) -> str:
    with dict_cursor(conn) as cur:
        cur.execute(
            """
            SELECT run_id
            FROM strategy_backtest_run
            WHERE run_mode = 'BACKTEST'
            ORDER BY started_at DESC NULLS LAST, run_id DESC
            LIMIT 1
            """
        )
        row = cur.fetchone()

    if not row:
        raise RuntimeError("strategy_backtest_run에서 최신 BACKTEST run_id를 찾지 못했어.")

    return str(row["run_id"])


def get_latest_backtest_data_date(conn, run_id: str) -> date:
    with dict_cursor(conn) as cur:
        cur.execute(
            """
            SELECT MAX(date) AS max_date
            FROM strategy_backtest_daily
            WHERE run_id = %s
            """,
            (run_id,),
        )
        row = cur.fetchone()

    if not row or row["max_date"] is None:
        raise RuntimeError("strategy_backtest_daily에서 최신 date를 찾지 못했어.")

    return row["max_date"]


def load_backtest_days(
    conn,
    run_id: str,
    start_date: date,
    end_date: date,
) -> List[Dict[str, Any]]:
    with dict_cursor(conn) as cur:
        cur.execute(
            """
            SELECT
                date,
                market_signal
            FROM strategy_backtest_daily
            WHERE run_id = %s
              AND date BETWEEN %s AND %s
            ORDER BY date
            """,
            (run_id, start_date, end_date),
        )
        return list(cur.fetchall())


def load_trading_dates(
    conn,
    start_date: date,
    end_date: date,
) -> List[date]:
    """
    pre_total_stock_daily_feature 기준 전체 거래일 캘린더 조회.
    """
    with dict_cursor(conn) as cur:
        cur.execute(
            """
            SELECT DISTINCT date
            FROM pre_total_stock_daily_feature
            WHERE date BETWEEN %s AND %s
            ORDER BY date
            """,
            (start_date, end_date),
        )
        rows = cur.fetchall()

    return [r["date"] for r in rows]


def get_nth_trading_date_after(
    trading_dates: List[date],
    base_date: date,
    holding_days: int,
) -> Optional[date]:
    """
    base_date 이후 N번째 거래일 반환.
    holding_days=10이면 base_date보다 큰 거래일 중 10번째.
    """
    future_dates = [d for d in trading_dates if d > base_date]

    if len(future_dates) < holding_days:
        return None

    return future_dates[holding_days - 1]


# ============================================================
# Candidate Loading
# ============================================================

def load_block_dates(
    conn,
    run_id: str,
    start_date: date,
    end_date: date,
) -> List[date]:
    rows = load_backtest_days(
        conn=conn,
        run_id=run_id,
        start_date=start_date,
        end_date=end_date,
    )

    return [
        r["date"]
        for r in rows
        if str(r["market_signal"]).upper() == "BLOCK"
    ]


def load_candidates_for_date(
    conn,
    signal_date: date,
    criteria: BlockExceptionCriteria,
    max_candidates_per_day: int,
) -> List[Candidate]:
    """
    BLOCK_EXCEPTION_BUY v0 후보 조회.

    종목명은 현재 pre_total_stock_daily_feature 실제 컬럼에 없을 수 있으므로 NULL 처리.
    필요 시 stock_master 조인으로 보강 가능.
    """
    with dict_cursor(conn) as cur:
        cur.execute(
            """
            SELECT
                date,
                ticker_code,
                NULL::text AS stock_name,
                close_price,
                flow_score,
                final_score,
                info_score,
                volatility_20d,
                intraday_range,
                short_pressure_score
            FROM pre_total_stock_daily_feature
            WHERE date = %s
              AND close_price IS NOT NULL
              AND flow_score IS NOT NULL
              AND final_score IS NOT NULL
              AND volatility_20d IS NOT NULL
              AND intraday_range IS NOT NULL
              AND flow_score >= %s
              AND final_score >= %s
              AND volatility_20d <= %s
              AND intraday_range >= %s
              AND intraday_range <= %s
            ORDER BY final_score DESC, flow_score DESC, intraday_range DESC, ticker_code
            LIMIT %s
            """,
            (
                signal_date,
                criteria.min_flow_score,
                criteria.min_final_score,
                criteria.max_volatility_20d,
                criteria.min_intraday_range,
                criteria.max_intraday_range,
                max_candidates_per_day,
            ),
        )
        rows = cur.fetchall()

    candidates: List[Candidate] = []

    for r in rows:
        close_price = to_decimal(r["close_price"])
        flow_score = to_decimal(r["flow_score"])
        final_score = to_decimal(r["final_score"])
        volatility_20d = to_decimal(r["volatility_20d"])
        intraday_range = to_decimal(r["intraday_range"])

        if (
            close_price is None
            or close_price <= 0
            or flow_score is None
            or final_score is None
            or volatility_20d is None
            or intraday_range is None
        ):
            continue

        candidates.append(
            Candidate(
                signal_date=r["date"],
                ticker_code=r["ticker_code"],
                stock_name=r.get("stock_name"),
                close_price=close_price,
                flow_score=flow_score,
                final_score=final_score,
                info_score=to_decimal(r.get("info_score")),
                volatility_20d=volatility_20d,
                intraday_range=intraday_range,
                short_pressure_score=to_decimal(r.get("short_pressure_score")),
            )
        )

    return candidates


def get_close_price(
    conn,
    ticker_code: str,
    target_date: date,
) -> Optional[Decimal]:
    with dict_cursor(conn) as cur:
        cur.execute(
            """
            SELECT close_price
            FROM pre_total_stock_daily_feature
            WHERE ticker_code = %s
              AND date = %s
              AND close_price IS NOT NULL
            """,
            (ticker_code, target_date),
        )
        row = cur.fetchone()

    if not row:
        return None

    return to_decimal(row["close_price"])


# ============================================================
# Backtest Core
# ============================================================

def build_trades(
    conn,
    block_dates: List[date],
    trading_dates: List[date],
    criteria: BlockExceptionCriteria,
    holding_days: int,
    max_candidates_per_day: int,
    max_open_positions: int,
    position_size: Decimal,
) -> List[Trade]:
    """
    독립 미니 백테스트.

    설계:
    - BLOCK 날짜에 조건 통과 후보를 매수했다고 가정
    - 진입가: signal_date close_price
    - 청산가: holding_days 뒤 close_price
    - 동일 ticker 중복 포지션은 허용하지 않음
    - 동시 보유 최대 개수 제한
    - DB write 없음
    """
    trades: List[Trade] = []
    open_positions: List[Trade] = []

    print_section("BLOCK_EXCEPTION_BUY Trade Build")

    for idx, signal_date in enumerate(block_dates, start=1):
        # 이미 청산일이 지난 포지션은 open_positions에서 제거
        open_positions = [
            t for t in open_positions
            if t.sell_date > signal_date
        ]

        available_slots = max_open_positions - len(open_positions)

        if available_slots <= 0:
            print(
                f"{idx:>3}. date={signal_date} "
                f"skip=MAX_OPEN_POSITIONS "
                f"open={len(open_positions)}"
            )
            continue

        candidates = load_candidates_for_date(
            conn=conn,
            signal_date=signal_date,
            criteria=criteria,
            max_candidates_per_day=max_candidates_per_day,
        )

        if not candidates:
            print(
                f"{idx:>3}. date={signal_date} "
                f"candidates=0 "
                f"open={len(open_positions)}"
            )
            continue

        # 현재 열려 있는 ticker는 중복 진입 방지
        open_tickers = {t.ticker_code for t in open_positions}

        selected: List[Candidate] = []

        for candidate in candidates:
            if candidate.ticker_code in open_tickers:
                continue

            selected.append(candidate)

            if len(selected) >= min(max_candidates_per_day, available_slots):
                break

        built_count = 0

        for candidate in selected:
            sell_date = get_nth_trading_date_after(
                trading_dates=trading_dates,
                base_date=candidate.signal_date,
                holding_days=holding_days,
            )

            if sell_date is None:
                continue

            sell_price = get_close_price(
                conn=conn,
                ticker_code=candidate.ticker_code,
                target_date=sell_date,
            )

            if sell_price is None or sell_price <= 0:
                continue

            raw_return = (sell_price / candidate.close_price) - Decimal("1")
            weighted_return = raw_return * position_size

            trade = Trade(
                ticker_code=candidate.ticker_code,
                stock_name=candidate.stock_name,
                buy_date=candidate.signal_date,
                sell_date=sell_date,
                holding_days=holding_days,
                position_size=position_size,
                buy_price=candidate.close_price,
                sell_price=sell_price,
                raw_return=raw_return,
                weighted_return=weighted_return,
                flow_score=candidate.flow_score,
                final_score=candidate.final_score,
                volatility_20d=candidate.volatility_20d,
                intraday_range=candidate.intraday_range,
            )

            trades.append(trade)
            open_positions.append(trade)
            built_count += 1

        print(
            f"{idx:>3}. date={signal_date} "
            f"candidates={len(candidates):>2} "
            f"selected={len(selected):>2} "
            f"built={built_count:>2} "
            f"open={len(open_positions):>2}"
        )

    print()
    print(f"total_trades : {len(trades)}")

    return trades


def build_daily_equity_curve(
    trading_dates: List[date],
    start_date: date,
    end_date: date,
    trades: List[Trade],
) -> pd.DataFrame:
    """
    청산일에 weighted_return을 반영하는 단순 equity curve.
    진입~보유 중 mark-to-market은 하지 않는다.

    목적:
    - BLOCK_EXCEPTION_BUY v0 조건 자체의 실현 손익 기여도 확인
    - 기존 backtest 엔진에 섞기 전 독립 검증
    """
    date_range = [
        d for d in trading_dates
        if start_date <= d <= end_date
    ]

    returns_by_date: Dict[date, Decimal] = {}

    for trade in trades:
        returns_by_date[trade.sell_date] = (
            returns_by_date.get(trade.sell_date, Decimal("0"))
            + trade.weighted_return
        )

    rows: List[Dict[str, Any]] = []
    cum_return = Decimal("1")

    for d in date_range:
        daily_return = returns_by_date.get(d, Decimal("0"))
        cum_return = cum_return * (Decimal("1") + daily_return)

        open_count = sum(
            1
            for t in trades
            if t.buy_date < d <= t.sell_date
        )

        rows.append(
            {
                "date": d,
                "daily_return": float(daily_return),
                "cum_return": float(cum_return),
                "position_count": open_count,
            }
        )

    return pd.DataFrame(rows)


# ============================================================
# Reporting
# ============================================================

def print_trade_summary(trades: List[Trade]) -> None:
    print_section("Trade Summary")

    if not trades:
        print("trade 없음")
        return

    returns = [t.raw_return for t in trades]
    wins = [r for r in returns if r > 0]

    avg_return = sum(returns) / Decimal(len(returns))
    win_rate = Decimal(len(wins)) / Decimal(len(returns))

    print(f"trade_count       : {len(trades)}")
    print(f"avg_trade_return  : {pct(avg_return)}")
    print(f"win_rate          : {pct(win_rate)}")

    print()
    print("[Best Trades]")
    for idx, t in enumerate(sorted(trades, key=lambda x: x.raw_return, reverse=True)[:10], start=1):
        print(
            f"{idx:>2}. {t.buy_date} -> {t.sell_date} "
            f"{t.ticker_code} {t.stock_name or ''} "
            f"ret={pct(t.raw_return):<8} "
            f"flow={t.flow_score} final={t.final_score} "
            f"vol={t.volatility_20d} range={t.intraday_range}"
        )

    print()
    print("[Worst Trades]")
    for idx, t in enumerate(sorted(trades, key=lambda x: x.raw_return)[:10], start=1):
        print(
            f"{idx:>2}. {t.buy_date} -> {t.sell_date} "
            f"{t.ticker_code} {t.stock_name or ''} "
            f"ret={pct(t.raw_return):<8} "
            f"flow={t.flow_score} final={t.final_score} "
            f"vol={t.volatility_20d} range={t.intraday_range}"
        )


def print_daily_result(df: pd.DataFrame) -> None:
    print_section("Daily Equity Result")

    if df.empty:
        print("daily result 없음")
        return

    total_return = float(df.iloc[-1]["cum_return"])
    mdd = float(calculate_mdd(df))
    sharpe = float(calculate_sharpe(df))

    print(df.tail(10).to_string(index=False))

    print()
    print(f"TOTAL RETURN : {total_return:.6f}")
    print(f"MDD          : {mdd:.4f}")
    print(f"Sharpe Ratio : {sharpe:.2f}")


def print_monthly_summary(trades: List[Trade]) -> None:
    print_section("Monthly Trade Summary")

    if not trades:
        print("trade 없음")
        return

    grouped: Dict[str, List[Trade]] = {}

    for t in trades:
        key = f"{t.buy_date.year:04d}-{t.buy_date.month:02d}"
        grouped.setdefault(key, []).append(t)

    for key in sorted(grouped.keys()):
        rows = grouped[key]
        returns = [t.raw_return for t in rows]
        wins = [r for r in returns if r > 0]
        avg_return = sum(returns) / Decimal(len(returns))
        win_rate = Decimal(len(wins)) / Decimal(len(returns))

        print(
            f"{key} "
            f"count={len(rows):>3} "
            f"avg={pct(avg_return):<8} "
            f"win={pct(win_rate)}"
        )


# ============================================================
# Safety Notice
# ============================================================

def print_safety_notice() -> None:
    print_section("Safety Guard")
    print("mode                           : READ_ONLY / MEMORY_ONLY")
    print("insert strategy_backtest_run    : NO")
    print("insert strategy_backtest_daily  : NO")
    print("insert strategy_trade_log       : NO")
    print("affect existing Sharpe/MDD      : NO")
    print("purpose                        : BLOCK_EXCEPTION_BUY v0 feasibility backtest")


# ============================================================
# Main
# ============================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="BLOCK_EXCEPTION_BUY v0 독립 콘솔 백테스트"
    )

    parser.add_argument(
        "--start-date",
        default="2023-01-27",
        help="분석 시작일. 기본값: 2023-01-27",
    )

    parser.add_argument(
        "--end-date",
        default=None,
        help="분석 종료일. 미지정 시 최신 strategy_backtest_daily.date 사용",
    )

    parser.add_argument(
        "--min-flow-score",
        default="0.90",
        help="최소 flow_score. 기본값: 0.90",
    )

    parser.add_argument(
        "--min-final-score",
        default="0.60",
        help="최소 final_score. 기본값: 0.60",
    )

    parser.add_argument(
        "--max-volatility-20d",
        default="0.08",
        help="최대 volatility_20d. 기본값: 0.08",
    )

    parser.add_argument(
        "--min-intraday-range",
        default="0.05",
        help="최소 intraday_range. 기본값: 0.05",
    )

    parser.add_argument(
        "--max-intraday-range",
        default="0.08",
        help="최대 intraday_range. 기본값: 0.08",
    )

    parser.add_argument(
        "--holding-days",
        type=int,
        default=10,
        help="고정 보유 거래일 수. 기본값: 10",
    )

    parser.add_argument(
        "--max-candidates-per-day",
        type=int,
        default=1,
        help="하루 최대 신규 진입 종목 수. 기본값: 1",
    )

    parser.add_argument(
        "--max-open-positions",
        type=int,
        default=4,
        help="동시 보유 최대 포지션 수. 기본값: 4",
    )

    parser.add_argument(
        "--position-size",
        default="0.10",
        help="종목당 포지션 크기. 기본값: 0.10",
    )

    return parser.parse_args()


def main() -> None:
    """CLI 인자를 파싱해 block 예외 매수 후보 백테스트를 수행한다."""
    args = parse_args()

    start_date = safe_date(args.start_date)

    criteria = BlockExceptionCriteria(
        min_flow_score=parse_decimal_arg(args.min_flow_score, "min_flow_score"),
        min_final_score=parse_decimal_arg(args.min_final_score, "min_final_score"),
        max_volatility_20d=parse_decimal_arg(args.max_volatility_20d, "max_volatility_20d"),
        min_intraday_range=parse_decimal_arg(args.min_intraday_range, "min_intraday_range"),
        max_intraday_range=parse_decimal_arg(args.max_intraday_range, "max_intraday_range"),
    )

    position_size = parse_decimal_arg(args.position_size, "position_size")

    print_section("BLOCK_EXCEPTION_BUY v0 Backtest Run")
    print(f"start_date              : {start_date}")
    print(f"end_date                : {args.end_date or 'LATEST_BACKTEST_DATA_DATE'}")
    print(f"criteria                : {criteria.describe()}")
    print(f"holding_days            : {args.holding_days}")
    print(f"max_candidates_per_day  : {args.max_candidates_per_day}")
    print(f"max_open_positions      : {args.max_open_positions}")
    print(f"position_size           : {position_size}")
    print("mode                    : READ_ONLY / MEMORY_ONLY")

    print_safety_notice()

    with get_conn() as conn:
        run_id = get_latest_backtest_run_id(conn)

        if args.end_date:
            end_date = safe_date(args.end_date)
        else:
            end_date = get_latest_backtest_data_date(conn, run_id)

        block_dates = load_block_dates(
            conn=conn,
            run_id=run_id,
            start_date=start_date,
            end_date=end_date,
        )

        trading_dates = load_trading_dates(
            conn=conn,
            start_date=start_date,
            end_date=end_date,
        )

        print_section("Input Summary")
        print(f"source_latest_backtest_run_id : {run_id}")
        print(f"period                        : {start_date} ~ {end_date}")
        print(f"trading_days                  : {len(trading_dates)}")
        print(f"block_days                    : {len(block_dates)}")

        trades = build_trades(
            conn=conn,
            block_dates=block_dates,
            trading_dates=trading_dates,
            criteria=criteria,
            holding_days=args.holding_days,
            max_candidates_per_day=args.max_candidates_per_day,
            max_open_positions=args.max_open_positions,
            position_size=position_size,
        )

        if not trades:
            print()
            print("생성된 trade가 없어서 종료.")
            return

        df = build_daily_equity_curve(
            trading_dates=trading_dates,
            start_date=start_date,
            end_date=end_date,
            trades=trades,
        )

        print_trade_summary(trades)
        print_monthly_summary(trades)
        print_daily_result(df)

    print_section("DONE")
    print("DB write 없이 BLOCK_EXCEPTION_BUY v0 독립 백테스트 완료.")


if __name__ == "__main__":
    main()
