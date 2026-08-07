# AGENTS.md - port_strategy_research

## 0. 최우선 문서 가독성 규칙

모든 작업은 정확성과 함께 읽기 쉬운 결과를 우선한다.

| 항목 | 규칙 |
|---|---|
| 기본 표 | 새로 만드는 독립 요약 표는 기본 2컬럼으로 작성한다. |
| 권장 컬럼 | `항목 / 값`, `파일 / 역할`, `단계 / 책임`, `위험 / 영향`을 우선한다. |
| 기존 표 | 기존 표에 행을 추가할 때는 기존 컬럼 구조를 유지한다. |
| 긴 셀 | 한 셀에는 핵심 사실 1~2개만 넣고, 3개 이상이면 여러 행이나 상세 문서로 분리한다. |
| 길이 제한 | 표 셀 300자, 일반 Markdown 한 줄 500자를 넘기지 않는다. |
| 반복 금지 | 같은 설명을 README, CHANGELOG와 source catalog에 장문으로 반복하지 않는다. |
| 사실 구분 | 현재 구현, 설계 원칙, 외부 운영 사실과 미검증 추정을 구분한다. |
| 원문 제한 | raw log, 전체 SQL, 전체 DB 결과, secret과 운영 식별자 원문을 문서에 넣지 않는다. |
| 인코딩 | 한글 Markdown은 UTF-8 No BOM으로 저장한다. |

문서 역할은 아래처럼 분리한다.

| 문서 | 역할 |
|---|---|
| `AGENTS.md` | Kiro 작업 범위, 안전, 데이터 계약과 검증 규칙 |
| `README.md` | 현재 Research 구조, 흐름, 설정과 운영 AS-IS |
| `CHANGELOG.md` | 실제 기능·구조·문서 기준 변경 이력 |
| `docs/source-file-catalog.md` | 운영상 중요한 파일 책임, 입출력과 변경 영향 |

## 1. 적용 범위와 우선순위

- 이 파일은 `port_strategy_research` 전용 최우선 작업 규칙이다.
- 이 저장소 작업에서는 다른 마이크로서비스의 `AGENTS.md`를 작업 기준으로 사용하지 않는다.
- Workspace 공통 안전·작업 방식은 `.kiro/AGENTS.md` 최신 규칙을 따른다.
- Research 책임·데이터 계약은 이 파일의 Research 전용 규칙을 우선한다.
- 사용자의 최신 명시 요청이 가장 높은 작업 지시다.
- `.kiro/AGENTS.md`와 이 파일이 직접 충돌하면 더 제한적이고 안전한 규칙을 적용한다.
- 현재 `port_strategy_research` 루트와 하위 파일만 직접 수정한다.
- 루트 밖 파일은 계약 확인을 위한 read-only 참고만 허용한다.
- 사용자가 지정한 대상 파일이 있으면 그 파일만 수정한다.
- 전체 workspace 전수 스캔, sub-agent, orchestrator와 신규 scanner 생성은 금지한다.
- 변경은 작고 검증 가능한 범위로 유지한다.
- 문서 작업 요청에서는 Python, Dockerfile, requirements와 운영 wrapper를 수정하지 않는다.

## 2. 서비스 책임

이 저장소는 전처리 feature와 가격·universe 데이터를 읽어 백테스트, 분석과 리포트를 생성하는 Research 계층이다.

현재 Research는 고정된 Common 판단 Engine에 Version별 Strategy Profile을 선택·주입하는
`Versioned Backtest Platform`이다. Common은 판단 함수와 기본 계약을 제공하고,
Research는 Version별 Strategy Profile을 선택해 전체 Backtest Run에 명시적으로 주입한다.
Research 실행 Artifact 배포와 Strategy 운영 성과 승격은 서로 다른 절차다.

| 영역 | Research 책임 |
|---|---|
| Strategy Profile | Version별 Config 선택과 Resolved Config 명시적 주입 |
| Backtest | 거래일 단위 포트폴리오 시뮬레이션 |
| Market | Common market 판단을 Research adapter로 호출 |
| Buy Filter | Common buy candidate filter를 Research adapter로 호출 |
| Sizing | Common position allocation을 Research adapter로 호출 |
| Buy·Sell | Guard, haircut과 sell 판단을 backtest 흐름에 적용 |
| Position | 보유·청산·이월 포지션 처리 |
| Persistence | Run, Daily, Daily Position과 Trade Log 저장 |
| Analysis | 기본·확장 분석 테이블 생성 또는 갱신 |
| Report | Summary, Buy·Sell, Trade Detail과 Recommendation 텍스트 생성 |
| Research 후보 | Block Watch와 Exception Buy 시나리오 연구 |

Research가 직접 담당하지 않는 범위는 아래와 같다.

| 영역 | 담당 계층 |
|---|---|
| 외부 데이터 수집 | Crawler |
| raw 전처리와 total feature 생성 | Preprocessor |
| Daily BUY와 HOLD·SELL·SKIP 운영 판단 | StrategyDecision |
| Execution Plan과 주문 요청 구성 | StrategyExecution |
| Broker 주문·체결·잔고·보유 동기화 | MarketConnector |
| 상태 조회와 승인 UI | View |
| 전체 Batch orchestration | Scheduler와 Step Functions |
| 이미지 build, ECR push와 인프라 등록 | 배포 파이프라인 |

Research 결과는 연구·검증 산출물이다. Daily Signal, Execution Plan과 실제 주문을 생성하는 운영 계층으로 표현하지 않는다.

## 3. 핵심 실행 흐름

### 3.1 Backtest Research

| 파일 | 역할 |
|---|---|
| `backtest_research_run.py` | Backtest Run 전체 orchestration |
| `backtest_engine.py` | 거래일 단위 메인 루프 |
| `backtest_loader.py` | Feature, 가격과 universe 조회 |
| `research_backtest_market_adapter.py` | Common market adapter |
| `research_backtest_filter_adapter.py` | Common buy filter adapter |
| `research_backtest_sizing_adapter.py` | Common sizing adapter |
| `backtest_buy_logic.py` | 신규 진입, guard와 haircut 처리 |
| `backtest_sell_logic.py` | Common sell 판단 wrapper |
| `backtest_position_manager.py` | 보유, 청산과 이월 처리 |
| `backtest_trade_log.py` | 완료 거래 저장 |
| `backtest_run_store.py` | Run, Daily와 Daily Position 저장 |
| `backtest_metrics.py` | MDD와 Sharpe 등 성과 계산 |

### 3.2 Analysis

| 파일 | 역할 |
|---|---|
| `backtest_analysis_basic.py` | 기본 분석 row 생성·저장 |
| `analysis_extended.py` | Run 기준 확장 분석 테이블 재생성 |
| `run_extended_analysis.py` | 확장 분석 실행 진입점 |

### 3.3 Report

| 파일 | 역할 |
|---|---|
| `backtest_report_run.py` | 전체 리포트 생성 orchestration |
| `report_data_loader.py` | 저장된 Run·Daily·Position·Trade·Analysis 조회 |
| `report_formatter.py` | Label, 비율, 입력과 사유 포맷 |
| `report_summary.py` | Summary 리포트 |
| `report_buy_sell.py` | 일자별 Buy·Sell 리포트 |
| `report_trade_detail.py` | 거래 상세 리포트 |
| `report_recommendation.py` | 추천·진단 리포트 |
| `aws_batch_backtest_report_wrapper.py` | AWS Batch 환경변수 매핑, 리포트 실행과 선택적 S3 업로드 |

### 3.4 Block·Watch·Exception Buy 연구

| 파일 | 취급 원칙 |
|---|---|
| `block_watch_analysis_run.py` | Watch 후보 분석·갱신 가능성이 있는 연구 진입점 |
| `block_watch_backtest_run.py` | BLOCK Watch backtest 후보 |
| `block_exception_buy_engine_run.py` | Exception Buy 연구 엔진 후보 |
| `block_exception_buy_backtest_run.py` | Exception Buy backtest 후보 |

위 파일들은 daily 운영 파이프라인의 정식 단계가 아니라 연구·보류 계열로 취급한다. 실제 import, DB 쓰기와 호출 증거를 확인하기 전에는 운영 기능으로 확정하지 않는다.

## 4. Common과 Decision 관계

Research는 내부 adapter를 통해 `port_strategy_common`을 직접 호출한다.

| 영역 | Research 호출 |
|---|---|
| Market | `common_decide_market` |
| Buy Filter | `common_filter_buy_candidates` |
| Sizing | `common_allocate_positions` |
| Buy Guard | Common buy guard |
| Haircut | Common backtest buy size haircut |
| Sell | `common_evaluate_backtest_sell` |
| Metrics 설정 | Risk-free rate와 연간 거래일 설정 |

- `port_strategy_decision`은 Research의 런타임 import 대상이 아니다.
- Research와 StrategyDecision은 동일한 `port_strategy_common` 계약을 공유하는 별도 소비자다.
- Decision은 Research Runtime 의존 대상이 아니라 동일 Common 계약의 별도 소비자다.
- Research adapter를 Decision adapter와 동일 파일 또는 동일 runtime 의존으로 합치지 않는다.
- Common 함수명, import path, dataclass 필드, enum, config key와 reason 문자열을 명시 요청 없이 변경하지 않는다.
- Common mapping 변경은 Research 결과와 Daily Decision 호환성에 영향을 줄 수 있으므로 기능 변경으로 취급한다.

### 4.1 Common Wheel Version Pin과 Runtime Version 검증

- Research Image는 Common Source Directory를 직접 Copy하지 않고 `port_strategy_common` Wheel `1.0.0`을 고정 설치한다.
- 실제 설치된 Distribution Version을 Runtime Version Source로 사용한다.
- Profile 선언 Common Package Version과 실제 설치 Version이 다르면 실행을 차단한다.
- Common Strategy Version도 Runtime 값과 Profile 선언 값이 일치해야 한다.
- Common Package와 Research Source의 책임을 혼동하지 않는다.

## 4A. Versioned Backtest Platform 계약

### 4A.1 Strategy Profile Schema

- Strategy Profile은 `strategy_profiles/`에서 관리하고 `strategy_config_version`이 Profile Identity다.
- Profile 파일명과 선언 Version이 일치해야 한다.
- 필수 Category, 필수 Metadata Key와 허용 Config Key만 허용한다.
- Category·Metadata의 Unknown Key, Type 오류와 누락 Key를 차단한다.
- Common Default와 Profile Override를 병합해 완전한 Resolved Config를 생성한다.
- 존재하지 않는 Version은 DB 연결과 Run 생성 전에 차단한다.
- Profile Status와 운영 승격 상태는 같은 의미가 아니다.

### 4A.2 Resolved Config 명시적 주입

- 선택한 Profile을 Load해 Resolved Config를 생성하고 전체 실행 경로에 명시적으로 주입한다.
- Market, Filter, Sizing, Buy Guard, Buy Haircut과 Sell 흐름에 실제 Config를 전달한다.
- Engine과 Adapter는 Module Global Config나 숨은 Default에 의존하지 않는다.
- BUY Guard는 실제 Resolved `buy_guard` Config를 사용한다. `config={}` 같은 빈 연결을 만들지 않는다.
- CLI 문법은 실제 Source에 있는 형태(`--strategy-config-version` 등)만 사용한다.

### 4A.3 Config Snapshot·Hash Canonical Source

- Common Default와 Profile Override를 병합한 전체 Resolved Config로 Canonical JSON과 SHA-256 Config Hash를 만든다.
- Run에 Strategy Config Version, Config Snapshot과 Flatten Config KV를 저장한다.
- Trade Log는 Run ID와 Config Identity로 같은 Snapshot을 참조한다.
- Global Common Config Snapshot이 아니라 실제 실행 Config가 Canonical Source다.
- Secret은 Config Snapshot과 Hash 입력에 포함하지 않는다.

### 4A.4 Version Identity 분리

- Common Package Version, Common Strategy Version, Research Engine Version, Strategy Config Version,
  Metrics Config Version, Run Identity, Source SHA와 Image Digest를 분리해 관리한다.
- Strategy Config Version과 Research Engine Version은 같은 값이 아니다.
- Common Package Version과 Common Strategy Version도 서로 다른 값이다.
- Metrics Config Version은 Strategy Config Identity와 별도로 기록한다.
- Run마다 위 Identity를 저장해 재현 가능성을 확보한다.
- 실제 상수명과 저장 필드는 Source와 SQL에서 확인되는 것만 사용한다.

### 4A.5 Run Mode 분리

- `BACKTEST`와 `CANDIDATE` Run Mode를 구분한다.
- 운영 Run과 Candidate Run 조회 기준을 Run Mode와 Identity로 분리한다.
- Candidate 실행을 운영 Scheduler에 자동 연결하지 않는다.
- Candidate는 자동 승격하지 않는다.
- Candidate 실패 Run도 실패 상태와 Artifact Identity를 저장한다.
- Candidate는 배포 Artifact와 실행 계약 검증 경로이며 전략 성과 자동 승인자가 아니다.
- Strategy 성과 판단과 DevOps Artifact 승격을 혼동하지 않는다.

### 4A.6 Artifact Identity와 Input Snapshot 분리

- Artifact Identity는 Source SHA, Image Digest와 Artifact Identity Status로 구성한다.
- Candidate·운영 Run 모두 동일한 Artifact Identity 구조와 Digest 고정 Image를 사용한다.
- Input Snapshot은 실행 입력 범위, Manifest, Input Snapshot Hash와 Snapshot Status로 구성한다.
- Config Identity와 Input Data Identity를 같은 것으로 설명하지 않는다.
- 동일 기간이라도 원천 데이터가 갱신되면 Input Snapshot Hash가 달라질 수 있다.

### 4A.7 재현성 비교 대상과 제외 대상

- 재현성 비교에서 Config와 Artifact Identity, Backtest 결과와 Trade Log는 완전 일치를 확인한다.
- Input Snapshot Manifest는 일치, Input Snapshot Hash는 원천 데이터 갱신으로 변동 가능으로 구분한다.
- Run ID와 생성·시작·종료 시각은 비교 대상에서 제외한다.
- "완전히 동일한 Input Snapshot Hash를 검증했다"고 잘못 기록하지 않는다.

## 5. 입력 데이터 계약

| 입력 | 역할 |
|---|---|
| `pre_total_market_daily_feature` | Market 판단 입력 |
| `pre_total_stock_daily_feature` | 종목 Filter·Sizing과 Sell 판단 입력 |
| `interest_price_raw` | 가격, 수익률과 체결 가정 입력 |
| `stock_universe` | Backtest 대상 universe |
| Config Snapshot | 전략과 판단 기준 재현 |
| Run Input | 기간, 초기 자산과 실행 옵션 |

입력 관련 규칙:

- 거래일, feature 기준일과 다음 거래일 가격의 관계를 혼용하지 않는다.
- 미래 가격 또는 미래 feature를 현재 판단에 사용하지 않는다.
- 동일 ticker·trade date 결합에서 중복 row와 cardinality를 확인한다.
- feature 누락과 실제 0값을 구분한다.
- `NULL`, `0`, 음수, 빈 문자열과 미수집 상태를 임의로 같은 값으로 처리하지 않는다.
- 가격 조정 여부, 거래정지와 universe 활성 조건을 코드 근거 없이 추정하지 않는다.
- 입력 table과 column은 loader SQL을 직접 확인한 뒤 문서화한다.

## 6. Backtest 실행 계약

- 기존 포지션 처리와 신규 매수 순서를 임의로 변경하지 않는다.
- 당일 수익률, 누적 수익률과 포트폴리오 평가액 계산 순서를 확인한다.
- 매수·매도 가격 기준과 다음 거래일 가격 사용 여부를 구분한다.
- 동시 매수 후보의 정렬, 동점 처리와 최대 보유 수를 변경하면 결과가 달라질 수 있다.
- Guard, haircut, stop, 보유 기간과 sell reason의 우선순위를 보존한다.
- 거래 비용, 슬리피지와 세금이 구현되어 있는지 확인 없이 포함한다고 단정하지 않는다.
- 부분 일자 저장 후 Run을 성공 처리하지 않는다.
- Backtest가 실패하면 분석과 리포트가 정상 결과처럼 이어지지 않게 한다.
- 동일 입력 재실행 시 새로운 Run 생성인지 기존 Run 갱신인지 구분한다.
- 결과 재현을 위해 strategy name, engine version, config와 input snapshot 계약을 유지한다.

## 7. 출력과 저장 계약

| 출력 | 의미 |
|---|---|
| `strategy_backtest_run` | Backtest 실행 메타데이터와 상태 |
| `strategy_backtest_daily` | 거래일별 성과와 포트폴리오 결과 |
| `strategy_backtest_daily_position` | 거래일별 보유 포지션 snapshot |
| `strategy_trade_log` | 완료 거래 상세 |
| `strategy_backtest_*_analysis` | Run 기준 기본·확장 분석 |
| Report TXT | 저장된 Run 기준 사람이 읽는 리포트 |

아래 계약은 명시 요청 없이 변경하지 않는다.

- schema, table과 column 이름
- run id와 외래 참조
- unique key와 conflict target
- insert, update, delete와 upsert 범위
- run status와 analysis 상태
- trade reason과 metadata 구조
- strategy, engine과 evaluator version
- config, threshold와 input snapshot 형식
- report 파일명, section과 의미

저장 처리 원칙:

- DDL 실행 여부를 함수명만 보고 추정하지 않고 실제 SQL을 확인한다.
- delete 후 insert 분석은 반드시 run id 삭제 범위를 확인한다.
- commit과 rollback 위치를 확인한다.
- Daily row와 Daily Position snapshot 저장 단위가 같은 transaction인지 확인한다.
- Trade Log insert 실패가 전체 Run 상태에 어떻게 반영되는지 확인한다.
- 실패를 catch한 뒤 성공 상태로 덮지 않는다.
- 일부 분석 테이블만 갱신된 상태를 전체 분석 완료로 기록하지 않는다.

## 8. Analysis 규칙

- Basic과 Extended Analysis를 같은 실행으로 간주하지 않는다.
- 분석 입력은 저장된 Run, Daily, Position과 Trade Log를 기준으로 확인한다.
- Run id 없이 최신 Run을 자동 선택하는지 코드에서 확인한다.
- 분석 table 삭제·재생성 범위를 다른 Run까지 확대하지 않는다.
- Threshold, 구간, Bucket과 Label 의미를 임의로 변경하지 않는다.
- 거래가 0건인 Run과 분석 입력 누락을 구분한다.
- 빈 DataFrame, `NULL`, 무한대와 0분모 처리를 확인한다.
- 분석 실패 후 기존 row가 삭제된 채 남을 수 있는지 transaction 경계를 점검한다.
- 분석 결과를 실제 운용 성과나 미래 성과 보장으로 표현하지 않는다.

## 9. Report 규칙

- Report는 저장된 Backtest 결과를 읽어 텍스트 파일을 생성하는 표현 계층이다.
- Summary, Buy·Sell, Trade Detail과 Recommendation의 역할을 구분한다.
- Report Formatter의 label, percentage와 reason mapping을 공통 계약으로 취급한다.
- 최신 Run 자동 선택과 지정 Run id 실행을 구분한다.
- 출력 디렉터리 기본값과 override를 실제 코드 기준으로 확인한다.
- 같은 파일명 덮어쓰기와 기존 파일 삭제 여부를 확인한다.
- 민감정보, DB 접속값, secret과 AWS 식별자를 report에 포함하지 않는다.
- Recommendation은 연구 진단이며 실제 투자 권고나 주문 지시로 표현하지 않는다.
- Report 생성 성공과 S3 업로드 성공을 별도 상태로 구분한다.

## 10. AWS Batch와 S3 규칙

`aws_batch_backtest_report_wrapper.py`는 운영 영향이 있는 wrapper로 취급한다.

| 항목 | 확인 기준 |
|---|---|
| Secret 입력 | `RESEARCH_APP_SECRET_JSON` 매핑 |
| DB 환경변수 | `INTEREST_DB_*`로 변환 |
| 출력 경로 | `REPORT_OUTPUT_DIR` |
| S3 조건 | `REPORT_S3_BUCKET` 설정 여부 |
| Prefix | `REPORT_S3_PREFIX`와 날짜·Job ID 조합 |
| 실행 | `runpy.run_module` 대상 |
| 업로드 | 생성된 report 파일만 대상인지 확인 |

- 실제 secret JSON 값을 출력하거나 문서에 기록하지 않는다.
- Secret ARN, Job Definition ARN, Queue ARN, Bucket, Prefix와 Job ID 원문을 남기지 않는다.
- S3 업로드는 Report 생성과 별도 외부 쓰기다.
- 일부 파일 업로드 실패를 전체 성공으로 처리하지 않는다.
- repository의 wrapper는 실제 AWS Batch 배포 완료 증거가 아니다.
- AWS CLI, SDK, Batch, ECS, Step Functions와 S3 작업은 명시 승인 없이 실행하지 않는다.

## 10A. Research CI·Candidate·운영 승격 규칙

### 10A.1 Build Role과 Runtime Role 권한 분리

- GitHub Actions는 OIDC 인증과 CodeBuild 실행·상태 확인만 담당한다.
- CodeBuild는 Compile, Test, Config·Version Contract, Container Build, Smoke와 조건부 Publish를 담당한다.
- CodeBuild Role은 Build, Logs와 Research ECR 범위로 제한한다.
- GitHub OIDC Role은 Research CodeBuild 시작·조회 범위로 제한한다.
- Batch, Step Functions와 DB 권한은 Build Role에 포함하지 않는다.

### 10A.2 OIDC Trust와 Image 계약

- OIDC Trust는 추정하지 않고 실제 Token Subject 계약과 Branch 제한을 확인한다.
- Trust 범위는 Repository와 `main` Branch로 제한한다.
- Build-only와 Image Publish를 분리하고, 실패 시 ECR Push를 차단한다.
- Git SHA 기반 Image Tag와 Digest를 증적으로 사용하고 Mutable `latest` 의존을 만들지 않는다.
- 운영·Candidate 모두 Digest 고정 Image를 사용한다.

### 10A.3 Candidate와 운영 경로 분리

- Candidate Job Definition Family와 운영 Job Definition Family를 분리한다.
- Candidate Revision은 Digest Image와 Source SHA·Image Digest 환경변수를 사용한다.
- Candidate는 `--run-mode CANDIDATE`와 `--require-artifact-identity`로 수동 실행한다.
- Candidate 검증은 Job Status, Container Exit Code와 저장 계약 확인까지 포함한다.
- Candidate 실행으로 운영 Step Functions와 Scheduler를 변경하지 않는다.
- Candidate 자동 승격을 구성하지 않는다.

### 10A.4 운영 승격·Rollback과 Resource 검증

- 운영 승격은 Revision 등록과 운영 State Machine Champion Pointer 변경을 구분한다.
- 장기간 Backtest는 Candidate 성공만으로 운영 Resource가 충분하다고 판단하지 않는다.
- 실제 운영 기간과 입력 규모로 Step 4 단독 검증을 수행한다.
- Exit Code 137과 OOM을 애플리케이션 로직 실패와 구분한다.
- Timeout과 Memory 실패를 별도로 식별한다.
- AWS Resource 변경은 새 Job Definition Revision으로 등록한다.
- Resource 변경 후 운영 Pointer 승격 전에 단독 실행한다.
- 실패 시 이전 ACTIVE Champion Revision으로 즉시 Rollback한다.
- 전체 ARN, Account ID, Job ID와 Digest 원문을 문서에 기록하지 않고 Family·Revision·상태만 사용한다.

## 11. Database 규칙

- DB 설정은 `db_config.py`의 실제 구현을 기준으로 확인한다.
- 환경변수 이름, 기본값과 필수값을 추정하지 않는다.
- Password 기본값을 새로 만들지 않는다.
- `search_path` 순서 변경은 unqualified SQL 해석에 영향을 주므로 계약 변경으로 취급한다.
- schema-qualified SQL과 search path 기반 SQL의 대상 schema를 확인한다.
- column, unique key와 conflict target은 SQL 또는 DDL 근거 없이 추정하지 않는다.
- 읽기 전용 작업에서도 import 시 DB 연결이 발생하는지 확인한다.
- DB 쓰기 변경 전 DDL, insert, update, delete, upsert와 transaction 범위를 확인한다.
- 실제 DB 접속 없이 정적 확인만 한 경우 데이터 정합성 검증 완료로 표현하지 않는다.

## 12. 실행과 운영 안전

사용자가 명시하지 않은 경우 아래 작업은 금지한다.

| 금지 작업 | 이유 |
|---|---|
| `backtest_research_run.py` 실행 | Run, Daily, Position, Trade와 Analysis 변경 가능 |
| `backtest_engine.py` 실행 | 거래일별 저장과 commit 가능 |
| `backtest_run_store.py` 함수 실행 | DDL·DML과 상태 변경 가능 |
| `backtest_trade_log.py` 실행 | Trade Log insert 가능 |
| Analysis 진입점 실행 | 분석 table delete·insert 가능 |
| Report 진입점 실행 | DB 조회와 로컬 파일 생성 가능 |
| AWS Batch wrapper 실행 | Secret 매핑, Report와 S3 업로드 가능 |
| Block·Watch 연구 실행 | DB update 또는 backtest 유사 처리 가능 |
| 실제 DB DDL·DML | 운영·연구 데이터 변경 |
| 외부 API·S3 호출 | 외부 시스템과 저장소 변경 |
| AWS CLI·SDK 실행 | Batch, ECS, Step Functions와 운영 자원 영향 |
| Crawler·Preprocessor 실행 | Upstream 데이터 변경 |
| Daily Decision·Execution 실행 | 운영 Signal과 주문 후보 영향 |
| Broker 주문·취소 | 실제 주문 영향 |
| Slack 전송 | 운영 알림 오발송 위험 |

문서 작업에서는 Python module import도 import-time DB·파일·AWS 동작이 없는지 확인하기 전에는 수행하지 않는다.

## 13. 코드 수정 규칙

- 사용자의 명시 요청 없이 Python, Dockerfile, requirements와 wrapper를 수정하지 않는다.
- 기존 함수 signature, CLI option과 module entrypoint를 유지한다.
- `python -m port_strategy_research.<module>` 실행 구조를 깨지 않는다.
- 원본 Python 파일의 대규모 문자열 치환을 피하고 국소 수정한다.
- 사용자 변경을 되돌리지 않는다.
- test, debug, output과 report dump를 운영 소스로 단정하지 않는다.
- 사용되지 않는 것처럼 보여도 import, Docker CMD, Batch wrapper와 외부 command 증거를 확인한다.
- 명시 승인 없이 파일을 삭제하지 않는다.
- 실패 후 무조건 SUCCESS를 출력하는 흐름을 만들지 않는다.
- 코드 수정 후 운영 실행이 필요한 검증은 수행하지 않고 한계로 남긴다.

## 14. 테스트와 검증

테스트가 있다면 DB, 파일 시스템과 AWS를 격리한 단위 검증을 우선한다.

| 영역 | 우선 검증 |
|---|---|
| Loader | 기간, 거래일, 기준일, 누락과 join cardinality |
| Adapter | Common 입력·출력 mapping과 reason |
| Buy | Guard, haircut, sizing과 후보 순서 |
| Sell | Stop, hold period와 Common sell mapping |
| Position | 청산, 이월과 당일 수익률 |
| Run Store | Run 상태, unique key, rollback과 재실행 |
| Trade Log | 완료 거래 필드와 metadata |
| Metrics | 빈 값, 0분모, MDD와 Sharpe 경계 |
| Analysis | Run 범위, delete·insert와 빈 거래 |
| Report | Run 선택, section, file path와 덮어쓰기 |
| AWS Wrapper | 환경변수 매핑, module 호출과 S3 mock |

검증 원칙:

- DB가 필요한 테스트는 connection과 cursor를 mock 또는 fixture로 대체한다.
- 파일 생성은 임시 디렉터리를 사용한다.
- boto3와 S3는 mock한다.
- 실제 운영 DB, secret, bucket과 AWS 자원을 사용하지 않는다.
- 테스트 import가 DB, 파일 생성이나 외부 호출을 수행하는지 먼저 확인한다.
- 실행하지 못한 테스트를 통과로 기록하지 않는다.
- 문서만 수정한 경우 문서 형식과 변경 범위만 검증한다.

## 15. Docker와 Dependency 규칙

- `Dockerfile`의 base image, copy 경로, work directory와 CMD를 실제 파일 기준으로 확인한다.
- 기본 CMD가 compile 확인인지 실제 Research 실행인지 구분한다.
- 실제 Backtest·Report command override는 외부 Batch 또는 ECS 설정과 분리한다.
- `port_strategy_common`은 Source vendoring이 아니라 Wheel `1.0.0` 고정 설치 구조임을 유지한다.
- Common Source Directory Copy와 Wheel Package 설치를 혼동하지 않는다.
- requirements의 pinned 버전은 파일 자체에서 관리한다.
- 코드 import와 requirements가 일치하는지 확인하되 문서 작업에서 임의 수정하지 않는다.
- Dockerfile 존재는 이미지 build, push와 배포 완료 증거가 아니다.

## 16. 보안과 민감정보

- Password, token, API key, account, webhook URL과 DB 접속정보를 출력하거나 문서화하지 않는다.
- Secret JSON과 환경변수 값은 키 이름만 확인하고 값은 인용하지 않는다.
- 발견한 민감정보는 값 자체가 아니라 존재와 위치만 보고한다.
- 예시는 `[REDACTED]` 또는 명백한 placeholder를 사용한다.
- AWS Batch Job ID, ARN, image URI, bucket, prefix와 command id 전체값을 기록하지 않는다.
- Report와 dump에 종목별 거래, 보유, 계좌 정보가 있으면 필요한 최소 사실만 요약한다.

## 17. 문서 갱신 규칙

### 17.1 README.md

다음이 바뀐 경우 필요한 부분만 갱신한다.

- Research 책임과 다른 MS 경계
- Backtest, Analysis와 Report 실행 흐름
- 입력·출력 table 계약
- Common과 Research adapter 구조
- Block·Watch·Exception Buy 분류
- DB 설정과 search path
- Docker CMD, AWS Batch wrapper와 S3 경로
- 외부 dependency 또는 실행 위험

### 17.2 CHANGELOG.md

- 실제 변경만 날짜별로 기록한다.
- 문서 재정비와 Python 기능 변경을 구분한다.
- 과거 worklog 생성과 파일 정리 기록은 당시 사실로 보존한다.
- 실행하지 않은 Backtest, DB, Report와 AWS 검증을 완료로 기록하지 않는다.
- 일회성 Run ID, Job ID, 경로와 실행 로그는 기록하지 않는다.

### 17.3 docs/source-file-catalog.md

다음 변경이 확인되면 관련 행이나 섹션을 함께 갱신한다.

| 변경 | 갱신 내용 |
|---|---|
| 파일 생성·삭제·이름 변경 | 파일 목록과 책임 |
| Entrypoint 변경 | 실행 흐름과 위험 |
| Loader·Store 책임 변경 | 입력·출력과 DB 영향 |
| Common adapter 변경 | 함수, mapping과 독립성 |
| Analysis 변경 | 입력, table과 재생성 범위 |
| Report 변경 | Data loader, formatter와 출력 파일 |
| AWS wrapper 변경 | Secret, output과 S3 영향 |
| Docker·dependency 변경 | Runtime과 실행 구조 |
| 연구 후보 상태 변경 | Block·Watch 계열 분류와 위험 |
| 문서 생성·삭제 | Documents 목록과 역할 |

내부 구현만 바뀌고 파일 책임과 변경 영향이 같으면 catalog를 수정하지 않는다.
카탈로그는 전체 inventory가 아니라 운영과 유지보수에 중요한 책임 문서로 유지한다.

### 17.4 Worklog

- `docs/worklog`와 날짜별 worklog는 새로 만들지 않는다.
- 과거 CHANGELOG에 남은 worklog 생성 이력은 당시 사실이므로 삭제하지 않는다.
- 현재 작업 이력은 CHANGELOG에 필요한 핵심 변경만 남긴다.

## 18. 문서 정합성

네 문서는 같은 용어와 책임 경계를 사용해야 한다.

| 용어 | 기준 |
|---|---|
| 서비스명 | `port_strategy_research` |
| 계층명 | Research |
| 플랫폼 성격 | Versioned Backtest Platform |
| Upstream | Preprocessor |
| 운영 판단 | StrategyDecision |
| 후속 실행 | StrategyExecution |
| 핵심 실행 | Backtest Research |
| 전략 설정 | Strategy Profile과 Strategy Config Version |
| 실행 Config | Resolved Config, Config Snapshot과 Config Hash |
| Version | Common Package·Common Strategy·Research Engine·Metrics Config Version |
| 실행 구분 | Run Mode (`BACKTEST`, `CANDIDATE`) |
| 재현성 | Artifact Identity와 Input Snapshot |
| 승격 | Candidate, Operating Champion, Manual Promotion과 Rollback Revision |
| 분석 | Basic Analysis와 Extended Analysis |
| 리포트 | Summary, Buy·Sell, Trade Detail과 Recommendation |
| 공통 계약 | `port_strategy_common` Wheel `1.0.0` |
| Adapter | Research 내부 adapter |
| 저장 단위 | Run ID |
| 일자 기준 | Trade Date |
| AWS 실행 | Step 4 Research와 Step 5 Report |
| 외부 운영 | Batch, ECS와 Step Functions를 repository 사실과 분리 |

코드에서 확인되지 않은 table, column, 상태, 알고리즘과 AWS 자원을 문서 편의를 위해 추가하지 않는다.

## 19. Git 규칙

- 작업 전후 사용자 변경을 보존한다.
- `git status --short`와 `git diff --stat`은 변경 범위 확인에만 사용한다.
- 가능하면 `git diff --check`로 공백 오류를 확인한다.
- 명시 요청 없이 `git add`, `commit`, `push`, `reset`, `restore`와 `checkout`을 실행하지 않는다.
- 저장소가 없는 첨부 파일 작업에서는 Git 검증을 수행한 것처럼 보고하지 않는다.

## 20. 완료 조건

작업 완료 전 아래를 확인한다.

- 대상 파일만 수정했는가
- Research 책임과 다른 MS의 경계를 유지했는가
- `port_strategy_decision` 런타임 의존으로 잘못 표현하지 않았는가
- Common과 Research adapter 계약을 보존했는가
- Backtest 입력과 저장 table 계약을 보존했는가
- Run, Daily, Position, Trade와 Analysis 의미를 혼동하지 않았는가
- Basic과 Extended Analysis를 구분했는가
- Report 생성과 S3 업로드를 구분했는가
- Block·Watch 연구 파일을 운영 파이프라인으로 단정하지 않았는가
- DB DDL·DML, 파일 생성과 재실행 위험을 확인했는가
- source catalog 갱신 조건에 해당하는지 확인했는가
- 신규 worklog를 만들지 않았는가
- 민감정보와 운영 식별자 원문을 새로 기록하지 않았는가
- 문서 역할과 용어가 네 문서에서 일치하는가
- UTF-8 No BOM, 300자 셀과 500자 라인 기준을 지켰는가
- 실행하지 않은 검증을 성공으로 보고하지 않았는가

## 21. 완료 보고

완료 보고는 2컬럼 표 중심으로 짧게 작성한다.

| 항목 | 보고 내용 |
|---|---|
| 변경 파일 | 실제 수정 파일 |
| 변경 요약 | 책임, 계약과 문서 구조의 핵심 변경 |
| 검증 결과 | 정적 확인과 실행한 안전 검증 |
| 미수행 | Backtest, DB, Report, AWS, S3와 주문 관련 미실행 항목 |
| 남은 위험 | 코드 대조 또는 운영 확인이 필요한 사항 |
| 민감정보 | 원문 신규 기록 여부 |

문서 수정 외 실제 Research 또는 운영 실행은 사용자가 명시적으로 요청하고 승인한 경우에만 수행한다.
