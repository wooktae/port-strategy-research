"""리포트 출력용 label, percentage, 사유 문자열 포맷터 모듈."""

from decimal import Decimal
from typing import Any, Optional

from port_strategy_common.config import REPORT_CONFIG

FMT_CFG = REPORT_CONFIG["formatter"]


# =========================================================
# 라벨 정의
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
    # 과거/확장 코드 호환용
    "market_block_loser": "BLOCK 손실 포지션 정리",
    "market_block_weak": "BLOCK 상대 약세 정리",
    "market_block_time_exit": "BLOCK 장기 체류 정리",
    "hard_stop": "급락 방어 강제 청산",
}

MARKET_SIGNAL_LABELS = {
    "BLOCK": "차단",
    "DEFENSIVE": "방어",
    "NEUTRAL": "중립",
    "AGGRESSIVE": "공격",
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

MBWEAK_COMBO_LABELS = {
    "both_weak": "수급·점수 동시 약세형",
    "flow_only_weak": "수급 약세형",
    "final_only_weak": "점수 약세형",
    "neither_clear": "혼합·불명확형",
}

RUN_INPUT_LABELS = {
    "backtest_start_date": "백테스트 시작일",
    "decision_run_date": "판단 기준일",
    "flow_min": "최소 수급 기준",
    "vol_penalty_multiplier": "변동성 감점 배수",
}


# =========================================================
# 공통 유틸
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
        return "없음"
    fmt = f"{{:{'+' if signed else ''}.{digits}f}}%"
    return fmt.format(v * 100)


def safe_pct_str(v: Optional[float], digits: int = 2, signed: bool = False) -> str:
    if v is None:
        return "없음"
    return pct_str(v, digits=digits, signed=signed)


def label_market_signal(v: Any) -> str:
    if v is None:
        return "없음"
    return MARKET_SIGNAL_LABELS.get(str(v), str(v))


def label_entry_metric(v: Any) -> str:
    if v is None:
        return "없음"
    return ENTRY_METRIC_LABELS.get(str(v), str(v))


def label_exit_reason(v: Any) -> str:
    if v is None:
        return "없음"
    return EXIT_REASON_LABELS.get(str(v), str(v))


def label_mbweak_combo(v: Any) -> str:
    if v is None:
        return "없음"
    return MBWEAK_COMBO_LABELS.get(str(v), str(v))


def label_run_input(k: str) -> str:
    return RUN_INPUT_LABELS.get(k, k)


def label_bool(v: Any) -> str:
    if v is True:
        return "있음"
    if v is False:
        return "없음"
    return "없음"


def format_run_inputs(run_inputs: dict[str, str]) -> str:
    if not run_inputs:
        return "없음"
    parts = [f"{label_run_input(k)} {v}" for k, v in sorted(run_inputs.items())]
    return ", ".join(parts)


def holding_comment(holding_days: int, holding_stats: dict[int, dict]) -> str:
    stat = holding_stats.get(int(holding_days))
    if not stat:
        return ""

    avg_return = stat["avg_return"]
    win_rate = stat["win_rate"]
    return (
        f" / 같은 {holding_days}일 보유 평균 {pct_str(avg_return)}, "
        f"승률 {win_rate * 100:.1f}%"
    )


def build_reason_stat_line(stat: dict[str, Any]) -> str:
    return (
        "동일 청산 사유 기준 "
        f"평균 수익률 {pct_str(stat['avg_return'], signed=True)}, "
        f"승률 {stat['win_rate'] * 100:.1f}%, "
        f"거래 수 {stat['trades']}건"
    )


def build_mbweak_stat_line(mb: dict[str, Any]) -> str:
    return (
        "동일 보유일수 기준 BLOCK 상대 약세 정리 평균: "
        f"평균 수익률 {pct_str(mb['avg_return'], signed=True)}, "
        f"평균 수급 {mb['avg_flow']:.2f}, "
        f"평균 종합 점수 {mb['avg_final']:.2f}, "
        f"거래 수 {mb['trades']}건"
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

    # 수급
    if flow >= FMT_CFG["flow_very_strong"]:
        flow_desc = "수급 지표가 매우 우호적이었음"
    elif flow >= FMT_CFG["flow_strong"]:
        flow_desc = "수급 지표가 우호적이었음"
    elif flow >= flow_min:
        flow_desc = "수급 기준을 충족했음"
    else:
        flow_desc = "수급 강도는 제한적이었음"

    lines.append(
        f"{flow_desc} "
        f"(수급 점수 {flow:.2f}, 최소 기준 {flow_min:.2f})"
    )

    # 점수
    if score >= final_extreme:
        score_desc = "종합 점수가 최상위 구간이었음"
    elif score >= final_strong:
        score_desc = "종합 점수가 기준 대비 양호했음"
    elif score >= final_min:
        score_desc = "종합 점수가 진입 기준을 충족했음"
    else:
        score_desc = "종합 점수는 보수적으로 해석할 수준이었음"

    lines.append(
        f"{score_desc} "
        f"(종합 점수 {score:.2f}, "
        f"최소 기준 {final_min:.2f}, "
        f"우수 기준 {final_strong:.2f}, "
        f"최상위 기준 {final_extreme:.2f})"
    )

    # 정보
    if info > FMT_CFG["info_positive_strong"]:
        info_desc = "정보 신호가 뚜렷하게 긍정적이었음"
    elif info > 0:
        info_desc = "정보 신호가 완만하게 긍정적이었음"
    elif info < 0:
        info_desc = "정보 신호는 다소 약했음"
    else:
        info_desc = "정보 신호는 중립이었음"

    lines.append(f"{info_desc} (정보 점수 {info:.2f})")

    # 종합 판단
    decisions = []
    if flow >= flow_min:
        decisions.append("수급 조건 충족")
    if score >= final_min:
        decisions.append("점수 조건 충족")
    if info > 0:
        decisions.append("정보 신호 보완")

    if decisions:
        lines.append(f"매수 판단: {', '.join(decisions)}")
    else:
        lines.append("매수 판단: 정량 조건상 제한적이지만 기록상 진입됨")

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
            f"진입 당일 손절 기준에 도달함 "
            f"({pct_str(thresholds['buy_day_intraday_stop_loss'], signed=True)})"
        )
        if low_ret is not None:
            lines.append(f"장중 저점 기준 손실 {pct_str(low_ret, signed=True)}")

    elif reason == "intraday_stop":
        lines.append("장중 변동이 손절 기준을 하회해 정리함")
        if low_ret is not None:
            lines.append(f"장중 저점 기준 손실 {pct_str(low_ret, signed=True)}")
        if cum_return is not None:
            lines.append(f"최종 누적 수익률 {pct_str(cum_return, signed=True)}")

    elif reason == "hard_stop":
        msg = "당일 손실이 하드스탑 기준을 하회해 즉시 청산함"
        if raw_today_ret is not None:
            msg += f" (당일 {pct_str(raw_today_ret, signed=True)})"
        lines.append(msg)

        lines.append(
            f"기준: 일간 손실 "
            f"{pct_str(thresholds['hard_stop_daily_return'], signed=True)} 이하"
        )

        lines.append("하드스탑 규칙: 급락 리스크 차단을 위한 강제 청산")

        if cum_return is not None:
            lines.append(f"최종 누적 수익률 {pct_str(cum_return, signed=True)}")

    elif reason == "profit_protect":
        msg = "이익 보호 조건이 충족되어 정리함"
        if cum_return is not None and raw_today_ret is not None:
            msg += (
                f" (누적 {pct_str(cum_return, signed=True)}, "
                f"당일 {pct_str(raw_today_ret, signed=True)})"
            )
        lines.append(msg)
        lines.append(
            "기준: "
            f"누적 {pct_str(thresholds['profit_protect_cum_return'])} 이상 "
            f"+ 당일 하락 {pct_str(thresholds['profit_protect_daily_drop'], signed=True)} 이하"
        )
        if flow is not None or final_score is not None:
            lines.append(
                "청산 시점 지표: "
                f"수급 {flow if flow is not None else 0.0:.2f}, "
                f"종합 점수 {final_score if final_score is not None else 0.0:.2f}"
            )

    elif reason == "early_risk_cut":
        lines.append("초기 보유 구간에서 리스크 관리 조건에 따라 정리함")
        if raw_today_ret is not None:
            lines.append(f"당일 수익률 {pct_str(raw_today_ret, signed=True)}")
        lines.append(
            f"기준: 초기 구간 일간 손실 "
            f"{pct_str(thresholds['early_risk_cut_daily_return'], signed=True)} 이하"
        )
        if cum_return is not None:
            lines.append(f"최종 누적 수익률 {pct_str(cum_return, signed=True)}")

    elif reason == "early_cut":
        lines.append("초기 반응이 기대에 못 미쳐 정리함")
        if cum_return is not None:
            lines.append(f"누적 수익률 {pct_str(cum_return, signed=True)}")
        lines.append(
            f"기준: 초기 구간 누적 수익률 "
            f"{pct_str(thresholds['early_cut_cum_return'], signed=True)} 이하"
        )

    elif reason == "market_block_loser":
        lines.append("BLOCK 구간에서 손실 포지션을 우선 정리함")
        if cum_return is not None:
            lines.append(f"누적 수익률 {pct_str(cum_return, signed=True)}")

    elif reason == "market_block_weak":
        lines.append("BLOCK 구간에서 상대 우위가 낮아 정리함")
        lines.append(
            f"보유 {holding_days}일, 유지 최소 기대수익 "
            f"{pct_str(thresholds['market_block_min_keep_profit'])} 미만"
        )
        if flow is not None or final_score is not None:
            lines.append(
                "청산 시점 지표: "
                f"수급 {flow if flow is not None else 0.0:.2f}, "
                f"종합 점수 {final_score if final_score is not None else 0.0:.2f}"
            )
        if cum_return is not None:
            lines.append(f"누적 수익률 {pct_str(cum_return, signed=True)}")

        mb = mbweak_stats.get(int(holding_days))
        if mb:
            lines.append(build_mbweak_stat_line(mb))

    elif reason == "market_block_time_exit":
        lines.append("BLOCK 구간 장기 체류로 인해 정리함")
        lines.append(
            f"기준 최대 보유 참고일수 "
            f"{thresholds['market_block_max_win_holding_days']}일"
        )
        if cum_return is not None:
            lines.append(f"최종 누적 수익률 {pct_str(cum_return, signed=True)}")

    elif reason == "flow_breakdown":
        lines.append("수급 우위가 약화되어 정리함")
        if flow is not None:
            lines.append(f"청산 시점 수급 점수 {flow:.2f}")
        if cum_return is not None:
            lines.append(f"누적 수익률 {pct_str(cum_return, signed=True)}")

    elif reason == "score_breakdown":
        lines.append("종합 점수가 진입 근거 대비 둔화되어 정리함")
        if final_score is not None:
            lines.append(f"청산 시점 종합 점수 {final_score:.2f}")
        if cum_return is not None:
            lines.append(f"누적 수익률 {pct_str(cum_return, signed=True)}")

    elif reason == "max_holding":
        lines.append(f"최대 보유 기간에 도달해 정리함 ({holding_days}일 보유)")
        lines.append(f"기준 최대 보유일수 {thresholds['max_holding_days']}일")
        if cum_return is not None:
            lines.append(f"최종 수익률 {pct_str(cum_return, signed=True)}")

    elif reason == "weak_signal":
        lines.append("신호 강도가 약화되어 정리함")
        if cum_return is not None:
            lines.append(f"누적 수익률 {pct_str(cum_return, signed=True)}")

    elif reason == "stale_loser":
        lines.append("보유 기간 대비 반등 강도가 제한적이어서 정리함")
        if flow is not None:
            lines.append(f"청산 시점 수급 점수 {flow:.2f}")
        if cum_return is not None:
            lines.append(f"누적 수익률 {pct_str(cum_return, signed=True)}")

    elif reason == "short_pressure":
        lines.append("공매도 압력이 높아져 정리함")
        if short is not None:
            lines.append(f"청산 시점 공매도 압력 {short:.2f}")
        if cum_return is not None:
            lines.append(f"누적 수익률 {pct_str(cum_return, signed=True)}")

    else:
        label = EXIT_REASON_LABELS.get(reason, f"기타 사유 정리 ({reason})")
        lines.append(label)
        if cum_return is not None:
            lines.append(f"누적 수익률 {pct_str(cum_return, signed=True)}")

    stat = reason_stats.get(reason)
    if stat:
        lines.append(build_reason_stat_line(stat))

    return lines
