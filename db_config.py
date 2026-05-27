import os


def get_db_config() -> dict:
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
        "dbname": os.getenv("INTEREST_DB_NAME", "interest_crawler"),
    }
