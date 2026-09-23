"""Computes backtest performance metrics using an explicit Metrics Config."""

from __future__ import annotations

from typing import Any

import numpy as np


def _validate_metrics_config(
    metrics_config: dict[str, Any],
) -> None:
    required = {
        "risk_free_rate",
        "trading_days_per_year",
    }
    missing = sorted(required - set(metrics_config))
    if missing:
        raise ValueError(
            "METRICS_CONFIG_MISSING_KEY="
            + ",".join(missing)
        )


def calculate_mdd(
    df,
    *,
    metrics_config: dict[str, Any],
):
    """Computes MDD while verifying the same-execution Metrics Config contract."""
    _validate_metrics_config(metrics_config)

    result = df.copy()
    result["peak"] = result["cum_return"].cummax()
    result["drawdown"] = (
        result["cum_return"] - result["peak"]
    ) / result["peak"]
    return result["drawdown"].min()


def calculate_sharpe(
    df,
    *,
    metrics_config: dict[str, Any],
):
    """Computes Sharpe using the explicit risk-free rate and trading days per year."""
    _validate_metrics_config(metrics_config)

    risk_free_rate = float(
        metrics_config["risk_free_rate"]
    )
    trading_days_per_year = int(
        metrics_config["trading_days_per_year"]
    )

    daily_returns = df["daily_return"]
    if len(daily_returns) < 2:
        return 0

    daily_rf = risk_free_rate / trading_days_per_year
    excess_returns = daily_returns - daily_rf

    mean_return = excess_returns.mean()
    std_return = excess_returns.std()

    if std_return == 0:
        return 0

    return (
        mean_return
        / std_return
        * np.sqrt(trading_days_per_year)
    )
