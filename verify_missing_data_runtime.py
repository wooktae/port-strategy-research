"""결측 입력 Snapshot과 로컬 단기 실행 범위 계약 검증."""

from __future__ import annotations

import inspect
import json
from decimal import Decimal

import numpy as np
import pandas as pd

from port_strategy_research import (
    backtest_loader,
    backtest_research_run,
)
from port_strategy_research.research_input_snapshot import (
    InputSnapshotBuilder,
    SPECIAL_VALUE_KEY,
)


def main() -> None:
    first = InputSnapshotBuilder()
    first.add(
        "price",
        "2026-08-04",
        [
            {
                "ticker_code": "000001",
                "open_price": np.nan,
                "low_price": pd.NA,
                "close_price": Decimal("Infinity"),
            },
            {
                "ticker_code": "000002",
                "open_price": None,
                "low_price": float("-inf"),
                "close_price": 0.0,
            },
        ],
    )
    evidence_1 = first.finalize()

    second = InputSnapshotBuilder()
    second.add(
        "price",
        "2026-08-04",
        [
            {
                "close_price": Decimal("Infinity"),
                "low_price": pd.NA,
                "open_price": np.float64("nan"),
                "ticker_code": "000001",
            },
            {
                "close_price": 0.0,
                "low_price": float("-inf"),
                "open_price": None,
                "ticker_code": "000002",
            },
        ],
    )
    evidence_2 = second.finalize()

    assert evidence_1.snapshot_hash == evidence_2.snapshot_hash
    assert evidence_1.special_value_count == 4

    manifest = json.loads(evidence_1.manifest_json)
    assert manifest["missing_data_contract"]["imputation"] == "disabled"
    assert (
        manifest["missing_data_contract"]["missing_price_row"]
        == "preserved_as_absent_row_without_imputation"
    )
    assert manifest["special_value_count"] == 4

    print("INPUT_SNAPSHOT_NAN_CANONICALIZATION=SUCCESS")
    print("INPUT_SNAPSHOT_PANDAS_NA_CANONICALIZATION=SUCCESS")
    print("INPUT_SNAPSHOT_INFINITY_CANONICALIZATION=SUCCESS")
    print("INPUT_SNAPSHOT_MISSING_VALUE_REPRODUCIBILITY=SUCCESS")
    print("INPUT_SNAPSHOT_ZERO_NOT_MISSING=SUCCESS")
    print("MISSING_PRICE_ROW_IMPUTATION_DISABLED=SUCCESS")

    loader_source = inspect.getsource(backtest_loader.get_dates)
    assert "backtest_end_date=None" in loader_source
    assert "date <= %s" in loader_source
    assert "get_price" in dir(backtest_loader)

    parser_source = inspect.getsource(backtest_research_run.parse_args)
    assert "--backtest-start-date" in parser_source
    assert "--backtest-end-date" in parser_source
    assert "--skip-extended-analysis" in parser_source

    start_date, end_date = (
        backtest_research_run._resolve_backtest_date_range(
            type(
                "Args",
                (),
                {
                    "backtest_start_date": "2026-07-01",
                    "backtest_end_date": "2026-07-31",
                },
            )()
        )
    )
    assert start_date.isoformat() == "2026-07-01"
    assert end_date is not None
    assert end_date.isoformat() == "2026-07-31"

    print("BACKTEST_START_DATE_CLI=SUCCESS")
    print("BACKTEST_END_DATE_CLI=SUCCESS")
    print("BACKTEST_DATE_RANGE_LOADER_FILTER=SUCCESS")
    print("EXTENDED_ANALYSIS_SKIP_CLI=SUCCESS")
    print(
        "LOCAL_RUNTIME_FAST_PATH="
        "--backtest-start-date+--backtest-end-date+"
        "--skip-extended-analysis"
    )
    print("MISSING_DATA_RUNTIME_CONTRACT_TEST=SUCCESS")


if __name__ == "__main__":
    main()
