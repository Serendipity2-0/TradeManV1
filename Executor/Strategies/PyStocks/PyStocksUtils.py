import pandas as pd
import yfinance as yf
import os
from dotenv import load_dotenv

DIR = os.getcwd()
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()


def get_stock_codes():
    """
    Fetch stock codes from a CSV file specified in the environment variables.

    Returns:
        list: A list of stock symbols.
    """
    url = os.getenv("tickers_url")
    return list(pd.read_csv(url)["SYMBOL"].values)


def get_stock_data(stockCode, period, duration):
    """
    Fetch historical stock data using the yfinance library.

    Args:
        stockCode (str): The stock symbol.
        period (str): The period of data to fetch (e.g., '1y' for one year).
        duration (str): The duration of each data point (e.g., '1d' for daily).

    Returns:
        DataFrame: A DataFrame containing the historical stock data.
    """
    try:
        append_exchange = ".NS"
        data = yf.download(
            tickers=stockCode + append_exchange, period=period, interval=duration
        )
        return data
    except Exception as e:
        logger.error(f"Error fetching data for {stockCode}: {e}")
        return None


def indicator_5EMA(stock_data):
    """
    Calculate the 5-period Exponential Moving Average (EMA) for the stock data.

    Args:
        stock_data (DataFrame): The stock data.

    Returns:
        Series: A Series containing the 5-period EMA.
    """
    return stock_data["Close"].ewm(span=5, min_periods=0, adjust=False).mean()


def indicator_13EMA(stock_data):
    """
    Calculate the 13-period Exponential Moving Average (EMA) for the stock data.

    Args:
        stock_data (DataFrame): The stock data.

    Returns:
        Series: A Series containing the 13-period EMA.
    """
    return stock_data["Close"].ewm(span=13, min_periods=0, adjust=False).mean()


def indicator_26EMA(stock_data):
    """
    Calculate the 26-period Exponential Moving Average (EMA) for the stock data.

    Args:
        stock_data (DataFrame): The stock data.

    Returns:
        Series: A Series containing the 26-period EMA.
    """
    return stock_data["Close"].ewm(span=26, min_periods=0, adjust=False).mean()


def indicator_50EMA(stock_data):
    """
    Calculate the 50-period Exponential Moving Average (EMA) for the stock data.

    Args:
        stock_data (DataFrame): The stock data.

    Returns:
        Series: A Series containing the 50-period EMA.
    """
    return stock_data["Close"].ewm(span=50, min_periods=0, adjust=False).mean()


def indicator_RSI(data, rsi_length, rsi_source):
    """
    Calculate the Relative Strength Index (RSI) for the stock data.

    Args:
        data (DataFrame): The stock data.
        rsi_length (int): The period for calculating RSI.
        rsi_source (str): The source column for RSI calculation (e.g., 'Close').

    Returns:
        Series: A Series containing the RSI values.
    """
    try:
        delta = data[rsi_source].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window=rsi_length).mean()
        avg_loss = loss.rolling(window=rsi_length).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    except Exception as e:
        logger.error(f"Error calculating RSI: {e}")
        pass


def indicator_bollinger_bands(data, window):
    """
    Calculate the Bollinger Bands for the stock data.

    Args:
        data (DataFrame): The stock data.
        window (int): The period for calculating Bollinger Bands.

    Returns:
        DataFrame: The original DataFrame with added columns for Bollinger Bands.
    """
    data["MA"] = data["Close"].rolling(window=window).mean()
    data["Std_dev"] = data["Close"].rolling(window=window).std()
    data["Upper_band"] = data["MA"] + (data["Std_dev"] * 2)
    data["Lower_band"] = data["MA"] - (data["Std_dev"] * 2)
    return data


def indicator_MACD(data, fast_length=12, slow_length=26, signal_length=9):
    """
    Calculate the Moving Average Convergence Divergence (MACD) for the stock data.

    Args:
        data (DataFrame): The stock data.
        fast_length (int): The period for the fast EMA.
        slow_length (int): The period for the slow EMA.
        signal_length (int): The period for the signal line.

    Returns:
        tuple: A tuple containing the MACD line and the signal line.
    """
    data["EMA_fast"] = data["Close"].ewm(span=fast_length, adjust=False).mean()
    data["EMA_slow"] = data["Close"].ewm(span=slow_length, adjust=False).mean()
    data["MACD"] = data["EMA_fast"] - data["EMA_slow"]
    data["Signal_line"] = data["MACD"].ewm(span=signal_length, adjust=False).mean()
    return data["MACD"], data["Signal_line"]


def indicator_atr(stock_data, window):
    """
    Calculate the Average True Range (ATR) for the stock data.

    Args:
        stock_data (DataFrame): The stock data.
        window (int): The period for calculating ATR.

    Returns:
        Series: A Series containing the ATR values.
    """
    stock_data["HL"] = stock_data["High"] - stock_data["Low"]
    stock_data["HC"] = abs(stock_data["High"] - stock_data["Close"].shift())
    stock_data["LC"] = abs(stock_data["Low"] - stock_data["Close"].shift())
    stock_data["TR"] = stock_data[["HL", "HC", "LC"]].max(axis=1)
    stock_data["ATR"] = stock_data["TR"].rolling(window=window).mean()
    return stock_data["ATR"]


selected_stocks = []


def strategy_VolumeBreakout(stock_data_dict, volume_change_threshold=3):
    """
    Strategy to identify stocks with significant volume breakouts.

    Args:
        stock_data_dict (dict): A dictionary containing stock data.
        volume_change_threshold (int): The threshold for volume change.

    Returns:
        list: A list of selected stocks based on volume breakout strategy.
    """
    global selected_stocks
    selected_stocks = []
    for symbol in stock_data_dict.keys():
        stock_data_daily = stock_data_dict[symbol]["daily_data"]
        volume_changes = (
            stock_data_daily["Volume"].pct_change(periods=1).iloc[-2:]
        )  # Calculate volume changes for last 2 days
        avg_volume_change = volume_changes.mean()

        if avg_volume_change > volume_change_threshold:

            # Calculate the ratio of All-Time High to Last Traded Price
            all_time_high = stock_data_daily["High"].max()
            last_traded_price = stock_data_daily["Close"].iloc[-1]
            ratio_ATH_LTP = all_time_high / last_traded_price

            selected_stocks.append([symbol, ratio_ATH_LTP])

            # Save sorted stocks to a CSV file
            # df_selected_stocks.to_csv("significant_volume_changes.csv", mode='w', header=False)
    return selected_stocks


def strategy_golden_crossover(stock_data_dict):
    """
    Strategy to identify stocks with a Golden Crossover pattern.

    Args:
        stock_data_dict (dict): A dictionary containing stock data.

    Returns:
        list: A list of selected stocks based on Golden Crossover strategy.
    """
    global selected_stocks
    selected_stocks = []
    for symbol in stock_data_dict.keys():
        stock_data_daily = stock_data_dict[symbol]["daily_data"]
        if (
            stock_data_daily is not None and len(stock_data_daily) >= 26
        ):  # Ensure sufficient data for EMA calculation
            stock_data_daily["EMA5"] = indicator_5EMA(stock_data_daily)
            stock_data_daily["EMA13"] = indicator_13EMA(stock_data_daily)
            stock_data_daily["EMA26"] = indicator_26EMA(stock_data_daily)

            # Check for Golden Crossover
            if (
                stock_data_daily["EMA5"].iloc[-2] < stock_data_daily["EMA13"].iloc[-2]
                and stock_data_daily["EMA13"].iloc[-2]
                < stock_data_daily["EMA26"].iloc[-2]
            ):
                if (
                    stock_data_daily["EMA5"].iloc[-1]
                    > stock_data_daily["EMA13"].iloc[-1]
                    and stock_data_daily["EMA13"].iloc[-1]
                    > stock_data_daily["EMA26"].iloc[-1]
                ):
                    # Calculate the ratio of All-Time High to Last Traded Price
                    all_time_high = stock_data_daily["High"].max()
                    last_traded_price = stock_data_daily["Close"].iloc[-1]
                    ratio_ATH_LTP = all_time_high / last_traded_price
                    selected_stocks.append([symbol, ratio_ATH_LTP])
    return selected_stocks


def strategy_above_50EMA(stock_data):
    """
    Strategy to identify stocks trading above their 50-period EMA.

    Args:
        stock_data (DataFrame): The stock data.

    Returns:
        DataFrame: The original DataFrame with an additional column indicating whether the stock is above 50 EMA.
    """
    if stock_data is not None and not stock_data.empty:
        stock_data["EMA_50"] = indicator_50EMA(stock_data)
        stock_data["Above_50_EMA"] = stock_data["Close"] > stock_data["EMA_50"]
        return stock_data
    else:
        return None


def strategy_momentum(stock_data_dict):
    """
    Strategy to identify momentum stocks.

    Args:
        stock_data_dict (dict): A dictionary containing stock data.

    Returns:
        list: A list of selected stocks based on momentum strategy.
    """
    global selected_stocks
    selected_stocks = []
    for symbol in stock_data_dict.keys():
        stock_data_daily = stock_data_dict[symbol]["daily_data"]
        if stock_data_daily is not None and not stock_data_daily.empty:
            # Calculate RSI
            rsi_length_input = 14
            rsi_source_input = "Close"
            rsi_values = indicator_RSI(
                stock_data_daily, rsi_length_input, rsi_source_input
            )

            # Calculate Bollinger Bands
            bb_window = 20
            stock_data_daily = indicator_bollinger_bands(stock_data_daily, bb_window)

            # Check if LTP is above 50 EMA
            stock_data_daily = strategy_above_50EMA(stock_data_daily)

            macd, signal_line = indicator_MACD(stock_data_daily)

            # Apply momentum Strategy conditions
            if rsi_values.iloc[-1] > 50 and stock_data_daily["Above_50_EMA"].iloc[-1]:
                if (
                    stock_data_daily["Upper_band"].iloc[-1]
                    < stock_data_daily["Close"].iloc[-1]
                ):
                    if macd.iloc[-1] > signal_line.iloc[-1]:  # Condition 4
                        all_time_high = stock_data_daily["High"].max()
                        last_traded_price = stock_data_daily["Close"].iloc[-1]
                        ratio_ATH_LTP = all_time_high / last_traded_price
                        selected_stocks.append([symbol, ratio_ATH_LTP])
                        # df_selected_stocks = pd.DataFrame(selected_stocks, columns=['Symbol', 'Stoploss'])
                        # df_selected_stocks.to_csv("Momentum.csv", mode='w', header=False)
    return selected_stocks


def strategy_mean_reversion(stock_data_dict):
    """
    Strategy to identify mean reversion stocks.

    Args:
        stock_data_dict (dict): A dictionary containing stock data.

    Returns:
        list: A list of selected stocks based on mean reversion strategy.
    """
    global selected_stocks
    selected_stocks = []
    for symbol in stock_data_dict.keys():
        stock_data_daily = stock_data_dict[symbol][
            "daily_data"
        ]  # for 15 min duration = 15m period = 50d, for hourly duration = 1h period = 1y
        stock_data_weekly = stock_data_dict[symbol]["weekly_data"]
        if stock_data_daily is not None and not stock_data_daily.empty:
            # Calculate RSI
            rsi_length_input = 14
            rsi_source_input = "Close"
            rsi_values = indicator_RSI(
                stock_data_daily, rsi_length_input, rsi_source_input
            )
            # Calculate Bollinger Bands
            bb_window = 20
            stock_data_weekly = indicator_bollinger_bands(stock_data_weekly, bb_window)
            # Check if LTP is above 50 EMA
            stock_data_daily = strategy_above_50EMA(stock_data_daily)
            # Apply Mean Reversion Strategy conditions
            if rsi_values.iloc[-1] < 40 and stock_data_daily["Above_50_EMA"].iloc[-1]:
                if (
                    stock_data_weekly["MA"].iloc[-1]
                    < stock_data_weekly["Close"].iloc[-1]
                ):
                    if (
                        stock_data_daily["Lower_band"].iloc[-2]
                        < stock_data_daily["Lower_band"].iloc[-3]
                    ):
                        if (
                            stock_data_daily["Lower_band"].iloc[-1]
                            > stock_data_daily["Lower_band"].iloc[-2]
                        ):
                            all_time_high = stock_data_daily["High"].max()
                            last_traded_price = stock_data_daily["Close"].iloc[-1]
                            ratio_ATH_LTP = all_time_high / last_traded_price
                            selected_stocks.append([symbol, ratio_ATH_LTP])
                            # df_selected_stocks = pd.DataFrame(selected_stocks, columns=['Symbol'])
                            # df_selected_stocks.to_csv("MeanReversion.csv", mode='w', header=False)
    return selected_stocks


def strategy_EMA_BB_Confluence(stock_data_dict):
    """
    Strategy to identify stocks with EMA and Bollinger Bands confluence.

    Args:
        stock_data_dict (dict): A dictionary containing stock data.

    Returns:
        list: A list of selected stocks based on EMA and Bollinger Bands confluence strategy.
    """
    global selected_stocks
    selected_stocks = []
    for symbol in stock_data_dict.keys():
        stock_data_daily = stock_data_dict[symbol]["daily_data"]
        if stock_data_daily is not None and not stock_data_daily.empty:
            bb_window = 20
            stock_data_daily = indicator_bollinger_bands(stock_data_daily, bb_window)
            stock_data_daily["EMA_50"] = indicator_50EMA(stock_data_daily)
            if (
                stock_data_daily["EMA_50"].iloc[-1]
                <= stock_data_daily["Lower_band"].iloc[-1]
            ):
                if stock_data_daily["Close"].iloc[-1] < stock_data_daily["MA"].iloc[-1]:
                    if (
                        stock_data_daily["Lower_band"].iloc[-2]
                        < stock_data_daily["Lower_band"].iloc[-3]
                    ):
                        if (
                            stock_data_daily["Lower_band"].iloc[-1]
                            > stock_data_daily["Lower_band"].iloc[-2]
                        ):
                            bollinger_close_to_ema = (
                                abs(
                                    stock_data_daily["Lower_band"].iloc[-1]
                                    - stock_data_daily["EMA_50"].iloc[-1]
                                )
                                < 0.05 * stock_data_daily["Close"].iloc[-1]
                            )
                            if bollinger_close_to_ema:
                                all_time_high = stock_data_daily["High"].max()
                                last_traded_price = stock_data_daily["Close"].iloc[-1]
                                ratio_ATH_LTP = all_time_high / last_traded_price
                                selected_stocks.append([symbol, ratio_ATH_LTP])
                                # df_selected_stocks = pd.DataFrame(selected_stocks, columns=['Symbol'])
                                # df_selected_stocks.to_csv("selected stocks.csv", mode='w', header=False)
                                break
    return selected_stocks


# initializing variables
momentum_stocks = []
mean_reversion_stocks = []
ema_bb_confluence_stocks = []
volume_breakout = []
golden_crossover_stocks = []


# Retrieves short term momentum, mean reversion and ema-bb confluence stocks
# Combines and sorts stocks by ATH to LTP ratio
# Exports sorted list to CSV and returns top picks
def shortTerm_pick(stock_data_dict):
    """
    Retrieves short term momentum, mean reversion and EMA-BB confluence stocks.
    Combines and sorts stocks by ATH to LTP ratio.
    Exports sorted list to CSV and returns top picks.

    Args:
        stock_data_dict (dict): A dictionary containing stock data.

    Returns:
        list: A sorted list of short term stock picks.
    """
    global momentum_stocks
    global mean_reversion_stocks
    global ema_bb_confluence_stocks
    momentum_stocks = strategy_momentum(stock_data_dict)
    mean_reversion_stocks = strategy_mean_reversion(stock_data_dict)
    ema_bb_confluence_stocks = strategy_EMA_BB_Confluence(stock_data_dict)

    # Combine selected stocks from all strategies
    shortTerm_stocks = (
        momentum_stocks + mean_reversion_stocks + ema_bb_confluence_stocks
    )

    # Sort the combined list based on ATH to LTP ratio in ascending order
    shortTerm_stocks.sort(key=lambda x: x[1])

    # Store the sorted list in a CSV file
    """df_short_selected_stocks = pd.DataFrame(
        shortTerm_stocks, columns=["Symbol", "ATH_to_LTP_Ratio"]
    )
    df_short_selected_stocks.to_csv(os.getenv("shortterm_path"), index=False)"""
    return shortTerm_stocks


# Retrieves volume breakout stocks and selects top mid term picks
# Sorts stocks by ATH to LTP ratio and exports to CSV
# Returns list of selected mid term stocks
def midTerm_pick(stock_data_dict):
    """
    Retrieves volume breakout stocks and selects top mid term picks.
    Sorts stocks by ATH to LTP ratio and exports to CSV.
    Returns list of selected mid term stocks.

    Args:
        stock_data_dict (dict): A dictionary containing stock data.

    Returns:
        list: A sorted list of mid term stock picks.
    """
    global volume_breakout
    volume_breakout = strategy_VolumeBreakout(stock_data_dict)
    # Combine selected stocks from all strategies
    midTerm_stocks = momentum_stocks + volume_breakout

    # Sort the combined list based on ATH to LTP ratio in ascending order
    midTerm_stocks.sort(key=lambda x: x[1])

    """df_mid_selected_stocks = pd.DataFrame(
        midTerm_stocks, columns=["Symbol", "ATH_to_LTP_Ratio"]
    )
    df_mid_selected_stocks.to_csv(os.getenv("midterm_path"), index=False)"""
    return midTerm_stocks


# Retrieves golden crossover stocks and selects top long term picks
# Sorts stocks by ATH to LTP ratio and exports to CSV
# Returns list of selected long term stocks
def longTerm_pick(stock_data_dict):
    """
    Retrieves golden crossover stocks and selects top long term picks.
    Sorts stocks by ATH to LTP ratio and exports to CSV.
    Returns list of selected long term stocks.

    Args:
        stock_data_dict (dict): A dictionary containing stock data.

    Returns:
        list: A sorted list of long term stock picks.
    """
    global golden_crossover_stocks
    golden_crossover_stocks = strategy_golden_crossover(stock_data_dict)
    # Combine selected stocks from all strategies
    longTerm_stocks = golden_crossover_stocks

    # Sort the combined list based on ATH to LTP ratio in ascending order
    longTerm_stocks.sort(key=lambda x: x[1])

    """df_long_selected_stocks = pd.DataFrame(
        longTerm_stocks, columns=["Symbol", "Stoploss"]
    )
    df_long_selected_stocks.to_csv(os.getenv("longterm_path"), index=False)"""
    return longTerm_stocks


# Initialize an empty dictionary to store the data


def get_stockpicks_csv():
    """
    Fetches stock data and selects top picks based on various strategies.
    Exports selected stocks to CSV files for short term, mid term, and long term picks.
    """
    stock_symbols = get_stock_codes()
    stock_data_dict = {}
    for stock in stock_symbols:

        # Assuming get_stock_data() function fetches data for the given stock symbol
        stock_data_daily = get_stock_data(stock, period="1y", duration="1d")
        stock_data_weekly = get_stock_data(stock, period="2y", duration="1wk")

        # Store the data in the dictionary
        stock_data_dict[stock] = {
            "daily_data": stock_data_daily,
            "weekly_data": stock_data_weekly,
        }

        # i += 1

    shortterm_top5 = shortTerm_pick(stock_data_dict)[1:11]

    midterm_top5 = midTerm_pick(stock_data_dict)[1:6]

    longterm_top5 = longTerm_pick(stock_data_dict)[1:6]

    df_shortterm_selected_stocks = pd.DataFrame(
        shortterm_top5, columns=["Symbol", "ATH_to_LTP_Ratio"]
    )
    df_shortterm_selected_stocks.to_csv(os.getenv("best5_shortterm_path"), index=False)

    df_midterm_selected_stocks = pd.DataFrame(
        midterm_top5, columns=["Symbol", "ATH_to_LTP_Ratio"]
    )
    df_midterm_selected_stocks.to_csv(os.getenv("best5_midterm_path"), index=False)

    df_longterm_selected_stocks = pd.DataFrame(
        longterm_top5, columns=["Symbol", "ratio_ATH_LTP"]
    )
    df_longterm_selected_stocks.to_csv(os.getenv("best5_longterm_path"), index=False)
