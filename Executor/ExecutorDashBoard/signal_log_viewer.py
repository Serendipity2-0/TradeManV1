import os, sys
import streamlit as st
from dotenv import load_dotenv
from datetime import datetime
import pandas as pd
import sqlite3

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

signal_db_path = os.getenv("SIGNAL_DB_PATH")

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()


# Function to get a list of all tables in the database
def get_table_names(db_path):
    """
    The function `get_table_names` retrieves the names of all tables in a SQLite database specified by
    the `db_path` parameter.
    
    :param db_path: The `db_path` parameter in the `get_table_names` function is a string that
    represents the path to the SQLite database file from which you want to retrieve the table names. You
    need to provide the full path to the SQLite database file in order for the function to connect to
    the database and fetch
    :return: The function `get_table_names` returns a list of table names present in the SQLite database
    located at the specified `db_path`.
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [table[0] for table in cur.fetchall()]
    conn.close()
    return tables

# Function to get dataframe from selected table
def get_data(table_name, db_path):
    """
    The function `get_data` retrieves all data from a specified table in a SQLite database and returns
    it as a pandas DataFrame.
    
    :param table_name: The `table_name` parameter in the `get_data` function refers to the name of the
    table in the database from which you want to retrieve data. It is a string that specifies the table
    name in the database schema
    :param db_path: The `db_path` parameter in the `get_data` function refers to the path where the
    SQLite database file is located. This path should include the name of the SQLite database file that
    you want to connect to in order to retrieve data from a specific table
    :return: The function `get_data` returns a pandas DataFrame containing all the data from the
    specified table in the database located at the given `db_path`.
    """
    conn = sqlite3.connect(db_path)
    query = f"SELECT * FROM {table_name}"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def signal_log_viewer():
    """
    The function `signal_log_viewer` displays data from a selected strategy in a Signal Database Viewer
    interface.
    """
    st.title('Signal Database Viewer')

    # Dropdown to select the strategy
    table_names = get_table_names(signal_db_path)
    selected_table = st.selectbox('Select a Strategy', table_names)

    # Display data for the selected strategy
    if selected_table:
        df = get_data(selected_table,signal_db_path)
        st.write(f"Data for {selected_table}:")
        st.dataframe(df,hide_index=True,use_container_width=True)