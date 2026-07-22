# Source File Catalog

`port_strategy_research`의 주요 파일 책임, 입력·출력, 변경 영향과 실행 위험을 정리한다.

이 문서는 전체 repository inventory가 아니다.
Research 흐름을 이해하고 유지보수하는 데 필요한 파일만 관리한다.

## 1. 문서 목적

| 항목 | 값 |
|---|---|
| 대상 | `port_strategy_research` 루트와 `docs/source-file-catalog.md` |
| 기준 | 현재 문서화된 파일 구조, import, entrypoint와 데이터 계약 |
| 제외 | Build 결과물, Cache, IDE 파일, `__pycache__`, 일회성 Dump와 Report 산출물 |
| 주요 관점 | 파일 책임, 입력, 출력, DB·파일·AWS 영향, 변경 연동 |
| 실제 실행 | 문서 정리 과정에서 수행하지 않음 |
| 미확인 사항 | 실제 코드 최종 대조가 필요한 내용은 추정하지 않음 |

## 2. 서비스 흐름

| 단계 | 책임 |
|---|---|
| Input Load | Market·Stock Feature, Price와 Universe 조회 |
| Market Decision | Common Market 판단 호출 |
| Position Process | 기존 Position의 보유·청산·이월 처리 |
| Buy Filter | 신규 매수 후보 선별 |
| Sizing·Guard | Allocation, Guard와 Haircut 적용 |
| Daily Store | 거래일별 성과와 Position Snapshot 저장 |
| Trade Store | 완료 거래와 Metadata 저장 |
| Analysis | Basic·Extended Analysis 생성 |
| Report | Summary·Buy·Sell·Trade·Recommendation 생성 |
| Delivery | AWS Batch Wrapper의 선택적 S3 업로드 |

## 3. Root와 설정 파일

| 파일 | 역할 |
|---|---|
| `__init__.py` | `port_strategy_research` Package Import 기준점 |
| `db_config.py` | `INTEREST_DB_*`와 Research DB 연결 설정 관리 |
| `requirements.txt` | Research Runtime Dependency 목록 |
| `Dockerfile` | Research Container Image와 기본 CMD 정의 |

### 3.1 `__init__.py`

| 항목 | 값 |
|---|---|
| 책임 | Package 초기화 |
| 기능 로직 | 없음 |
| 변경 영향 | `python -m port_strategy_research.<module>` Import 구조 |
| 주의 | 기능이 없어 보여도 임의 삭제하지 않음 |

### 3.2 `db_config.py`

| 항목 | 값 |
|---|---|
| 책임 | PostgreSQL 접속 설정 중앙화 |
| 주요 입력 | `INTEREST_DB_HOST`, `PORT`, `NAME`, `USER`, `PASSWORD` |
| Password | 기본값 없이 외부 주입 |
| Search Path | `research, preprocessor, interest, reference, legacy, public` |
| 호출 영향 | Connection 생성 시 DB 접속 발생 가능 |
| 변경 위험 | 기본 DB, Schema 순서와 Credential 처리 계약 |
| 주의 | 실제 접속값을 문서·로그에 기록하지 않음 |

### 3.3 `requirements.txt`

| 항목 | 값 |
|---|---|
| 주요 Dependency | `psycopg2-binary`, `pandas`, `numpy`, `boto3` |
| Common 처리 | `port_strategy_common`은 Image Build 과정에서 포함 |
| 변경 영향 | Container Build와 Runtime Import |
| 주의 | Pinned Version은 파일 자체에서 관리하고 문서에 반복하지 않음 |

### 3.4 `Dockerfile`

| 항목 | 값 |
|---|---|
| 기반 이미지 | `python:3.13-slim` |
| 포함 대상 | `port_strategy_common`, `port_strategy_research` |
| 기본 CMD | `backtest_research_run.py` Compile 확인 |
| 실제 실행 | Batch·ECS 또는 Local Command Override |
| 저장소 경계 | Image Push와 Job·Task 등록은 배포 영역 |
| 주의 | URI, ARN, Queue와 Registry 원문을 문서에 기록하지 않음 |

## 4. Backtest Research Entrypoint

### 4.1 `backtest_research_run.py`

| 항목 | 값 |
|---|---|
| 책임 | 표준 Backtest Research 전체 Orchestration |
| 주요 입력 | 기간, 초기 자산, Strategy Config와 DB Feature |
| 주요 처리 | DB 연결, Run 생성, Snapshot, Engine 실행과 Analysis |
| 주요 출력 | Run, Daily, Daily Position, Trade와 Analysis |
| DB 영향 | DDL·DML과 Commit 가능 |
| 상태 영향 | Run 시작·완료·실패 상태 변경 가능 |
| 재실행 위험 | 동일 입력에 새 Run 또는 기존 결과 연결 가능 |
| 실행 위험 | 실제 Research 데이터 생성·변경 |
| 주의 | 문서화·정적 분석 중 실행하지 않음 |

## 5. Backtest Core

Backtest Core는 거래일 순서대로 기존 Position을 처리하고 신규 진입을 계산한다.

| 순서 | 파일 |
|---|---|
| 1 | `backtest_engine.py` |
| 2 | `backtest_loader.py` |
| 3 | Research Adapter 3종 |
| 4 | `backtest_position_manager.py`, `backtest_sell_logic.py` |
| 5 | `backtest_buy_logic.py` |
| 6 | `backtest_run_store.py`, `backtest_trade_log.py` |
| 7 | `backtest_metrics.py` |

### 5.1 `backtest_engine.py`

| 항목 | 값 |
|---|---|
| 책임 | 거래일 단위 Backtest 메인 루프 |
| 주요 입력 | 거래일, Feature, Price, Universe와 초기 상태 |
| 주요 처리 | Market, Position, Filter, Buy와 성과 집계 |
| 처리 순서 | 신규 Buy 전에 기존 Position 처리 |
| 주요 출력 | Daily Result와 Daily Position Snapshot |
| DB 영향 | Store Helper를 통한 쓰기와 Commit 가능 |
| 변경 위험 | 거래일 순서, 가격 기준, Position 처리 순서와 수익률 계산 |
| 주의 | Look-ahead와 Partial Save 가능성을 함께 확인 |

### 5.2 `backtest_loader.py`

| 항목 | 값 |
|---|---|
| 책임 | Backtest 입력 DB 조회 |
| Market 입력 | `pre_total_market_daily_feature` |
| Stock 입력 | `pre_total_stock_daily_feature` |
| Price 입력 | `interest_price_raw` |
| Universe 입력 | `stock_universe` |
| DB 영향 | 조회 |
| 변경 위험 | Date 기준, Join Cardinality, 정렬과 Row Shape |
| 주의 | Feature 누락, 실제 0과 미래 데이터를 구분 |

### 5.3 `backtest_buy_logic.py`

| 항목 | 값 |
|---|---|
| 책임 | 신규 Position 진입 처리 |
| 주요 입력 | Filter 후보, Market Decision, Cash와 Config |
| Sizing | Research Sizing Adapter |
| Guard | Common Buy Guard |
| Haircut | Common Backtest Buy Size Haircut |
| 주요 출력 | 신규 Position과 Entry Metadata |
| DB 직접 쓰기 | Trade Log Helper를 통해 당일 Stop 거래 저장 가능 |
| 변경 위험 | Candidate 순서, Allocation, Reason과 Position Shape |
| 주의 | 운영 Daily BUY Signal 생성 흐름으로 표현하지 않음 |

### 5.4 `backtest_sell_logic.py`

| 항목 | 값 |
|---|---|
| 책임 | Common Sell 판단 Wrapper |
| 공통 함수 | `common_evaluate_backtest_sell` |
| 주요 입력 | Position, Market·Stock Feature와 Config |
| 주요 출력 | Sell Decision과 Reason |
| DB 직접 접근 | 없음 |
| 변경 위험 | Common Input Mapping, 우선순위와 Reason |
| 주의 | Daily Position Evaluator와 같은 Runtime 구현으로 간주하지 않음 |

### 5.5 `backtest_position_manager.py`

| 항목 | 값 |
|---|---|
| 책임 | 기존 Position의 보유·청산·이월 처리 |
| 주요 처리 | 당일 수익률, 장중 Stop, 일반 Sell과 Carry |
| 주요 출력 | 생존 Position, 청산 거래와 일별 성과 |
| DB 영향 | Trade Log Helper를 통한 쓰기 가능 |
| 변경 위험 | Stop 우선순위, 보유일, 가격과 Position Dict |
| 주의 | 청산 거래 저장 실패와 Position State를 함께 확인 |

### 5.6 `backtest_trade_log.py`

| 항목 | 값 |
|---|---|
| 책임 | 완료 거래 Persistence |
| 주요 Table | `strategy_trade_log` |
| 주요 입력 | Run, 종목, Buy·Sell 일자, 가격, Reason과 Snapshot |
| DB 영향 | Insert |
| 변경 위험 | Column, JSON Metadata, Return과 Hold Period 의미 |
| 주의 | 동일 거래 중복과 Transaction 참여 범위를 확인 |

### 5.7 `backtest_metrics.py`

| 항목 | 값 |
|---|---|
| 책임 | Backtest 성과 지표 계산 |
| 주요 입력 | Daily Return DataFrame |
| 주요 출력 | MDD와 Sharpe Ratio |
| 설정 | Common Risk-free Rate와 Trading Days |
| DB 접근 | 없음 |
| 변경 위험 | Column, Annualization, 빈 값과 0분모 처리 |
| 주의 | 표본 부족이나 계산 불가를 정상 수치로 만들지 않음 |

### 5.8 `backtest_run_store.py`

| 항목 | 값 |
|---|---|
| 책임 | Backtest Run과 일별 결과 Persistence |
| 주요 Table | `strategy_backtest_run`, `strategy_backtest_daily` |
| Position Table | `strategy_backtest_daily_position` |
| 주요 처리 | Table 확인, Run 생성, Daily 저장, Position 저장과 Finalize |
| DB 영향 | DDL, Insert, Update, Upsert와 Commit 가능 |
| 재실행 위험 | Run·Date·Ticker 기준 중복 또는 기존 Row 갱신 |
| 변경 위험 | Unique Key, Conflict Target, Status와 Transaction |
| 주의 | Daily와 Position 저장 후 Run 상태 확정 순서를 확인 |

## 6. Research Adapter

Research Adapter는 `port_strategy_common`을 직접 호출하며 `port_strategy_decision`을 Runtime Import하지 않는다.

### 6.1 `research_backtest_market_adapter.py`

| 항목 | 값 |
|---|---|
| 책임 | Market Feature를 Common Context로 변환 |
| 공통 함수 | `common_decide_market` |
| 주요 출력 | Research가 사용하는 Market Decision |
| DB 접근 | 없음 |
| 변경 위험 | Context Field, Config와 Reason Mapping |
| 주의 | Common 결과 의미를 Research에서 임의 재해석하지 않음 |

### 6.2 `research_backtest_filter_adapter.py`

| 항목 | 값 |
|---|---|
| 책임 | Stock Feature를 Common Buy Filter에 연결 |
| 공통 함수 | `common_filter_buy_candidates` |
| 주요 출력 | 통과·제외 후보와 Reason |
| DB 접근 | 없음 |
| 변경 위험 | Candidate Row, Filter Config와 정렬 |
| 주의 | Filter 탈락과 Feature 누락을 구분 |

### 6.3 `research_backtest_sizing_adapter.py`

| 항목 | 값 |
|---|---|
| 책임 | Filter 후보를 Common Allocation에 연결 |
| 공통 함수 | `common_allocate_positions` |
| 주요 출력 | 후보별 Position Allocation |
| DB 접근 | 없음 |
| 변경 위험 | Cash, Exposure, 수량·비중과 Rounding |
| 주의 | Position 크기 의미를 Research 전용으로 임의 변경하지 않음 |

## 7. Analysis

### 7.1 `backtest_analysis_basic.py`

| 항목 | 값 |
|---|---|
| 책임 | Run 기준 기본 집계 Analysis 생성 |
| 주요 입력 | Trade Log와 저장된 Backtest 결과 |
| 주요 출력 | Buy Reason, Hold Period와 Market Signal 분석 |
| DB 영향 | 3개 Analysis Table Insert (Delete·Upsert 없음) |
| 실행 위치 | `backtest_research_run.py`에서 주석 처리, 표준 Run 자동 실행 아님 |
| 변경 위험 | Run ID 범위, Bucket과 Label 의미 |
| 주의 | 거래 0건과 입력 누락을 구분 |

### 7.2 `analysis_extended.py`

| 항목 | 값 |
|---|---|
| 책임 | Run 기준 확장 Analysis 재생성 |
| 실행 위치 | `backtest_research_run.py` 자동 호출 + `run_extended_analysis.py` 단독 실행 |
| 주요 영역 | Signal·Holding, Ticker, Entry·Exit, Sector와 MB Weak |
| 주요 출력 | `strategy_backtest_*_analysis` 계열 |
| DB 영향 | 12개 Table Delete 후 Insert |
| 재실행 위험 | 마지막 단일 commit, 중간 실패 시 함께 rollback |
| 변경 위험 | Run 범위, Threshold, Bucket과 Transaction |
| 주의 | 삭제 대상 12개 Table 범위를 다른 Run으로 확대하지 않음 |

### 7.3 `run_extended_analysis.py`

| 항목 | 값 |
|---|---|
| 책임 | Extended Analysis 실행 Entrypoint |
| Run 선택 | 최신 또는 코드가 결정한 Run ID |
| 호출 대상 | `analysis_extended.run_analysis_extended` |
| DB 영향 | Analysis Table 갱신 |
| 실행 위험 | Delete·Insert와 Commit 가능 |
| 주의 | 문서 작업에서 실행하지 않음 |

## 8. Report

### 8.1 `backtest_report_run.py`

| 항목 | 값 |
|---|---|
| 책임 | 전체 Text Report 생성 Orchestration |
| Run 선택 | `started_at DESC` 최신 Run 자동 선택 (진입점 지정 옵션 없음) |
| 호출 대상 | Summary, Buy·Sell, Trade Detail과 Recommendation |
| DB 영향 | 조회 |
| 파일 영향 | Local TXT 생성 |
| 변경 위험 | Run 선택, 호출 순서, 파일명과 덮어쓰기 |
| 주의 | Report 생성 성공과 S3 업로드 성공을 구분 |

### 8.2 `report_data_loader.py`

| 항목 | 값 |
|---|---|
| 책임 | Report 공통 데이터 조회 |
| 주요 입력 | Run, Daily, Daily Position, Trade와 Analysis |
| Snapshot 입력 | Threshold와 Config 관련 저장 데이터 |
| DB 영향 | 조회 |
| 변경 위험 | 최신 Run, Join, Sort와 Missing 처리 |
| 주의 | Daily Position Snapshot과 Trade Event 의미를 혼동하지 않음 |

### 8.3 `report_formatter.py`

| 항목 | 값 |
|---|---|
| 책임 | 사람이 읽는 문자열 포맷 |
| 주요 처리 | Label, Percentage, Run Input과 Buy·Sell Reason |
| DB 접근 | 없음 |
| 파일 쓰기 | 없음 |
| 변경 위험 | Reason Mapping, 단위와 표시 의미 |
| 주의 | 표시 변경도 Report 해석 변경으로 기록 |

### 8.4 `report_summary.py`

| 항목 | 값 |
|---|---|
| 책임 | Summary Report 생성 |
| 주요 입력 | Run, Metrics와 주요 Analysis |
| 출력 | Summary TXT |
| DB 영향 | 조회 |
| 파일 영향 | 쓰기 |
| 주의 | 미산출 지표를 0으로 표시하지 않음 |

### 8.5 `report_buy_sell.py`

| 항목 | 값 |
|---|---|
| 책임 | 거래일별 Buy·Sell Report 생성 |
| 주요 입력 | Daily, Daily Position과 Trade Event |
| 출력 | Buy·Sell TXT |
| DB 영향 | 조회 |
| 파일 영향 | 쓰기 |
| 주의 | 보유 Position과 신규 Buy를 Snapshot 기준으로 구분 |

### 8.6 `report_trade_detail.py`

| 항목 | 값 |
|---|---|
| 책임 | 완료 거래 상세 Report 생성 |
| 주요 입력 | `strategy_trade_log` |
| 출력 | Trade Detail TXT |
| DB 영향 | 조회 |
| 변경 위험 | Trade Column, Reason과 Return 의미 |
| 주의 | 실제 주문·체결 Report로 표현하지 않음 |

### 8.7 `report_recommendation.py`

| 항목 | 값 |
|---|---|
| 책임 | Research 추천·진단 Report 생성 |
| 주요 입력 | Analysis와 Threshold Snapshot |
| 출력 | Recommendation TXT |
| DB 영향 | 조회 |
| 파일 영향 | 쓰기 |
| 변경 위험 | Threshold 해석, Label과 진단 문구 |
| 주의 | 실제 투자 권고나 주문 지시로 표현하지 않음 |

## 9. AWS Batch Report Wrapper

### 9.1 `aws_batch_backtest_report_wrapper.py`

| 항목 | 값 |
|---|---|
| 책임 | AWS Batch Report 실행과 선택적 S3 업로드 |
| Secret 입력 | `RESEARCH_APP_SECRET_JSON` |
| DB Mapping | `INTEREST_DB_*` 환경변수 |
| Output | `REPORT_OUTPUT_DIR` |
| 실행 대상 | `port_strategy_research.backtest_report_run` |
| S3 조건 | `REPORT_S3_BUCKET` 설정 |
| Key 구성 | Prefix, 날짜, Job ID와 파일명 |
| 외부 영향 | DB 조회, Local File과 S3 쓰기 |
| 주의 | Secret, Bucket, Prefix와 Job ID 원문을 남기지 않음 |

## 10. Block·Watch·Exception Buy 연구

이 계열은 Daily 운영 파이프라인의 정식 단계가 아닌 연구·보류 파일로 관리한다.

### 10.1 `block_watch_analysis_run.py`

| 항목 | 값 |
|---|---|
| 책임 | Watch Candidate 사후 성과 분석 |
| 주요 처리 | N일 후 Return 계산 |
| DB 영향 | Candidate Return Update 가능 |
| 분류 | Research |
| 주의 | 실행하지 않고 삭제 대상도 아님 |

### 10.2 `block_watch_backtest_run.py`

| 항목 | 값 |
|---|---|
| 책임 | BLOCK 이후 Watch Candidate 품질 검증 |
| 주요 처리 | Candidate와 Forward Return 계산 |
| DB 영향 | 조회 |
| 출력 | Console Summary 가능 |
| 분류 | Backtest 성격 Research |
| 주의 | 운영 BLOCK Watch 실행으로 표현하지 않음 |

### 10.3 `block_exception_buy_engine_run.py`

| 항목 | 값 |
|---|---|
| 책임 | Backtest Engine 기반 Exception Buy 검증 |
| 주요 처리 | Run 생성, Daily 저장과 Finalize (Analysis 미호출) |
| DB 영향 | 쓰기와 Commit 가능 |
| 분류 | Research·보류 |
| 주의 | 명시 승인 없이 실행하지 않음 |

### 10.4 `block_exception_buy_backtest_run.py`

| 항목 | 값 |
|---|---|
| 책임 | Threshold 기반 Exception Buy 후보 검증 |
| 주요 출력 | Candidate, Trade와 월별 Summary |
| DB 영향 | 조회 가능 |
| 분류 | Backtest 성격 Research |
| 주의 | 실제 Daily BUY 예외 허용 기능으로 단정하지 않음 |

## 11. 데이터 계약

### 11.1 주요 입력

| 데이터 | 역할 |
|---|---|
| `pre_total_market_daily_feature` | Market 판단 |
| `pre_total_stock_daily_feature` | Filter, Sizing과 Sell 판단 |
| `interest_price_raw` | 가격, 수익률과 체결 가정 |
| `stock_universe` | Backtest 대상 Universe |
| Config Snapshot | Strategy 기준 재현 |
| Run Input | 기간, 초기 자산과 실행 옵션 |

### 11.2 주요 출력

| 데이터 | 역할 |
|---|---|
| `strategy_backtest_run` | Backtest 실행 메타데이터와 상태 |
| `strategy_backtest_daily` | 거래일별 성과 |
| `strategy_backtest_daily_position` | 거래일별 Position Snapshot |
| `strategy_trade_log` | 완료 거래 상세 |
| `strategy_backtest_*_analysis` | Run 기준 분석 결과 |
| Report TXT | 사람이 읽는 Research 결과 |

### 11.3 변경 시 확인할 계약

| 항목 | 확인 내용 |
|---|---|
| Table | Schema, Table Name과 Search Path |
| Column | Type, NULL 허용과 의미 |
| Key | Run ID, Unique Key와 Conflict Target |
| Date | Trade Date, Feature Date와 Price Date |
| Status | Run과 Analysis 상태값 |
| Reason | Common·Report가 소비하는 문자열 |
| Snapshot | Config, Input, Threshold와 Metadata Shape |
| Transaction | DDL·DML, Partial Save와 Rollback |
| Re-run | 신규 Run, Delete·Insert와 Upsert 동작 |
| File | Report 이름, 경로와 덮어쓰기 |
| S3 | 업로드 조건, 대상 파일과 부분 실패 |

## 12. 실행 위험 분류

| 등급 | 의미 |
|---|---|
| 읽기 | DB 조회와 운영·연구 데이터 출력 가능 |
| 쓰기 | Research Table Insert·Update·Upsert 가능 |
| 삭제 | Run ID 대상 Analysis Row 삭제 가능 |
| 파일 | Local TXT 생성·덮어쓰기 가능 |
| 외부 쓰기 | S3 업로드 가능 |
| 후속 영향 | Analysis와 Report가 저장 결과를 소비 |

### 12.1 파일별 위험

| 파일 | 위험 |
|---|---|
| `backtest_research_run.py` | DB DDL·DML, Backtest와 Analysis |
| `backtest_engine.py` | Daily·Position 저장과 Commit 가능 |
| `backtest_run_store.py` | DDL, Insert, Update와 Finalize |
| `backtest_trade_log.py` | Trade Log Insert |
| `analysis_extended.py` | Analysis Delete·Insert |
| `run_extended_analysis.py` | DB 연결과 Extended Analysis 실행 |
| `backtest_report_run.py` | DB Read와 Local TXT 생성 |
| `report_*.py` | DB Read 또는 Local File 쓰기 |
| AWS Batch Wrapper | Secret 매핑, Report와 S3 업로드 |
| `block_watch_analysis_run.py` | DB Update 가능 |
| Exception Buy 계열 | DB 연결과 Backtest 유사 실행 |
| Loader | DB Read |
| Adapter·Formatter·Metrics | 직접 DB 쓰기는 없지만 결과 계약에 영향 |

### 12.2 문서 작업 중 실행하지 않는 대상

| 대상 | 이유 |
|---|---|
| Backtest Entrypoint | Run과 결과 Table 변경 가능 |
| Engine·Store 함수 | DDL·DML과 Commit 가능 |
| Analysis Entrypoint | Delete·Insert 가능 |
| Report Entrypoint | DB Read와 Local File 생성 |
| AWS Batch Wrapper | Secret, File과 S3 영향 |
| Block·Watch 연구 | DB Update 또는 Simulation 가능 |
| Container Command Override | 실제 Research 실행 가능 |
| AWS Batch·ECS | 외부 운영 실행으로 연결 |

## 13. AWS와 운영 위치

| 항목 | 값 |
|---|---|
| Paper Daily Step 4 | `backtest_research_run.py` |
| Paper Daily Step 5 | `backtest_report_run.py` |
| Orchestration | Scheduler와 Step Functions 책임 |
| Report Wrapper | AWS Batch 환경에서 사용 가능 |
| Container 기본 CMD | Compile 확인 |
| 실제 실행 | Job·Task Command Override |
| 저장소 증거 | Dockerfile, Wrapper와 Python Entrypoint |
| 외부 운영 사실 | Queue, Definition, Schedule과 State Machine 문서에서 관리 |

Repository 파일로 확인되는 구조와 실제 AWS 현재 상태를 혼동하지 않는다.

## 14. 문서 파일

| 파일 | 역할 |
|---|---|
| `AGENTS.md` | 작업 범위, 안전, 데이터 계약과 완료 기준 |
| `README.md` | Research 구조, 흐름, 설정과 운영 AS-IS |
| `CHANGELOG.md` | 기능·구조·문서 기준 변경 이력 |
| `docs/source-file-catalog.md` | 파일 책임, 입출력과 변경 영향 |

### 문서별 갱신 기준

| 문서 | 갱신 조건 |
|---|---|
| `AGENTS.md` | 작업 규칙, 안전 기준과 필수 계약이 바뀜 |
| `README.md` | 책임, 흐름, 설정, Entrypoint와 운영 위치가 바뀜 |
| `CHANGELOG.md` | 실제 기능, 구조 또는 문서 기준이 바뀜 |
| `docs/source-file-catalog.md` | 파일, 책임, 입출력과 실행 위험이 바뀜 |

날짜별 `docs/worklog/*.md`는 새로 만들지 않는다.
과거 생성 사실은 CHANGELOG의 당시 이력으로만 보존한다.

## 15. 정리 후보

| 파일 | 현재 판단 |
|---|---|
| Block Watch 계열 | 연구·검증 파일로 보존 |
| Exception Buy 계열 | 연구·보류 파일로 보존 |
| Report 모듈 | 운영 Report 생성 구성요소로 유지 |
| 기타 Tracked Source | 현재 삭제 확정 대상 없음 |

다음 조건을 충족하기 전에는 파일을 삭제하지 않는다.

| 확인 | 기준 |
|---|---|
| Import | 다른 파일에서 참조하지 않음 |
| Entrypoint | Local, Docker, Batch와 ECS Command에서 호출하지 않음 |
| DB 계약 | 운영 검증이나 수동 Research에 사용되지 않음 |
| Output | Report 또는 Analysis 생성에 필요하지 않음 |
| 문서 | README, CHANGELOG와 Catalog에서 책임 정리 |
| 승인 | 사용자의 명시적 삭제 요청 |

## 16. 카탈로그 갱신 조건

다음 변경이 발생하면 이 문서를 같은 작업에서 갱신한다.

| 변경 | 반영 내용 |
|---|---|
| 파일 추가 | 역할, 입력, 출력과 위험 추가 |
| 파일 삭제 | 참조 제거와 삭제 이력 확인 |
| 파일 이동 | 경로와 Import·Entrypoint 영향 수정 |
| Entrypoint 변경 | Step 4·5와 실행 위험 반영 |
| Loader 변경 | 입력 Table, Date와 Join 계약 수정 |
| Store 변경 | Output Table, Key와 Transaction 수정 |
| Adapter 변경 | Common 함수와 Mapping 수정 |
| Analysis 변경 | Table, Run 범위와 Delete·Insert 수정 |
| Report 변경 | Data Loader, Formatter와 Output File 수정 |
| AWS Wrapper 변경 | Secret, Environment, Output과 S3 영향 수정 |
| Docker 변경 | Runtime, Copy와 Command 수정 |
| Dependency 변경 | Runtime Import와 설치 구조 수정 |
| 연구 후보 변경 | Block·Watch 계열 분류와 위험 수정 |
| 문서 체계 변경 | AGENTS, README와 CHANGELOG 역할 정합성 수정 |

카탈로그에는 확인된 현재 책임만 기록한다.
존재하지 않는 파일, 추정한 AWS Resource와 미확인 동작은 추가하지 않는다.
