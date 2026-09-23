"""Module that generates an improvement-recommendation text report from backtest analysis results.

It reads the extended analysis tables and config thresholds to build diagnostic statements
from risk, entry, exit, and sector perspectives.
Running it performs DB queries and local file writes.
"""

from datetime import datetime
from collections import defaultdict

from port_strategy_common.config import REPORT_CONFIG

REC_CFG = REPORT_CONFIG["recommendation"]
MBW_CFG = REPORT_CONFIG["mbweak"]
SIG_H1, SIG_H2, SIG_H3, SIG_H4 = REPORT_CONFIG["holding_buckets"]["signal_holding"]
MBW_HOLDING_LABELS = MBW_CFG["holding_bucket_labels"]
MBW_PROFIT_LABELS = MBW_CFG["profit_bucket_labels"]

from port_strategy_research.report_data_loader import (
    get_conn,
    get_latest_run_id,
    get_run_summary,
    get_run_inputs,
    get_thresholds,
    load_reason_stats,
    load_holding_stats,
    load_mbweak_stats,
    load_entry_stats,
    load_signal_holding_stats,
    load_ticker_stats,
    to_float,
    load_exit_trigger_stats,
    load_entry_day_stats,
    load_sector_stats,
    load_mbweak_bucket_rows,
    load_mbweak_candidate_rows,
    load_mbweak_other_rows,
)
from port_strategy_research.report_formatter import (
    pct_str,
    format_run_inputs,
    label_entry_metric,
    label_exit_reason,
    label_mbweak_combo,
    label_market_signal,
)


def _safe_div(a: float, b: float) -> float:
    if not b:
        return 0.0
    return float(a) / float(b)


def _candidate_label(candidate_type: str) -> str:
    return {
        "quality_drop": "질 저하형",
        "weak_other": "기타 약세형",
    }.get(candidate_type, candidate_type)


def _entry_bucket_label(metric_name: str, bucket_label: str) -> str:
    """
    The bucket_label from the analysis table is often already in a human-readable form,
    so by default the original value is kept.
    Only true/false-style values are tidied up for presentation.
    """
    raw = str(bucket_label)

    if metric_name == "buy_has_info_flag":
        lowered = raw.lower()
        if lowered in ("true", "1", "yes"):
            return "정보 신호 있음"
        if lowered in ("false", "0", "no"):
            return "정보 신호 없음"

    if metric_name == "buy_entry_signal":
        return label_market_signal(raw)

    return raw


def _top_bad_tickers(ticker_rows, limit: int = 5) -> list[dict]:
    results = []
    for row in ticker_rows[:limit]:
        (
            ticker_code,
            company_name,
            trades,
            avg_return,
            win_rate,
            total_pnl_contribution,
            avg_holding,
            major_exit_reason,
            avg_buy_flow,
            avg_buy_score,
        ) = row

        results.append(
            {
                "ticker_code": str(ticker_code),
                "company_name": str(company_name),
                "trades": int(trades or 0),
                "avg_return": to_float(avg_return, 0.0),
                "win_rate": to_float(win_rate, 0.0),
                "total_pnl_contribution": to_float(total_pnl_contribution, 0.0),
                "avg_holding": to_float(avg_holding, 0.0),
                "major_exit_reason": str(major_exit_reason or ""),
                "avg_buy_flow": to_float(avg_buy_flow, 0.0),
                "avg_buy_score": to_float(avg_buy_score, 0.0),
            }
        )
    return results


def _group_entry_stats(entry_rows) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for metric_name, bucket_label, trades, avg_return, win_rate, avg_holding in entry_rows:
        grouped[str(metric_name)].append(
            {
                "bucket_label": str(bucket_label),
                "trades": int(trades or 0),
                "avg_return": to_float(avg_return, 0.0),
                "win_rate": to_float(win_rate, 0.0),
                "avg_holding": to_float(avg_holding, 0.0),
            }
        )

    for metric_name in grouped:
        grouped[metric_name].sort(key=lambda x: x["bucket_label"])
    return grouped


def _group_signal_holding_rows(signal_rows) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for entry_market_signal, holding_bucket, exit_reason, trades, avg_return, win_rate, avg_holding in signal_rows:
        grouped[str(entry_market_signal)].append(
            {
                "holding_bucket": str(holding_bucket),
                "exit_reason": str(exit_reason),
                "trades": int(trades or 0),
                "avg_return": to_float(avg_return, 0.0),
                "win_rate": to_float(win_rate, 0.0),
                "avg_holding": to_float(avg_holding, 0.0),
            }
        )
    return grouped


def build_recommendations(
    run_summary: dict,
    run_inputs: dict,
    thresholds: dict,
    reason_stats: dict[str, dict],
    holding_stats: dict[int, dict],
    mbweak_stats: dict[int, dict],
    entry_grouped: dict[str, list[dict]],
    signal_grouped: dict[str, list[dict]],
    ticker_rows,
    exit_trigger_rows,
    entry_day_rows,
    sector_rows,
    mbweak_bucket_rows,
    mbweak_candidate_rows,
    mbweak_other_rows,
):
    """Combine analysis rows and the threshold snapshot to build the list of recommendation statements."""
    total_trades = int(run_summary.get("trade_count", 0) or 0)
    sharpe = to_float(run_summary.get("sharpe"), 0.0)
    mdd = to_float(run_summary.get("mdd"), 0.0)

    positives: list[str] = []
    cautions: list[str] = []
    actions: list[str] = []

    # --------------------------------------------------
    # 1. Top-level performance summary
    # --------------------------------------------------
    if sharpe >= REC_CFG["sharpe_excellent"]:
        positives.append(
            f"샤프 지수가 {sharpe:.2f}로 2.0 이상이라 전체 전략 품질은 이미 좋은 구간임"
        )
    elif sharpe >= REC_CFG["sharpe_good"]:
        positives.append(
            f"샤프 지수가 {sharpe:.2f}로 기본 품질은 양호하지만, 청산·사이징 미세조정 여지가 남아 있음"
        )
    else:
        cautions.append(
            f"샤프 지수가 {sharpe:.2f}라 구조적 개선이 더 우선임"
        )

    if mdd <= REC_CFG["mdd_warning"]:
        cautions.append(
            f"최대 낙폭이 {pct_str(mdd, signed=True)}로 큰 편이라 손실 구간 방어가 필요함"
        )
    else:
        positives.append(
            f"최대 낙폭이 {pct_str(mdd, signed=True)} 수준으로 과도하게 무너지진 않음"
        )

    # --------------------------------------------------
    # 2. exit reason-centered diagnosis
    # --------------------------------------------------
    mb_early_flat = reason_stats.get("market_block_early_flat")
    mb_late_flat = reason_stats.get("market_block_late_flat")
    mb_quality_drop = reason_stats.get("market_block_quality_drop")
    mb_weak_other = reason_stats.get("market_block_weak_other")

    max_holding = reason_stats.get("max_holding")
    profit_protect = reason_stats.get("profit_protect")
    early_cut = reason_stats.get("early_cut")
    early_risk_cut = reason_stats.get("early_risk_cut")
    buy_day_intraday_stop = reason_stats.get("buy_day_intraday_stop")
    intraday_stop = reason_stats.get("intraday_stop")

    def _stat_trades(stat):
        return int(stat["trades"]) if stat else 0

    def _stat_avg(stat):
        return to_float(stat["avg_return"], 0.0) if stat else 0.0

    bad_trades = _stat_trades(mb_quality_drop) + _stat_trades(mb_weak_other)
    flat_trades = _stat_trades(mb_early_flat) + _stat_trades(mb_late_flat)

    bad_ret_sum = (
        _stat_trades(mb_quality_drop) * _stat_avg(mb_quality_drop)
        + _stat_trades(mb_weak_other) * _stat_avg(mb_weak_other)
    )
    flat_ret_sum = (
        _stat_trades(mb_early_flat) * _stat_avg(mb_early_flat)
        + _stat_trades(mb_late_flat) * _stat_avg(mb_late_flat)
    )

    bad_avg = bad_ret_sum / bad_trades if bad_trades else 0.0
    flat_avg = flat_ret_sum / flat_trades if flat_trades else 0.0
    bad_ratio = _safe_div(bad_trades, total_trades) * 100.0 if total_trades else 0.0

    if bad_trades > 0:
        cautions.append(
            f"BLOCK 손실군 비중이 {bad_trades}건({bad_ratio:.1f}%)이며 평균 수익률이 {pct_str(bad_avg, signed=True)}라 BLOCK 시점 손실군이 성과를 깎고 있음"
        )
        actions.append(
            "BLOCK 튜닝은 전면 완화보다 질 저하형·기타 약세형 축소 중심으로 보는 것이 타당함"
        )
        actions.append(
            "1순위로 BLOCK 손실군 조건 재점검 필요: "
            f"최소 유지 기대수익 {thresholds['market_block_min_keep_profit']:.3f}, "
            f"최소 보유일 {thresholds['market_block_sell_min_holding_days']}일, "
            f"최대 승자 보유일 {thresholds['market_block_max_win_holding_days']}일, "
            f"강한 종목 최소 수급 기준 {thresholds.get('market_block_strong_min_flow')}, "
            f"강한 종목 최소 종합 점수 기준 {thresholds.get('market_block_strong_min_final')}"
        )

    if flat_trades > 0 and flat_avg > 0:
        positives.append(
            f"BLOCK 평탄형 그룹은 {flat_trades}건이며 평균 수익률이 {pct_str(flat_avg, signed=True)}라 BLOCK에서도 일부는 무리 없이 더 보유 가능했을 여지가 있음"
        )
        actions.append(
            "BLOCK 초기 평탄형 / 후기 평탄형 조건은 별도 선별 보유 실험 대상으로 분리할 가치가 있음"
        )

    if mb_quality_drop and _stat_avg(mb_quality_drop) < 0:
        cautions.append(
            f"BLOCK 질 저하형 청산군 평균 수익률이 {pct_str(mb_quality_drop['avg_return'], signed=True)}라 BLOCK 직전 종목 질 저하를 더 빨리 감지할 필요가 있음"
        )

    if mb_weak_other and _stat_avg(mb_weak_other) < 0:
        cautions.append(
            f"BLOCK 기타 약세형 청산군 평균 수익률이 {pct_str(mb_weak_other['avg_return'], signed=True)}라 기타 약세형 BLOCK 청산군도 따로 관리가 필요함"
        )

    if max_holding and to_float(max_holding["avg_return"], 0.0) > 0:
        positives.append(
            f"최대 보유기간 도달 청산의 평균 수익률이 {pct_str(max_holding['avg_return'], signed=True)}라 오래 버틴 승자는 잘 먹는 구조임"
        )

    if profit_protect and to_float(profit_protect["avg_return"], 0.0) > 0:
        positives.append(
            f"이익 보전 청산의 평균 수익률이 {pct_str(profit_protect['avg_return'], signed=True)}라 이익 보전 로직은 잘 작동하는 편임"
        )

    if early_cut and to_float(early_cut["avg_return"], 0.0) < 0:
        cautions.append(
            f"초기 기대 미달 정리의 평균 수익률이 {pct_str(early_cut['avg_return'], signed=True)}라 "
            "진입 직후 기대에 못 미치는 종목이 존재함. "
            "다만 이 구간은 매수 당시 수급·점수가 양호한 경우도 있어 사전 차단보다 사후 리스크 관리 관점에서 보는 편이 적절함"
        )

    if early_risk_cut and to_float(early_risk_cut["avg_return"], 0.0) < 0:
        cautions.append(
            f"초기 급락 방어 청산의 평균 수익률이 {pct_str(early_risk_cut['avg_return'], signed=True)}라 "
            "초반 급락 방어 장치가 필요한 구간이 확인됨. "
            "이 구간은 추가 진입 필터보다 현재 early risk cut이 손실 확대를 막는지 확인하는 방향이 적절함"
        )

    if buy_day_intraday_stop and int(buy_day_intraday_stop["trades"]) > 0:
        cautions.append(
            f"진입 당일 급락 방어 청산이 {buy_day_intraday_stop['trades']}건 존재함. "
            "다만 표본이 크지 않으므로 단독 필터 추가보다는 진입 당일 급락을 빠르게 인정하는 방어 장치로 해석하는 편이 적절함"
        )
        actions.append(
            f"진입 당일 급락 방어 기준({thresholds['buy_day_intraday_stop_loss']:.2%})은 "
            "즉시 강화하기보다, 매수일 장중 변동폭·수급 점수·종합 점수와 함께 비교해 과적합 여부를 확인할 것"
        )

    if intraday_stop and int(intraday_stop["trades"]) > 0:
        positives.append(
            f"장중 손절은 {intraday_stop['trades']}건 존재하며, 평균 수익률 {pct_str(intraday_stop['avg_return'], signed=True)}로 단순 손절만은 아님"
        )

    # --------------------------------------------------
    # 3. holding-period diagnosis
    # --------------------------------------------------
    bad_early_holding = []
    good_late_holding = []

    for holding_days, stat in sorted(holding_stats.items()):
        avg_ret = to_float(stat["avg_return"], 0.0)
        trades = int(stat["trades"])

        if holding_days <= SIG_H1 and trades > 0 and avg_ret < 0:
            bad_early_holding.append((holding_days, trades, avg_ret))

        if holding_days >= SIG_H3 and trades > 0 and avg_ret > 0:
            good_late_holding.append((holding_days, trades, avg_ret))

    if bad_early_holding:
        joined = ", ".join(
            f"{d}일({t}건, {pct_str(r, signed=True)})"
            for d, t, r in bad_early_holding
        )
        cautions.append(
            f"초반 0~2일 구간 수익성이 약함: {joined}. "
            "다만 초기 손실군은 매수 당시에는 양호해 보이는 케이스가 섞일 수 있어, 무리한 사전 필터링은 과적합 위험이 있음"
        )
        actions.append(
            "초기 0~2일 손실 구간은 추가 진입 차단보다, "
            "현재 early cut / hard stop이 손실 확대를 적절히 제한하는지 확인하는 방향으로 점검할 것"
        )

    if good_late_holding:
        positives.append(
            "10일 이상 버틴 구간에서 양의 평균수익이 확인되어, 승자 장기 보유 구조는 살아 있음"
        )

    # --------------------------------------------------
    # 4. market_block bad details
    # --------------------------------------------------
    bad_mb_buckets = []
    for holding_days, stat in sorted(mbweak_stats.items()):
        avg_ret = to_float(stat["avg_return"], 0.0)
        trades = int(stat["trades"])
        if trades >= REC_CFG["min_sample_for_warning"] and avg_ret < 0:
            bad_mb_buckets.append(
                (
                    holding_days,
                    trades,
                    avg_ret,
                    to_float(stat["avg_flow"], 0.0),
                    to_float(stat["avg_final"], 0.0),
                )
            )

    if bad_mb_buckets:
        worst = min(bad_mb_buckets, key=lambda x: x[2])
        cautions.append(
            "BLOCK 손실군이 보유 기간별로도 음수인 구간이 존재함"
        )
        actions.append(
                "BLOCK 손실군 상세 구간 중 특히 "
                f"{worst[0]}일(거래 수 {worst[1]}건, 평균 수익률 {pct_str(worst[2], signed=True)}, "
                f"평균 수급 점수 {worst[3]:.3f}, 평균 종합 점수 {worst[4]:.3f}) "
                "구간부터 우선 점검할 것"
        )    

    # --------------------------------------------------
    # 4-A. market_block bad bucket / salvage candidate diagnosis
    # --------------------------------------------------
    quality_cnt = 0
    quality_ret_sum = 0.0
    weak_cnt = 0
    weak_ret_sum = 0.0

    holding_reason_map: dict[tuple[str, str], dict] = {}
    profit_bucket_map: dict[str, int] = {}

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

        profit_bucket_map[profit_bucket] = profit_bucket_map.get(profit_bucket, 0) + trades

    salvage_examples = [
        row for row in mbweak_candidate_rows
        if to_float(row[5], 0.0) >= 0.0
        and to_float(row[6], 0.0) >= MBW_CFG["strong_candidate_min_flow"]
        and to_float(row[7], 0.0) >= MBW_CFG["strong_candidate_min_final"]
    ]
    salvage_cnt = len(salvage_examples)

    if salvage_cnt > 0:
        positives.append(
            f"BLOCK 손실군 사례 중 선별 보유 후보가 {salvage_cnt}건 존재해, BLOCK 전면 청산보다 선택적 유지 실험 가치가 있음"
        )

    b45_quality = holding_reason_map.get((MBW_HOLDING_LABELS[1], "quality_drop"))
    b45_weak = holding_reason_map.get((MBW_HOLDING_LABELS[1], "weak_other"))
    b68_quality = holding_reason_map.get((MBW_HOLDING_LABELS[2], "quality_drop"))
    b68_weak = holding_reason_map.get((MBW_HOLDING_LABELS[2], "weak_other"))

    if b45_quality and b45_quality["trades"] >= 5:
        avg_ret = b45_quality["ret_sum"] / b45_quality["trades"]
        if avg_ret < 0:
            cautions.append(
                f"4~5일 구간 질 저하형 평균 수익률이 {pct_str(avg_ret, signed=True)}라 이 구간은 유지보다 정리 쪽이 더 맞을 가능성이 큼"
            )

    if b45_weak and b45_weak["trades"] >= 5:
        avg_ret = b45_weak["ret_sum"] / b45_weak["trades"]
        if avg_ret < 0:
            cautions.append(
                f"4~5일 구간 기타 약세형 평균 수익률이 {pct_str(avg_ret, signed=True)}라 중간 보유 구간 BLOCK 손실군도 별도 관리가 필요함"
            )

    if b68_quality and b68_quality["trades"] >= 5:
        avg_ret = b68_quality["ret_sum"] / b68_quality["trades"]
        if avg_ret < 0:
            cautions.append(
                f"6~8일 구간 질 저하형 평균 수익률이 {pct_str(avg_ret, signed=True)}라 장기 완화는 오히려 역효과 가능성이 있음"
            )

    if b68_weak and b68_weak["trades"] >= 5:
        avg_ret = b68_weak["ret_sum"] / b68_weak["trades"]
        if avg_ret < 0:
            cautions.append(
                f"6~8일 구간 기타 약세형 평균 수익률이 {pct_str(avg_ret, signed=True)}라 장기 구간까지 BLOCK 완화를 넓히는 것은 주의가 필요함"
            )

    profit_0_23 = profit_bucket_map.get(MBW_PROFIT_LABELS[3], 0)
    total_bad_bucket = quality_cnt + weak_cnt
    if total_bad_bucket > 0 and profit_0_23 > 0:
        ratio_0_23 = profit_0_23 * 100.0 / total_bad_bucket
        cautions.append(
            f"BLOCK 손실군 중 0%~2.3% 구간이 {profit_0_23}건({ratio_0_23:.1f}%)으로 많아, 본전/소폭수익 종목까지 너무 일찍 자를 가능성이 있음"
        )

    # --------------------------------------------------
    # 4-B. market_block_weak_other combo detailed diagnosis
    # --------------------------------------------------
    weak_combo_map: dict[str, dict] = {}
    weak_holding_combo_map: dict[tuple[str, str], dict] = {}

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

    combo_avg_map = {}
    total_weak_other_combo = 0

    for combo_type in combo_order:
        val = weak_combo_map.get(combo_type)
        if not val or val["trades"] == 0:
            continue

        trades = val["trades"]
        avg_ret = val["ret_sum"] / trades
        avg_flow = val["flow_sum"] / trades
        avg_final = val["final_sum"] / trades
        avg_holding = val["holding_sum"] / trades

        combo_avg_map[combo_type] = {
            "trades": trades,
            "avg_return": avg_ret,
            "avg_flow": avg_flow,
            "avg_final": avg_final,
            "avg_holding": avg_holding,
        }
        total_weak_other_combo += trades

    if combo_avg_map:
        worst_combo_name = min(
            combo_avg_map.keys(),
            key=lambda x: combo_avg_map[x]["avg_return"]
        )
        worst_combo = combo_avg_map[worst_combo_name]

        largest_combo_name = max(
            combo_avg_map.keys(),
            key=lambda x: combo_avg_map[x]["trades"]
        )
        largest_combo = combo_avg_map[largest_combo_name]

        worst_ratio = 0.0
        largest_ratio = 0.0

        if total_weak_other_combo > 0:
            worst_ratio = worst_combo["trades"] * 100.0 / total_weak_other_combo
            largest_ratio = largest_combo["trades"] * 100.0 / total_weak_other_combo

        cautions.append(
            f"BLOCK 기타 약세형 내부에서는 {label_mbweak_combo(worst_combo_name)} 구간의 평균 수익률이 가장 낮음 "
            f"(거래 수 {worst_combo['trades']}건, 비중 {worst_ratio:.1f}%, "
            f"평균 수익률 {pct_str(worst_combo['avg_return'], signed=True)})"
        )

        if worst_combo["trades"] < REC_CFG["min_sample_for_warning"]:
            cautions.append(
                f"다만 {label_mbweak_combo(worst_combo_name)} 구간은 표본이 {worst_combo['trades']}건으로 작아 "
                "핵심 병목으로 단정하기보다는 관찰 대상으로 보는 편이 적절함"
            )
        else:
            cautions.append(
                f"{label_mbweak_combo(worst_combo_name)} 구간은 표본이 {worst_combo['trades']}건 이상이라 "
                "세부 조건 점검 대상에 포함할 수 있음"
            )

        if largest_combo_name != worst_combo_name:
            cautions.append(
                f"기타 약세형 내부의 주된 덩어리는 {label_mbweak_combo(largest_combo_name)} 구간임 "
                f"(거래 수 {largest_combo['trades']}건, 비중 {largest_ratio:.1f}%, "
                f"평균 수익률 {pct_str(largest_combo['avg_return'], signed=True)})"
            )

        if largest_combo_name == "neither_clear":
            actions.append(
                "기타 약세형 개선은 점수 약세형 같은 단일 약세 신호보다 혼합·불명확형 세부 조건을 먼저 분해하는 방향이 적절함"
            )
            actions.append(
                "혼합·불명확형은 현재 정의가 넓을 수 있으므로, 수급/종합점수/보유일/수익률 구간을 나눠 추가 진단하는 편이 효율적임"
            )
        elif largest_combo_name == "both_weak":
            actions.append(
                "기타 약세형의 주된 덩어리가 수급·점수 동시 약세형이라면, BLOCK 완화보다 수급·종합 점수 동시 약세 구간을 더 빠르게 정리하는 방향이 타당함"
            )
        elif largest_combo_name == "flow_only_weak":
            actions.append(
                "기타 약세형의 주된 덩어리가 수급 약세형이라면, 내부 판단에서 종합 점수보다 수급 붕괴를 더 중시하는 방향으로 재정의할 가치가 있음"
            )
        elif largest_combo_name == "final_only_weak":
            actions.append(
                "기타 약세형의 주된 덩어리가 점수 약세형이라면, 내부 판단에서 수급보다 종합 점수 저하를 더 빨리 반영하는 방향을 점검할 수 있음"
            )

        if worst_combo_name != largest_combo_name:
            actions.append(
                f"평균 수익률 최저 구간({label_mbweak_combo(worst_combo_name)})과 "
                f"최대 비중 구간({label_mbweak_combo(largest_combo_name)})이 다르므로, "
                "최저 수익률만 보고 핵심 병목으로 단정하지 말고 표본 수와 비중을 함께 판단할 것"
            )

    worst_holding_combo = None
    worst_holding_combo_key = None

    for key, val in weak_holding_combo_map.items():
        if val["trades"] < 3:
            continue

        avg_ret = val["ret_sum"] / val["trades"]
        if worst_holding_combo is None or avg_ret < worst_holding_combo["avg_return"]:
            worst_holding_combo = {
                "trades": val["trades"],
                "avg_return": avg_ret,
                "avg_flow": val["flow_sum"] / val["trades"],
                "avg_final": val["final_sum"] / val["trades"],
                "avg_holding": val["holding_sum"] / val["trades"],
            }
            worst_holding_combo_key = key

    if worst_holding_combo_key and worst_holding_combo:
        holding_bucket, combo_type = worst_holding_combo_key
        cautions.append(
            f"기타 약세형 세부 구간 중 {holding_bucket} / {label_mbweak_combo(combo_type)} 구간이 가장 약함 "
            f"({pct_str(worst_holding_combo['avg_return'], signed=True)}). "
            "다만 이 구간은 단독 매도 강화 대상이라기보다 기타 약세형 내부를 더 잘게 분해하기 위한 관찰 대상으로 보는 편이 적절함"
        )
        actions.append(
            f"BLOCK 전면 완화나 즉시 로직 변경보다 우선 {holding_bucket} / {label_mbweak_combo(combo_type)} 구간을 "
            "수급·종합점수·보유일·수익률 조건으로 추가 분해해 원인을 확인할 것"
        )

    # --------------------------------------------------
    # 4-1. exit trigger overlap diagnosis
    # --------------------------------------------------
    exit_trigger_map: dict[str, list[dict]] = defaultdict(list)

    for exit_reason, trigger_name, trades, avg_return, win_rate, avg_holding in exit_trigger_rows:
        exit_trigger_map[str(exit_reason)].append(
            {
                "trigger_name": str(trigger_name),
                "trades": int(trades or 0),
                "avg_return": to_float(avg_return, 0.0),
                "win_rate": to_float(win_rate, 0.0),
                "avg_holding": to_float(avg_holding, 0.0),
            }
        )

    mb_bad_trigger_rows = (
        exit_trigger_map.get("market_block_quality_drop", [])
        + exit_trigger_map.get("market_block_weak_other", [])
    )

    if mb_bad_trigger_rows:
        flow_overlap = next(
            (x for x in mb_bad_trigger_rows if x["trigger_name"] == "flow_breakdown_condition"),
            None,
        )
        score_overlap = next(
            (x for x in mb_bad_trigger_rows if x["trigger_name"] == "score_breakdown_condition"),
            None,
        )
        mid_holding_overlap = next(
            (x for x in mb_bad_trigger_rows if x["trigger_name"] == "mid_holding_condition"),
            None,
        )

        if flow_overlap and flow_overlap["trades"] >= REC_CFG["min_sample_for_overlap"]:
            cautions.append(
                f"BLOCK 손실군 중 수급 붕괴 동반 건수가 {flow_overlap['trades']}건 존재 → 단순 시장 이슈보다 종목 약화가 함께 작동했을 가능성 있음"
            )

        if score_overlap and score_overlap["trades"] >= 10:
            cautions.append(
                f"BLOCK 손실군 중 종합 점수 붕괴 동반 건수가 {score_overlap['trades']}건 존재 → BLOCK 청산 전에 종목 질적 저하가 선행됐을 가능성 있음"
            )

        if mid_holding_overlap and mid_holding_overlap["trades"] >= 10:
            cautions.append(
                f"BLOCK 손실군이 3~5일 보유 구간에서 {mid_holding_overlap['trades']}건 발생 → 중간 보유 구간 방어 청산이 과도할 수 있음"
            )
            actions.append(
                "BLOCK 최소 보유일 상향 또는 최소 유지 기대수익 완화 실험 가치가 있음"
            )

    # --------------------------------------------------
    # 5. entry analysis diagnosis
    # --------------------------------------------------
    def add_metric_comparison(metric_name: str):
        human_name = label_entry_metric(metric_name)
        rows = entry_grouped.get(metric_name, [])
        if len(rows) < 2:
            return

        best = max(rows, key=lambda x: x["avg_return"])
        worst = min(rows, key=lambda x: x["avg_return"])
        spread = best["avg_return"] - worst["avg_return"]

        best_label = _entry_bucket_label(metric_name, best["bucket_label"])
        worst_label = _entry_bucket_label(metric_name, worst["bucket_label"])

        if abs(spread) >= REC_CFG["spread_meaningful"]:
            positives.append(
                f"{human_name} 구간 간 성과 차이가 존재함 "
                f"(가장 좋았던 구간은 {best_label} {pct_str(best['avg_return'], signed=True)}, "
                f"가장 약했던 구간은 {worst_label} {pct_str(worst['avg_return'], signed=True)})"
            )

            if metric_name == "buy_flow":
                actions.append(
                    f"매수 수급 점수는 실질 구분력이 있으니, "
                    f"{best_label} 구간 유지/강화 및 {worst_label} 구간 약화 실험 가치가 있음"
                )
            elif metric_name == "buy_score":
                actions.append(
                    f"매수 종합 점수는 실질 구분력이 있으니, "
                    f"{best_label} 구간 강화 및 {worst_label} 구간 보수화 실험 가치가 있음"
                )
            elif metric_name == "buy_info":
                actions.append(
                    f"매수 정보 점수는 단독보다는 보조 신호 성격이지만, "
                    f"{best_label} 구간 우대 여부를 점검할 가치가 있음"
                )
            else:
                actions.append(
                    f"{human_name} 기준은 실질 구분력이 있으니, "
                    f"{best_label} 쪽을 강화하고 {worst_label} 쪽을 약화하는 실험 가치가 있음"
                )

        else:
            if metric_name == "buy_flow":
                cautions.append(
                    "매수 수급 점수 구간 간 전반적 성과 차이는 제한적이지만, 일부 구간은 상대적으로 양호해 관찰 유지가 필요함"
                )
            elif metric_name == "buy_info":
                cautions.append(
                    "매수 정보 점수 구간 간 성과 차이는 제한적이라 단독 신호로 해석하기엔 약할 수 있음"
                )
            elif metric_name == "buy_short":
                cautions.append(
                    "매수 시 공매도 압력 구간 간 성과 차이는 크지 않아 현재 공매도 압력 기준은 진입 구분력 측면에서 제한적일 수 있음"
                )
            elif metric_name == "buy_vol":
                cautions.append(
                    "매수 시 20일 변동성 구간 간 성과 차이는 크지 않아 현재 변동성 기준은 추가 미세조정 여지가 크지 않을 수 있음"
                )
            elif metric_name == "buy_intraday_range":
                cautions.append(
                    "매수일 장중 변동폭 구간 간 성과 차이는 크지 않아 단독 필터보다는 다른 진입 신호와 함께 보는 편이 적절함"
                )
            elif metric_name == "buy_entry_signal":
                cautions.append(
                    "진입 시장 상태 구간 간 성과 차이는 크지 않아 진입 시 시장 상태만으로 종목 성과를 크게 가르긴 어려워 보임"
                )
            elif metric_name == "buy_score_flow_combo":
                cautions.append(
                    "매수 점수·수급 조합 구간 간 성과 차이는 크지 않아, 현재 조합 기준은 기대만큼의 추가 구분력을 주지 않을 수 있음"
                )
            else:
                cautions.append(
                    f"{human_name} 구간 간 성과 차이가 크지 않음 → 현재 기준으로는 구분력이 제한적일 수 있음"
                )

    add_metric_comparison("buy_flow")
    add_metric_comparison("buy_score")
    add_metric_comparison("buy_info")
    add_metric_comparison("buy_short")
    add_metric_comparison("buy_vol")
    add_metric_comparison("buy_intraday_range")
    add_metric_comparison("buy_entry_signal")
    add_metric_comparison("buy_score_flow_combo")

    info_flag_rows = entry_grouped.get("buy_has_info_flag", [])
    if len(info_flag_rows) >= 2:
        best = max(info_flag_rows, key=lambda x: x["avg_return"])
        worst = min(info_flag_rows, key=lambda x: x["avg_return"])

        best_label = _entry_bucket_label("buy_has_info_flag", best["bucket_label"])
        worst_label = _entry_bucket_label("buy_has_info_flag", worst["bucket_label"])

        if abs(best["avg_return"] - worst["avg_return"]) >= REC_CFG["info_flag_gap_meaningful"]:
            positives.append(
                f"정보 신호 존재 여부 차이가 의미 있음 "
                f"(가장 좋았던 구간은 {best_label} {pct_str(best['avg_return'], signed=True)}, "
                f"가장 약했던 구간은 {worst_label} {pct_str(worst['avg_return'], signed=True)})"
            )
        else:
            cautions.append(
                "정보 신호 존재 여부 차이는 크지 않아, 정보 신호 자체보다는 다른 지표와의 조합으로 보는 편이 적절함"
            )

    # --------------------------------------------------
    # 5-1. entry day follow-through diagnosis
    # --------------------------------------------------
    entry_day_map: dict[str, list[dict]] = defaultdict(list)

    for (
        metric_name,
        bucket_label,
        trades,
        avg_day1_return,
        day1_win_rate,
        avg_exit_open_return,
        exit_open_win_rate,
        avg_final_return,
        final_win_rate,
    ) in entry_day_rows:
        entry_day_map[str(metric_name)].append(
            {
                "bucket_label": str(bucket_label),
                "trades": int(trades or 0),
                "avg_day1_return": to_float(avg_day1_return, 0.0),
                "day1_win_rate": to_float(day1_win_rate, 0.0),
                "avg_exit_open_return": to_float(avg_exit_open_return, 0.0),
                "exit_open_win_rate": to_float(exit_open_win_rate, 0.0),
                "avg_final_return": to_float(avg_final_return, 0.0),
                "final_win_rate": to_float(final_win_rate, 0.0),
            }
        )

    flow_day_rows = entry_day_map.get("buy_flow", [])
    if len(flow_day_rows) >= 2:
        best_flow = max(flow_day_rows, key=lambda x: x["avg_final_return"])
        worst_flow = min(flow_day_rows, key=lambda x: x["avg_final_return"])

        worst_flow_label = _entry_bucket_label("buy_flow", worst_flow["bucket_label"])
        best_flow_label = _entry_bucket_label("buy_flow", best_flow["bucket_label"])

        if worst_flow["trades"] >= 5 and worst_flow["avg_day1_return"] < 0 and worst_flow["avg_final_return"] < 0:
            cautions.append(
                f"매수 수급 점수 {worst_flow_label} 구간은 진입 당일부터 약하고 최종 성과도 부진 → 진입 품질 자체가 약할 가능성 있음"
            )

        if best_flow["trades"] >= 5 and best_flow["avg_day1_return"] > 0 and best_flow["avg_final_return"] > 0:
            positives.append(
                f"매수 수급 점수 {best_flow_label} 구간은 초반/최종 성과가 모두 양호해 유지 관찰 후보로 볼 수 있음"
            )

    score_day_rows = entry_day_map.get("buy_score", [])
    if len(score_day_rows) >= 2:
        weak_score_rows = [
            x for x in score_day_rows
            if x["trades"] >= 5 and x["avg_day1_return"] < 0 and x["avg_final_return"] < 0
        ]
        if weak_score_rows:
            worst_score = min(weak_score_rows, key=lambda x: x["avg_final_return"])
            worst_score_label = _entry_bucket_label("buy_score", worst_score["bucket_label"])
            cautions.append(
                f"매수 종합 점수 {worst_score_label} 구간은 초반 반응부터 약함 → 낮은 종합 점수 구간 진입 강화는 비효율적일 수 있음"
            )

    # --------------------------------------------------
    # 6. signal + holding + exit_reason diagnosis
    # --------------------------------------------------
    for signal, rows in signal_grouped.items():
        heavy_negative = [
            r for r in rows
            if r["trades"] >= 5
            and r["avg_return"] < 0
            and r["exit_reason"] in ("market_block_quality_drop", "market_block_weak_other")
        ]
        if heavy_negative:
            worst = min(heavy_negative, key=lambda x: x["avg_return"])
            cautions.append(
                f"{label_market_signal(signal)} 진입 후 {worst['holding_bucket']} 보유에서 "
                f"{label_exit_reason(worst['exit_reason'])} 성과가 약함 ({pct_str(worst['avg_return'], signed=True)})"
            )

    # --------------------------------------------------
    # 7. ticker analysis diagnosis
    # --------------------------------------------------
    bad_tickers = _top_bad_tickers(ticker_rows, limit=5)
    if bad_tickers:
        cautions.append(
            "손실 기여 상위 종목이 존재하므로 특정 종목/섹터 편향 여부도 같이 점검해야 함"
        )

    # --------------------------------------------------
    # 7-1. sector analysis
    # --------------------------------------------------
    bad_sector_rows = []
    good_sector_rows = []

    for (
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
        avg_buy_score,
    ) in sector_rows:
        row = {
            "sector_level1": str(sector_level1),
            "sector_level2": str(sector_level2) if sector_level2 is not None else "",
            "market": str(market) if market is not None else "",
            "universe": str(universe) if universe is not None else "",
            "trades": int(trades or 0),
            "avg_return": to_float(avg_return, 0.0),
            "win_rate": to_float(win_rate, 0.0),
            "total_pnl_contribution": to_float(total_pnl_contribution, 0.0),
            "avg_holding": to_float(avg_holding, 0.0),
            "major_exit_reason": str(major_exit_reason or ""),
            "avg_buy_flow": to_float(avg_buy_flow, 0.0),
            "avg_buy_score": to_float(avg_buy_score, 0.0),
        }

        if row["trades"] >= 10:
            if row["avg_return"] <= -0.01 or row["total_pnl_contribution"] < 0:
                bad_sector_rows.append(row)
            if row["avg_return"] >= 0.02 and row["total_pnl_contribution"] > 0:
                good_sector_rows.append(row)

    if bad_sector_rows:
        worst_sector = min(
            bad_sector_rows,
            key=lambda x: (x["total_pnl_contribution"], x["avg_return"]),
        )
        sector_name = worst_sector["sector_level1"]
        if worst_sector["sector_level2"]:
            sector_name += f"/{worst_sector['sector_level2']}"

        cautions.append(
            f"{sector_name} 섹터 성과가 약함 "
            f"(거래 수 {worst_sector['trades']}건, 평균 수익률 {pct_str(worst_sector['avg_return'], signed=True)}, "
            f"총 손익 기여도 {pct_str(worst_sector['total_pnl_contribution'], signed=True)})"
        )
        actions.append(
            f"{sector_name} 섹터 비중 축소 또는 별도 필터링 실험 가치가 있음"
        )

    if good_sector_rows:
        best_sector = max(
            good_sector_rows,
            key=lambda x: (x["total_pnl_contribution"], x["avg_return"]),
        )
        sector_name = best_sector["sector_level1"]
        if best_sector["sector_level2"]:
            sector_name += f"/{best_sector['sector_level2']}"

        positives.append(
            f"{sector_name} 섹터는 성과가 양호함 "
            f"(거래 수 {best_sector['trades']}건, 평균 수익률 {pct_str(best_sector['avg_return'], signed=True)})"
        )

    # --------------------------------------------------
    # 8. run input-based action summary
    # --------------------------------------------------
    flow_min = run_inputs.get("flow_min")
    vol_penalty_multiplier = run_inputs.get("vol_penalty_multiplier")

    if flow_min is not None:
        actions.append(
            f"현재 최소 수급 기준 {flow_min}이므로, 매수 수급 점수 구간 성과 차이를 근거로 상향/하향 실험 가능"
        )

    if vol_penalty_multiplier is not None:
        actions.append(
            f"현재 변동성 감점 배수 {vol_penalty_multiplier} 기준이므로, "
            "매수 시 20일 변동성 구간과 초반 손실 구간을 함께 보면서 추가 미세조정 가능"
        )

    def dedupe(items: list[str]) -> list[str]:
        seen = set()
        result = []
        for item in items:
            if item not in seen:
                result.append(item)
                seen.add(item)
        return result

    return {
        "positives": dedupe(positives),
        "cautions": dedupe(cautions),
        "actions": dedupe(actions),
        "bad_tickers": bad_tickers,
        "salvage_examples": salvage_examples[:MBW_CFG["example_limit"]],
    }


def generate_recommendation_report(
    run_id: str,
    output_file: str = "04_추천리포트.txt",
):
    """Generate the recommendation/diagnosis report for a single run_id into the given file."""
    conn = get_conn()
    cur = conn.cursor()

    try:
        run_summary = get_run_summary(cur, run_id)
        run_inputs = get_run_inputs(cur, run_id)
        thresholds = get_thresholds(run_summary["config_snapshot"])

        reason_stats = load_reason_stats(cur, run_id)
        holding_stats = load_holding_stats(cur, run_id)
        mbweak_stats = load_mbweak_stats(cur, run_id)

        entry_rows = load_entry_stats(cur, run_id)
        signal_rows = load_signal_holding_stats(cur, run_id)
        ticker_rows = load_ticker_stats(cur, run_id)

        entry_grouped = _group_entry_stats(entry_rows)
        signal_grouped = _group_signal_holding_rows(signal_rows)

        exit_trigger_rows = load_exit_trigger_stats(cur, run_id)
        entry_day_rows = load_entry_day_stats(cur, run_id)
        sector_rows = load_sector_stats(cur, run_id)
        mbweak_bucket_rows = load_mbweak_bucket_rows(cur, run_id)
        mbweak_candidate_rows = load_mbweak_candidate_rows(cur, run_id)
        mbweak_other_rows = load_mbweak_other_rows(cur, run_id)

        result = build_recommendations(
            run_summary=run_summary,
            run_inputs=run_inputs,
            thresholds=thresholds,
            reason_stats=reason_stats,
            holding_stats=holding_stats,
            mbweak_stats=mbweak_stats,
            entry_grouped=entry_grouped,
            signal_grouped=signal_grouped,
            ticker_rows=ticker_rows,
            exit_trigger_rows=exit_trigger_rows,
            entry_day_rows=entry_day_rows,
            sector_rows=sector_rows,
            mbweak_bucket_rows=mbweak_bucket_rows,
            mbweak_candidate_rows=mbweak_candidate_rows,
            mbweak_other_rows=mbweak_other_rows,
        )

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"실행일자: {datetime.now().strftime('%Y-%m-%d')}\n")
            f.write(f"전략명: {run_summary['strategy_name']}\n")
            f.write(f"엔진: {run_summary['strategy_version']}\n")
            f.write(f"실행 ID: {run_id}\n")
            f.write(
                f"백테스트 구간: {run_summary['backtest_start_date']} ~ "
                f"{run_summary['backtest_end_date']}\n\n"
            )

            f.write("최종 결과\n")
            f.write("=============================\n")
            f.write(f"누적 이익: {pct_str(run_summary['total_return'])}\n")
            f.write(f"최대 낙폭: {pct_str(run_summary['mdd'], signed=True)}\n")
            f.write(f"샤프 지수: {to_float(run_summary['sharpe'], 0.0):.2f}\n")
            f.write(f"총 거래수: {run_summary['trade_count']}\n")
            f.write(f"실험 입력값: {format_run_inputs(run_inputs)}\n\n")

            f.write("핵심 진단\n")
            f.write("=============================\n")
            if not result["cautions"]:
                f.write("- 없음\n")
            else:
                for idx, line in enumerate(result["cautions"], 1):
                    f.write(f"{idx}. {line}\n")

            f.write("\n좋은 점\n")
            f.write("=============================\n")
            if not result["positives"]:
                f.write("- 없음\n")
            else:
                for idx, line in enumerate(result["positives"], 1):
                    f.write(f"{idx}. {line}\n")

            f.write("\n다음 액션 추천\n")
            f.write("=============================\n")
            if not result["actions"]:
                f.write("- 없음\n")
            else:
                for idx, line in enumerate(result["actions"], 1):
                    f.write(f"{idx}. {line}\n")

            f.write("\n손실 기여 상위 종목\n")
            f.write("=============================\n")
            if not result["bad_tickers"]:
                f.write("- 없음\n")
            else:
                for row in result["bad_tickers"]:
                    f.write(
                        f"- {row['company_name']} ({row['ticker_code']}): "
                        f"거래 수 {row['trades']}건, "
                        f"평균 수익률 {pct_str(row['avg_return'], signed=True)}, "
                        f"승률 {row['win_rate'] * 100:.1f}%, "
                        f"총 손익 기여도 {pct_str(row['total_pnl_contribution'], signed=True)}, "
                        f"평균 보유일 {row['avg_holding']:.2f}일, "
                        f"주요 청산 사유 {label_exit_reason(row['major_exit_reason'])}, "
                        f"평균 매수 수급 점수 {row['avg_buy_flow']:.3f}, "
                        f"평균 매수 종합 점수 {row['avg_buy_score']:.3f}\n"
                    )

            f.write("\n진입 구간 요약\n")
            f.write("=============================\n")
            if not entry_grouped:
                f.write("- 진입 분석 없음\n")
            else:
                for metric_name in sorted(entry_grouped.keys()):
                    f.write(f"[{label_entry_metric(metric_name)}]\n")
                    for row in entry_grouped[metric_name]:
                        f.write(
                            f"  - {_entry_bucket_label(metric_name, row['bucket_label'])}: "
                            f"{row['trades']}건, "
                            f"평균 수익률 {pct_str(row['avg_return'], signed=True)}, "
                            f"승률 {row['win_rate'] * 100:.1f}%, "
                            f"평균 보유일 {row['avg_holding']:.2f}일\n"
                        )
                    f.write("\n")

            f.write("\nBLOCK 선별 보유 후보 사례\n")
            f.write("=============================\n")
            salvage_examples = result["salvage_examples"]

            if not salvage_examples:
                f.write("- 없음\n")
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

                    f.write(
                        f"- {company_name} ({ticker_code}): "
                        f"유형 {_candidate_label(candidate_type)}, "
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
            raise RuntimeError("최신 실행 ID 없음")
    finally:
        cur.close()
        conn.close()

    generate_recommendation_report(run_id)
    print("✅ 04_추천리포트.txt 생성 완료")
