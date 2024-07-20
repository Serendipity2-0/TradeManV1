import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

DIR = os.getcwd()
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)


def calculate_sum_trade_points(table_name, conn):
    """
    Calculate the sum of trade points for different time periods from a specified table.

    Args:
        table_name (str): The name of the table to query.
        conn (sqlite3.Connection): The SQLite database connection.

    Returns:
        dict: A dictionary containing the strategy name and sum of trade points for today, this week, this month, and this year.
    """
    # Query to select relevant columns (focusing on entry_time and trade_points)
    query = f"SELECT exit_time, trade_points FROM {table_name}"
    df = pd.read_sql_query(query, conn)
    # Convert exit_time to datetime, handling empty or incorrect formats gracefully
    try:
        df["exit_time"] = pd.to_datetime(df["exit_time"])
    except Exception as e:
        print(e)
        return {
            "Strategy": table_name,
            "Today": None,
            "Week": None,
            "Month": None,
            "Year": None,
        }

    # Use the system's current date for calculations
    current_date = pd.to_datetime("today").normalize()  # Start of today
    next_day = current_date + timedelta(days=1)  # Start of the next day

    periods = {
        "Today": (current_date, next_day),
        "Week": (current_date - timedelta(weeks=1), next_day),
        "Month": (
            current_date - timedelta(days=30),
            next_day,
        ),  # Approximation for a month
        "Year": (
            current_date - timedelta(days=365),
            next_day,
        ),  # Leap year not considered for simplicity
    }
    results = {"Strategy": table_name}

    for period_name, (start_date, end_date) in periods.items():
        period_df = df[(df["exit_time"] >= start_date) & (df["exit_time"] < end_date)]
        sum_points = period_df["trade_points"].sum()
        results[period_name] = "{:,.2f}".format(sum_points)

    return results


# Connect to the SQLite database
db_path = os.getenv("SIGNAL_DB_PATH")
conn = sqlite3.connect(db_path)

# Retrieve all table names
tables_query = "SELECT name FROM sqlite_master WHERE type='table';"
tables = pd.read_sql_query(tables_query, conn)["name"].tolist()
# Remove Error table from the list
tables.remove("Error")

# Calculate metrics for each table and collect them in a list
data_dict = [calculate_sum_trade_points(table, conn) for table in tables]

# Close the database connection
conn.close()


def main():
    """
    Main function to create a DataFrame containing the sum of trade points for different strategies and time periods.

    Returns:
        DataFrame: DataFrame containing the strategy name and sum of trade points for today, this week, this month, and this year.
    """
    # Create DataFrame from the collected data
    df = pd.DataFrame(data_dict)

    # Reordering DataFrame columns to match the requested format
    df = df[["Strategy", "Today", "Week", "Month", "Year"]]

    return df
