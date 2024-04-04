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

def calculate_pnl_summary(user_name, user_tables):
    """
    Calculate the sum of net_pnl for day, week, month, and year for each table in user_tables,
    and the overall sum across all strategies.
    """

    # Define time periods relative to the current date
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)
    start_of_year = today.replace(month=1, day=1)

    # Placeholder for individual strategy data and overall summary
    pnl_summary = []
    overall_summary = {'Name': user_name, 'Day': 0, 'Week': 0, 'Month': 0, 'Year': 0}

    # Process each table
    for table_dict in user_tables:
        for strategy, table in table_dict.items():
            if not table.empty:
                # Ensure 'exit_time' column is in datetime format
                table['exit_time'] = pd.to_datetime(table['exit_time']).dt.date
                
                # Calculate sum of net_pnl for each period
                day_sum = table[table['exit_time'] == today]['net_pnl'].sum()
                week_sum = table[table['exit_time'] >= start_of_week]['net_pnl'].sum()
                month_sum = table[table['exit_time'] >= start_of_month]['net_pnl'].sum()
                year_sum = table[table['exit_time'] >= start_of_year]['net_pnl'].sum()
                
                # Append results to strategy-specific summary list
                pnl_summary.append({
                    'User': user_name,
                    'Strategy': strategy,
                    'Day': day_sum,
                    'Week': week_sum,
                    'Month': month_sum,
                    'Year': year_sum
                })
                
                # Accumulate overall totals
                overall_summary['Day'] += day_sum
                overall_summary['Week'] += week_sum
                overall_summary['Month'] += month_sum
                overall_summary['Year'] += year_sum

                # format the overall_summary_df
                overall_summary['Day'] = "{:,.2f}".format(overall_summary['Day'])
                overall_summary['Week'] = "{:,.2f}".format(overall_summary['Week'])
                overall_summary['Month'] = "{:,.2f}".format(overall_summary['Month'])
                overall_summary['Year'] = "{:,.2f}".format(overall_summary['Year'])

    # Convert summary data to DataFrame for easier viewing/manipulation
    summary_df = pd.DataFrame(pnl_summary)
    overall_summary_df = pd.DataFrame([overall_summary])

    return summary_df, overall_summary_df

def user_pnl_movement_data():
    active_users = fetch_active_users_from_firebase()

    for user in active_users:
        try:
            user_db_path = os.path.join(DB_DIR, f"{user['Tr_No']}.db")
            user_db_conn = get_db_connection(user_db_path)
            user_tables = fetch_user_tables(user_db_conn)
            user_name = user['Profile']['Name']
            summary_df, overall_summary_df = calculate_pnl_summary(user_name,user_tables)
            return overall_summary_df
            # Placeholder values, replace with actual queries and Firebase fetches

        except Exception as e:
            logger.error(f"Error: {e}")
    
