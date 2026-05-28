"""최신 backtest run에 대한 확장 분석 실행 진입점.

실행 시 DB에 접속해 최신 run_id를 찾고 확장 분석 테이블을 재생성한다.
문서화 작업에서는 정적 확인만 수행하고 직접 실행하지 않는다.
"""

from port_strategy_research.report_data_loader import get_conn, get_latest_run_id
from port_strategy_research.analysis_extended import run_analysis_extended


if __name__ == "__main__":
    conn = get_conn()
    cur = conn.cursor()
    try:
        run_id = get_latest_run_id(cur)
        if not run_id:
            raise RuntimeError("최신 run_id 없음")
        print(f"👉 latest run_id = {run_id}")
    finally:
        cur.close()

    try:
        run_analysis_extended(conn, run_id)
        print("✅ extended analysis 완료")
    finally:
        conn.close()
        
