"""최신 backtest run 기준 텍스트 리포트 묶음을 생성하는 진입점.

DB에서 최신 run_id를 조회하고 요약/매매/거래상세/추천 리포트 파일을 로컬에 쓴다.
리포트 파일 생성과 DB 조회가 발생하므로 실행 전 출력 위치와 대상 DB를 확인해야 한다.
"""

import os
import re
from datetime import datetime

from port_strategy_research.report_summary import generate_summary_report
from port_strategy_research.report_buy_sell import generate_buy_sell_report
from port_strategy_research.report_trade_detail import generate_trade_detail_report
from port_strategy_research.report_recommendation import generate_recommendation_report
from port_strategy_research.report_data_loader import get_conn, get_latest_run_id

from port_strategy_common.config import REPORT_CONFIG


def get_today_str():
    return datetime.now().strftime("%Y%m%d")


def get_next_version(filename_prefix: str, date_str: str, ext: str = "txt") -> str:
    pattern = re.compile(rf"{filename_prefix}_{date_str}_v(\d+)\.{ext}")
    max_v = 0

    for f in os.listdir("."):
        match = pattern.match(f)
        if match:
            v = int(match.group(1))
            max_v = max(max_v, v)

    return f"{filename_prefix}_{date_str}_v{max_v + 1}.{ext}"


def main():
    today_str = get_today_str()

    conn = get_conn()
    cur = conn.cursor()

    try:
        run_id = get_latest_run_id(cur)
        if not run_id:
            raise RuntimeError("최신 실행 ID 없음")

        print(f"👉 최신 실행 ID: {run_id}")

    finally:
        cur.close()
        conn.close()

    summary_file = get_next_version(REPORT_CONFIG["file_prefix"]["summary"], today_str)
    timeline_file = get_next_version(REPORT_CONFIG["file_prefix"]["timeline"], today_str)
    trade_file = get_next_version(REPORT_CONFIG["file_prefix"]["trade_detail"], today_str)
    recommendation_file = get_next_version(REPORT_CONFIG["file_prefix"]["recommendation"], today_str)

    print("📄 생성 파일명:")
    print(f"- {summary_file}")
    print(f"- {timeline_file}")
    print(f"- {trade_file}")
    print(f"- {recommendation_file}")

    generate_summary_report(run_id, summary_file)
    generate_buy_sell_report(run_id, timeline_file)
    generate_trade_detail_report(run_id, trade_file)
    generate_recommendation_report(run_id, recommendation_file)

    print("\n✅ 전체 리포트 생성 완료")


if __name__ == "__main__":
    main()
