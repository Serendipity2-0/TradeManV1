"""
This module contains utility functions and common operations for broker interactions.
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

ZERODHA = os.getenv("ZERODHA_BROKER")
ALICEBLUE = os.getenv("ALICEBLUE_BROKER")
FIRSTOCK = os.getenv("FIRSTOCK_BROKER")
CLIENTS_USER_DB = os.getenv("MONGO_USER_COLLECTION", "clients")
STRATEGY_DB = os.getenv("MONGO_STRATEGY_COLLECTION", "strategies")

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
import Executor.ExecutorUtils.ExeDBUtils.MongoUtils.exemongo_adapter as mongo_utils
import Executor.ExecutorUtils.BrokerCenter.Brokers.AliceBlue.alice_adapter as alice_adapter
import Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter as zerodha_adapter
import Executor.ExecutorUtils.BrokerCenter.Brokers.Firstock.firstock_adapter as firstock_adapter
from Executor.ExecutorUtils.ExeUtils import (
    EQUITY_STRATEGY_LIST,
    DERIVATIVES_STRATEGY_LIST,
)

logger = LoggerSetup()

BROKER_ADAPTERS = {
    ZERODHA: zerodha_adapter,
    ALICEBLUE: alice_adapter,
    FIRSTOCK: firstock_adapter,
}


def fetch_freecash_for_user(user):
    """
    Retrieves the cash margin available for a user based on their broker.

    Args:
        user (dict): Details of the user account.

    Returns:
        float: Available cash margin.
    """
    try:
        logger.debug(
            f"Fetching free cash for {user['Broker']['BrokerName']} for user {user['Broker']['BrokerUsername']}"
        )
        if user["Broker"]["BrokerName"] == ZERODHA:
            cash_margin = zerodha_adapter.zerodha_fetch_free_cash(user["Broker"])
        elif user["Broker"]["BrokerName"] == ALICEBLUE:
            cash_margin = alice_adapter.alice_fetch_free_cash(user["Broker"])
        elif user["Broker"]["BrokerName"] == FIRSTOCK:
            cash_margin = firstock_adapter.firstock_fetch_free_cash(user["Broker"])
        # Ensure cash_margin is a float
        return float(cash_margin)
    except Exception as e:
        logger.error(f"Error while fetching free cash for brokers: {e}")
        return 0.0


def get_primary_account_obj(broker):
    """
    Fetches the primary account object for the specified broker account.

    Args:
        broker (str): The name of the broker.

    Returns:
        object: Primary account object, or None if not found or on error.
    """
    try:
        from .broker_login import fetch_primary_accounts
        primary_accounts = fetch_primary_accounts()
        account = next(
            (user for user in primary_accounts if user["BrokerName"] == broker), None
        )

        if account and broker in BROKER_ADAPTERS:
            return BROKER_ADAPTERS[broker].create_broker_obj(user_details=account)
    except Exception as e:
        logger.error(f"Error fetching primary account object for {broker}: {e}")
    return None


def download_csv_for_brokers(broker):
    """
    Downloads CSV data for a given broker's primary account.

    Args:
        broker (str): The name of the broker.

    Returns:
        str: Path to the downloaded CSV file.
    """
    adapter = BROKER_ADAPTERS.get(broker)
    if adapter:
        return adapter.get_ins_csv()
    else:
        raise ValueError(f"Unsupported broker: {broker}")


def fetch_holdings_value_for_user_broker(user):
    """
    Fetches the value of holdings for a user based on their broker.

    Args:
        user (dict): User account details.

    Returns:
        float: Value of holdings.
    """
    if user["Broker"]["BrokerName"] == ZERODHA:
        return zerodha_adapter.fetch_zerodha_holdings_value(user)
    elif user["Broker"]["BrokerName"] == ALICEBLUE:
        return alice_adapter.fetch_aliceblue_holdings_value(user)
    elif user["Broker"]["BrokerName"] == FIRSTOCK:
        return firstock_adapter.fetch_firstock_holdings_value(user)


def fetch_user_json(tr_no):
    """
    Fetches user details from MongoDB based on the Tr_No.

    Args:
        tr_no (str): The Tr_No of the user.

    Returns:
        dict: User details for the specified Tr_No.
    """
    user_details = mongo_utils.fetch_collection_data_mongodb(CLIENTS_USER_DB)
    if user_details:
        for user in user_details.values():
            if user.get("Tr_No") == tr_no:
                return user


def fetch_user_credentials(broker_user_name):
    """
    Fetches user credentials from MongoDB based on the broker username.

    Args:
        broker_user_name (str): The broker username.

    Returns:
        dict: User credentials for the specified broker username.
    """
    try:
        user_credentials = mongo_utils.fetch_collection_data_mongodb(CLIENTS_USER_DB)
        if user_credentials:
            for user in user_credentials.values():
                if user.get("Broker", {}).get("BrokerUsername") == broker_user_name:
                    return user.get("Broker")
    except Exception as e:
        logger.error(f"Error while fetching user credentials from MongoDB: {e}")


def fetch_strategy_details_for_user(username):
    """
    Fetches strategy details for a user from MongoDB based on their username.

    Args:
        username (str): The username of the user.

    Returns:
        dict: Strategy details for the specified user.
    """
    try:
        user_details = mongo_utils.fetch_collection_data_mongodb(CLIENTS_USER_DB)
        if user_details:
            for user in user_details.values():
                if user.get("Broker", {}).get("BrokerUsername") == username:
                    equity_strategy_details = user.get("Strategies", {}).get("Equity", {})
                    derivatives_strategy_details = user.get("Strategies", {}).get("Derivatives", {})
                    return {**equity_strategy_details, **derivatives_strategy_details}
    except Exception as e:
        logger.error(f"Error while fetching strategy details for user {username}: {e}")


def fetch_active_strategies_all_users():
    """
    Fetches a list of all unique active strategies from MongoDB.

    Returns:
        list: A list of unique active strategies across all active users.
    """
    try:
        user_details = mongo_utils.fetch_collection_data_mongodb(CLIENTS_USER_DB)
        strategies = set()
        if user_details:
            for user in user_details.values():
                if user.get("Active", False):
                    user_strategies = user.get("Strategies", {})
                    for category in ["Equity", "Derivatives", "Debt"]:
                        if category in user_strategies:
                            strategies.update(user_strategies[category])
        return list(strategies)
    except Exception as e:
        logger.error(f"Error while fetching active strategies for all users: {e}")
        return []


def get_broker_pnl(user):
    """
    Fetches the Profit and Loss (PnL) for a user based on their broker.

    Args:
        user (dict): User account details.

    Returns:
        dict: Broker PnL details.
    """
    try:
        broker = user["Broker"]["BrokerName"]
        if broker == ZERODHA:
            return zerodha_adapter.get_zerodha_pnl(user)
        elif broker == ALICEBLUE:
            return alice_adapter.get_alice_pnl(user)
        elif broker == FIRSTOCK:
            return firstock_adapter.get_firstock_pnl(user)
    except Exception as e:
        logger.error(
            f"Error fetching broker pnl for user: {user['Broker']['BrokerUsername']}: {e}"
        )
        return None


def get_broker_payin(user):
    """
    Fetches the broker payin details for a user based on their broker.

    Args:
        user (dict): User account details.

    Returns:
        dict: Broker payin details.
    """
    if user["Broker"]["BrokerName"] == ZERODHA:
        return zerodha_adapter.get_broker_payin(user)
    elif user["Broker"]["BrokerName"] == ALICEBLUE:
        return alice_adapter.get_broker_payin(user)
    elif user["Broker"]["BrokerName"] == FIRSTOCK:
        return firstock_adapter.get_broker_payin(user)
    else:
        return None


def get_avg_prc_broker_key(broker_name):
    """
    Returns the average price key for a given broker.

    Args:
        broker_name (str): The name of the broker.

    Returns:
        str: The average price key.
    """
    if broker_name == ZERODHA:
        return "average_price"
    elif broker_name == ALICEBLUE:
        return "Avgprc"
    elif broker_name == FIRSTOCK:
        return "averagePrice"


def get_order_id_broker_key(broker_name):
    """
    Returns the order ID key for a given broker.

    Args:
        broker_name (str): The name of the broker.

    Returns:
        str: The order ID key.
    """
    if broker_name == ZERODHA:
        return "order_id"
    elif broker_name == ALICEBLUE:
        return "Nstordno"
    elif broker_name == FIRSTOCK:
        return "orderNumber"


def get_trading_symbol_broker_key(broker_name):
    """
    Returns the trading symbol key for a given broker.

    Args:
        broker_name (str): The name of the broker.

    Returns:
        str: The trading symbol key.
    """
    if broker_name == ZERODHA:
        return "tradingsymbol"
    elif broker_name == ALICEBLUE:
        return "Trsym"
    elif broker_name == FIRSTOCK:
        return "tradingSymbol"


def get_qty_broker_key(broker_name):
    """
    Returns the quantity key for a given broker.

    Args:
        broker_name (str): The name of the broker.

    Returns:
        str: The quantity key.
    """
    if broker_name == ZERODHA:
        return "quantity"
    elif broker_name == ALICEBLUE:
        return "Qty"
    elif broker_name == FIRSTOCK:
        return "quantity"


def get_time_stamp_broker_key(broker_name):
    """
    Returns the timestamp key for a given broker.

    Args:
        broker_name (str): The name of the broker.

    Returns:
        str: The timestamp key.
    """
    if broker_name == ZERODHA:
        return "order_timestamp"
    elif broker_name == ALICEBLUE:
        return "OrderedTime"
    elif broker_name == FIRSTOCK:
        return "orderTime"


def get_trade_id_broker_key(broker_name):
    """
    Returns the trade ID key for a given broker.

    Args:
        broker_name (str): The name of the broker.

    Returns:
        str: The trade ID key.
    """
    if broker_name == ZERODHA:
        return "tag"
    elif broker_name == ALICEBLUE:
        return "remarks"
    elif broker_name == FIRSTOCK:
        return "remarks"


def convert_date_str_to_standard_format(date_str):
    """
    Converts a date string to a standard format.

    Args:
        date_str (str): The date string to convert.

    Returns:
        str: The date string in standard format.
    """
    # Define possible date formats
    date_formats = [
        "%Y-%m-%d %H:%M:%S",  # 2024-01-31 09:20:03
        "%d-%b-%Y %H:%M:%S",  # 23-Jan-2024 09:20:04
        "%d/%m/%Y %H:%M:%S",  # 23/01/2024 09:20:05
    ]

    for fmt in date_formats:
        try:
            # Try to parse the date string using the current format
            dt = datetime.strptime(date_str, fmt)
            # If parsing is successful, return the formatted string
            date_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            return date_str
        except ValueError:
            # If parsing fails, try the next format
            continue
    return "Invalid date format"


def convert_to_standard_format(date_str):
    """
    Converts a date string or datetime object to a standard format.

    Args:
        date_str (str or datetime): The date string or datetime object to convert.

    Returns:
        str: The date string in standard format.
    """
    # first check the type of the date_str whether it is string or datetime and then convert it to standard format
    if isinstance(date_str, str):
        return convert_date_str_to_standard_format(date_str)
    elif isinstance(date_str, datetime):
        date_str = date_str.strftime("%Y-%m-%d %H:%M:%S")
        return convert_date_str_to_standard_format(date_str)
    else:
        return "Invalid date format"
