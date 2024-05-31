import os
import sys
from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

ZERODHA = os.getenv("ZERODHA_BROKER")
ALICEBLUE = os.getenv("ALICEBLUE_BROKER")
FIRSTOCK = os.getenv("FIRSTOCK_BROKER")
CLIENTS_USER_FB_DB = os.getenv("FIREBASE_USER_COLLECTION")
STRATEGY_FB_DB = os.getenv("FIREBASE_STRATEGY_COLLECTION")

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()

import Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter as firebase_utils
import Executor.ExecutorUtils.BrokerCenter.Brokers.AliceBlue.alice_adapter as alice_adapter
import Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter as zerodha_adapter
import Executor.ExecutorUtils.BrokerCenter.Brokers.Firstock.firstock_adapter as firstock_adapter


def place_order_for_brokers(order_details, user_credentials):
    if order_details["broker"] == ZERODHA:
        return zerodha_adapter.kite_place_orders_for_users(
            order_details, user_credentials
        )
    elif order_details["broker"] == ALICEBLUE:
        return alice_adapter.ant_place_orders_for_users(
            order_details, user_credentials
        )
    elif order_details["broker"] == FIRSTOCK:
        return firstock_adapter.firstock_place_orders_for_users(
            order_details, user_credentials
        )


def modify_order_for_brokers(order_details, user_credentials):
    if order_details["broker"] == ZERODHA:
        return zerodha_adapter.kite_modify_orders_for_users(
            order_details, user_credentials
        )
    elif order_details["broker"] == ALICEBLUE:
        return alice_adapter.ant_modify_orders_for_users(
            order_details, user_credentials
        )
    elif order_details["broker"] == FIRSTOCK:
        return firstock_adapter.firstock_modify_orders_for_users(
            order_details, user_credentials
        )


def all_broker_login(active_users):
    import Executor.ExecutorUtils.BrokerCenter.Brokers.AliceBlue.alice_login as alice_blue
    import Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.kite_login as zerodha
    import Executor.ExecutorUtils.BrokerCenter.Brokers.Firstock.firstock_login as firstock
    
    for user in active_users:
        if user["Broker"]["BrokerName"] == ZERODHA:
            logger.debug(f"Logging in for Zerodha for user: {user['Broker']['BrokerUsername']}")
            try:
                session_id = zerodha.login_in_zerodha(user["Broker"])
                firebase_utils.update_fields_firebase(
                    CLIENTS_USER_FB_DB, user["Tr_No"], {"SessionId": session_id}, "Broker"
                )
            except Exception as e:
                logger.error(f"Error while logging in for Zerodha: {e} for user: {user['Broker']['BrokerUsername']}")
        elif user["Broker"]["BrokerName"] == ALICEBLUE:
            logger.debug(f"Logging in for AliceBlue for user: {user['Broker']['BrokerUsername']}")
            try:
                session_id = alice_blue.login_in_aliceblue(user["Broker"])
                firebase_utils.update_fields_firebase(
                    CLIENTS_USER_FB_DB, user["Tr_No"], {"SessionId": session_id}, "Broker"
                )
            except Exception as e:
                logger.error(f"Error while logging in for AliceBlue: {e} for user: {user['Broker']['BrokerUsername']}")
        elif user["Broker"]["BrokerName"] == FIRSTOCK:
            logger.debug(f"Logging in for Firstock for user: {user['Broker']['BrokerUsername']}")
            try:
                session_id = firstock.login_in_firstock(user["Broker"])
                firebase_utils.update_fields_firebase(
                    CLIENTS_USER_FB_DB, user["Tr_No"], {"SessionId": session_id}, "Broker"
                )
            except Exception as e:
                logger.error(f"Error while logging in for Firstock: {e} for user: {user['Broker']['BrokerUsername']}")
        else:
            logger.error(f"Broker not supported for user: {user['Broker']['BrokerUsername']}")
    return active_users


def fetch_active_users_from_firebase():
    """
    Fetches active users from Firebase.

    Returns:
        list: A list of active user account details.
    """
    try:
        active_users = []
        account_details = firebase_utils.fetch_collection_data_firebase(CLIENTS_USER_FB_DB)
        for account in account_details:
            if account_details[account]["Active"] == True:
                active_users.append(account_details[account])
        return active_users
    except Exception as e:
        logger.error(f"Error while fetching active users from Firebase: {e}")
        return []


def fetch_list_of_strategies_from_firebase():
    """
    Fetches a list of strategies from Firebase.

    Returns:
        list: A list of strategy names.
    """
    try:
        strategies = []
        acounts = fetch_active_users_from_firebase()
        for account in acounts:
            for strategy in account["Strategies"]:
                if strategy not in strategies:
                    strategies.append(strategy)
        return strategies
    except Exception as e:
        logger.error(f"Error while fetching strategies from Firebase: {e}")
        return []


def fetch_users_for_strategies_from_firebase(strategy_name):
    """
    Fetches users who have a specific strategy from Firebase.

    Args:
        strategy_name (str): The name of the strategy.

    Returns:
        list: A list of user accounts that have the specified strategy.
    """
    accounts = fetch_active_users_from_firebase()
    users = []
    for account in accounts:
        try:
            if strategy_name in account["Strategies"]:
                users.append(account)
        except Exception as e:
            logger.error(f"Error while fetching users for strategy {strategy_name}: {e}")
    return users


def fetch_primary_accounts_from_firebase(primary_account):
    # fetch the tr_no from .env file and fetch the primary account from firebase
    try:
        account_details = firebase_utils.fetch_collection_data_firebase(CLIENTS_USER_FB_DB)
        for account in account_details:
            if account_details[account]["Tr_No"] == primary_account:
                return account_details[account]
    except Exception as e:
        logger.error(f"Error while fetching primary account from Firebase: {e}")


def fetch_freecash_for_user(user):
    """Retrieves the cash margin available for a user based on their broker."""
    try:
        logger.debug(f"Fetching free cash for {user['Broker']['BrokerName']} for user {user['Broker']['BrokerUsername']}")
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
        


def download_csv_for_brokers(primary_account):
    if primary_account["Broker"]["BrokerName"] == ZERODHA:
        return zerodha_adapter.get_csv_kite(primary_account)  # Get CSV for this user
    elif primary_account["Broker"]["BrokerName"] == ALICEBLUE:
        return alice_adapter.get_ins_csv_alice(primary_account)  # Get CSV for this user
    # elif primary_account["Broker"]["BrokerName"] == FIRSTOCK:
    #     return firstock_adapter.get_csv_firstock(primary_account)  # Get CSV for this user


def fetch_holdings_value_for_user_broker(user):
    if user["Broker"]["BrokerName"] == ZERODHA:
        return zerodha_adapter.fetch_zerodha_holdings_value(user)
    elif user["Broker"]["BrokerName"] == ALICEBLUE:
        return alice_adapter.fetch_aliceblue_holdings_value(user)
    elif user["Broker"]["BrokerName"] == FIRSTOCK:
        return firstock_adapter.fetch_firstock_holdings_value(user)


def fetch_user_credentials_firebase(broker_user_name):
    try:
        user_credentials = firebase_utils.fetch_collection_data_firebase(CLIENTS_USER_FB_DB)
        for user in user_credentials:
            if user_credentials[user]["Broker"]["BrokerUsername"] == broker_user_name:
                return user_credentials[user]["Broker"]
    except Exception as e:
        logger.error(f"Error while fetching user credentials from Firebase: {e}")

def fetch_strategy_details_for_user(username):
    try:
        user_details = firebase_utils.fetch_collection_data_firebase(CLIENTS_USER_FB_DB)
        for user in user_details:
            if user_details[user]["Broker"]["BrokerUsername"] == username:
                return user_details[user]["Strategies"]
    except Exception as e:
        logger.error(f"Error while fetching strategy details for user {username}: {e}")
        
def fetch_active_strategies_all_users():
    try:
        user_details = firebase_utils.fetch_collection_data_firebase(CLIENTS_USER_FB_DB)
        strategies = []
        for user in user_details:
            if user_details[user]["Active"] == True:
                for strategy in user_details[user]["Strategies"]:
                    if strategy not in strategies:
                        strategies.append(strategy)
        return strategies
    except Exception as e:
        logger.error(f"Error while fetching active strategies for all users: {e}")


def get_today_orders_for_brokers(user):
    if user["Broker"]["BrokerName"] == ZERODHA:
        try:
            logger.debug(f"Fetching today's orders for {user['Broker']['BrokerUsername']}")
            kite_data = zerodha_adapter.zerodha_todays_tradebook(user["Broker"])
            if kite_data:
                kite_data = [
                    trade
                    for trade in kite_data
                    if trade["status"] != "REJECTED" or trade["status"] != "CANCELLED"
                ]
        except Exception as e:
            logger.error(f"Error while fetching today's orders for {user['Broker']['BrokerUsername']}: {e}")
            kite_data = []
        return kite_data
    elif user["Broker"]["BrokerName"] == ALICEBLUE:
        try:
            logger.debug(f"Fetching today's tradebook for {user['Broker']['BrokerUsername']}")
            alice_data = alice_adapter.aliceblue_todays_tradebook(user["Broker"])
            if alice_data:
                alice_data = [
                    trade
                    for trade in alice_data
                    if trade["Status"] != "rejected" or trade["Status"] != "cancelled"
                ]
        except Exception as e:
            logger.error(f"Error while fetching today's tradebook for {user['Broker']['BrokerUsername']}: {e}")
            alice_data = []
        return alice_data
    elif user["Broker"]["BrokerName"] == FIRSTOCK:
        try:
            logger.debug(f"Fetching today's tradebook for {user['Broker']['BrokerUsername']}")
            firstock_data = firstock_adapter.firstock_todays_tradebook(user["Broker"])
            if firstock_data:
                firstock_data = [
                    trade
                    for trade in firstock_data
                    if trade["status"] != "REJECTED" or trade["status"] != "CANCELLED"
                ]
        except Exception as e:
            logger.error(f"Error while fetching today's tradebook for {user['Broker']['BrokerUsername']}: {e}")
            firstock_data = []
        return firstock_data

def get_today_open_orders_for_brokers(user):
    if user["Broker"]["BrokerName"] == ZERODHA:
        kite_data = zerodha_adapter.fetch_open_orders(user)
        return kite_data
    elif user["Broker"]["BrokerName"] == ALICEBLUE:
        alice_data = alice_adapter.fetch_open_orders(user)
        return alice_data
    elif user["Broker"]["BrokerName"] == FIRSTOCK:
        firstock_data = firstock_adapter.fetch_open_orders(user)
        return firstock_data

def create_counter_order_details(tradebook, user):
    counter_order_details = []
    try:
        for trade in tradebook:
            if user["Broker"]["BrokerName"] == ZERODHA:
                if trade["status"] == "TRIGGER PENDING" and trade["product"] == "MIS":
                    zerodha_adapter.kite_create_cancel_order(trade, user)
                    counter_order = zerodha_adapter.kite_create_sl_counter_order(trade, user)
                    counter_order_details.append(counter_order)
                    logger.info(f"Created counter orders for {user['Broker']['BrokerName']} for user {user['Broker']['BrokerUsername']} for trade_id {trade['tag']}")
            elif user["Broker"]["BrokerName"] == ALICEBLUE:
                if trade["Status"] == "trigger pending" and trade["Pcode"] == "MIS":
                    alice_adapter.ant_create_cancel_orders(trade, user)
                    counter_order = alice_adapter.ant_create_counter_order(trade, user)
                    counter_order_details.append(counter_order)
                    logger.info(f"Created counter orders for {user['Broker']['BrokerName']} for user {user['Broker']['BrokerUsername']} for trade_id {trade['remarks']}")
            elif user["Broker"]["BrokerName"] == FIRSTOCK:
                if trade["status"] == "TRIGGER_PENDING" and trade["product"] == "I":
                    firstock_adapter.firstock_create_cancel_order(trade, user)
                    counter_order = firstock_adapter.firstock_create_sl_counter_order(trade, user)
                    counter_order_details.append(counter_order)
                    logger.info(f"Created counter orders for {user['Broker']['BrokerName']} for user {user['Broker']['BrokerUsername']} for trade_id {trade['remarks']}")
        return counter_order_details
    except Exception as e:
        logger.error(f"Error while creating counter orders for {user['Broker']['BrokerName']} for user {user['Broker']['BrokerUsername']}: {e}")
        return []


def create_hedge_counter_order_details(tradebook, user, open_orders):
    hedge_counter_order = []
    if user["Broker"]["BrokerName"] == ZERODHA:
        try:
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
                        logger.info(f"Created hedge counter orders for {user['Broker']['BrokerName']} for user {user['Broker']['BrokerUsername']} for trade_id {trade['tag']}")
        except Exception as e:
            logger.error(f"Error while creating hedge counter orders for {user['Broker']['BrokerName']} for user {user['Broker']['BrokerUsername']}: {e}")
    elif user["Broker"]["BrokerName"] == ALICEBLUE:
        try:
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
                        logger.info(f"Created hedge counter orders for {user['Broker']['BrokerName']} for user {user['Broker']['BrokerUsername']} for trade_id {trade['remarks']}")
        except Exception as e:
            logger.error(f"Error while creating hedge counter orders for {user['Broker']['BrokerName']} for user {user['Broker']['BrokerUsername']}: {e}")
    elif user["Broker"]["BrokerName"] == FIRSTOCK:
        try:
            open_order_tokens = {position['token'] for position in open_orders if position['product'] == 'I' and position['netQuantity'] != '0'}
            for trade in tradebook:
                remarks = trade.get("remarks", "")
                if not remarks:
                    continue

                if (
                    trade["status"] == "COMPLETE"
                    and trade["product"] == "I"
                    and "HO_EN" in trade["remarks"]
                    and "HO_EX" not in trade["remarks"]
                    and trade["token"] in open_order_tokens
                ):
                    counter_order = firstock_adapter.firstock_create_hedge_counter_order(
                        trade, user
                    )
                    if counter_order not in hedge_counter_order:
                        hedge_counter_order.append(counter_order)
                        logger.info(f"Created hedge counter orders for {user['Broker']['BrokerName']} for user {user['Broker']['BrokerUsername']} for trade_id {trade['remarks']}")
        except Exception as e:
            logger.error(f"Error while creating hedge counter orders for {user['Broker']['BrokerName']} for user {user['Broker']['BrokerUsername']}: {e}")
    return hedge_counter_order

def get_avg_prc_broker_key(broker_name):
    if broker_name == ZERODHA:
        return "average_price"
    elif broker_name == ALICEBLUE:
        return "Avgprc"
    elif broker_name == FIRSTOCK:
        return "averagePrice"


def get_order_id_broker_key(broker_name):
    if broker_name == ZERODHA:
        return "order_id"
    elif broker_name == ALICEBLUE:
        return "Nstordno"
    elif broker_name == FIRSTOCK:
        return "orderNumber"


def get_trading_symbol_broker_key(broker_name):
    if broker_name == ZERODHA:
        return "tradingsymbol"
    elif broker_name == ALICEBLUE:
        return "Trsym"
    elif broker_name == FIRSTOCK:
        return "tradingSymbol"


def get_qty_broker_key(broker_name):
    if broker_name == ZERODHA:
        return "quantity"
    elif broker_name == ALICEBLUE:
        return "Qty"
    elif broker_name == FIRSTOCK:
        return "quantity"


def get_time_stamp_broker_key(broker_name):
    if broker_name == ZERODHA:
        return "order_timestamp"
    elif broker_name == ALICEBLUE:
        return "OrderedTime"
    elif broker_name == FIRSTOCK:
        return "orderTime"


def get_trade_id_broker_key(broker_name):
    if broker_name == ZERODHA:
        return "tag"
    elif broker_name == ALICEBLUE:
        return "remarks"
    elif broker_name == FIRSTOCK:
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
    elif user["Broker"]["BrokerName"] == FIRSTOCK:
        return firstock_adapter.firstock_get_ledger(user)


def process_user_ledger(user, ledger):
    if user["Broker"]["BrokerName"] == ZERODHA:
        return zerodha_adapter.process_kite_ledger(ledger, user)
    elif user["Broker"]["BrokerName"] == ALICEBLUE:
        return alice_adapter.process_alice_ledger(ledger, user)
    elif user["Broker"]["BrokerName"] == FIRSTOCK:  
        return firstock_adapter.process_firstock_ledger(ledger, user)


def calculate_user_net_values(user, categorized_df):
    if user["Broker"]["BrokerName"] == ZERODHA:
        return zerodha_adapter.calculate_kite_net_values(user, categorized_df)
    elif user["Broker"]["BrokerName"] == ALICEBLUE:
        return alice_adapter.calculate_alice_net_values(user, categorized_df)
    elif user["Broker"]["BrokerName"] == FIRSTOCK:
        return firstock_adapter.calculate_firstock_net_values(user, categorized_df)

def get_primary_account_obj():
    zerodha_primary = os.getenv("ZERODHA_PRIMARY_ACCOUNT")
    primary_account_session_id = fetch_primary_accounts_from_firebase(
        zerodha_primary
    )
    obj = zerodha_adapter.create_kite_obj(
        api_key=primary_account_session_id["Broker"]["ApiKey"],
        access_token=primary_account_session_id["Broker"]["SessionId"],
    )
    return obj

def get_broker_pnl(user):
    try:
        broker = user["Broker"]["BrokerName"]
        if broker == ZERODHA:
            return zerodha_adapter.get_zerodha_pnl(user)
        elif broker == ALICEBLUE:
            return alice_adapter.get_alice_pnl(user)
        elif broker == FIRSTOCK:
            return firstock_adapter.get_firstock_pnl(user)
    except Exception as e:
        logger.error(f"Error fetching broker pnl for user: {user['Broker']['BrokerUsername']}: {e}")
        return None
    
def get_orders_tax(orders_to_place,user_credentials):
    #TODO As of now passing all the brokers to zerodha adapter
    if user_credentials['BrokerName'] == ZERODHA:
        return zerodha_adapter.get_order_tax(orders_to_place,user_credentials,user_credentials['BrokerName'])
    elif user_credentials['BrokerName'] == ALICEBLUE:
        return zerodha_adapter.get_order_tax(orders_to_place,user_credentials,user_credentials['BrokerName'])
    elif user_credentials['BrokerName'] == FIRSTOCK:
        return zerodha_adapter.get_order_tax(orders_to_place,user_credentials,user_credentials['BrokerName'])
    else:
        return None
    
def get_order_margin(orders_to_place,user_credentials):
    #TODO As of now passing all the brokers to zerodha adapter
    if user_credentials['BrokerName'] == ZERODHA:
        return zerodha_adapter.get_margin_utilized(user_credentials)
    elif user_credentials['BrokerName'] == ALICEBLUE:
        return alice_adapter.get_margin_utilized(user_credentials)
    elif user_credentials['BrokerName'] == FIRSTOCK:
        return firstock_adapter.get_margin_utilized(user_credentials)
    else:
        return None
    
def get_broker_payin(user):
    if user["Broker"]["BrokerName"] == ZERODHA:
        return zerodha_adapter.get_broker_payin(user)
    elif user["Broker"]["BrokerName"] == ALICEBLUE:
        return alice_adapter.get_broker_payin(user)
    elif user["Broker"]["BrokerName"] == FIRSTOCK:
        return firstock_adapter.get_broker_payin(user)
    else:
        return None

def get_basket_order_margins(orders_to_place,user_credentials):
    if user_credentials['BrokerName'] == ZERODHA:
        return zerodha_adapter.get_basket_margin(orders_to_place=orders_to_place)
    elif user_credentials['BrokerName'] == ALICEBLUE:
        return alice_adapter.get_basket_margin(user_credentials)
    elif user_credentials['BrokerName'] == FIRSTOCK:
        return firstock_adapter.get_basket_margin(orders_to_place=orders_to_place)
    else:
        return None