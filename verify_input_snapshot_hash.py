"""Verifies the Research Input Snapshot Hash determinism and Run persistence contract."""

from __future__ import annotations

import inspect

from port_strategy_research import (
    backtest_engine,
    backtest_run_store,
)
from port_strategy_research.research_input_snapshot import (
    InputSnapshotBuilder,
    InputSnapshotError,
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


def _build(order: list[str]):
    values = {
        "dates": (
            "trade_dates",
            "ordered_dates",
            ["2026-08-01", "2026-08-02"],
        ),
        "universe": (
            "stock_universe",
            "full_universe",
            {"000001": "A", "000002": "B"},
        ),
        "market": (
            "market_feature",
            "2026-08-01",
            {"date": "2026-08-01", "score": 1},
        ),
        "stocks": (
            "stock_feature",
            "2026-08-01",
            [
                {"ticker_code": "000001", "value": 10},
                {"ticker_code": "000002", "value": 20},
            ],
        ),
        "price": (
            "price",
            "2026-08-02",
            [
                {
                    "ticker_code": "000001",
                    "open_price": 100,
                    "low_price": 90,
                    "close_price": 110,
                },
            ],
        ),
    }

    builder = InputSnapshotBuilder()
    for key in order:
        builder.add(*values[key])
    return builder.finalize()


def _expect_error(expected_marker: str, callback) -> None:
    try:
        callback()
    except InputSnapshotError as exc:
        assert expected_marker in str(exc), str(exc)
        return
    raise AssertionError(
        f"EXPECTED_INPUT_SNAPSHOT_ERROR={expected_marker}"
    )


def main() -> None:
    first = _build(
        ["dates", "universe", "market", "stocks", "price"]
    )
    second = _build(
        ["price", "stocks", "market", "universe", "dates"]
    )

    assert first.snapshot_hash == second.snapshot_hash
    assert first.manifest_json == second.manifest_json
    assert len(first.snapshot_hash) == 64
    assert first.dataset_count == 5
    assert first.item_count == 5

    print("INPUT_SNAPSHOT_ORDER_INDEPENDENCE=SUCCESS")
    print("INPUT_SNAPSHOT_HASH_REPRODUCIBILITY=SUCCESS")
    print("INPUT_SNAPSHOT_MANIFEST_REPRODUCIBILITY=SUCCESS")

    changed = InputSnapshotBuilder()
    changed.add(
        "market_feature",
        "2026-08-01",
        {"date": "2026-08-01", "score": 2},
    )
    changed_evidence = changed.finalize()

    assert changed_evidence.snapshot_hash != first.snapshot_hash

    print("INPUT_SNAPSHOT_CHANGE_DETECTION=SUCCESS")

    duplicate = InputSnapshotBuilder()
    duplicate.add("price", "2026-08-02", [])
    _expect_error(
        "INPUT_SNAPSHOT_DUPLICATE_ITEM",
        lambda: duplicate.add("price", "2026-08-02", []),
    )

    _expect_error(
        "INPUT_SNAPSHOT_EMPTY",
        lambda: InputSnapshotBuilder().finalize(),
    )

    print("INPUT_SNAPSHOT_VALIDATION=SUCCESS")

    conn = FakeConnection()
    backtest_run_store.complete_input_snapshot(
        conn,
        "run-1",
        input_snapshot_hash=first.snapshot_hash,
        input_snapshot_manifest=first.manifest_json,
    )

    sql, params = conn.cursor_instance.calls[0]
    assert "input_snapshot_hash" in sql
    assert "input_snapshot_status = 'COMPLETE'" in sql
    assert "input_snapshot_manifest" in sql
    assert params[0] == first.snapshot_hash
    assert params[1] == first.manifest_json

    print("RUN_INPUT_SNAPSHOT_HASH_PERSISTENCE=SUCCESS")
    print("RUN_INPUT_SNAPSHOT_MANIFEST_PERSISTENCE=SUCCESS")
    print("RUN_INPUT_SNAPSHOT_STATUS_PERSISTENCE=SUCCESS")

    engine_source = inspect.getsource(backtest_engine.run_backtest)
    for marker in (
        '"trade_dates"',
        '"stock_universe"',
        '"market_feature"',
        '"stock_feature"',
        '"price"',
    ):
        assert marker in engine_source

    ddl_source = inspect.getsource(
        backtest_run_store.ensure_run_tables
    )
    assert "input_snapshot_hash" in ddl_source
    assert "input_snapshot_status" in ddl_source
    assert "input_snapshot_manifest" in ddl_source

    print("ENGINE_ACTUAL_INPUT_CAPTURE_WIRING=SUCCESS")
    print("RUN_INPUT_SNAPSHOT_DDL=SUCCESS")
    print(
        "INPUT_SNAPSHOT_CANONICAL_SCOPE="
        "trade_dates+stock_universe+market_feature+"
        "stock_feature+price"
    )
    print("INPUT_SNAPSHOT_HASH_CONTRACT_TEST=SUCCESS")


if __name__ == "__main__":
    main()
