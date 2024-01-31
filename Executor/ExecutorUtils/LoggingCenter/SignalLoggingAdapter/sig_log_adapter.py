import os,sys
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment,NamedStyle
from dotenv import load_dotenv
from datetime import datetime
from openpyxl.utils.dataframe import dataframe_to_rows



DIR = os.getcwd()
sys.path.append(DIR)

import MarketUtils.general_calc as general_calc
import Brokers.place_order_calc as place_order_calc
from Strategies.StrategyBase import Strategy
import DBpy.DB_utils as db_utils

ENV_PATH = os.path.join(DIR, 'trademan.env')
load_dotenv(ENV_PATH)

excel_dir = os.getenv('onedrive_excel_folder')
# excel_dir = r"/Users/amolkittur/Desktop/Dev/UserProfile/Excel"


#Should read the csv in the format of list of list of dict{trades for strategies for user}
def read_from_db(conn, strategy, date_column='exit_time'):
    """Read data from the database for a specific strategy and date."""
    today = pd.Timestamp.today().normalize()
    query = f"SELECT * FROM {strategy} WHERE strftime('%Y-%m-%d', {date_column}) = ?"
    return pd.read_sql_query(query, conn, params=(today.strftime('%Y-%m-%d'),))

def append_data_to_db(conn, data, table_name):
    """Append data to the specified table in the database."""
    new_data_df = pd.DataFrame([data])
    try:
        new_data_df.to_sql(table_name, conn, if_exists='append', index=False)
    except Exception as e:
        print(f"An error occurred while appending to the table {table_name}: {e}")

def process_signal_info():
    #fetch the details from firebase/strategy/today_signals(list)/
    pass

def process_signal():
    #Segregate the info from the firebase/strategy/today_signals(list)/ and upload it to the DB
    pass

def process_user():
    #from signal_log_validator get the matched orders and upload it to the DB
    pass
