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
ADMIN_FB_DB = os.getenv("FIREBASE_ADMIN_COLLECTION")

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import (
    send_admin_message_via_discord,
)

logger = LoggerSetup()

import Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter as firebase_utils
import Executor.ExecutorUtils.BrokerCenter.Brokers.AliceBlue.alice_adapter as alice_adapter
import Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter as zerodha_adapter
import Executor.ExecutorUtils.BrokerCenter.Brokers.Firstock.firstock_adapter as firstock_adapter
from Executor.ExecutorUtils.ExeUtils import (
    EQUITY_STRATEGY_LIST,
    DERIVATIVES_STRATEGY_LIST,
)

BROKER_ADAPTERS = {
    ZERODHA: zerodha_adapter,
    ALICEBLUE: alice_adapter,
    FIRSTOCK: firstock_adapter,
}


async def place_order_for_brokers(order_details, user_credentials):
    """
    Places an order for a given broker.

    Args:
        order_details (dict): Details of the order to be placed.
        user_credentials (dict): Credentials of the user placing the order.

    Returns:
        dict: Response from the broker API.
    """
    if order_details["broker"] == ZERODHA:
        return await zerodha_adapter.kite_place_orders_for_users(
            order_details, user_credentials
        )
    elif order_details["broker"] == ALICEBLUE:
        return await alice_adapter.ant_place_orders_for_users(
            order_details, user_credentials
        )
    elif order_details["broker"] == FIRSTOCK:
        return await firstock_adapter.firstock_place_orders_for_users(
            order_details, user_credentials
        )


def modify_order_for_brokers(order_details, user_credentials):
    """
    Modifies an order for a given broker.

    Args:
        order_details (dict): Details of the order to be modified.
        user_credentials (dict): Credentials of the user modifying the order.

    Returns:
        dict: Response from the broker API.
    """
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


import traceback


def all_broker_login(active_users, account_type):
    """
    Logs in all active users to their respective brokers.

    Args:
        active_users (list): List of active user accounts.
        account_type (str): Type of account to login (Primary or Client).

    Returns:
        list: List of active user accounts after login attempt.
    """
    import Executor.ExecutorUtils.BrokerCenter.Brokers.AliceBlue.alice_login as alice_blue
    import Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.kite_login as zerodha
    import Executor.ExecutorUtils.BrokerCenter.Brokers.Firstock.firstock_login as firstock

    for user in active_users:
        broker_name = (
            user["BrokerName"]
            if account_type == "Primary"
            else user["Broker"]["BrokerName"]
        )
        broker_username = (
            user["BrokerUsername"]
            if account_type == "Primary"
            else user["Broker"]["BrokerUsername"]
        )

        if broker_name == ZERODHA:
            logger.debug(f"Logging in for Zerodha for user: {broker_username}")
            try:
                session_id = zerodha.login_in_zerodha(
                    user if account_type == "Primary" else user["Broker"]
                )
                update_session_id(user, session_id, account_type)
            except Exception as e:
                send_admin_message_via_discord(
                    f"Error while logging in for Zerodha for user: {broker_username}"
                )
                logger.error(
                    f"Error while logging in for Zerodha: {e} for user: {broker_username}"
                )
                logger.error(traceback.format_exc())
        elif broker_name == ALICEBLUE:
            logger.debug(f"Logging in for AliceBlue for user: {broker_username}")
            try:
                session_id = alice_blue.login_in_aliceblue(
                    user if account_type == "Primary" else user["Broker"]
                )
                update_session_id(user, session_id, account_type)
            except Exception as e:
                send_admin_message_via_discord(
                    f"Error while logging in for AliceBlue for user: {broker_username}"
                )
                logger.error(
                    f"Error while logging in for AliceBlue: {e} for user: {broker_username}"
                )
        elif broker_name == FIRSTOCK:
            logger.debug(f"Logging in for Firstock for user: {broker_username}")
            try:
                session_id = firstock.login_in_firstock(
                    user if account_type == "Primary" else user["Broker"]
                )
                update_session_id(user, session_id, account_type)
            except Exception as e:
                send_admin_message_via_discord(
                    f"Error while logging in for Firstock for user: {broker_username}"
                )
                logger.error(
                    f"Error while logging in for Firstock: {e} for user: {broker_username}"
                )
        else:
            logger.error(f"Broker not supported for user: {broker_username}")
    return active_users


def update_session_id(user, session_id, account_type):
    """
    Updates the session ID in Firebase based on the account type.

    Args:
        user (dict): User information.
        session_id (str): The session ID to update.
        account_type (str): Type of account (Primary or Client).
    """
    if account_type == "Client":
        firebase_utils.update_fields_firebase(
            CLIENTS_USER_FB_DB,
            user["Tr_No"],
            {"SessionId": session_id},
            "Broker",
        )
    elif account_type == "Primary":
        firebase_utils.update_fields_firebase(
            ADMIN_FB_DB,
            "primary_accounts",
            {"SessionId": session_id},
            user["BrokerName"],
        )


def fetch_active_users_from_firebase():
    """
    Fetches active users from Firebase.

    Returns:
        list: A list of active user account details.
    """
    try:
        active_users = []
        account_details = firebase_utils.fetch_collection_data_firebase(
            CLIENTS_USER_FB_DB
        )
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
        accounts = fetch_active_users_from_firebase()
        for account in accounts:
            for trade_type in ["Equity", "Derivatives"]:
                if trade_type in account.get("Strategies", {}):
                    for strategy in account["Strategies"][trade_type]:
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
            if (
                strategy_name in EQUITY_STRATEGY_LIST
                and strategy_name in account["Strategies"]["Equity"]
            ):
                users.append(account)
            elif (
                strategy_name in DERIVATIVES_STRATEGY_LIST
                and strategy_name in account["Strategies"]["Derivatives"]
            ):
                users.append(account)
        except Exception as e:
            logger.error(
                f"Error while fetching users for strategy {strategy_name}: {e}"
            )
    return users


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


def fetch_primary_accounts_from_firebase():
    """
    Fetches the primary account details from Admin collection of Firebase.

    Returns:
        dict: Details of the primary account for the available brokers.
    """
    try:
        account_details = firebase_utils.fetch_collection_data_firebase(ADMIN_FB_DB)
        primary_accounts = []
        for broker in account_details["primary_accounts"]:
            primary_accounts.append(account_details["primary_accounts"][broker])
        return primary_accounts
    except Exception as e:
        logger.error(f"Error while fetching primary account from Firebase: {e}")


def get_primary_account_obj(broker):
    """
    Fetches the primary account object for the specified broker account.

    Args:
        broker (str): The name of the broker.

    Returns:
        object: Primary account object, or None if not found or on error.
    """
    try:
        primary_accounts = fetch_primary_accounts_from_firebase()
        account = next(
            (user for user in primary_accounts if user["BrokerName"] == broker), None
        )

        if account and broker in BROKER_ADAPTERS:
            return BROKER_ADAPTERS[broker].create_broker_obj(user_details=account)
    except Exception as e:
        logger.error(f"Error fetching primary account object for {broker}: {e}")
    return None


def fetch_primary_broker_list():
    """
    Fetches a list of primary brokers from Firebase.

    Returns:
        list: A list of primary brokers.
    """
    primary_brokers = fetch_primary_accounts_from_firebase()
    brokers = []
    for broker in primary_brokers:
        brokers.append(broker["BrokerName"])
    return brokers


def download_csv_for_brokers(broker):
    """
    Downloads CSV data for a given broker's primary account.

    Args:
        primary_account (dict): Primary account details.

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


def fetch_user_json_from_firebase(tr_no):
    """
    Fetches user details from Firebase based on the Tr_No.

    Args:
        tr_no (str): The Tr_No of the user.

    Returns:
        dict: User details for the specified Tr_No.
    """
    user_details = firebase_utils.fetch_collection_data_firebase(CLIENTS_USER_FB_DB)
    for user in user_details:
        if user_details[user]["Tr_No"] == tr_no:
            return user_details[user]


def fetch_user_credentials_firebase(broker_user_name):
    """
    Fetches user credentials from Firebase based on the broker username.

    Args:
        broker_user_name (str): The broker username.

    Returns:
        dict: User credentials for the specified broker username.
    """
    try:
        user_credentials = firebase_utils.fetch_collection_data_firebase(
            CLIENTS_USER_FB_DB
        )
        for user in user_credentials:
            if user_credentials[user]["Broker"]["BrokerUsername"] == broker_user_name:
                return user_credentials[user]["Broker"]
    except Exception as e:
        logger.error(f"Error while fetching user credentials from Firebase: {e}")


def fetch_strategy_details_for_user(username):
    """
    Fetches strategy details for a user from Firebase based on their username.

    Args:
        username (str): The username of the user.

    Returns:
        dict: Strategy details for the specified user.
    """
    try:
        user_details = firebase_utils.fetch_collection_data_firebase(CLIENTS_USER_FB_DB)
        for user in user_details:
            if user_details[user]["Broker"]["BrokerUsername"] == username:
                equity_strategy_details = user_details[user]["Strategies"]["Equity"]
                derivatives_strategy_details = user_details[user]["Strategies"][
                    "Derivatives"
                ]
                # retun it in a dictionary
                combined_strategy_details = {
                    **equity_strategy_details,
                    **derivatives_strategy_details,
                }
                return combined_strategy_details
    except Exception as e:
        logger.error(f"Error while fetching strategy details for user {username}: {e}")


def fetch_active_strategies_all_users():
    """
    Fetches a list of all unique active strategies from Firebase.

    Returns:
        list: A list of unique active strategies across all active users.
    """
    try:
        user_details = firebase_utils.fetch_collection_data_firebase(CLIENTS_USER_FB_DB)
        strategies = set()
        for user in user_details:
            if user_details[user].get("Active", False):
                user_strategies = user_details[user].get("Strategies", {})
                for category in ["Equity", "Derivatives", "Debt"]:
                    if category in user_strategies:
                        strategies.update(user_strategies[category])
        return list(strategies)
    except Exception as e:
        logger.error(f"Error while fetching active strategies for all users: {e}")
        return []


def get_today_orders_for_brokers(user):
    """
    Fetches today's orders for a user based on their broker.

    Args:
        user (dict): User account details.

    Returns:
        list: List of today's orders.
    """
    if user["Broker"]["BrokerName"] == ZERODHA:
        try:
            logger.debug(
                f"Fetching today's orders for {user['Broker']['BrokerUsername']}"
            )
            kite_data = zerodha_adapter.zerodha_todays_tradebook(user["Broker"])
            if kite_data:
                kite_data = [
                    trade
                    for trade in kite_data
                    if trade["status"] != "REJECTED" or trade["status"] != "CANCELLED"
                ]
        except Exception as e:
            logger.error(
                f"Error while fetching today's orders for {user['Broker']['BrokerUsername']}: {e}"
            )
            kite_data = []
        return kite_data
    elif user["Broker"]["BrokerName"] == ALICEBLUE:
        try:
            logger.debug(
                f"Fetching today's tradebook for {user['Broker']['BrokerUsername']}"
            )
            alice_data = alice_adapter.aliceblue_todays_tradebook(user["Broker"])
            if alice_data:
                alice_data = [
                    trade
                    for trade in alice_data
                    if trade["Status"] != "rejected" or trade["Status"] != "cancelled"
                ]
        except Exception as e:
            logger.error(
                f"Error while fetching today's tradebook for {user['Broker']['BrokerUsername']}: {e}"
            )
            alice_data = []
        return alice_data
    elif user["Broker"]["BrokerName"] == FIRSTOCK:
        try:
            logger.debug(
                f"Fetching today's tradebook for {user['Broker']['BrokerUsername']}"
            )
            firstock_data = firstock_adapter.firstock_todays_tradebook(user["Broker"])
            if firstock_data:
                firstock_data = [
                    trade
                    for trade in firstock_data
                    if trade["status"] != "REJECTED" or trade["status"] != "CANCELLED"
                ]
        except Exception as e:
            logger.error(
                f"Error while fetching today's tradebook for {user['Broker']['BrokerUsername']}: {e}"
            )
            firstock_data = []
        return firstock_data


def get_today_open_orders_for_brokers(user):
    """
    Fetches today's open orders for a user based on their broker.

    Args:
        user (dict): User account details.

    Returns:
        list: List of today's open orders.
    """
    if user["Broker"]["BrokerName"] == ZERODHA:
        kite_data = zerodha_adapter.fetch_kite_open_orders(user)
        return kite_data
    elif user["Broker"]["BrokerName"] == ALICEBLUE:
        alice_data = alice_adapter.fetch_alice_open_orders(user)
        return alice_data
    elif user["Broker"]["BrokerName"] == FIRSTOCK:
        firstock_data = firstock_adapter.fetch_firstock_open_orders(user)
        return firstock_data


def create_counter_order_details(tradebook, user):
    """
    Creates counter order details based on the tradebook and user details.

    Args:
        tradebook (list): List of trades.
        user (dict): User account details.

    Returns:
        list: List of counter order details.
    """
    counter_order_details = []
    try:
        if not tradebook:
            logger.warning(
                f"Tradebook is empty for user {user['Broker']['BrokerUsername']}"
            )
            return []
        for trade in tradebook:
            if user["Broker"]["BrokerName"] == ZERODHA:
                if trade["status"] == "TRIGGER PENDING" and trade["product"] == "MIS":
                    zerodha_adapter.kite_create_cancel_order(trade, user)
                    counter_order = zerodha_adapter.kite_create_sl_counter_order(
                        trade, user
                    )
                    counter_order_details.append(counter_order)
                    logger.info(
                        f"Created counter orders for {user['Broker']['BrokerName']} for user {user['Broker']['BrokerUsername']} for trade_id {trade['tag']}"
                    )
            elif user["Broker"]["BrokerName"] == ALICEBLUE:
                if trade["Status"] == "trigger pending" and trade["Pcode"] == "MIS":
                    alice_adapter.ant_create_cancel_orders(trade, user)
                    counter_order = alice_adapter.ant_create_counter_order(trade, user)
                    counter_order_details.append(counter_order)
                    logger.info(
                        f"Created counter orders for {user['Broker']['BrokerName']} for user {user['Broker']['BrokerUsername']} for trade_id {trade['remarks']}"
                    )
            elif user["Broker"]["BrokerName"] == FIRSTOCK:
                if trade["status"] == "TRIGGER_PENDING" and trade["product"] == "I":
                    firstock_adapter.firstock_create_cancel_order(trade, user)
                    counter_order = firstock_adapter.firstock_create_sl_counter_order(
                        trade, user
                    )
                    counter_order_details.append(counter_order)
                    logger.info(
                        f"Created counter orders for {user['Broker']['BrokerName']} for user {user['Broker']['BrokerUsername']} for trade_id {trade['remarks']}"
                    )
        return counter_order_details
    except Exception as e:
        logger.error(
            f"Error while creating counter orders for {user['Broker']['BrokerName']} for user {user['Broker']['BrokerUsername']}: {e}"
        )
        logger.error(traceback.format_exc())
        return []


def cancel_normal_orders(tradebook, user):
    """
    Cancels normal orders based on the tradebook and user details.

    Args:
        tradebook (list): List of trades.
        user (dict): User account details.

    Returns:
        list: List of canceled orders.
    """
    try:
        if not tradebook:
            logger.warning(
                f"Tradebook is empty for user {user['Broker']['BrokerUsername']}"
            )
            return []
        for trade in tradebook:
            if user["Broker"]["BrokerName"] == ZERODHA:
                if trade["status"] == "TRIGGER PENDING" and trade["product"] == "NRML":
                    zerodha_adapter.kite_create_cancel_order(trade, user)
            if user["Broker"]["BrokerName"] == ALICEBLUE:
                if trade["Status"] == "trigger pending" and trade["Pcode"] == "NRML":
                    alice_adapter.ant_create_cancel_orders(trade, user)
            if user["Broker"]["BrokerName"] == FIRSTOCK:
                if trade["status"] == "TRIGGER_PENDING" and trade["product"] == "C":
                    print("going to cancel")

                    firstock_adapter.firstock_create_cancel_order(trade, user)
    except Exception as e:
        logger.error(
            f"Error while cancelling normal orders for {user['Broker']['BrokerName']} for user {user['Broker']['BrokerUsername']}: {e}"
        )
        logger.error(traceback.format_exc())
        return []


def create_hedge_counter_order_details(tradebook, user, open_orders):
    """
    Creates hedge counter order details based on the tradebook, user details, and open orders.

    Args:
        tradebook (list): List of trades.
        user (dict): User account details.
        open_orders (list): List of open orders.

    Returns:
        list: List of hedge counter order details.
    """
    if not tradebook:
        logger.warning(
            f"Tradebook is empty for user {user['Broker']['BrokerUsername']}"
        )
        return []
    hedge_counter_order = []
    if user["Broker"]["BrokerName"] == ZERODHA:
        try:
            open_order_tokens = {
                position["instrument_token"]
                for position in open_orders["net"]
                if position["product"] == "MIS" and position["quantity"] != 0
            }
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
                        logger.info(
                            f"Created hedge counter orders for {user['Broker']['BrokerName']} for user {user['Broker']['BrokerUsername']} for trade_id {trade['tag']}"
                        )
        except Exception as e:
            logger.error(
                f"Error while creating hedge counter orders for {user['Broker']['BrokerName']} for user {user['Broker']['BrokerUsername']}: {e}"
            )
    elif user["Broker"]["BrokerName"] == ALICEBLUE:
        try:
            open_order_tokens = open_order_tokens = {
                position["Token"]: abs(int(position["Netqty"]))
                for position in open_orders
                if position["Pcode"] == "MIS" and position["Netqty"] != "0.00"
            }
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
                    counter_order = alice_adapter.ant_create_hedge_counter_order(
                        trade, user
                    )
                    if counter_order not in hedge_counter_order:
                        hedge_counter_order.append(counter_order)
                        logger.info(
                            f"Created hedge counter orders for {user['Broker']['BrokerName']} for user {user['Broker']['BrokerUsername']} for trade_id {trade['remarks']}"
                        )
        except Exception as e:
            logger.error(
                f"Error while creating hedge counter orders for {user['Broker']['BrokerName']} for user {user['Broker']['BrokerUsername']}: {e}"
            )
    elif user["Broker"]["BrokerName"] == FIRSTOCK:
        try:
            open_order_tokens = {
                position["token"]
                for position in open_orders
                if position["product"] == "I" and position["netQuantity"] != "0"
            }
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
                    counter_order = (
                        firstock_adapter.firstock_create_hedge_counter_order(
                            trade, user
                        )
                    )
                    if counter_order not in hedge_counter_order:
                        hedge_counter_order.append(counter_order)
                        logger.info(
                            f"Created hedge counter orders for {user['Broker']['BrokerName']} for user {user['Broker']['BrokerUsername']} for trade_id {trade['remarks']}"
                        )
        except Exception as e:
            logger.error(
                f"Error while creating hedge counter orders for {user['Broker']['BrokerName']} for user {user['Broker']['BrokerUsername']}: {e}"
            )
    return hedge_counter_order


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
    """
    Converts a date string or datetime object to a standard format.

    Args:
        date_str (str or datetime): The date string or datetime object to convert.

    Returns:
        str: The date string in standard format.
    """
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
    """
    Fetches the ledger for a user based on their broker.

    Args:
        user (dict): User account details.

    Returns:
        dict: Ledger details.
    """
    if user["Broker"]["BrokerName"] == ZERODHA:
        return zerodha_adapter.zerodha_get_ledger(user)
    elif user["Broker"]["BrokerName"] == ALICEBLUE:
        return alice_adapter.alice_get_ledger(user)
    elif user["Broker"]["BrokerName"] == FIRSTOCK:
        return firstock_adapter.firstock_get_ledger(user)


def process_user_ledger(user, ledger):
    """
    Processes the ledger for a user based on their broker.

    Args:
        user (dict): User account details.
        ledger (dict): Ledger details.

    Returns:
        dict: Processed ledger details.
    """
    if user["Broker"]["BrokerName"] == ZERODHA:
        return zerodha_adapter.process_kite_ledger(ledger, user)
    elif user["Broker"]["BrokerName"] == ALICEBLUE:
        return alice_adapter.process_alice_ledger(ledger, user)
    elif user["Broker"]["BrokerName"] == FIRSTOCK:
        return firstock_adapter.process_firstock_ledger(ledger, user)


def calculate_user_net_values(user, categorized_df):
    """
    Calculates the net values for a user based on their broker and categorized dataframe.

    Args:
        user (dict): User account details.
        categorized_df (DataFrame): Categorized dataframe.

    Returns:
        dict: Calculated net values.
    """
    if user["Broker"]["BrokerName"] == ZERODHA:
        return zerodha_adapter.calculate_kite_net_values(user, categorized_df)
    elif user["Broker"]["BrokerName"] == ALICEBLUE:
        return alice_adapter.calculate_alice_net_values(user, categorized_df)
    elif user["Broker"]["BrokerName"] == FIRSTOCK:
        return firstock_adapter.calculate_firstock_net_values(user, categorized_df)


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


def get_orders_tax(orders_to_place, user_credentials):
    """
    Fetches the order tax for a user based on their broker.

    Args:
        orders_to_place (list): List of orders to place.
        user_credentials (dict): User credentials.

    Returns:
        dict: Order tax details.
    """
    if user_credentials["BrokerName"] == ZERODHA:
        return zerodha_adapter.get_kite_order_tax(
            orders_to_place, user_credentials["BrokerName"]
        )
    elif user_credentials["BrokerName"] == ALICEBLUE:
        return zerodha_adapter.get_kite_order_tax(
            orders_to_place, user_credentials["BrokerName"]
        )
    elif user_credentials["BrokerName"] == FIRSTOCK:
        return zerodha_adapter.get_kite_order_tax(
            orders_to_place, user_credentials["BrokerName"]
        )
    else:
        return None


def get_order_margin(orders_to_place, user_credentials):
    """
    Fetches the order margin for a user based on their broker.

    Args:
        orders_to_place (list): List of orders to place.
        user_credentials (dict): User credentials.

    Returns:
        dict: Order margin details.
    """
    if user_credentials["BrokerName"] == ZERODHA:
        return zerodha_adapter.get_margin_utilized(user_credentials)
    elif user_credentials["BrokerName"] == ALICEBLUE:
        return alice_adapter.get_margin_utilized(user_credentials)
    elif user_credentials["BrokerName"] == FIRSTOCK:
        return firstock_adapter.get_margin_utilized(user_credentials)
    else:
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


def get_basket_order_margins(orders_to_place, user_credentials):
    if user_credentials["BrokerName"] == ZERODHA:
        return zerodha_adapter.get_basket_margin(orders_to_place=orders_to_place)
    elif user_credentials["BrokerName"] == ALICEBLUE:
        return alice_adapter.get_basket_margin(user_credentials)
    elif user_credentials["BrokerName"] == FIRSTOCK:
        return firstock_adapter.get_basket_margin(orders_to_place=orders_to_place)
    else:
        return None
