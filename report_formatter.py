"""Formatter module for report label, percentage, and reason strings."""

from decimal import Decimal
from typing import Any, Optional

from port_strategy_common.config import REPORT_CONFIG

from port_strategy_research.report_locale import t, get_report_locale

FMT_CFG = REPORT_CONFIG["formatter"]


# =========================================================
# Label definitions
# =========================================================

EXIT_REASON_LABELS = {
    "market_block_early_flat": "BLOCK 초기 평탄형 청산",
    "market_block_late_flat": "BLOCK 후기 평탄형 청산",
    "market_block_quality_drop": "BLOCK 질 저하형 청산",
    "market_block_weak_other": "BLOCK 기타 약세형 청산",
    "market_block_both_weak_fast": "BLOCK 수급·점수 동시 약세형 청산",
    "market_block_flow_only_weak": "BLOCK 수급 약세형 청산",
    "market_block_mid_hold_neither_clear": "BLOCK 중기 혼합·불명확형 청산",
    "flow_breakdown": "수급 약화 정리",
    "score_breakdown": "종합 점수 약화 정리",
    "max_holding": "최대 보유기간 도달",
    "profit_protect": "이익 보전 청산",
    "early_cut": "초기 기대 미달 정리",
    "early_risk_cut": "초기 급락 방어 청산",
    "buy_day_intraday_stop": "진입 당일 급락 방어 청산",
    "intraday_stop": "장중 손절",
    "short_pressure": "공매도 압력 정리",
    "stale_loser": "장기 부진 정리",
    "weak_signal": "약한 신호 정리",
    # For backward compatibility with legacy/extended codes
    "market_block_loser": "BLOCK 손실 포지션 정리",
    "market_block_weak": "BLOCK 상대 약세 정리",
    "market_block_time_exit": "BLOCK 장기 체류 정리",
    "hard_stop": "급락 방어 강제 청산",
}

EXIT_REASON_LABELS_EN = {
    "market_block_early_flat": "BLOCK regime early-flat exit",
    "market_block_late_flat": "BLOCK regime late-flat exit",
    "market_block_quality_drop": "BLOCK regime quality-deterioration exit",
    "market_block_weak_other": "BLOCK regime other-weakness exit",
    "market_block_both_weak_fast": "BLOCK regime flow & score dual-weakness exit",
    "market_block_flow_only_weak": "BLOCK regime flow-weakness exit",
    "market_block_mid_hold_neither_clear": "BLOCK regime mid-hold mixed/unclear exit",
    "flow_breakdown": "Flow weakening exit",
    "score_breakdown": "Composite score weakening exit",
    "max_holding": "Maximum holding period reached",
    "profit_protect": "Profit protection exit",
    "early_cut": "Early underperformance exit",
    "early_risk_cut": "Early sharp-drop defensive exit",
    "buy_day_intraday_stop": "Entry-day sharp-drop defensive exit",
    "intraday_stop": "Intraday stop-loss",
    "short_pressure": "Short-selling pressure exit",
    "stale_loser": "Prolonged underperformance exit",
    "weak_signal": "Weak signal exit",
    # For backward compatibility with legacy/extended codes
    "market_block_loser": "BLOCK regime losing-position exit",
    "market_block_weak": "BLOCK regime relative-weakness exit",
    "market_block_time_exit": "BLOCK regime prolonged-holding exit",
    "hard_stop": "Hard-stop forced exit",
}

MARKET_SIGNAL_LABELS = {
    "BLOCK": "차단",
    "DEFENSIVE": "방어",
    "NEUTRAL": "중립",
    "AGGRESSIVE": "공격",
}

MARKET_SIGNAL_LABELS_EN = {
    "BLOCK": "Block",
    "DEFENSIVE": "Defensive",
    "NEUTRAL": "Neutral",
    "AGGRESSIVE": "Aggressive",
}

ENTRY_METRIC_LABELS = {
    "buy_flow": "매수 수급 점수",
    "buy_score": "매수 종합 점수",
    "buy_info": "매수 정보 점수",
    "buy_short": "매수 시 공매도 압력",
    "buy_vol": "매수 시 20일 변동성",
    "buy_intraday_range": "매수일 장중 변동폭",
    "buy_has_info_flag": "정보 신호 존재 여부",
    "buy_entry_signal": "진입 시장 상태",
    "buy_score_flow_combo": "매수 점수·수급 조합",
}

ENTRY_METRIC_LABELS_EN = {
    "buy_flow": "Buy flow score",
    "buy_score": "Buy composite score",
    "buy_info": "Buy information score",
    "buy_short": "Short-selling pressure at buy",
    "buy_vol": "20-day volatility at buy",
    "buy_intraday_range": "Entry-day intraday range",
    "buy_has_info_flag": "Information signal present",
    "buy_entry_signal": "Entry market state",
    "buy_score_flow_combo": "Buy score & flow combination",
}

MBWEAK_COMBO_LABELS = {
    "both_weak": "수급·점수 동시 약세형",
    "flow_only_weak": "수급 약세형",
    "final_only_weak": "점수 약세형",
    "neither_clear": "혼합·불명확형",
}

MBWEAK_COMBO_LABELS_EN = {
    "both_weak": "Flow & score dual-weakness type",
    "flow_only_weak": "Flow-weakness type",
    "final_only_weak": "Score-weakness type",
    "neither_clear": "Mixed/unclear type",
}

RUN_INPUT_LABELS = {
    "backtest_start_date": "백테스트 시작일",
    "decision_run_date": "판단 기준일",
    "flow_min": "최소 수급 기준",
    "vol_penalty_multiplier": "변동성 감점 배수",
}

RUN_INPUT_LABELS_EN = {
    "backtest_start_date": "Backtest start date",
    "decision_run_date": "Decision reference date",
    "flow_min": "Minimum flow threshold",
    "vol_penalty_multiplier": "Volatility penalty multiplier",
}


# =========================================================
# Common utilities
# =========================================================

def to_float(v: Any, default: Optional[float] = 0.0) -> Optional[float]:
    if v is None:
        return default
    if isinstance(v, Decimal):
        return float(v)
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def pct_str(v: Optional[float], digits: int = 2, signed: bool = False) -> str:
    if v is None:
        return t("None", "없음")
    fmt = f"{{:{'+' if signed else ''}.{digits}f}}%"
    return fmt.format(v * 100)


def safe_pct_str(v: Optional[float], digits: int = 2, signed: bool = False) -> str:
    if v is None:
        return t("None", "없음")
    return pct_str(v, digits=digits, signed=signed)


def label_market_signal(v: Any) -> str:
    if v is None:
        return t("None", "없음")
    labels = MARKET_SIGNAL_LABELS_EN if get_report_locale() == "en" else MARKET_SIGNAL_LABELS
    return labels.get(str(v), str(v))


def label_entry_metric(v: Any) -> str:
    if v is None:
        return t("None", "없음")
    labels = ENTRY_METRIC_LABELS_EN if get_report_locale() == "en" else ENTRY_METRIC_LABELS
    return labels.get(str(v), str(v))


def label_exit_reason(v: Any) -> str:
    if v is None:
        return t("None", "없음")
    labels = EXIT_REASON_LABELS_EN if get_report_locale() == "en" else EXIT_REASON_LABELS
    return labels.get(str(v), str(v))


def label_mbweak_combo(v: Any) -> str:
    if v is None:
        return t("None", "없음")
    labels = MBWEAK_COMBO_LABELS_EN if get_report_locale() == "en" else MBWEAK_COMBO_LABELS
    return labels.get(str(v), str(v))


def label_run_input(k: str) -> str:
    labels = RUN_INPUT_LABELS_EN if get_report_locale() == "en" else RUN_INPUT_LABELS
    return labels.get(k, k)


def label_bool(v: Any) -> str:
    if v is True:
        return t("Yes", "있음")
    if v is False:
        return t("None", "없음")
    return t("None", "없음")


def format_run_inputs(run_inputs: dict[str, str]) -> str:
    if not run_inputs:
        return t("None", "없음")
    parts = [f"{label_run_input(k)} {v}" for k, v in sorted(run_inputs.items())]
    return ", ".join(parts)


def holding_comment(holding_days: int, holding_stats: dict[int, dict]) -> str:
    stat = holding_stats.get(int(holding_days))
    if not stat:
        return ""

    avg_return = stat["avg_return"]
    win_rate = stat["win_rate"]
    return t(
        f" / Same {holding_days}-day holding avg {pct_str(avg_return)}, "
        f"win rate {win_rate * 100:.1f}%",
        f" / 같은 {holding_days}일 보유 평균 {pct_str(avg_return)}, "
        f"승률 {win_rate * 100:.1f}%",
    )


def build_reason_stat_line(stat: dict[str, Any]) -> str:
    return t(
        "For the same exit reason: "
        f"average return {pct_str(stat['avg_return'], signed=True)}, "
        f"win rate {stat['win_rate'] * 100:.1f}%, "
        f"trades {stat['trades']}",
        "동일 청산 사유 기준 "
        f"평균 수익률 {pct_str(stat['avg_return'], signed=True)}, "
        f"승률 {stat['win_rate'] * 100:.1f}%, "
        f"거래 수 {stat['trades']}건",
    )


def build_mbweak_stat_line(mb: dict[str, Any]) -> str:
    return t(
        "Average for BLOCK regime relative-weakness exits at the same holding period: "
        f"average return {pct_str(mb['avg_return'], signed=True)}, "
        f"average flow {mb['avg_flow']:.2f}, "
        f"average composite score {mb['avg_final']:.2f}, "
        f"trades {mb['trades']}",
        "동일 보유일수 기준 BLOCK 상대 약세 정리 평균: "
        f"평균 수익률 {pct_str(mb['avg_return'], signed=True)}, "
        f"평균 수급 {mb['avg_flow']:.2f}, "
        f"평균 종합 점수 {mb['avg_final']:.2f}, "
        f"거래 수 {mb['trades']}건",
    )


# =========================================================
# BUY REASON
# =========================================================

def build_buy_reason(
    buy_info: dict,
    thresholds: dict,
) -> list[str]:
    flow = to_float(buy_info.get("flow"), 0.0)
    score = to_float(buy_info.get("score"), 0.0)
    info = to_float(buy_info.get("info"), 0.0)

    lines: list[str] = []

    flow_min = to_float(thresholds.get("flow_min"), 0.0)
    final_min = to_float(thresholds.get("final_min"), 0.0)
    final_strong = to_float(thresholds.get("final_strong"), 0.0)
    final_extreme = to_float(thresholds.get("final_extreme"), 0.0)

    # Supply/demand (flow)
    if flow >= FMT_CFG["flow_very_strong"]:
        flow_desc = t("Flow indicators were very favorable", "수급 지표가 매우 우호적이었음")
    elif flow >= FMT_CFG["flow_strong"]:
        flow_desc = t("Flow indicators were favorable", "수급 지표가 우호적이었음")
    elif flow >= flow_min:
        flow_desc = t("Flow met the threshold", "수급 기준을 충족했음")
    else:
        flow_desc = t("Flow strength was limited", "수급 강도는 제한적이었음")

    lines.append(
        t(
            f"{flow_desc} "
            f"(flow score {flow:.2f}, minimum threshold {flow_min:.2f})",
            f"{flow_desc} "
            f"(수급 점수 {flow:.2f}, 최소 기준 {flow_min:.2f})",
        )
    )

    # Score
    if score >= final_extreme:
        score_desc = t("Composite score was in the top tier", "종합 점수가 최상위 구간이었음")
    elif score >= final_strong:
        score_desc = t("Composite score was strong relative to the threshold", "종합 점수가 기준 대비 양호했음")
    elif score >= final_min:
        score_desc = t("Composite score met the entry threshold", "종합 점수가 진입 기준을 충족했음")
    else:
        score_desc = t("Composite score warranted a conservative reading", "종합 점수는 보수적으로 해석할 수준이었음")

    lines.append(
        t(
            f"{score_desc} "
            f"(composite score {score:.2f}, "
            f"minimum threshold {final_min:.2f}, "
            f"strong threshold {final_strong:.2f}, "
            f"top-tier threshold {final_extreme:.2f})",
            f"{score_desc} "
            f"(종합 점수 {score:.2f}, "
            f"최소 기준 {final_min:.2f}, "
            f"우수 기준 {final_strong:.2f}, "
            f"최상위 기준 {final_extreme:.2f})",
        )
    )

    # Information signal
    if info > FMT_CFG["info_positive_strong"]:
        info_desc = t("Information signal was clearly positive", "정보 신호가 뚜렷하게 긍정적이었음")
    elif info > 0:
        info_desc = t("Information signal was mildly positive", "정보 신호가 완만하게 긍정적이었음")
    elif info < 0:
        info_desc = t("Information signal was somewhat weak", "정보 신호는 다소 약했음")
    else:
        info_desc = t("Information signal was neutral", "정보 신호는 중립이었음")

    lines.append(t(f"{info_desc} (information score {info:.2f})", f"{info_desc} (정보 점수 {info:.2f})"))

    # Overall decision
    decisions = []
    if flow >= flow_min:
        decisions.append(t("flow condition met", "수급 조건 충족"))
    if score >= final_min:
        decisions.append(t("score condition met", "점수 조건 충족"))
    if info > 0:
        decisions.append(t("information signal supportive", "정보 신호 보완"))

    if decisions:
        lines.append(t(f"Buy rationale: {', '.join(decisions)}", f"매수 판단: {', '.join(decisions)}"))
    else:
        lines.append(t("Buy rationale: limited on quantitative conditions but entered per record", "매수 판단: 정량 조건상 제한적이지만 기록상 진입됨"))

    return lines


# =========================================================
# SELL REASON
# =========================================================

def build_sell_reason(
    sell_info: dict,
    holding_days: int,
    thresholds: dict,
    reason_stats: dict[str, dict],
    mbweak_stats: dict[int, dict],
) -> list[str]:
    reason = str(sell_info.get("reason") or "unknown")
    flow = to_float(sell_info.get("flow"), None)
    final_score = to_float(sell_info.get("final"), None)
    short = to_float(sell_info.get("short"), None)
    cum_return = to_float(sell_info.get("cum_return"), None)
    raw_today_ret = to_float(sell_info.get("raw_today_ret"), None)
    low_ret = to_float(sell_info.get("low_ret"), None)

    lines: list[str] = []

    if reason == "buy_day_intraday_stop":
        lines.append(
            t(
                f"Reached the entry-day stop-loss threshold "
                f"({pct_str(thresholds['buy_day_intraday_stop_loss'], signed=True)})",
                f"진입 당일 손절 기준에 도달함 "
                f"({pct_str(thresholds['buy_day_intraday_stop_loss'], signed=True)})",
            )
        )
        if low_ret is not None:
            lines.append(t(f"Loss at intraday low {pct_str(low_ret, signed=True)}", f"장중 저점 기준 손실 {pct_str(low_ret, signed=True)}"))

    elif reason == "intraday_stop":
        lines.append(t("Exited as intraday movement fell below the stop-loss threshold", "장중 변동이 손절 기준을 하회해 정리함"))
        if low_ret is not None:
            lines.append(t(f"Loss at intraday low {pct_str(low_ret, signed=True)}", f"장중 저점 기준 손실 {pct_str(low_ret, signed=True)}"))
        if cum_return is not None:
            lines.append(t(f"Final cumulative return {pct_str(cum_return, signed=True)}", f"최종 누적 수익률 {pct_str(cum_return, signed=True)}"))

    elif reason == "hard_stop":
        msg = t("Exited immediately as the daily loss fell below the hard-stop threshold", "당일 손실이 하드스탑 기준을 하회해 즉시 청산함")
        if raw_today_ret is not None:
            msg += t(f" (today {pct_str(raw_today_ret, signed=True)})", f" (당일 {pct_str(raw_today_ret, signed=True)})")
        lines.append(msg)

        lines.append(
            t(
                f"Threshold: daily loss "
                f"{pct_str(thresholds['hard_stop_daily_return'], signed=True)} or below",
                f"기준: 일간 손실 "
                f"{pct_str(thresholds['hard_stop_daily_return'], signed=True)} 이하",
            )
        )

        lines.append(t("Hard-stop rule: forced exit to block sharp-drop risk", "하드스탑 규칙: 급락 리스크 차단을 위한 강제 청산"))

        if cum_return is not None:
            lines.append(t(f"Final cumulative return {pct_str(cum_return, signed=True)}", f"최종 누적 수익률 {pct_str(cum_return, signed=True)}"))

    elif reason == "profit_protect":
        msg = t("Exited as the profit protection condition was met", "이익 보호 조건이 충족되어 정리함")
        if cum_return is not None and raw_today_ret is not None:
            msg += t(
                f" (cumulative {pct_str(cum_return, signed=True)}, "
                f"today {pct_str(raw_today_ret, signed=True)})",
                f" (누적 {pct_str(cum_return, signed=True)}, "
                f"당일 {pct_str(raw_today_ret, signed=True)})",
            )
        lines.append(msg)
        lines.append(
            t(
                "Threshold: "
                f"cumulative {pct_str(thresholds['profit_protect_cum_return'])} or above "
                f"+ daily drop {pct_str(thresholds['profit_protect_daily_drop'], signed=True)} or below",
                "기준: "
                f"누적 {pct_str(thresholds['profit_protect_cum_return'])} 이상 "
                f"+ 당일 하락 {pct_str(thresholds['profit_protect_daily_drop'], signed=True)} 이하",
            )
        )
        if flow is not None or final_score is not None:
            lines.append(
                t(
                    "Indicators at exit: "
                    f"flow {flow if flow is not None else 0.0:.2f}, "
                    f"composite score {final_score if final_score is not None else 0.0:.2f}",
                    "청산 시점 지표: "
                    f"수급 {flow if flow is not None else 0.0:.2f}, "
                    f"종합 점수 {final_score if final_score is not None else 0.0:.2f}",
                )
            )

    elif reason == "early_risk_cut":
        lines.append(t("Exited per risk-management conditions during the early holding period", "초기 보유 구간에서 리스크 관리 조건에 따라 정리함"))
        if raw_today_ret is not None:
            lines.append(t(f"Today's return {pct_str(raw_today_ret, signed=True)}", f"당일 수익률 {pct_str(raw_today_ret, signed=True)}"))
        lines.append(
            t(
                f"Threshold: early-period daily loss "
                f"{pct_str(thresholds['early_risk_cut_daily_return'], signed=True)} or below",
                f"기준: 초기 구간 일간 손실 "
                f"{pct_str(thresholds['early_risk_cut_daily_return'], signed=True)} 이하",
            )
        )
        if cum_return is not None:
            lines.append(t(f"Final cumulative return {pct_str(cum_return, signed=True)}", f"최종 누적 수익률 {pct_str(cum_return, signed=True)}"))

    elif reason == "early_cut":
        lines.append(t("Exited as the early response fell short of expectations", "초기 반응이 기대에 못 미쳐 정리함"))
        if cum_return is not None:
            lines.append(t(f"Cumulative return {pct_str(cum_return, signed=True)}", f"누적 수익률 {pct_str(cum_return, signed=True)}"))
        lines.append(
            t(
                f"Threshold: early-period cumulative return "
                f"{pct_str(thresholds['early_cut_cum_return'], signed=True)} or below",
                f"기준: 초기 구간 누적 수익률 "
                f"{pct_str(thresholds['early_cut_cum_return'], signed=True)} 이하",
            )
        )

    elif reason == "market_block_loser":
        lines.append(t("Prioritized exiting the losing position during the BLOCK regime", "BLOCK 구간에서 손실 포지션을 우선 정리함"))
        if cum_return is not None:
            lines.append(t(f"Cumulative return {pct_str(cum_return, signed=True)}", f"누적 수익률 {pct_str(cum_return, signed=True)}"))

    elif reason == "market_block_weak":
        lines.append(t("Exited due to low relative advantage during the BLOCK regime", "BLOCK 구간에서 상대 우위가 낮아 정리함"))
        lines.append(
            t(
                f"Held {holding_days} days, below the minimum expected return to hold "
                f"{pct_str(thresholds['market_block_min_keep_profit'])}",
                f"보유 {holding_days}일, 유지 최소 기대수익 "
                f"{pct_str(thresholds['market_block_min_keep_profit'])} 미만",
            )
        )
        if flow is not None or final_score is not None:
            lines.append(
                t(
                    "Indicators at exit: "
                    f"flow {flow if flow is not None else 0.0:.2f}, "
                    f"composite score {final_score if final_score is not None else 0.0:.2f}",
                    "청산 시점 지표: "
                    f"수급 {flow if flow is not None else 0.0:.2f}, "
                    f"종합 점수 {final_score if final_score is not None else 0.0:.2f}",
                )
            )
        if cum_return is not None:
            lines.append(t(f"Cumulative return {pct_str(cum_return, signed=True)}", f"누적 수익률 {pct_str(cum_return, signed=True)}"))

        mb = mbweak_stats.get(int(holding_days))
        if mb:
            lines.append(build_mbweak_stat_line(mb))

    elif reason == "market_block_time_exit":
        lines.append(t("Exited due to prolonged holding during the BLOCK regime", "BLOCK 구간 장기 체류로 인해 정리함"))
        lines.append(
            t(
                f"Reference maximum holding days "
                f"{thresholds['market_block_max_win_holding_days']} days",
                f"기준 최대 보유 참고일수 "
                f"{thresholds['market_block_max_win_holding_days']}일",
            )
        )
        if cum_return is not None:
            lines.append(t(f"Final cumulative return {pct_str(cum_return, signed=True)}", f"최종 누적 수익률 {pct_str(cum_return, signed=True)}"))

    elif reason == "flow_breakdown":
        lines.append(t("Exited as the flow advantage weakened", "수급 우위가 약화되어 정리함"))
        if flow is not None:
            lines.append(t(f"Flow score at exit {flow:.2f}", f"청산 시점 수급 점수 {flow:.2f}"))
        if cum_return is not None:
            lines.append(t(f"Cumulative return {pct_str(cum_return, signed=True)}", f"누적 수익률 {pct_str(cum_return, signed=True)}"))

    elif reason == "score_breakdown":
        lines.append(t("Exited as the composite score slowed relative to the entry rationale", "종합 점수가 진입 근거 대비 둔화되어 정리함"))
        if final_score is not None:
            lines.append(t(f"Composite score at exit {final_score:.2f}", f"청산 시점 종합 점수 {final_score:.2f}"))
        if cum_return is not None:
            lines.append(t(f"Cumulative return {pct_str(cum_return, signed=True)}", f"누적 수익률 {pct_str(cum_return, signed=True)}"))

    elif reason == "max_holding":
        lines.append(t(f"Exited on reaching the maximum holding period ({holding_days} days held)", f"최대 보유 기간에 도달해 정리함 ({holding_days}일 보유)"))
        lines.append(t(f"Reference maximum holding days {thresholds['max_holding_days']} days", f"기준 최대 보유일수 {thresholds['max_holding_days']}일"))
        if cum_return is not None:
            lines.append(t(f"Final return {pct_str(cum_return, signed=True)}", f"최종 수익률 {pct_str(cum_return, signed=True)}"))

    elif reason == "weak_signal":
        lines.append(t("Exited as signal strength weakened", "신호 강도가 약화되어 정리함"))
        if cum_return is not None:
            lines.append(t(f"Cumulative return {pct_str(cum_return, signed=True)}", f"누적 수익률 {pct_str(cum_return, signed=True)}"))

    elif reason == "stale_loser":
        lines.append(t("Exited as the rebound strength was limited relative to the holding period", "보유 기간 대비 반등 강도가 제한적이어서 정리함"))
        if flow is not None:
            lines.append(t(f"Flow score at exit {flow:.2f}", f"청산 시점 수급 점수 {flow:.2f}"))
        if cum_return is not None:
            lines.append(t(f"Cumulative return {pct_str(cum_return, signed=True)}", f"누적 수익률 {pct_str(cum_return, signed=True)}"))

    elif reason == "short_pressure":
        lines.append(t("Exited as short-selling pressure increased", "공매도 압력이 높아져 정리함"))
        if short is not None:
            lines.append(t(f"Short-selling pressure at exit {short:.2f}", f"청산 시점 공매도 압력 {short:.2f}"))
        if cum_return is not None:
            lines.append(t(f"Cumulative return {pct_str(cum_return, signed=True)}", f"누적 수익률 {pct_str(cum_return, signed=True)}"))

    else:
        labels = EXIT_REASON_LABELS_EN if get_report_locale() == "en" else EXIT_REASON_LABELS
        label = labels.get(reason, t(f"Other reason exit ({reason})", f"기타 사유 정리 ({reason})"))
        lines.append(label)
        if cum_return is not None:
            lines.append(t(f"Cumulative return {pct_str(cum_return, signed=True)}", f"누적 수익률 {pct_str(cum_return, signed=True)}"))

    stat = reason_stats.get(reason)
    if stat:
        lines.append(build_reason_stat_line(stat))

    return lines
