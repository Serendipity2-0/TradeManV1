import os, sys
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime, timedelta

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)
 
DB_DIR = os.getenv("DB_DIR")

from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import fetch_active_users_from_firebase,fetch_active_strategies_all_users
from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter import get_db_connection
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()

# I want to calculate the PnL for each user and categorize them into Daily, Weekly, Monthly, and Yearly

def fetch_user_tables(user_db_conn):
    """
    Fetch user tables for the active strategies.
    Tables whose names are not in the list of active strategies are skipped.
    """
    user_tables = []
    active_strategies = fetch_active_strategies_all_users()
    try:
        # Fetch all table names from the database
        all_tables_query = "SELECT name FROM sqlite_master WHERE type='table';"
        all_table_names = [table_name[0] for table_name in user_db_conn.execute(all_tables_query).fetchall()]
        
        # Filter tables based on active strategies
        for strategy in active_strategies:
            if strategy in all_table_names:
                # If the table exists, fetch its data
                query = f"SELECT * FROM {strategy}"
                table_df = pd.read_sql_query(query, user_db_conn)
                user_tables.append({strategy: table_df})
            else:
                # If the table for a strategy does not exist, you can choose to log or take some action
                logger.info(f"Table for strategy {strategy} does not exist.")
    except Exception as e:
        logger.error(f"Error in fetching user tables for active strategies: {e}")
    return user_tables

def calculate_pnl_summary():
    """
    Calculate the sum of net_pnl for day, week, month, and year for each table in user_tables,
    and the overall sum across all strategies.
    """
    pnl_summary = []
    overall_summaries = []  # List to hold overall summaries for each user
    active_users = fetch_active_users_from_firebase()
    for user in active_users:
        user_name = user['Profile']['Name']
        user_db_path = os.path.join(DB_DIR, f"{user['Tr_No']}.db")
        user_db_conn = get_db_connection(user_db_path)
        user_tables = fetch_user_tables(user_db_conn)
        overall_summary = {'User': user_name, 'Day': 0, 'Week': 0, 'Month': 0, 'Year': 0}

        today = datetime.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        start_of_month = datetime(today.year, today.month, 1).date()
        start_of_year = datetime(today.year, 1, 1).date()

        for table_dict in user_tables:
            for strategy, table in table_dict.items():
                if not table.empty:
                    table['exit_time'] = pd.to_datetime(table['exit_time']).dt.date

                    day_sum = table[table['exit_time'] == today]['net_pnl'].sum()
                    week_sum = table[table['exit_time'] >= start_of_week]['net_pnl'].sum()
                    month_sum = table[table['exit_time'] >= start_of_month]['net_pnl'].sum()
                    year_sum = table[table['exit_time'] >= start_of_year]['net_pnl'].sum()

                    pnl_summary.append({
                        'User': user_name,
                        'Strategy': strategy,
                        'Day': day_sum,
                        'Week': week_sum,
                        'Month': month_sum,
                        'Year': year_sum
                    })

                    overall_summary['Day'] += day_sum
                    overall_summary['Week'] += week_sum
                    overall_summary['Month'] += month_sum
                    overall_summary['Year'] += year_sum

        # After processing all strategies for a user, add the overall summary for that user to the list
        overall_summaries.append(overall_summary)

    # Convert the summaries into DataFrames
    summary_df = pd.DataFrame(pnl_summary)
    overall_summary_df = pd.DataFrame(overall_summaries)

    return summary_df, overall_summary_df

def main():
    try:
        strategy_wise_pnl,overall_pnl = calculate_pnl_summary()
    except Exception as e:
        logger.error(f"Error: {e}")
    return overall_pnl

    
