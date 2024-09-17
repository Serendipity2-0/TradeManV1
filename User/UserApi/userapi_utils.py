import pandas as pd
import os, sys
from dotenv import load_dotenv
from babel.numbers import format_currency
from datetime import date, datetime
import csv
import numpy as np
import re
from collections import Counter
from typing import Dict, Any, List, Optional
import sqlite3
import traceback
import ast

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)


from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import (
    fetch_collection_data_firebase,
    update_fields_firebase,
)
from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_utils import (
    upload_new_client_data_to_firebase,
)
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
    fetch_active_strategies_all_users,
)
from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter import get_db_connection
from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_utils import get_db_table_names
from Executor.NSEStrategies.NSEStrategiesUtil import (
    update_qty_user_firebase,
    fetch_qty_amplifier,
    fetch_strategy_amplifier,
    get_order_mode,
    get_transaction_type,
)
from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import Instrument

from Executor.ExecutorUtils.ExeUtils import (
    EQUITY_STRATEGY_LIST,
    DERIVATIVES_STRATEGY_LIST,
)


logger = LoggerSetup()


ACTIVE_STRATEGIES = fetch_active_strategies_all_users()
ADMIN_DB = os.getenv("FIREBASE_ADMIN_COLLECTION")
CLIENTS_COLLECTION = os.getenv("FIREBASE_USER_COLLECTION")
PARAMS_UPDATE_LOG_CSV_PATH = os.getenv("PARAMS_UPDATE_LOG_CSV_PATH")
STRATEGIES_FB_COLLECTION = os.getenv("FIREBASE_STRATEGY_COLLECTION")
MARKET_INFO_FB_COLLECTION = os.getenv("MARKET_INFO_FB_COLLECTION")
USER_DB_EQUITY_PATH = os.getenv("USR_TRADELOG_EQUITY_DB_FOLDER")
USER_DB_DERIVATIVES_PATH = os.getenv("USR_TRADELOG_DERIVATIVES_DB_FOLDER")
USER_DB_DEBT_PATH = os.getenv("USR_TRADELOG_DEBT_DB_FOLDER")

MODE_TO_DB = {
    "Equity": ("equity", USER_DB_EQUITY_PATH),
    "Derivatives": ("derivatives", USER_DB_DERIVATIVES_PATH),
    "Debt": ("debt", USER_DB_DEBT_PATH),
}
EQUITY = "Equity"
DERIVATIVES = "Derivatives"
ERROR_LOG_PATH = os.getenv("ERROR_LOG_PATH")
ERROR_LOG_CSV_PATH = os.getenv("ERROR_LOG_CSV_PATH")


def all_users_data():
    """
    Fetches all user data from the Firebase database.

    Returns:
    dict: A dictionary containing all user data.
    """
    users_data = fetch_collection_data_firebase(CLIENTS_COLLECTION)
    return users_data


def get_next_trader_number():
    """
    Retrieves the next trader number from the admin database.

    Returns:
    int: The next trader number.
    """
    admin_data = fetch_collection_data_firebase(ADMIN_DB)
    return admin_data.get("NextTradeManId", 0)


def update_new_client_data_to_db(trader_number, user_dict):
    """
    Updates the user's data in the Firebase database.

    Args:
    trader_number (int): The new user's trader number.
    user_dict (dict): The user's data as a dictionary.
    """
    upload_new_client_data_to_firebase(trader_number, user_dict)


def update_next_trader_number():
    """
    Updates the next trader number inside the admin database.
    """
    admin_data = fetch_collection_data_firebase(ADMIN_DB)
    current_trader_number = admin_data.get("NextTradeManId", 0)
    next_number = int(current_trader_number[2:]) + 1
    next_trader_number = f"Tr{next_number}"
    next_trader_number_dict = {"NextTradeManId": next_trader_number}
    update_fields_firebase(ADMIN_DB, document=None, data=next_trader_number_dict)


def log_changes_via_webapp(updated_data, section_info=None):
    """
    The function `log_changes` logs updated data along with section information to a CSV file with date
    and time stamp.

    :param updated_data: The `updated_data` parameter is the data that has been updated and will be
    logged in the CSV file. It should be provided as an argument when calling the `log_changes` function
    :param section_info: Section_info is an optional parameter that can be passed to the log_changes
    function. It is used to provide additional information about the section being updated in the log
    entry. If section_info is provided, it will be included in the log entry under the "section_info"
    column in the CSV log file
    """
    filename = PARAMS_UPDATE_LOG_CSV_PATH
    headers = ["date", "updated_info", "section_info"]
    date_str = datetime.now().strftime("%d%b%y %I:%M%p")  # Format: 23Feb24 9:43AM

    with open(filename, mode="a", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=headers)

        # Write headers if file is being created for the first time
        if not os.path.isfile(filename):
            writer.writeheader()

        log_entry = {
            "date": date_str,
            "updated_info": str(updated_data),  # Corrected key to match header
            "section_info": section_info if section_info else "",
        }

        writer.writerow(log_entry)


def get_user_segments(tr_no: str) -> List[str]:
    """
    Fetches the segments for a user from the Firebase database.

    Args:
    tr_no (str): The user's ID.

    Returns:
    list: A list of segments for the user.
    """
    try:
        user_data = fetch_collection_data_firebase(CLIENTS_COLLECTION, tr_no)
        return list(user_data.get("Strategies", {}).keys())
    except Exception as e:
        logger.error(f"Error fetching user segments for {tr_no}: {e}")
        return []


def create_portfolio_stats(db_path: str) -> Optional[pd.DataFrame]:
    """
    Fetches portfolio stats for a user from a specific database file.

    Args:
    db_path (str): The path to the database file.

    Returns:
    Optional[pd.DataFrame]: The portfolio stats data as a pandas DataFrame
    with the columns 'exit_time', 'trade_id', 'net_pnl', and 'segment'.
    Returns None if there's an error or no data.
    """
    try:
        dtd_data_list = []  # Use a list to collect DataFrame fragments
        conn = get_db_connection(db_path)
        table_names = get_db_table_names(conn)

        segment = "equity" if "_equity.db" in db_path else "derivatives"

        user_strategy_table_names = [
            table for table in table_names if table in ACTIVE_STRATEGIES
        ]

        for table in user_strategy_table_names:
            data = pd.read_sql_query(f"SELECT * FROM {table}", conn)

            # Check if required columns exist in the table
            required_columns = ["exit_time", "trade_id", "net_pnl"]
            if all(item in data.columns for item in required_columns):
                df = data[required_columns].copy()
                df["segment"] = segment  # Add segment information
                dtd_data_list.append(df)
            else:
                missing_cols = set(required_columns) - set(data.columns)
                logger.error(f"Missing columns {missing_cols} in table {table}")

        if dtd_data_list:  # Only concatenate if there are data frames in the list
            dtd_data = pd.concat(dtd_data_list, ignore_index=True)
            return dtd_data
        else:
            logger.error(
                f"No data frames to concatenate in {db_path}. Check table column consistency."
            )
            return None
    except Exception as e:
        logger.error(f"Error fetching portfolio stats from {db_path}: {e}")
        return None


def get_monthly_returns_data(
    user_stats: pd.DataFrame, page: int, page_size: int
) -> dict:
    """
    Calculates the paginated monthly returns for a given DataFrame of portfolio stats data.

    Args:
    user_stats (pd.DataFrame): The DataFrame of portfolio stats data.
    page: The page number.
    page_size: The number of items per page.

    Returns:
    dict: A dictionary containing the paginated DataFrame of monthly returns and the total number of items.
    """
    try:
        user_stats["exit_time"] = pd.to_datetime(
            user_stats["exit_time"], errors="coerce"
        )
        user_stats = user_stats.dropna(subset=["exit_time"])

        user_stats["Year"] = user_stats["exit_time"].dt.year
        user_stats["Month"] = user_stats["exit_time"].dt.strftime("%B")
        user_stats["net_pnl"] = pd.to_numeric(user_stats["net_pnl"], errors="coerce")

        monthly_absolute_returns = (
            user_stats.groupby(["Year", "Month"])["net_pnl"]
            .sum()
            .reset_index()
            .rename(columns={"net_pnl": "Monthly Absolute Returns (Rs.)"})
        )

        monthly_absolute_returns[
            "Monthly Absolute Returns (Rs.)"
        ] = monthly_absolute_returns["Monthly Absolute Returns (Rs.)"].apply(
            lambda x: format_currency(x, "INR", locale="en_IN")
        )

        # Sort the DataFrame by Year and Month
        month_order = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]
        monthly_absolute_returns["Month"] = pd.Categorical(
            monthly_absolute_returns["Month"], categories=month_order, ordered=True
        )
        monthly_absolute_returns = monthly_absolute_returns.sort_values(
            ["Year", "Month"], ascending=[False, False]
        )

        # Calculate total number of items
        total_items = len(monthly_absolute_returns)

        # Apply pagination
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated_data = monthly_absolute_returns.iloc[start_index:end_index]

        return {
            "items": paginated_data.to_dict(orient="records"),
            "total_items": total_items,
        }

    except Exception as e:
        logger.error(f"Error calculating monthly returns: {e}")
        logger.error(traceback.format_exc())
        return {
            "items": [],
            "total_items": 0,
        }


def get_weekly_cumulative_returns_data(
    user_stats: pd.DataFrame, page: int, page_size: int
) -> dict:
    """
    Calculates the paginated weekly cumulative returns for a given DataFrame of portfolio stats data.

    Args:
    user_stats (pd.DataFrame): The DataFrame of portfolio stats data.
    page: The page number.
    page_size: The number of items per page.

    Returns:
    dict: A dictionary containing the paginated DataFrame of weekly cumulative returns and the total number of items.
    """
    try:
        user_stats["Date"] = pd.to_datetime(user_stats["exit_time"], errors="coerce")
        user_stats = user_stats.dropna(subset=["Date"])
        user_stats["Year"] = user_stats["Date"].dt.year
        user_stats["Month"] = user_stats["Date"].dt.month
        user_stats["Week_Ending_Date"] = (
            user_stats["Date"]
            + pd.to_timedelta((5 - user_stats["Date"].dt.weekday) % 7, unit="d")
        ).dt.normalize()
        user_stats["net_pnl"] = pd.to_numeric(user_stats["net_pnl"], errors="coerce")

        weekly_absolute_returns = (
            user_stats.groupby("Week_Ending_Date")
            .agg(Weekly_Absolute_Returns=pd.NamedAgg(column="net_pnl", aggfunc="sum"))
            .reset_index()
        )

        weekly_absolute_returns[
            "Cumulative Absolute Returns (Rs.)"
        ] = weekly_absolute_returns["Weekly_Absolute_Returns"].cumsum()
        weekly_absolute_returns = weekly_absolute_returns.sort_values(
            by="Week_Ending_Date"
        )

        weekly_absolute_returns["Week_Ending_Date"] = weekly_absolute_returns[
            "Week_Ending_Date"
        ].dt.strftime("%d%b%y")
        weekly_absolute_returns.rename(
            columns={"Weekly_Absolute_Returns": "Weekly Absolute Returns (Rs.)"},
            inplace=True,
        )

        # Format currency after all calculations
        weekly_absolute_returns[
            "Weekly Absolute Returns (Rs.)"
        ] = weekly_absolute_returns["Weekly Absolute Returns (Rs.)"].apply(
            lambda x: format_currency(x, "INR", locale="en_IN")
        )
        weekly_absolute_returns[
            "Cumulative Absolute Returns (Rs.)"
        ] = weekly_absolute_returns["Cumulative Absolute Returns (Rs.)"].apply(
            lambda x: format_currency(x, "INR", locale="en_IN")
        )

        # Calculate total number of items
        total_items = len(weekly_absolute_returns)

        # Apply pagination
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated_data = weekly_absolute_returns.iloc[start_index:end_index]
        return {
            "items": paginated_data.to_dict(orient="records"),
            "total_items": total_items,
        }

    except Exception as e:
        logger.error(f"Error calculating weekly returns: {e}")
        logger.error(traceback.format_exc())
        return {
            "items": [],
            "total_items": 0,
        }


def get_individual_strategy_data(
    tr_no: str, strategy_name: str, page: int, page_size: int
):
    """
    Retrieves the paginated data for a specific strategy for a given user.

    Args:
        tr_no (str): The user's ID.
        strategy_name (str): The name of the strategy.
        page (int): The page number.
        page_size (int): The number of items per page.

    Returns:
        dict: A dictionary containing the paginated DataFrame of strategy data and the total number of items.
    """
    try:
        if strategy_name in EQUITY_STRATEGY_LIST:
            db_name, folder_path = MODE_TO_DB["Equity"]
        elif strategy_name in DERIVATIVES_STRATEGY_LIST:
            db_name, folder_path = MODE_TO_DB["Derivatives"]
        else:
            db_name, folder_path = MODE_TO_DB["Equity"]
        db_path = os.path.join(folder_path, f"{tr_no}_{db_name}.db")

        conn = get_db_connection(db_path)
        strategies = ACTIVE_STRATEGIES + ["Holdings"]

        if strategy_name in strategies:
            # Calculate the offset
            offset = (page - 1) * page_size

            # Get the total count of items
            total_items = pd.read_sql_query(
                f"SELECT COUNT(*) as count FROM {strategy_name}", conn
            ).iloc[0]["count"]

            # Fetch paginated data
            data = pd.read_sql_query(
                f"SELECT * FROM {strategy_name} LIMIT {page_size} OFFSET {offset}", conn
            )

            if strategy_name == "Holdings":
                # Convert any potential NumPy types to Python native types
                data = data.astype(object).where(pd.notnull(data), None)
            else:
                data["exit_time"] = pd.to_datetime(data["exit_time"])
                # Convert any potential NumPy types to Python native types
                data = data.astype(object).where(pd.notnull(data), None)

            return {
                "items": data,
                "total_items": int(total_items),  # Ensure this is a Python int
            }
        else:
            logger.error(f"Strategy not found: {strategy_name}")
            return None
    except pd.io.sql.DatabaseError as e:
        if "no such table" in str(e):
            return {"items": pd.DataFrame(), "total_items": 0}
        else:
            logger.error(f"Error calculating individual strategy data: {e}")
            raise
    except Exception as e:
        logger.error(f"Error calculating individual strategy data: {e}")
        raise


def strategy_graph_data(tr_no: str, strategy_name: str):
    """
    Retrieves the strategy graph data for a specific user by their user ID and strategy name.

    Args:
        tr_no (str): The user's ID.
        strategy_name (str): The name of the strategy.

    Returns:
        dict: The strategy graph data for the specified user and strategy.
    """
    try:
        if strategy_name in EQUITY_STRATEGY_LIST:
            db_name, folder_path = MODE_TO_DB["Equity"]
        elif strategy_name in DERIVATIVES_STRATEGY_LIST:
            db_name, folder_path = MODE_TO_DB["Derivatives"]
        else:
            db_name, folder_path = MODE_TO_DB["Equity"]
        db_path = os.path.join(folder_path, f"{tr_no}_{db_name}.db")

        conn = get_db_connection(db_path)
        strategies = ACTIVE_STRATEGIES + ["Holdings"]

        if strategy_name in strategies:
            # Fetch only exit_time and pnl
            data = pd.read_sql_query(
                f"SELECT exit_time, pnl FROM {strategy_name}", conn
            )

            data["exit_time"] = pd.to_datetime(data["exit_time"])

            # Convert DataFrame to list of dictionaries
            combined_data = data.to_dict("records")

            # Convert any numpy types to Python native types
            for item in combined_data:
                item["exit_time"] = item["exit_time"].isoformat()
                if isinstance(item["pnl"], np.number):
                    item["pnl"] = float(item["pnl"])

            return {"items": combined_data}
        else:
            logger.error(f"Strategy not found: {strategy_name}")
            return None
    except pd.io.sql.DatabaseError as e:
        if "no such table" in str(e):
            return {"items": pd.DataFrame()}
        else:
            logger.error(f"Error retrieving strategy graph data: {e}")
            raise
    except Exception as e:
        logger.error(f"Error retrieving strategy graph data: {e}")
        raise


def fetch_strategy_signals(
    strategy_name: str, segment: str, page: int, page_size: int
) -> Dict[str, Any]:
    """
    Fetches the strategy signals for a specific strategy.

    Args:
        strategy_name (str): The name of the strategy.
        segment (SegmentType): The segment of the strategy ("EQUITY" or "DERIVATIVES").
        page (int): The page number for pagination.
        page_size (int): The number of items per page.

    Returns:
        Dict[str, Any]: A dictionary containing the list of signals and total item count.

    Raises:
        ValueError: If an invalid segment is provided.
        sqlite3.Error: If there's an issue with the database connection or query.
    """
    if segment == EQUITY:
        signal_db_path = os.getenv("EQUITY_SIGNAL_DB_PATH")
    elif segment == DERIVATIVES:
        signal_db_path = os.getenv("DERIVATIVES_SIGNAL_DB_PATH")
    else:
        raise ValueError(f"Invalid segment: {segment}")

    if not signal_db_path:
        raise ValueError(f"Database path not found for segment: {segment}")

    try:
        conn = get_db_connection(signal_db_path)
        with conn:
            total_items = pd.read_sql_query(
                f"SELECT COUNT(*) as count FROM {strategy_name}", conn
            ).iloc[0]["count"]

            offset = (page - 1) * page_size
            data = pd.read_sql_query(
                f"SELECT * FROM {strategy_name} LIMIT {page_size} OFFSET {offset}", conn
            )

        data = data.to_dict(orient="records")
        return {
            "items": data,
            "total_items": int(total_items),
        }
    except sqlite3.Error as e:
        raise sqlite3.Error(f"Database error: {e}")
    finally:
        if conn:
            conn.close()


def signal_graph_data(strategy_name: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Retrieves the strategy signals graph data for a specific strategy.

    Args:
        strategy_name (str): The name of the strategy.

    Returns:
        Dict[str, List[Dict[str, Any]]]: The strategy signals graph data for the specified strategy.
    """
    try:
        if strategy_name in EQUITY_STRATEGY_LIST:
            db_path = os.getenv("EQUITY_SIGNAL_DB_PATH")
        elif strategy_name in DERIVATIVES_STRATEGY_LIST:
            db_path = os.getenv("DERIVATIVES_SIGNAL_DB_PATH")
        else:
            raise ValueError(f"Invalid strategy name: {strategy_name}")

        if not db_path:
            raise ValueError(f"Database path not found for strategy: {strategy_name}")

        conn = get_db_connection(db_path)
        try:
            data = pd.read_sql_query(
                f"SELECT exit_time, trade_points FROM {strategy_name}", conn
            )

            data["exit_time"] = pd.to_datetime(data["exit_time"])

            # Convert DataFrame to list of dictionaries
            combined_data = data.to_dict("records")

            # Convert any numpy types to Python native types
            for item in combined_data:
                item["exit_time"] = item["exit_time"].isoformat()
                if isinstance(item["trade_points"], np.number):
                    item["trade_points"] = float(item["trade_points"])

            return {"items": combined_data}

        except pd.io.sql.DatabaseError as e:
            if "no such table" in str(e):
                logger.warning(f"No data found for strategy: {strategy_name}")
                return {"items": []}
            else:
                logger.error(
                    f"Database error while retrieving strategy graph data: {e}"
                )
                raise
        finally:
            conn.close()

    except Exception as e:
        logger.error(f"Error retrieving strategy graph data: {e}")
        raise


def calculate_strategy_statistics(df: pd.DataFrame, is_signals: bool):
    """
    Calculate strategy statistics from a DataFrame.

    Args:
    df: DataFrame containing strategy data.
    is_signals: Boolean indicating if the strategy is a signals strategy.

    Returns:
    Dict: Calculated strategy statistics.
    """
    if df.empty:
        return None
    column_for_calc = "trade_points" if is_signals else "net_pnl"

    # Basic calculations
    positive_trades = df[df[column_for_calc] > 0]
    negative_trades = df[df[column_for_calc] < 0]

    net_trade_points = df[column_for_calc].sum()
    num_trades = len(df)
    num_wins = len(positive_trades)
    num_losses = len(negative_trades)

    # Consecutive wins and losses
    df["win"] = df[column_for_calc] > 0
    df["group"] = (df["win"] != df["win"].shift()).cumsum()
    consecutive_wins = (
        df[df["win"]].groupby("group").size().max() if num_wins > 0 else 0
    )
    consecutive_losses = (
        df[~df["win"]].groupby("group").size().max() if num_losses > 0 else 0
    )

    # Advanced calculations
    avg_profit_loss = df[column_for_calc].mean()
    df["profit_percent"] = df[column_for_calc] / df["entry_price"] * 100
    avg_profit_loss_percent = df["profit_percent"].mean()
    max_trade_drawdown = df[column_for_calc].min()
    cumulative_net_pnl = df[column_for_calc].cumsum()
    max_system_drawdown = cumulative_net_pnl.min()

    recovery_factor = (
        net_trade_points / -max_system_drawdown if max_system_drawdown < 0 else 0
    )

    annual_return = 0.1  # Assume 10% annual return or replace with actual calculation
    max_dd_percent = max_system_drawdown / df["entry_price"].iloc[0] * 100
    car_maxdd = annual_return / -max_dd_percent if max_dd_percent < 0 else 0

    std_error = df[column_for_calc].std()
    risk_reward_ratio = avg_profit_loss / std_error if std_error != 0 else 0

    drawdown = cumulative_net_pnl.cummin() - cumulative_net_pnl
    ulcer_index = np.sqrt(np.mean(drawdown**2))

    statistics = {
        "Net Trade Points": net_trade_points,
        "No of Trades": num_trades,
        "No of Wins": num_wins,
        "No of Losses": num_losses,
        "No of Cons Win": consecutive_wins,
        "No of Cons Loss": consecutive_losses,
        "Avg. Profit/Loss (Expectancy Rs)": avg_profit_loss,
        "Avg. Profit/Loss % (Expectancy %)": avg_profit_loss_percent,
        "Max. Trade Drawdown": max_trade_drawdown,
        "Max. System Drawdown": max_system_drawdown,
        "Recovery Factor": recovery_factor,
        "CAR/MaxDD": car_maxdd,
        "Standard Error": std_error,
        "Risk-Reward Ratio": risk_reward_ratio,
        "Ulcer Index": ulcer_index,
    }

    # Convert numpy types to Python native types
    formatted_stats = {}
    for key, value in statistics.items():
        if isinstance(value, np.integer):
            formatted_stats[key] = int(value)
        elif isinstance(value, np.floating):
            formatted_stats[key] = float(value)
        elif isinstance(value, np.ndarray):
            formatted_stats[key] = value.tolist()
        else:
            formatted_stats[key] = value

    # Format floats to 2 decimal places
    for key, value in formatted_stats.items():
        if isinstance(value, float):
            formatted_stats[key] = f"{value:.2f}"

    return formatted_stats


def get_base_capital(tr_no: str):
    """
    Retrieves the base capital for a specific user by their user ID.

    Args:
    user_id: The unique identifier of the user.

    Returns:
    float: The base capital.
    """
    try:
        # Assume fetching user profile from a database
        user = fetch_collection_data_firebase(CLIENTS_COLLECTION, document=tr_no)
        return user["Accounts"]["CurrentBaseCapital"]

    except Exception as e:
        logger.error(f"Error calculating base capital: {e}")
        return 0.0


def get_broker_bank_transactions_data(
    tr_no: str, mode: str, from_date: date = None, to_date: date = None
):
    """
    Retrieves the broker and bank transactions data for a specific user by their user ID, filtered by a date range.

    Args:
        tr_no: The unique identifier of the user.
        from_date: Start date for filtering transactions(YYYY-MM-DD). Defaults to None.
        to_date: End date for filtering transactions(YYYY-MM-DD). Defaults to None.

    Returns:
        DataFrame: The broker and bank transactions data.
    """
    # TODO : Change the DB paths when the DBs are ready
    MODE_TO_DB = {
        "Equity": ("equity", USER_DB_EQUITY_PATH),
        "Derivatives": ("derivatives", USER_DB_DERIVATIVES_PATH),
        "Debt": ("debt", USER_DB_DEBT_PATH),
    }

    try:
        db_name, folder_path = MODE_TO_DB[mode]
        # db_path = os.path.join(folder_path, f"{tr_no}_{db_name}.db") # TODO: Uncomment this line when ready to update
        db_path = os.path.join(folder_path, f"{tr_no}.db")
    except KeyError:
        raise ValueError(f"Invalid mode: {mode}")

    conn = get_db_connection(db_path)
    starting_capital = get_base_capital(tr_no)

    # Build the query dynamically based on whether date filters are provided
    where_clauses = []
    if from_date:
        where_clauses.append(f"posting_date >= '{from_date}'")
    if to_date:
        where_clauses.append(f"posting_date <= '{to_date}'")
    where_stmt = " AND ".join(where_clauses) if where_clauses else "1=1"

    # Query modifications to include the date filters
    deposits = pd.read_sql_query(
        f"SELECT posting_date AS date, particulars, debit, credit FROM Deposits WHERE {where_stmt}",
        conn,
    )
    withdrawals = pd.read_sql_query(
        f"SELECT posting_date AS date, particulars, debit, credit FROM Withdrawals WHERE {where_stmt}",
        conn,
    )
    charges = pd.read_sql_query(
        f"SELECT posting_date AS date, particulars, debit, credit FROM Charges WHERE {where_stmt}",
        conn,
    )

    # Combine the data from all tables
    combined_data = pd.concat([deposits, withdrawals, charges], ignore_index=True)
    combined_data["date"] = pd.to_datetime(combined_data["date"])
    sorted_data = combined_data.sort_values(by="date", ascending=True).reset_index(
        drop=True
    )

    # Convert 'date' to a string in the desired format
    sorted_data["date"] = sorted_data["date"].dt.strftime("%Y-%m-%d")

    # Initialize running balance column
    sorted_data["running balance"] = 0.0  # Initialize as float

    # Set the first row's running balance
    sorted_data.at[0, "running balance"] = (
        starting_capital + sorted_data.at[0, "credit"] - sorted_data.at[0, "debit"]
    )

    # Compute running balance for the rest of the DataFrame
    for i in range(1, len(sorted_data)):
        sorted_data.at[i, "running balance"] = (
            sorted_data.at[i - 1, "running balance"]
            + sorted_data.at[i, "credit"]
            - sorted_data.at[i, "debit"]
        )

    # Add empty columns for 'tags' and 'comments'
    sorted_data["tags"] = None  # Assuming you want to fill this later or keep it empty
    sorted_data["comments"] = None

    # Close the database connection
    conn.close()

    return sorted_data


def fetch_strategies_for_user(tr_no: str):
    """
    Retrieves the strategies associated with a specific user.

    Args:
        tr_no (str): The user's ID.

    Returns:
        dict: A dictionary containing lists of strategy names for 'Equity' and 'Derivatives'.

    Raises:
        HTTPException: If there's an error fetching from the database.
    """

    user = fetch_collection_data_firebase(CLIENTS_COLLECTION, document=tr_no)
    strategies = []

    if "Strategies" in user:
        if "Equity" in user["Strategies"]:
            strategies.extend([strategy for strategy in user["Strategies"]["Equity"]])
        if "Derivatives" in user["Strategies"]:
            strategies.extend(
                [strategy for strategy in user["Strategies"]["Derivatives"]]
            )

    return strategies


def get_users_db_holdings(tr_no: str, mode: str):
    """
    Retrieves the users holdings based on mode.

    Args:
        tr_no (str): The user's ID.
        mode (str): The mode of holdings to retrieve.

    Returns:
        list: A list of equity holdings for the user.

    Raises:
        HTTPException: If there's an error fetching from the database.
    """
    try:
        db_name, folder_path = MODE_TO_DB[mode]
        db_path = os.path.join(folder_path, f"{tr_no}_{db_name}.db")
    except KeyError:
        raise ValueError(f"Invalid mode: {mode}")
    conn = get_db_connection(db_path)
    table_names = get_db_table_names(conn)

    for table in table_names:
        if table == "Holdings":
            data = pd.read_sql_query(f"SELECT * FROM {table}", conn)
            data = data.to_dict("records")
            break
    conn.close()
    return data


def parse_value(value):
    """Parse string values to appropriate types."""
    if isinstance(value, str):
        if value.lower() == "true":
            return True
        elif value.lower() == "false":
            return False
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return value
    return value


def fetch_segment_from_strategy(strategy_name: str):
    """
    Fetches the segment from the strategy name.

    Args:
        strategy_name (str): The name of the strategy.

    Returns:
        str: The segment of the strategy.
    """
    if strategy_name in EQUITY_STRATEGY_LIST:
        return EQUITY
    elif strategy_name in DERIVATIVES_STRATEGY_LIST:
        return DERIVATIVES
    else:
        return None


def fetch_list_of_nse_instruments():
    """
    Fetch the list of NSE instruments.
    """
    instruments = Instrument().fetch_complete_instruments_by_segment("NSE")
    return instruments


def fetch_tradingsymbol_by_name(name: str):
    """
    Fetch the trading symbol by name.
    """
    trading_symbol = Instrument().fetch_trading_symbol_by_name(name)
    return trading_symbol


def update_strategy_qty(
    strategy_name: str,
    user: str,
    qty_calculation_mode: str,
    qty: int,
    ltp: float,
    strategy_type: str,
    num_stocks: int,
    setup_name: str = None,
):
    """
    Updates the quantity of the strategy.
    """
    if num_stocks is None:
        num_stocks = 1

    qty_amplifier = fetch_qty_amplifier(strategy_name, strategy_type)
    strategy_amplifier = fetch_strategy_amplifier(strategy_name)
    segment = fetch_segment_from_strategy(strategy_name)
    if qty_calculation_mode == "Auto":
        update_qty_user_firebase(
            strategy_name=strategy_name,
            avg_sl_points_or_ltp=ltp,
            qty_amplifier=qty_amplifier,
            strategy_amplifier=strategy_amplifier,
            asset_segment=segment,
            asset_term=setup_name,
            num_stocks=num_stocks,
        )
    elif qty_calculation_mode == "Manual":
        if segment == EQUITY:
            path = f"Strategies/{segment}/{strategy_name}/{setup_name}"
        elif segment == DERIVATIVES:
            path = f"Strategies/{segment}/{strategy_name}"
        update_fields_firebase(
            CLIENTS_COLLECTION,
            user,
            {"Qty": qty},
            path,
        )


def prepare_order_details(
    strategy_name: str,
    symbol: str,
    exchange_token: str,
    order_type: str,
    product_type: str,
    trade_id: str,
    ltp: float,
    setup_name: str = None,
):
    """
    Prepares the order details for the strategy.

    Args:
        strategy_name (str): The name of the strategy.
        symbol (str): The symbol of the stock.
        exchange_token (str): The exchange token of the stock.
        order_type (str): The order type of the stock.
        product_type (str): The product type of the stock.
        trade_id (str): The trade_id of the stock.
        setup_name (str): The setup name of the stock.
        ltp (float): The ltp of the stock.

    Returns:
        list: The order details for the strategy.
    """
    order_mode = get_order_mode(trade_id)
    transaction_type = get_transaction_type(trade_id)
    if setup_name:
        setup_name = setup_name.upper()
    else:
        setup_name = None
    order_details = [
        {
            "strategy": strategy_name,
            "signal": "Long",
            "base_symbol": symbol,
            "exchange_token": exchange_token,
            "transaction_type": transaction_type,
            "order_type": order_type,
            "product_type": product_type,
            "order_mode": order_mode,
            "trade_id": trade_id,
            "limit_prc": ltp,
            "trade_mode": os.getenv("TRADE_MODE"),
            "setup": setup_name,
        }
    ]
    return order_details


def calculate_aum():
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
            aum["Derivatives"] += accounts.get("Derivatives", {}).get(
                "Derivatives_FreeCash", 0
            )
            aum["Portfolio"] += accounts.get("Portfolio", {}).get(
                "Portfolio_FreeCash", 0
            )

    return aum


def get_total_base_capital():
    """
    Calculates the total CurrentBaseCapital for all active users.

    Returns:
        float: The total base capital.
    """
    users_data = fetch_collection_data_firebase(CLIENTS_COLLECTION)
    total_base_capital = 0

    for user_id, user_data in users_data.items():
        if user_data.get("Active", False):
            total_base_capital += user_data.get("Accounts", {}).get(
                "CurrentBaseCapital", 0
            )

    return total_base_capital


def calculate_active_users_data():
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


def get_firebase_holdings(tr_no: str, strategy_name: str):
    """
    Retrieves the holdings from the firebase for a specific user.

    Args:
        tr_no (str): The trader number of the user.
        strategy_name (str): The name of the strategy.

    Returns:
        list: A list of orders for the strategy.
    """
    user_details = fetch_collection_data_firebase(CLIENTS_COLLECTION, document=tr_no)

    if strategy_name in EQUITY_STRATEGY_LIST:
        equity_strategy = user_details["Strategies"]["Equity"]
        if strategy_name in EQUITY_STRATEGY_LIST:
            all_orders = []
            for setup in equity_strategy[strategy_name]:
                if setup != "AllocationPercent":
                    setup_data = equity_strategy[strategy_name][setup]
                    if isinstance(setup_data, dict) and "TradeState" in setup_data:
                        all_orders.extend(setup_data["TradeState"].get("orders", []))
            return all_orders
        else:
            return (
                equity_strategy[strategy_name].get("TradeState", {}).get("orders", [])
            )

    if strategy_name in DERIVATIVES_STRATEGY_LIST:
        return user_details["Strategies"]["Derivatives"][strategy_name].get(
            "orders", []
        )

    return []


# Adjust the function to extract the timestamp as well
def extract_error_details_with_timestamp(line):
    """
    Extracts timestamp, module, and error message from a log line.

    :param line: A log line in the format "YYYY-MM-DD HH:MM:SS.mmm | ERROR    | <module_path>:<something> - <error_message>"
    :return: Tuple (timestamp, module, error_message) if the pattern matches; (None, None, None) otherwise.
    """
    pattern = r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) \| ERROR    \| (.+?):(.+?) - (.+)$"
    match = re.search(pattern, line)
    if match:
        timestamp = match.group(1)
        full_module_path = match.group(2).strip()
        module = full_module_path.split(".")[-1]  # Get the last part of the module path
        error_message = match.group(4).strip()
        return timestamp, module, error_message
    else:
        logger.debug(f"No pattern match for line: {line}")
    return None, None, None


def read_n_process_err_log():
    """
    The function reads and processes an error log file, extracts error details, counts occurrences of
    each error message, aggregates unique errors with their latest timestamp, module, and count,
    converts the data to a DataFrame, and appends the processed data to a CSV file.
    :return: The function `read_n_process_err_log` returns a DataFrame containing unique error messages
    along with their latest timestamp, module, occurrence count, and sorted by timestamp in descending
    order. This DataFrame is also logged using the `logger.debug` function and appended to an existing
    CSV file specified by `ERROR_LOG_CSV_PATH`.
    """
    timestamps, modules, errors = [], [], []
    # Resetting the lists to ensure clean data collection
    timestamps = []
    modules = []
    errors = []

    with open(ERROR_LOG_PATH, "r") as file:
        for line in file:
            if "| ERROR    |" in line:
                timestamp, module, error_message = extract_error_details_with_timestamp(
                    line
                )
                if module and error_message:
                    timestamps.append(timestamp)
                    modules.append(module)
                    errors.append(error_message)

    if not errors:
        logger.debug("No errors found in the log.")
        return pd.DataFrame()  # Return an empty DataFrame if there are no errors

    error_counts = Counter(errors)
    unique_errors = {}
    for timestamp, module, error in zip(timestamps, modules, errors):
        if error in unique_errors:
            unique_errors[error]["Timestamp"] = timestamp
        else:
            unique_errors[error] = {
                "Timestamp": timestamp,
                "Module": module,
                "Count": error_counts[error],
            }

    error_df = pd.DataFrame(
        [
            {
                "Timestamp": details["Timestamp"],
                "Module": details["Module"],
                "Error": error,
                "Count": details["Count"],
            }
            for error, details in unique_errors.items()
        ]
    )

    error_df_sorted = error_df.sort_values(by="Timestamp", ascending=False).reset_index(
        drop=True
    )

    with open(os.path.join(DIR_PATH, ERROR_LOG_CSV_PATH), "a") as f:
        error_df_sorted.to_csv(f, header=f.tell() == 0, index=False)

    return error_df_sorted
