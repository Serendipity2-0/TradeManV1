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
from Executor.NSEStrategies.Equity.LongTerm.LongTerm import longterm_obj


logger = LoggerSetup()
LONG_RATIO = "Long_Ratio"
LONG_COMBO = "Long_Combo"

FINANCIAL_DB_PATH = os.getenv("FINANCIAL_DB_PATH")

#config
# Accessing the values from longterm_obj for Ratio thresholds
RATIO_MARKET_CAP_THRESHOLD = longterm_obj.ExtraInformation.RatioMarketCapThreshold
RATIO_PE_THRESHOLD = longterm_obj.ExtraInformation.RatioPEThreshold
RATIO_PB_THRESHOLD = longterm_obj.ExtraInformation.RatioPBThreshold
RATIO_DIVIDEND_YIELD_THRESHOLD = longterm_obj.ExtraInformation.RatioDividendYieldThreshold

# Accessing the values from longterm_obj for Combo thresholds
COMBO_MARKET_CAP_THRESHOLD = longterm_obj.ExtraInformation.ComboMarketCapThreshold
COMBO_F_SCORE_THRESHOLD = longterm_obj.ExtraInformation.ComboFScoreThreshold
COMBO_PE_THRESHOLD = longterm_obj.ExtraInformation.ComboPEThreshold
COMBO_PB_THRESHOLD = longterm_obj.ExtraInformation.ComboPBThreshold
COMBO_OP_PROFIT_MARGIN_THRESHOLD = longterm_obj.ExtraInformation.ComboOpProfitMarginThreshold
COMBO_DEBT_TO_EQUITY_THRESHOLD = longterm_obj.ExtraInformation.ComboDebtToEquityThreshold
COMBO_GROSS_PROFIT_THRESHOLD = longterm_obj.ExtraInformation.ComboGrossProfitThreshold

def get_longterm_stocks_df():
    """
    Get long-term stocks data.

    Returns:
        tuple: Tuple containing:
            pandas.DataFrame: Stock financial data.
            pandas.DataFrame: Stock ratio data.
    """
    combo_stocks_df = perform_combo_strategy(db_path=FINANCIAL_DB_PATH)
    ratio_stocks_df = perform_ratio_strategy(db_path=FINANCIAL_DB_PATH)
    return combo_stocks_df, ratio_stocks_df


# Define the fundamental ratio strategy
def perform_ratio_strategy(
    db_path
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
        df[LONG_RATIO] = 0
        shortlisted_df = df[
            (df["Market Cap"] > RATIO_MARKET_CAP_THRESHOLD)
            & (df["P/E Ratio"] < RATIO_PE_THRESHOLD)
            & (df["P/B Ratio"] < RATIO_PB_THRESHOLD)
            & (df["Dividend Yield"] > RATIO_DIVIDEND_YIELD_THRESHOLD)
        ]
        df.loc[shortlisted_df.index, LONG_RATIO] = 1

        conn.close()

        return df

    except Exception as e:
        logger.error(f"Error in shortlisting stocks: {e}")
        return pd.DataFrame()


# Define the combined strategy function
def perform_combo_strategy(
    db_path
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
        df[LONG_COMBO] = 0
        shortlisted_df = df[
            (df["Market Cap"] > COMBO_MARKET_CAP_THRESHOLD)
            & (df["Piotroski F-Score"] >= COMBO_F_SCORE_THRESHOLD)
            & (df["P/E Ratio"] < COMBO_PE_THRESHOLD)
            & (df["P/B Ratio"] < COMBO_PB_THRESHOLD)
            & (df["Operating Profit Margin"] > COMBO_OP_PROFIT_MARGIN_THRESHOLD)
            & (df["Debt to Equity"] < COMBO_DEBT_TO_EQUITY_THRESHOLD)
            & (df["Gross Profit Growth"] > COMBO_GROSS_PROFIT_THRESHOLD)
        ]
        df.loc[shortlisted_df.index, LONG_COMBO] = 1
        conn.close()

        return df

    except Exception as e:
        logger.error(f"Error in shortlisting stocks: {e}")
        return pd.DataFrame()


if __name__ == "__main__":
    get_longterm_stocks_df()
