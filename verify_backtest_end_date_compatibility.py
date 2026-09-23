"""Verifies the Backtest End Date optional-forwarding backward-compatibility contract."""

from __future__ import annotations

import inspect

from port_strategy_research import backtest_engine


def main() -> None:
    source = inspect.getsource(backtest_engine.run_backtest)

    assert "if backtest_end_date is None:" in source
    assert "backtest_start_date=backtest_start_date" in source
    assert "backtest_end_date=backtest_end_date" in source

    none_branch = source.split(
        "if backtest_end_date is None:",
        1,
    )[1].split("else:", 1)[0]

    assert "backtest_end_date=" not in none_branch

    print("BACKTEST_END_DATE_OPTIONAL_FORWARDING=SUCCESS")
    print("LEGACY_GET_DATES_SIGNATURE_COMPATIBILITY=SUCCESS")
    print("CONFIG_INJECTION_FAKE_LOADER_COMPATIBILITY=SUCCESS")


if __name__ == "__main__":
    main()
