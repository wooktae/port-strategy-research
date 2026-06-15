"""AWS Batch용 BACKTEST_REPORT wrapper.

역할:
- Job Definition에서 주입된 RESEARCH_APP_SECRET_JSON을 INTEREST_DB_* 환경변수로 매핑한다.
- Batch 실행 시 리포트 출력 경로 기본값을 /tmp/portfolio-reports 로 지정한다.
- REPORT_S3_BUCKET 환경변수가 있으면 생성된 리포트 txt 파일을 S3로 업로드한다.
- 실제 report entrypoint는 port_strategy_research.backtest_report_run 으로 위임한다.
"""

import json
import os
import runpy
from datetime import datetime
from pathlib import Path

import boto3


def inject_interest_db_env_from_secret_json() -> None:
    raw = os.environ.get("RESEARCH_APP_SECRET_JSON")
    if not raw:
        print("[report-wrapper] RESEARCH_APP_SECRET_JSON not found. Use existing INTEREST_DB_* env.")
        return

    secret = json.loads(raw)

    mapping = {
        "INTEREST_DB_HOST": ["INTEREST_DB_HOST", "host"],
        "INTEREST_DB_PORT": ["INTEREST_DB_PORT", "port"],
        "INTEREST_DB_NAME": ["INTEREST_DB_NAME", "dbname", "database"],
        "INTEREST_DB_USER": ["INTEREST_DB_USER", "username", "user"],
        "INTEREST_DB_PASSWORD": ["INTEREST_DB_PASSWORD", "password"],
    }

    for env_key, candidates in mapping.items():
        if os.environ.get(env_key):
            continue

        for key in candidates:
            value = secret.get(key)
            if value is not None and str(value) != "":
                os.environ[env_key] = str(value)
                break

    missing = [
        key
        for key in [
            "INTEREST_DB_HOST",
            "INTEREST_DB_PORT",
            "INTEREST_DB_NAME",
            "INTEREST_DB_USER",
            "INTEREST_DB_PASSWORD",
        ]
        if not os.environ.get(key)
    ]

    if missing:
        raise RuntimeError(f"Missing DB env after secret mapping: {missing}")

    print("[report-wrapper] DB env mapping completed.")


def configure_report_output_dir() -> None:
    os.environ.setdefault("REPORT_OUTPUT_DIR", "/tmp/portfolio-reports")
    print(f"[report-wrapper] REPORT_OUTPUT_DIR={os.environ.get('REPORT_OUTPUT_DIR')}")


def build_s3_prefix() -> str:
    base_prefix = os.environ.get("REPORT_S3_PREFIX", "strategy-research/reports").strip("/")
    date_str = datetime.now().strftime("%Y%m%d")
    job_id = os.environ.get("AWS_BATCH_JOB_ID", "local").strip()

    return f"{base_prefix}/{date_str}/{job_id}"


def upload_reports_to_s3() -> None:
    bucket = os.environ.get("REPORT_S3_BUCKET")
    if not bucket:
        print("[report-wrapper] REPORT_S3_BUCKET not set. Skip S3 upload.")
        return

    output_dir = Path(os.environ.get("REPORT_OUTPUT_DIR", "/tmp/portfolio-reports"))
    if not output_dir.exists():
        raise RuntimeError(f"Report output directory does not exist: {output_dir}")

    report_files = sorted(output_dir.glob("*.txt"))
    if not report_files:
        raise RuntimeError(f"No report txt files found in: {output_dir}")

    prefix = build_s3_prefix()
    s3 = boto3.client("s3")

    for report_file in report_files:
        key = f"{prefix}/{report_file.name}"
        s3.upload_file(str(report_file), bucket, key)
        print(f"[report-wrapper] Uploaded s3://{bucket}/{key}")

    print(f"[report-wrapper] S3 upload completed. count={len(report_files)}")


def main() -> None:
    inject_interest_db_env_from_secret_json()
    configure_report_output_dir()

    runpy.run_module(
        "port_strategy_research.backtest_report_run",
        run_name="__main__",
    )

    upload_reports_to_s3()


if __name__ == "__main__":
    main()
