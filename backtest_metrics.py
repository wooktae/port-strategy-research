"""백테스트 일별 수익률 DataFrame에서 성과 지표를 계산하는 모듈."""

import numpy as np

from port_strategy_common.config import RISK_FREE_RATE, TRADING_DAYS_PER_YEAR


def calculate_mdd(df):
    df = df.copy()
    df["peak"] = df["cum_return"].cummax()
    df["drawdown"] = (df["cum_return"] - df["peak"]) / df["peak"]
    return df["drawdown"].min()


def calculate_sharpe(df, risk_free_rate=RISK_FREE_RATE):
    daily_returns = df["daily_return"]
    if len(daily_returns) < 2:
        return 0

    daily_rf = risk_free_rate / TRADING_DAYS_PER_YEAR
    excess_returns = daily_returns - daily_rf

    mean_return = excess_returns.mean()
    std_return = excess_returns.std()

    if std_return == 0:
        return 0

    return mean_return / std_return * np.sqrt(TRADING_DAYS_PER_YEAR)
