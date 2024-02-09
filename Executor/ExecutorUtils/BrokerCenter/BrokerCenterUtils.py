import os
import sys
import json


from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

ZERODHA = os.getenv("ZERODHA_BROKER")
ALICEBLUE = os.getenv("ALICEBLUE_BROKER")
CLIENTS_DB = os.getenv("FIREBASE_USER_COLLECTION")

from loguru import logger

ERROR_LOG_PATH = os.getenv("ERROR_LOG_PATH")
logger.add(
    ERROR_LOG_PATH,
    level="TRACE",
    rotation="00:00",
    enqueue=True,
    backtrace=True,
    diagnose=True,
)


import Executor.ExecutorUtils.BrokerCenter.Brokers.AliceBlue.alice_adapter as alice_adapter
import Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter as zerodha_adapter
import Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter as firebase_utils


def place_order_for_brokers(order_details, user_credentials):
    if order_details["broker"] == ZERODHA:
        return zerodha_adapter.kite_place_orders_for_users(
            order_details, user_credentials
        )
    elif order_details["broker"] == ALICEBLUE:
        return alice_adapter.ant_place_orders_for_users(order_details, user_credentials)


def modify_order_for_brokers(order_details, user_credentials):
    # based on the broker name call the respective function with order_details and user_credentials with broker details
    if order_details["broker"] == ZERODHA:
        return zerodha_adapter.kite_modify_orders_for_users(
            order_details, user_credentials
        )
    elif order_details["broker"] == ALICEBLUE:
        return alice_adapter.ant_modify_orders_for_users(
            order_details, user_credentials
        )


def all_broker_login(active_users):
    try:
        import Executor.ExecutorUtils.BrokerCenter.Brokers.AliceBlue.alice_login as alice_blue
    except ModuleNotFoundError as e:
        logger.error(f"Module not found: {e}")
        alice_blue = None  # Set to None to indicate the module couldn't be imported

    try:
        import Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.kite_login as zerodha
    except ModuleNotFoundError as e:
        logger.error(f"Module not found: {e}")
        zerodha = None  # Set to None to indicate the module couldn't be imported

    for user in active_users:
        if user["Broker"]["BrokerName"] == ZERODHA:
            logger.info("Logging in for Zerodha")
            session_id = zerodha.login_in_zerodha(user["Broker"])
            firebase_utils.update_fields_firebase(
                CLIENTS_DB, user["Tr_No"], {"SessionId": session_id}, "Broker"
            )
        elif user["Broker"]["BrokerName"] == ALICEBLUE:
            logger.info("Logging in for AliceBlue")
            try:
                session_id = alice_blue.login_in_aliceblue(user["Broker"])
                firebase_utils.update_fields_firebase(
                    CLIENTS_DB, user["Tr_No"], {"SessionId": session_id}, "Broker"
                )
            except Exception as e:
                logger.error(f"Error while logging in for AliceBlue: {e}")
        else:
            logger.error("Broker not supported")
    return active_users


def fetch_active_users_from_firebase():
    """
    Fetches active users from Firebase.

    Returns:
        list: A list of active user account details.
    """
    active_users = []
    account_details = firebase_utils.fetch_collection_data_firebase(CLIENTS_DB)
    for account in account_details:
        if account_details[account]["Active"] == True:
            active_users.append(account_details[account])
    return active_users


def fetch_list_of_strategies_from_firebase():
    """
    Fetches a list of strategies from Firebase.

    Returns:
        list: A list of strategy names.
    """
    strategies = []
    acounts = fetch_active_users_from_firebase()
    for account in acounts:
        for strategy in account["Strategies"]:
            if strategy not in strategies:
                strategies.append(strategy)
    return strategies


def fetch_users_for_strategies_from_firebase(strategy_name):
    """
    Fetches users who have a specific strategy from Firebase.

    Args:
        strategy_name (str): The name of the strategy.

    Returns:
        list: A list of user accounts that have the specified strategy.
    """
    users = []
    accounts = fetch_active_users_from_firebase()
    for account in accounts:
        if strategy_name in account["Strategies"]:
            users.append(account)
    return users


def fetch_primary_accounts_from_firebase(primary_account):
    # fetch the tr_no from .env file and fetch the primary account from firebase
    account_details = firebase_utils.fetch_collection_data_firebase(CLIENTS_DB)
    for account in account_details:
        if account_details[account]["Tr_No"] == primary_account:
            return account_details[account]


def fetch_freecash_brokers(active_users):
    """Retrieves the cash margin available for a user based on their broker."""
    for user in active_users:
        if user["Broker"]["BrokerName"] == ZERODHA:
            cash_margin = zerodha_adapter.zerodha_fetch_free_cash(user["Broker"])
        elif user["Broker"]["BrokerName"] == ALICEBLUE:
            cash_margin = alice_adapter.alice_fetch_free_cash(user["Broker"])
        # Ensure cash_margin is a float
        return float(cash_margin) if cash_margin else 0.0
    return 0.0  # If user or broker not found


def download_csv_for_brokers(primary_account):
    if primary_account["Broker"]["BrokerName"] == ZERODHA:
        return zerodha_adapter.get_csv_kite(primary_account)  # Get CSV for this user
    elif primary_account["Broker"]["BrokerName"] == ALICEBLUE:
        return alice_adapter.get_ins_csv_alice(primary_account)  # Get CSV for this user


def fetch_holdings_for_brokers(user):
    if user["Broker"]["BrokerName"] == ZERODHA:
        return zerodha_adapter.fetch_zerodha_holdings(user)
    elif user["Broker"]["BrokerName"] == ALICEBLUE:
        return alice_adapter.fetch_aliceblue_holdings(user)


def fetch_user_credentials_firebase(broker_user_name):
    user_credentials = firebase_utils.fetch_collection_data_firebase(CLIENTS_DB)
    for user in user_credentials:
        if user_credentials[user]["Broker"]["BrokerUsername"] == broker_user_name:
            return user_credentials[user]["Broker"]


def fetch_strategy_details_for_user(username):
    user_details = firebase_utils.fetch_collection_data_firebase(CLIENTS_DB)
    for user in user_details:
        if user_details[user]["Broker"]["BrokerUsername"] == username:
            return user_details[user]["Strategies"]
        
def fetch_active_strategies_all_users():
    user_details = firebase_utils.fetch_collection_data_firebase(CLIENTS_DB)
    strategies = []
    for user in user_details:
        if user_details[user]["Active"] == True:
            for strategy in user_details[user]["Strategies"]:
                if strategy not in strategies:
                    strategies.append(strategy)
    return strategies


def get_today_orders_for_brokers(user):
    if user["Broker"]["BrokerName"] == ZERODHA:
        # with open('/Users/amolkittur/Desktop/TradeManV1/SampleData/kite_orders.json') as f:
        #     kite_data = json.load(f)
        kite_data = zerodha_adapter.zerodha_todays_tradebook(user["Broker"])
        kite_data = [
            trade
            for trade in kite_data
            if trade["status"] != "REJECTED" or trade["status"] != "CANCELLED"
        ]
        return kite_data

    elif user["Broker"]["BrokerName"] == ALICEBLUE:
        # with open('/Users/amolkittur/Desktop/TradeManV1/SampleData/aliceblue_orders.json') as f:
        #     alice_data = json.load(f)
        alice_data = alice_adapter.aliceblue_todays_tradebook(user["Broker"])
        alice_data = [
            trade
            for trade in alice_data
            if trade["Status"] != "rejected" or trade["Status"] != "cancelled"
        ]
        return alice_data

def get_today_open_orders_for_brokers(user):
    if user["Broker"]["BrokerName"] == ZERODHA:
        kite_data = zerodha_adapter.fetch_open_orders(user)
        return kite_data
    elif user["Broker"]["BrokerName"] == ALICEBLUE:
        alice_data = alice_adapter.fetch_open_orders(user)
        return alice_data

def create_counter_order_details(tradebook, user):
    counter_order_details = []
    for trade in tradebook:
        if user["Broker"]["BrokerName"] == ZERODHA:
            if trade["status"] == "TRIGGER PENDING" and trade["product"] == "MIS":
                zerodha_adapter.kite_create_cancel_order(trade, user)
                counter_order = zerodha_adapter.kite_create_sl_counter_order(trade, user)
                counter_order_details.append(counter_order)
        elif user["Broker"]["BrokerName"] == ALICEBLUE:
            if trade["Status"] == "trigger pending" and trade["Pcode"] == "MIS":
                alice_adapter.ant_create_cancel_orders(trade, user)
                counter_order = alice_adapter.ant_create_counter_order(trade, user)
                counter_order_details.append(counter_order)
    return counter_order_details


def create_hedge_counter_order_details(tradebook, user, open_orders):
    hedge_counter_order = []
    if user["Broker"]["BrokerName"] == ZERODHA:
        open_order_tokens = {position['instrument_token'] for position in open_orders['net'] if position['product'] == 'MIS' and position['quantity'] != 0}
        for trade in tradebook:
            if trade["tag"] is None:
                continue

            if (
                trade["status"] == "COMPLETE"
                and trade["product"] == "MIS"
                and "HO_EN" in trade["tag"]
                and "HO_EX" not in trade["tag"]
                and trade["instrument_token"] in open_order_tokens
            ):
                counter_order = zerodha_adapter.kite_create_hedge_counter_order(
                    trade, user
                )
                if counter_order not in hedge_counter_order:
                    hedge_counter_order.append(counter_order)

    elif user["Broker"]["BrokerName"] == ALICEBLUE:
        open_order_tokens = open_order_tokens = {position['Token']: abs(int(position['Netqty'])) for position in open_orders if position['Pcode'] == 'MIS' and position['Netqty'] != '0.00'}        
        for trade in tradebook:
            if trade["remarks"] is None:
                continue

            trade_token_str = str(trade["token"])
            if (
                trade["Status"] == "complete"
                and trade["Pcode"] == "MIS"
                and "HO_EN" in trade["remarks"]
                and "HO_EX" not in trade["remarks"]
                and trade_token_str in open_order_tokens
            ):
                counter_order = alice_adapter.ant_create_hedge_counter_order(trade, user)
                if counter_order not in hedge_counter_order:
                    hedge_counter_order.append(counter_order)
    return hedge_counter_order

def get_avg_prc_broker_key(broker_name):
    if broker_name == ZERODHA:
        return "average_price"
    elif broker_name == ALICEBLUE:
        return "Avgprc"


def get_order_id_broker_key(broker_name):
    if broker_name == ZERODHA:
        return "order_id"
    elif broker_name == ALICEBLUE:
        return "Nstordno"


def get_trading_symbol_broker_key(broker_name):
    if broker_name == ZERODHA:
        return "tradingsymbol"
    elif broker_name == ALICEBLUE:
        return "Trsym"


def get_qty_broker_key(broker_name):
    if broker_name == ZERODHA:
        return "quantity"
    elif broker_name == ALICEBLUE:
        return "Qty"


def get_time_stamp_broker_key(broker_name):
    if broker_name == ZERODHA:
        return "order_timestamp"
    elif broker_name == ALICEBLUE:
        return "OrderedTime"


def get_trade_id_broker_key(broker_name):
    if broker_name == ZERODHA:
        return "tag"
    elif broker_name == ALICEBLUE:
        return "remarks"


def convert_date_str_to_standard_format(date_str):
    from datetime import datetime

    # Define possible date formats
    date_formats = [
        "%Y-%m-%d %H:%M:%S",  # 2024-01-31 09:20:03
        "%d-%b-%Y %H:%M:%S",  # 23-Jan-2024 09:20:04
        "%d/%m/%Y %H:%M:%S",  # 23/01/2024 09:20:05
        # Add any other formats you expect here
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
    from datetime import datetime

    # first check the type of the date_str whether it is string or datetime and then convert it to standard format
    if isinstance(date_str, str):
        return convert_date_str_to_standard_format(date_str)
    elif isinstance(date_str, datetime):
        date_str = date_str.strftime("%Y-%m-%d %H:%M:%S")
        return convert_date_str_to_standard_format(date_str)
    else:
        return "Invalid date format"


def get_ledger_for_user(user):
    if user["Broker"]["BrokerName"] == ZERODHA:
        return zerodha_adapter.zerodha_get_ledger(user)
    elif user["Broker"]["BrokerName"] == ALICEBLUE:
        return alice_adapter.alice_get_ledger(user)


def process_user_ledger(user, ledger):
    if user["Broker"]["BrokerName"] == ZERODHA:
        return zerodha_adapter.process_kite_ledger(ledger, user)
    elif user["Broker"]["BrokerName"] == ALICEBLUE:
        return alice_adapter.process_alice_ledger(ledger, user)


def calculate_user_net_values(user, categorized_df):
    if user["Broker"]["BrokerName"] == ZERODHA:
        return zerodha_adapter.calculate_kite_net_values(user, categorized_df)
    elif user["Broker"]["BrokerName"] == ALICEBLUE:
        return alice_adapter.calculate_alice_net_values(user, categorized_df)


# This function calculates the taxes and brokerage for a given broker for a given set of orders
# trade_type is 'regular' for regular trades and 'futures' for future trades
def calculate_taxes(broker, trade_type, qty, net_entry_prc, net_exit_prc, no_of_orders):
    # TODO : change the logic to calculate brokerage
    # Brokerage
    if broker == "Zerodha":
        brokerage_rate = 20 
    elif broker == "AliceBlue":
        brokerage_rate = 15 
    brokerage = brokerage_rate * no_of_orders

    # STT/CTT
    intrinsic_value = max(0, net_exit_prc - net_entry_prc) * qty
    stt_ctt_rate = 0.125 / 100 if trade_type == "regular" else 0.0125 / 100
    stt_ctt = stt_ctt_rate * intrinsic_value

    # Transaction charges
    transaction_charges_rate = 0.05 / 100 if trade_type == "regular" else 0.0019 / 100
    transaction_charges = transaction_charges_rate * net_exit_prc * qty

    # SEBI charges
    sebi_charges_rate = 10 / 10000000
    sebi_charges = sebi_charges_rate * net_exit_prc * qty

    # GST
    gst_rate = 18 / 100
    gst = gst_rate * (brokerage + sebi_charges + transaction_charges)

    # Stamp charges
    stamp_charges_rate = 0.003 / 100 if trade_type == "regular" else 0.002 / 100
    stamp_charges = stamp_charges_rate * net_entry_prc * qty

    total_charges = (
        brokerage + stt_ctt + transaction_charges + gst + sebi_charges + stamp_charges
    )
    return total_charges
