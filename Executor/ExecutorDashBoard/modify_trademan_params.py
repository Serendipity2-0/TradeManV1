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
from Executor.ExecutorDashBoard.exe_main_app_utils import log_changes
from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import discord_admin_bot

logger = LoggerSetup()

strategies_fb_db = os.getenv("FIREBASE_STRATEGY_COLLECTION")
market_info_fb_db = os.getenv("MARKET_INFO_FB_COLLECTION")

def modify_market_info():
    """
    The `modify_market_info` function fetches market information from a Firebase database, displays a
    form for updating the information using Streamlit, and updates the database with the new information
    upon submission.
    """
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
        message = f"Market info updated for {updated_market_info}"
        discord_admin_bot(message)
        st.success("Market info updated successfully!")


def modify_strategy_params():
    """
    This Python function modifies strategy parameters by allowing users to select a strategy, edit its
    parameters in different sections, and submit updates to a Firebase database.
    """
    strategies = fetch_collection_data_firebase(strategies_fb_db)
    # Your strategies data structure}
    # Streamlit UI components
    st.title("Strategy Manager")

    strategy_name = st.selectbox("Select Strategy", options=list(strategies.keys()))

    if strategy_name:
        strategy_params = strategies[strategy_name]
        strategy_params.pop("MarketInfoParams")

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
                        message = f"Params {updated_params} changed for {strategy_name} in {section}"
                        discord_admin_bot(message)
                        st.success(f"{section} updated successfully!")

                    # Your existing logic for submitting updates
                else:
                    st.write(f"The section '{section}' does not contain editable parameters.")
