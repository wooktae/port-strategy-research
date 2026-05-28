# CHANGELOG

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
