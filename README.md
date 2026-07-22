# port_strategy_research

`port_strategy_research`는 전처리 feature와 가격·universe 데이터를 읽어 포트폴리오 백테스트를 수행하고,
저장된 결과를 분석해 텍스트 리포트를 생성하는 Research 마이크로서비스다.

Research는 내부 adapter를 통해 `port_strategy_common`의 market, filter, sizing, guard와 sell 계약을 직접 사용한다.
`port_strategy_decision`을 런타임에 import하지 않으며, 두 서비스는 동일한 Common 계약을 사용하는 별도 소비자다.

이 문서는 현재 저장소의 파일 구조, import, entrypoint와 기존 운영 문서를 기준으로 작성했다.
문서 정리 과정에서는 실제 Backtest, Analysis, Report, DB 쓰기, AWS, S3와 주문 실행을 수행하지 않았다.

## 1. 서비스 요약

| 항목 | 값 |
|---|---|
| 서비스 | `port_strategy_research` |
| 계층 | Research |
| 주요 입력 | Market·Stock Feature, Price Raw, Stock Universe와 Config |
| 핵심 실행 | Backtest Research |
| 후속 처리 | Basic·Extended Analysis와 Text Report |
| 주요 저장 | Run, Daily, Daily Position, Trade Log와 Analysis |
| 공통 로직 | `port_strategy_common` |
| 운영 진입점 | `backtest_research_run.py`, `backtest_report_run.py` |
| AWS 위치 | Paper Daily Step 4, Step 5 |
| 상세 파일 문서 | `docs/source-file-catalog.md` |

## 2. 책임 경계

Research는 과거 구간을 시뮬레이션하고 그 결과를 분석·표현한다.
원천 데이터 수집, Daily 운영 판단과 실제 주문은 다른 계층의 책임이다.

### 2.1 Research가 담당하는 범위

| 영역 | 책임 |
|---|---|
| Backtest | 거래일 단위 포트폴리오 시뮬레이션 |
| Market | Common Market 판단을 Research adapter로 호출 |
| Buy Filter | Common Buy Candidate Filter 호출 |
| Sizing | 후보별 Position Allocation 계산 |
| Buy·Sell | Guard, Haircut과 Common Sell 판단 적용 |
| Position | 보유, 청산과 다음 거래일 이월 처리 |
| Persistence | Run, Daily, Daily Position과 Trade Log 저장 |
| Analysis | Basic·Extended Analysis 생성 또는 갱신 |
| Report | Summary, Buy·Sell, Trade Detail과 Recommendation 생성 |
| Research 후보 | Block Watch와 Exception Buy 시나리오 연구 |

### 2.2 다른 계층이 담당하는 범위

| 영역 | 담당 계층 |
|---|---|
| 외부 데이터 수집 | Crawler |
| Raw 전처리와 Total Feature 생성 | Preprocessor |
| Daily BUY와 HOLD·SELL·SKIP 판단 | StrategyDecision |
| Execution Plan과 주문 요청 구성 | StrategyExecution |
| Broker 주문·체결·잔고·보유 동기화 | MarketConnector |
| 상태 조회와 승인 UI | View |
| 전체 Batch orchestration | Scheduler와 Step Functions |
| Image build, ECR push와 인프라 등록 | 배포 파이프라인 |

Research 결과는 연구·검증 산출물이다.
Daily Signal, Execution Plan 또는 실제 주문으로 표현하지 않는다.

## 3. 전체 실행 흐름

```text
Preprocessor Feature + Price + Universe + Config
  → Backtest Research
  → Run · Daily · Daily Position · Trade Log
  → Basic / Extended Analysis
  → Summary / Buy·Sell / Trade Detail / Recommendation Report
  → 선택적 S3 업로드
```

| 단계 | 주요 진입점 |
|---|---|
| Backtest | `backtest_research_run.py` |
| Basic Analysis | `backtest_analysis_basic.py` |
| Extended Analysis | `run_extended_analysis.py` |
| Report | `backtest_report_run.py` |
| AWS Batch Report | `aws_batch_backtest_report_wrapper.py` |

## 4. Backtest Research

### 4.1 실행 흐름

```text
Run 생성과 입력 Snapshot
  → 거래일·Feature·가격·Universe 조회
  → Market Decision
  → 기존 Position 처리
  → Buy Candidate Filter
  → Guard와 Sizing
  → 신규 Position 생성
  → Daily Result와 Daily Position 저장
  → Trade Log 저장
  → Metrics와 Run 상태 확정
```

| 단계 | 주요 파일 |
|---|---|
| 전체 orchestration | `backtest_research_run.py` |
| 거래일 메인 루프 | `backtest_engine.py` |
| 입력 조회 | `backtest_loader.py` |
| Market adapter | `research_backtest_market_adapter.py` |
| Filter adapter | `research_backtest_filter_adapter.py` |
| Sizing adapter | `research_backtest_sizing_adapter.py` |
| 신규 진입 | `backtest_buy_logic.py` |
| Sell 판단 | `backtest_sell_logic.py` |
| Position 처리 | `backtest_position_manager.py` |
| Trade 저장 | `backtest_trade_log.py` |
| Run·Daily 저장 | `backtest_run_store.py` |
| 성과 계산 | `backtest_metrics.py` |

### 4.2 Engine

`backtest_engine.py`는 거래일 단위 메인 루프를 조율한다.

| 항목 | 역할 |
|---|---|
| 입력 | 거래일, Market·Stock Feature, 가격과 Universe |
| Market | Research Market Adapter 호출 |
| Position | 신규 매수보다 기존 Position을 먼저 처리 |
| Buy | Filter, Guard, Haircut과 Sizing 적용 |
| 성과 | 일별 수익률과 누적 성과 계산 |
| 저장 | Daily Result와 Daily Position Snapshot |
| 거래 | 청산 또는 당일 손절 거래를 Trade Log로 전달 |

가격 기준, 거래일 정렬, 기존 Position 처리 순서와 신규 매수 시점은 백테스트 결과를 바꾸는 핵심 계약이다.

### 4.3 Loader

`backtest_loader.py`는 Backtest 입력을 읽는 SQL helper다.

| 입력 | 사용 목적 |
|---|---|
| `pre_total_market_daily_feature` | Market 판단 |
| `pre_total_stock_daily_feature` | Filter, Sizing과 Sell 판단 |
| `interest_price_raw` | 가격과 수익률 계산 |
| `stock_universe` | Backtest 대상 Universe |

거래일, Feature 기준일과 다음 거래일 가격을 구분해야 한다.
미래 가격이나 미래 Feature가 현재 판단에 포함되면 Look-ahead Bias가 발생한다.

### 4.4 Research Adapter

Research 내부 adapter는 `port_strategy_common` 계약을 Backtest 흐름에 연결한다.

| 파일 | Common 호출 |
|---|---|
| `research_backtest_market_adapter.py` | `common_decide_market` |
| `research_backtest_filter_adapter.py` | `common_filter_buy_candidates` |
| `research_backtest_sizing_adapter.py` | `common_allocate_positions` |

Adapter는 자체 DB 접근이나 외부 API 호출을 담당하지 않는다.
Common 결과를 Research row와 객체 형식으로 변환하는 경계다.

### 4.5 Buy Logic

`backtest_buy_logic.py`는 신규 Position 진입을 담당한다.

| 항목 | 처리 |
|---|---|
| 후보 | Filter 통과 종목 |
| Allocation | Research Sizing Adapter |
| Guard | Common Buy Guard |
| Haircut | Common Backtest Buy Size Haircut |
| Metadata | Entry Reason과 사후 분석용 정보 |
| 당일 Stop | 조건에 따라 Trade Log 생성 가능 |

Available Cash, Exposure, Max Positions, 최소 수량과 반올림 기준은 결과에 직접 영향을 준다.

### 4.6 Sell Logic과 Position Manager

`backtest_sell_logic.py`는 Common Sell 판단을 감싼 wrapper다.

`backtest_position_manager.py`는 기존 Position을 처리한다.

| 처리 | 의미 |
|---|---|
| 일별 수익률 | 보유 Position의 당일 변화 계산 |
| 장중 Stop | 기존 Position의 긴급 청산 조건 |
| 일반 Sell | Common Sell Decision |
| 청산 | Trade Log 생성 |
| 이월 | 살아남은 Position을 다음 거래일로 전달 |

Stop, 보유 기간과 Sell Reason 우선순위는 Daily Decision과 공유하는 Common 계약에 영향을 받는다.

### 4.7 Metrics

`backtest_metrics.py`는 DataFrame 기반 성과 계산을 제공한다.

| 지표 | 의미 |
|---|---|
| MDD | 최대 낙폭 |
| Sharpe Ratio | 위험 대비 수익률 |

Risk-free Rate와 연간 거래일 수는 `port_strategy_common.config` 계약을 사용한다.
빈 데이터, 0분모와 표본 수 부족 처리는 실제 코드 기준으로 확인해야 한다.

## 5. 입력 데이터

| 입력 | 역할 |
|---|---|
| Market Total Feature | 시장 상태와 허용 노출 판단 |
| Stock Total Feature | 종목 Filter, Sizing과 Sell 판단 |
| Price Raw | 가격, 수익률과 체결 가정 |
| Stock Universe | 대상 종목과 활성 조건 |
| Config Snapshot | 실행 당시 전략 기준 재현 |
| Run Input | 기간, 초기 자산과 실행 옵션 |

입력 데이터에서는 아래를 구분한다.

| 구분 | 확인 내용 |
|---|---|
| Trade Date | 거래일 순서와 기준 |
| Feature Date | Market·Stock Feature 기준일 |
| Price Date | 진입·청산에 사용하는 가격 일자 |
| Missing | 미수집 또는 결합 실패 |
| Zero | 실제 값이 0인 상태 |
| Duplicate | 동일 Ticker·Date 중복 row |
| Universe | 활성 종목과 제외 조건 |

## 6. 출력 데이터

### 6.1 Backtest 저장

| 출력 | 의미 |
|---|---|
| `strategy_backtest_run` | Run 메타데이터, 입력과 상태 |
| `strategy_backtest_daily` | 거래일별 포트폴리오 성과 |
| `strategy_backtest_daily_position` | 거래일별 보유 Position Snapshot |
| `strategy_trade_log` | 완료 거래 상세와 Buy·Sell Metadata |

### 6.2 Analysis 저장

| 출력 | 의미 |
|---|---|
| Basic Analysis | Run의 기본 집계 결과 |
| Extended Analysis | Threshold, Bucket과 진단 목적 확장 결과 |
| `strategy_backtest_*_analysis` | Run ID 기준 분석 테이블 계열 |

### 6.3 Report 파일

| 리포트 | 의미 |
|---|---|
| Summary | Run 성과와 주요 지표 요약 |
| Buy·Sell | 일자별 매수·매도 내역 |
| Trade Detail | 거래별 상세 정보 |
| Recommendation | 연구 관점 추천·진단 |

Recommendation은 연구 진단이다.
실제 투자 권고, 주문 지시 또는 미래 성과 보장으로 해석하지 않는다.

## 7. 저장과 재실행

| 주의사항 | 확인 내용 |
|---|---|
| Run 생성 | 동일 입력이 신규 Run인지 기존 Run 갱신인지 |
| Daily 저장 | 거래일별 Unique Key와 Upsert |
| Position 저장 | Run·Trade Date·Ticker 기준 |
| Trade Log | 완료 거래와 Metadata 계약 |
| 상태 전환 | Started, Completed와 Failed 처리 |
| Transaction | Run, Daily, Position과 Trade 저장 경계 |
| Partial Success | 일부 저장 후 Run만 성공 처리되는지 |
| Re-run | 기존 Analysis·Report와의 연결 |
| Snapshot | Config와 Input 재현 가능성 |

실제 Unique Key와 Conflict Target은 SQL 또는 DDL을 직접 확인해야 한다.
문서만으로 추정하지 않는다.

## 8. Analysis

### 8.1 Basic Analysis

`backtest_analysis_basic.py`는 저장된 Run 결과를 기본 집계 형태로 변환해 저장한다.
표준 Backtest Run 진입점에서는 이 Basic Analysis 호출이 주석 처리되어 자동 실행되지 않는다.

| 항목 | 의미 |
|---|---|
| 기준 | Run ID |
| 입력 | Run, Daily, Position과 Trade Log |
| 출력 | 기본 Analysis Row |
| 위험 | DB Insert 또는 Upsert 가능 |

### 8.2 Extended Analysis

`analysis_extended.py`는 Run ID 기준 확장 분석을 재생성한다.
표준 Backtest Run 진입점(`backtest_research_run.py`)이 Extended Analysis를 자동 호출한다.

| 항목 | 의미 |
|---|---|
| 실행 진입점 | `run_extended_analysis.py` |
| 입력 | 저장된 Backtest 결과 |
| 처리 | 기존 Run 대상 row 삭제 후 재계산 가능 |
| 출력 | 여러 Extended Analysis Table |
| 위험 | Delete 후 Insert와 Commit |

12개 분석 Table을 Delete한 뒤 재계산하고 마지막에 한 번 commit한다.
중간 실패 시 Delete와 Insert가 함께 rollback되어 부분 결과만 남지 않는다.

### 8.3 분석 해석

| 상태 | 구분 |
|---|---|
| 거래 0건 | 정상 Run이지만 거래가 없는 결과일 수 있음 |
| 입력 누락 | 분석에 필요한 저장 데이터가 없는 상태 |
| 빈 DataFrame | 계산 대상이 없는 상태 |
| 0분모 | 비율 계산 불가 |
| `NULL` | 미산출 또는 누락 |
| 무한대 | 분모 또는 수치 안정성 문제 가능 |

분석 결과를 실제 운용 성과와 동일하게 표현하지 않는다.

## 9. Report

### 9.1 Report 구성

| 파일 | 역할 |
|---|---|
| `report_data_loader.py` | Run·Daily·Position·Trade·Analysis 조회 |
| `report_formatter.py` | Label, Percentage와 Reason 포맷 |
| `report_summary.py` | Summary 생성 |
| `report_buy_sell.py` | 일자별 Buy·Sell 생성 |
| `report_trade_detail.py` | 거래 상세 생성 |
| `report_recommendation.py` | 추천·진단 생성 |
| `backtest_report_run.py` | 전체 Report orchestration |

Report는 저장된 Backtest 결과를 읽어 Text File을 생성하는 표현 계층이다.

### 9.2 Run 선택

| 방식 | 의미 |
|---|---|
| 최신 Run 자동 선택 | `get_latest_run_id`가 `started_at DESC` 최신 Run 선택 |
| 지정 Run ID | 각 report 함수는 run_id 인자를 받지만 진입점 CLI 옵션은 없음 |
| Run 없음 | Report 생성 불가 |

최신 Run은 완료 여부와 무관하게 `started_at` 기준으로 선택한다.

### 9.3 출력 파일

| 항목 | 현재 문서 기준 |
|---|---|
| 기본 출력 | 현재 작업 디렉터리 |
| AWS Batch 출력 | `/tmp/portfolio-reports` |
| 형식 | Text File |
| 덮어쓰기 | 파일명 생성 규칙 확인 필요 |
| S3 | Wrapper 환경변수가 설정된 경우 선택적 업로드 |

Report 생성 성공과 S3 업로드 성공은 별도 상태다.

## 10. Block·Watch·Exception Buy 연구

| 파일 | 현재 분류 |
|---|---|
| `block_watch_analysis_run.py` | Watch Candidate 분석 |
| `block_watch_backtest_run.py` | BLOCK Watch Backtest |
| `block_exception_buy_engine_run.py` | Exception Buy Engine 연구 |
| `block_exception_buy_backtest_run.py` | Exception Buy Backtest |

이 계열은 Daily 운영 파이프라인의 정식 단계가 아닌 연구·보류 후보로 관리한다.

실행 시 발생 가능한 영향:

| 영향 | 예시 |
|---|---|
| DB Read | Candidate와 Feature 조회 |
| DB Write | Watch 수익률 Update |
| Simulation | Backtest 유사 계산 |
| Output | 연구 결과 출력 또는 파일 생성 |

사용 흔적과 운영 연결이 확인되지 않았다는 이유만으로 삭제하지 않는다.

## 11. `port_strategy_common` 관계

Research는 핵심 판단 로직을 Common에서 재사용한다.

| 영역 | Common 계약 |
|---|---|
| Config | Strategy, Engine과 판단 설정 |
| Market | Market Context와 Decision |
| Filter | Buy Candidate Filter |
| Sizing | Position Allocation |
| Guard | Buy Guard |
| Haircut | Backtest Buy Size Haircut |
| Sell | Backtest Sell Decision |
| Metrics | Risk-free Rate와 Trading Days |

Public 함수명, dataclass 필드, enum, config key와 reason 문자열은 다른 서비스와 연결될 수 있다.

### StrategyDecision과의 관계

| 항목 | 관계 |
|---|---|
| 런타임 Import | 없음 |
| 공유 대상 | `port_strategy_common` 계약 |
| Research Adapter | Research 저장소 내부 |
| Decision Adapter | StrategyDecision 저장소 내부 |
| Daily 운영 판단 | StrategyDecision 책임 |
| Backtest 판단 | Research 책임 |

Research 변경만으로 Common 또는 Decision 계약을 임의 변경하지 않는다.

## 12. AWS Paper Daily 위치

Research는 AWS Paper Daily에서 Backtest와 Report 실행 단위로 호출된다.

| Daily 단계 | Research 역할 |
|---|---|
| Step 4 · Backtest Research | Feature를 읽어 Backtest와 분석 결과 생성 |
| Step 5 · Backtest Report | 저장된 Run 기준 Text Report 생성 |

### 12.1 Step 4

| 항목 | 값 |
|---|---|
| 진입점 | `backtest_research_run.py` |
| 입력 | Feature, Price, Universe, Config와 기간 |
| 출력 | Run, Daily, Position, Trade와 Analysis |
| DB 영향 | DDL·DML과 Commit 가능 |
| 직접 하지 않는 일 | Daily Signal, Execution Plan과 Broker 주문 |

### 12.2 Step 5

| 항목 | 값 |
|---|---|
| 진입점 | `backtest_report_run.py` |
| 입력 | 최신 또는 지정 Run ID |
| 출력 | Summary, Buy·Sell, Trade Detail과 Recommendation |
| 파일 영향 | Local Text File 생성 |
| 선택적 영향 | AWS Batch Wrapper를 통한 S3 업로드 |

Scheduler와 Step Functions는 실행 orchestration을 담당한다.
Research 저장소의 entrypoint 존재는 현재 AWS 실행 상태나 배포 완료 증거가 아니다.

## 13. 컨테이너와 AWS Batch

### 13.1 Dockerfile

| 항목 | 현재 문서 기준 |
|---|---|
| Base Image | `python:3.13-slim` |
| 포함 대상 | `port_strategy_common`, `port_strategy_research` |
| Dependency | `requirements.txt` |
| 기본 CMD | `backtest_research_run.py` Compile 확인 |
| 실제 Research 실행 | 외부 Command Override |
| 배포 책임 | 별도 배포 파이프라인 |

기본 CMD는 실제 Backtest 실행이 아니라 Compile 확인이다.

### 13.2 AWS Batch Report Wrapper

`aws_batch_backtest_report_wrapper.py`는 AWS Batch용 Report Wrapper다.

| 항목 | 역할 |
|---|---|
| `RESEARCH_APP_SECRET_JSON` | DB Secret JSON 입력 |
| `INTEREST_DB_*` | Research DB 환경변수로 매핑 |
| `REPORT_OUTPUT_DIR` | Report 출력 경로 |
| `runpy.run_module` | Report Entrypoint 실행 |
| `REPORT_S3_BUCKET` | S3 업로드 활성 조건 |
| `REPORT_S3_PREFIX` | S3 Key Prefix |
| `AWS_BATCH_JOB_ID` | Job별 출력 경로 구분 |

Secret 값, 실제 Bucket, Prefix, Job ID와 ARN은 문서에 기록하지 않는다.

## 14. 실행 방법

내부 import는 `port_strategy_research` package 경로를 기준으로 한다.
실행이 필요한 경우 파일 경로 직접 실행보다 `python -m` 형식을 사용한다.

아래 명령은 형식 설명용 예시다.
실제 DB 쓰기, 파일 생성과 S3 업로드가 발생할 수 있으므로 문서 작업 중에는 실행하지 않는다.

```powershell
python -m port_strategy_research.backtest_research_run

python -m port_strategy_research.run_extended_analysis

python -m port_strategy_research.backtest_report_run

python -m port_strategy_research.aws_batch_backtest_report_wrapper
```

실제 CLI Option과 필수 환경변수는 각 Entrypoint 소스를 확인해야 한다.

| 진입점 | 실행 영향 |
|---|---|
| `backtest_research_run` | Backtest Run과 결과 저장 가능 |
| `run_extended_analysis` | Analysis Table Delete·Insert 가능 |
| `backtest_report_run` | DB Read와 Local Report 생성 |
| AWS Batch Wrapper | Secret 매핑, Report 생성과 S3 업로드 가능 |
| Block·Watch Entrypoint | DB Update 또는 Simulation 가능 |

## 15. DB 설정

DB 연결은 `db_config.py`의 `get_db_config()`를 사용한다.

### 15.1 환경변수

| 환경변수 | 현재 문서 기준 |
|---|---|
| `INTEREST_DB_HOST` | 기본 `localhost` |
| `INTEREST_DB_PORT` | 기본 `5433` |
| `INTEREST_DB_NAME` | 기본 `portfolio` |
| `INTEREST_DB_USER` | 기본 `postgres` |
| `INTEREST_DB_PASSWORD` | 기본값 없음, 누락 시 실행 오류 |

```powershell
$env:INTEREST_DB_HOST="localhost"
$env:INTEREST_DB_PORT="5433"
$env:INTEREST_DB_NAME="portfolio"
$env:INTEREST_DB_USER="postgres"
$env:INTEREST_DB_PASSWORD="[REDACTED]"
```

예시 값은 로컬 문서 기준이며 실제 운영 접속정보가 아니다.

### 15.2 Search Path

현재 문서 기준 Search Path는 다음 순서다.

```text
research, preprocessor, interest, reference, legacy, public
```

| Schema | 주요 역할 |
|---|---|
| `research` | Backtest, Analysis와 Research 산출물 |
| `preprocessor` | Total Feature |
| `interest` | Price Raw |
| `reference` | Stock Universe |
| `legacy`, `public` | 기존 Unqualified SQL 호환 |

Search Path 순서 변경은 Unqualified SQL이 참조하는 Table을 바꿀 수 있다.

## 16. 외부 의존성

| 의존성 | 용도 |
|---|---|
| Python | Runtime |
| PostgreSQL | Feature 조회와 Research 결과 저장 |
| `pandas` | Table과 성과 계산 |
| `numpy` | 수치 계산 |
| `psycopg2` | PostgreSQL 연결 |
| `psycopg2-binary` | 설치 Package |
| `boto3` | AWS Batch Wrapper의 S3 업로드 |
| `port_strategy_common` | 공통 판단과 설정 |

Pinned Version은 `requirements.txt`에서 관리한다.
README에 버전 값을 중복 기록하지 않는다.

## 17. 상태와 계산 주의사항

| 주의사항 | 확인 내용 |
|---|---|
| Look-ahead | 미래 Feature·Price 사용 금지 |
| Trade Order | 기존 Position 처리와 신규 Buy 순서 |
| Missing | 누락값과 실제 0 구분 |
| Duplicate | Ticker·Date Join Cardinality |
| Cash | Available Cash와 Position Allocation |
| Cost | Fee, Tax와 Slippage 구현 여부 |
| Stop | 당일 Stop과 일반 Sell 우선순위 |
| Run Status | Partial Save 후 Completed 처리 여부 |
| Analysis | Delete 후 Insert 실패 가능성 |
| Report | 최신 Run 선택과 파일 덮어쓰기 |
| S3 | 일부 업로드 실패와 전체 성공 구분 |
| Reproducibility | Config·Input Snapshot 보존 |

현재 구현이 모든 실패와 수치 경계를 자동 처리한다고 README만으로 단정하지 않는다.
코드 변경이나 장애 분석에서는 EntryPoint, Store와 Transaction을 직접 확인해야 한다.

## 18. 문서 구조

| 문서 | 역할 |
|---|---|
| `AGENTS.md` | Kiro 작업 범위, 안전, 데이터 계약과 검증 규칙 |
| `README.md` | 현재 Research 구조, 실행·설정과 운영 위치 |
| `CHANGELOG.md` | 주요 변경 이력과 당시 사실 |
| `docs/source-file-catalog.md` | 파일 책임, 입출력과 변경 영향 |

파일 책임, Entrypoint, DB 접근, Analysis, Report, AWS Wrapper와 Dependency가 바뀌면
README와 `docs/source-file-catalog.md`를 함께 확인한다.

날짜별 `docs/worklog/*.md`는 새로 만들지 않는다.
과거 생성 사실은 CHANGELOG의 당시 이력으로만 보존한다.

## 19. 안전한 검증 범위

문서만 수정한 경우에는 변경 파일과 Diff 범위만 확인한다.

```powershell
git status --short
git diff --stat
git diff --check
```

코드 수정 시에도 실제 Backtest, Analysis, Report, DB 쓰기, AWS, S3와 주문 실행이 없는 검증을 우선한다.

| 검증 | 안전한 방식 |
|---|---|
| Adapter | 단위 입력·출력 비교 |
| Metrics | 작은 DataFrame Fixture |
| Loader | DB Mock |
| Run Store | Connection·Cursor Mock |
| Report | 임시 디렉터리 |
| AWS Wrapper | 환경변수와 boto3 Mock |

운영 실행이 필요한 검증은 자동 수행하지 않고 남은 검증으로 보고한다.
