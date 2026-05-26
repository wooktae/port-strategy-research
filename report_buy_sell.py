from datetime import datetime

from port_strategy_research.report_data_loader import (
    get_conn,
    get_latest_run_id,
    get_run_summary,
    get_run_inputs,
    get_thresholds,
    load_reason_stats,
    load_holding_stats,
    load_mbweak_stats,
    get_dates,
    get_holdings_for_date,
    get_buys_for_date,
    get_sells_for_date,
    get_price_on_date,
    to_float,
)
from port_strategy_research.report_formatter import (
    pct_str,
    format_run_inputs,
    holding_comment,
    build_buy_reason,
    build_sell_reason,
    label_market_signal,
)


def _write_section(f, title: str):
    f.write(f"{title}\n")
    f.write("=============================\n")


def generate_buy_sell_report(run_id: str, output_file: str = "02_일자별매매리포트.txt"):
    conn = get_conn()
    cur = conn.cursor()

    try:
        run_summary = get_run_summary(cur, run_id)
        run_inputs = get_run_inputs(cur, run_id)
        thresholds = get_thresholds(run_summary["config_snapshot"])
        reason_stats = load_reason_stats(cur, run_id)
        holding_stats = load_holding_stats(cur, run_id)
        mbweak_stats = load_mbweak_stats(cur, run_id)
        date_rows = get_dates(cur, run_id)

        with open(output_file, "w", encoding="utf-8") as f:
            # --------------------------------------------------
            # 기본 정보
            # --------------------------------------------------
            f.write(f"실행일자: {datetime.now().strftime('%Y-%m-%d')}\n")
            f.write(f"엔진: {run_summary['strategy_version']}\n")
            f.write(f"전략명: {run_summary['strategy_name']}\n")
            f.write(f"실행 ID: {run_id}\n")
            f.write(
                f"백테스트 구간: "
                f"{run_summary['backtest_start_date']} ~ {run_summary['backtest_end_date']}\n"
            )
            f.write("\n")

            # --------------------------------------------------
            # 최종 결과
            # --------------------------------------------------
            _write_section(f, "최종 결과")
            f.write(f"누적 이익: {pct_str(run_summary['total_return'])}\n")
            f.write(f"최대 낙폭: {pct_str(run_summary['mdd'], signed=True)}\n")
            f.write(f"샤프 지수: {to_float(run_summary['sharpe'], 0.0):.2f}\n")
            f.write(f"총 거래수: {run_summary['trade_count']}\n")
            f.write(f"실험 입력값: {format_run_inputs(run_inputs)}\n")
            f.write("\n")

            # --------------------------------------------------
            # 일자별 매매
            # --------------------------------------------------
            _write_section(f, "일자별 매매")
            f.write("\n")

            for d, market_signal, position_count, daily_return, cum_return in date_rows:
                f.write(f"--- {d.strftime('%m/%d/%y')} ---\n")

                f.write(
                    f"시장 상태: {label_market_signal(market_signal)} "
                    f"(보유 종목 수 {int(position_count or 0)}, "
                    f"일 수익률 {pct_str(to_float(daily_return, 0.0), signed=True)}, "
                    f"누적 수익률 {pct_str(to_float(cum_return, 0.0))})\n\n"
                )

                # --------------------------------------------------
                # 1. 보유 종목
                # --------------------------------------------------
                holdings = get_holdings_for_date(cur, run_id, d)

                f.write("1. 보유 종목\n")
                if not holdings:
                    f.write(" - 없음\n")
                else:
                    for ticker_code, company_name, buy_date, buy_open_price in holdings:
                        buy_price = to_float(buy_open_price, None)
                        current_price = get_price_on_date(cur, ticker_code, d)
                        holding_days = (d - buy_date).days

                        if buy_price and current_price:
                            eval_return = (current_price / buy_price) - 1
                            extra = holding_comment(holding_days, holding_stats)

                            f.write(
                                f" - {company_name} "
                                f"(보유 {holding_days}일, "
                                f"평가 수익률 {pct_str(eval_return, signed=True)}{extra})\n"
                            )
                        else:
                            f.write(
                                f" - {company_name} "
                                f"(보유 {holding_days}일, 평가 수익률 계산 불가)\n"
                            )

                # --------------------------------------------------
                # 2. 매수
                # --------------------------------------------------
                buys = get_buys_for_date(cur, run_id, d)

                f.write("\n2. 매수\n")
                if not buys:
                    f.write(" - 없음\n")
                else:
                    for company_name, buy_info in buys:
                        buy_info = buy_info or {}
                        lines = build_buy_reason(buy_info, thresholds)

                        f.write(f" - {company_name}\n")
                        for line in lines:
                            f.write(f"   → {line}\n")

                # --------------------------------------------------
                # 3. 매도
                # --------------------------------------------------
                sells = get_sells_for_date(cur, run_id, d)

                f.write("\n3. 매도\n")
                if not sells:
                    f.write(" - 없음\n")
                else:
                    for company_name, sell_info, holding_period in sells:
                        sell_info = sell_info or {}

                        lines = build_sell_reason(
                            sell_info=sell_info,
                            holding_days=int(holding_period or 0),
                            thresholds=thresholds,
                            reason_stats=reason_stats,
                            mbweak_stats=mbweak_stats,
                        )

                        f.write(f" - {company_name}\n")
                        for line in lines:
                            f.write(f"   → {line}\n")

                f.write("\n")

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    conn = get_conn()
    cur = conn.cursor()

    try:
        run_id = get_latest_run_id(cur)
        if not run_id:
            raise RuntimeError("최신 실행_ID 없음")

        print(f"👉 최신 실행_ID: {run_id}")
    finally:
        cur.close()
        conn.close()

    generate_buy_sell_report(run_id, "02_일자별매매리포트.txt")
    print("✅ 02_일자별매매리포트.txt 생성 완료")