import pandas as pd
import os
from dotenv import load_dotenv
import sys
import sqlite3

DIR = os.getcwd()
sys.path.append(DIR)
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.EquityCenter.EquityCenterUtils import (
    get_financial_data,
    get_stock_codes,
)
logger = LoggerSetup()

financial_db_path = os.getenv("financial_db_path")

def get_longterm_stocks_df():
    """
    Get long-term stocks data.

    Returns:
        tuple: Tuple containing:
            pandas.DataFrame: Stock financial data.
            pandas.DataFrame: Stock ratio data.
    """
    stock_codes = get_stock_codes()
    stock_financial_data_df = get_financial_data(stock_codes)
    if not stock_financial_data_df.empty:
        # SQLite database path
        table_name = "financials"
        try:
            conn = sqlite3.connect(financial_db_path)
            stock_financial_data_df.to_sql(
                table_name, conn, if_exists="replace", index=False
            )
            logger.debug(f"Data uploaded to {table_name} table in {financial_db_path}")
        except Exception as e:
            logger.error(f"Error uploading data to SQLite: {e}")
        finally:
            conn.close()

        combo_stocks_df = perform_combo_strategy(db_path=financial_db_path)
        ratio_stocks_df = perform_ratio_strategy(db_path=financial_db_path)
        return combo_stocks_df, ratio_stocks_df
    
# Define the fundamental ratio strategy
def perform_ratio_strategy(
    db_path,
    market_cap_threshold=10e9,
    pe_ratio_threshold=20,
    pb_ratio_threshold=3,
    dividend_yield_threshold=0.02,
):
    """
    Shortlist stocks based on fundamental criteria.

    Args:
        db_path (str): Path to the SQLite database.
        market_cap_threshold (float): Minimum market cap threshold (default: 10 billion).
        pe_ratio_threshold (float): Maximum P/E ratio threshold (default: 20).
        pb_ratio_threshold (float): Maximum P/B ratio threshold (default: 3).
        dividend_yield_threshold (float): Minimum dividend yield threshold (default: 2%).

    Returns:
        DataFrame: DataFrame containing all stocks with an additional column 'Long_Ratio' indicating shortlisted status.
    """
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(db_path)

        # Query financial data from the database
        query = """
        SELECT
            Symbol,
            [Market Cap],
            [P/E Ratio],
            [P/B Ratio],
            [Dividend Yield]
        FROM
            financials
        """
        df = pd.read_sql(query, conn)

        # Apply filtering criteria and add Long_Ratio column
        df["Long_Ratio"] = 0
        shortlisted_df = df[
            (df["Market Cap"] > market_cap_threshold)
            & (df["P/E Ratio"] < pe_ratio_threshold)
            & (df["P/B Ratio"] < pb_ratio_threshold)
            & (df["Dividend Yield"] > dividend_yield_threshold)
        ]
        df.loc[shortlisted_df.index, "Long_Ratio"] = 1

        conn.close()

        return df

    except Exception as e:
        logger.error(f"Error in shortlisting stocks: {e}")
        return pd.DataFrame()


# Define the combined strategy function
def perform_combo_strategy(
    db_path,
    market_cap_threshold=10e9,
    f_score_threshold=7,
    pe_ratio_threshold=20,
    pb_ratio_threshold=3,
    op_profit_margin_threshold=0.15,
    debt_to_equity_threshold=0.5,
    gross_profit_growth_threshold=0.1,
):
    """
    Shortlist stocks based on a combined fundamental strategy.

    Args:
        db_path (str): Path to the SQLite database.
        market_cap_threshold (float): Minimum market cap threshold (default: 10 billion).
        f_score_threshold (int): Minimum Piotroski F-Score threshold (default: 7).
        pe_ratio_threshold (float): Maximum P/E ratio threshold (default: 20).
        pb_ratio_threshold (float): Maximum P/B ratio threshold (default: 3).
        op_profit_margin_threshold (float): Minimum operating profit margin threshold (default: 15%).
        debt_to_equity_threshold (float): Maximum debt-to-equity ratio threshold (default: 0.5).
        gross_profit_growth_threshold (float): Minimum gross profit growth threshold (default: 10%).

    Returns:
        DataFrame: DataFrame containing all stocks with an additional column 'Long_Combo' indicating shortlisted status.
    """
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(db_path)

        # Query financial data from the database
        query = """
        SELECT
            Symbol,
            [Market Cap],
            [Piotroski F-Score],
            [P/E Ratio],
            [P/B Ratio],
            [Operating Profit Margin],
            [Debt to Equity],
            [Gross Profit Growth]
        FROM
            financials
        """
        df = pd.read_sql(query, conn)

        # Apply filtering criteria and add Long_Combo column
        df["Long_Combo"] = 0
        shortlisted_df = df[
            (df["Market Cap"] > market_cap_threshold)
            & (df["Piotroski F-Score"] >= f_score_threshold)
            & (df["P/E Ratio"] < pe_ratio_threshold)
            & (df["P/B Ratio"] < pb_ratio_threshold)
            & (df["Operating Profit Margin"] > op_profit_margin_threshold)
            & (df["Debt to Equity"] < debt_to_equity_threshold)
            & (df["Gross Profit Growth"] > gross_profit_growth_threshold)
        ]
        df.loc[shortlisted_df.index, "Long_Combo"] = 1

        conn.close()

        return df

    except Exception as e:
        logger.error(f"Error in shortlisting stocks: {e}")
        return pd.DataFrame()
