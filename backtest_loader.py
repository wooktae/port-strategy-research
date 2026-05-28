"""백테스트 입력 feature를 DB에서 읽어오는 loader 모듈.

시장 feature, 종목 feature, 다음 거래일 가격, 종목 universe를 조회한다.
읽기 전용 SQL helper지만 실제 DB connection을 넘겨받아 실행하므로
백테스트 실행 흐름 안에서만 대상 DB를 확인한 뒤 사용한다.
"""

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
