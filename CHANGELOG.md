# CHANGELOG

`port_strategy_research`의 기능, 데이터 계약, 실행 구조와 문서 기준 변경 이력을 기록한다.

- 최신 변경을 위에 배치한다.
- 기능 변경과 문서 정비를 구분한다.
- 민감정보와 일회성 운영값은 기록하지 않는다.
- 날짜별 worklog는 새로 만들지 않고 주요 변경은 이 문서에 남긴다.

## 2026-07-22

### Research 문서 기준 재정비

| 항목 | 값 |
|---|---|
| 변경 범위 | `AGENTS.md`, `README.md`, `CHANGELOG.md`, `docs/source-file-catalog.md` 문서 정비 |
| 기능 변경 | 없음 |
| 코드·설정 변경 | 없음 |
| DB·AWS·S3 실행 | 없음 |
| Backtest·Analysis·Report 실행 | 없음 |
| 운영 데이터 변경 | 없음 |

### AGENTS.md

| 항목 | 변경 내용 |
|---|---|
| 최우선 규칙 | 가독성, 2열 표, 긴 셀 분리와 문서 중복 방지 기준을 문서 앞부분에 배치 |
| 작업 범위 | `port_strategy_research` 내부 작업과 다른 MS read-only 원칙을 명확화 |
| 책임 경계 | Research와 Crawler, Preprocessor, StrategyDecision, StrategyExecution, MarketConnector, View의 책임을 분리 |
| Backtest | Entrypoint, Engine, Loader, Adapter, Buy·Sell, Position, Store와 Metrics 흐름을 구분 |
| Analysis | Basic과 Extended Analysis의 입력, 저장과 재생성 위험을 분리 |
| Report | Loader, Formatter, Summary, Buy·Sell, Trade Detail과 Recommendation 책임을 구분 |
| Common 관계 | Research가 내부 adapter를 통해 `port_strategy_common`을 직접 호출함을 명확화 |
| Decision 관계 | `port_strategy_decision` 런타임 의존 표현을 제거하고 별도 Common 소비자로 정리 |
| 데이터 계약 | Feature, Price, Universe 입력과 Run, Daily, Position, Trade, Analysis, Report 출력을 정리 |
| Backtest 안전 | Look-ahead, 거래일·가격 기준, 후보 순서, 부분 성공과 재현성 기준을 추가 |
| DB 안전 | DDL·DML, delete·insert, transaction, rollback과 재실행 영향 기준을 추가 |
| AWS Batch | Secret 매핑, Report 생성과 S3 업로드 위험을 별도 구분 |
| 연구 후보 | Block Watch와 Exception Buy 계열을 연구·보류 파일로 분류 |
| 문서 연동 | 파일 책임이 바뀌면 `docs/source-file-catalog.md`도 함께 갱신하도록 명시 |
| Worklog | 날짜별 worklog 신규 생성 금지로 현행 문서 운영 기준을 변경 |

### README.md

| 항목 | 변경 내용 |
|---|---|
| 문서 목적 | 작업 규칙보다 현재 Research 구조와 운영 AS-IS 설명에 집중하도록 재구성 |
| 서비스 요약 | 입력, 핵심 실행, 저장, 공통 로직, 진입점과 AWS 위치를 첫 표에 배치 |
| 전체 흐름 | Feature → Backtest → 저장 → Analysis → Report → 선택적 S3 업로드로 정리 |
| Backtest | Engine, Loader, Adapter, Buy, Sell, Position, Store와 Metrics를 역할별로 분리 |
| Common 관계 | Research 내부 adapter와 `port_strategy_common` 직접 호출 구조를 명확화 |
| Decision 관계 | StrategyDecision과 런타임 비의존, Common 계약 공유 관계를 별도 표로 정리 |
| 입력 계약 | Market·Stock Feature, Price Raw, Universe, Config Snapshot과 Run Input 구분 |
| 출력 계약 | Run, Daily, Daily Position, Trade Log, Analysis와 Report 구분 |
| 재실행 | Run 생성, 부분 저장, transaction, snapshot과 idempotency 주의사항 추가 |
| Analysis | Basic과 Extended Analysis를 별도 실행과 저장 흐름으로 분리 |
| Report | Run 선택, 출력 파일, 덮어쓰기와 S3 성공 상태를 구분 |
| Recommendation | 실제 투자 권고가 아닌 연구 진단임을 명시 |
| 연구 후보 | Block Watch와 Exception Buy를 Daily 운영과 분리 |
| AWS 위치 | Paper Daily Step 4와 Step 5에서의 Research 책임을 정리 |
| Docker | Compile 기본 CMD와 실제 실행 command override를 구분 |
| AWS Batch Wrapper | Secret 매핑, output directory, module 실행과 S3 업로드를 정리 |
| DB 설정 | `INTEREST_DB_*`, 기본 DB와 search path 설명을 표 중심으로 정리 |
| 계산 안전 | Look-ahead, duplicate join, fee·tax·slippage와 수치 경계를 보강 |
| 문서 체계 | AGENTS, README, CHANGELOG와 source catalog의 역할을 구분 |

### docs/source-file-catalog.md

| 항목 | 변경 내용 |
|---|---|
| 파일별 표 | 흐름, 입출력과 DB·파일·AWS 영향 중심으로 재구성 |
| 갱신 조건 | Entrypoint, Loader, Store, Adapter, Analysis, Report, Wrapper, Docker 변경 기준 추가 |
| 코드 대조 | Entrypoint, Loader, Adapter, Store, Analysis, Report와 Wrapper를 실제 소스로 확인 |

### CHANGELOG.md

| 항목 | 변경 내용 |
|---|---|
| 변경 범위 | 이번 문서 정비 범위를 4개 문서로 명시 |
| Worklog | 삭제된 날짜별 Worklog 항목 미복원과 신규 생성 금지 유지 |

### 문서 운영 결정

| 항목 | 값 |
|---|---|
| 신규 worklog | 생성하지 않음 |
| 과거 worklog 기록 | 당시 변경 사실이므로 CHANGELOG에서 보존 |
| 상세 파일 책임 | `docs/source-file-catalog.md`에서 관리 |
| 실제 코드 대조 | Source catalog 정비와 최종 점검 단계에서 별도 수행 |
| 민감정보 | 원문 기록 금지 |
| 일회성 Run·Job 값 | CHANGELOG 기록 대상에서 제외 |

## 2026-07-01

### AWS 운영 위치와 Research 책임 경계 문서화

| 항목 | 변경 내용 |
|---|---|
| 책임 경계 | Backtest·Analysis·Report와 다른 MS 책임을 README에 구분 |
| Step 4 | `backtest_research_run.py`를 Backtest Research 진입점으로 정리 |
| Step 5 | `backtest_report_run.py`를 Backtest Report 진입점으로 정리 |
| 컨테이너 | Dockerfile, requirements와 AWS Batch Report Wrapper 역할 추가 |
| Wrapper 설정 | Report output, Secret JSON, S3 Bucket·Prefix와 Job ID 사용 경로 설명 |
| 연구 후보 | Block Watch와 Exception Buy 계열을 Daily 운영과 분리 |
| Adapter | Research 내부 Market·Filter·Sizing Adapter 3종 반영 |
| Source catalog | Adapter와 Container·AWS Batch Wrapper 파일 책임 추가 |
| Worklog | 당시 문서 운영 기준에 따라 `docs/worklog/2026-07-01.md` 생성 |

### 구조 정정

| 항목 | 변경 내용 |
|---|---|
| Research·Decision 관계 | Research가 `port_strategy_common`을 직접 호출하고 Decision을 런타임 import하지 않음을 명시 |
| Engine | Research Market·Filter Adapter 호출 경로로 설명 갱신 |
| Buy Logic | Research Sizing Adapter 경유 구조로 설명 갱신 |
| Dependency | `port_strategy_decision` 런타임 의존 제거 |
| AWS Dependency | S3 업로드 경로의 `boto3` 반영 |
| PostgreSQL Package | 설치 기준을 `psycopg2-binary`로 표기 |

### 작업 범위

| 항목 | 값 |
|---|---|
| 기능 변경 | 없음 |
| 코드·설정 변경 | 없음 |
| 실제 실행 | Backtest, Analysis, Report, DB, AWS, S3, Slack과 주문 실행 없음 |
| 외부 MS 기록 | 다른 MS 내부와 전체 orchestration 상세는 반영하지 않음 |
| 민감정보 | Secret, ARN, URI, Bucket, Command와 DB 접속값 원문 기록 없음 |

## 2026-05-28

### 파일 카탈로그와 설명 주석 정비

| 항목 | 변경 내용 |
|---|---|
| Source catalog | 파일별 역할, 주요 책임과 실행 주의사항 문서 추가 |
| Python 설명 | 모듈 단위 한글 docstring 추가 |
| 함수 설명 | DB 저장, 분석, Report와 핵심 Backtest 함수에 제한적으로 docstring 추가 |
| Daily Position Snapshot | `strategy_backtest_daily_position` 저장 흐름 문서화 |
| Report 조회 | 일별 Position Snapshot 기반 조회 전환 내용 반영 |
| Worklog | 당시 문서 운영 기준에 따라 `docs/worklog/2026-05-28.md` 생성 |

### 작업 범위

| 항목 | 값 |
|---|---|
| 문서·주석 변경 | 있음 |
| 기능 변경 | 없음으로 기록 |
| 실제 Backtest·DB 실행 | 없음 |
| 민감정보 | 원문 기록 없음 |

## 2026-05-27

### DB 설정과 Schema 구조 정비

| 항목 | 변경 내용 |
|---|---|
| DB 설정 | `db_config.py`의 `get_db_config()`로 접속 설정 외부화 |
| 환경변수 | `INTEREST_DB_*` 기반 설정으로 정리 |
| Password | 하드코딩 후보 제거와 외부 주입 원칙 적용 |
| 기본 DB | 로컬 기본 DB명을 `portfolio`로 정리 |
| Schema 구조 | 단일 DB와 Domain별 Schema 구조 문서화 |
| Search Path | `research, preprocessor, interest, reference, legacy, public` 명시 |
| SQL 호환 | 기존 SQL이 Search Path 기반으로 동작하는 구조 유지 |

### 작업 범위

| 항목 | 값 |
|---|---|
| 실제 DB 실행 | 없음 |
| Backtest·Report 실행 | 없음 |
| 외부 호출·주문 | 없음 |
| 민감정보 | 원문 기록 없음 |

## 2026-05-26

### 초기 문서와 캐시 정리

| 항목 | 변경 내용 |
|---|---|
| 초기 문서 | `AGENTS.md`, `README.md`와 당시 Worklog 초안 추가 |
| 캐시 정리 | `__pycache__/`와 내부 `*.pyc` 파일 정리 |
| 작성 기준 | 당시 파일 구조와 소스를 Read-only로 확인한 결과 |

### 작업 범위

| 항목 | 값 |
|---|---|
| 실제 실행 | Backtest, Research, Report, DB, 외부 API, Crawler와 주문 실행 없음 |
| 민감정보 | 원문 기록 없음 |
