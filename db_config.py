"""research 모듈의 PostgreSQL 접속 설정을 환경변수에서 구성하는 모듈.

민감정보인 password 값은 소스나 문서에 두지 않고 `INTEREST_DB_PASSWORD`로 주입한다.
AWS Migration 준비 구조에 맞춰 `portfolio` DB와 domain schema search_path를 기본값으로 둔다.
"""

import os


def get_db_config() -> dict:
    """`psycopg2.connect`에 전달할 DB 설정 dict를 반환한다."""
    password = os.getenv("INTEREST_DB_PASSWORD")
    if not password:
        raise RuntimeError("INTEREST_DB_PASSWORD 환경변수가 설정되어 있지 않습니다.")

    port_value = os.getenv("INTEREST_DB_PORT", "5433")
    try:
        port = int(port_value)
    except ValueError as exc:
        raise RuntimeError("INTEREST_DB_PORT는 정수여야 합니다.") from exc

    return {
        "host": os.getenv("INTEREST_DB_HOST", "localhost"),
        "port": port,
        "user": os.getenv("INTEREST_DB_USER", "postgres"),
        "password": password,
        "dbname": os.getenv("INTEREST_DB_NAME", "portfolio"),
        "options": "-c search_path=research,preprocessor,interest,reference,legacy,public",
    }
