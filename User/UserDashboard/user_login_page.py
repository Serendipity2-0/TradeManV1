
import os,sys

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from firebase_admin import credentials, db, storage
from PIL import Image
from profile_page import show_profile
from register_page import register_page
from streamlit_calendar import calendar
from streamlit_option_menu import option_menu

DIR = os.getcwd()
sys.path.append(DIR)
ENV_PATH = os.path.join(DIR, "trademan.env")
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
    page_title="TradeMan User Dashboard",
    page_icon="🏂",
    layout="wide",
    initial_sidebar_state="expanded",
)


def user_login_page():
    if not st.session_state.logged_in:
        # create sidebar with radio buttons for login page, Admin Page and register page
        st.sidebar.title("Welcome to TradeMan")
        radio = st.sidebar.radio("", ("Login", "Admin Page", "Register"))
        if radio == "Login":
            login()
        elif radio == "Admin Page":
            admin_login()
        elif radio == "Register":
            register_page()
            



def login():

    # If the user is not logged in, show the login form
    if not st.session_state.logged_in:
        # Take inputs for login information
        username = st.text_input("Email or Phone Number:", key="user_email_input")
        password = st.text_input(
            "Password:", type="password", key="user_Password_input"
        )

        # Add a login button
        login = st.button("Login")

        # Check if the login button is clicked
        if login:
            # Fetch data from Firebase Realtime Database to verify the credentials
            try:
                # Get a reference to the 'clients' node in the database
                ref = db.reference("trademan_clients")

                # Fetch all clients data
                clients = ref.get()

                # Go through each client and check if the credentials match
                for client_id, client_data in clients.items():
                    logger.debug("")
                    
                    if (
                        client_data.get('Profile').get("Email") == username
                        or client_data.get('Profile').get("PhoneNumber") == username
                    ) and client_data.get('Profile').get("GmailPassword") == password:
                        logger.debug(f"client_data: {client_data}")
                        # If credentials match, show a success message and break the loop
                        st.success("Logged in successfully.")
                        st.session_state.logged_in = True
                        st.session_state.client_data = client_data
                        st.experimental_rerun()
                        break
                else:
                    # If no matching credentials are found, show an error message
                    st.error("Invalid username or password.")
            except Exception as e:
                # Show an error message if there's an exception
                st.error("Failed to fetch data: " + str(e))
    else:
        # If the user is already logged in, show the other contents
        pass


def admin_login():
    pass




def logout():
    from user_main_app import session_state

    # Reset session state variables
    session_state.logged_in = False
    session_state.client_data = None
