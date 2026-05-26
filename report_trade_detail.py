from datetime import datetime

from port_strategy_research.report_data_loader import (
    get_conn,
    get_latest_run_id,
    get_run_summary,
    load_trade_details,
    get_thresholds,
    load_reason_stats,
    load_mbweak_stats,
    to_float,
)

from port_strategy_research.report_formatter import (
    build_buy_reason,
    build_sell_reason,
    label_market_signal,
    label_bool,
)


def generate_trade_detail_report(run_id: str, output_file: str = "03_거래_상세_리포트.txt"):
    conn = get_conn()
    cur = conn.cursor()

    try:
        run_summary = get_run_summary(cur, run_id)
        thresholds = get_thresholds(run_summary["config_snapshot"])
        trades = load_trade_details(cur, run_id)
        reason_stats = load_reason_stats(cur, run_id)
        mbweak_stats = load_mbweak_stats(cur, run_id)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"실행일자: {datetime.now().strftime('%Y-%m-%d')}\n")
            f.write(f"실행 ID: {run_id}\n")
            f.write(f"엔진: {run_summary['strategy_version']}\n\n")

            f.write("거래 상세\n")
            f.write("=============================\n\n")

            for row in trades:
                (
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
                    sell_info,
                ) = row

                f.write(f"[{company_name} / {ticker_code}]\n")
                f.write(f"- 매수일: {buy_date}\n")
                f.write(f"- 매도일: {sell_date}\n")
                f.write(f"- 보유일: {holding_period}\n")
                f.write(f"- 최종 수익률: {return_pct}\n")

                entry_market_signal = (buy_info or {}).get("entry_market_signal")
                position_size = to_float((buy_info or {}).get("position_size"), None)
                short_score = to_float((buy_info or {}).get("short"), None)
                vol_20d = to_float((buy_info or {}).get("vol"), None)
                intraday_range = to_float((buy_info or {}).get("intraday_range"), None)
                has_info_flag = (buy_info or {}).get("has_info_flag", None)

                if entry_market_signal:
                    f.write(f"- 진입 시장 상태: {label_market_signal(entry_market_signal)}\n")
                if position_size is not None:
                    f.write(f"- 포지션 크기: {position_size:.4f}\n")
                if short_score is not None:
                    f.write(f"- 진입 시 공매도 압력: {short_score:.2f}\n")
                if vol_20d is not None:
                    f.write(f"- 진입 시 20일 변동성: {vol_20d:.4f}\n")
                if intraday_range is not None:
                    f.write(f"- 진입 시 장중 변동폭: {intraday_range:.4f}\n")
                if has_info_flag is not None:
                    f.write(f"- 정보 신호 존재 여부: {label_bool(bool(has_info_flag))}\n")

                f.write(
                    f"- 매수가격(시가/종가/저가): "
                    f"{buy_open_price} / {buy_close_price} / {buy_low_price}\n"
                )
                f.write(
                    f"- 매도가격(시가/종가/저가): "
                    f"{sell_open_price} / {sell_close_price} / {sell_low_price}\n"
                )

                f.write("- 매수 사유\n")
                for line in build_buy_reason(buy_info or {}, thresholds):
                    f.write(f"  → {line}\n")

                f.write("- 매도 사유\n")
                for line in build_sell_reason(
                    sell_info=sell_info or {},
                    holding_days=int(holding_period or 0),
                    thresholds=thresholds,
                    reason_stats=reason_stats,
                    mbweak_stats=mbweak_stats,
                ):
                    f.write(f"  → {line}\n")

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
            raise RuntimeError("최신 실행 ID 없음")
    finally:
        cur.close()
        conn.close()

    generate_trade_detail_report(run_id)
    print("✅ 03_거래_상세_리포트.txt 생성 완료")