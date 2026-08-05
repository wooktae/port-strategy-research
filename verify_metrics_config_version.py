"""Metrics Config Version Runtime Identity와 Run 저장 계약 검증."""

from __future__ import annotations

import inspect
from pathlib import Path

from port_strategy_research import backtest_run_store
from port_strategy_research.research_version_identity import (
    ResearchVersionIdentityError,
    get_metrics_config_version,
    resolve_metrics_config_identity,
)
from port_strategy_research.strategy_config_snapshot import (
    StrategyConfigSnapshot,
)


class FakeCursor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple | None]] = []

    def execute(self, sql, params=None) -> None:
        self.calls.append((sql, params))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


class FakeConnection:
    def __init__(self) -> None:
        self.cursor_instance = FakeCursor()
        self.commit_count = 0

    def cursor(self) -> FakeCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.commit_count += 1


def _snapshot(
    metrics_version: str = "RMETRICS-0001",
) -> StrategyConfigSnapshot:
    return StrategyConfigSnapshot(
        strategy_config_version="RSCFG-0001",
        resolved_config={
            "metadata": {
                "strategy_config_version": "RSCFG-0001",
                "metrics_config_version": metrics_version,
            },
            "metrics": {
                "risk_free_rate": 0.0,
                "trading_days_per_year": 252,
            },
        },
        canonical_json="{}",
        config_hash="0" * 64,
        profile_path=Path(
            "strategy_profiles/RSCFG-0001.json"
        ),
    )


def _expect_error(
    expected_marker: str,
    callback,
) -> None:
    try:
        callback()
    except ResearchVersionIdentityError as exc:
        assert expected_marker in str(exc), str(exc)
        return

    raise AssertionError(
        f"EXPECTED_RESEARCH_VERSION_IDENTITY_ERROR={expected_marker}"
    )


def main() -> None:
    snapshot = _snapshot()

    assert (
        get_metrics_config_version(
            snapshot.resolved_config
        )
        == "RMETRICS-0001"
    )

    print("METRICS_CONFIG_VERSION_METADATA_SOURCE=SUCCESS")

    identity = resolve_metrics_config_identity(snapshot)
    assert identity.version == "RMETRICS-0001"

    print("METRICS_CONFIG_VERSION_IDENTITY_RESOLUTION=SUCCESS")

    _expect_error(
        "METRICS_CONFIG_PROFILE_METADATA_MISSING",
        lambda: get_metrics_config_version({}),
    )

    _expect_error(
        "METRICS_CONFIG_PROFILE_VERSION_MISSING",
        lambda: get_metrics_config_version(
            {"metadata": {}}
        ),
    )

    _expect_error(
        "METRICS_CONFIG_PROFILE_VERSION_FORMAT_INVALID",
        lambda: get_metrics_config_version(
            {
                "metadata": {
                    "metrics_config_version": "INVALID",
                },
            }
        ),
    )

    print("METRICS_CONFIG_VERSION_VALIDATION=SUCCESS")

    conn = FakeConnection()
    run_id = backtest_run_store.create_run(
        conn,
        run_mode="BACKTEST",
        config_snapshot=snapshot,
    )

    assert run_id
    assert conn.commit_count == 1
    assert len(conn.cursor_instance.calls) == 1

    sql, params = conn.cursor_instance.calls[0]
    assert "metrics_config_version" in sql
    assert params is not None
    assert "RMETRICS-0001" in params

    print("RUN_METRICS_CONFIG_VERSION_PERSISTENCE=SUCCESS")

    source = inspect.getsource(
        backtest_run_store.ensure_run_tables
    )
    assert (
        "ADD COLUMN IF NOT EXISTS metrics_config_version"
        in source
    )
    assert (
        "idx_strategy_backtest_run_metrics_config_version"
        in source
    )

    print("RUN_METRICS_CONFIG_VERSION_DDL=SUCCESS")
    print(
        "METRICS_CONFIG_VERSION_CANONICAL_SOURCE="
        "resolved_config.metadata.metrics_config_version"
    )
    print("METRICS_CONFIG_VERSION_CONTRACT_TEST=SUCCESS")


if __name__ == "__main__":
    main()
