import asyncio
import os
import sys

import pendulum
from dotenv import load_dotenv

import Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils as broker_center_utils
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import (
    send_admin_message_via_discord,
)

DIR = os.getcwd()
sys.path.append(DIR)  # Add the current directory to the system path

# Load environment variables from the trademan.env file
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)


ERROR_LOG_PATH = os.getenv("ERROR_LOG_PATH")
CLIENTS_USER_FB_DB = os.getenv("FIREBASE_USER_COLLECTION")
STRATEGY_FB_DB = os.getenv("FIREBASE_STRATEGY_COLLECTION")

logger = LoggerSetup()

logger.info("Shree Ganeshaya Namaha")
logger.info("Jai Hanuman")
logger.info("Market is Supreme")
today = pendulum.today().format("DD-MM-YYYY")
logger.info(f"Today's date: {today}")


def main():
    """
    The main function fetches active users from Firebase collections, logs information about them, and
    performs broker login for all active users.
    """

    logger.debug(
        f"Fetching users from {CLIENTS_USER_FB_DB} and {STRATEGY_FB_DB} collections."
    )

    if CLIENTS_USER_FB_DB != "trademan_clients" or STRATEGY_FB_DB != "strategies":
        logger.warning(
            f"Using Non Production Environment Using {CLIENTS_USER_FB_DB} and {STRATEGY_FB_DB} collections."
        )
        send_admin_message_via_discord(
            f"Using Non Production Environment Using {CLIENTS_USER_FB_DB} and {STRATEGY_FB_DB} collections."
        )

    today_active_users = broker_center_utils.fetch_active_users_from_firebase()
    primary_accounts = broker_center_utils.fetch_primary_accounts_from_firebase()

    logger.info(f"Total active users today: {len(today_active_users)}")
    logger.info(f"Total primary accounts: {len(primary_accounts)}")
    send_admin_message_via_discord(
        f"Total active users today: {len(today_active_users)}"
    )

    for user in today_active_users:
        logger.debug(
            f"Active user: {user['Broker']['BrokerName']}: {user['Profile']['Name']}"
        )

    try:
        asyncio.run(broker_center_utils.all_broker_login(primary_accounts, "Primary"))
        asyncio.run(broker_center_utils.all_broker_login(today_active_users, "Client"))
        send_admin_message_via_discord("All brokers logged in successfully")
    except Exception as e:
        logger.error(f"Error in logging in brokers: {e}")
        send_admin_message_via_discord(f"Error in logging in brokers: {e}")


if __name__ == "__main__":
    main()
