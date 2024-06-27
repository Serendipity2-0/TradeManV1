import os, sys
from dotenv import load_dotenv
import numpy as np
import pandas as pd
from typing import Dict, Any
from fastapi import HTTPException

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

# importing packages
import User.UserApi.schemas as schemas
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import (
    discord_admin_bot,
)
from User.UserApi.userapi_utils import (
    ACTIVE_STRATEGIES,
    CLIENTS_COLLECTION,
    MARKET_INFO_FB_COLLECTION,
    STRATEGIES_FB_COLLECTION,
    get_next_trader_number,
    update_new_client_data_to_db,
    all_users_data,
    create_portfolio_stats,
    get_monthly_returns_data,
    get_weekly_cumulative_returns_data,
    get_individual_strategy_data,
    equity_get_broker_bank_transactions_data,
    strategy_graph_data,
    calculate_strategy_statistics,
    log_changes_via_webapp,
)
from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import (
    fetch_collection_data_firebase,
    update_collection,
    update_fields_firebase,
)
from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
    fetch_users_for_strategies_from_firebase,
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


def register_user(user_detail: schemas.UserDetails):
    """
    Registers a new user by adding the user details to the database.

    Args:
        user_detail (schemas.UserDetails): An object containing the user's details.
    """
    user_detail = dict(user_detail)
    update_new_client_data_to_db(get_next_trader_number(), user_detail)
    return {"message": "User registered successfully"}


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


def equity_broker_bank_transactions_data(tr_no: str, from_date, to_date):
    """
    Retrieves the broker and bank transactions data for a specific user by their user ID.

    Args:
    user_id: The unique identifier of the user.

    Returns:
    dict: The broker and bank transactions data.
    """

    transaction_data = equity_get_broker_bank_transactions_data(
        tr_no, from_date, to_date
    )

    return transaction_data


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
    Update StrategyQtyAmplifier for a specific strategy or all strategies.

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
    Modify parameters for a specific section of a strategy.

    This function allows updating the parameters of a specific section for a given strategy.
    It also logs the changes and sends a notification via Discord.

    Args:
        strategy_name (str): The name of the strategy to update.
        section (str): The section of the strategy parameters to update.
        updated_params (Dict[str, Any]): A dictionary containing the updated parameters for the section.

    Returns:
        dict: A message indicating successful update.

    Raises:
        HTTPException: If there's an error updating the database or if the strategy or section is not found.
    """
    # Fetch current strategy data
    strategies = fetch_collection_data_firebase(STRATEGIES_FB_COLLECTION)

    if strategy_name not in strategies:
        raise HTTPException(
            status_code=404, detail=f"Strategy '{strategy_name}' not found."
        )

    strategy_params = strategies[strategy_name]
    if section not in strategy_params or section == "MarketInfoParams":
        raise HTTPException(
            status_code=404, detail=f"Section '{section}' not found or not editable."
        )

    # Update the database
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
        if (
            user_data
            and "Strategies" in user_data
            and strategy in user_data["Strategies"]
        ):
            strategy_data = user_data["Strategies"][strategy]
            result[trader_number] = {
                "RiskPerTrade": strategy_data.get("RiskPerTrade", "N/A"),
                "Sector": strategy_data.get("Sector", "N/A")
                if strategy == "PyStocks"
                else "N/A",
                "Cap": strategy_data.get("Cap", "N/A")
                if strategy == "PyStocks"
                else "N/A",
            }
        else:
            result[trader_number] = "No data available"

    return result


def update_user_risk_params(
    strategy, trader_numbers, risk_percentage, sector=None, cap=None
):
    """
    Update risk percentage and sector/cap for a specific strategy and user.

    This function updates the risk percentage and sector/cap for a given strategy and user in the Firebase database.

    Args:
        strategy (str): The name of the strategy to update.
        trader_numbers (List[str]): List of trader numbers to update, or ['all'] for all traders.
        risk_percentage (float): Risk percentage to set (between 0.0 and 10.0).
        sector (Optional[str]): Sector for PyStocks strategy.
        cap (Optional[str]): Cap for PyStocks strategy.

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

    update_fields = {"RiskPerTrade": risk_percentage}
    if strategy == "PyStocks":
        if not sector or not cap:
            raise HTTPException(
                status_code=400,
                detail="Sector and Cap are required for PyStocks strategy",
            )
        update_fields.update({"Sector": sector, "Cap": cap})

    for trader_number in trader_numbers:
        update_path = f"Strategies/{strategy}/"
        update_fields_firebase(
            CLIENTS_COLLECTION, trader_number, update_fields, update_path
        )

    message = f"Params {list(update_fields.keys())} changed for {strategy} for {trader_numbers}"
    log_changes_via_webapp(update_fields, section_info=message)
    discord_admin_bot(message)

    return {"message": "User strategy parameters updated successfully!"}
