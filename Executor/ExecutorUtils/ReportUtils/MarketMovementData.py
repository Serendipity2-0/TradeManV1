import os,sys
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
from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import get_primary_account_obj
import Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils as InstrumentCenterUtils

instrument_obj = InstrumentCenterUtils.Instrument()

logger = LoggerSetup()
kite_obj = get_primary_account_obj()

def fetch_historical_data(instrument_token, from_date, to_date):
    global kite_obj
    data = kite_obj.historical_data(instrument_token, from_date, to_date, "day")
    return data


def calculate_movement(data):
    if data:  # Check if data is not empty
        opening_price = data[0]['open']
        closing_price = data[-1]['close']
        movement_range = closing_price - opening_price
        percentage_movement = (movement_range / opening_price) * 100
        return movement_range, percentage_movement
    return 0, 0  # Return 0,0 if data is empty

# Initialize an empty list for storing data
data_dict = {}

base_symbols = ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'SENSEX', 'MIDCPNIFTY']
today = datetime.date.today()
last_week = today - datetime.timedelta(weeks=1)
last_month = today - datetime.timedelta(days=30)
last_year = today - datetime.timedelta(days=365)

for symbol in base_symbols:
    # Initialize dictionary for this token
    token = instrument_obj.fetch_base_symbol_token(symbol)
    data_dict[token] = {"Token": symbol}
    periods = {
        "Today": fetch_historical_data(token, today, today),
        "Week": fetch_historical_data(token, last_week, today),
        "Month": fetch_historical_data(token, last_month, today),
        "Year": fetch_historical_data(token, last_year, today)
    }
    for period_name, period_data in periods.items():
        movement_range, percentage_movement = calculate_movement(period_data)
        # Store the range along with the percentage movement for the period
        data_dict[token][period_name] = f"{movement_range:.2f} ({percentage_movement:.2f}%)"

def main():
    # Convert the dictionary to a DataFrame
    df = pd.DataFrame(list(data_dict.values()))

    # Reordering DataFrame columns to match the requested format
    df = df[['Token', 'Today', 'Week', 'Month', 'Year']]

    return df