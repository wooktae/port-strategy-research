# port_strategy_research

`port_strategy_research`는 포트폴리오 전략의 백테스트, 결과 분석, 텍스트 리포트 생성을 담당하는 Python research MS다. 공통 설정과 guard 로직은 `port_strategy_common`을 재사용하고, 시장 판단/후보 필터/사이징 로직은 `port_strategy_decision`을 재사용한다.

이 README는 현재 파일 구조와 소스를 읽기 전용으로 확인해 작성한 초기 문서 초안이다. 실제 백테스트, 리포트 생성, DB 쓰기, 외부 API 호출, 크롤링, 주문 실행은 수행하지 않았다.

## 주요 역할

- 전처리된 시장, 종목, 가격 feature를 DB에서 조회한다.
- 거래일 기준 포트폴리오 백테스트를 수행한다.
- `port_strategy_decision`의 시장 판단, 후보 필터링, 포지션 사이징 로직을 재사용한다.
- `port_strategy_common`의 config, buy guard, size haircut, sell decision 로직을 재사용한다.
- 승인된 실행 흐름에서는 backtest run 메타데이터, 일별 성과, 거래 로그를 저장한다.
- 현재 정리 기준에서는 일별 보유 포지션 snapshot을 `strategy_backtest_daily_position`에 저장하고 리포트 보유/신규 매수 조회에 사용할 수 있다.
- 저장된 backtest run을 기준으로 분석 테이블과 텍스트 리포트를 생성한다.

## 실행 주의사항

다음 파일과 함수는 명시적 승인과 DB 대상 확인 없이 실행하지 않는다.

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
- `block_watch_analysis_run.py`
- `block_watch_backtest_run.py`
- `block_exception_buy_engine_run.py`
- `block_exception_buy_backtest_run.py`

위 파일들은 table 생성, row insert/update/delete, DB commit, 로컬 report 파일 생성을 수행할 수 있다. 수동 확인 없이 passive source file처럼 실행하면 안 된다.

민감정보 값은 문서나 채팅에 기록하지 않는다. 설명이 필요하면 `[REDACTED]`로 표기한다.

## 파일 구조

```text
.
├── __init__.py
├── backtest_engine.py
├── backtest_loader.py
├── backtest_buy_logic.py
├── backtest_sell_logic.py
├── backtest_position_manager.py
├── backtest_trade_log.py
├── backtest_metrics.py
├── backtest_run_store.py
├── db_config.py
├── backtest_research_run.py
├── backtest_analysis_basic.py
├── analysis_extended.py
├── run_extended_analysis.py
├── backtest_report_run.py
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
- `port_strategy_decision.backtest_market.evaluate_market`으로 시장 판단을 수행한다.
- `port_strategy_decision.backtest_filter.filter_buy_candidates`로 매수 후보를 필터링한다.
- 신규 매수 전에 기존 포지션을 먼저 처리한다.
- 보유/매도/매수 수익률을 일별 수익률과 누적 수익률로 집계한다.
- `backtest_run_store.insert_daily_result`로 일별 backtest row를 저장한다.
- `backtest_run_store.insert_daily_positions`로 일별 보유 포지션 snapshot을 저장할 수 있다.

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
- `port_strategy_decision.backtest_sizing.allocate_positions`로 포지션을 배분한다.
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

리포트 생성은 DB 연결과 현재 작업 디렉터리의 텍스트 파일 생성을 동반한다.

## 파일 카탈로그와 설명 주석

AWS Migration 전 초기 정리 자료로 `docs/source-file-catalog.md`를 추가했다. 이 문서는 repository root 기준 파일별 역할, 주요 책임, DB 접근/파일 생성/환경변수 의존성 같은 운영 주의사항을 정리한다.

Python 파일에는 모듈 docstring을 추가해 각 파일의 역할과 실행 위험을 상단에서 확인할 수 있게 했다. 함수 docstring은 DB 저장, 리포트 생성, 분석 테이블 갱신, 핵심 백테스트 파이프라인처럼 운영상 중요한 함수에만 제한적으로 추가했다. 기능 로직 변경은 없다.

## 외부 의존성

정적 확인 기준 주요 import:

- `pandas`
- `numpy`
- `psycopg2`
- `port_strategy_common`
- `port_strategy_decision`

DB 설정은 민감정보로 취급한다. credential 값은 문서화하지 않는다.

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
