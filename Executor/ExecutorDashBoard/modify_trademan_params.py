import os, sys
import streamlit as st
from dotenv import load_dotenv
from datetime import datetime
import pandas as pd
import csv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

signal_db_path = os.getenv("SIGNAL_DB_PATH")
ERROR_LOG_PATH = os.getenv("ERROR_LOG_PATH")
PARAMS_UPDATE_LOG_CSV_PATH = os.getenv("PARAMS_UPDATE_LOG_CSV_PATH")

from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import fetch_collection_data_firebase, update_fields_firebase, update_collection
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()

strategies_fb_db = os.getenv("FIREBASE_STRATEGY_COLLECTION")
market_info_fb_db = os.getenv("MARKET_INFO_FB_COLLECTION")

def modify_market_info():
    market_info = fetch_collection_data_firebase(market_info_fb_db)
    st.title("Market Info Manager")

    # Display form for market_info parameters
    with st.form("market_info_form"):
        updated_market_info = {}
        for key, value in market_info.items():
            if isinstance(value, (int, float)):
                # Use number_input for numeric values
                updated_market_info[key] = st.number_input(key, value=float(value))
            elif isinstance(value, str):
                # Use text_input for string values
                updated_market_info[key] = st.text_input(key, value=value)
            # Add other types as necessary
        
        submit_button = st.form_submit_button("Submit")
    
    if submit_button:
        # Assuming you're updating the entire document at once
        update_collection(market_info_fb_db,updated_market_info)
        # Log changes
        log_changes(updated_market_info)
        st.success("Market info updated successfully!")


def modify_strategy_params():
    strategies = fetch_collection_data_firebase(strategies_fb_db)
    # Your strategies data structure}
    # Streamlit UI components
    st.title("Strategy Manager")

    strategy_name = st.selectbox("Select Strategy", options=list(strategies.keys()))

    if strategy_name:
        strategy_params = strategies[strategy_name]

        for section, params in strategy_params.items():
            with st.expander(f"Edit {section} Parameters"):
                # Ensure params is a dictionary before proceeding
                if isinstance(params, dict):
                    updated_params = {}
                    for param, value in params.items():
                        # Your existing logic for handling parameters
                        updated_value = st.text_input(param, value=str(value))
                        updated_params[param] = updated_value
                        
                    submit_key = f"submit_{section}"
                    if st.button("Submit", key=submit_key):
                        # Assuming you want to update the entire section at once
                        update_fields_firebase(strategies_fb_db, strategy_name, {section: updated_params})
                        # Log changes with section_info
                        log_changes(updated_params, section_info=section)
                        st.success(f"{section} updated successfully!")

                    # Your existing logic for submitting updates
                else:
                    st.write(f"The section '{section}' does not contain editable parameters.")
                    
def log_changes(updated_data, section_info=None):
    logger.error(f"error testing 456")
    filename = PARAMS_UPDATE_LOG_CSV_PATH
    headers = ["date", "updated_info", "section_info"]
    date_str = datetime.now().strftime("%d%b%y %I:%M%p")  # Format: 23Feb24 9:43AM

    with open(filename, mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        
        # Write headers if file is being created for the first time
        if not os.path.isfile(filename):
            writer.writeheader()

        log_entry = {
            "date": date_str,
            "updated_info": str(updated_data),  # Corrected key to match header
            "section_info": section_info if section_info else ""
        }
        
        writer.writerow(log_entry)