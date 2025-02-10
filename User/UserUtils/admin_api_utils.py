"""
Administrative utility functions for user management.
"""

import os
import csv
import pandas as pd
from datetime import datetime
from typing import Dict, List
from dotenv import load_dotenv
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import (
    fetch_collection_data_firebase,
    update_fields_firebase,
)
from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_utils import (
    upload_new_client_data_to_firebase,
)

DIR_PATH = os.getcwd()
ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

logger = LoggerSetup()

ADMIN_DB = os.getenv("FIREBASE_ADMIN_COLLECTION")
CLIENTS_COLLECTION = os.getenv("FIREBASE_USER_COLLECTION")
PARAMS_UPDATE_LOG_CSV_PATH = os.getenv("PARAMS_UPDATE_LOG_CSV_PATH")
ERROR_LOG_PATH = os.getenv("ERROR_LOG_PATH")
ERROR_LOG_CSV_PATH = os.getenv("ERROR_LOG_CSV_PATH")

def all_users_data() -> Dict:
    """
    Fetches all user data from the Firebase database.

    Returns:
        dict: A dictionary containing all user data.
    """
    users_data = fetch_collection_data_firebase(CLIENTS_COLLECTION)
    return users_data

def get_next_trader_number() -> int:
    """
    Retrieves the next trader number from the admin database.

    Returns:
        int: The next trader number.
    """
    admin_data = fetch_collection_data_firebase(ADMIN_DB)
    return admin_data.get("NextTradeManId", 0)

def update_new_client_data_to_db(trader_number: str, user_dict: Dict) -> None:
    """
    Updates the user's data in the Firebase database.

    Args:
        trader_number (str): The new user's trader number.
        user_dict (dict): The user's data as a dictionary.
    """
    upload_new_client_data_to_firebase(trader_number, user_dict)

def update_next_trader_number() -> None:
    """
    Updates the next trader number inside the admin database.
    """
    admin_data = fetch_collection_data_firebase(ADMIN_DB)
    current_trader_number = admin_data.get("NextTradeManId", 0)
    next_number = int(current_trader_number[2:]) + 1
    next_trader_number = f"Tr{next_number}"
    next_trader_number_dict = {"NextTradeManId": next_trader_number}
    update_fields_firebase(ADMIN_DB, document=None, data=next_trader_number_dict)

def log_changes_via_webapp(updated_data: Dict, section_info: str = None) -> None:
    """
    Logs updated data along with section information to a CSV file with date and time stamp.

    Args:
        updated_data: The data that has been updated.
        section_info: Additional information about the section being updated.
    """
    filename = PARAMS_UPDATE_LOG_CSV_PATH
    headers = ["date", "updated_info", "section_info"]
    date_str = datetime.now().strftime("%d%b%y %I:%M%p")

    with open(filename, mode="a", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=headers)

        if not os.path.isfile(filename):
            writer.writeheader()

        log_entry = {
            "date": date_str,
            "updated_info": str(updated_data),
            "section_info": section_info if section_info else "",
        }

        writer.writerow(log_entry)

def calculate_aum() -> Dict[str, float]:
    """
    Calculates the Assets Under Management (AUM) for all active users.

    Returns:
        dict: A dictionary containing the AUM for Equity, Debt, Derivatives, and Portfolio.
    """
    users_data = fetch_collection_data_firebase(CLIENTS_COLLECTION)
    aum = {"Equity": 0, "Debt": 0, "Derivatives": 0, "Portfolio": 0}

    for user_id, user_data in users_data.items():
        if user_data.get("Active", False):
            accounts = user_data.get("Accounts", {})
            aum["Equity"] += accounts.get("Equity", {}).get("Equity_FreeCash", 0)
            aum["Debt"] += accounts.get("Debt", {}).get("Debt_FreeCash", 0)
            aum["Derivatives"] += accounts.get("Derivatives", {}).get("Derivatives_FreeCash", 0)
            aum["Portfolio"] += accounts.get("Portfolio", {}).get("Portfolio_FreeCash", 0)

    return aum

def get_total_base_capital() -> float:
    """
    Calculates the total CurrentBaseCapital for all active users.

    Returns:
        float: The total base capital.
    """
    users_data = fetch_collection_data_firebase(CLIENTS_COLLECTION)
    total_base_capital = 0

    for user_id, user_data in users_data.items():
        if user_data.get("Active", False):
            total_base_capital += user_data.get("Accounts", {}).get("CurrentBaseCapital", 0)

    return total_base_capital

def calculate_active_users_data() -> pd.DataFrame:
    """
    Retrieves data for all active users including their account values and holdings.

    Returns:
        pd.DataFrame: A DataFrame containing the active users' data.
    """
    users_data = fetch_collection_data_firebase(CLIENTS_COLLECTION)
    active_users = []

    for tr_no, user_data in users_data.items():
        if user_data.get("Active", False):
            accounts = user_data.get("Accounts", {})
            equity = accounts.get("Equity", {})
            debt = accounts.get("Debt", {})
            derivatives = accounts.get("Derivatives", {})
            portfolio = accounts.get("Portfolio", {})

            total_holdings = portfolio.get("Portfolio_Holdings", 0)

            user_row = {
                "Tr_no": tr_no,
                "Name": user_data.get("Profile", {}).get("Name", ""),
                "Equity_AccountValue": equity,
                "Debt_AccountValue": debt,
                "Derivatives_AccountValue": derivatives,
                "Portfolio_AccountValue": portfolio,
                "Total_Holdings": total_holdings,
            }

            active_users.append(user_row)

    return pd.DataFrame(active_users)
