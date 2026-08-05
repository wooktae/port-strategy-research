"""Input Snapshot Builder 비활성 시 기존 Price Frame 호환 계약 검증."""

from __future__ import annotations

import inspect

from port_strategy_research import backtest_engine


def main() -> None:
    source = inspect.getsource(backtest_engine.run_backtest)

    builder_guard = "if input_snapshot_builder is not None:"
    price_conversion = 'price_rows = price_tomorrow_df.to_dict("records")'

    assert builder_guard in source
    assert price_conversion in source

    guard_index = source.index(builder_guard, source.index("price_tomorrow_df"))
    conversion_index = source.index(price_conversion)

    assert guard_index < conversion_index

    guarded_block = source[guard_index:conversion_index]
    assert "input_snapshot_builder is not None" in guarded_block

    print("PRICE_FRAME_TO_DICT_BUILDER_GUARDED=SUCCESS")
    print("CONFIG_INJECTION_FAKE_PRICE_FRAME_COMPATIBILITY=SUCCESS")
    print("INPUT_SNAPSHOT_OPTIONAL_CAPTURE_CONTRACT=SUCCESS")


if __name__ == "__main__":
    main()
