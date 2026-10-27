"""Verifies the create_run Artifact Identity backward-compatibility contract."""

from __future__ import annotations

from pathlib import Path

from port_strategy_research import backtest_run_store
from port_strategy_research.strategy_config_snapshot import (
    StrategyConfigSnapshot,
)


class FakeCursor:
    def __init__(self) -> None:
        self.calls = []

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

    def cursor(self):
        return self.cursor_instance

    def commit(self) -> None:
        self.commit_count += 1


def main() -> None:
    snapshot = StrategyConfigSnapshot(
        strategy_config_version="RSCFG-0001",
        resolved_config={
            "metadata": {
                "strategy_config_version": "RSCFG-0001",
                "metrics_config_version": "RMETRICS-0001",
            },
        },
        canonical_json="{}",
        config_hash="0" * 64,
        profile_path=Path("strategy_profiles/RSCFG-0001.json"),
    )

    conn = FakeConnection()
    run_id = backtest_run_store.create_run(
        conn,
        run_mode="BACKTEST",
        config_snapshot=snapshot,
    )

    assert run_id
    sql, params = conn.cursor_instance.calls[0]
    assert params is not None
    assert "UNRESOLVED" in params
    assert None in params
    assert "artifact_identity_status" in sql

    print("CREATE_RUN_ARTIFACT_IDENTITY_OPTIONAL=SUCCESS")
    print("CREATE_RUN_DEFAULT_ARTIFACT_STATUS=UNRESOLVED")
    print("ARTIFACT_IDENTITY_BACKWARD_COMPATIBILITY=SUCCESS")


if __name__ == "__main__":
    main()
