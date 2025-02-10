"""
Transaction-related utility functions for managing user transactions.
"""

import os
import pandas as pd
from typing import Dict, List, Optional
from dotenv import load_dotenv
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter import get_db_connection
from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_utils import get_db_table_names
from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import (
    fetch_collection_data_firebase,
)
from Executor.ExecutorUtils.ExeUtils import (
    EQUITY_STRATEGY_LIST,
    DERIVATIVES_STRATEGY_LIST,
    DEBT_STRATEGY_LIST,
)

DIR_PATH = os.getcwd()
ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

logger = LoggerSetup()

USER_DB_EQUITY_PATH = os.getenv("USR_TRADELOG_EQUITY_DB_FOLDER")
USER_DB_DERIVATIVES_PATH = os.getenv("USR_TRADELOG_DERIVATIVES_DB_FOLDER")
USER_DB_DEBT_PATH = os.getenv("USR_TRADELOG_DEBT_DB_FOLDER")

MODE_TO_DB = {
    "Equity": ("equity", USER_DB_EQUITY_PATH),
    "Derivatives": ("derivatives", USER_DB_DERIVATIVES_PATH),
    "Debt": ("debt", USER_DB_DEBT_PATH),
}


def get_individual_strategy_data(
    tr_no: str, strategy_name: str, page: int, page_size: int
) -> Optional[Dict]:
    """
    Retrieves the paginated data for a specific strategy for a given user.

    Args:
        tr_no (str): The user's ID.
        strategy_name (str): The name of the strategy.
        page (int): The page number.
        page_size (int): The number of items per page.

    Returns:
        dict: A dictionary containing the paginated DataFrame of strategy data and total items.
    """
    try:
        if strategy_name in EQUITY_STRATEGY_LIST:
            db_name, folder_path = MODE_TO_DB["Equity"]
        elif strategy_name in DERIVATIVES_STRATEGY_LIST:
            db_name, folder_path = MODE_TO_DB["Derivatives"]
        elif strategy_name in DEBT_STRATEGY_LIST:
            db_name, folder_path = MODE_TO_DB["Debt"]
        else:
            db_name, folder_path = MODE_TO_DB["Equity"]

        db_path = os.path.join(folder_path, f"{tr_no}_{db_name}.db")
        logger.info(f"DB Path: {db_path}")

        conn = get_db_connection(db_path)
        strategies = ACTIVE_STRATEGIES + ["Holdings"]
        logger.info(f"Strategies: {strategies}")

        if strategy_name in strategies:
            offset = (page - 1) * page_size
            total_items = pd.read_sql_query(
                f"SELECT COUNT(*) as count FROM {strategy_name}", conn
            ).iloc[0]["count"]

            data = pd.read_sql_query(
                f"SELECT * FROM {strategy_name} LIMIT {page_size} OFFSET {offset}", conn
            )

            if strategy_name == "Holdings" or strategy_name in DEBT_STRATEGY_LIST:
                data = data.astype(object).where(pd.notnull(data), None)
            else:
                data["exit_time"] = pd.to_datetime(data["exit_time"])
                data = data.astype(object).where(pd.notnull(data), None)

            return {
                "items": data,
                "total_items": int(total_items),
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


def strategy_graph_data(tr_no: str, strategy_name: str) -> Dict:
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
        elif strategy_name in DEBT_STRATEGY_LIST:
            db_name, folder_path = MODE_TO_DB["Debt"]
        else:
            db_name, folder_path = MODE_TO_DB["Equity"]

        db_path = os.path.join(folder_path, f"{tr_no}_{db_name}.db")
        conn = get_db_connection(db_path)
        strategies = ACTIVE_STRATEGIES + ["Holdings"]

        if strategy_name in strategies:
            if strategy_name not in DEBT_STRATEGY_LIST:
                data = pd.read_sql_query(
                    f"SELECT exit_time, pnl FROM {strategy_name}", conn
                )
                data["exit_time"] = pd.to_datetime(data["exit_time"])
                combined_data = data.to_dict("records")

                for item in combined_data:
                    item["exit_time"] = item["exit_time"].isoformat()
                    if isinstance(item["pnl"], pd.np.number):
                        item["pnl"] = float(item["pnl"])

                return {"items": combined_data}
            else:
                data = pd.read_sql_query(f"SELECT date FROM {strategy_name}", conn)
                return {"items": data}
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


def get_broker_bank_transactions_data(
    tr_no: str, mode: str, from_date: str = None, to_date: str = None
) -> pd.DataFrame:
    """
    Retrieves the broker and bank transactions data for a specific user by their user ID,
    filtered by a date range.

    Args:
        tr_no: The unique identifier of the user.
        mode: The mode of transactions (Equity, Derivatives, Debt).
        from_date: Start date for filtering transactions(YYYY-MM-DD).
        to_date: End date for filtering transactions(YYYY-MM-DD).

    Returns:
        DataFrame: The broker and bank transactions data.
    """
    try:
        db_name, folder_path = MODE_TO_DB[mode]
        db_path = os.path.join(folder_path, f"{tr_no}.db")
    except KeyError:
        raise ValueError(f"Invalid mode: {mode}")

    conn = get_db_connection(db_path)
    starting_capital = get_base_capital(tr_no)

    where_clauses = []
    if from_date:
        where_clauses.append(f"posting_date >= '{from_date}'")
    if to_date:
        where_clauses.append(f"posting_date <= '{to_date}'")
    where_stmt = " AND ".join(where_clauses) if where_clauses else "1=1"

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

    combined_data = pd.concat([deposits, withdrawals, charges], ignore_index=True)
    combined_data["date"] = pd.to_datetime(combined_data["date"])
    sorted_data = combined_data.sort_values(by="date", ascending=True).reset_index(
        drop=True
    )
    sorted_data["date"] = sorted_data["date"].dt.strftime("%Y-%m-%d")
    sorted_data["running balance"] = 0.0

    sorted_data.at[0, "running balance"] = (
        starting_capital + sorted_data.at[0, "credit"] - sorted_data.at[0, "debit"]
    )

    for i in range(1, len(sorted_data)):
        sorted_data.at[i, "running balance"] = (
            sorted_data.at[i - 1, "running balance"]
            + sorted_data.at[i, "credit"]
            - sorted_data.at[i, "debit"]
        )

    sorted_data["tags"] = None
    sorted_data["comments"] = None

    conn.close()
    return sorted_data


def get_base_capital(tr_no: str) -> float:
    """
    Retrieves the base capital for a specific user by their user ID.

    Args:
        tr_no: The unique identifier of the user.

    Returns:
        float: The base capital.
    """
    try:
        user = fetch_collection_data_firebase(
            os.getenv("FIREBASE_USER_COLLECTION"), document=tr_no
        )
        return user["Accounts"]["CurrentBaseCapital"]
    except Exception as e:
        logger.error(f"Error calculating base capital: {e}")
        return 0.0


def get_users_db_holdings(tr_no: str, mode: str) -> List[Dict]:
    """
    Retrieves the users holdings based on mode.

    Args:
        tr_no (str): The user's ID.
        mode (str): The mode of holdings to retrieve.

    Returns:
        list: A list of holdings for the user.
    """
    try:
        db_name, folder_path = MODE_TO_DB[mode]
        db_path = os.path.join(folder_path, f"{tr_no}_{db_name}.db")
    except KeyError:
        raise ValueError(f"Invalid mode: {mode}")

    conn = get_db_connection(db_path)
    table_names = get_db_table_names(conn)

    data = []
    for table in table_names:
        if table == "Holdings":
            data = pd.read_sql_query(f"SELECT * FROM {table}", conn)
            data = data.to_dict("records")
            break

    conn.close()
    return data


def serialize_transactions(transactions: List) -> List[Dict]:
    """
    Serializes the transactions to a list of dictionaries.

    Args:
        transactions: The transactions to serialize.

    Returns:
        list[dict]: The serialized transactions.
    """
    return [
        {
            "transaction_id": tx.transaction_id,
            "date": tx.date,
            "description": tx.description,
            "amount": tx.amount,
            "payment_mode": tx.payment_mode,
            "acc_id": tx.acc_id,
            "department": tx.department,
            "comments": tx.comments,
            "category": tx.category,
            "deducted_received_through": tx.deducted_received_through,
            "zoho_match": tx.zoho_match,
            "expected_payment_date": tx.expected_payment_date,
            "current_balance": tx.current_balance,
        }
        for tx in transactions
    ]
