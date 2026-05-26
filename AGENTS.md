# AGENTS.md - port_strategy_research

## 프로젝트

- 이 저장소는 포트폴리오 전략의 백테스트, 분석, 리포트 생성을 담당하는 Python research MS 루트다.
- 주요 역할은 전처리된 market/stock/price feature를 읽어 백테스트를 수행하고, run/daily/trade log/analysis/report 계열 산출물을 생성하는 것이다.
- `port_strategy_common`의 config, common buy guard, buy sizing haircut, sell decision, utility, common model을 재사용한다.
- `port_strategy_decision`의 market decision, buy candidate filter, backtest sizing 로직을 재사용한다.
- 현재 구조는 패키지 디렉터리보다 루트에 배치된 실행형 Python 스크립트 중심이다.

## 작업 범위

- 현재 `port_strategy_research` 루트 안에서만 작업한다.
- 현재 루트 밖 파일은 참고용으로만 읽고 수정하지 않는다.
- 소스 코드 또는 문서 수정 전 현재 파일 구조와 실행 영향 범위를 먼저 확인한다.
- 변경은 작고 검증 가능한 범위로 제한한다.
- 사용자가 문서 작업을 요청한 경우 문서 파일만 수정한다.
- 사용자가 코드 수정을 명시하지 않은 경우 Python 소스 코드는 수정하지 않는다.

## 허용 작업

- README / docs / worklog 작성 및 수정
- Python 스크립트 구조의 정적 분석
- 실행하지 않는 범위의 import, entrypoint, DB 접근 지점, 파일 출력 지점 확인
- backtest engine, loader, buy/sell logic, position manager, trade log, metrics, report/analysis 스크립트 구분
- `port_strategy_common` 의존성과 `port_strategy_decision` 재사용 지점 문서화
- 실행 위험, 설정 항목, 검증 한계, 후속 작업 문서화
- 명시 요청이 있는 경우에만 테스트 또는 디버그 코드 정리

## 금지 작업

- 실제 백테스트 실행 금지
- research/backtest 실행 금지
- 리포트 생성 실행 금지
- DB DDL/DML 직접 실행 금지
- DB 쓰기/저장 helper 실행 금지
- 외부 API 호출 금지
- 크롤링 실행 금지
- 주문 제출 또는 주문 실행 금지
- 실제 트레이딩, batch, execution workflow 실행 금지
- 민감정보 값 출력 또는 문서 기록 금지
- 실제 로컬 운영 설정 파일 수정 금지
- 명시 승인 없는 파일 삭제 금지
- 명시 요청 없는 commit 금지

## 유지해야 할 계약

- 기존 DB 테이블명, 컬럼명, unique key, upsert 정책을 임의로 바꾸지 않는다.
- `strategy_backtest_run`, `strategy_backtest_daily`, `strategy_trade_log` 관련 저장 계약을 임의로 바꾸지 않는다.
- `strategy_backtest_*_analysis` 계열 분석 테이블의 run_id 기준 생성/갱신 흐름을 임의로 바꾸지 않는다.
- `pre_total_market_daily_feature`, `pre_total_stock_daily_feature`, `interest_price_raw`, `stock_universe` 입력 feature 계약을 임의로 바꾸지 않는다.
- `port_strategy_common`의 public config key, dataclass field, enum/reason 문자열, common function signature를 단정하거나 임의 변경하지 않는다.
- `port_strategy_decision`의 market/filter/sizing 결과 구조와 reason 문자열을 단정하거나 임의 변경하지 않는다.
- backtest와 daily decision이 공유하는 common market/filter/sizing/sell 판단 호환성을 훼손하지 않는다.
- test/debug/output/report dump 파일은 운영 소스로 단정하지 말고 후보 또는 로컬 산출물로만 표현한다.

## 스크립트 구분 원칙

- backtest engine 계열은 `backtest_engine.py`, `backtest_research_run.py` 중심으로 본다.
- loader 계열은 `backtest_loader.py`, `report_data_loader.py` 중심으로 본다.
- buy/sell logic 계열은 `backtest_buy_logic.py`, `backtest_sell_logic.py` 중심으로 본다.
- position/trade 계열은 `backtest_position_manager.py`, `backtest_trade_log.py` 중심으로 본다.
- metrics 계열은 `backtest_metrics.py` 중심으로 본다.
- analysis 저장 계열은 `backtest_analysis_basic.py`, `analysis_extended.py`, `run_extended_analysis.py` 중심으로 본다.
- report 생성 계열은 `backtest_report_run.py`, `report_summary.py`, `report_buy_sell.py`, `report_trade_detail.py`, `report_recommendation.py`, `report_formatter.py` 중심으로 본다.
- block/watch/exception-buy 연구 계열은 `block_watch_*`, `block_exception_buy_*` 파일로 구분하되, 실행 전 DB write 여부를 반드시 정적으로 확인한다.

## 실행 위험 파일

- `backtest_research_run.py`
  - DB 연결, run 생성, config/input snapshot 저장, backtest 실행, analysis 저장, commit 가능.
- `backtest_engine.py`
  - daily result 저장과 commit 가능.
- `backtest_run_store.py`
  - DDL, insert, upsert, update, commit 가능.
- `backtest_trade_log.py`
  - `strategy_trade_log` insert 가능.
- `backtest_buy_logic.py`
  - 당일 손절 거래 저장 가능.
- `backtest_position_manager.py`
  - 청산 거래 저장 가능.
- `analysis_extended.py`, `backtest_analysis_basic.py`, `run_extended_analysis.py`
  - 분석 테이블 delete/insert 가능.
- `backtest_report_run.py`, `report_*.py`
  - DB read와 로컬 txt report 파일 생성 가능.
- `block_watch_analysis_run.py`
  - watch 후보 수익률 update 가능.
- `block_watch_backtest_run.py`, `block_exception_buy_engine_run.py`, `block_exception_buy_backtest_run.py`
  - backtest 유사 실행 또는 DB 연결 가능성이 있으므로 실행 금지 대상으로 본다.

## 보안 규칙

- 비밀번호, token, API key, 계좌번호, webhook URL, DB 접속정보, 실제 사용자 ID 등 민감정보 값을 출력하거나 문서에 기록하지 않는다.
- 민감정보가 필요하면 `[REDACTED]`로 마스킹한다.
- 로컬 파일에서 민감정보를 발견해도 값을 인용하지 않는다.
- 예시 설정에는 실제 credential을 넣지 않는다.
- secret은 source가 아니라 환경변수 또는 local config로 분리하는 방향을 우선한다.

## Git 규칙

- 작업 전후 `git status --short`로 변경 범위를 확인한다.
- 작업 후 `git diff --stat`으로 변경 파일 범위를 확인한다.
- untracked 파일은 `git diff --stat`에 잡히지 않을 수 있으므로 `git status --short`를 함께 본다.
- 사용자 변경을 되돌리지 않는다.
- 명시 요청 없이 commit하지 않는다.
- 명시 승인 없이 destructive command를 실행하지 않는다.

## 검증 명령

문서만 수정한 경우:

```powershell
git status --short
git diff --stat
```

코드 수정 시에는 실제 backtest/research, report 생성, DB 쓰기, 외부 API, 크롤링, 주문 실행이 포함되지 않는 검증만 선택한다. 실행 위험이 있으면 완료 보고에 검증 한계를 명확히 적는다.

## 완료 보고

작업 완료 시 아래 항목만 짧게 보고한다.

- 변경 파일
- 변경 요약
- 검증 결과
- 남은 위험 또는 후속 작업

## 문서화 규칙

- README.md는 프로젝트 이해, 실행 방법, 설정 방법, 주요 기능, 폴더 구조, 외부 의존성이 바뀐 경우에만 갱신한다.
- CHANGELOG.md에는 실제 변경된 주요 내용만 짧게 기록한다.
- docs/worklog/YYYY-MM-DD.md에는 작업 내용을 계획/완료 처리 형식으로 정리한다.
- worklog 작성 시 아래 들여쓰기 형식을 유지한다.
  - `1. 큰 작업 명`
  - ` 1) 세부 작업`
  - `   (1) 더 세부 작업`
  - `       - 추가 설명`
- 완료/예정/보류/실패/확인 상태를 작업 명 끝에 `: 완료`, `: 예정`, `: 보류`, `: 실패`, `: 확인`으로 명확히 표시한다.
- 상태값은 `작업 명: 완료`처럼 작업 명과 콜론 사이에 공백을 두지 않는다.
- test/debug/output/report dump 파일은 운영 소스로 단정하지 말고 후보 또는 로컬 산출물로만 표현한다.
- 참고한 sibling 프로젝트 문서는 형식과 문서화 원칙 참고용으로만 사용하고 현재 루트 문서에 맞게 재작성한다.

