"""Module that generates the backtest summary text report.

It reads the run summary, daily performance, and key analysis statistics and writes them to a human-readable txt file.
Running it performs DB queries and local file writes.
"""

from datetime import datetime

from port_strategy_common.config import REPORT_CONFIG
MBW_CFG = REPORT_CONFIG["mbweak"]

from port_strategy_research.report_data_loader import (
    get_conn,
    get_latest_run_id,
    get_run_summary,
    get_run_inputs,
    load_reason_stats,
    load_holding_stats,
    load_mbweak_stats,
    to_float,
    load_mbweak_bucket_rows,
    load_mbweak_candidate_rows,
    load_mbweak_other_rows,
)
from port_strategy_research.report_formatter import (
    pct_str,
    format_run_inputs,
    label_exit_reason,
    label_mbweak_combo,
)


def _candidate_label(candidate_type: str) -> str:
    return {
        "quality_drop": "질 저하형",
        "weak_other": "기타 약세형",
    }.get(candidate_type, candidate_type)


def _write_section_title(f, title: str):
    f.write(f"{title}\n")
    f.write("=============================\n")


def _write_empty(f):
    f.write("- 없음\n")


def generate_summary_report(run_id: str, output_file: str = "01_요약리포트.txt"):
    """Generate the summary report for a single run_id into the given file."""
    conn = get_conn()
    cur = conn.cursor()

    try:
        run_summary = get_run_summary(cur, run_id)
        run_inputs = get_run_inputs(cur, run_id)
        reason_stats = load_reason_stats(cur, run_id)
        holding_stats = load_holding_stats(cur, run_id)
        mbweak_stats = load_mbweak_stats(cur, run_id)
        mbweak_bucket_rows = load_mbweak_bucket_rows(cur, run_id)
        mbweak_candidate_rows = load_mbweak_candidate_rows(cur, run_id)
        mbweak_other_rows = load_mbweak_other_rows(cur, run_id)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"실행일자: {datetime.now().strftime('%Y-%m-%d')}\n")
            f.write(f"전략명: {run_summary['strategy_name']}\n")
            f.write(f"엔진: {run_summary['strategy_version']}\n")
            f.write(f"실행 ID: {run_id}\n")
            f.write(
                f"백테스트 구간: {run_summary['backtest_start_date']} ~ "
                f"{run_summary['backtest_end_date']}\n\n"
            )

            # --------------------------------------------------
            # Final results
            # --------------------------------------------------
            _write_section_title(f, "최종 결과")
            f.write(f"누적 이익: {pct_str(run_summary['total_return'])}\n")
            f.write(f"최대 낙폭: {pct_str(run_summary['mdd'], signed=True)}\n")
            f.write(f"샤프 지수: {to_float(run_summary['sharpe'], 0.0):.2f}\n")
            f.write(f"총 거래수: {run_summary['trade_count']}\n")
            f.write(f"실험 입력값: {format_run_inputs(run_inputs)}\n\n")

            # --------------------------------------------------
            # Exit reason statistics
            # --------------------------------------------------
            _write_section_title(f, "청산 사유 통계")
            for reason, stat in sorted(reason_stats.items()):
                f.write(
                    f"- {label_exit_reason(reason)}: "
                    f"{stat['trades']}건, "
                    f"평균 수익률 {pct_str(stat['avg_return'], signed=True)}, "
                    f"승률 {stat['win_rate'] * 100:.1f}%\n"
                )

            # --------------------------------------------------
            # Holding-period statistics
            # --------------------------------------------------
            f.write("\n")
            _write_section_title(f, "보유 기간 통계")
            for holding_days, stat in sorted(holding_stats.items()):
                f.write(
                    f"- {holding_days}일 보유: "
                    f"{stat['trades']}건, "
                    f"평균 수익률 {pct_str(stat['avg_return'], signed=True)}, "
                    f"승률 {stat['win_rate'] * 100:.1f}%\n"
                )

            # --------------------------------------------------
            # BLOCK loss group details
            # --------------------------------------------------
            f.write("\n")
            _write_section_title(f, "BLOCK 손실군 상세 (질 저하형 + 기타 약세형)")
            if not mbweak_stats:
                _write_empty(f)
            else:
                for holding_days, stat in sorted(mbweak_stats.items()):
                    f.write(
                        f"- {holding_days}일 보유: "
                        f"{stat['trades']}건, "
                        f"평균 수익률 {pct_str(stat['avg_return'], signed=True)}, "
                        f"평균 수급 점수 {to_float(stat['avg_flow'], 0.0):.3f}, "
                        f"평균 종합 점수 {to_float(stat['avg_final'], 0.0):.3f}\n"
                    )

            # --------------------------------------------------
            # BLOCK loss group summary
            # --------------------------------------------------
            f.write("\n")
            _write_section_title(f, "BLOCK 손실군 요약")

            quality_cnt = 0
            quality_ret_sum = 0.0
            weak_cnt = 0
            weak_ret_sum = 0.0

            holding_reason_map = {}
            profit_bucket_map = {}

            for row in mbweak_bucket_rows:
                (
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
                    avg_holding,
                ) = row

                trades = int(trades or 0)
                avg_return = to_float(avg_return, 0.0)

                if candidate_type == "quality_drop":
                    quality_cnt += trades
                    quality_ret_sum += trades * avg_return
                elif candidate_type == "weak_other":
                    weak_cnt += trades
                    weak_ret_sum += trades * avg_return

                key = (holding_bucket, candidate_type)
                if key not in holding_reason_map:
                    holding_reason_map[key] = {"trades": 0, "ret_sum": 0.0}
                holding_reason_map[key]["trades"] += trades
                holding_reason_map[key]["ret_sum"] += trades * avg_return

                if profit_bucket not in profit_bucket_map:
                    profit_bucket_map[profit_bucket] = 0
                profit_bucket_map[profit_bucket] += trades

            total_bad = quality_cnt + weak_cnt

            if total_bad == 0:
                _write_empty(f)
            else:
                quality_avg = quality_ret_sum / quality_cnt if quality_cnt else 0.0
                weak_avg = weak_ret_sum / weak_cnt if weak_cnt else 0.0

                f.write(
                    f"- 질 저하형: "
                    f"{quality_cnt}건, "
                    f"평균 수익률 {pct_str(quality_avg, signed=True)}\n"
                )
                f.write(
                    f"- 기타 약세형: "
                    f"{weak_cnt}건, "
                    f"평균 수익률 {pct_str(weak_avg, signed=True)}\n"
                )
                f.write(f"- 손실군 전체 거래 수: {total_bad}건\n")

            # --------------------------------------------------
            # Type summary by holding-period bucket
            # --------------------------------------------------
            f.write("\n")
            _write_section_title(f, "BLOCK 손실군 보유구간별 유형 요약")
            has_holding_reason = False

            for holding_bucket in MBW_CFG["holding_bucket_labels"]:
                for candidate_type in ["quality_drop", "weak_other"]:
                    key = (holding_bucket, candidate_type)
                    val = holding_reason_map.get(key)
                    if not val or val["trades"] == 0:
                        continue

                    candidate_label = _candidate_label(candidate_type)
                    has_holding_reason = True
                    avg_ret = val["ret_sum"] / val["trades"]

                    f.write(
                        f"- {holding_bucket} / {candidate_label}: "
                        f"{val['trades']}건, "
                        f"평균 수익률 {pct_str(avg_ret, signed=True)}\n"
                    )

            if not has_holding_reason:
                _write_empty(f)

            # --------------------------------------------------
            # Profit bucket summary
            # --------------------------------------------------
            f.write("\n")
            _write_section_title(f, "BLOCK 손실군 수익구간 요약")
            has_profit_bucket = False

            for bucket in MBW_CFG["profit_bucket_labels"]:
                cnt = profit_bucket_map.get(bucket, 0)
                if cnt > 0:
                    has_profit_bucket = True
                    f.write(f"- {bucket}: {cnt}건\n")

            if not has_profit_bucket:
                _write_empty(f)

            # --------------------------------------------------
            # BLOCK weak_other combo summary
            # --------------------------------------------------
            f.write("\n")
            _write_section_title(f, "기타 약세형 세부 조합 요약")

            weak_combo_map = {}
            weak_holding_combo_map = {}

            for row in mbweak_other_rows:
                (
                    holding_bucket,
                    flow_bucket,
                    final_bucket,
                    combo_type,
                    trades,
                    avg_return,
                    win_rate,
                    avg_flow,
                    avg_final,
                    avg_holding,
                ) = row

                trades = int(trades or 0)
                avg_return = to_float(avg_return, 0.0)
                avg_flow = to_float(avg_flow, 0.0)
                avg_final = to_float(avg_final, 0.0)
                avg_holding = to_float(avg_holding, 0.0)

                if combo_type not in weak_combo_map:
                    weak_combo_map[combo_type] = {
                        "trades": 0,
                        "ret_sum": 0.0,
                        "flow_sum": 0.0,
                        "final_sum": 0.0,
                        "holding_sum": 0.0,
                    }

                weak_combo_map[combo_type]["trades"] += trades
                weak_combo_map[combo_type]["ret_sum"] += trades * avg_return
                weak_combo_map[combo_type]["flow_sum"] += trades * avg_flow
                weak_combo_map[combo_type]["final_sum"] += trades * avg_final
                weak_combo_map[combo_type]["holding_sum"] += trades * avg_holding

                key = (holding_bucket, combo_type)
                if key not in weak_holding_combo_map:
                    weak_holding_combo_map[key] = {
                        "trades": 0,
                        "ret_sum": 0.0,
                        "flow_sum": 0.0,
                        "final_sum": 0.0,
                        "holding_sum": 0.0,
                    }

                weak_holding_combo_map[key]["trades"] += trades
                weak_holding_combo_map[key]["ret_sum"] += trades * avg_return
                weak_holding_combo_map[key]["flow_sum"] += trades * avg_flow
                weak_holding_combo_map[key]["final_sum"] += trades * avg_final
                weak_holding_combo_map[key]["holding_sum"] += trades * avg_holding

            combo_order = [
                "both_weak",
                "flow_only_weak",
                "final_only_weak",
                "neither_clear",
            ]

            has_weak_combo = False
            for combo_type in combo_order:
                val = weak_combo_map.get(combo_type)
                if not val or val["trades"] == 0:
                    continue

                has_weak_combo = True
                trades = val["trades"]
                avg_ret = val["ret_sum"] / trades
                avg_flow = val["flow_sum"] / trades
                avg_final = val["final_sum"] / trades
                avg_holding = val["holding_sum"] / trades

                f.write(
                    f"- {label_mbweak_combo(combo_type)}: "
                    f"거래 수 {trades}건, "
                    f"평균 수익률 {pct_str(avg_ret, signed=True)}, "
                    f"평균 수급 점수 {avg_flow:.3f}, "
                    f"평균 종합 점수 {avg_final:.3f}, "
                    f"평균 보유일 {avg_holding:.2f}일\n"
                )

            if not has_weak_combo:
                _write_empty(f)

            # --------------------------------------------------
            # Detailed combo summary by holding-period bucket
            # --------------------------------------------------
            f.write("\n")
            _write_section_title(f, "기타 약세형 보유구간별 세부 조합 요약")

            has_weak_holding_combo = False
            for holding_bucket in MBW_CFG["holding_bucket_labels"]:
                for combo_type in combo_order:
                    key = (holding_bucket, combo_type)
                    val = weak_holding_combo_map.get(key)
                    if not val or val["trades"] == 0:
                        continue

                    has_weak_holding_combo = True
                    trades = val["trades"]
                    avg_ret = val["ret_sum"] / trades
                    avg_flow = val["flow_sum"] / trades
                    avg_final = val["final_sum"] / trades
                    avg_holding = val["holding_sum"] / trades

                    f.write(
                        f"- {holding_bucket} / {label_mbweak_combo(combo_type)}: "
                        f"{trades}건, "
                        f"평균 수익률 {pct_str(avg_ret, signed=True)}, "
                        f"평균 수급 점수 {avg_flow:.3f}, "
                        f"평균 종합 점수 {avg_final:.3f}, "
                        f"평균 보유일 {avg_holding:.2f}일\n"
                    )

            if not has_weak_holding_combo:
                _write_empty(f)

            # --------------------------------------------------
            # BLOCK flat summary
            # --------------------------------------------------
            f.write("\n")
            _write_section_title(f, "BLOCK 평탄형 요약")

            early_flat = reason_stats.get("market_block_early_flat")
            late_flat = reason_stats.get("market_block_late_flat")

            if not early_flat and not late_flat:
                _write_empty(f)
            else:
                if early_flat:
                    f.write(
                        f"- 초기 평탄형: "
                        f"{early_flat['trades']}건, "
                        f"평균 수익률 {pct_str(early_flat['avg_return'], signed=True)}, "
                        f"승률 {early_flat['win_rate'] * 100:.1f}%\n"
                    )
                if late_flat:
                    f.write(
                        f"- 후기 평탄형: "
                        f"{late_flat['trades']}건, "
                        f"평균 수익률 {pct_str(late_flat['avg_return'], signed=True)}, "
                        f"승률 {late_flat['win_rate'] * 100:.1f}%\n"
                    )

            # --------------------------------------------------
            # BLOCK selective-hold candidate examples
            # --------------------------------------------------
            f.write("\n")
            _write_section_title(f, "BLOCK 선별 보유 후보 사례")

            salvage_examples = [
                row for row in mbweak_candidate_rows
                if to_float(row[5], 0.0) >= 0.0
                and to_float(row[6], 0.0) >= MBW_CFG["strong_candidate_min_flow"]
                and to_float(row[7], 0.0) >= MBW_CFG["strong_candidate_min_final"]
            ][:MBW_CFG["example_limit"]]

            if not salvage_examples:
                _write_empty(f)
            else:
                for row in salvage_examples:
                    (
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
                        profit_bucket,
                    ) = row

                    candidate_label = _candidate_label(candidate_type)

                    f.write(
                        f"- {company_name} ({ticker_code}): "
                        f"유형 {candidate_label}, "
                        f"보유일 {holding_period}일, "
                        f"누적 수익률 {pct_str(to_float(cum_return, 0.0), signed=True)}, "
                        f"수급 점수 {to_float(flow_value, 0.0):.3f}, "
                        f"종합 점수 {to_float(final_value, 0.0):.3f}, "
                        f"수익 구간 {profit_bucket}\n"
                    )

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
    finally:
        cur.close()
        conn.close()

    generate_summary_report(run_id)
    print("✅ 01_요약리포트.txt 생성 완료")
