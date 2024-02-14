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

from loguru import logger

ERROR_LOG_PATH = os.getenv("ERROR_LOG_PATH")
logger.add(
    ERROR_LOG_PATH,
    level="TRACE",
    rotation="00:00",
    enqueue=True,
    backtrace=True,
    diagnose=True,
)


# Function to get a list of all tables in the database
def get_table_names(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [table[0] for table in cur.fetchall()]
    conn.close()
    return tables

# Function to get dataframe from selected table
def get_data(table_name, db_path):
    conn = sqlite3.connect(db_path)
    query = f"SELECT * FROM {table_name}"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def signal_log_viewer():
    st.title('Signal Database Viewer')

    # Dropdown to select the strategy
    table_names = get_table_names(signal_db_path)
    selected_table = st.selectbox('Select a Strategy', table_names)

    # Display data for the selected strategy
    if selected_table:
        df = get_data(selected_table,signal_db_path)
        st.write(f"Data for {selected_table}:")
        st.dataframe(df,hide_index=True,use_container_width=True)