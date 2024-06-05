import os, sys
import datetime as dt
import psycopg2
from datetime import timedelta
from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()

from Executor.Strategies.StrategiesUtil import StrategyBase
import Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils as InstrumentCenterUtils
from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
    fetch_primary_accounts_from_firebase,
)
from Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter import (
    create_kite_obj,
)
from Executor.ExecutorUtils.ExeUtils import holidays
from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import (
    discord_bot,
)

strategy_obj = StrategyBase.load_from_db("ExpiryTrader")
primary_account = os.getenv("ZERODHA_PRIMARY_ACCOUNT")

primary_account_details = fetch_primary_accounts_from_firebase(primary_account)
kite = create_kite_obj(primary_account_details["Broker"])

symbols_list = ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "MIDCPNIFTY"]
segments = ["NFO-OPT", "BFO-OPT"]

instru_obj = InstrumentCenterUtils.Instrument()


def connect_to_db(base_symbol):
    """
    Connect to the PostgreSQL database for the given base symbol.

    Args:
        base_symbol (str): The base symbol for which to connect to the database.

    Returns:
        connection: A psycopg2 connection object if the connection is successful.

    Raises:
        Exception: If there is an error connecting to the database.
    """
    try:
        logger.info(f"Connecting to database {base_symbol.lower()}...")
        return psycopg2.connect(
            dbname=base_symbol.lower(),
            user="postgres",
            password="K@nnada1",
            host="localhost",
            port="5432",
        )
    except Exception as e:
        logger.error(f"Error connecting to database {base_symbol.lower()}: {e}")


def store_data_in_postgres(trading_symbol_list, all_data, cursor):
    """
    Store historical trading data in the PostgreSQL database.

    Args:
        trading_symbol_list (str): The trading symbol list to be used as the table name.
        all_data (list): A list of dictionaries containing the historical data records.
        cursor: A cursor object to interact with the PostgreSQL database.

    Raises:
        Exception: If there is an error while inserting records into the database.
    """
    table_name = trading_symbol_list

    if " " or "(" or ")" in table_name:
        table_name = table_name.replace(" ", "").replace("(", "").replace(")", "")

    logger.info(f"Storing data in table {table_name}...")
    # table_name = trading_symbol_list[0].replace("-", "_").lower()
    create_table_query = f"CREATE TABLE IF NOT EXISTS {table_name} (date TIMESTAMP, open REAL, high REAL, low REAL, close REAL, volume INT);"
    cursor.execute(create_table_query)

    for record in all_data:
        date = record["date"].strftime("%Y-%m-%d %H:%M:%S")
        open_price = record["open"]
        high = record["high"]
        low = record["low"]
        close_price = record["close"]
        volume = record["volume"]

        insert_query = f"INSERT INTO {table_name} (date, open, high, low, close, volume) VALUES ('{date}', {open_price}, {high}, {low}, {close_price}, {volume});"
        try:
            cursor.execute(insert_query)
        except Exception as e:
            logger.error(f"Error while inserting record {table_name}: {e}")

    cursor.connection.commit()


def fetch_token_and_name(base_symbol, strike_prc, option_type, expiry_date):
    """
    Fetch the exchange token and trading symbol for a given set of criteria.

    Args:
        base_symbol (str): The base symbol.
        strike_prc (int): The strike price.
        option_type (str): The option type (e.g., "CE" or "PE").
        expiry_date (datetime): The expiry date of the option.

    Returns:
        tuple: A tuple containing the token and name.
    """
    exchange_token = instru_obj.get_exchange_token_by_criteria(
        base_symbol, int(strike_prc), option_type, expiry_date
    )
    token = instru_obj.get_kite_token_by_exchange_token(exchange_token)
    name = instru_obj.get_trading_symbol_by_exchange_token(exchange_token)
    return token, name


def calculate_expiry_date(
    base_symbol, strike_prc, option_type, expiry_type="current_week"
):
    """
    Calculate the expiry date for the given criteria.

    Args:
        base_symbol (str): The base symbol.
        strike_prc (int): The strike price.
        option_type (str): The option type (e.g., "CE" or "PE").
        expiry_type (str): The expiry type (e.g., "current_week" or "current_month").

    Returns:
        datetime: The calculated expiry date.
    """
    return instru_obj.get_expiry_by_criteria(
        base_symbol, int(strike_prc), option_type, expiry_type
    )


def fetch_and_store_historical_data(base_symbol, start_date, end_date, cursor):
    """
    Fetch and store historical data for a given base symbol within a specified date range.

    Args:
        base_symbol (str): The base symbol for which to fetch data.
        start_date (str): The start date for fetching data (format: "YYYY-MM-DD").
        end_date (str): The end date for fetching data (format: "YYYY-MM-DD").
        cursor: A cursor object to interact with the PostgreSQL database.

    Raises:
        Exception: If there is an error while fetching or storing data.
    """
    strike_prc = strategy_obj.calculate_current_atm_strike_prc(base_symbol)
    strike_step = strategy_obj.get_strike_step(base_symbol)
    upper_strikes = [(strike_prc + i * strike_step) for i in range(1, 9)]
    lower_strikes = [(strike_prc - i * strike_step) for i in range(1, 9)]
    all_strikes = lower_strikes + [strike_prc] + upper_strikes

    future_expiry = calculate_expiry_date(base_symbol, 0, "FUT", "current_month")
    option_expiry = calculate_expiry_date(base_symbol, int(strike_prc), "CE")

    base_token = instru_obj.fetch_base_symbol_token(base_symbol)
    logger.info(base_token)

    base_data = kite.historical_data(
        instrument_token=base_token,
        from_date=start_date,
        to_date=end_date,
        interval="minute",
        continuous=False,
    )
    store_data_in_postgres(base_symbol, base_data, cursor)

    future_token, future_symbol = fetch_token_and_name(
        base_symbol, 0, "FUT", future_expiry
    )
    future_data = kite.historical_data(
        instrument_token=future_token,
        from_date=start_date,
        to_date=end_date,
        interval="minute",
        continuous=False,
    )
    store_data_in_postgres(future_symbol, future_data, cursor)

    for strike in all_strikes:
        logger.info(strike)
        for option_type in ["CE", "PE"]:
            token, name = fetch_token_and_name(
                base_symbol, int(strike), option_type, option_expiry
            )
            try:
                option_data = kite.historical_data(
                    instrument_token=token,
                    from_date=start_date,
                    to_date=end_date,
                    interval="minute",
                    continuous=False,
                )
                store_data_in_postgres(name, option_data, cursor)
            except Exception as e:
                logger.error(f"Error while fetching data for {name}: {e}")


def main():
    """
    Main function to fetch and store historical trading data for specified base symbols.

    This function performs the following steps:
        - Checks if today is a holiday.
        - Fetches base symbols with expiry today.
        - Connects to the PostgreSQL database.
        - Fetches and stores historical data for each base symbol.

    Raises:
        Exception: If there is an error while fetching or storing data.
    """
    today = dt.datetime.today()

    base_symbols = []

    for segment in segments:
        base_symbol = instru_obj.get_symbols_with_expiry_today(
            segment, symbols_list
        )  # get the segment from the csv file
        base_symbols.extend(base_symbol)

    if today.date() in holidays:
        logger.info("Today is a holiday")
        return

    for base_symbol in base_symbols:
        try:
            conn = connect_to_db(base_symbol)
            cursor = conn.cursor()

            start_date = (dt.datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            end_date = dt.datetime.now().strftime("%Y-%m-%d")
            fetch_and_store_historical_data(base_symbol, start_date, end_date, cursor)

            cursor.close()
            conn.close()
        except Exception as e:
            logger.error(f"Error while fetching data for {base_symbol}: {e}")
            discord_bot(f"Error while fetching data for {base_symbol}: {e}", "db")

    logger.info(base_symbols)
    discord_bot(f"Fetching data for {base_symbols}...", "db")
