# CHANGELOG

## 2026-07-01

### Added

- README에 Research 책임 경계 섹션을 추가했다. Research가 담당하는 backtest/analysis/report 영역과 Crawler, Preprocessor, StrategyDecision, StrategyExecution, MarketConnector, port-view가 각각 담당하는 영역을 구분해 서술했다.
- README에 AWS Paper Daily 운영 관점 섹션을 추가했다. Daily Step 4 Backtest Research는 `backtest_research_run.py`, Daily Step 5 Backtest Report는 `backtest_report_run.py`가 담당하는 흐름으로 정리했다.
- README에 컨테이너 실행 구조 섹션을 추가했다. `Dockerfile`, `requirements.txt`, `aws_batch_backtest_report_wrapper.py`의 역할과 `REPORT_OUTPUT_DIR`, `RESEARCH_APP_SECRET_JSON`, `REPORT_S3_BUCKET`, `REPORT_S3_PREFIX`, `AWS_BATCH_JOB_ID` 사용 경로를 설명했다.
- README에 block/watch/exception-buy 연구 계열 섹션을 추가했다. 연구/보류 계열로만 표현하고 daily 운영 파이프라인과 분리했다.
- README와 실행 위험 목록에 `aws_batch_backtest_report_wrapper.py`를 추가했다.
- README 파일 구조 트리에 `Dockerfile`, `requirements.txt`, `aws_batch_backtest_report_wrapper.py`, `research_backtest_market_adapter.py`, `research_backtest_filter_adapter.py`, `research_backtest_sizing_adapter.py`를 반영했다.
- `docs/source-file-catalog.md`에 Research 내부 adapter 3종과 컨테이너/AWS Batch wrapper 3종을 새 표로 추가했다.
- `docs/worklog/2026-07-01.md` 작업 기록을 추가했다.

### Changed

- README의 Research/Decision 관계 서술을 최신 상태로 갱신했다. Research는 내부 adapter를 통해 `port_strategy_common`을 직접 호출하며, `port_strategy_decision` 런타임 import 없이 backtest 흐름이 동작한다는 점을 명시했다.
- README Engine/Buy Logic 섹션의 호출 경로를 `research_backtest_market_adapter.evaluate_market`, `research_backtest_filter_adapter.filter_buy_candidates`, `research_backtest_sizing_adapter.allocate_positions` 기준으로 갱신했다.
- README 외부 의존성 섹션에서 `port_strategy_decision`을 런타임 의존에서 제거하고 `boto3` 추가와 `psycopg2-binary` 표기를 반영했다.
- `docs/source-file-catalog.md`의 `backtest_buy_logic.py` 항목을 adapter 경유 표현으로 갱신했다.

### Notes

- 기능 변경 없음. 이번 변경은 md 문서에 한정된 최신화 작업이다.
- 실제 백테스트, research run, 리포트 생성, DB DDL/DML, 외부 API 호출, 크롤링, 주문 실행, AWS Batch/ECS/Step Functions/EventBridge 실행, S3 업로드, Slack 통지는 수행하지 않았다.
- 다른 마이크로서비스(port-view, MarketConnector, Crawler, Preprocessor, StrategyDecision, StrategyExecution) 내부 상세, Step Functions state machine 전체 step, EventBridge Scheduler 전체 라인업, Lambda 내부 구현, command id, 실행 시간, 일회성 검증 로그는 반영 범위에서 제외했다.
- DB password, API key, token, Slack webhook URL, 계좌번호, secret ARN, IAM Role ARN, AWS Batch job definition/queue ARN, ECS task definition ARN, image URI, S3 bucket/path, command id, 전체 DB connection string은 문서에 기록하지 않았다.

## 2026-05-28

### Added

- `docs/source-file-catalog.md`를 추가해 파일별 역할, 주요 책임, 수정/운영 시 주의사항을 정리했다.
- Python 소스 파일 상단에 한글 module docstring을 추가했다.
- DB 저장, 분석 저장, 리포트 생성, 핵심 백테스트 파이프라인 함수에 한해 짧은 function docstring을 추가했다.
- 2026-05-28 작업 기록을 `docs/worklog/2026-05-28.md`에 추가했다.

### Changed

- README에 일별 포지션 snapshot 저장/조회 흐름과 파일 카탈로그 문서 위치를 반영했다.
- 기존 미커밋 변경사항인 `strategy_backtest_daily_position` 저장 및 리포트 조회 전환 내용을 문서화했다.

### Notes

- 기능 변경 없음. 문서화와 설명 주석만 추가했다.
- 실제 백테스트, research run, 리포트 생성, DB DDL/DML, 외부 API 호출, 크롤링, 주문 실행은 수행하지 않았다.
- 실제 password, token, account, webhook URL 값은 기록하지 않는다.

## 2026-05-27

### Added

- 로컬 PostgreSQL DB name 기본값이 `portfolio`임을 문서화했다.
- 단일 DB `portfolio`와 domain별 schema를 사용하는 schema-per-domain 구조를 문서화했다.
- `port_strategy_research` DB connection search_path를 `research, preprocessor, interest, reference, legacy, public`으로 명시했다.

### Changed

- DB 접속 설정을 `db_config.py`의 `get_db_config()`로 외부화했다.
- `INTEREST_DB_HOST`, `INTEREST_DB_PORT`, `INTEREST_DB_NAME`, `INTEREST_DB_USER`, `INTEREST_DB_PASSWORD` 환경변수 기반으로 DB 연결 정보를 구성하도록 변경했다.
- 하드코딩된 DB password 후보를 제거했다.
- schema-per-domain 전환 후에도 기존 SQL은 search_path 기반으로 동작한다는 설명을 추가했다.
- AWS Migration 준비 관점에서 단일 DB `portfolio` 구조를 기준으로 설명을 정리했다.

### Notes

- 실제 DB 접속, 백테스트 실행, 리포트 생성, DB DDL/DML, 외부 API 호출, 크롤링, 주문 실행은 수행하지 않았다.
- 실제 password, token, account, webhook URL 값은 기록하지 않는다.

## 2026-05-26

### Added

- 초기 프로젝트 문서 초안을 추가했다.
  - `AGENTS.md`
  - `README.md`
  - `docs/worklog/2026-05-26.md`

### Removed

- 명백한 로컬 캐시 산출물인 `__pycache__/` 및 내부 `*.pyc` 파일을 정리했다.

### Notes

- 문서는 현재 파일 구조와 소스를 읽기 전용으로 확인한 결과를 기준으로 작성했다.
- 실제 백테스트, research run, 리포트 생성, DB DDL/DML, 외부 API 호출, 크롤링, 주문 실행은 수행하지 않았다.
- 민감정보 값은 문서에 기록하지 않으며, 필요한 경우 `[REDACTED]`로 표기한다.
