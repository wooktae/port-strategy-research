import pandas as pd

from port_strategy_common.config import BACKTEST_START_DATE


def get_dates(conn):
    sql = """
    SELECT date
    FROM pre_total_market_daily_feature
    WHERE date >= %s
    ORDER BY date
    """
    return pd.read_sql(sql, conn, params=[BACKTEST_START_DATE])["date"].tolist()


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
    return pd.read_sql(sql, conn, params=(date,)).iloc[0].to_dict()


def get_stocks(conn, date):
    sql = """
    SELECT *
    FROM pre_total_stock_daily_feature
    WHERE date = %s
    """
    return pd.read_sql(sql, conn, params=(date,)).to_dict("records")


def get_price(conn, price_date):
    sql = """
        SELECT
            ticker_code,
            open_price,
            low_price,
            close_price
        FROM interest_price_raw
        WHERE price_date = %s
    """
    return pd.read_sql(sql, conn, params=[price_date])
