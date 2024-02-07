import os
import sqlite3
import sys

import pandas as pd
from dotenv import load_dotenv
from loguru import logger

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

ERROR_LOG_PATH = os.getenv("ERROR_LOG_PATH")
logger.add(
    ERROR_LOG_PATH,
    level="TRACE",
    rotation="00:00",
    enqueue=True,
    backtrace=True,
    diagnose=True,
)

def get_db_connection(db_path):
    """Create a database connection to the SQLite database specified by db_path."""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
    except sqlite3.Error as e:
        (e)
    return conn

def format_decimal_values(df, decimal_columns):
    """Format specified columns of a DataFrame to show two decimal places."""
    for col in decimal_columns:
        if col in df.columns:
            # Convert to float and format as a string with two decimal places
            df[col] = df[col].apply(lambda x: "{:.2f}".format(float(x)))

    return df

# append the data from df to sqlite db
def append_df_to_sqlite(conn, df, table_name, decimal_columns):
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
            
# dump_df_to_sqlite
def dump_df_to_sqlite(conn, df, table_name, decimal_columns):
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
    """Read the strategy table from the database and return a DataFrame."""
    query = f"SELECT * FROM {strategy_name}"
    df = pd.read_sql(query, conn)
    return df

def fetch_qty_for_holdings_sqldb(Tr_No, trade_id):
    # i want just the trade_id.split[0] to match the trade_id.split[0] in the db
    trade_id = trade_id.split("_")[0]
    db_path = os.path.join(os.getenv("DB_DIR"), f"{Tr_No}.db")
    conn = get_db_connection(db_path) 
    """Fetch the quantity from the Holdings table from database which match the first part of the trade_id."""
    query = f"SELECT * FROM Holdings WHERE trade_id LIKE '{trade_id}%'"
    df = pd.read_sql(query, conn)
    if not df.empty:
        qty = df["qty"].values[0]
    else:
        qty = 0
    return qty
