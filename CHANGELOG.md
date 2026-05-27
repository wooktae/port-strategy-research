# CHANGELOG

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
