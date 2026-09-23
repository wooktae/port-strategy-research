"""Loader module that reads the backtest input Features from the DB."""

import pandas as pd


def get_dates(
    conn,
    *,
    backtest_start_date,
    backtest_end_date=None,
):
    """Queries trading days within the explicitly provided start-date/end-date range."""
    if backtest_end_date is None:
        sql = """
        SELECT date
        FROM pre_total_market_daily_feature
        WHERE date >= %s
        ORDER BY date
        """
        params = [backtest_start_date]
    else:
        sql = """
        SELECT date
        FROM pre_total_market_daily_feature
        WHERE date >= %s
          AND date <= %s
        ORDER BY date
        """
        params = [
            backtest_start_date,
            backtest_end_date,
        ]

    return pd.read_sql(
        sql,
        conn,
        params=params,
    )["date"].tolist()


def load_stock_universe(conn):
    sql = """
    SELECT ticker_code, company_name
    FROM stock_universe
    """
    df = pd.read_sql(sql, conn)
    return dict(zip(df["ticker_code"], df["company_name"]))


def get_market(conn, date):
    sql = """
    SELECT *
    FROM pre_total_market_daily_feature
    WHERE date = %s
    """
    return pd.read_sql(
        sql,
        conn,
        params=(date,),
    ).iloc[0].to_dict()


def get_stocks(conn, date):
    sql = """
    SELECT *
    FROM pre_total_stock_daily_feature
    WHERE date = %s
    """
    return pd.read_sql(
        sql,
        conn,
        params=(date,),
    ).to_dict("records")


def get_price(conn, price_date):
    """Returns only Price Rows that actually exist on the given date, without any imputation."""
    sql = """
        SELECT
            ticker_code,
            open_price,
            low_price,
            close_price
        FROM interest_price_raw
        WHERE price_date = %s
    """
    return pd.read_sql(
        sql,
        conn,
        params=[price_date],
    )
