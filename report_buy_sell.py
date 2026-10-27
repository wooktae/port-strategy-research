"""Module that generates the per-date buy/sell text report.

It combines daily performance, holdings snapshot, new buys, and sell logs and writes them to a txt file.
Running it performs DB queries and local file writes.
"""

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
from port_strategy_research.report_locale import t, get_report_locale


def _write_section(f, title: str):
    f.write(f"{title}\n")
    f.write("=============================\n")


def generate_buy_sell_report(run_id: str, output_file: str = "02_일자별매매리포트.txt"):
    """Generate the per-date trading report for a single run_id into the given file."""
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
            # Basic information
            # --------------------------------------------------
            f.write(t(
                f"Run Date: {datetime.now().strftime('%Y-%m-%d')}\n",
                f"실행일자: {datetime.now().strftime('%Y-%m-%d')}\n",
            ))
            f.write(t(
                f"Engine: {run_summary['strategy_version']}\n",
                f"엔진: {run_summary['strategy_version']}\n",
            ))
            f.write(t(
                f"Strategy Name: {run_summary['strategy_name']}\n",
                f"전략명: {run_summary['strategy_name']}\n",
            ))
            f.write(t(
                f"Run ID: {run_id}\n",
                f"실행 ID: {run_id}\n",
            ))
            f.write(
                t(
                    f"Backtest Period: "
                    f"{run_summary['backtest_start_date']} ~ {run_summary['backtest_end_date']}\n",
                    f"백테스트 구간: "
                    f"{run_summary['backtest_start_date']} ~ {run_summary['backtest_end_date']}\n",
                )
            )
            f.write("\n")

            # --------------------------------------------------
            # Final results
            # --------------------------------------------------
            _write_section(f, t("Final Results", "최종 결과"))
            f.write(t(
                f"Cumulative Return: {pct_str(run_summary['total_return'])}\n",
                f"누적 이익: {pct_str(run_summary['total_return'])}\n",
            ))
            f.write(t(
                f"Max Drawdown: {pct_str(run_summary['mdd'], signed=True)}\n",
                f"최대 낙폭: {pct_str(run_summary['mdd'], signed=True)}\n",
            ))
            f.write(t(
                f"Sharpe Ratio: {to_float(run_summary['sharpe'], 0.0):.2f}\n",
                f"샤프 지수: {to_float(run_summary['sharpe'], 0.0):.2f}\n",
            ))
            f.write(t(
                f"Total Trades: {run_summary['trade_count']}\n",
                f"총 거래수: {run_summary['trade_count']}\n",
            ))
            f.write(t(
                f"Run Inputs: {format_run_inputs(run_inputs)}\n",
                f"실험 입력값: {format_run_inputs(run_inputs)}\n",
            ))
            f.write("\n")

            # --------------------------------------------------
            # Per-date trading
            # --------------------------------------------------
            _write_section(f, t("Per-Date Trading", "일자별 매매"))
            f.write("\n")

            for d, market_signal, position_count, daily_return, cum_return in date_rows:
                f.write(f"--- {d.strftime('%m/%d/%y')} ---\n")

                f.write(
                    t(
                        f"Market State: {label_market_signal(market_signal)} "
                        f"(holdings {int(position_count or 0)}, "
                        f"daily return {pct_str(to_float(daily_return, 0.0), signed=True)}, "
                        f"cumulative return {pct_str(to_float(cum_return, 0.0))})\n\n",
                        f"시장 상태: {label_market_signal(market_signal)} "
                        f"(보유 종목 수 {int(position_count or 0)}, "
                        f"일 수익률 {pct_str(to_float(daily_return, 0.0), signed=True)}, "
                        f"누적 수익률 {pct_str(to_float(cum_return, 0.0))})\n\n",
                    )
                )

                # --------------------------------------------------
                # 1. Holdings
                # --------------------------------------------------
                holdings = get_holdings_for_date(cur, run_id, d)

                f.write(t("1. Holdings\n", "1. 보유 종목\n"))
                if not holdings:
                    f.write(t(" - None\n", " - 없음\n"))
                else:
                    for ticker_code, company_name, buy_date, buy_open_price in holdings:
                        buy_price = to_float(buy_open_price, None)
                        current_price = get_price_on_date(cur, ticker_code, d)
                        holding_days = (d - buy_date).days

                        if buy_price and current_price:
                            eval_return = (current_price / buy_price) - 1
                            extra = holding_comment(holding_days, holding_stats)

                            f.write(
                                t(
                                    f" - {company_name} "
                                    f"(held {holding_days} days, "
                                    f"eval return {pct_str(eval_return, signed=True)}{extra})\n",
                                    f" - {company_name} "
                                    f"(보유 {holding_days}일, "
                                    f"평가 수익률 {pct_str(eval_return, signed=True)}{extra})\n",
                                )
                            )
                        else:
                            f.write(
                                t(
                                    f" - {company_name} "
                                    f"(held {holding_days} days, eval return not computable)\n",
                                    f" - {company_name} "
                                    f"(보유 {holding_days}일, 평가 수익률 계산 불가)\n",
                                )
                            )

                # --------------------------------------------------
                # 2. Buys
                # --------------------------------------------------
                buys = get_buys_for_date(cur, run_id, d)

                f.write(t("\n2. Buys\n", "\n2. 매수\n"))
                if not buys:
                    f.write(t(" - None\n", " - 없음\n"))
                else:
                    for company_name, buy_info in buys:
                        buy_info = buy_info or {}
                        lines = build_buy_reason(buy_info, thresholds)

                        f.write(f" - {company_name}\n")
                        for line in lines:
                            f.write(f"   → {line}\n")

                # --------------------------------------------------
                # 3. Sells
                # --------------------------------------------------
                sells = get_sells_for_date(cur, run_id, d)

                f.write(t("\n3. Sells\n", "\n3. 매도\n"))
                if not sells:
                    f.write(t(" - None\n", " - 없음\n"))
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
