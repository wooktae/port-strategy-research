# port_strategy_research

`port_strategy_research`는 전처리 feature와 가격·universe 데이터를 읽어 포트폴리오 백테스트를 수행하고,
저장된 결과를 분석해 텍스트 리포트를 생성하는 Research 마이크로서비스다.

현재 Research는 단일 고정 Config 백테스트 실행기가 아니라, 고정된 Common 판단 Engine에
Version별 Strategy Profile을 선택·주입하는 `Versioned Backtest Platform`이다.
Common은 판단 함수와 기본 계약을 제공하고, Research는 Version별 `Strategy Profile`을 선택해
전체 Backtest Run에 명시적으로 주입한다.

Research는 내부 adapter를 통해 `port_strategy_common`의 market, filter, sizing, guard와 sell 계약을 직접 사용한다.
`port_strategy_decision`을 런타임에 import하지 않으며, 두 서비스는 동일한 Common 계약을 사용하는 별도 소비자다.

Research 결과는 여전히 연구·검증 산출물이다.
Daily Signal, Execution Plan과 실제 주문은 Research 책임이 아니다.
Research 실행 Artifact 배포와 Strategy 운영 성과 승격은 서로 다른 절차다.

이 문서는 현재 저장소의 파일 구조, import, entrypoint와 실제 소스를 기준으로 작성했다.
문서 정리 과정에서는 실제 Backtest, Analysis, Report, DB 쓰기, AWS, S3와 주문 실행을 수행하지 않았다.

## 1. 서비스 요약

| 항목 | 값 |
|---|---|
| 서비스 | `port_strategy_research` |
| 계층 | Research |
| 성격 | Versioned Backtest Platform |
| 공통 로직 | `port_strategy_common` Wheel `1.0.0` 고정 설치 |
| 전략 설정 | Version별 Strategy Profile (`strategy_profiles/`) |
| 기본 Baseline | `RSCFG-0001` (`status=BASELINE`) |
| Challenger | `RSCFG-0002` (`status=CANDIDATE`) |
| 핵심 실행 | Backtest Research |
| Run Mode | `BACKTEST`, `CANDIDATE` |
| 주요 저장 | Run, Daily, Daily Position, Trade Log와 Analysis |
| 운영 진입점 | `backtest_research_run.py`, `backtest_report_run.py` |
| AWS 위치 | Paper Daily Step 4, Step 5 |
| 상세 파일 문서 | `docs/source-file-catalog.md` |

## 2. 책임 경계

Research는 과거 구간을 시뮬레이션하고 그 결과를 분석·표현한다.
원천 데이터 수집, Daily 운영 판단과 실제 주문은 다른 계층의 책임이다.

### 2.1 Research가 담당하는 범위

| 영역 | 책임 |
|---|---|
| Strategy Profile | Version별 Config 선택과 Resolved Config 주입 |
| Backtest | 거래일 단위 포트폴리오 시뮬레이션 |
| Market | Common Market 판단을 Research adapter로 호출 |
| Buy Filter | Common Buy Candidate Filter 호출 |
| Sizing | 후보별 Position Allocation 계산 |
| Buy·Sell | Guard, Haircut과 Common Sell 판단 적용 |
| Position | 보유, 청산과 다음 거래일 이월 처리 |
| Persistence | Run, Daily, Daily Position, Trade Log와 Config·Identity 저장 |
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

## 3. Versioned Backtest Platform

Research는 고정된 Common 판단 Engine에 Version별 Strategy Profile을 주입한다.
전략 설정은 Common Default와 Profile Override를 병합한 Resolved Config로 확정된다.

### 3.1 Config 데이터 흐름

```text
Strategy Profile (RSCFG-0001.json)
  → Load       프로파일 JSON 로드
  → Resolve    Common Default + Profile Override 병합
  → Validate   Schema, 허용 Category·Key, Type과 Metadata 검증
  → Hash       Canonical JSON과 SHA-256 Config Hash 생성
  → Inject     Engine과 Adapter에 Resolved Config 명시적 주입
  → Persist    Run에 Config Snapshot·Hash·Version Identity 저장
```

| 단계 | 파일 |
|---|---|
| Load·Resolve·Snapshot | `strategy_profile_loader.py` |
| Schema·병합 검증 | `strategy_profile_schema.py` |
| Canonical JSON·Hash | `strategy_config_snapshot.py` |
| Version Identity | `research_version_identity.py` |
| Engine 주입 | `backtest_engine.py` |
| Run·Config 저장 | `backtest_run_store.py` |

### 3.2 Common Wheel 소비 구조

| 항목 | 현재 구조 |
|---|---|
| Common 포함 방식 | Common Source Directory Copy가 아니라 Wheel Package 설치 |
| 설치 대상 | `port_strategy_common-1.0.0-py3-none-any.whl` |
| Runtime Version Source | 실제 설치된 Distribution Metadata Version |
| Package Version 검증 | Profile 선언 Version과 설치 Version이 다르면 실행 차단 |
| Strategy Version 검증 | Runtime 값과 Profile 선언 값이 다르면 실행 차단 |
| Consumer 관계 | Decision과 Research가 동일 Common Package 계약을 소비 |

Common Package와 Research Source의 책임을 혼동하지 않는다.
Common은 판단 계약을 제공하고, Research는 Version별 Profile 선택과 주입을 담당한다.

### 3.3 Strategy Profile

`strategy_profiles/`는 Version별 Strategy Profile을 관리한다.
`strategy_config_version`이 Profile Identity이며, 각 Version은 별도 Strategy Config Identity다.

| Version | 성격 |
|---|---|
| `RSCFG-0001` | Baseline Strategy Profile (`status=BASELINE`) |
| `RSCFG-0002` | Challenger Strategy Profile (`status=CANDIDATE`) |

`RSCFG-0002`는 `RSCFG-0001`을 덮어쓰지 않고 새 Version으로 분리한 Challenger다.
두 Profile의 유일한 값 차이는 `market.aggressive_max_positions`이며, `RSCFG-0001`은 `4`, `RSCFG-0002`는 `6`이다.
나머지 Category 값은 동일하다.

| Config Category | 성격 |
|---|---|
| `metadata` | Profile·Version Metadata |
| `market` | Market Regime과 Exposure 기준 |
| `filter` | Buy Filter 기준 |
| `sizing` | Position Sizing 기준 |
| `buy_guard` | Buy Guard와 Haircut 기준 |
| `buy` | 매수 실행 관련 값 |
| `sell` | Sell 판단 기준 |
| `backtest_policy` | 재진입, Return Floor와 Risk-off 정책 |
| `metrics` | Risk-free Rate와 연간 거래일 |

Profile 검증 계약:

| 항목 | 기준 |
|---|---|
| 파일명·Version | Profile 파일명과 선언 `strategy_config_version` 일치 |
| Metadata | 필수 Metadata Key 존재와 비어있지 않은 값 검증 |
| Category | 허용 Category와 허용 Key만 허용 |
| Unknown Key | Category 또는 Metadata의 Unknown Key 차단 |
| Type·누락 | Type 오류와 Resolved Config Key 누락 차단 |
| 병합 | Common Default와 Profile Override를 병합해 완전한 Config 생성 |
| 미존재 Version | DB 연결과 Run 생성 전에 차단 |

Profile Status와 운영 승격 상태는 같은 의미가 아니다.
`RSCFG-0002`의 `status=CANDIDATE`는 운영 Champion 지정이나 자동 승격을 의미하지 않는다.
`RSCFG-0001`의 `status=BASELINE`도 운영 Champion 상태와 동일한 의미가 아니다.

### 3.4 Config 선택 CLI와 명시적 주입

`backtest_research_run.py`가 Profile을 선택하고 Resolved Config를 전체 실행 경로에 명시적으로 주입한다.

| CLI Option | 역할 |
|---|---|
| `--strategy-config-version` | 실행할 Strategy Profile Version, 기본값 `RSCFG-0001` |
| `--run-mode` | `BACKTEST` 또는 `CANDIDATE`, 기본값 `BACKTEST` |
| `--require-artifact-identity` | Source SHA·Image Digest 미주입 시 실행 차단 |
| `--backtest-start-date` | 백테스트 시작일 |
| `--backtest-end-date` | 백테스트 종료일, 생략 시 최신 거래일 |
| `--skip-extended-analysis` | 로컬 단기 검증에서 Extended Analysis 생략 |

주입 계약:

- 선택한 Profile을 Load하고 Resolved Config를 생성한다.
- Market, Filter, Sizing, Buy Guard, Buy Haircut과 Sell 흐름에 실제 Config를 전달한다.
- Engine과 Adapter는 Module Global Config나 숨은 Default에 의존하지 않는다.
- BUY Guard는 이전의 `config={}` 연결 대신 실제 Resolved `buy_guard` Config를 전달한다.

### 3.5 Version Identity

Run마다 아래 Version Identity를 분리해 저장하고, 재현 가능성을 확보한다.

| Identity | 기준 |
|---|---|
| Common Package Version | 설치된 `port-strategy-common` Distribution Version |
| Common Strategy Version | 설치된 Common Wheel이 제공하는 Strategy Version 상수 |
| Research Engine Version | Research 저장소 상수 (`research_engine_version.py`) |
| Strategy Config Version | 실행 Profile의 `RSCFG-` Version |
| Metrics Config Version | Resolved Config Metadata의 `RMETRICS-` Version |
| Run Identity | Run ID |
| Source SHA | 배포 Source 환경변수 |
| Image Digest | 배포 Image 환경변수 |

구분 기준:

- Strategy Config Version과 Research Engine Version은 같은 값이 아니다.
- Common Package Version과 Common Strategy Version도 서로 다른 값이다.
- Metrics Config Version은 Strategy Config Identity와 별도로 기록한다.
- Source SHA와 Image Digest는 서로 다른 식별자다.

### 3.6 Config Snapshot·Hash와 Input Snapshot

Config Identity와 Input Data Identity는 서로 다른 개념이다.

| 항목 | Config Snapshot·Hash | Input Snapshot |
|---|---|---|
| 대상 | 실행에 사용한 Resolved Config | 실제 소비한 입력 데이터 |
| Canonical | Config Canonical JSON | 입력 Canonical JSON |
| Hash | SHA-256 Config Hash | SHA-256 Input Snapshot Hash |
| Run 저장 | `config_snapshot`, `config_hash` | `input_snapshot_hash`, `input_snapshot_manifest` |
| 변동성 | 동일 Profile은 동일 Config Hash | 원천 데이터 갱신 시 Hash 변동 가능 |

Config Snapshot 흐름:

- Common Default와 Profile Override를 병합한 전체 Resolved Config를 생성한다.
- Canonical JSON과 SHA-256 Config Hash를 생성한다.
- Run에 Strategy Config Version, Config Snapshot과 Flatten Config KV(`strategy_run_input`)를 저장한다.
- Trade Log는 Run ID와 Config Identity(Version·Hash)로 같은 Snapshot을 참조한다.
- Global Common Config Snapshot이 아니라 실제 실행 Config가 Canonical Source다.
- Secret은 Config Snapshot과 Hash 입력에 포함하지 않는다.

Input Snapshot 흐름:

- 실행 입력 범위와 Manifest를 저장한다.
- Input Snapshot Hash와 Snapshot Status를 저장한다.
- 실행 기간과 입력 Data Identity를 연결한다.
- 동일 기간이라도 원천 데이터가 갱신되면 Input Snapshot Hash가 달라질 수 있다.

### 3.7 Run Mode와 Candidate

Research 실행은 `BACKTEST`와 `CANDIDATE` Run Mode를 구분한다.

| 항목 | 기준 |
|---|---|
| 운영 Run | `BACKTEST` Run Mode |
| Candidate Run | `CANDIDATE` Run Mode |
| 조회 분리 | Run Mode와 Identity로 운영 Run과 Candidate Run을 구분 |
| Scheduler 연결 | Candidate 실행을 운영 Scheduler에 자동 연결하지 않음 |
| 자동 승격 | Candidate는 자동 승격하지 않음 |
| 실패 저장 | Candidate 실패 Run도 실패 상태와 Artifact Identity 저장 |
| RDS 공유 | 같은 RDS를 사용할 수 있으나 Run Mode와 Identity로 구분 |

Candidate는 전략 성과의 자동 승인자가 아니라 배포 Artifact와 실행 계약 검증 경로다.
Candidate 실행은 `--run-mode CANDIDATE`와 선택된 `--strategy-config-version`으로 수행한다.
Candidate Run은 `strategy_backtest_run`에 Run Mode·Version Identity와 함께 저장된다.
Candidate 성공은 Challenger 검증 완료를 의미하며 Champion 자동 Promotion을 의미하지 않는다.

`RSCFG-0002` Challenger는 Candidate 경로로 실행해 검증했고, Candidate Run이 DB에 저장된 상태다.
`RSCFG-0001`과 `RSCFG-0002`는 Version별 Research 결과로 각각 조회할 수 있다.

Champion–Challenger 책임은 아래처럼 분리한다.

| 주체 | 책임 |
|---|---|
| DevOps 자동화 | Candidate 생성·실행·검증(Challenger 확정)까지 |
| Research 담당자 | 여러 Challenger 성과 비교와 Champion 선택 판단 |
| View | Version 조회와 Champion·Challenger 비교·선택 Interface |

View는 전략의 우열을 자동 판단하지 않는다.
Champion 선택 의사결정 주체는 Research 담당자이며, View는 그 결정을 수행하는 Interface다.
실제 View 운영 승격 기능 구현은 이 문서 작업 범위가 아니다.

### 3.8 Artifact Identity

| 항목 | 기준 |
|---|---|
| Source SHA | 40자리 hex 형식 검증 |
| Image Digest | `sha256:` 64자리 hex 형식 검증 |
| Artifact Identity Status | `UNRESOLVED`, `COMPLETE` 또는 형식 오류 차단 |
| Digest 고정 | 운영·Candidate 모두 Digest 기반 고정 Image 사용 |
| 필수 검증 | `--require-artifact-identity`로 완전한 Identity 강제 |
| 구조 공유 | Candidate와 운영 Run 모두 동일한 Artifact Identity 구조 사용 |

배포 Artifact Identity가 불완전한 상태(`UNRESOLVED`)와 완전한 상태(`COMPLETE`)를 구분한다.

### 3.9 재현성 검증 기준

동일 Version 재실행 시 아래를 구분해 검증한다.

| 대상 | 기준 |
|---|---|
| Config와 Artifact Identity | 완전 일치 |
| Backtest 결과와 Trade Log | 완전 일치 |
| Input Snapshot Manifest | 일치 |
| Input Snapshot Hash | 원천 데이터 갱신으로 변동 가능 |
| 비교 제외 | Run ID와 생성·시작·종료 시각 |
| 수치 허용 오차 | `0.000000000001` |

Manifest와 결과가 동일하고 Hash 차이가 원천 데이터 갱신으로 설명되는 경우를 예외로 인정한다.

## 4. 전체 실행 흐름

```text
Strategy Profile + Common Wheel + Preprocessor Feature + Price + Universe
  → Backtest Research
  → Run · Daily · Daily Position · Trade Log · Config·Input Snapshot
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

## 5. Backtest Research

### 5.1 실행 흐름

```text
Profile Load · Resolve · Hash · Artifact Identity
  → Run 생성과 Config·Version Identity 저장
  → 거래일·Feature·가격·Universe 조회와 Input Snapshot 수집
  → Market Decision
  → 기존 Position 처리
  → Buy Candidate Filter
  → Guard와 Sizing
  → 신규 Position 생성
  → Daily Result와 Daily Position 저장
  → Trade Log 저장
  → Input Snapshot 확정
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
| Run·Daily·Config 저장 | `backtest_run_store.py` |
| Input Snapshot | `research_input_snapshot.py` |
| 성과 계산 | `backtest_metrics.py` |

### 5.2 Engine

`backtest_engine.py`는 거래일 단위 메인 루프를 조율한다.
`run_backtest`는 Resolved Config, Strategy Config Version과 Config Hash를 인자로 받아 전체 경로에 주입한다.

| 항목 | 역할 |
|---|---|
| 입력 | 거래일, Market·Stock Feature, 가격과 Universe |
| Config 검증 | 필수 Config Category 존재와 Config Hash 형식 확인 |
| Market | Research Market Adapter에 `market_config` 전달 |
| Position | 신규 매수보다 기존 Position을 먼저 처리 |
| Buy | Filter, Guard, Haircut과 Sizing에 실제 Config 전달 |
| Input Snapshot | 소비한 거래일·Feature·가격·Universe를 Builder에 기록 |
| 저장 | Daily Result와 Daily Position Snapshot |

가격 기준, 거래일 정렬, 기존 Position 처리 순서와 신규 매수 시점은 백테스트 결과를 바꾸는 핵심 계약이다.

### 5.3 Loader

`backtest_loader.py`는 Backtest 입력을 읽는 SQL helper다.

| 입력 | 사용 목적 |
|---|---|
| `pre_total_market_daily_feature` | Market 판단 |
| `pre_total_stock_daily_feature` | Filter, Sizing과 Sell 판단 |
| `interest_price_raw` | 가격과 수익률 계산 |
| `stock_universe` | Backtest 대상 Universe |

거래일, Feature 기준일과 다음 거래일 가격을 구분해야 한다.
미래 가격이나 미래 Feature가 현재 판단에 포함되면 Look-ahead Bias가 발생한다.

### 5.4 Research Adapter

Research 내부 adapter는 `port_strategy_common` 계약을 Backtest 흐름에 연결하며, Resolved Config를 명시적으로 받는다.

| 파일 | Common 호출 |
|---|---|
| `research_backtest_market_adapter.py` | `common_decide_market` |
| `research_backtest_filter_adapter.py` | `common_filter_buy_candidates` |
| `research_backtest_sizing_adapter.py` | `common_allocate_positions` |

Adapter는 자체 DB 접근이나 외부 API 호출을 담당하지 않는다.
Common 결과를 Research row와 객체 형식으로 변환하는 경계다.

### 5.5 Buy Logic

`backtest_buy_logic.py`는 신규 Position 진입을 담당한다.

| 항목 | 처리 |
|---|---|
| 후보 | Filter 통과 종목 |
| Allocation | Research Sizing Adapter에 `sizing_config` 전달 |
| Guard | Common Buy Guard에 `buy_guard_config` 전달 |
| Haircut | Common Backtest Buy Size Haircut에 `buy_guard_config` 전달 |
| Metadata | Entry Reason과 사후 분석용 정보 |
| 당일 Stop | 조건에 따라 Trade Log 생성 가능 |

Available Cash, Exposure, Max Positions, 최소 수량과 반올림 기준은 결과에 직접 영향을 준다.
BUY Guard와 Haircut은 실제 Resolved `buy_guard` Config를 사용한다.

### 5.6 Sell Logic과 Position Manager

`backtest_sell_logic.py`는 Common Sell 판단을 감싼 wrapper다.

`backtest_position_manager.py`는 기존 Position을 처리하며 `sell_config`와 `backtest_policy`를 전달받는다.

| 처리 | 의미 |
|---|---|
| 일별 수익률 | 보유 Position의 당일 변화 계산 |
| 장중 Stop | 기존 Position의 긴급 청산 조건 |
| 일반 Sell | Common Sell Decision |
| 청산 | Trade Log 생성 |
| 이월 | 살아남은 Position을 다음 거래일로 전달 |

Stop, 보유 기간과 Sell Reason 우선순위는 Daily Decision과 공유하는 Common 계약에 영향을 받는다.

### 5.7 Metrics

`backtest_metrics.py`는 DataFrame 기반 성과 계산을 제공하며 Resolved `metrics` Config를 인자로 받는다.

| 지표 | 의미 |
|---|---|
| MDD | 최대 낙폭 |
| Sharpe Ratio | 위험 대비 수익률 |

Risk-free Rate와 연간 거래일 수는 Profile `metrics` Config에서 전달된다.
빈 데이터, 0분모와 표본 수 부족 처리는 실제 코드 기준으로 확인해야 한다.

## 6. 입력 데이터

| 입력 | 역할 |
|---|---|
| Market Total Feature | 시장 상태와 허용 노출 판단 |
| Stock Total Feature | 종목 Filter, Sizing과 Sell 판단 |
| Price Raw | 가격, 수익률과 체결 가정 |
| Stock Universe | 대상 종목과 활성 조건 |
| Strategy Profile | Version별 Resolved Config 재현 |
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

## 7. 출력 데이터

### 7.1 Backtest 저장

| 출력 | 의미 |
|---|---|
| `strategy_backtest_run` | Run 메타데이터, Config Snapshot, Version Identity와 상태 |
| `strategy_backtest_daily` | 거래일별 포트폴리오 성과 |
| `strategy_backtest_daily_position` | 거래일별 보유 Position Snapshot |
| `strategy_trade_log` | 완료 거래 상세, Run ID와 Config Identity 참조 |
| `strategy_run_input` | Run 입력값과 Flatten Config KV |

`strategy_backtest_run`은 Config Snapshot과 함께 Strategy Config Version, Metrics Config Version,
Source SHA, Image Digest, Artifact Identity Status, Config Hash, Input Snapshot Hash·Status·Manifest를 저장한다.

### 7.2 Analysis 저장

| 출력 | 의미 |
|---|---|
| Basic Analysis | Run의 기본 집계 결과 |
| Extended Analysis | Threshold, Bucket과 진단 목적 확장 결과 |
| `strategy_backtest_*_analysis` | Run ID 기준 분석 테이블 계열 |

### 7.3 Report 파일

| 리포트 | 의미 |
|---|---|
| Summary | Run 성과와 주요 지표 요약 |
| Buy·Sell | 일자별 매수·매도 내역 |
| Trade Detail | 거래별 상세 정보 |
| Recommendation | 연구 관점 추천·진단 |

Recommendation은 연구 진단이다.
실제 투자 권고, 주문 지시 또는 미래 성과 보장으로 해석하지 않는다.

## 8. 저장과 재실행

| 주의사항 | 확인 내용 |
|---|---|
| Run 생성 | 동일 입력이 신규 Run인지 기존 Run 갱신인지 |
| Config 저장 | Run당 Config Snapshot 1회, Trade Log는 Identity 참조 |
| Daily 저장 | 거래일별 Unique Key와 Upsert |
| Position 저장 | Run·Trade Date·Ticker 기준 |
| Trade Log | 완료 거래와 Metadata 계약 |
| 상태 전환 | Started, Completed와 Failed 처리 |
| Input Snapshot | Manifest·Hash·Status 확정 시점 |
| Transaction | Run, Daily, Position과 Trade 저장 경계 |
| Partial Success | 일부 저장 후 Run만 성공 처리되는지 |
| Re-run | 기존 Analysis·Report와의 연결 |
| Snapshot | Config와 Input 재현 가능성 |

실제 Unique Key와 Conflict Target은 SQL 또는 DDL을 직접 확인해야 한다.
문서만으로 추정하지 않는다.

## 9. Analysis

### 9.1 Basic Analysis

`backtest_analysis_basic.py`는 저장된 Run 결과를 기본 집계 형태로 변환해 저장한다.
표준 Backtest Run 진입점에서는 이 Basic Analysis 호출이 주석 처리되어 자동 실행되지 않는다.

| 항목 | 의미 |
|---|---|
| 기준 | Run ID |
| 입력 | Run, Daily, Position과 Trade Log |
| 출력 | 기본 Analysis Row |
| 위험 | DB Insert 가능 |

### 9.2 Extended Analysis

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

### 9.3 분석 해석

| 상태 | 구분 |
|---|---|
| 거래 0건 | 정상 Run이지만 거래가 없는 결과일 수 있음 |
| 입력 누락 | 분석에 필요한 저장 데이터가 없는 상태 |
| 빈 DataFrame | 계산 대상이 없는 상태 |
| 0분모 | 비율 계산 불가 |
| `NULL` | 미산출 또는 누락 |
| 무한대 | 분모 또는 수치 안정성 문제 가능 |

분석 결과를 실제 운용 성과와 동일하게 표현하지 않는다.

## 10. Report

### 10.1 Report 구성

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

### 10.2 Run 선택

| 방식 | 의미 |
|---|---|
| 최신 Run 자동 선택 | `get_latest_run_id`가 `started_at DESC` 최신 Run 선택 |
| 지정 Run ID | 각 report 함수는 run_id 인자를 받지만 진입점 CLI 옵션은 없음 |
| Run 없음 | Report 생성 불가 |

최신 Run은 완료 여부와 무관하게 `started_at` 기준으로 선택한다.

### 10.3 출력 파일

| 항목 | 현재 문서 기준 |
|---|---|
| 기본 출력 | 현재 작업 디렉터리 |
| AWS Batch 출력 | `/tmp/portfolio-reports` |
| 형식 | Text File |
| 덮어쓰기 | 파일명 생성 규칙 확인 필요 |
| S3 | Wrapper 환경변수가 설정된 경우 선택적 업로드 |

Report 생성 성공과 S3 업로드 성공은 별도 상태다.

## 11. Block·Watch·Exception Buy 연구

| 파일 | 현재 분류 |
|---|---|
| `block_watch_analysis_run.py` | Watch Candidate 분석 |
| `block_watch_backtest_run.py` | BLOCK Watch Backtest |
| `block_exception_buy_engine_run.py` | Exception Buy Engine 연구 |
| `block_exception_buy_backtest_run.py` | Exception Buy Backtest |

이 계열은 Daily 운영 파이프라인의 정식 단계가 아닌 연구·보류 후보로 관리한다.
사용 흔적과 운영 연결이 확인되지 않았다는 이유만으로 삭제하지 않는다.

## 12. `port_strategy_common` 관계

Research는 핵심 판단 로직을 Common에서 재사용한다.

| 영역 | Common 계약 |
|---|---|
| Config | Strategy, Engine과 판단 설정 Default |
| Market | Market Context와 Decision |
| Filter | Buy Candidate Filter |
| Sizing | Position Allocation |
| Guard | Buy Guard |
| Haircut | Backtest Buy Size Haircut |
| Sell | Backtest Sell Decision |
| Metrics | Risk-free Rate와 Trading Days Default |

Public 함수명, dataclass 필드, enum, config key와 reason 문자열은 다른 서비스와 연결될 수 있다.

### 12.1 StrategyDecision과의 관계

| 항목 | 관계 |
|---|---|
| 런타임 Import | 없음 |
| 공유 대상 | `port_strategy_common` 계약 |
| Research Adapter | Research 저장소 내부 |
| Decision Adapter | StrategyDecision 저장소 내부 |
| Daily 운영 판단 | StrategyDecision 책임 |
| Backtest 판단 | Research 책임 |

Decision은 Research Runtime 의존 대상이 아니라 동일 Common 계약의 별도 소비자다.
Research 변경만으로 Common 또는 Decision 계약을 임의 변경하지 않는다.

## 13. AWS Paper Daily 위치

Research는 AWS Paper Daily에서 Backtest와 Report 실행 단위로 호출된다.

| Daily 단계 | Research 역할 |
|---|---|
| Step 4 · Backtest Research | Feature를 읽어 Backtest와 분석 결과 생성 |
| Step 5 · Backtest Report | 저장된 Run 기준 Text Report 생성 |

### 13.1 Step 4

| 항목 | 값 |
|---|---|
| 진입점 | `backtest_research_run.py` |
| 입력 | Feature, Price, Universe, Strategy Profile과 기간 |
| 출력 | Run, Daily, Position, Trade와 Analysis |
| DB 영향 | DDL·DML과 Commit 가능 |
| 직접 하지 않는 일 | Daily Signal, Execution Plan과 Broker 주문 |

### 13.2 Step 5

| 항목 | 값 |
|---|---|
| 진입점 | `backtest_report_run.py` |
| 입력 | 최신 또는 지정 Run ID |
| 출력 | Summary, Buy·Sell, Trade Detail과 Recommendation |
| 파일 영향 | Local Text File 생성 |
| 선택적 영향 | AWS Batch Wrapper를 통한 S3 업로드 |

Scheduler와 Step Functions는 실행 orchestration을 담당한다.
Research 저장소의 entrypoint 존재는 현재 AWS 실행 상태나 배포 완료 증거가 아니다.

## 14. Research CI와 배포 경로 계약

Research 전용 DevOps는 GitHub Actions·OIDC와 CodeBuild 기반이며,
Build/Test/Artifact 책임과 Release Control 책임을 분리한다.
아래는 Research가 알아야 하는 실행 계약 수준이며, 세부 GitHub Actions 분기, IAM Policy,
AWS CLI, Job Definition Revision 변경 절차와 Step Functions 갱신 절차는 `port-devops` 문서 책임이다.

### 14.1 현재 배포 경로 AS-IS

| 항목 | 현재 계약 |
|---|---|
| `main` Push | Build/Test 검증 경로 (Image Publish·Candidate·Operating 미수행) |
| Release 경로 분리 | Strategy Logic 변경 여부에 따라 Candidate 또는 Operating Release로 분리 |
| Candidate 경로 | 신규 Challenger `RSCFG` Version을 `-candidate` Family로 검증 |
| Operating 경로 | 검증된 Artifact를 운영 Family로 배포 (Strategy Config Version 유지) |
| 공통 | Candidate와 Operating은 서로 다른 배포 경로 |

- `main` Push는 Build/Test 검증까지만 수행한다.
- Candidate와 Operating Release는 서로 다른 경로이며 같은 실행으로 묶지 않는다.
- Candidate는 자동 Champion Promotion이 아니다.
- Research 실행 Artifact 배포와 Strategy 성과 승격은 별도 절차다.

### 14.2 책임 분리

| 주체 | 책임 |
|---|---|
| GitHub Actions | OIDC 인증, CodeBuild 실행·상태 확인과 Release Control |
| CodeBuild | Compile, Test, Config·Version Contract, Container Build·Smoke와 조건부 ECR Artifact 생성 |
| CodeBuild Role | Build, Logs와 Research ECR 범위 |
| GitHub OIDC Role | Research CodeBuild 시작·조회와 Release Control 범위 |

Build Role에 운영 Batch 배포, Step Functions와 운영 DB 권한을 부여하지 않는다.
Candidate·Operating Release는 검증된 Digest 고정 Image를 사용하고, Mutable `latest` 의존을 만들지 않는다.
세부 권한과 배포 절차는 `port-devops` 문서에서 관리하고 이 문서에 복제하지 않는다.

## 15. Candidate와 운영 경로 계약

Candidate 전용 Job Definition Family는 운영 Family와 분리한다.

| 항목 | 계약 |
|---|---|
| 운영 Family | 운영 Backtest Job Definition Family |
| Candidate Family | 운영과 분리된 `-candidate` Family |
| Artifact | Candidate·운영 모두 검증된 Digest 고정 Image와 Source SHA·Image Digest 주입 |
| Candidate 실행 | `--run-mode CANDIDATE`, 선택 `--strategy-config-version`, `--require-artifact-identity` |
| Candidate Runtime | Fargate, VCPU 1, Memory 4096 MiB |
| Operating Release | Strategy Config Version을 유지한 채 검증된 Artifact만 교체 |

Candidate 검증에서는 Job Status·Container Exit Code와 Run·Config Hash·Metrics·Input Snapshot 저장,
의도적 실패 Candidate의 실패 저장 계약을 확인한다.

Candidate 성공 후에도 Operating Job Definition, Step Functions 참조와 Champion은 자동 변경하지 않는다.
Job Definition Revision 등록과 Step Functions 참조 전환의 실제 절차는 `port-devops` 문서 책임이다.

## 16. 운영 승격·Rollback 과거 이력

아래는 운영자가 AWS에서 수행한 과거 수동 승격·검증 결과를 문서화한 운영 사실이며,
Research 저장소 코드만으로 확정되는 값이 아니다.
이 이력은 과거 수동 검증 사실로 보존하며, 현재 자동화 AS-IS(14.1)와 구분한다.

| 항목 | 값 |
|---|---|
| 당시 운영 Champion | Research Job Definition Revision 7 |
| 당시 운영 Resource | VCPU 1, Memory 4096MiB |
| 당시 Rollback 대상 | Revision 5 (ACTIVE 유지) |
| Revision 6 | OOM 실패 Revision, 증적으로 보존 |
| 당시 운영 Run Mode | `BACKTEST` |
| 당시 운영 Strategy Config Version | `RSCFG-0001` |

과거 승격·Rollback 요약:

- Champion Revision 5에서 검증된 Artifact로 Revision 6을 등록하고 운영 Step 4 참조를 5→6으로 승격했다.
- Revision 6은 VCPU 1·Memory 2048MiB에서 Exit Code 137 Fargate OutOfMemoryError로 실패했다(로직·Config 오류가 아닌 Memory 부족).
- Revision 5로 Rollback한 뒤, Memory만 4096MiB로 확장한 Revision 7을 단독 검증하고 운영 Step 4로 최종 승격했다.

이 이력은 과거 수동 검증 사실이며, 현재 `main` Push는 이런 운영 Champion 변경을 자동으로 수행하지 않는다.
Strategy 성과 평가와 DevOps Artifact 승격 책임은 분리한다.

## 17. 컨테이너와 주요 DevOps 파일

### 17.1 Dockerfile

| 항목 | 현재 소스 기준 |
|---|---|
| Base Image | `python:3.13-slim` |
| Dependency | `requirements.txt` |
| Common | `.devops/packages/port_strategy_common-1.0.0-py3-none-any.whl`를 `--no-deps` 설치 |
| Version 검증 | 설치 후 `1.0.0` Assert |
| 포함 대상 | 루트 `*.py`와 `strategy_profiles/` |
| 기본 CMD | `backtest_research_run.py` Compile 확인 |
| 실제 Research 실행 | 외부 Command Override |

기본 CMD는 실제 Backtest 실행이 아니라 Compile 확인이다.
Common Source Directory를 직접 Copy하지 않고 Wheel Package를 설치한다.

### 17.2 주요 신규 DevOps 파일

| 파일 | 역할 |
|---|---|
| `Dockerfile` | Common Wheel 설치와 Compile 기본 CMD |
| `.dockerignore` | 문서·DevOps Script·비런타임 파일 Build Context 제외 |
| `.devops/codebuild/buildspec.yml` | Build/Test/Container/ECR Artifact 생성 (Job Definition 등록 책임 없음) |
| `.devops/scripts/verify-candidate-contract.py` | Candidate 정적 계약 검증 |
| `.devops/scripts/container-smoke.py` | Network 차단 Container Smoke Test |
| `.devops/scripts/generate-strategy-config.py` | 최신 Profile에서 다음 `RSCFG` Challenger(`status=CANDIDATE`) 생성 |
| `.devops/scripts/deploy-candidate.sh` | Candidate Family 신규 Revision 등록과 AWS Batch Candidate 실행·검증 |
| `.devops/scripts/deploy-operating.sh` | 운영 Family Revision 등록과 운영 Step 4 참조 전환 |
| `.github/workflows/research-codebuild.yml` | `main` Push Build/Test와 Candidate·Operating Release 경로 분기 |
| `strategy_profiles/README.md` | Strategy Profile 관리 기준 |
| `strategy_profiles/RSCFG-0001.json` | Baseline Strategy Profile (`status=BASELINE`) |
| `strategy_profiles/RSCFG-0002.json` | Challenger Strategy Profile (`status=CANDIDATE`) |

위 DevOps 파일의 IAM, ARN, Job Definition Revision과 Step Functions 운영 절차 상세는 `port-devops` 문서 책임이다.

### 17.3 AWS Batch Report Wrapper

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

## 18. 실행 방법

내부 import는 `port_strategy_research` package 경로를 기준으로 한다.
실행이 필요한 경우 파일 경로 직접 실행보다 `python -m` 형식을 사용한다.

아래 명령은 형식 설명용 예시다.
실제 DB 쓰기, 파일 생성과 S3 업로드가 발생할 수 있으므로 문서 작업 중에는 실행하지 않는다.

```powershell
python -m port_strategy_research.backtest_research_run --strategy-config-version RSCFG-0001

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

## 19. DB 설정

DB 연결은 `db_config.py`의 `get_db_config()`를 사용한다.

### 19.1 환경변수

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
Artifact Identity 환경변수 `RESEARCH_SOURCE_SHA`, `RESEARCH_IMAGE_DIGEST`는 배포 Runtime에서 주입한다.

### 19.2 Search Path

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

## 20. 외부 의존성

| 의존성 | 용도 |
|---|---|
| Python | Runtime |
| PostgreSQL | Feature 조회와 Research 결과 저장 |
| `pandas` | Table과 성과 계산 |
| `numpy` | 수치 계산 |
| `psycopg2` | PostgreSQL 연결 |
| `psycopg2-binary` | 설치 Package |
| `boto3` | AWS Batch Wrapper의 S3 업로드 |
| `port_strategy_common` | Wheel `1.0.0` 고정 설치, 공통 판단과 설정 |

Pinned Version은 `requirements.txt`에서 관리한다.
README에 버전 값을 중복 기록하지 않는다.

## 21. 상태와 계산 주의사항

| 주의사항 | 확인 내용 |
|---|---|
| Look-ahead | 미래 Feature·Price 사용 금지 |
| Trade Order | 기존 Position 처리와 신규 Buy 순서 |
| Missing | 누락값과 실제 0 구분 |
| Duplicate | Ticker·Date Join Cardinality |
| Cash | Available Cash와 Position Allocation |
| Cost | Fee, Tax와 Slippage 구현 여부 |
| Stop | 당일 Stop과 일반 Sell 우선순위 |
| Config Inject | Module Global이 아닌 Resolved Config 사용 |
| Run Status | Partial Save 후 Completed 처리 여부 |
| Analysis | Delete 후 Insert 실패 가능성 |
| Report | 최신 Run 선택과 파일 덮어쓰기 |
| S3 | 일부 업로드 실패와 전체 성공 구분 |
| Reproducibility | Config·Input Snapshot과 Artifact Identity 보존 |

현재 구현이 모든 실패와 수치 경계를 자동 처리한다고 README만으로 단정하지 않는다.
코드 변경이나 장애 분석에서는 EntryPoint, Store와 Transaction을 직접 확인해야 한다.

## 22. 문서 구조

| 문서 | 역할 |
|---|---|
| `AGENTS.md` | Kiro 작업 범위, 안전, 데이터 계약과 검증 규칙 |
| `README.md` | 현재 Research 구조, 실행·설정과 운영 AS-IS |
| `CHANGELOG.md` | 주요 변경 이력과 당시 사실 |
| `docs/source-file-catalog.md` | 파일 책임, 입출력과 변경 영향 |

파일 책임, Entrypoint, DB 접근, Analysis, Report, AWS Wrapper와 Dependency가 바뀌면
README와 `docs/source-file-catalog.md`를 함께 확인한다.

날짜별 `docs/worklog/*.md`는 새로 만들지 않는다.
과거 생성 사실은 CHANGELOG의 당시 이력으로만 보존한다.

## 23. 안전한 검증 범위

문서만 수정한 경우에는 변경 파일과 Diff 범위만 확인한다.

```powershell
git status --short
git diff --stat
git diff --check
```

코드 수정 시에도 실제 Backtest, Analysis, Report, DB 쓰기, AWS, S3와 주문 실행이 없는 검증을 우선한다.

| 검증 | 안전한 방식 |
|---|---|
| Profile·Schema | Resolved Config 병합과 Unknown Key 단위 검증 |
| Config Snapshot | Canonical JSON과 Hash 단위 검증 |
| Adapter | 단위 입력·출력 비교 |
| Metrics | 작은 DataFrame Fixture |
| Loader | DB Mock |
| Run Store | Connection·Cursor Mock |
| Report | 임시 디렉터리 |
| AWS Wrapper | 환경변수와 boto3 Mock |

운영 실행이 필요한 검증은 자동 수행하지 않고 남은 검증으로 보고한다.
