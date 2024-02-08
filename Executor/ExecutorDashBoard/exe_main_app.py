# Required imports
import glob
import os
import sqlite3

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from exe_login import exe_login_page, SessionState
from loguru import logger as log


#######################
# Page configuration
st.set_page_config(
    page_title="TradeMan Executor Dashboard",
    page_icon="🏂",
    layout="wide",
    initial_sidebar_state="expanded",
)

##################################################################
session_state = SessionState(logged_in=False, client_data=None)


# Streamlit app
def main():
    log.info("Starting TradeMan Executor Dashboard")
    exe_login_page()

    if session_state.logged_in:
        st.title("TradeMan Execution Dashboard")

        # Create tabs for 'Data', 'Stats', and 'Charts'
        tab1, tab2, tab3 = st.tabs(["Live View", "Order Executor", "Error Monitor"])

        with tab1:
            st.header("Live View")

        with tab2:
            st.header("Order Exector")

        with tab3:
            st.header("Error Monitor")


# Run the app
if __name__ == "__main__":
    main()
