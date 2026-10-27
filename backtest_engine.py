"""Engine module that runs the backtest date loop."""

from __future__ import annotations

from typing import Any

from port_strategy_research.backtest_buy_logic import process_buy
from port_strategy_research.backtest_loader import (
    get_dates,
    get_market,
    get_price,
    get_stocks,
    load_stock_universe,
)
from port_strategy_research.backtest_position_manager import (
    process_existing_positions,
)
from port_strategy_research.backtest_run_store import (
    insert_daily_positions,
    insert_daily_result,
)
from port_strategy_research.research_backtest_filter_adapter import (
    filter_buy_candidates,
)
from port_strategy_research.research_backtest_market_adapter import (
    evaluate_market,
)
from port_strategy_research.research_engine_version import (
    RESEARCH_ENGINE_VERSION,
)
from port_strategy_research.research_input_snapshot import (
    InputSnapshotBuilder,
)


REQUIRED_CONFIG_CATEGORIES = {
    "market",
    "filter",
    "sizing",
    "buy_guard",
    "buy",
    "sell",
    "backtest_policy",
    "metrics",
}


def _validate_resolved_config(
    resolved_config: dict[str, Any],
) -> None:
    missing = sorted(
        REQUIRED_CONFIG_CATEGORIES - set(resolved_config)
    )
    if missing:
        raise ValueError(
            "BACKTEST_RESOLVED_CONFIG_MISSING_CATEGORY="
            + ",".join(missing)
        )


def run_backtest(
    conn,
    run_id,
    resolved_config: dict[str, Any],
    backtest_start_date,
    backtest_end_date=None,
    *,
    strategy_config_version: str,
    config_hash: str,
    input_snapshot_builder: InputSnapshotBuilder | None = None,
):
    """Injects the same Config and Config Identity into the full trading-day execution path."""
    _validate_resolved_config(resolved_config)

    if not strategy_config_version:
        raise ValueError("BACKTEST_STRATEGY_CONFIG_VERSION_REQUIRED")
    if len(config_hash) != 64:
        raise ValueError("BACKTEST_CONFIG_HASH_INVALID")

    market_config = resolved_config["market"]
    filter_config = resolved_config["filter"]
    sizing_config = resolved_config["sizing"]
    buy_guard_config = resolved_config["buy_guard"]
    buy_config = resolved_config["buy"]
    sell_config = resolved_config["sell"]
    backtest_policy = resolved_config["backtest_policy"]

    print(
        "RESEARCH ENGINE VERSION =",
        RESEARCH_ENGINE_VERSION,
        __file__,
    )

    if backtest_end_date is None:
        dates = get_dates(
            conn,
            backtest_start_date=backtest_start_date,
        )
    else:
        dates = get_dates(
            conn,
            backtest_start_date=backtest_start_date,
            backtest_end_date=backtest_end_date,
        )
    if input_snapshot_builder is not None:
        input_snapshot_builder.add(
            "trade_dates",
            "ordered_dates",
            dates,
        )

    total_return = 1.0
    history = []
    positions = {}
    risk_off_flag = False
    company_map = load_stock_universe(conn)

    if input_snapshot_builder is not None:
        input_snapshot_builder.add(
            "stock_universe",
            "full_universe",
            company_map,
        )

    for index in range(len(dates) - 1):
        today = str(dates[index])
        tomorrow = str(dates[index + 1])

        market = get_market(conn, today)
        stocks = get_stocks(conn, today)

        if input_snapshot_builder is not None:
            input_snapshot_builder.add(
                "market_feature",
                today,
                market,
            )
            input_snapshot_builder.add(
                "stock_feature",
                today,
                stocks,
            )

        decision = evaluate_market(
            market,
            market_config=market_config,
        )
        candidates = filter_buy_candidates(
            stocks,
            decision,
            filter_config=filter_config,
        )

        price_tomorrow_df = get_price(conn, tomorrow)

        if input_snapshot_builder is not None:
            price_rows = price_tomorrow_df.to_dict("records")
            input_snapshot_builder.add(
                "price",
                tomorrow,
                price_rows,
            )

        price_tomorrow_map = {
            row["ticker_code"]: {
                "open": row["open_price"],
                "low": row["low_price"],
                "close": row["close_price"],
            }
            for _, row in price_tomorrow_df.iterrows()
        }

        (
            positions,
            sold_today,
            sold_count_today,
            sold_returns,
            held_returns,
        ) = process_existing_positions(
            conn=conn,
            positions=positions,
            stocks=stocks,
            decision=decision,
            company_map=company_map,
            execution_date=tomorrow,
            price_map=price_tomorrow_map,
            run_id=run_id,
            sell_config=sell_config,
            backtest_policy=backtest_policy,
            strategy_config_version=strategy_config_version,
            config_hash=config_hash,
        )

        (
            positions,
            bought_count_today,
            bought_returns,
        ) = process_buy(
            conn=conn,
            positions=positions,
            candidates=candidates,
            decision=decision,
            sold_today=sold_today,
            risk_off_flag=risk_off_flag,
            today=tomorrow,
            company_map=company_map,
            price_map=price_tomorrow_map,
            run_id=run_id,
            sizing_config=sizing_config,
            buy_guard_config=buy_guard_config,
            buy_config=buy_config,
            backtest_policy=backtest_policy,
            strategy_config_version=strategy_config_version,
            config_hash=config_hash,
        )

        daily_ret = 0.0
        for result in held_returns:
            daily_ret += float(result["size"]) * float(result["ret"])
        for result in sold_returns:
            daily_ret += float(result["size"]) * float(result["ret"])
        for result in bought_returns:
            daily_ret += float(result["size"]) * float(result["ret"])

        total_return *= 1 + daily_ret
        risk_off_flag = daily_ret <= float(
            backtest_policy["risk_off_trigger_daily_return"]
        )

        row = {
            "date": tomorrow,
            "market_signal": decision.signal_type,
            "position_count": len(positions),
            "daily_return": daily_ret,
            "cum_return": total_return,
        }

        history.append(row)
        insert_daily_result(conn, run_id, row)
        insert_daily_positions(
            conn,
            run_id,
            tomorrow,
            positions,
            company_map,
        )

        print(
            f"{today} -> {tomorrow} | "
            f"signal={decision.signal_type} | "
            f"buy={bought_count_today} | "
            f"sell={sold_count_today} | "
            f"pos={len(positions)} | "
            f"daily={daily_ret:.4f} | "
            f"cum={total_return:.4f}"
        )

        conn.commit()

    return history
