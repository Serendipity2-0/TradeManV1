import pandas as pd
import os
from dotenv import load_dotenv
import sys
import sqlite3

# Set up directory and load environment variables
DIR = os.getcwd()
sys.path.append(DIR)
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

# Import custom utilities
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.EquityCenter.EquityCenterUtils import (
    calculate_sma,
    indicator_rsi,
    read_stock_data_from_db,
    calculate_ema,
)

# Initialize logger
logger = LoggerSetup()
MID_TFMOMENTUM = os.getenv("MID_TFMOMENTUM")
MID_TFEMA = os.getenv("MID_TFEMA")


def get_midterm_stocks_df():
    tfmomentum_stocks_df = perform_tfmomentum_strategy()
    tfema_stocks_df = perform_tfema_strategy()
    return tfmomentum_stocks_df, tfema_stocks_df


def perform_tfmomentum_strategy():
    """
    Main function to orchestrate the fetching and processing of stock data.
    """
    try:
        # Define paths to the databases
        stock_db_path = os.getenv(
            "equity_stock_data_db_path"
        )  # Path to stock data database
        financial_db_path = os.getenv(
            "financial_db_path"
        )  # Path to financial data database
        # Fetch stock data from the database
        stock_data_dict = read_stock_data_from_db(stock_db_path)
        if not stock_data_dict:
            logger.error("Failed to retrieve stock data from the database.")
            return pd.DataFrame()

        all_stock_df = []
        for stock_code, stock_data in stock_data_dict.items():
            # Establish connection to the SQLite database
            conn = sqlite3.connect(financial_db_path)
            query = f"SELECT * FROM financials WHERE Symbol = '{stock_code}'"
            financial_data = pd.read_sql_query(query, conn)
            conn.close()
            if financial_data.empty:
                logger.info(f"No financial data found for {stock_code}")
                continue

            # Convert list data to DataFrame for easier processing (example for daily data)
            stock_data_df = pd.DataFrame(stock_data["daily_data"])
            stock_data_df["SMA_20"] = calculate_sma(stock_data_df["Close"], 20)
            stock_data_df["RSI_14"] = indicator_rsi(stock_data_df, 14, "Close")
            df = pd.DataFrame(
                {
                    "Symbol": [stock_code],
                    "SMA_20": [stock_data_df["SMA_20"].iloc[-1]],
                    "RSI_14": [stock_data_df["RSI_14"].iloc[-1]],
                    "Gross Profit Growth": [
                        financial_data["Gross Profit Growth"].iloc[-1]
                    ],
                    "Net Income": [financial_data["Net Income"].iloc[-1]],
                    "Total Revenue": [financial_data["Total Revenue"].iloc[-1]],
                }
            )
            all_stock_df.append(df)

        if all_stock_df:
            combined_stock_df = pd.concat(all_stock_df)
            # Initialize the Mid_Strat column
            combined_stock_df[MID_TFMOMENTUM] = 0
            # Define the criteria as a separate variable for readability
            criteria = (
                (combined_stock_df["RSI_14"] >= 50)
                & (combined_stock_df["RSI_14"] <= 55)
                & (combined_stock_df["Gross Profit Growth"] > 10**9)
                & (combined_stock_df["Net Income"] > 10**8)
                & (combined_stock_df["SMA_20"] > 200)
                & (combined_stock_df["Total Revenue"] > 10**9)
            )
            # Apply the criteria
            combined_stock_df.loc[criteria, MID_TFMOMENTUM] = 1
            return combined_stock_df

    except Exception as e:
        logger.error(f"An error occurred in the main function: {e}")
        return pd.DataFrame()


def perform_tfema_strategy():
    """
    Apply a strategy based on multiple EMA filters and other financial metrics.
    """
    try:
        stock_db_path = os.getenv(
            "equity_stock_data_db_path"
        )  # Path to stock data database
        financial_db_path = os.getenv(
            "financial_db_path"
        )  # Path to financial data database

        # Fetch stock data
        stock_data_dict = read_stock_data_from_db(stock_db_path)
        if not stock_data_dict:
            logger.error("Failed to retrieve stock data from the database.")
            return pd.DataFrame()

        all_stock_df = []
        for stock_code, stock_data in stock_data_dict.items():
            # Fetch financial data
            conn = sqlite3.connect(financial_db_path)
            query = f"SELECT * FROM financials WHERE Symbol = '{stock_code}'"
            financial_data = pd.read_sql_query(query, conn)
            conn.close()
            if financial_data.empty:
                logger.info(f"No financial data found for {stock_code}")
                continue

            stock_data_df = pd.DataFrame(stock_data["daily_data"])
            stock_data_df["EMA_9"] = calculate_ema(stock_data_df["Close"], 9)
            stock_data_df["EMA_21"] = calculate_ema(stock_data_df["Close"], 21)
            stock_data_df["EMA_63"] = calculate_ema(stock_data_df["Close"], 63)
            stock_data_df["EMA_200"] = calculate_ema(stock_data_df["Close"], 200)
            stock_data_df["RSI_14"] = indicator_rsi(stock_data_df, 14, "Close")
            stock_data_df["SMA_20_Volume"] = calculate_sma(stock_data_df["Volume"], 20)

            # Combine the latest technical indicators with financial data
            df = pd.DataFrame(
                {
                    "Symbol": [stock_code],
                    "EMA_9": [stock_data_df["EMA_9"].iloc[-1]],
                    "EMA_21": [stock_data_df["EMA_21"].iloc[-1]],
                    "EMA_63": [stock_data_df["EMA_63"].iloc[-1]],
                    "EMA_200": [stock_data_df["EMA_200"].iloc[-1]],
                    "RSI_14": [stock_data_df["RSI_14"].iloc[-1]],
                    "SMA_20_Volume": [stock_data_df["SMA_20_Volume"].iloc[-1]],
                    "Close": [stock_data_df["Close"].iloc[-1]],
                    "Volume": [stock_data_df["Volume"].iloc[-1]],
                    "Market Cap": [financial_data["Market Cap"].iloc[-1]],
                    "Return on Equity": [financial_data["Return on Equity"].iloc[-1]],
                }
            )
            all_stock_df.append(df)
        if all_stock_df:
            combined_stock_df = pd.concat(all_stock_df)
            combined_stock_df[MID_TFEMA] = 0
            # Define the criteria as a separate variable for readability
            criteria = (
                (combined_stock_df["Close"] > combined_stock_df["EMA_9"])
                & (combined_stock_df["EMA_9"] > combined_stock_df["EMA_21"])
                & (combined_stock_df["EMA_21"] > combined_stock_df["EMA_63"])
                & (combined_stock_df["EMA_63"] > combined_stock_df["EMA_200"])
                & (combined_stock_df["RSI_14"] >= 55)
                & (combined_stock_df["Volume"] > 2 * combined_stock_df["SMA_20_Volume"])
                & (combined_stock_df["Market Cap"] >= 999)
                & (combined_stock_df["Return on Equity"] >= 16)
            )
            # Apply the criteria
            combined_stock_df.loc[criteria, MID_TFEMA] = 1
            return combined_stock_df

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return pd.DataFrame()


if __name__ == "__main__":
    get_midterm_stocks_df()
