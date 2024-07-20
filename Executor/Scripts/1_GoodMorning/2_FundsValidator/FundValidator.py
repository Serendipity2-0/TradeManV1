import os, sys
from dotenv import load_dotenv
import datetime as dt
from time import sleep

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

# Load environment variables from the trademan.env file
ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.ExeUtils import (
    get_second_previous_trading_day,
    get_previous_freecash,
)
import Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils as broker_center_utils
from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import (
    update_fields_firebase,
    delete_fields_firebase,
)
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()

CLIENTS_USER_FB_DB = os.getenv("FIREBASE_USER_COLLECTION")

active_users = broker_center_utils.fetch_active_users_from_firebase()

broker_free_cash = {}
db_free_cash = {}


def fetch_freecash_all_brokers(active_users):
    """
    The function fetches free cash for all active users from different brokers and returns a dictionary
    mapping user transaction numbers to their respective free cash amounts.

    :param active_users: active_users is a list of active users, where each user is a dictionary
    containing information about the user, including their broker details. The user dictionary has keys
    like "Broker" and "Tr_No" which store information about the user's broker and transaction number
    respectively
    :return: The function `fetch_freecash_all_brokers` returns a dictionary `broker_free_cash`
    containing the free cash/margin information for each user in the `active_users` list. The keys in
    the dictionary are the `Tr_No` of each user, and the values are the free cash/margin amounts fetched
    from different brokers based on the user's broker name.
    """
    logger.debug(f"Fetching free cash no of users for brokers: {len(active_users)}")
    for user in active_users:
        if user["Broker"]["BrokerName"] == broker_center_utils.ZERODHA:
            cash_margin = broker_center_utils.zerodha_adapter.zerodha_fetch_free_cash(
                user["Broker"]
            )
            broker_free_cash[user["Tr_No"]] = cash_margin
        elif user["Broker"]["BrokerName"] == broker_center_utils.ALICEBLUE:
            cash_margin = broker_center_utils.alice_adapter.alice_fetch_free_cash(
                user["Broker"]
            )
            broker_free_cash[user["Tr_No"]] = cash_margin
        elif user["Broker"]["BrokerName"] == broker_center_utils.FIRSTOCK:
            cash_margin = broker_center_utils.firstock_adapter.firstock_fetch_free_cash(
                user["Broker"]
            )
            broker_free_cash[user["Tr_No"]] = cash_margin
    return broker_free_cash


def fetch_freecash_all_db(active_users):  # pass active_users['Accounts'] as argument
    """
    This function fetches free cash data for active users from a Firebase database based on the previous
    trading day.

    :param active_users: active_users is a list of users with their account information. Each user in
    the list has a "Tr_No" key which is used as a unique identifier for the user, and an "Accounts" key
    which contains information about the user's accounts. The function fetches the free cash amount for
    each
    :return: The function `fetch_freecash_all_db` is returning a dictionary `db_free_cash` containing
    the free cash values for each user in the `active_users` list.
    """
    logger.debug(
        f"Fetching free cash no of users from Firebase DB: {len(active_users)}"
    )
    previous_trading_day_fb_format = get_previous_freecash(dt.date.today())
    previous_day_key = previous_trading_day_fb_format + "_" + "FreeCash"
    for user in active_users:
        try:
            db_free_cash[user["Tr_No"]] = user["Accounts"][previous_day_key]
        except KeyError:
            logger.error(f"Free cash for {user['Tr_No']} not found in Firebase DB")
            db_free_cash[user["Tr_No"]] = 0
        logger.info(
            f"Free cash for {user['Tr_No']} from Firebase DB: {db_free_cash[user['Tr_No']]}"
        )
    return db_free_cash


def delete_old_free_cash(active_users):
    """
    The function `delete_old_free_cash` deletes keys in active users' accounts that are older than 2
    days and contain '_FreeCash', '_Holdings', or '_AccountValue'.

    :param active_users: Active users is a list of dictionaries where each dictionary represents a user
    and contains information about their accounts. Each user dictionary has a key 'Accounts' which holds
    a list of keys related to the user's account information. The function `delete_old_free_cash`
    iterates over each user in the list and
    """
    # delete all the keys which have _FreeCash , _Holdings and _AccountValue and are older than 2 days
    for user in active_users:
        for key in user["Accounts"]:
            if "_FreeCash" in key or "_Holdings" in key or "_AccountValue" in key:
                second = get_second_previous_trading_day(dt.date.today())
                second = dt.datetime.strptime(second, "%d%b%y")
                if dt.datetime.strptime(key.split("_")[0], "%d%b%y") <= second:
                    logger.info(f"Deleting old key {key} for user {user['Tr_No']}")
                    delete_fields_firebase(
                        CLIENTS_USER_FB_DB, user["Tr_No"], f"Accounts/{key}"
                    )


def compare_freecash(broker_free_cash, db_free_cash):
    """
    The function compares free cash values from brokers and the database, sends notifications if
    there are discrepancies, and updates the database with the latest free cash values if the
    values match within a tolerable difference.

    :param broker_free_cash: A dictionary containing the free cash values fetched from different
    brokers for active users. The keys are the user's transaction numbers (Tr_No), and the values
    are the respective free cash amounts.
    :param db_free_cash: A dictionary containing the free cash values fetched from the Firebase
    database for active users. The keys are the user's transaction numbers (Tr_No), and the values
    are the respective free cash amounts.
    """
    from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import (
        discord_admin_bot,
    )

    tolerable_difference = os.getenv("ACC_DIFF_TOLERANCE")

    discord_admin_bot(f"Today's number of users = {len(broker_free_cash)}")

    for user in broker_free_cash:
        try:
            message = f"Trader Number - {user} : Broker Freecash - {round(broker_free_cash[user],2)} : Difference - {round(broker_free_cash[user] - db_free_cash[user],2)}"
            discord_admin_bot(message)
            sleep(0.3)
        except KeyError:
            logger.error(f"Trader Number - {user} : Free cash not found in DB")
            discord_admin_bot(f"Trader Number - {user} : Free cash not found in DB")

    for user in broker_free_cash:
        logger.info(f"Comparing free cash for {user}")
        # check if the difference is more than 1%
        try:
            if (
                abs(broker_free_cash[user] - db_free_cash[user])
                > float(tolerable_difference) * db_free_cash[user]
            ):
                logger.error(f"Free cash for {user} is not matching")
                discord_admin_bot(
                    f"Free cash for {user} is not matching, BrokerFreeCash - {round(broker_free_cash[user],2)}, DBFreeCash - {round(db_free_cash[user],2)}"
                )
            else:
                logger.info(f"Free cash for {user} is matching")
            update_fields_firebase(
                CLIENTS_USER_FB_DB,
                user,
                {
                    dt.datetime.now().strftime("%d%b%y")
                    + "_FreeCash": broker_free_cash[user]
                },
                "Accounts",
            )
        except Exception as e:
            logger.error(f"Error while comparing free cash for {user} with error: {e}")
            discord_admin_bot(
                f"Error while comparing free cash for {user} with error: {e}"
            )


def main():
    """
    The main function orchestrates the fetching, comparing, and updating of free cash values for
    active users from brokers and the Firebase database. It also deletes old free cash values from
    the database to maintain data consistency.

    The function performs the following steps:
    1. Fetch free cash values for active users from different brokers.
    2. Fetch free cash values for active users from the Firebase database.
    3. Compare the free cash values from brokers and the database.
    4. Delete old free cash values from the database.
    """
    broker_free_cash = fetch_freecash_all_brokers(active_users)
    db_free_cash = fetch_freecash_all_db(active_users)
    compare_freecash(broker_free_cash, db_free_cash)
    delete_old_free_cash(active_users)


if __name__ == "__main__":
    main()
