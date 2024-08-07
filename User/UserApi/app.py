import os, sys
from dotenv import load_dotenv
import numpy as np
import pandas as pd
from typing import Dict, Any, List
from fastapi import HTTPException
from datetime import datetime

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

# Constants
EQUITY = "Equity"
DERIVATIVES = "Derivatives"
EQUITY_STRATEGY_LIST = os.getenv("EQUITY_STRATEGY_LIST")
DERIVATIVES_STRATEGY_LIST = os.getenv("DERIVATIVES_STRATEGY_LIST")
# importing packages
import User.UserApi.schemas as schemas
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import (
    discord_admin_bot,
)
from User.UserApi.userapi_utils import *
from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import (
    fetch_collection_data_firebase,
    update_collection,
    update_fields_firebase,
    delete_fields_firebase,
)
from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
    fetch_users_for_strategies_from_firebase,
    fetch_user_json_from_firebase,
)
from Executor.NSEStrategies.NSEStrategiesUtil import (
    fetch_strategy_users,
    StrategyBase,
    place_order_single_user,
)
from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import (
    Instrument as instrument_obj,
    get_single_ltp,
)

logger = LoggerSetup()


def check_credentials(user_credentials: schemas.LoginUserDetails):
    """
    Checks the user credentials against the database.

    Args:
        user_credentials (schemas.LoginUserDetails): An object containing the user's credentials.

    Returns:
        trader_no if the credentials are valid, None otherwise.
    """
    users_data = all_users_data()

    for trader_no, user in users_data.items():
        # Assuming user_name and password are top-level keys in each user dict
        if (
            user_credentials.Email == user["Profile"]["usr"]
            and user_credentials.Password == user["Profile"]["pwd"]
        ):
            return trader_no
    return None


user_data_collection = {}


def store_accounts_data(user_id, data):
    """
    This function stores the accounts data for a user in the user_data_collection dictionary.

    Args:
    user_id (str): The user ID.
    data (dict): The accounts data to be stored.
    """
    if user_id not in user_data_collection:
        user_data_collection[user_id] = {}
    user_data_collection[user_id]["Accounts"] = data
    return user_data_collection[user_id]


def store_profile_data(user_id, data):
    """
    This function stores the profile data for a user in the user_data_collection dictionary.

    Args:
    user_id (str): The user ID.
    data (dict): The profile data to be stored.
    """
    if user_id not in user_data_collection:
        user_data_collection[user_id] = {}
    user_data_collection[user_id]["Profile"] = data
    return user_data_collection[user_id]


def store_broker_data(user_id, data):
    """
    This function stores the broker data for a user in the user_data_collection dictionary.

    Args:
    user_id (str): The user ID.
    data (dict): The broker data to be stored.
    """
    if user_id not in user_data_collection:
        user_data_collection[user_id] = {}
    user_data_collection[user_id]["Broker"] = data
    return user_data_collection[user_id]


def store_strategies_data(user_id, data):
    """
    This function stores the strategies data for a user in the user_data_collection dictionary.

    Args:
    user_id (str): The user ID.
    data (dict): The strategies data to be stored.
    """
    if user_id not in user_data_collection:
        user_data_collection[user_id] = {}
    user_data_collection[user_id]["Strategies"] = data
    return user_data_collection[user_id]


def store_tr_no(user_id, data):
    """
    This function stores the trader number for a user in the user_data_collection dictionary.

    Args:
    user_id (str): The user ID.
    data (str): The trader number to be stored.
    """
    if user_id not in user_data_collection:
        user_data_collection[user_id] = {}
    user_data_collection[user_id]["Tr_No"] = data
    return user_data_collection[user_id]


def store_active_status(user_id, data):
    """
    This function stores the active status for a user in the user_data_collection dictionary.

    Args:
    user_id (str): The user ID.
    data (dict): The active status data to be stored.
    """
    if user_id not in user_data_collection:
        user_data_collection[user_id] = {}
    user_data_collection[user_id]["Active"] = data
    return user_data_collection[user_id]


def merge_and_register_user(user_id):
    """
    This function merges the user data from the user_data_collection dictionary and registers the user.

    Args:
    user_id (str): The user ID.

    Returns:
    dict: A dictionary containing the user details and the response from the register_user function.
    """
    if user_id in user_data_collection:
        user_detail = user_data_collection.pop(
            user_id
        )  # Retrieve and remove from temporary storage
        try:
            # Assuming register_user is a function that takes the complete user details and saves them to the DB
            response = register_user(user_detail)
            return {"message": "User registered successfully", "details": response}
        except Exception as e:
            raise Exception(f"Failed to register user: {e}")
    else:
        raise Exception("User data not found for registration")


def register_user(user_detail: Dict[str, Any]):
    """
    Registers a new user by adding the user details to the database.

    Args:
        user_detail (Dict[str, Any]): A dictionary containing the user's details.
    """

    # Check if user_detail is a Pydantic model or already a dictionary
    if hasattr(user_detail, "model_dump"):
        user_detail_dict = user_detail.model_dump()
    elif hasattr(user_detail, "dict"):
        user_detail_dict = user_detail.dict()
    else:
        user_detail_dict = user_detail  # It's already a dictionary

    try:
        # check if user_detail_dict has Accounts, Profile, Broker, Strategies keys
        if (
            "Accounts"
            and "Active"
            and "Profile"
            and "Broker"
            and "Strategies" in user_detail_dict
        ):
            update_new_client_data_to_db(get_next_trader_number(), user_detail_dict)
            update_next_trader_number()
            return {"message": "User registered successfully"}
    except Exception:
        raise HTTPException(
            status_code=500, detail=str("Fields missing in user detail")
        )


def get_user_profile(tr_no: str):
    """
    Retrieves the user profile based on the trader number (tr_no).

    Args:
        tr_no (str): The trader number of the user.

    Returns:
        schemas.LoginUserDetails: An object containing the user's name, email, and phone number.

    Raises:
        KeyError: If the user with the given trader number is not found.
    """
    # Assume fetching user profile from a database
    users_data = all_users_data()
    for user_id, user in users_data.items():
        if user["Tr_No"] == tr_no:
            strategies = []
            for strategy_name, strategy_data in user["Strategies"].items():
                strategies.append(strategy_name)
            profile_data = {
                "Name": user["Profile"]["Name"],
                "Email": user["Profile"]["Email"],
                "Phone": user["Profile"]["PhoneNumber"],
                "Date of Birth": user["Profile"]["DOB"],
                "Aadhar Card": user["Profile"]["AadharCardNo"],
                "Pan Card": user["Profile"]["PANCardNo"],
                "Bank Name": user["Profile"]["BankName"],
                "Bank Account Number": user["Profile"]["BankAccountNo"],
                "Broker Name": user["Broker"]["BrokerName"],
                "Strategies": strategies,
            }
            return profile_data
        else:
            raise KeyError("User not found")


def get_portfolio_stats(tr_no: str):
    """
    Retrieves the portfolio stats view for a specific user by their user ID.

    Args:
    user_id: The unique identifier of the user.

    Returns:
    dict: The portfolio stats view.
    """
    # Assume fetching user profile from a database
    USER_DB_FOLDER_PATH = os.getenv("USR_TRADELOG_DB_FOLDER")
    users_db_path = os.path.join(USER_DB_FOLDER_PATH, f"{tr_no}.db")
    user_stats = create_portfolio_stats(users_db_path)
    # TODO: Check if latest account value is required for plotting the graph

    # Convert DataFrame to a list of dictionaries and ensure JSON serializable
    result = user_stats.to_dict(orient="records")

    # Ensure all values are JSON serializable
    for i, record in enumerate(result):
        for key, value in record.items():
            if isinstance(value, (np.integer, int)):
                record[key] = int(value)
            elif isinstance(value, (np.floating, float)):
                record[key] = float(value)
            elif isinstance(value, (np.datetime64, pd.Timestamp)):
                record[key] = value.isoformat()  # Convert datetime to ISO format
            elif isinstance(value, np.ndarray):
                record[key] = value.tolist()
            else:
                record[key] = str(value)  # Convert any other types to string
    return result


def monthly_returns_data(tr_no: str, page: int, page_size: int):
    """
    Retrieves the paginated monthly returns data for a specific user by their user ID.

    Args:
    tr_no: The unique identifier of the user.
    page: The page number.
    page_size: The number of items per page.

    Returns:
    dict: The paginated monthly returns data.
    """
    USER_DB_FOLDER_PATH = os.getenv("USR_TRADELOG_DB_FOLDER")
    users_db_path = os.path.join(USER_DB_FOLDER_PATH, f"{tr_no}.db")
    user_stats = create_portfolio_stats(users_db_path)
    return get_monthly_returns_data(user_stats, page, page_size)


def weekly_cummulative_returns_data(tr_no: str, page: int, page_size: int):
    """
    Retrieves the paginated weekly cummulative returns data for a specific user by their user ID.

    Args:
    tr_no: The unique identifier of the user.
    page: The page number.
    page_size: The number of items per page.

    Returns:
    dict: The paginated weekly cummulative returns data.
    """
    USER_DB_FOLDER_PATH = os.getenv("USR_TRADELOG_DB_FOLDER")
    users_db_path = os.path.join(USER_DB_FOLDER_PATH, f"{tr_no}.db")
    user_stats = create_portfolio_stats(users_db_path)
    return get_weekly_cumulative_returns_data(user_stats, page, page_size)


def individual_strategy_data(tr_no: str, strategy_name: str, page: int, page_size: int):
    """
    Retrieves the paginated individual strategy data for a specific user by their user ID and strategy name.

    Args:
    tr_no: The unique identifier of the user.
    strategy_name: The name of the strategy.
    page: The page number.
    page_size: The number of items per page.

    Returns:
    dict: The paginated individual strategy data.
    """
    strategy_data = get_individual_strategy_data(tr_no, strategy_name, page, page_size)
    return strategy_data


def graph_data(tr_no: str, strategy_name: str):
    """
    Retrieves the strategy graph data for a specific user by their user ID and strategy name.

    Args:
        tr_no (str): The user's ID.
        strategy_name (str): The name of the strategy.

    Returns:
        dict: The strategy graph data for the specified user and strategy.
    """
    graph_data = strategy_graph_data(tr_no, strategy_name)
    return graph_data


def strategy_statistics(tr_no: str, strategy_name: str) -> Dict[str, Any]:
    """
    Retrieves and calculates strategy statistics for a specific user's strategy.

    Args:
    tr_no: The unique identifier of the user.
    strategy_name: The name of the strategy.

    Returns:
    Dict: The calculated strategy statistics.
    """
    try:
        page = 1
        page_size = 1000000000
        data = get_individual_strategy_data(tr_no, strategy_name, page, page_size)

        if data is None or data.get("items") is None:
            return None

        df = data["items"]
        is_signals = strategy_name != "Holdings"

        return calculate_strategy_statistics(df, is_signals)

    except Exception as e:
        # Log the error here if needed
        raise e


def broker_bank_transactions_data(tr_no: str, mode: str, from_date, to_date):
    """
    Retrieves the broker and bank transactions data for a specific user by their user ID.

    Args:
    user_id: The unique identifier of the user.

    Returns:
    dict: The broker and bank transactions data.
    """

    transaction_data = get_broker_bank_transactions_data(
        tr_no, mode, from_date, to_date
    )

    return transaction_data


def get_strategies_for_user(tr_no: str):
    """
    Retrieves the users associated with a specific strategy.

    Args:
        strategy (str): The name of the strategy.

    Returns:
        list: A list of user names associated with the strategy.
    """
    return fetch_strategies_for_user(tr_no)


def get_users_holdings(tr_no: str, mode: str):
    """
    Retrieves the users' equity holdings.

    Args:
        tr_no (str): The user's ID.
        mode (str): The mode of holdings to retrieve.

    Returns:
        list: A list of equity holdings for the user.

    Raises:
        HTTPException: If there's an error fetching from the database.
    """
    holdings = get_users_db_holdings(tr_no, mode)
    return holdings


def update_market_info_params(updated_market_info):
    """
    Update market info parameters.

    This function updates the market info parameters in the Firebase database.
    It also logs the changes and sends a notification via Discord.

    Args:
    updated_market_info (dict): A dictionary containing the updated market info parameters.

    Returns:
    dict: A message indicating successful update.
    """
    if isinstance(updated_market_info, schemas.MarketInfoParams):
        updated_market_info = updated_market_info.dict()

    # Update the database
    update_collection(MARKET_INFO_FB_COLLECTION, updated_market_info)

    # Log changes
    log_changes_via_webapp(updated_market_info)

    # Send Discord notification
    message = f"Market info updated for {updated_market_info}"
    discord_admin_bot(message)

    return {"message": "Market info updated successfully!"}


def get_market_info_params():
    """
    Fetch current market info parameters.

    This function retrieves the current market info parameters from the Firebase database.

    Returns:
    dict: The current market info parameters.
    """
    market_info = fetch_collection_data_firebase(MARKET_INFO_FB_COLLECTION)
    return market_info


def update_strategy_qty_amplifier(strategy, amplifier):
    """
    Update StrategyQtyAmplifier for a specific strategy or all strategies inside the market info params of the strategy.

    This function updates the StrategyQtyAmplifier for a specific strategy or all strategies in the Firebase database.
    It also logs the changes and sends a notification via Discord.

    Args:
    strategy (str): The name of the strategy to update, or 'all' for all strategies.
    amplifier (float): The new StrategyQtyAmplifier value.

    Returns:
    dict: A message indicating successful update.
    """
    try:
        active_strategies = ACTIVE_STRATEGIES

        if strategy.lower() == "all":
            for strat in active_strategies:
                update_path = f"{strat}/MarketInfoParams/"
                update_fields_firebase(
                    STRATEGIES_FB_COLLECTION,
                    update_path,
                    {"StrategyQtyAmplifier": amplifier},
                )
            return {
                "message": f"StrategyQtyAmplifier set to {amplifier} for all strategies."
            }
        else:
            if strategy not in active_strategies:
                raise HTTPException(
                    status_code=404, detail=f"Strategy '{strategy}' not found."
                )
            update_path = f"{strategy}/MarketInfoParams/"
            update_fields_firebase(
                STRATEGIES_FB_COLLECTION,
                update_path,
                {"StrategyQtyAmplifier": amplifier},
            )
            return {
                "message": f"StrategyQtyAmplifier set to {amplifier} for {strategy}."
            }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error updating StrategyQtyAmplifier: {str(e)}"
        )


def modify_strategy_params(strategy_name, section, updated_params):
    """
    Modify strategy parameters for a specific strategy.

    This function modifies the parameters for a given strategy in the Firebase database.
    NOTE: 1. For variables that are lists, the response should be sent as a list.
    For example, if the section is "Instruments", the response should be sent as a list of instruments.
    2. If the section is "MarketInfoParams", the response should be sent as a dictionary.
    3. If the section is "Root-level values", the response should be sent as a dictionary.
    Example: section : Description and request body should be like this {"Description": "New Description"}

    Args:
        strategy_name (str): The name of the strategy to modify.
        section (str): The section of the strategy to modify.
        updated_params (dict): The updated parameters for the strategy.


    Returns:
        dict: A message indicating successful update.
    """
    strategies = fetch_collection_data_firebase(STRATEGIES_FB_COLLECTION)

    if strategy_name not in strategies:
        raise HTTPException(
            status_code=404, detail=f"Strategy '{strategy_name}' not found."
        )

    strategy_params = strategies[strategy_name]

    # Handle root-level values
    root_level_fields = ["Description", "NextTradeId", "StrategyName", "StrategyPrefix"]
    if section in root_level_fields:
        update_fields_firebase(STRATEGIES_FB_COLLECTION, strategy_name, updated_params)
        log_changes_via_webapp({section: updated_params})
        discord_admin_bot(f"{section} updated for {strategy_name}")
        return {"message": f"{section} for {strategy_name} updated successfully!"}

    # Handle the Instruments list
    if section == "Instruments":
        if not isinstance(updated_params["Instruments"], list):
            raise HTTPException(status_code=400, detail="Instruments must be a list.")
        update_fields_firebase(STRATEGIES_FB_COLLECTION, strategy_name, updated_params)
        log_changes_via_webapp({"Instruments": updated_params})
        discord_admin_bot(f"Instruments list updated for {strategy_name}")
        return {"message": f"Instruments for {strategy_name} updated successfully!"}

    # Handle nested objects
    if section not in strategy_params or section == "MarketInfoParams":
        raise HTTPException(
            status_code=404, detail=f"Section '{section}' not found or not editable."
        )

    # Update the nested object
    update_fields_firebase(
        STRATEGIES_FB_COLLECTION, strategy_name, {section: updated_params}
    )

    # Log changes
    log_changes_via_webapp(updated_params, section_info=section)

    # Send Discord notification
    message = f"Params {updated_params} changed for {strategy_name} in {section}"
    discord_admin_bot(message)

    return {"message": f"{section} for {strategy_name} updated successfully!"}


def get_strategy_params(strategy_name):
    """
    Fetch current parameters for a specific strategy.

    This function retrieves the current parameters for a given strategy from the Firebase database.

    Args:
        strategy_name (str): The name of the strategy to fetch.

    Returns:
        dict: The current parameters for the strategy.

    Raises:
        HTTPException: If there's an error fetching from the database or if the strategy is not found.
    """
    strategies = fetch_collection_data_firebase(STRATEGIES_FB_COLLECTION)
    if strategy_name not in strategies:
        raise HTTPException(
            status_code=404, detail=f"Strategy '{strategy_name}' not found."
        )

    strategy_params = strategies[strategy_name]
    # Remove MarketInfoParams as it's not editable through this interface
    strategy_params.pop("MarketInfoParams", None)
    return strategy_params


def get_user_risk_params(strategy, trader_numbers):
    """
    Fetch current risk percentage and sector/cap for a specific strategy and user.

    This function retrieves the current risk percentage and sector/cap for a given strategy and user from the Firebase database.

    Args:
        strategy (str): The name of the strategy to fetch.
        trader_numbers (Optional[List[str]]): List of trader numbers to fetch, or omit for all traders.

    Returns:
        dict: The current risk percentage and sector/cap for the strategy and user.

    Raises:
        HTTPException: If there's an error fetching from the database or if the strategy or user is not found.
    """

    active_strategies = ACTIVE_STRATEGIES
    if strategy not in active_strategies:
        raise HTTPException(status_code=400, detail=f"Invalid strategy: {strategy}")

    strategy_active_users = fetch_users_for_strategies_from_firebase(strategy)
    all_trader_numbers = [user["Tr_No"] for user in strategy_active_users]

    if trader_numbers is None:
        trader_numbers = all_trader_numbers
    else:
        invalid_traders = set(trader_numbers) - set(all_trader_numbers)
        if invalid_traders:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid trader numbers: {', '.join(invalid_traders)}",
            )

    result = {}
    for trader_number in trader_numbers:
        user_data = fetch_collection_data_firebase(
            CLIENTS_COLLECTION, document=trader_number
        )
        if user_data and "Strategies" in user_data:
            if strategy in EQUITY_STRATEGY_LIST:
                result[trader_number] = {
                    "RiskPerTrade": "Equity risk is at strategy level"
                }
            elif strategy in DERIVATIVES_STRATEGY_LIST:
                if strategy in user_data["Strategies"].get("Derivatives", {}):
                    strategy_data = user_data["Strategies"]["Derivatives"][strategy]
                    result[trader_number] = {
                        "RiskPerTrade": strategy_data.get("RiskPerTrade", "N/A"),
                    }
                else:
                    result[
                        trader_number
                    ] = "No data available for this derivative strategy"
            else:
                result[trader_number] = "Strategy type not recognized"
        else:
            result[trader_number] = "No data available"

    return result


def update_user_risk_params(strategy, trader_numbers, risk_percentage):
    """
    Update risk percentage and sector/cap for a specific strategy and user.

    This function updates the risk percentage for a given strategy and user in the Firebase database.

    Args:
        strategy (str): The name of the strategy to update.
        trader_numbers (List[str]): List of trader numbers to update, or ['all'] for all traders.
        risk_percentage (float): Risk percentage to set (between 0.0 and 10.0).

    Returns:
        dict: A message indicating successful update.

    Raises:
        HTTPException: If there's an error updating the database or if the input is invalid.
    """
    active_strategies = ACTIVE_STRATEGIES
    if strategy not in active_strategies:
        raise HTTPException(status_code=400, detail=f"Invalid strategy: {strategy}")

    strategy_active_users = fetch_users_for_strategies_from_firebase(strategy)
    all_trader_numbers = [user["Tr_No"] for user in strategy_active_users]

    if trader_numbers == ["all"]:
        trader_numbers = all_trader_numbers
    else:
        invalid_traders = set(trader_numbers) - set(all_trader_numbers)
        if invalid_traders:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid trader numbers: {', '.join(invalid_traders)}",
            )

    update_fields = {}
    update_path = ""

    if strategy in EQUITY_STRATEGY_LIST:
        message = f"Equity risk is at strategy level. No changes made for {strategy}."
    elif strategy in DERIVATIVES_STRATEGY_LIST:
        update_fields = {"RiskPerTrade": risk_percentage}
        update_path = f"Strategies/{DERIVATIVES}/{strategy}/"

        for trader_number in trader_numbers:
            update_fields_firebase(
                CLIENTS_COLLECTION, trader_number, update_fields, update_path
            )

        message = f"Params {list(update_fields.keys())} changed for {strategy} for {trader_numbers}"
    else:
        raise HTTPException(
            status_code=400, detail=f"Unrecognized strategy type: {strategy}"
        )

    log_changes_via_webapp(update_fields, section_info=message)
    discord_admin_bot(message)

    return {"message": message}


def get_user_list_from_db():
    """
    Fetch user list from the database.

    Args:
        None

    Returns:
        list: A list of user names.
    """
    try:
        user_list = fetch_collection_data_firebase(CLIENTS_COLLECTION)
        user_names = []
        for (
            key,
            profile,
        ) in user_list.items():  # Changed to items() to get both key and value
            if "Profile" in profile and "Name" in profile["Profile"]:
                user_names.append(
                    {"username": profile["Profile"]["Name"], "tr_no": profile["Tr_No"]}
                )
            else:
                # Raising ValueError including the key of the profile
                raise ValueError(
                    f"Missing 'Name' or 'Profile' key in user data {key}: {profile}"
                )
        return user_names
    except Exception as e:
        # Catching all exceptions and raising HTTPException with the error message
        raise HTTPException(status_code=500, detail=str(e))


def get_strategy_list():
    """
    Fetches the list of strategies from the database.

    Returns:
        list: A list of strategy names.
    """
    return ACTIVE_STRATEGIES


def fetch_user_details_by_username(username: str):
    """
    Fetch user details by username from the database.

    Args:
        username (str): The username of the user.

    Returns:
        list: A list of user details.
    """
    user_list = fetch_collection_data_firebase(CLIENTS_COLLECTION)
    user_details = [
        profile
        for profile in user_list.values()
        if profile["Profile"]["Name"] == username
    ]
    return user_details


def update_user_section(user_id: str, section: str, details: dict):
    """
    Update user details by replacing the existing details with the new details.

    Args:
        user_id (str): The ID of the user to update.
        section (str): The section to update.
        details (dict): The new details to update.

    Returns:
        dict: A message indicating successful update.
    """
    root_level_fields = ["Tr_No", "Active"]

    if section in root_level_fields:
        # Handle root-level updates
        update_fields_firebase(CLIENTS_COLLECTION, user_id, parse_value(details))
        log_changes_via_webapp({section: details})
        discord_admin_bot(f"{section} updated for user {user_id}")
        return {"message": f"{section} for user {user_id} updated successfully!"}

    # Handle nested dictionary updates
    if section not in ["Accounts", "Broker", "Profile", "Strategies"]:
        raise ValueError(f"Invalid section: {section}")

    # Parse values in the details dictionary
    parsed_details = {key: parse_value(value) for key, value in details.items()}

    path = f"{user_id}/{section}"

    update_fields_firebase(CLIENTS_COLLECTION, path, parsed_details)
    log_changes_via_webapp({section: parsed_details})
    discord_admin_bot(f"Section {section} updated for user {user_id}")
    return {"message": f"{section} for user {user_id} updated successfully!"}


def fetch_users_for_strategy(strategy_name: str):
    """
    Fetches the list of users who have opted for a specific strategy.

    Args:
        strategy_name (str): The name of the strategy.

    Returns:
        list: A list of users who have opted for the strategy.
    """
    try:
        if strategy_name in EQUITY_STRATEGY_LIST:
            users = fetch_strategy_users(strategy_name, asset_segment=EQUITY)
            tr_no_list = [user["Tr_No"] for user in users]
            return tr_no_list
        elif strategy_name in DERIVATIVES_STRATEGY_LIST:
            users = fetch_strategy_users(strategy_name, asset_segment=DERIVATIVES)
            tr_no_list = [user["Tr_No"] for user in users]
            return tr_no_list
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching users for strategy: {str(e)}"
        )


def get_order_modes():
    """
    Fetches the list of order modes.

    Returns:
        list: A list of order modes.
    """
    return ["Complete Order", "Repair Order"]


def get_qty_calculation_mode():
    """
    Fetches the qty calculation mode.

    Returns:
        list: A list of qty calculation modes.
    """
    return ["Auto", "Manual"]


def fetch_today_order(strategy_name: str):
    """
    Process complete order.

    Args:
        strategy_name (str): The name of the strategy.

    Returns:
        list: A list of today's orders.
    """
    strategy_params = get_strategy_params(strategy_name)
    today_orders_list = []
    if strategy_params.get("TodayOrders"):
        today_orders = strategy_params.get("TodayOrders")
        for order_id, order_details in today_orders.items():
            if order_details.get("EntryTime").split(" ")[0] == datetime.now().strftime(
                "%Y-%m-%d"
            ):
                today_orders_list.append(order_details)
        return today_orders_list
    else:
        return {"message": "Today's orders not processed yet!"}


def place_complete_order(
    strategy_name: str,
    users: list,
    symbols: list,
    qty_calculation_mode: str,
    trade_id: str,
    qty: float = None,
    setup_name: str = None,
):
    """
    Places orders for the order mode "Complete Order".

    Args:
        strategy_name (str): The name of the strategy.(Ex: ExpiryTrader, LONG_RATIO)
        users (list): The list of users.
        symbols (list): The list of symbols.
        qty_calculation_mode (str): The qty calculation mode.
        qty (float): The quantity.
        trade_id (str): The trade id.
        setup_name (str): The setup name.
    """
    try:
        for user in users:
            for symbol in symbols:
                exchange = instrument_obj().get_segment_by_symbol(symbol)
                exchange_token = instrument_obj().get_exchange_token_by_name(
                    symbol, exchange
                )
                strategy_obj = StrategyBase.load_from_db(strategy_name)
                order_type = strategy_obj.GeneralParams.OrderType
                product_type = strategy_obj.GeneralParams.ProductType
                strategy_type = strategy_obj.GeneralParams.StrategyType
                num_stocks = strategy_obj.ExtraInformation.StocksPerStrategy
                if num_stocks is None:
                    num_stocks = 1

                ltp = get_single_ltp(exchange_token=exchange_token, segment=exchange)
                ltp = round(ltp * 20) / 20

                update_strategy_qty(
                    strategy_name=strategy_name,
                    user=user,
                    qty_calculation_mode=qty_calculation_mode,
                    qty=qty,
                    ltp=ltp,
                    strategy_type=strategy_type,
                    num_stocks=num_stocks,
                    setup_name=setup_name,
                )
                order_details = prepare_order_details(
                    strategy_name=strategy_name,
                    symbol=symbol,
                    exchange_token=exchange_token,
                    order_type=order_type,
                    product_type=product_type,
                    trade_id=trade_id,
                    ltp=ltp,
                    setup_name=setup_name,
                )
                user_details = fetch_user_json_from_firebase(user)
                place_order_single_user([user_details], order_details)
            return {"message": "Order placed successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def place_repair_order(
    strategy_name: str,
    users: list,
    symbols: list,
    qty_calculation_mode: str,
    trade_id: str,
    qty: float = None,
    setup_name: str = None,
):
    """
    Places orders for the order mode "Repair Order".

    Args:
        strategy_name (str): The name of the strategy.
        users (list): The list of users.
        symbols (list): The list of symbols.
        qty_calculation_mode (str): The qty calculation mode.
        qty (float): The quantity.
        trade_id (str): The trade id.
        setup_name (str): The setup name.
    """
    try:
        for user in users:
            for symbol in symbols:
                exchange = instrument_obj().get_segment_by_symbol(symbol)
                exchange_token = instrument_obj().get_exchange_token_by_name(
                    symbol, exchange
                )
                strategy_obj = StrategyBase.load_from_db(strategy_name)
                order_type = strategy_obj.GeneralParams.OrderType
                product_type = strategy_obj.GeneralParams.ProductType
                strategy_type = strategy_obj.GeneralParams.StrategyType
                num_stocks = strategy_obj.ExtraInformation.StocksPerStrategy
                if num_stocks is None:
                    num_stocks = 1

                ltp = get_single_ltp(exchange_token=exchange_token, segment=exchange)
                ltp = round(ltp * 20) / 20

                update_strategy_qty(
                    strategy_name=strategy_name,
                    user=user,
                    qty_calculation_mode=qty_calculation_mode,
                    qty=qty,
                    ltp=ltp,
                    strategy_type=strategy_type,
                    num_stocks=num_stocks,
                    setup_name=setup_name,
                )
                order_details = prepare_order_details(
                    strategy_name=strategy_name,
                    symbol=symbol,
                    exchange_token=exchange_token,
                    order_type=order_type,
                    product_type=product_type,
                    trade_id=trade_id,
                    ltp=ltp,
                    setup_name=setup_name,
                )
                user_details = fetch_user_json_from_firebase(user)
                place_order_single_user([user_details], order_details)
        return {"message": "Order placed successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def delete_user(tr_no: str):
    """
    Deletes a user from the database.

    Args:
        tr_no (str): The trader number of the user to delete.
    """
    CLIENTS_USER_FB_DB = os.getenv("FIREBASE_USER_COLLECTION")
    delete_fields_firebase(CLIENTS_USER_FB_DB, tr_no)


def get_aum_from_firebase():
    """
    Calculates the Assets Under Management (AUM) for all active users.

    Returns:
        dict: A dictionary containing the AUM for Equity, Debt, Derivatives, and Portfolio.
    """
    return calculate_aum()


def get_total_base_capital_from_firebase():
    """
    Calculates the total CurrentBaseCapital for all active users.

    Returns:
        dict: A dictionary containing the total base capital.
    """
    return get_total_base_capital()


def get_active_users_data_from_firebase():
    """
    Retrieves data for all active users from Firebase.

    Returns:
        dict: A dictionary containing active users' data.
    """
    return calculate_active_users_data()
