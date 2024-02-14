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

def main():
    from Executor.ExecutorDashBoard.live_trade_viewer import trade_state_viewer, calculate_trademan_stats
    tab1, tab2, tab3, tab4,tab5 = st.tabs(["Admin","Error Monitor", "Trade State", "Order Executor","Signal Log"])
    
    st.balloons()

    # TODO: Add streamlit notifications for errors as well as trade state updates
    with tab1:
        st.header("TradeMan Admin")
        calculate_trademan_stats()

    with tab2:
        st.header("Error Monitor")
        
        #TODO: Add streamlit toast when error dataframe is updated to notify the user

        st.dataframe(error_logging_page.read_n_process_err_log(),use_container_width=True,hide_index=True)
    
        st.header("Trade State")
        trade_state_viewer()

    with tab3:
        st.header("Order Executor")
      
    
    with tab4:
        st.header("Signal Log")
        

# Run the app
if __name__ == "__main__":
    main()
