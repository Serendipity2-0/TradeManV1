"""
This module handles all broker login-related functionality.
"""

import os
import sys
import traceback
from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

ZERODHA = os.getenv("ZERODHA_BROKER")
ALICEBLUE = os.getenv("ALICEBLUE_BROKER")
FIRSTOCK = os.getenv("FIRSTOCK_BROKER")
CLIENTS_USER_DB = os.getenv("MONGO_USER_COLLECTION", "clients")
ADMIN_DB = os.getenv("MONGO_ADMIN_COLLECTION", "v1admin")

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import (
    send_admin_message_via_discord,
)
import Executor.ExecutorUtils.ExeDBUtils.MongoUtils.exemongo_adapter as mongo_utils
import Executor.ExecutorUtils.BrokerCenter.Brokers.AliceBlue.alice_adapter as alice_adapter
import Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter as zerodha_adapter
import Executor.ExecutorUtils.BrokerCenter.Brokers.Firstock.firstock_adapter as firstock_adapter

logger = LoggerSetup()

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
    Updates the session ID in MongoDB based on the account type.

    Args:
        user (dict): User information.
        session_id (str): The session ID to update.
        account_type (str): Type of account (Primary or Client).
    """
    if account_type == "Client":
        mongo_utils.update_fields_mongodb(
            CLIENTS_USER_DB,
            user["document_id"],
            {"Broker.SessionId": session_id}
        )
    elif account_type == "Primary":
        mongo_utils.update_fields_mongodb(
            ADMIN_DB,
            "primary_accounts",
            {f"{user['BrokerName']}.SessionId": session_id}
        )


def fetch_active_users():
    """
    Fetches active users from MongoDB.

    Returns:
        list: A list of active user account details.
    """
    try:
        active_users = []
        account_details = mongo_utils.fetch_collection_data_mongodb(CLIENTS_USER_DB)
        if account_details:
            for account in account_details.values():
                if account.get("Active") == True:
                    active_users.append(account)
        return active_users
    except Exception as e:
        logger.error(f"Error while fetching active users from MongoDB: {e}")
        return []


def fetch_primary_accounts():
    """
    Fetches the primary account details from Admin collection of MongoDB.

    Returns:
        dict: Details of the primary account for the available brokers.
    """
    try:
        logger.debug(f"Fetching primary accounts from MongoDB: {ADMIN_DB}")
        account_details = mongo_utils.fetch_collection_data_mongodb(ADMIN_DB)
        primary_accounts = []
        if account_details:
            for account in account_details.values():
                if "primary_accounts" in account:
                    for broker in account["primary_accounts"]:
                        primary_accounts.append(account["primary_accounts"][broker])
        return primary_accounts
    except Exception as e:
        logger.error(f"Error while fetching primary account from MongoDB: {e}")


def fetch_primary_broker_list():
    """
    Fetches a list of primary brokers from MongoDB.

    Returns:
        list: A list of primary brokers.
    """
    primary_brokers = fetch_primary_accounts()
    brokers = []
    for broker in primary_brokers:
        brokers.append(broker["BrokerName"])
    return brokers
