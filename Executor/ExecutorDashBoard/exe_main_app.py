# Required imports
import glob
import os,sys
import sqlite3

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from loguru import logger as log
import error_logging_page
from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

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


#######################
# Page configuration
st.set_page_config(
    page_title="TradeMan Executor Dashboard",
    page_icon="🏂",
    layout="wide",
    initial_sidebar_state="expanded",
)


# Streamlit app
def main():
    # log.info("Starting TradeMan Executor Dashboard")
    # exe_login_page()

    # if session_state.logged_in:
    #     st.title("TradeMan Execution Dashboard")

    # Create tabs for 'Data', 'Stats', and 'Charts'
    tab1, tab2, tab3 = st.tabs(["Live View", "Order Executor", "Error Monitor"])

    with tab1:
        st.header("Live View")

    with tab2:
        st.header("Order Executor")

    with tab3:
        st.header("Error Monitor")
        st.dataframe(error_logging_page.read_n_process_err_log(),use_container_width=True,hide_index=True)
            


# Run the app
if __name__ == "__main__":
    main()
