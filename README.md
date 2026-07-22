# port_strategy_research

`port_strategy_research`는 포트폴리오 전략의 백테스트, 결과 분석, 텍스트 리포트 생성을 담당하는 Python research MS다. 공통 설정, guard, sizing haircut, sell decision, metrics는 `port_strategy_common`을 재사용한다. 시장 판단/후보 필터/사이징 알고리즘은 `port_strategy_decision`의 daily decision 흐름과 동일한 `port_strategy_common` 계약을 공유하며, Research 저장소 안에서는 내부 adapter(`research_backtest_market_adapter.py`, `research_backtest_filter_adapter.py`, `research_backtest_sizing_adapter.py`)를 통해 `port_strategy_common`을 직접 호출한다. 이 adapter는 `port_strategy_decision` 런타임 import 없이 backtest 흐름이 동작하도록 분리되어 있다.

이 README는 현재 파일 구조와 소스를 읽기 전용으로 확인해 작성한 문서다. 실제 백테스트, 리포트 생성, DB 쓰기, 외부 API 호출, 크롤링, 주문 실행은 수행하지 않았다.

## 주요 역할

- 전처리된 시장, 종목, 가격 feature를 DB에서 조회한다.
- 거래일 기준 포트폴리오 백테스트를 수행한다.
- 내부 adapter를 통해 `port_strategy_common`의 market decision, buy candidate filter, sizing 로직을 호출한다. 알고리즘 정의 자체는 `port_strategy_common`에 있으며 `port_strategy_decision`의 daily 흐름과 계약을 공유한다.
- `port_strategy_common`의 config, buy guard, buy sizing haircut, sell decision, metrics 관련 로직을 재사용한다.
- 승인된 실행 흐름에서는 backtest run 메타데이터, 일별 성과, 일별 보유 포지션 snapshot, 거래 로그를 저장한다.
- 저장된 `strategy_backtest_run`, `strategy_backtest_daily`, `strategy_backtest_daily_position`, `strategy_trade_log`를 기반으로 기본/확장 분석 테이블을 생성하거나 갱신할 수 있다.
- 저장된 run_id 기준으로 summary, 일자별 매매, 거래 상세, 추천/진단 텍스트 리포트를 생성할 수 있다.

## Research 책임 경계

- Research가 담당하는 영역:
  - 전처리 feature와 가격/universe 데이터를 읽어 백테스트를 수행하는 것
  - `port_strategy_common` 알고리즘 계약을 backtest 관점에서 호출하는 것
  - backtest run/daily/position/trade 산출물과 그 위에서 만들어지는 기본/확장 분석 및 텍스트 리포트를 생성하는 것
  - AWS Paper Daily 파이프라인에서 backtest research 및 backtest report 실행 단위로 호출되는 것
- Research가 직접 책임지지 않는 영역:
  - 외부 데이터 수집(Crawler)과 raw 데이터 전처리/feature 생성(Preprocessor)
  - daily 운영 BUY signal 생성과 daily position HOLD/SELL/SKIP decision 생성(StrategyDecision)
  - execution plan 생성과 주문 후보 변환, 주문성 처리(StrategyExecution)
  - KIS 주문 제출, 주문/체결 동기화, 잔고/보유 snapshot refresh(MarketConnector)
  - View 화면 렌더링과 승인 UI(port-view)
  - Daily Batch 전체 orchestration과 Step Functions/EventBridge 세부 라인업

## 실행 주의사항

다음 파일과 함수는 명시적 승인과 DB/컨테이너 대상 확인 없이 실행하지 않는다.

- `backtest_research_run.py`
- `backtest_engine.run_backtest(...)`
- `backtest_run_store.ensure_run_tables(...)`
- `backtest_run_store.create_run(...)`
- `backtest_run_store.insert_daily_result(...)`
- `backtest_run_store.insert_daily_positions(...)`
- `backtest_run_store.finalize_run(...)`
- `backtest_trade_log.insert_trade_log(...)`
- `analysis_extended.run_analysis_extended(...)`
- `backtest_analysis_basic.run_analysis(...)`
- `run_extended_analysis.py`
- `backtest_report_run.py`
- `report_summary.py`
- `report_buy_sell.py`
- `report_trade_detail.py`
- `report_recommendation.py`
- `aws_batch_backtest_report_wrapper.py`
- `block_watch_analysis_run.py`
- `block_watch_backtest_run.py`
- `block_exception_buy_engine_run.py`
- `block_exception_buy_backtest_run.py`

위 파일들은 table 생성, row insert/update/delete, DB commit, 로컬 report 파일 생성, S3 업로드, backtest 유사 계산을 수행할 수 있다. 수동 확인 없이 passive source file처럼 실행하면 안 된다.

민감정보 값은 문서나 채팅에 기록하지 않는다. 설명이 필요하면 `[REDACTED]`, `<RESEARCH_BATCH_JOB>`, `<RESEARCH_ECS_TASK>`, `<ECR_IMAGE_URI>`, `<JOB_DEFINITION_ARN>`, `<JOB_QUEUE_ARN>`, `<TASK_DEFINITION_ARN>`, `<COMMAND_ID>`, `<DB_HOST>` 형태의 placeholder로 표기한다.

## 파일 구조

```text
.
├── __init__.py
├── Dockerfile
├── requirements.txt
├── db_config.py
├── backtest_engine.py
├── backtest_loader.py
├── backtest_buy_logic.py
├── backtest_sell_logic.py
├── backtest_position_manager.py
├── backtest_trade_log.py
├── backtest_metrics.py
├── backtest_run_store.py
├── backtest_research_run.py
├── research_backtest_market_adapter.py
├── research_backtest_filter_adapter.py
├── research_backtest_sizing_adapter.py
├── backtest_analysis_basic.py
├── analysis_extended.py
├── run_extended_analysis.py
├── backtest_report_run.py
├── aws_batch_backtest_report_wrapper.py
├── report_data_loader.py
├── report_formatter.py
├── report_summary.py
├── report_buy_sell.py
├── report_trade_detail.py
├── report_recommendation.py
├── block_watch_analysis_run.py
├── block_watch_backtest_run.py
├── block_exception_buy_engine_run.py
└── block_exception_buy_backtest_run.py
```

## 백테스트 구성요소

### Engine

`backtest_engine.py`는 백테스트의 메인 루프를 조율한다.

- 거래일, 시장 feature, 종목 feature, 다음 거래일 가격, 종목 universe를 로드한다.
- `research_backtest_market_adapter.evaluate_market`으로 시장 판단을 수행한다. 내부적으로 `port_strategy_common.common_market.common_decide_market`을 호출한다.
- `research_backtest_filter_adapter.filter_buy_candidates`로 매수 후보를 필터링한다. 내부적으로 `port_strategy_common.common_buy_filter.common_filter_buy_candidates`를 호출한다.
- 신규 매수 전에 기존 포지션을 먼저 처리한다.
- 보유/매도/매수 수익률을 일별 수익률과 누적 수익률로 집계한다.
- `backtest_run_store.insert_daily_result`로 일별 backtest row를 저장한다.
- `backtest_run_store.insert_daily_positions`로 일별 보유 포지션 snapshot을 저장할 수 있다.

### Research Backtest Adapters

`research_backtest_market_adapter.py`, `research_backtest_filter_adapter.py`, `research_backtest_sizing_adapter.py`는 `port_strategy_common`의 market/filter/sizing 계약을 backtest 흐름에 맞춰 호출하는 얇은 adapter다.

- `evaluate_market`, `filter_buy_candidates`, `allocate_positions` 세 진입점을 제공한다.
- 각각 `common_decide_market`, `common_filter_buy_candidates`, `common_allocate_positions`에 위임한다.
- `port_strategy_decision` 런타임 import 없이 Research가 backtest를 실행할 수 있도록 분리된 파일이며, 자체 DB 접근이나 외부 API 호출은 하지 않는다.
- decision reason 문자열, dataclass 필드, 공통 config key 계약은 그대로 유지한다.

### Loader

`backtest_loader.py`는 다음 DB 테이블을 읽는 SQL helper를 제공한다.

- `pre_total_market_daily_feature`
- `pre_total_stock_daily_feature`
- `interest_price_raw`
- `stock_universe`

### Buy Logic

`backtest_buy_logic.py`는 신규 진입 로직을 담당한다.

- 사후 분석용 entry metadata를 만든다.
- local decision/stock row를 common model로 변환한다.
- `research_backtest_sizing_adapter.allocate_positions`로 포지션을 배분한다. 내부적으로 `port_strategy_common.common_buy_sizing.common_allocate_positions`를 호출한다.
- `port_strategy_common.common_buy_guard.common_decide_buy_guard`를 적용한다.
- `port_strategy_common.common_buy_sizing.common_apply_backtest_buy_size_haircut`을 적용한다.
- 당일 장중 손절 조건에 걸린 거래는 `insert_trade_log`로 저장할 수 있다.

### Sell Logic / Position Manager

`backtest_sell_logic.py`는 `port_strategy_common.common_sell_decision.common_evaluate_backtest_sell` 호출을 감싼 wrapper다.

`backtest_position_manager.py`는 기존 보유 종목을 처리한다.

- 당일 수익률을 계산한다.
- 기존 포지션 장중 손절 조건을 적용한다.
- 일반 매도 판단을 수행한다.
- 청산된 거래는 `insert_trade_log`로 저장한다.
- 살아남은 포지션은 다음 일자로 이월한다.

### Trade Log

`backtest_trade_log.py`는 완료된 거래를 `strategy_trade_log`에 insert한다. 저장 항목에는 run id, 전략 메타데이터, 종목 정보, 매수/매도일, 보유 기간, 가격, buy/sell metadata, config snapshot이 포함된다.

### Metrics

`backtest_metrics.py`는 DataFrame 기반 계산을 제공한다.

- 최대 낙폭(MDD)
- Sharpe ratio

`RISK_FREE_RATE`, `TRADING_DAYS_PER_YEAR`는 `port_strategy_common.config`에서 가져온다.

## 분석 및 리포트

`backtest_analysis_basic.py`는 기본 집계 분석 row를 저장한다.

`analysis_extended.py`는 run_id 기준으로 여러 분석 테이블을 다시 만든다. 기존 row를 삭제한 뒤 재계산 row를 insert하는 DB write 경로다.

`report_data_loader.py`는 저장된 backtest run, daily row, 일별 포지션 snapshot, trade log, 분석 테이블, threshold snapshot을 읽는다.

`report_formatter.py`는 label, percentage, run input, 매수 사유, 매도 사유를 포맷팅한다.

리포트 생성 파일:

- `report_summary.py`: 요약 리포트
- `report_buy_sell.py`: 일자별 매매 리포트
- `report_trade_detail.py`: 거래 상세 리포트
- `report_recommendation.py`: 추천/진단 리포트
- `backtest_report_run.py`: 최신 run id 기준 전체 리포트 생성 orchestration

리포트 생성은 DB 연결과 로컬 텍스트 파일 생성을 동반한다. 출력 디렉터리는 기본 현재 작업 디렉터리이며, AWS Batch 실행에서는 wrapper가 `REPORT_OUTPUT_DIR=/tmp/portfolio-reports`로 지정한다.

## block/watch/exception-buy 연구 계열

`block_watch_analysis_run.py`, `block_watch_backtest_run.py`, `block_exception_buy_engine_run.py`, `block_exception_buy_backtest_run.py`는 block/watch/예외 매수 관점의 연구 실행 후보다.

- 실행 시 DB 연결, backtest 유사 계산, watch 후보 수익률 update가 발생할 수 있다.
- 이 파일들은 daily 운영 파이프라인과 연결되지 않은 연구/보류 계열이며, Research 문서에서만 범위와 위험을 요약한다.
- 문서 작업 중 실행하지 않고, 삭제하지 않고 연구 계열로 보존한다.

## AWS Paper Daily 운영 관점

Research는 AWS Paper 운영에서 백테스트 실행 및 리포트 생성 단위로 호출된다. Scheduler와 Step Functions는 실행 orchestration을 담당하고, Research는 backtest, analysis, report 생성 자체만 책임진다.

- Daily Step 4 Backtest Research
  - `backtest_research_run.py`가 DB feature를 읽고 backtest run metadata, daily result, 일별 포지션 snapshot, trade log, 기본/확장 분석 산출물을 생성할 수 있다.
  - 내부적으로 `backtest_engine.py`, `backtest_loader.py`, `backtest_buy_logic.py`, `backtest_sell_logic.py`, `backtest_position_manager.py`, `backtest_trade_log.py`, `backtest_metrics.py`, `backtest_run_store.py`, adapter 3종을 호출한다.
  - DB DDL/DML, commit이 발생할 수 있는 실행 위험 흐름이므로 문서 작업 중에는 실행하지 않는다.
- Daily Step 5 Backtest Report
  - `backtest_report_run.py`가 최신 또는 지정 run_id 기준으로 report 생성을 orchestration한다.
  - `report_data_loader.py`, `report_formatter.py`, `report_summary.py`, `report_buy_sell.py`, `report_trade_detail.py`, `report_recommendation.py`가 순서대로 호출된다.
  - DB read와 로컬 txt report 파일 생성이 동반된다.
- 실행 orchestration 책임 경계
  - Scheduler(EventBridge Scheduler)와 Step Functions는 Research entrypoint를 실행 대상으로 호출하는 orchestrator 역할이며, Research가 아니다.
  - Preprocessor는 Research 입력 feature(`pre_total_market_daily_feature`, `pre_total_stock_daily_feature`)를 생성한다.
  - StrategyDecision은 daily 운영 판단(BUY signal, HOLD/SELL/SKIP)과 backtest 흐름이 공유하는 판단 계약의 daily 소비자다.
  - StrategyExecution은 daily 운영 산출물을 실행 계획과 주문 후보로 변환하는 후속 책임이다.
  - MarketConnector는 실제 broker API 호출과 주문/체결/잔고 책임이다.
  - port-view는 실행 상태 조회 또는 trigger UI일 뿐 Research 내부 실행 책임이 아니다.

실제 compute environment 이름, AWS Batch job queue/job definition ARN, ECS task definition ARN, ECR image URI, S3 bucket/path, command id, 실행 시간, 일회성 실행 로그는 문서에 원문 기록하지 않는다. 필요 시 `<RESEARCH_BATCH_JOB>`, `<JOB_QUEUE_ARN>`, `<JOB_DEFINITION_ARN>`, `<TASK_DEFINITION_ARN>`, `<ECR_IMAGE_URI>`, `<COMMAND_ID>` 형태의 placeholder만 사용한다.

## 컨테이너 실행 구조

Research는 컨테이너 실행 대상으로도 사용될 수 있다.

- `Dockerfile`
  - Base image는 `python:3.13-slim`이다.
  - `port_strategy_common/`과 `port_strategy_research/`를 함께 copy하고 `requirements.txt`로 의존성을 설치한다.
  - 기본 `CMD`는 `python -m py_compile port_strategy_research/backtest_research_run.py`로, 컨테이너 자체 실행 시에는 compile 확인만 수행한다.
  - 실제 실행 command는 AWS Batch job definition, ECS task definition, 또는 로컬 override에서 지정한다.
- `requirements.txt`
  - Research 실행에 필요한 pinned 의존성을 관리한다.
  - 개별 pinned 버전 값은 파일 자체에서 관리하며 문서에는 반복 기록하지 않는다.
- `aws_batch_backtest_report_wrapper.py`
  - AWS Batch용 BACKTEST_REPORT 실행 wrapper다.
  - `RESEARCH_APP_SECRET_JSON` 환경변수 값을 `INTEREST_DB_HOST/PORT/NAME/USER/PASSWORD`로 매핑한다. secret 값 자체는 로그나 문서에 남기지 않는다.
  - `REPORT_OUTPUT_DIR` 기본값을 `/tmp/portfolio-reports`로 지정한다.
  - `runpy.run_module`로 `port_strategy_research.backtest_report_run`을 실행한다.
  - `REPORT_S3_BUCKET`이 설정되어 있으면 `<REPORT_S3_PREFIX>/YYYYMMDD/<AWS_BATCH_JOB_ID>/<파일명>.txt` 경로로 생성 report txt 파일을 S3에 업로드한다.
  - 실제 secret 이름, bucket 이름, prefix, job id 원문은 문서에 기록하지 않는다.

## 파일 카탈로그와 설명 주석

AWS Migration 전 초기 정리 자료로 `docs/source-file-catalog.md`를 추가했다. 이 문서는 repository root 기준 파일별 역할, 주요 책임, DB 접근/파일 생성/환경변수 의존성 같은 운영 주의사항을 정리한다.

Python 파일에는 모듈 docstring을 추가해 각 파일의 역할과 실행 위험을 상단에서 확인할 수 있게 했다. 함수 docstring은 DB 저장, 리포트 생성, 분석 테이블 갱신, 핵심 백테스트 파이프라인처럼 운영상 중요한 함수에만 제한적으로 추가했다. 기능 로직 변경은 없다.

## 외부 의존성

정적 확인 기준 주요 import:

- `pandas`
- `numpy`
- `psycopg2` (`requirements.txt`는 `psycopg2-binary`로 지정)
- `boto3` (AWS Batch wrapper의 S3 업로드 경로에서만 사용)
- `port_strategy_common`

`port_strategy_decision`은 런타임 import 대상이 아니다. Research는 내부 adapter를 통해 `port_strategy_common`을 직접 호출하며, `port_strategy_decision`은 daily decision 흐름의 소비자로서 동일한 `port_strategy_common` 계약을 공유하는 관계다.

DB 설정, secret 값, S3 bucket 이름, image URI, ARN 종류는 민감정보로 취급한다. credential 값은 문서화하지 않는다.

## DB 접속 환경변수

DB 접속 설정은 `db_config.py`의 `get_db_config()`에서 `INTEREST_DB_*` 환경변수로 읽는다. 현재 로컬 PostgreSQL 기본 DB name은 `portfolio`다.

| 환경변수 | 기본값 | 설명 |
| --- | --- | --- |
| `INTEREST_DB_HOST` | `localhost` | PostgreSQL host |
| `INTEREST_DB_PORT` | `5433` | PostgreSQL port |
| `INTEREST_DB_NAME` | `portfolio` | DB name |
| `INTEREST_DB_USER` | `postgres` | DB user |
| `INTEREST_DB_PASSWORD` | 없음 | DB password. 비어 있으면 실행 시 `RuntimeError`가 발생한다. |

예시:

```powershell
$env:INTEREST_DB_HOST = "localhost"
$env:INTEREST_DB_PORT = "5433"
$env:INTEREST_DB_NAME = "portfolio"
$env:INTEREST_DB_USER = "postgres"
$env:INTEREST_DB_PASSWORD = "<DB_PASSWORD>"
```

실제 password 값은 소스, 문서, 채팅에 기록하지 않는다.

## DB schema 구조

AWS Migration 준비 관점에서 PostgreSQL은 단일 DB `portfolio` 안에 domain별 schema를 나누는 schema-per-domain 구조를 사용한다.

- `reference`
- `interest`
- `preprocessor`
- `research`
- `decision`
- `execution`
- `connector`
- `ops`
- `legacy`
- `public`

이 모듈의 DB connection search_path는 다음 순서로 적용한다.

```sql
research, preprocessor, interest, reference, legacy, public
```

schema-per-domain 전환 후에도 기존 SQL은 schema-qualified table name으로 모두 바꾸는 방식이 아니라 위 `search_path`를 기준으로 동작한다. 예를 들어 backtest 입력 feature와 research 산출 테이블은 동일한 `portfolio` DB 안에서 domain schema 우선순위에 따라 해석된다.

DB name 설정은 `INTEREST_DB_NAME=portfolio`를 기본으로 정리한다. 다른 모듈에서 `PORTFOLIO_DB_NAME` 계열 환경변수를 사용하더라도 기본 DB name은 동일하게 `portfolio`로 맞춘다.

민감정보는 환경변수 또는 로컬 설정으로 관리한다. 문서에는 실제 password, token, account, webhook URL 값을 기록하지 않는다.

## 운영 가이드

문서화나 리뷰 목적의 기본 확인은 정적 검사 위주로 수행한다.

```powershell
rg --files
rg "pattern" -n
git status --short
git diff --stat
```

DB row 저장, 리포트 생성, 백테스트 실행 가능성이 있는 작업 전에는 다음을 확인한다.

- 대상 DB와 실행 환경
- run id 또는 날짜 범위
- 쓰기 대상 table/file
- 생성된 report/output 파일 보존 여부
