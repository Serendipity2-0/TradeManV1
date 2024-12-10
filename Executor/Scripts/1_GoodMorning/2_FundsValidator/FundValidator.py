import os, sys
from dotenv import load_dotenv
import datetime as dt
from time import sleep
import json

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
from Executor.ExecutorUtils.BrokerCenter.broker_utils import (
    ZERODHA,
    ALICEBLUE,
    FIRSTOCK,
)
import Executor.ExecutorUtils.BrokerCenter.Brokers.AliceBlue.alice_adapter as alice_adapter
import Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter as zerodha_adapter
import Executor.ExecutorUtils.BrokerCenter.Brokers.Firstock.firstock_adapter as firstock_adapter
from Executor.ExecutorUtils.ExeDBUtils.MongoUtils.exemongo_adapter import (
    update_fields_mongodb,
    delete_fields_mongodb,
)
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()

CLIENTS_USER_DB = os.getenv("MONGO_USER_COLLECTION", "clients")

active_users = broker_center_utils.fetch_active_users()

broker_free_cash = {}
db_free_cash = {}


def parse_firstock_response(response):
    """
    Parse Firstock API response which could be either a string or dict.
    
    Args:
        response: The response from Firstock API
        
    Returns:
        dict: Parsed response as dictionary
    """
    try:
        if isinstance(response, str):
            return json.loads(response)
        elif isinstance(response, dict):
            return response
        else:
            logger.error(f"Unexpected response type from Firstock: {type(response)}")
            return {}
    except json.JSONDecodeError:
        logger.error(f"Failed to parse Firstock response: {response}")
        return {}


def ensure_float(value):
    """
    Ensures a value is converted to float, handling various input types.
    
    Args:
        value: Value to convert, can be string, int, float or None
        
    Returns:
        float: The converted value, or 0.0 if conversion fails
    """
    if value is None:
        return 0.0
    try:
        if isinstance(value, str):
            # Remove any commas and convert to float
            value = value.replace(",", "")
        return float(value)
    except (ValueError, TypeError):
        logger.error(f"Failed to convert value to float: {value}")
        return 0.0


def fetch_freecash_all_brokers(active_users):
    """
    The function fetches free cash for all active users from different brokers and returns a dictionary
    mapping user transaction numbers to their respective free cash amounts.

    Args:
        active_users (list): List of active users, where each user is a dictionary containing information 
                           about the user, including their broker details.

    Returns:
        dict: Dictionary containing the free cash/margin information for each user.
    """
    logger.debug(f"Fetching free cash no of users for brokers: {len(active_users)}")
    for user in active_users:
        try:
            if user["Broker"]["BrokerName"] == ZERODHA:
                cash_margin = zerodha_adapter.zerodha_fetch_free_cash(
                    user["Broker"]
                )
                broker_free_cash[user["Tr_No"]] = ensure_float(cash_margin)
            elif user["Broker"]["BrokerName"] == ALICEBLUE:
                cash_margin = alice_adapter.alice_fetch_free_cash(
                    user["Broker"]
                )
                broker_free_cash[user["Tr_No"]] = ensure_float(cash_margin)
            elif user["Broker"]["BrokerName"] == FIRSTOCK:
                response = firstock_adapter.firstock_fetch_free_cash(
                    user["Broker"]
                )
                parsed_response = parse_firstock_response(response)
                cash_margin = parsed_response.get("data", {}).get("cash", 0)
                broker_free_cash[user["Tr_No"]] = ensure_float(cash_margin)
        except Exception as e:
            logger.error(f"Error fetching free cash for user {user['Tr_No']}: {str(e)}")
            broker_free_cash[user["Tr_No"]] = 0.0
    return broker_free_cash


def fetch_freecash_all_db(active_users):
    """
    This function fetches free cash data for active users from MongoDB based on the previous
    trading day.

    Args:
        active_users (list): List of users with their account information.

    Returns:
        dict: Dictionary containing the free cash values for each user.
    """
    logger.debug(
        f"Fetching free cash no of users from MongoDB: {len(active_users)}"
    )
    previous_trading_day_fb_format = get_previous_freecash(dt.date.today())
    previous_day_key = previous_trading_day_fb_format + "_" + "Portfolio_FreeCash"
    for user in active_users:
        try:
            portfolio = user.get("Accounts", {}).get("Portfolio", {})
            if not portfolio:
                logger.error(f"No portfolio data found for user {user['Tr_No']}")
                db_free_cash[user["Tr_No"]] = 0.0
                continue

            # Try both Portfolio_FreeCash and Equity_FreeCash
            free_cash = ensure_float(portfolio.get(previous_day_key))
            if free_cash == 0.0:
                equity_key = previous_trading_day_fb_format + "_" + "Equity_FreeCash"
                free_cash = ensure_float(portfolio.get(equity_key))

            db_free_cash[user["Tr_No"]] = free_cash
        except KeyError:
            logger.error(f"Free cash for {user['Tr_No']} not found in MongoDB")
            db_free_cash[user["Tr_No"]] = 0.0
        logger.info(
            f"Free cash for {user['Tr_No']} from MongoDB: {db_free_cash[user['Tr_No']]}"
        )
    return db_free_cash


def is_valid_date_key(key):
    """
    Check if a key starts with a valid date in the format ddMMMyy.
    
    Args:
        key (str): The key to validate.
        
    Returns:
        bool: True if the key starts with a valid date, False otherwise.
    """
    try:
        # Split the key and check if it has at least one part
        parts = key.split("_")
        if not parts:
            return False
            
        # Try to parse the first part as a date
        dt.datetime.strptime(parts[0], "%d%b%y")
        return True
    except (ValueError, IndexError):
        return False


def delete_old_free_cash(active_users):
    """
    The function deletes keys in active users' accounts that are older than 2 days and contain 
    '_FreeCash', '_Holdings', or '_AccountValue'.

    Args:
        active_users (list): List of active users whose old data needs to be deleted.
    """
    # delete all the keys which have _FreeCash , _Holdings and _AccountValue and are older than 2 days
    for user in active_users:
        try:
            portfolio = user.get("Accounts", {}).get("Portfolio", {})
            if not portfolio:
                logger.warning(f"No portfolio data found for user {user['Tr_No']}")
                continue

            second = get_second_previous_trading_day(dt.date.today())
            second_date = dt.datetime.strptime(second, "%d%b%y")

            for key in portfolio:
                if not any(suffix in key for suffix in ["_FreeCash", "_Holdings", "_AccountValue"]):
                    continue

                if not is_valid_date_key(key):
                    logger.warning(f"Invalid date format in key: {key} for user {user['Tr_No']}")
                    continue

                key_date = dt.datetime.strptime(key.split("_")[0], "%d%b%y")
                if key_date <= second_date:
                    logger.info(f"Deleting old key {key} for user {user['Tr_No']}")
                    delete_fields_mongodb(
                        CLIENTS_USER_DB, user["Tr_No"], f"Accounts/Portfolio/{key}"
                    )
        except Exception as e:
            logger.error(f"Error processing user {user.get('Tr_No', 'Unknown')}: {str(e)}")


def compare_freecash(broker_free_cash, db_free_cash):
    """
    Compares and Updates the Portfolio FreeCash from the broker and MongoDB and
    If the difference is more than the tolerable difference we get a discord notification.

    Args:
        broker_free_cash (dict): Free cash from the broker
        db_free_cash (dict): Free cash from MongoDB
    """
    from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import (
        send_admin_message_via_discord,
    )

    tolerable_difference = ensure_float(os.getenv("ACC_DIFF_TOLERANCE"))
    send_admin_message_via_discord(f"Today's number of users = {len(broker_free_cash)}")

    for user in broker_free_cash:
        try:
            broker_cash = ensure_float(broker_free_cash[user])
            db_cash = ensure_float(db_free_cash[user])
            
            message = f"Trader Number - {user} : Broker Freecash - {round(broker_cash,2)} : Difference - {round(broker_cash - db_cash,2)}"
            send_admin_message_via_discord(message)
            sleep(0.3)
        except KeyError:
            logger.error(f"Trader Number - {user} : Free cash not found in DB")
            send_admin_message_via_discord(
                f"Trader Number - {user} : Free cash not found in DB"
            )

        if db_cash == 0.0:
            logger.warning(f"DB free cash is 0 for user {user}, skipping difference check")
            continue

        if abs(broker_cash - db_cash) > tolerable_difference * db_cash:
            logger.error(f"Free cash for {user} is not matching")
            send_admin_message_via_discord(
                f"Free cash for {user} is not matching, BrokerFreeCash - {round(broker_cash,2)}, DBFreeCash - {round(db_cash,2)}"
            )
        else:
            logger.info(f"Free cash for {user} is matching")

        user_data = next(
            (
                active_user
                for active_user in active_users
                if active_user["Tr_No"] == user
            ),
            None,
        )
        if user_data:
            today_key = dt.datetime.now().strftime("%d%b%y")
            # Update both Portfolio and Equity sections for consistency
            update_fields_mongodb(
                CLIENTS_USER_DB,
                user,
                broker_cash,
                f"Accounts/Portfolio/{today_key}_Portfolio_FreeCash"
            )
            update_fields_mongodb(
                CLIENTS_USER_DB,
                user,
                broker_cash,
                f"Accounts/Portfolio/{today_key}_Equity_FreeCash"
            )
        else:
            logger.error(f"User data not found for {user}")


def main():
    """
    The main function orchestrates the fetching, comparing, and updating of free cash values for
    active users from brokers and MongoDB. It also deletes old free cash values from
    the database to maintain data consistency.

    The function performs the following steps:
    1. Fetch free cash values for active users from different brokers.
    2. Fetch free cash values for active users from MongoDB.
    3. Compare the free cash values from brokers and the database.
    4. Delete old free cash values from the database.
    """
    broker_free_cash = fetch_freecash_all_brokers(active_users)
    db_free_cash = fetch_freecash_all_db(active_users)
    compare_freecash(broker_free_cash, db_free_cash)
    delete_old_free_cash(active_users)


if __name__ == "__main__":
    main()
