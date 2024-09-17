import os, sys
import pandas as pd
import datetime
from dotenv import load_dotenv

# Define constants and load environment variables
DIR = os.getcwd()
sys.path.append(DIR)  # Add the current directory to the system path

ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

CONSOLIDATED_REPORT_PATH = os.getenv("CONSOLIDATED_REPORT_PATH")
ERROR_LOG_PATH = os.getenv("ERROR_LOG_PATH")

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
    get_primary_account_obj,
)
import Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils as InstrumentCenterUtils

instrument_obj = InstrumentCenterUtils.Instrument()

logger = LoggerSetup()
primary_broker = os.getenv("PRIMARY_BROKER")
kite_obj = get_primary_account_obj(primary_broker)


def fetch_historical_data(instrument_token, from_date, to_date):
    """
    Fetch historical data for a given instrument token within a specified date range.

    Args:
        instrument_token (int): The instrument token.
        from_date (datetime.date): The start date for fetching historical data.
        to_date (datetime.date): The end date for fetching historical data.

    Returns:
        list: A list of dictionaries containing historical data.
    """
    global kite_obj
    data = kite_obj.historical_data(instrument_token, from_date, to_date, "day")
    ltp_data = kite_obj.ltp(instrument_token)
    ltp = ltp_data[instrument_token]["last_price"]
    return data, ltp


def calculate_movement(data, ltp):
    """
    Calculate the movement range and percentage movement based on historical data.

    Args:
        data (list): A list of dictionaries containing historical data.

    Returns:
        tuple: A tuple containing the movement range and percentage movement.
    """
    global kite_obj
    if data:  # Check if data is not empty
        prev_close = data[0]["close"]
        movement_range = ltp - prev_close
        percentage_movement = (movement_range / prev_close) * 100
        return movement_range, percentage_movement
    return 0, 0  # Return 0,0 if data is empty


def calculate_ohlc(data, today):
    """
    Calculate the movement range and percentage movement for all base symbols.

    Args:
        data (list): A list of dictionaries containing historical data.

    Returns:
        tuple: A tuple containing the movement range and percentage movement.
    """
    if data:
        for row in data:
            if row["date"].date() == today:
                return row["open"], row["high"], row["low"], row["close"]
    return 0, 0, 0, 0


# Initialize an empty list for storing data
data_dict = {}

base_symbols = ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "MIDCPNIFTY"]
today = datetime.date.today()
yesterday = today - datetime.timedelta(days=1)

for symbol in base_symbols:
    # Initialize dictionary for this token
    token = instrument_obj.fetch_base_symbol_token(symbol)
    data_dict[token] = {"Token": symbol}
    periods = {
        "Today": fetch_historical_data(token, yesterday, today),
    }

    for period_name, period_data in periods.items():
        movement_range, percentage_movement = calculate_movement(
            period_data[0], period_data[1]
        )
        ohlc = calculate_ohlc(period_data[0], today)

        # Store the range along with the percentage movement for the period
        data_dict[token][
            period_name
        ] = f"{movement_range:.2f} ({percentage_movement:.2f}%)"
        # append ohlc to data_dict
        data_dict[token]["Open"] = f"{ohlc[0]:.2f}"
        data_dict[token]["High"] = f"{ohlc[1]:.2f}"
        data_dict[token]["Low"] = f"{ohlc[2]:.2f}"
        data_dict[token]["Close"] = f"{ohlc[3]:.2f}"


def main():
    """
    Main function to fetch and calculate movement data for base symbols and convert it to a DataFrame.

    Returns:
        DataFrame: DataFrame containing movement data for base symbols.
    """
    # Convert the dictionary to a DataFrame
    df = pd.DataFrame(list(data_dict.values()))

    # Reordering DataFrame columns to match the requested format
    df = df[["Token", "Open", "High", "Low", "Close", "Today"]]

    return df
