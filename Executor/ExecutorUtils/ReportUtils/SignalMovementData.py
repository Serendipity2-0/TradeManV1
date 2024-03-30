import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

DIR = os.getcwd()
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)


def calculate_sum_trade_points(table_name, conn):
    # Query to select relevant columns (focusing on entry_time and trade_points)
    query = f"SELECT entry_time, trade_points FROM {table_name}"
    df = pd.read_sql_query(query, conn)
    
    # Convert entry_time to datetime, handling empty or incorrect formats gracefully
    try:
        df['entry_time'] = pd.to_datetime(df['entry_time'])
    except Exception as e:
        return {'Strategy': table_name, 'Today': None, 'Week': None, 'Month': None, 'Year': None}
    
    # Use the system's current date for calculations
    current_date = pd.to_datetime('today').normalize()  # Normalize to remove time component
    
    periods = {
        'Today': current_date - timedelta(days=1),
        'Week': current_date - timedelta(weeks=1),
        'Month': current_date - timedelta(days=30),  # Approximation for a month
        'Year': current_date - timedelta(days=365)  # Leap year not considered for simplicity
    }
    
    results = {'Strategy': table_name}
    
    for period_name, start_date in periods.items():
        period_df = df[(df['entry_time'] > start_date) & (df['entry_time'] < current_date)]
        sum_points = period_df['trade_points'].sum()
        results[period_name] = sum_points
        results[period_name] = "{:,.2f}".format(results[period_name])
    
    return results

# Connect to the SQLite database
db_path = os.getenv("SIGNAL_DB_PATH")
conn = sqlite3.connect(db_path)

# Retrieve all table names
tables_query = "SELECT name FROM sqlite_master WHERE type='table';"
tables = pd.read_sql_query(tables_query, conn)['name'].tolist()

# Calculate metrics for each table and collect them in a list
data_dict = [calculate_sum_trade_points(table, conn) for table in tables]

# Close the database connection
conn.close()

def main():
    # Create DataFrame from the collected data
    df = pd.DataFrame(data_dict)

    # Reordering DataFrame columns to match the requested format
    df = df[['Strategy', 'Today', 'Week', 'Month', 'Year']]

    return df
