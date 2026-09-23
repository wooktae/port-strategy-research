"""Verifies the Candidate Run Mode, failure finalization, and operating-query isolation contract."""

from __future__ import annotations

import inspect
import sys
from unittest.mock import patch

from port_strategy_research import (
    backtest_research_run,
    backtest_run_store,
    report_data_loader,
)
from port_strategy_research.strategy_profile_loader import (
    load_strategy_config_snapshot,
)


class FakeCursor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple | None]] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, sql: str, params=None) -> None:
        self.calls.append((sql, params))

    def fetchone(self):
        return ("run-1",)


class FakeConnection:
    def __init__(self) -> None:
        self.cursor_instance = FakeCursor()
        self.commit_count = 0
        self.rollback_count = 0

    def cursor(self) -> FakeCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.commit_count += 1

    def rollback(self) -> None:
        self.rollback_count += 1


def verify_cli_contract() -> None:
    with patch.object(
        sys,
        "argv",
        ["backtest_research_run"],
    ):
        args = backtest_research_run.parse_args()

    assert args.run_mode == "BACKTEST"

    with patch.object(
        sys,
        "argv",
        [
            "backtest_research_run",
            "--run-mode",
            "candidate",
        ],
    ):
        args = backtest_research_run.parse_args()

    assert args.run_mode == "CANDIDATE"

    print("RUN_MODE_CLI_DEFAULT_BACKTEST=SUCCESS")
    print("RUN_MODE_CLI_CANDIDATE_NORMALIZATION=SUCCESS")


def verify_create_run_validation() -> None:
    snapshot = load_strategy_config_snapshot("RSCFG-0001")

    conn = FakeConnection()
    run_id = backtest_run_store.create_run(
        conn,
        run_mode="candidate",
        config_snapshot=snapshot,
    )

    assert run_id
    assert conn.commit_count == 1

    sql, params = conn.cursor_instance.calls[0]
    assert "run_mode" in sql
    assert params is not None
    assert "CANDIDATE" in params

    try:
        backtest_run_store.create_run(
            FakeConnection(),
            run_mode="INVALID",
            config_snapshot=snapshot,
        )
    except ValueError as exc:
        assert "RUN_MODE_INVALID=" in str(exc)
    else:
        raise AssertionError("INVALID_RUN_MODE_NOT_REJECTED")

    print("CREATE_RUN_CANDIDATE_PERSISTENCE=SUCCESS")
    print("CREATE_RUN_INVALID_MODE_REJECTION=SUCCESS")


def verify_failure_finalization() -> None:
    conn = FakeConnection()

    backtest_run_store.fail_run(
        conn,
        "run-1",
        backtest_start_date="2026-08-01",
        backtest_end_date="2026-08-02",
        error_type="RuntimeError",
        error_message="history empty",
    )

    assert conn.commit_count == 1

    sql, params = conn.cursor_instance.calls[0]
    assert "finished_at = now()" in sql
    assert "backtest_start_date = COALESCE" in sql
    assert "backtest_end_date = COALESCE" in sql
    assert params is not None
    assert len(params) == 4

    failure_note = str(params[2])

    assert "run_status=FAILED" in failure_note
    assert "error_type=RuntimeError" in failure_note
    assert "error_message=history empty" in failure_note

    print("FAILED_RUN_FINISHED_AT_PERSISTENCE=SUCCESS")
    print("FAILED_RUN_DATE_RANGE_PERSISTENCE=SUCCESS")
    print("FAILED_RUN_REASON_PERSISTENCE=SUCCESS")


def verify_operating_latest_query() -> None:
    conn = FakeConnection()

    report_data_loader.get_latest_run_id(conn.cursor_instance)

    sql, _ = conn.cursor_instance.calls[0]
    normalized = " ".join(sql.split())

    assert "WHERE run_mode = 'BACKTEST'" in normalized
    assert "finished_at IS NOT NULL" in normalized
    assert "ORDER BY started_at DESC" in normalized

    print("LATEST_RUN_BACKTEST_ONLY=SUCCESS")
    print("LATEST_RUN_COMPLETED_ONLY=SUCCESS")


def verify_source_wiring() -> None:
    source = inspect.getsource(backtest_research_run.main)

    assert "run_mode=selected_run_mode" in source
    assert '"run_mode": selected_run_mode' in source
    assert "fail_run(" in source
    assert "conn.rollback()" in source

    print("ENTRYPOINT_RUN_MODE_WIRING=SUCCESS")
    print("ENTRYPOINT_RUN_INPUT_MODE_PERSISTENCE=SUCCESS")
    print("ENTRYPOINT_FAILED_RUN_FINALIZATION=SUCCESS")


def main() -> None:
    verify_cli_contract()
    verify_create_run_validation()
    verify_failure_finalization()
    verify_operating_latest_query()
    verify_source_wiring()

    print("CANDIDATE_RUN_MODE_CONTRACT_TEST=SUCCESS")


if __name__ == "__main__":
    main()
