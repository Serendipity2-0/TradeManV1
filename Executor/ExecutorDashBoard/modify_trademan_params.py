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
from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import fetch_collection_data_firebase, update_fields_firebase

strategies_fb_db = os.getenv("STRATEGIES_FB_COLLECTION")
market_info_fb_db = os.getenv("MARKET_INFO_FB_COLLECTION")

# CRUD function on market_info.json
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
        update_fields_firebase("your-collection", "market_info", updated_market_info)
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

                    # Your existing logic for submitting updates
                else:
                    st.write(f"The section '{section}' does not contain editable parameters.")