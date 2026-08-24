# CHANGELOG

`port_strategy_research`의 기능, 데이터 계약, 실행 구조와 문서 기준 변경 이력을 기록한다.

- 최신 변경을 위에 배치한다.
- 기능 변경과 문서 정비를 구분한다.
- 민감정보와 일회성 운영값은 기록하지 않는다.
- 날짜별 worklog는 새로 만들지 않고 주요 변경은 이 문서에 남긴다.

## 2026-08-24

### Research Strategy Version과 Champion–Challenger 경로 고도화

Strategy Config Version을 Strategy Logic Release Identity로 두고, Baseline을 덮어쓰지 않는
Challenger Version과 Candidate·Operating 배포 경로 분리를 반영한 변경이다.
이번 작업은 4개 문서 정비이며 코드·AWS·DB·Backtest는 실행하지 않았다.

#### 기능·구조 AS-IS

| 항목 | 값 |
|---|---|
| Challenger 추가 | `RSCFG-0002` Challenger Profile 추가 (`status=CANDIDATE`) |
| 값 차이 | `market.aggressive_max_positions` `4` → `6` (RSCFG-0001은 유지) |
| Baseline 보존 | `RSCFG-0001` Baseline을 덮어쓰지 않고 별도 Version으로 분리 |
| Candidate 실행 | `RSCFG-0002` Candidate 실행 성공 (운영자 검증 사실) |
| Candidate 저장 | Candidate Run이 `strategy_backtest_run`에 저장됨 |
| Version 조회 | `RSCFG-0001`·`RSCFG-0002` Version별 결과 조회 가능 |

#### 배포 경로 AS-IS

| 항목 | 값 |
|---|---|
| `main` Push | Build/Test 검증 경로 (Candidate 자동 실행 아님) |
| 경로 분리 | Strategy Logic 변경 여부에 따라 Candidate 또는 Operating Release로 분리 |
| Candidate·Operating | 서로 다른 배포 경로 |
| Champion Promotion | Candidate 성공은 자동 Champion Promotion이 아님 |
| Champion 판단 | Research 담당자 판단, View는 조회·선택 Interface |

#### 문서 경계

| 항목 | 값 |
|---|---|
| 과거 표현 정정 | "main Push → Candidate 자동 실행" 표현을 현재 AS-IS로 수정 |
| 과거 이력 보존 | Revision 5·6·7 승격·Rollback은 과거 수동 검증 이력으로 유지 |
| DevOps 상세 | IAM·AWS CLI·Job Definition·Step Functions 절차는 `port-devops` 책임 |
| 변경 범위 | `AGENTS.md`, `README.md`, `CHANGELOG.md`, `docs/source-file-catalog.md` |
| 일회성 식별자 | 전체 SHA, Digest, ARN, Job ID와 GitHub Run ID는 기록하지 않음 |

## 2026-08-12

### Research main Push Candidate 자동화 완료

`main` Push 기반 CI에서 ECR Publish와 Candidate 검증까지 자동화한 DevOps AS-IS 변경이다.
문서 기준 변경이며 이번 작업에서 코드·AWS·DB는 실행하지 않았다.

#### DevOps AS-IS

| 항목 | 변경 내용 |
|---|---|
| main Push CI | GitHub Actions·OIDC로 Research CodeBuild 자동 실행 |
| ECR Publish | Git SHA 기반 Image 자동 Publish와 Image Digest Artifact 확정 |
| Candidate 등록 | Candidate Job Definition 신규 Revision 자동 등록 |
| Candidate 실행 | AWS Batch Candidate 자동 실행과 Artifact Identity 검증 |
| Candidate 검증 | Batch SUCCEEDED와 Container Exit Code 0 확인 |
| 자동화 범위 확정 | DevOps 자동화 완료 범위를 Challenger 검증까지로 확정 |

#### Candidate Runtime

| 항목 | 값 |
|---|---|
| Candidate Revision 4 | VCPU 1, Memory 2048 MiB, Exit Code 137 Fargate OOM |
| Candidate Memory 정렬 | 4096 MiB로 정렬 |
| Candidate Revision 5 | VCPU 1, Memory 4096 MiB, 전체 기간 실행 성공 |

#### 운영 경계

| 항목 | 값 |
|---|---|
| Operating Job Definition 변경 | 없음 |
| Step Functions 변경 | 없음 |
| Champion 자동 Promotion | 미수행 |
| Champion 선택 판단 | Research 담당자 책임 |
| Champion 선택·전환 Interface | View 운영 UI |

#### 작업 범위

| 항목 | 값 |
|---|---|
| 이번 문서 변경 범위 | `AGENTS.md`, `README.md`, `CHANGELOG.md`, `docs/source-file-catalog.md` |
| 코드·설정 변경 | 이번 문서 작업에서는 없음 |
| Backtest·DB·AWS·S3 실행 | 이번 문서 작업에서는 없음 |
| 일회성 식별자 | 전체 SHA, Digest, ARN, Job ID와 GitHub Run ID는 기록하지 않음 |
| 과거 이력 | 2026-08-05~06 수동 Candidate·Promotion·Rollback 검증은 당시 이력으로 유지 |

## 2026-08-06

### 2026-08-05~2026-08-06 Research Versioned Backtest Platform과 DevOps 적용

Research를 고정 Config 실행기에서 Versioned Backtest Platform으로 전환하고,
Research 전용 CI·Container·Candidate·운영 승격 구조를 적용한 변경 묶음이다.

#### 기능

| 항목 | 변경 내용 |
|---|---|
| Common Wheel Pin | Common Source Copy를 제거하고 `port_strategy_common` Wheel `1.0.0` 고정 설치로 전환 |
| Config CLI | `--strategy-config-version`(기본 `RSCFG-0001`)과 `--run-mode` 등 실행 옵션 추가 |
| 명시적 Config 주입 | Engine·Adapter·Buy·Sell·Position에 Resolved Config 명시적 전달 |
| BUY Guard 수정 | BUY Guard의 `config={}` 연결을 실제 Resolved `buy_guard` Config 전달로 수정 |
| Config Snapshot·Hash | Resolved Config Canonical JSON과 SHA-256 Config Hash 생성 |

#### 구조

| 항목 | 변경 내용 |
|---|---|
| Strategy Profile | `strategy_profiles/`와 `RSCFG-0001` Baseline Profile 도입 |
| Schema 검증 | 필수 Category·Metadata, 허용 Key와 Unknown Key 차단 검증 추가 |
| Version Identity 분리 | Common Package·Common Strategy·Research Engine·Strategy Config·Metrics Config Version 분리 |
| Run·Trade Config Persistence | Run에 Config Snapshot 1회 저장, Trade Log는 Run ID·Config Identity 참조 |
| Artifact Identity | Source SHA·Image Digest·Status 저장과 형식 검증 추가 |
| Input Snapshot | 입력 Manifest·Hash·Status 저장 구조 추가 |
| Run Mode 분리 | `BACKTEST`와 `CANDIDATE` Run Mode 구분 |

#### DevOps

| 항목 | 변경 내용 |
|---|---|
| GitHub Actions·OIDC | OIDC 인증으로 Research CodeBuild 시작·상태 확인 Workflow 추가 |
| CodeBuild | Compile, Contract Test, Config·Version 검증, Docker Build와 Smoke 실행 |
| Build-only와 Publish | Build-only 기본과 조건부 ECR Publish 분리, 실패 시 Push 차단 |
| Image Identity | Git SHA 기반 Image Tag와 Digest 증적, Mutable `latest` 의존 제거 |
| Candidate Job Definition | 운영 Family와 분리한 `-candidate` Family 정적 계약 검증 |
| OIDC Trust 수정 | 최초 Workflow의 `AssumeRoleWithWebIdentity` 실패 원인을 실제 Subject 불일치로 확인 후 수정 |

#### 검증

| 항목 | 결과 |
|---|---|
| OIDC 최초 실패 | 최초 Workflow는 OIDC 단계에서 실패, CodeBuild 미시작, ECR Push 미발생 |
| OIDC 해결 | 실제 Token Subject 기준으로 Trust Policy를 Repository와 `main` Branch로 제한 후 Build-only 성공, 이후 Image Publish Workflow 성공 |
| Candidate 실행 | `--run-mode CANDIDATE`·`RSCFG-0001`·`--require-artifact-identity`로 수동 실행, Job Status·Exit Code·CloudWatch Log와 Run·Config Hash·Metrics·Input Snapshot 저장 확인 |
| Candidate 실패 계약 | 의도적 실패 Candidate 실행에서 실패 상태와 Artifact Identity 저장 확인 |
| Candidate 격리 | 운영 Step Functions·Scheduler 미변경과 자동 승격 미구성 확인 |
| 재현성 – 일치 | 동일 Candidate Revision·Digest·Source SHA·`RSCFG-0001`에서 Config Hash, Config Snapshot·KV, Daily Result·Position, Trade Log, Run Input과 Total Return·MDD·Sharpe·Trade Count 완전 일치 (허용 오차 `0.000000000001`) |
| 재현성 – 제외 | Run ID와 생성·시작·종료 시각은 비교 대상에서 제외 |
| 재현성 – Input Snapshot | Manifest는 일치하나 원천 데이터 갱신으로 Input Snapshot Hash는 변동 가능, 완전 동일 Hash로 기록하지 않음 |
| 운영 승격 | Champion Revision 5에서 검증된 Candidate Artifact로 Revision 6 등록 후 운영 State Machine Step 4 참조를 5→6으로 승격, Step 4 이외 정의·Role·Type 미변경 |
| Rollback | 운영 State Machine Step 4 참조를 6→5로 복원(Champion Pointer 변경), Revision 5 ACTIVE 유지 확인 |
| Revision 6 OOM | VCPU 1·Memory 2048MiB Step 4 단독 실행에서 Exit Code 137 Fargate OutOfMemoryError, 로직·Config 오류가 아닌 Memory 부족으로 확인 후 Revision 5로 Rollback |
| Revision 7 해결 | Revision 6 Image·Command·Config·Role·Secret·Environment 유지, Memory만 4096MiB로 확장, VCPU 1 유지 |
| Revision 7 승격 | Step 4 전용 State Machine 단독 검증(Step Functions·AWS Batch 성공, Exit Code 0) 후 운영 Step 4를 Revision 7로 최종 승격 |
| Revision 5 Rollback 유지 | Revision 5를 Rollback 대상 ACTIVE Revision으로 유지, Revision 6은 실패 증적으로 보존 |

#### 운영 AS-IS

| 항목 | 값 |
|---|---|
| 운영 Champion | Revision 7 |
| 운영 Step 4 | Revision 7 |
| 운영 Resource | VCPU 1, Memory 4096MiB, Attempt Timeout 600초 |
| 이전 Rollback Revision | Revision 5 |
| 운영 Run Mode | `BACKTEST` |
| 운영 Strategy Config Version | `RSCFG-0001` |

#### 작업 범위

| 항목 | 값 |
|---|---|
| 이번 문서 변경 범위 | `AGENTS.md`, `README.md`, `CHANGELOG.md`, `docs/source-file-catalog.md` |
| 코드·설정 변경 | 이번 문서 작업에서는 없음 |
| Backtest·DB·AWS·S3 실행 | 이번 문서 작업에서는 없음 |
| 일회성 식별자 | 전체 SHA, Digest, ARN과 Job ID는 기록하지 않음 |

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
