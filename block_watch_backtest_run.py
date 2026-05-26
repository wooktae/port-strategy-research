from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Sequence, Tuple

import psycopg2
import psycopg2.extras


# ============================================================
# DB_CONFIG import
# ============================================================

try:
    from port_strategy_common.config import DB_CONFIG
except Exception as e:
    raise RuntimeError(
        "DB_CONFIG import 실패. port_strategy_common.config 경로를 확인해줘."
    ) from e


# ============================================================
# Common BLOCK Watch Logic
# ============================================================

try:
    from port_strategy_common.common_block_watch import evaluate_block_watch_candidate
except Exception as e:
    raise RuntimeError(
        "common_block_watch.evaluate_block_watch_candidate import 실패. "
        "C:\\Workspaces\\port_strategy_common\\common_block_watch.py 파일과 PYTHONPATH를 확인해줘."
    ) from e


# ============================================================
# Data Models
# ============================================================

@dataclass(frozen=True)
class BlockDate:
    data_date: date
    market_signal: str


@dataclass(frozen=True)
class WatchCriteria:
    min_flow_score: Decimal
    min_final_score: Decimal
    max_volatility_20d: Decimal
    min_intraday_range: Optional[Decimal]
    max_intraday_range: Decimal

    def describe(self) -> Dict[str, Optional[str]]:
        return {
            "min_flow_score": str(self.min_flow_score),
            "min_final_score": str(self.min_final_score),
            "max_volatility_20d": str(self.max_volatility_20d),
            "min_intraday_range": (
                str(self.min_intraday_range)
                if self.min_intraday_range is not None
                else None
            ),
            "max_intraday_range": str(self.max_intraday_range),
        }


@dataclass
class WatchCandidate:
    signal_date: date
    ticker_code: str
    stock_name: Optional[str]
    close_price: Decimal

    flow_score: Optional[Decimal]
    final_score: Optional[Decimal]
    info_score: Optional[Decimal]
    volatility_20d: Optional[Decimal]
    intraday_range: Optional[Decimal]
    short_pressure_score: Optional[Decimal]

    watch_reason: Optional[str]
    watch_detail: Dict[str, Any]

    return_1d: Optional[Decimal] = None
    return_3d: Optional[Decimal] = None
    return_5d: Optional[Decimal] = None
    return_10d: Optional[Decimal] = None


# ============================================================
# Basic Utils
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


def parse_decimal_arg(value: Optional[str], field_name: str) -> Optional[Decimal]:
    if value is None:
        return None

    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as e:
        raise ValueError(f"{field_name} 값이 Decimal로 변환되지 않아: {value}") from e


def safe_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def pct(value: Optional[Decimal]) -> str:
    if value is None:
        return "-"

    return f"{value * Decimal('100'):.2f}%"


def avg(values: Sequence[Optional[Decimal]]) -> Optional[Decimal]:
    valid = [v for v in values if v is not None]

    if not valid:
        return None

    return sum(valid) / Decimal(len(valid))


def win_rate(values: Sequence[Optional[Decimal]]) -> Optional[Decimal]:
    valid = [v for v in values if v is not None]

    if not valid:
        return None

    wins = [v for v in valid if v > 0]
    return Decimal(len(wins)) / Decimal(len(valid))


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


def dict_cursor(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def print_section(title: str) -> None:
    print()
    print("========================================")
    print(f"[{title}]")
    print("========================================")


# ============================================================
# Latest Backtest Run / BLOCK Date Loading
# ============================================================

def get_latest_backtest_run_id(conn) -> str:
    """
    최신 백테스트 run_id 조회.

    실제 DDL 기준:
    - strategy_backtest_run PK: run_id
    - 최신 기준: started_at DESC
    - run_mode: BACKTEST
    """
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


def get_latest_backtest_data_date(conn, run_id: str) -> Optional[date]:
    """
    최신 backtest_daily date 조회.
    --end-date 미지정 시 이 날짜를 분석 종료일로 사용.
    """
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

    if not row:
        return None

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


def load_block_dates_from_backtest_daily(
    conn,
    start_date: date,
    end_date: Optional[date],
    limit_days: Optional[int],
) -> Tuple[str, List[BlockDate], int, date]:
    """
    기존 backtest 결과에서 market_signal = BLOCK 날짜만 추출한다.

    중요:
    - read-only select만 수행
    - 기존 backtest_research_run 결과와 분리
    - strategy_daily_signal / strategy_execution_order / trade_log write 없음
    """
    run_id = get_latest_backtest_run_id(conn)

    if end_date is None:
        latest_data_date = get_latest_backtest_data_date(conn, run_id)
        if latest_data_date is None:
            raise RuntimeError("strategy_backtest_daily에서 최신 data_date를 찾지 못했어.")
        resolved_end_date = latest_data_date
    else:
        resolved_end_date = end_date

    rows = load_backtest_days(
        conn=conn,
        run_id=run_id,
        start_date=start_date,
        end_date=resolved_end_date,
    )

    total_days = len(rows)
    block_dates = [
        BlockDate(
            data_date=r["date"],
            market_signal=str(r["market_signal"]).upper(),
        )
        for r in rows
        if str(r["market_signal"]).upper() == "BLOCK"
    ]

    if limit_days is not None:
        block_dates = block_dates[:limit_days]

    print_section("BLOCK Date Summary")
    print(f"source_latest_backtest_run_id : {run_id}")
    print(f"period                        : {start_date} ~ {resolved_end_date}")
    print(f"total_backtest_days            : {total_days}")
    print(f"block_days                     : {len(block_dates)}")

    if total_days > 0:
        print(f"block_ratio                    : {len(block_dates) / total_days:.2%}")
    else:
        print("block_ratio                    : -")

    if limit_days is not None:
        print(f"limit_days                     : {limit_days}")

    return run_id, block_dates, total_days, resolved_end_date


def summarize_block_streaks(
    conn,
    run_id: str,
    start_date: date,
    end_date: date,
) -> None:
    """
    전체 backtest 거래일 캘린더 기준으로 BLOCK 연속 구간을 요약한다.
    calendar day 기준이 아니라 strategy_backtest_daily의 거래일 순서 기준.
    """
    rows = load_backtest_days(
        conn=conn,
        run_id=run_id,
        start_date=start_date,
        end_date=end_date,
    )

    streaks: List[List[date]] = []
    current: List[date] = []

    for r in rows:
        d = r["date"]
        signal = str(r["market_signal"]).upper()

        if signal == "BLOCK":
            current.append(d)
        else:
            if current:
                streaks.append(current)
                current = []

    if current:
        streaks.append(current)

    print_section("BLOCK Streak Summary")

    if not streaks:
        print("BLOCK streak 없음")
        return

    lengths = [len(s) for s in streaks]
    longest = max(streaks, key=len)

    print(f"streak_count       : {len(streaks)}")
    print(f"max_streak_days    : {len(longest)}")
    print(f"max_streak_period  : {longest[0]} ~ {longest[-1]}")
    print(f"avg_streak_days    : {sum(lengths) / len(lengths):.2f}")

    print()
    print("[Top BLOCK Streaks]")
    top_streaks = sorted(streaks, key=len, reverse=True)[:10]

    for idx, s in enumerate(top_streaks, start=1):
        print(
            f"{idx:>2}. {s[0]} ~ {s[-1]} "
            f"days={len(s)}"
        )


# ============================================================
# Watch Candidate Generation
# ============================================================

def load_stock_features_for_date(conn, signal_date: date) -> List[Dict[str, Any]]:
    """
    BLOCK 날짜의 전체 종목 feature 조회.

    주의:
    - 현재 DB의 pre_total_stock_daily_feature 실제 컬럼에는 company_name/stock_name이 없을 수 있음.
    - 분석 핵심은 ticker_code 기준이므로 종목명은 NULL AS stock_name으로 처리.
    - 나중에 stock_master 조인 가능하면 종목명 보강 가능.
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
            ORDER BY ticker_code
            """,
            (signal_date,),
        )
        return list(cur.fetchall())


def evaluate_watch(
    row: Dict[str, Any],
    criteria: WatchCriteria,
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    common_block_watch.evaluate_block_watch_candidate() 실제 시그니처 기준.

    기본 Watch 조건은 common_block_watch 재사용.
    추가 실험 조건인 min_intraday_range는 이 분석 파일에서만 별도로 적용한다.

    이 함수는 매수/주문/신호 저장을 하지 않고 관찰 여부만 반환한다.
    """
    decision = evaluate_block_watch_candidate(
        market_signal="BLOCK",
        stock_context=row,
        min_flow_score=criteria.min_flow_score,
        min_final_score=criteria.min_final_score,
        max_volatility_20d=criteria.max_volatility_20d,
        max_intraday_range=criteria.max_intraday_range,
    )

    if not decision.is_watch:
        return decision.is_watch, decision.watch_reason, decision.watch_detail

    # 분석 전용 추가 조건: intraday_range 하한
    # common_block_watch에는 max만 있으므로 min은 여기서만 적용한다.
    if criteria.min_intraday_range is not None:
        intraday_range = to_decimal(row.get("intraday_range"))

        if intraday_range is None:
            detail = dict(decision.watch_detail or {})
            detail["analysis_extra_failed_reason"] = "MISSING_INTRADAY_RANGE_FOR_MIN_FILTER"
            return False, "MISSING_INTRADAY_RANGE_FOR_MIN_FILTER", detail

        if intraday_range < criteria.min_intraday_range:
            detail = dict(decision.watch_detail or {})
            detail["analysis_extra_failed_reason"] = "INTRADAY_RANGE_TOO_NARROW"
            detail["analysis_extra_criteria"] = {
                "min_intraday_range": str(criteria.min_intraday_range),
                "actual_intraday_range": str(intraday_range),
            }
            return False, "INTRADAY_RANGE_TOO_NARROW", detail

    return decision.is_watch, decision.watch_reason, decision.watch_detail


def build_watch_candidates(
    conn,
    block_dates: List[BlockDate],
    criteria: WatchCriteria,
) -> List[WatchCandidate]:
    candidates: List[WatchCandidate] = []

    print_section("Watch Candidate Generation")

    print("[Watch Criteria]")
    for k, v in criteria.describe().items():
        print(f"{k:<24}: {v}")
    print()

    for idx, block in enumerate(block_dates, start=1):
        rows = load_stock_features_for_date(conn, block.data_date)
        day_candidates: List[WatchCandidate] = []

        for row in rows:
            is_watch, watch_reason, watch_detail = evaluate_watch(row, criteria)

            if not is_watch:
                continue

            close_price = to_decimal(row.get("close_price"))
            if close_price is None or close_price <= 0:
                continue

            candidate = WatchCandidate(
                signal_date=row["date"],
                ticker_code=row["ticker_code"],
                stock_name=row.get("stock_name"),
                close_price=close_price,
                flow_score=to_decimal(row.get("flow_score")),
                final_score=to_decimal(row.get("final_score")),
                info_score=to_decimal(row.get("info_score")),
                volatility_20d=to_decimal(row.get("volatility_20d")),
                intraday_range=to_decimal(row.get("intraday_range")),
                short_pressure_score=to_decimal(row.get("short_pressure_score")),
                watch_reason=watch_reason,
                watch_detail=watch_detail or {},
            )

            day_candidates.append(candidate)

        candidates.extend(day_candidates)

        print(
            f"{idx:>3}. date={block.data_date} "
            f"stocks={len(rows):>4} "
            f"watch_candidates={len(day_candidates):>3}"
        )

    print()
    print(f"total_watch_candidates : {len(candidates)}")

    return candidates


# ============================================================
# Forward Return Calculation
# ============================================================

def load_future_prices(
    conn,
    ticker_code: str,
    signal_date: date,
    max_days: int = 10,
) -> List[Dict[str, Any]]:
    """
    같은 ticker_code 기준 signal_date 이후 거래일 종가 조회.
    1번째/3번째/5번째/10번째 거래일 수익률 계산에 사용.
    """
    with dict_cursor(conn) as cur:
        cur.execute(
            """
            SELECT
                date,
                close_price
            FROM pre_total_stock_daily_feature
            WHERE ticker_code = %s
              AND date > %s
              AND close_price IS NOT NULL
            ORDER BY date
            LIMIT %s
            """,
            (ticker_code, signal_date, max_days),
        )
        return list(cur.fetchall())


def calc_return(
    base_price: Decimal,
    future_price: Optional[Decimal],
) -> Optional[Decimal]:
    if future_price is None:
        return None

    if base_price is None or base_price <= 0:
        return None

    return (future_price / base_price) - Decimal("1")


def attach_forward_returns(
    conn,
    candidates: List[WatchCandidate],
) -> None:
    print_section("Forward Return Calculation")

    for idx, candidate in enumerate(candidates, start=1):
        future_prices = load_future_prices(
            conn=conn,
            ticker_code=candidate.ticker_code,
            signal_date=candidate.signal_date,
            max_days=10,
        )

        def nth_close(n: int) -> Optional[Decimal]:
            if len(future_prices) < n:
                return None
            return to_decimal(future_prices[n - 1]["close_price"])

        candidate.return_1d = calc_return(candidate.close_price, nth_close(1))
        candidate.return_3d = calc_return(candidate.close_price, nth_close(3))
        candidate.return_5d = calc_return(candidate.close_price, nth_close(5))
        candidate.return_10d = calc_return(candidate.close_price, nth_close(10))

        if idx % 100 == 0:
            print(f"processed_candidates : {idx}/{len(candidates)}")

    print(f"processed_candidates : {len(candidates)}/{len(candidates)}")


# ============================================================
# Analysis Helpers
# ============================================================

def get_return_values(
    candidates: List[WatchCandidate],
    field: str,
) -> List[Optional[Decimal]]:
    return [getattr(c, field) for c in candidates]


def print_return_summary(candidates: List[WatchCandidate]) -> None:
    print_section("Return Summary")

    print(f"candidate_count : {len(candidates)}")

    horizons = [
        ("1D", "return_1d"),
        ("3D", "return_3d"),
        ("5D", "return_5d"),
        ("10D", "return_10d"),
    ]

    for label, field in horizons:
        values = get_return_values(candidates, field)
        valid_count = len([v for v in values if v is not None])

        print(
            f"{label:<4} "
            f"valid={valid_count:<5} "
            f"avg={pct(avg(values)):<10} "
            f"win_rate={pct(win_rate(values))}"
        )


def print_daily_candidate_summary(candidates: List[WatchCandidate]) -> None:
    grouped: Dict[date, List[WatchCandidate]] = {}

    for c in candidates:
        grouped.setdefault(c.signal_date, []).append(c)

    print_section("Daily Candidate Summary")

    for d in sorted(grouped.keys()):
        rows = grouped[d]
        print(
            f"{d} "
            f"count={len(rows):>3} "
            f"avg_1d={pct(avg([r.return_1d for r in rows])):<9} "
            f"avg_3d={pct(avg([r.return_3d for r in rows])):<9} "
            f"avg_5d={pct(avg([r.return_5d for r in rows])):<9} "
            f"avg_10d={pct(avg([r.return_10d for r in rows]))}"
        )


def bucket_value(
    value: Optional[Decimal],
    buckets: List[Tuple[str, Optional[Decimal], Optional[Decimal]]],
) -> str:
    if value is None:
        return "NULL"

    for label, low, high in buckets:
        if low is not None and value < low:
            continue

        if high is not None and value >= high:
            continue

        return label

    return "OTHER"


def print_bucket_analysis(
    title: str,
    candidates: List[WatchCandidate],
    field: str,
    buckets: List[Tuple[str, Optional[Decimal], Optional[Decimal]]],
) -> None:
    grouped: Dict[str, List[WatchCandidate]] = {}

    for c in candidates:
        label = bucket_value(getattr(c, field), buckets)
        grouped.setdefault(label, []).append(c)

    print_section(title)

    bucket_order = [b[0] for b in buckets] + ["NULL", "OTHER"]

    for label in bucket_order:
        rows = grouped.get(label, [])

        if not rows:
            continue

        print(
            f"{label:<16} "
            f"count={len(rows):>5} "
            f"avg_1d={pct(avg([r.return_1d for r in rows])):<9} "
            f"win_1d={pct(win_rate([r.return_1d for r in rows])):<9} "
            f"avg_3d={pct(avg([r.return_3d for r in rows])):<9} "
            f"win_3d={pct(win_rate([r.return_3d for r in rows])):<9} "
            f"avg_5d={pct(avg([r.return_5d for r in rows])):<9} "
            f"win_5d={pct(win_rate([r.return_5d for r in rows])):<9} "
            f"avg_10d={pct(avg([r.return_10d for r in rows])):<9} "
            f"win_10d={pct(win_rate([r.return_10d for r in rows]))}"
        )


def print_repeated_tickers(
    candidates: List[WatchCandidate],
    limit: int = 20,
) -> None:
    grouped: Dict[str, List[WatchCandidate]] = {}

    for c in candidates:
        grouped.setdefault(c.ticker_code, []).append(c)

    rows = sorted(
        grouped.items(),
        key=lambda item: len(item[1]),
        reverse=True,
    )[:limit]

    print_section("Repeated Watch Tickers TOP")

    if not rows:
        print("반복 등장 종목 없음")
        return

    for idx, (ticker, items) in enumerate(rows, start=1):
        stock_name = items[0].stock_name or ""
        print(
            f"{idx:>2}. {ticker} {stock_name} "
            f"count={len(items):<4} "
            f"avg_1d={pct(avg([x.return_1d for x in items])):<9} "
            f"avg_3d={pct(avg([x.return_3d for x in items])):<9} "
            f"avg_5d={pct(avg([x.return_5d for x in items])):<9} "
            f"avg_10d={pct(avg([x.return_10d for x in items]))}"
        )


def print_reason_summary(candidates: List[WatchCandidate]) -> None:
    counter = Counter(c.watch_reason or "UNKNOWN" for c in candidates)

    print_section("Watch Reason Summary")

    for reason, count in counter.most_common():
        print(f"{reason:<40} count={count}")


def print_best_worst(
    candidates: List[WatchCandidate],
    field: str,
    limit: int = 10,
) -> None:
    valid = [c for c in candidates if getattr(c, field) is not None]

    print_section(f"Best / Worst by {field}")

    if not valid:
        print("유효 수익률 데이터 없음")
        return

    best = sorted(
        valid,
        key=lambda c: getattr(c, field),
        reverse=True,
    )[:limit]

    worst = sorted(
        valid,
        key=lambda c: getattr(c, field),
    )[:limit]

    print()
    print("[BEST]")

    for idx, c in enumerate(best, start=1):
        print(
            f"{idx:>2}. {c.signal_date} "
            f"{c.ticker_code} {c.stock_name or ''} "
            f"{field}={pct(getattr(c, field)):<9} "
            f"flow={c.flow_score} "
            f"final={c.final_score} "
            f"vol={c.volatility_20d} "
            f"range={c.intraday_range}"
        )

    print()
    print("[WORST]")

    for idx, c in enumerate(worst, start=1):
        print(
            f"{idx:>2}. {c.signal_date} "
            f"{c.ticker_code} {c.stock_name or ''} "
            f"{field}={pct(getattr(c, field)):<9} "
            f"flow={c.flow_score} "
            f"final={c.final_score} "
            f"vol={c.volatility_20d} "
            f"range={c.intraday_range}"
        )


def print_exception_buy_judgement(candidates: List[WatchCandidate]) -> None:
    print_section("BLOCK_EXCEPTION_BUY Experiment Judgement - Draft")

    horizons = [
        ("1D", "return_1d"),
        ("3D", "return_3d"),
        ("5D", "return_5d"),
        ("10D", "return_10d"),
    ]

    scored: List[Tuple[str, Optional[Decimal], Optional[Decimal], int]] = []

    for label, field in horizons:
        values = get_return_values(candidates, field)
        avg_return = avg(values)
        wr = win_rate(values)
        valid_count = len([v for v in values if v is not None])
        scored.append((label, avg_return, wr, valid_count))

    for label, avg_return, wr, valid_count in scored:
        print(
            f"{label:<4} "
            f"valid={valid_count:<5} "
            f"avg={pct(avg_return):<10} "
            f"win_rate={pct(wr)}"
        )

    valid_scored = [
        s for s in scored
        if s[1] is not None and s[2] is not None and s[3] > 0
    ]

    print()

    if not valid_scored:
        print("judgement : 미래 수익률 데이터가 부족해서 판단 불가")
        return

    best_by_avg = sorted(
        valid_scored,
        key=lambda x: x[1],
        reverse=True,
    )[0]

    best_label, best_avg, best_wr, best_valid_count = best_by_avg

    print(
        f"best_horizon_by_avg : {best_label} "
        f"avg={pct(best_avg)} "
        f"win_rate={pct(best_wr)} "
        f"valid={best_valid_count}"
    )

    if best_avg > 0 and best_wr >= Decimal("0.55"):
        print(
            "judgement : 평균수익률과 승률이 모두 양호해 보여. "
            "다음 단계에서 특정 score/volatility/range bucket만 좁혀 "
            "BLOCK_EXCEPTION_BUY 별도 실험 버전을 만들 가치가 있어."
        )
    elif best_avg > 0 and best_wr >= Decimal("0.50"):
        print(
            "judgement : 평균수익률은 양수이고 승률도 최소 기준은 넘을 수 있어. "
            "전체 예외매수보다는 조건부 예외매수 후보로만 검토하는 게 좋아."
        )
    elif best_avg > 0:
        print(
            "judgement : 평균수익률은 양수지만 승률이 약해. "
            "소수 급등 종목에 의존했는지 Best/Worst와 bucket 분석을 같이 봐야 해."
        )
    else:
        print(
            "judgement : 전체 Watch 후보 기준으로는 예외매수 근거가 약해. "
            "현재는 Watch를 관찰용으로 유지하는 쪽이 안전해."
        )


def run_analysis(candidates: List[WatchCandidate]) -> None:
    print_return_summary(candidates)
    print_daily_candidate_summary(candidates)
    print_reason_summary(candidates)

    score_buckets = [
        ("<0.45", None, Decimal("0.45")),
        ("0.45~0.60", Decimal("0.45"), Decimal("0.60")),
        ("0.60~0.75", Decimal("0.60"), Decimal("0.75")),
        ("0.75~0.90", Decimal("0.75"), Decimal("0.90")),
        (">=0.90", Decimal("0.90"), None),
    ]

    vol_buckets = [
        ("<0.03", None, Decimal("0.03")),
        ("0.03~0.05", Decimal("0.03"), Decimal("0.05")),
        ("0.05~0.08", Decimal("0.05"), Decimal("0.08")),
        ("0.08~0.10", Decimal("0.08"), Decimal("0.10")),
        (">=0.10", Decimal("0.10"), None),
    ]

    range_buckets = [
        ("<0.03", None, Decimal("0.03")),
        ("0.03~0.05", Decimal("0.03"), Decimal("0.05")),
        ("0.05~0.08", Decimal("0.05"), Decimal("0.08")),
        ("0.08~0.12", Decimal("0.08"), Decimal("0.12")),
        (">=0.12", Decimal("0.12"), None),
    ]

    print_bucket_analysis(
        title="flow_score Bucket Analysis",
        candidates=candidates,
        field="flow_score",
        buckets=score_buckets,
    )

    print_bucket_analysis(
        title="final_score Bucket Analysis",
        candidates=candidates,
        field="final_score",
        buckets=score_buckets,
    )

    print_bucket_analysis(
        title="volatility_20d Bucket Analysis",
        candidates=candidates,
        field="volatility_20d",
        buckets=vol_buckets,
    )

    print_bucket_analysis(
        title="intraday_range Bucket Analysis",
        candidates=candidates,
        field="intraday_range",
        buckets=range_buckets,
    )

    print_repeated_tickers(candidates, limit=20)
    print_best_worst(candidates, field="return_5d", limit=10)
    print_best_worst(candidates, field="return_10d", limit=10)
    print_exception_buy_judgement(candidates)


# ============================================================
# Verification / Safety
# ============================================================

def print_safety_notice() -> None:
    print_section("Safety Guard")
    print("mode                              : READ_ONLY / MEMORY_ONLY")
    print("insert strategy_daily_signal       : NO")
    print("insert strategy_execution_order    : NO")
    print("insert strategy_block_watch_candidate : NO")
    print("insert strategy_trade_log          : NO")
    print("affect Sharpe/MDD/CumReturn        : NO")
    print("purpose                           : BLOCK exception buy feasibility analysis only")


# ============================================================
# Main
# ============================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="BLOCK 구간 Watch 후보 사후 수익률 분석용 read-only backtest"
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
        "--limit-days",
        type=int,
        default=None,
        help="BLOCK 날짜 앞에서 N개만 테스트. 빠른 검증용",
    )

    parser.add_argument(
        "--min-flow-score",
        default="0.75",
        help="Watch 후보 최소 flow_score. 기본값: 0.75",
    )

    parser.add_argument(
        "--min-final-score",
        default="0.45",
        help="Watch 후보 최소 final_score. 기본값: 0.45",
    )

    parser.add_argument(
        "--max-volatility-20d",
        default="0.10",
        help="Watch 후보 최대 volatility_20d. 기본값: 0.10",
    )

    parser.add_argument(
        "--min-intraday-range",
        default=None,
        help="분석 전용 intraday_range 최소값. 미지정 시 하한 없음",
    )

    parser.add_argument(
        "--max-intraday-range",
        default="0.12",
        help="Watch 후보 최대 intraday_range. 기본값: 0.12",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    start_date = safe_date(args.start_date)
    end_date = safe_date(args.end_date) if args.end_date else None

    criteria = WatchCriteria(
        min_flow_score=parse_decimal_arg(args.min_flow_score, "min_flow_score"),
        min_final_score=parse_decimal_arg(args.min_final_score, "min_final_score"),
        max_volatility_20d=parse_decimal_arg(args.max_volatility_20d, "max_volatility_20d"),
        min_intraday_range=parse_decimal_arg(args.min_intraday_range, "min_intraday_range"),
        max_intraday_range=parse_decimal_arg(args.max_intraday_range, "max_intraday_range"),
    )

    print_section("Block Watch Backtest Run")
    print(f"start_date : {start_date}")
    print(f"end_date   : {end_date or 'LATEST_BACKTEST_DATA_DATE'}")
    print(f"limit_days : {args.limit_days}")
    print("version    : block_watch_backtest_run.v2.criteria")
    print("mode       : READ_ONLY / MEMORY_ONLY")
    print(f"criteria   : {criteria.describe()}")

    print_safety_notice()

    with get_conn() as conn:
        run_id, block_dates, total_days, resolved_end_date = load_block_dates_from_backtest_daily(
            conn=conn,
            start_date=start_date,
            end_date=end_date,
            limit_days=args.limit_days,
        )

        summarize_block_streaks(
            conn=conn,
            run_id=run_id,
            start_date=start_date,
            end_date=resolved_end_date,
        )

        if not block_dates:
            print()
            print("BLOCK 날짜가 없어서 종료.")
            return

        candidates = build_watch_candidates(
            conn=conn,
            block_dates=block_dates,
            criteria=criteria,
        )

        if not candidates:
            print()
            print("Watch 후보가 없어서 종료.")
            return

        attach_forward_returns(
            conn=conn,
            candidates=candidates,
        )

        run_analysis(candidates)

    print_section("DONE")
    print("DB write 없이 Block Watch 과거 분석 완료.")


if __name__ == "__main__":
    main()