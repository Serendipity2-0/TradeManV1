import os
import sqlite3
import sys
import pandas as pd
from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()


def get_db_connection(db_path):
    """
    Create a database connection to the SQLite database specified by db_path.

    Args:
        db_path (str): The file path to the SQLite database.

    Returns:
        sqlite3.Connection: The database connection object.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
    except sqlite3.Error as e:
        logger.error(f"An error occurred while connecting to the database: {e}")
    return conn


def format_decimal_values(df, decimal_columns):
    """
    Format specified columns of a DataFrame to show two decimal places.

    Args:
        df (pd.DataFrame): The DataFrame to format.
        decimal_columns (list): List of column names to format as decimals.

    Returns:
        pd.DataFrame: The formatted DataFrame.
    """
    for col in decimal_columns:
        if col in df.columns:
            # Convert to float and format as a string with two decimal places
            df[col] = df[col].apply(lambda x: "{:.2f}".format(float(x)))
    return df


def append_df_to_sqlite(conn, df, table_name, decimal_columns):
    """
    Append the data from a DataFrame to a specified SQLite table.

    Args:
        conn (sqlite3.Connection): The database connection object.
        df (pd.DataFrame): The DataFrame to append.
        table_name (str): The name of the table to append to.
        decimal_columns (list): List of column names to format as decimals.

    Returns:
        None
    """
    if not df.empty:
        formatted_df = format_decimal_values(df, decimal_columns)
        # Cast decimal columns to text
        for col in decimal_columns:
            if col in formatted_df.columns:
                formatted_df[col] = formatted_df[col].astype(str)
        try:
            formatted_df.to_sql(table_name, conn, if_exists="append", index=False)
        except Exception as e:
            logger.error(
                f"An error occurred while appending to the table {table_name}: {e}"
            )


def dump_df_to_sqlite(conn, df, table_name, decimal_columns):
    """
    Dump the data from a DataFrame to a specified SQLite table, replacing existing data.

    Args:
        conn (sqlite3.Connection): The database connection object.
        df (pd.DataFrame): The DataFrame to dump.
        table_name (str): The name of the table to dump to.
        decimal_columns (list): List of column names to format as decimals.

    Returns:
        None
    """
    if not df.empty:
        formatted_df = format_decimal_values(df, decimal_columns)
        # Cast decimal columns to text
        for col in decimal_columns:
            if col in formatted_df.columns:
                formatted_df[col] = formatted_df[col].astype(str)
        try:
            formatted_df.to_sql(table_name, conn, if_exists="replace", index=False)
        except Exception as e:
            logger.error(
                f"An error occurred while dumping to the table {table_name}: {e}"
            )


def read_strategy_table(conn, strategy_name):
    """
    Read the strategy table from the database and return a DataFrame.

    Args:
        conn (sqlite3.Connection): The database connection object.
        strategy_name (str): The name of the strategy table.

    Returns:
        pd.DataFrame: The DataFrame containing the strategy table data.
    """
    try:
        query = f"SELECT * FROM {strategy_name}"
        df = pd.read_sql(query, conn)
        return df
    except pd.io.sql.DatabaseError:
        logger.warning(f"Table '{strategy_name}' does not exist in the database.")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"An error occurred while reading the table {strategy_name}: {e}")
        return None


def create_holding_strategy_table(conn, table_name):
    """
    Create a new table in the database.

    Parameters:
    conn (sqlite3.Connection): SQLite connection object
    table_name (str): The name of the table to create
    """
    try:
        query = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            trade_id TEXT PRIMARY KEY,
            trading_symbol TEXT,
            signal TEXT,
            qty INTEGER,
            margin_utilized REAL,
            entry_time TEXT,
            entry_prc REAL,
            tax REAL,
            setup TEXT
        )
        """
        cursor = conn.cursor()
        cursor.execute(query)
        conn.commit()
    except Exception as e:
        logger.error(f"An error occurred while creating the table {table_name}: {e}")


def fetch_qty_for_holdings_sqldb(Tr_No, trade_id, strategy_type):
    """
    Fetch the quantity from the Holdings table that matches the first part of the trade_id.

    Args:
        Tr_No (str): The trader number.
        trade_id (str): The trade ID.

    Returns:
        int: The quantity from the Holdings table.
    """
    # check the strategy type and accordingly change the db path
    db_folder = os.getenv(f"USR_TRADELOG_{strategy_type.upper()}_DB_FOLDER")
    db_path = os.path.join(db_folder, f"{Tr_No}_{strategy_type.lower()}.db")
    conn = get_db_connection(db_path)
    trade_id = trade_id.split("_")[0]
    query = f"SELECT * FROM Holdings WHERE trade_id LIKE '{trade_id}%'"
    df = pd.read_sql(query, conn)
    if not df.empty:
        qty = df["qty"].values[0]
    else:
        qty = 0
    return int(qty)
