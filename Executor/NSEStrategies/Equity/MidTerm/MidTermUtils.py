import pandas as pd
import os
from dotenv import load_dotenv
import sys
import sqlite3
import yfinance as yf

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
from Executor.NSEStrategies.Equity.MidTerm.MidTermConfig import (
    TFMOMENTUM_SMA_VALUE,
    TFMOMENTUM_RSI_UPPER_THRESHOLD,
    TFMOMENTUM_RSI_LOWER_THRESHOLD,
    TFMOMENTUM_GROSS_PROFIT_GROWTH,
    TFMOMENTUM_NET_INCOME,
    TFMOMENTUM_TOTAL_REVENUE,
    TFMOMENTUM_EMA_THRESHOLD,
    TFEMA_SHORT_EMA_VALUE,
    TFEMA_SMALL_EMA_VALUE,
    TFEMA_MEDIUM_EMA_VALUE,
    TFEMA_LARGE_EMA_VALUE,
    TFEMA_SMA_VALUE,
    TFEMA_RSI_UPPER_THRESHOLD,
    TFEMA_MARKET_CAP_THRESHOLD,
    TFEMA_VOLUME_MULTIPLIER,
    TFEMA_ROE_THRESHOLD,
    EQUITY_STOCK_DATA_DB_PATH,
    FINANCIAL_DB_PATH,
    MID_TFMOMENTUM,
    MID_TFEMA,
)

# Initialize logger
logger = LoggerSetup()


def get_financial_data(stock_code):
    """
    Get financial data for a stock from yfinance.

    Args:
        stock_code (str): Stock symbol

    Returns:
        dict: Financial data dictionary
    """
    try:
        stock = yf.Ticker(f"{stock_code}.NS")
        info = stock.info
        if not info:
            logger.warning(f"No info data found for {stock_code}")
            return None

        cashflow = stock.cashflow
        if cashflow.empty:
            logger.warning(f"No cashflow data found for {stock_code}")
            return None

        # Extract financial metrics
        total_revenue = info.get("totalRevenue", 0)
        operating_cashflow = cashflow.loc["Operating Cash Flow"].iloc[0] if "Operating Cash Flow" in cashflow.index else 0
        total_debt = info.get("totalDebt", 0)
        book_value_per_share = info.get("bookValue", 0)
        shares_outstanding = info.get("sharesOutstanding", 0)
        revenue_growth = info.get("revenueGrowth", 0)
        market_cap = info.get("marketCap", 0)
        net_income = info.get("netIncomeToCommon", 0)
        eps = info.get("trailingEps", 0)
        pe_ratio = info.get("trailingPE", 0)
        pb_ratio = info.get("priceToBook", 0)
        dividend_yield = info.get("dividendYield", 0)
        total_cash = info.get("totalCash", 0)
        ebitda = info.get("ebitda", 0)
        roe = info.get("returnOnEquity", 0)

        # Calculate additional metrics
        operating_profit_margin = (operating_cashflow / total_revenue) if total_revenue and operating_cashflow else 0
        equity = (book_value_per_share * shares_outstanding) if book_value_per_share and shares_outstanding else 0
        debt_to_equity = (total_debt / equity) if equity and total_debt else 0
        gross_profit_growth = revenue_growth  # Simplified assumption

        # Construct financial data dictionary
        return {
            "Symbol": stock_code,
            "Market Cap": market_cap,
            "Total Revenue": total_revenue,
            "Net Income": net_income,
            "EPS": eps,
            "P/E Ratio": pe_ratio,
            "P/B Ratio": pb_ratio,
            "Dividend Yield": dividend_yield,
            "Operating Cashflow": operating_cashflow,
            "Total Debt": total_debt,
            "Cash": total_cash,
            "EBITDA": ebitda,
            "Operating Profit Margin": operating_profit_margin,
            "Debt to Equity": debt_to_equity,
            "Gross Profit Growth": gross_profit_growth,
            "Return on Equity": roe,
        }
    except Exception as e:
        logger.error(f"Error fetching financial data for {stock_code}: {e}")
        return None


def get_midterm_stocks_df():
    """
    Get stocks for both mid-term strategies.

    Returns:
        tuple: (tfmomentum_stocks_df, tfema_stocks_df)
    """
    tfmomentum_stocks_df = perform_tfmomentum_strategy()
    tfema_stocks_df = perform_tfema_strategy()
    return tfmomentum_stocks_df, tfema_stocks_df


def perform_tfmomentum_strategy():
    """
    Main function to orchestrate the fetching and processing of stock data.

    Returns:
        DataFrame: DataFrame containing filtered stocks based on TFMomentum strategy
    """
    try:
        # Fetch stock data from the database
        stock_data_dict = read_stock_data_from_db(EQUITY_STOCK_DATA_DB_PATH)
        if not stock_data_dict:
            logger.error("Failed to retrieve stock data from the database.")
            return pd.DataFrame()

        all_stock_df = []
        for stock_code, stock_data in stock_data_dict.items():
            # Get financial data
            financial_data = get_financial_data(stock_code)
            if not financial_data:
                continue

            # Convert list data to DataFrame for easier processing
            stock_data_df = pd.DataFrame(stock_data["daily_data"])
            stock_data_df["SMA_20"] = calculate_sma(stock_data_df["Close"], TFMOMENTUM_SMA_VALUE)
            stock_data_df["RSI_14"] = indicator_rsi(stock_data_df, 14, "Close")

            df = pd.DataFrame([{
                "Symbol": stock_code,
                "SMA_20": stock_data_df["SMA_20"].iloc[-1],
                "RSI_14": stock_data_df["RSI_14"].iloc[-1],
                "Gross Profit Growth": financial_data["Gross Profit Growth"],
                "Net Income": financial_data["Net Income"],
                "Total Revenue": financial_data["Total Revenue"],
            }])
            all_stock_df.append(df)

        if all_stock_df:
            combined_stock_df = pd.concat(all_stock_df)
            # Initialize the Mid_Strat column
            combined_stock_df[MID_TFMOMENTUM] = 0
            # Define the criteria as a separate variable for readability
            criteria = (
                (combined_stock_df["RSI_14"] >= TFMOMENTUM_RSI_LOWER_THRESHOLD)
                & (combined_stock_df["RSI_14"] <= TFMOMENTUM_RSI_UPPER_THRESHOLD)
                & (combined_stock_df["Gross Profit Growth"] > TFMOMENTUM_GROSS_PROFIT_GROWTH)
                & (combined_stock_df["Net Income"] > TFMOMENTUM_NET_INCOME)
                & (combined_stock_df["SMA_20"] > TFMOMENTUM_EMA_THRESHOLD)
                & (combined_stock_df["Total Revenue"] > TFMOMENTUM_TOTAL_REVENUE)
            )
            # Apply the criteria
            combined_stock_df.loc[criteria, MID_TFMOMENTUM] = 1
            return combined_stock_df

        return pd.DataFrame()

    except Exception as e:
        logger.error(f"An error occurred in perform_tfmomentum_strategy: {e}")
        return pd.DataFrame()


def perform_tfema_strategy():
    """
    Apply a strategy based on multiple EMA filters and other financial metrics.

    Returns:
        DataFrame: DataFrame containing filtered stocks based on TFEMA strategy
    """
    try:
        # Fetch stock data
        stock_data_dict = read_stock_data_from_db(EQUITY_STOCK_DATA_DB_PATH)
        if not stock_data_dict:
            logger.error("Failed to retrieve stock data from the database.")
            return pd.DataFrame()

        all_stock_df = []
        for stock_code, stock_data in stock_data_dict.items():
            # Get financial data
            financial_data = get_financial_data(stock_code)
            if not financial_data:
                continue

            stock_data_df = pd.DataFrame(stock_data["daily_data"])
            stock_data_df["SHORT_EMA"] = calculate_ema(stock_data_df["Close"], TFEMA_SHORT_EMA_VALUE)
            stock_data_df["SMALL_EMA"] = calculate_ema(stock_data_df["Close"], TFEMA_SMALL_EMA_VALUE)
            stock_data_df["MEDIUM_EMA"] = calculate_ema(stock_data_df["Close"], TFEMA_MEDIUM_EMA_VALUE)
            stock_data_df["LARGE_EMA"] = calculate_ema(stock_data_df["Close"], TFEMA_LARGE_EMA_VALUE)
            stock_data_df["RSI_14"] = indicator_rsi(stock_data_df, 14, "Close")
            stock_data_df["SMA_20_Volume"] = calculate_sma(stock_data_df["Volume"], TFEMA_SMA_VALUE)

            df = pd.DataFrame([{
                "Symbol": stock_code,
                "SHORT_EMA": stock_data_df["SHORT_EMA"].iloc[-1],
                "SMALL_EMA": stock_data_df["SMALL_EMA"].iloc[-1],
                "MEDIUM_EMA": stock_data_df["MEDIUM_EMA"].iloc[-1],
                "LARGE_EMA": stock_data_df["LARGE_EMA"].iloc[-1],
                "RSI_14": stock_data_df["RSI_14"].iloc[-1],
                "SMA_20_Volume": stock_data_df["SMA_20_Volume"].iloc[-1],
                "Close": stock_data_df["Close"].iloc[-1],
                "Volume": stock_data_df["Volume"].iloc[-1],
                "Market Cap": financial_data["Market Cap"],
                "Return on Equity": financial_data["Return on Equity"],
            }])
            all_stock_df.append(df)

        if all_stock_df:
            combined_stock_df = pd.concat(all_stock_df)
            combined_stock_df[MID_TFEMA] = 0
            # Define the criteria as a separate variable for readability
            criteria = (
                (combined_stock_df["Close"] > combined_stock_df["SHORT_EMA"])
                & (combined_stock_df["SHORT_EMA"] > combined_stock_df["SMALL_EMA"])
                & (combined_stock_df["SMALL_EMA"] > combined_stock_df["MEDIUM_EMA"])
                & (combined_stock_df["MEDIUM_EMA"] > combined_stock_df["LARGE_EMA"])
                & (combined_stock_df["RSI_14"] >= TFEMA_RSI_UPPER_THRESHOLD)
                & (combined_stock_df["Volume"] > TFEMA_VOLUME_MULTIPLIER * combined_stock_df["SMA_20_Volume"])
                & (combined_stock_df["Market Cap"] >= TFEMA_MARKET_CAP_THRESHOLD)
                & (combined_stock_df["Return on Equity"] >= TFEMA_ROE_THRESHOLD)
            )
            # Apply the criteria
            combined_stock_df.loc[criteria, MID_TFEMA] = 1
            return combined_stock_df

        return pd.DataFrame()

    except Exception as e:
        logger.error(f"An error occurred in perform_tfema_strategy: {e}")
        return pd.DataFrame()


if __name__ == "__main__":
    get_midterm_stocks_df()
