"""Research Engine Version 분리 계약 검증."""

from __future__ import annotations

import inspect
from unittest.mock import patch

from port_strategy_research import (
    backtest_engine,
    backtest_run_store,
    backtest_trade_log,
)
from port_strategy_research.research_engine_version import (
    RESEARCH_ENGINE_VERSION,
)
from port_strategy_research.research_version_identity import (
    ResearchVersionIdentityError,
    get_runtime_research_engine_version,
    resolve_research_engine_identity,
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
    assert RESEARCH_ENGINE_VERSION == "RESEARCH_V3_EXIT_SOFTENED"
    assert (
        get_runtime_research_engine_version()
        == RESEARCH_ENGINE_VERSION
    )

    print("RESEARCH_ENGINE_VERSION_SOURCE=SUCCESS")

    identity = resolve_research_engine_identity()
    assert identity.runtime_version == RESEARCH_ENGINE_VERSION

    print("RESEARCH_ENGINE_IDENTITY_RESOLUTION=SUCCESS")

    engine_source = inspect.getsource(backtest_engine)
    run_store_source = inspect.getsource(backtest_run_store)
    trade_log_source = inspect.getsource(backtest_trade_log)

    for source in (
        engine_source,
        run_store_source,
        trade_log_source,
    ):
        assert "port_strategy_common.config import ENGINE_VERSION" not in source
        assert "RESEARCH_ENGINE_VERSION" in source

    print("COMMON_ENGINE_VERSION_IMPORT_REMOVED=SUCCESS")
    print("RESEARCH_ENGINE_VERSION_RUNTIME_WIRING=SUCCESS")

    assert "RESEARCH_ENGINE_VERSION," in run_store_source
    assert "RESEARCH_ENGINE_VERSION," in trade_log_source

    print("RUN_RESEARCH_ENGINE_VERSION_PERSISTENCE=SUCCESS")
    print("TRADE_RESEARCH_ENGINE_VERSION_PERSISTENCE=SUCCESS")

    with patch(
        "port_strategy_research.research_version_identity."
        "RESEARCH_ENGINE_VERSION",
        "",
    ):
        _expect_error(
            "RESEARCH_ENGINE_VERSION_EMPTY",
            get_runtime_research_engine_version,
        )

    print("RESEARCH_ENGINE_VERSION_VALIDATION=SUCCESS")
    print(
        "RESEARCH_ENGINE_VERSION_CANONICAL_SOURCE="
        "port_strategy_research.research_engine_version."
        "RESEARCH_ENGINE_VERSION"
    )
    print("RESEARCH_ENGINE_VERSION_CONTRACT_TEST=SUCCESS")


if __name__ == "__main__":
    main()
