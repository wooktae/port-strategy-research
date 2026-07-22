# 소스 파일 카탈로그

이 문서는 `port_strategy_research` 루트의 주요 소스와 문서를 AWS Migration 전 초기 정리 관점에서 정리한 목록이다. 실제 백테스트, DB 접속, 리포트 생성, 외부 API 호출, 크롤링, 주문 실행은 수행하지 않고 정적 확인 기준으로 작성했다.

## 백테스트 코어

| 파일 경로 | 한글 제목 | 파일 내용 | 주요 역할 | 수정/운영 시 주의사항 |
| --- | --- | --- | --- | --- |
| `__init__.py` | research 패키지 표시 | Python 패키지 루트 표시 파일이다. | `port_strategy_research` import 경계를 제공한다. | 기능 로직은 없지만 패키지 인식에 필요하므로 삭제하지 않는다. |
| `backtest_engine.py` | 백테스트 엔진 루프 | 거래일 루프에서 시장 판단, 후보 필터, 포지션 처리, 매수 처리를 연결한다. | 일별 성과를 만들고 `strategy_backtest_daily`, `strategy_backtest_daily_position` 저장 helper를 호출한다. | 실행 시 DB read/write와 commit이 발생한다. 현재 미커밋 변경에 일별 포지션 저장 및 디버그 출력이 포함되어 있어 운영 실행 전 확인이 필요하다. |
| `backtest_loader.py` | 백테스트 입력 로더 | market/stock/price feature와 stock universe를 SQL로 조회한다. | `pre_total_market_daily_feature`, `pre_total_stock_daily_feature`, `interest_price_raw`, `stock_universe` 입력 계약을 읽는다. | 읽기 helper지만 실제 DB connection을 사용한다. 입력 테이블명과 컬럼 의미를 임의 변경하지 않는다. |
| `backtest_buy_logic.py` | 신규 매수 처리 | 후보 종목을 common context로 변환하고 sizing, guard, haircut, 당일 손절을 처리한다. | `research_backtest_sizing_adapter`를 경유해 `port_strategy_common` sizing/buy guard/sizing haircut을 재사용한다. | 당일 손절 거래는 `strategy_trade_log` insert로 이어질 수 있다. strategy 조건과 reason 문자열을 임의 변경하지 않는다. |
| `backtest_sell_logic.py` | 매도 판단 wrapper | common sell decision 호출을 백테스트 구조에 맞게 감싼다. | `port_strategy_common.common_sell_decision.common_evaluate_backtest_sell` 재사용 지점이다. | 공통 sell decision signature와 reason 구조를 임의 변경하지 않는다. |
| `backtest_position_manager.py` | 기존 포지션 처리 | 보유 종목의 수익률, 장중 손절, 일반 매도, 이월 포지션을 계산한다. | 청산 거래 저장과 생존 포지션 이월을 담당한다. | `insert_trade_log` 호출이 있어 DB write로 이어질 수 있다. 실행 순서와 포지션 dict key를 변경하지 않는다. |
| `backtest_trade_log.py` | 거래 로그 저장 | 완료 거래 또는 당일 손절 거래를 `strategy_trade_log`에 insert한다. | 매수/매도 가격, 보유 기간, 수익률, buy/sell metadata, config snapshot을 저장한다. | DB insert 경로다. 테이블명, 컬럼명, JSON 저장 의미를 임의 변경하지 않는다. |
| `backtest_metrics.py` | 성과 지표 계산 | 일별 수익률 DataFrame에서 MDD와 Sharpe ratio를 계산한다. | backtest 종료 성과 요약에 필요한 지표를 제공한다. | 입력 DataFrame 컬럼 계약을 유지한다. |
| `backtest_run_store.py` | run 저장소 | backtest run, daily result, 일별 포지션 snapshot 저장 SQL을 담는다. | `strategy_backtest_run`, `strategy_backtest_daily`, `strategy_backtest_daily_position` 저장과 run finalize를 담당한다. | DDL/DML과 commit 경로가 포함된다. 현재 미커밋 변경에 `insert_daily_positions()`가 추가되어 대상 테이블 존재와 unique key 확인이 필요하다. |
| `backtest_research_run.py` | 표준 research run 진입점 | DB 연결, run 생성, input/config snapshot 저장, 엔진 실행, 기본 분석 저장을 순서대로 수행한다. | 표준 백테스트 전체 실행 orchestration이다. | 실행 금지 대상이다. DB DDL/DML, commit, 분석 저장을 수행할 수 있다. |

## Research 내부 adapter

| 파일 경로 | 한글 제목 | 파일 내용 | 주요 역할 | 수정/운영 시 주의사항 |
| --- | --- | --- | --- | --- |
| `research_backtest_market_adapter.py` | market decision adapter | preprocessor market feature row를 common 입력 context로 변환하고 `common_decide_market`을 호출한다. | Research 내부에서 `port_strategy_decision` 런타임 의존 없이 market decision 계약을 공유한다. | DB 접근이나 외부 API 호출은 없다. reason 문자열과 dataclass 필드를 임의 변경하지 않는다. |
| `research_backtest_filter_adapter.py` | buy filter adapter | stock feature 목록과 market decision을 `common_filter_buy_candidates` 입력으로 맞춘다. | Research 내부에서 buy candidate filter 계약을 공유한다. | 자체 DB 접근은 없다. decision reason 문자열과 공통 설정 계약을 유지한다. |
| `research_backtest_sizing_adapter.py` | sizing adapter | 필터를 통과한 후보와 market decision을 `common_allocate_positions` 입력으로 변환한다. | Research 내부에서 sizing 계약을 공유한다. | 포지션 크기 계산은 `port_strategy_common`에 위임한다. DB 접근은 없다. |

## 분석 모듈

| 파일 경로 | 한글 제목 | 파일 내용 | 주요 역할 | 수정/운영 시 주의사항 |
| --- | --- | --- | --- | --- |
| `backtest_analysis_basic.py` | 기본 분석 저장 | 거래 로그 기반 기본 분석 row를 생성한다. | 매수 사유, 보유 기간, 시장 신호별 분석 테이블을 저장한다. | run_id 기준 delete/insert 가능성이 있는 DB write 경로다. |
| `analysis_extended.py` | 확장 분석 저장 | signal/holding, ticker, entry/exit, sector, MB weak 분석을 생성한다. | 리포트 추천에 필요한 확장 분석 테이블들을 재계산한다. | 여러 `strategy_backtest_*_analysis` 테이블을 갱신한다. 실행 전 run_id와 대상 DB를 확인한다. |
| `run_extended_analysis.py` | 확장 분석 실행 진입점 | 최신 run_id를 조회해 확장 분석을 실행한다. | `analysis_extended.run_analysis_extended()` 호출용 entrypoint다. | DB 접속과 분석 테이블 갱신을 수행하므로 문서화 작업에서 실행하지 않는다. |

## 리포트 모듈

| 파일 경로 | 한글 제목 | 파일 내용 | 주요 역할 | 수정/운영 시 주의사항 |
| --- | --- | --- | --- | --- |
| `backtest_report_run.py` | 리포트 묶음 생성 | 최신 run_id 기준으로 요약, 매매, 거래 상세, 추천 리포트를 생성한다. | report 모듈들을 순서대로 호출하고 로컬 txt 파일명을 만든다. | DB 조회와 로컬 파일 생성이 발생한다. 출력 위치와 version filename 규칙을 확인한다. |
| `report_data_loader.py` | 리포트 데이터 로더 | run, daily, daily position, trade log, analysis table을 조회한다. | 리포트 생성 모듈의 공통 DB read helper다. | 현재 미커밋 변경으로 보유/신규 매수 조회가 `strategy_backtest_daily_position` 기준으로 바뀌었다. |
| `report_formatter.py` | 리포트 포맷터 | 퍼센트, label, run input, 매수/매도 사유 문자열을 포맷팅한다. | 사람이 읽는 리포트 문구 변환을 담당한다. | reason 문자열과 config key label을 변경할 때 report 영향 범위를 확인한다. |
| `report_summary.py` | 요약 리포트 | run 요약과 주요 분석 통계를 txt로 출력한다. | 전체 backtest 결과 요약 파일을 생성한다. | DB 조회와 파일 쓰기가 발생한다. |
| `report_buy_sell.py` | 일자별 매매 리포트 | 일별 성과, 보유 현황, 신규 매수, 매도를 txt로 출력한다. | 일자별 포트폴리오 상태와 매매 이벤트를 보여준다. | 보유/신규 매수는 일별 포지션 snapshot 조회에 의존한다. |
| `report_trade_detail.py` | 거래 상세 리포트 | 완료 거래 로그를 거래 단위 txt로 출력한다. | 거래별 진입/청산 정보와 사유를 보여준다. | `strategy_trade_log` 컬럼 계약을 유지한다. |
| `report_recommendation.py` | 추천/진단 리포트 | 분석 통계와 threshold snapshot을 조합해 개선 추천 문구를 생성한다. | 리스크, 진입, 청산, 종목/섹터 관점의 진단을 출력한다. | DB 조회와 파일 쓰기가 발생한다. 추천 문구 변경은 기능 로직이 아니라 리포트 해석 변경으로 관리한다. |

## 컨테이너 실행 및 AWS Batch wrapper

| 파일 경로 | 한글 제목 | 파일 내용 | 주요 역할 | 수정/운영 시 주의사항 |
| --- | --- | --- | --- | --- |
| `Dockerfile` | Research 컨테이너 정의 | `python:3.13-slim` 기반으로 `port_strategy_common`, `port_strategy_research`, `requirements.txt`를 포함하는 이미지 정의다. | AWS Batch/ECS 등 컨테이너 실행 환경에서 Research entrypoint를 실행할 이미지를 만든다. | 기본 CMD는 py_compile 확인이며 실제 실행 command는 job/task 정의에서 override한다. 실제 image URI/registry 원문은 문서에 남기지 않는다. |
| `requirements.txt` | 의존성 목록 | `psycopg2-binary`, `pandas`, `numpy`, `boto3` 등 Research 실행에 필요한 pip 의존성을 관리한다. | 컨테이너 이미지 빌드 시 `pip install -r requirements.txt`로 소비된다. | 개별 pinned 버전 값은 파일 자체에서 관리하며 문서에는 반복 기록하지 않는다. |
| `aws_batch_backtest_report_wrapper.py` | AWS Batch BACKTEST_REPORT wrapper | `RESEARCH_APP_SECRET_JSON`을 `INTEREST_DB_*`로 매핑하고, `backtest_report_run`을 실행한 뒤 생성된 report txt 파일을 S3에 업로드한다. | AWS Batch job에서 Daily Step 5 리포트 생성을 실행할 때 사용된다. | secret 값, bucket 이름, prefix, job id 원문은 로그/문서/커밋에 남기지 않는다. S3 업로드 경로와 `REPORT_OUTPUT_DIR` 기본값을 임의로 바꾸지 않는다. |

## block/watch/exception-buy 연구 계열

| 파일 경로 | 한글 제목 | 파일 내용 | 주요 역할 | 수정/운영 시 주의사항 |
| --- | --- | --- | --- | --- |
| `block_watch_analysis_run.py` | block watch 사후 분석 | watch 후보의 n일 후 수익률을 계산하고 DB에 갱신한다. | watch 후보 성과 확인용 분석을 수행한다. | DB update가 포함된다. 실행 금지 대상이며 삭제하지 않고 연구 계열로 보류한다. |
| `block_watch_backtest_run.py` | block watch 후보 백테스트성 분석 | block 이후 watch 후보와 forward return을 계산해 콘솔 요약을 출력한다. | block 장세 후 관찰 후보의 품질을 검증한다. | DB 연결과 backtest 유사 계산이 있다. 정리 후보가 아니라 연구/검증 후보로 문서화만 유지한다. |
| `block_exception_buy_engine_run.py` | block 예외 매수 엔진 검증 | 기존 백테스트 엔진 흐름을 활용해 block 예외 매수를 검증한다. | run 생성, daily 저장, 분석 저장까지 이어질 수 있는 연구 실행 파일이다. | DB write와 commit 가능성이 있어 명시 승인 없이 실행하지 않는다. 연구 계열 보류 파일이다. |
| `block_exception_buy_backtest_run.py` | block 예외 매수 후보 검증 | CLI threshold 기반으로 후보, 거래, 월별 요약을 계산한다. | block 예외 매수 조건의 사후 성과를 검증한다. | DB 연결과 backtest 유사 계산이 있다. 연구 계열 보류 파일이며 삭제하지 않는다. |

## 설정과 문서

| 파일 경로 | 한글 제목 | 파일 내용 | 주요 역할 | 수정/운영 시 주의사항 |
| --- | --- | --- | --- | --- |
| `db_config.py` | DB 접속 설정 | `INTEREST_DB_*` 환경변수로 PostgreSQL connection dict를 만든다. | `portfolio` DB와 domain schema search_path 기본값을 제공한다. | password 값은 환경변수/로컬 설정에서 주입한다. 실제 민감정보 값을 문서나 소스에 기록하지 않는다. |
| `AGENTS.md` | 작업 규칙 | 이 저장소에서의 작업 범위, 금지 작업, 검증 규칙을 정의한다. | Codex/작업자용 운영 가드레일이다. | 현재 루트 밖 파일 수정 금지, 백테스트/DB write 실행 금지 규칙을 유지한다. |
| `README.md` | 프로젝트 설명 | 백테스트 구성요소, 실행 주의사항, DB 환경변수, schema 구조를 설명한다. | 신규 작업자가 프로젝트 구조와 위험 지점을 빠르게 파악하도록 돕는다. | 실제 credential과 운영 로컬 경로를 기록하지 않는다. |
| `CHANGELOG.md` | 변경 기록 | 날짜별 주요 변경 사항과 기능 변경 여부를 기록한다. | 미커밋 변경과 문서화 작업의 요약 기록이다. | 실제 코드 변경 의미와 문서화 작업을 구분해 기록한다. |
| `docs/source-file-catalog.md` | 파일 카탈로그 | repository root 기준 파일별 역할, 책임, 주의사항을 정리한다. | AWS Migration 전 초기 정리와 영향 범위 파악 자료다. | 생성물/cache는 제외하고 운영 소스와 문서 중심으로 유지한다. |
| `docs/worklog/2026-05-26.md` | 2026-05-26 작업 기록 | 초기 파일 구조 분석과 문서 초안 작성 기록이다. | 과거 문서화 작업 이력을 제공한다. | 기존 형식과 상태 표기를 유지한다. |
| `docs/worklog/2026-05-27.md` | 2026-05-27 작업 기록 | DB 접속 환경변수 외부화와 schema 문서화 작업 기록이다. | 전날 미커밋 변경의 배경을 제공한다. | 민감정보 값은 기록하지 않는다. |
| `docs/worklog/2026-05-28.md` | 2026-05-28 작업 기록 | 미커밋 변경 확인, 파일 카탈로그 작성, 설명 주석 추가 기록이다. | 이번 AWS Migration 전 초기 정리 작업 이력을 남긴다. | 기능 변경 없음과 실행하지 않은 검증 한계를 명시한다. |

## 제외 기준

- `__pycache__/`, `*.pyc`, build/target/cache/IDE 임시 파일은 카탈로그 대상에서 제외한다.
- 현재 확인된 Java, HTML, CSS, SQL, YAML, properties 운영 파일은 없다.
- 삭제 후보 파일은 이번 작업에서 확정하지 않는다. block/watch/exception-buy 계열은 연구/보류 계열로만 표시한다.
