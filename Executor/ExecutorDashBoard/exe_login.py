import base64
import datetime
import io
import os, sys

import firebase_admin
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from firebase_admin import credentials, db, storage
from PIL import Image
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()

DIR = os.getcwd()
sys.path.append(DIR)

ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

firebase_credentials_path = os.getenv("FIREBASE_CRED_PATH")
database_url = os.getenv("FIREBASE_DATABASE_URL")
storage_bucket = os.getenv("STORAGE_BUCKET")
admin_collection = os.getenv("ADMIN_COLLECTION")

logger.info(firebase_credentials_path)

class SessionState:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


# Create a session state variable
session_state = SessionState(logged_in=False, client_data=None)

# Initialize Firebase app
if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_credentials_path)
    firebase_admin.initialize_app(
        cred, {"databaseURL": database_url, "storageBucket": storage_bucket}
    )

def exe_login_page():
    """
    The function `exe_login_page` handles user login functionality by verifying credentials from a
    Firebase Realtime Database and displaying appropriate messages based on the outcome.
    """
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    # If the user is not logged in, show the login form
    if not st.session_state.logged_in:
        # Take inputs for login information
        username = st.text_input("Username:", key="username_input")
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
                ref = db.reference(admin_collection)

                # Fetch all clients data
                clients = ref.get()

                # Go through each client and check if the credentials match
                for client_id, client_data in clients.items():
                    if (
                        client_data.get("username") == username
                        and client_data.get("Password") == password
                    ):
                        # If credentials match, show a success message and break the loop
                        session_state.logged_in = True
                        session_state.client_data = client_data
                        st.rerun()
                        break
                else:
                    # If no matching credentials are found, show an error message
                    st.error("Invalid username or password.")
            except Exception as e:
                # Show an error message if there's an exception
                st.error("Failed to fetch data: " + str(e))
    else:
        pass
