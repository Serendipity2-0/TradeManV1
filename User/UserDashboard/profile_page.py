import io
import os, sys
import base64
import datetime
from PIL import Image
import streamlit as st
import pandas as pd
from firebase_admin import db
from firebase_admin import credentials, storage
import json
from io import BytesIO
import streamlit.components.v1 as components
from streamlit_option_menu import option_menu
from dotenv import load_dotenv



DIR = os.getcwd()
sys.path.append(DIR)
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.ExeUtils import get_previous_trading_day

ACTIVE_STRATEGIES = os.getenv("ACTIVE_STRATEGIES")
USR_TRADELOG_DB_FOLDER = os.getenv("USR_TRADELOG_DB_FOLDER")
user_db_collection = os.getenv("FIREBASE_USER_COLLECTION")

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()


def display_profile_picture(client_data, style=None):
    # Ensure that client_data is a dictionary
    if isinstance(client_data, str):
        # Try to load the string as a JSON dictionary
        try:
            client_data = json.loads(client_data)
        except json.JSONDecodeError:
            return

    # Fetch the profile picture from the client_data dictionary
    profile_picture = client_data.get("Profile Picture")

    # Display the profile picture if available
    if profile_picture is not None:
        try:
            # Ensure the base64 string is correctly padded
            profile_picture += "=" * ((4 - len(profile_picture) % 4) % 4)

            # Decode base64 string to bytes
            profile_picture_bytes = base64.b64decode(profile_picture)

            # Convert profile picture from bytes to PIL Image
            image = Image.open(io.BytesIO(profile_picture_bytes))

            # Convert the image to RGB
            image_rgb = image.convert("RGB")

            # Save the image in JPG format with reduced quality (adjust the quality value as needed)
            image_path = "profile_picture.jpg"
            image_rgb.save(image_path, "JPEG", quality=50)

            # The rest of your existing code to display the image...

        except Exception as e:
            st.error(f"Failed to load profile picture: {e}")
            return


def show_profile(client_data):
    # Display profile picture
    # display_profile_picture(client_data)

    pd.options.display.float_format = "{:,.2f}".format
    # Set the title for the Streamlit app
    st.markdown("<h3 style='color: darkblue'>Profile</h3>", unsafe_allow_html=True)
    
    client_profile = client_data.get("Profile", {})
    client_broker = client_data.get("Broker", {})
    client_strategies = client_data.get("Strategies", {})
    # get all list of "StrategyName" under client_data.get("Strategies")

    # Extract client data from the dictionary
    Name = client_profile.get("Name", "")
    Email = client_profile.get("Email", "")
    Phone_Number = client_profile.get("PhoneNumber", "")
    Date_of_Birth = client_profile.get("DOB", "")
    Aadhar_Card_No = client_profile.get("AadharCardNo", "")
    PAN_Card_No = client_profile.get("PANCardNo", "")
    Bank_Name = client_profile.get("BankName", "")
    Bank_Account_No = client_profile.get("BankAccountNo", "")
    Broker = client_broker.get("BrokerName", "")
    
    # Strategy_list is list of keys from client_strategies
    
    Strategy_list = list(client_strategies.keys())
    logger.debug(f"Strategy_list: {client_strategies}")
    logger.debug(f"typeof Strategy_list: {type(client_strategies)}")

    # Create a DataFrame to display the client data in tabular form
    data = {
        "Field": [
            "Name",
            "Email",
            "Phone Number",
            "Date of Birth",
            "Aadhar Card No",
            "PAN Card No",
            "Bank Name",
            "Bank Account No",
            "BrokerName",
            "Strategies",
        ],
        "Value": [
            str(Name),
            str(Email),
            str(Phone_Number),
            str(Date_of_Birth),
            str(Aadhar_Card_No),
            str(PAN_Card_No),
            str(Bank_Name),
            str(Bank_Account_No),
            str(Broker),
            str(Strategy_list),
        ],
    }
    logger.debug(f"Data: {data}")
    df = pd.DataFrame(data)
    # Display the DataFrame as a table with CSS styling and remove index column
    st.markdown(table_style, unsafe_allow_html=True)
    st.write(df.to_html(index=False, escape=False), unsafe_allow_html=True)


table_style = """
<style>
table.dataframe {
    border-collapse: collapse;
    width: 100%;
}

table.dataframe th,
table.dataframe td {
    border: 1px solid black;
    padding: 8px;
    text-align: left; /* Align text to the left */
}

/* Header background color */
table.dataframe th {
    background-color: AliceBlue;
}

/* Alternating row background colors */
table.dataframe tr:nth-child(even) {
    background-color: AliceBlue;  /* Even rows will be AliceBlue */
}
table.dataframe tr:nth-child(odd) {
    background-color: AliceBlue;  /* Odd rows will be white */
}

/* Hover style for rows */
table.dataframe tr:hover {
    background-color: HoneyDew;
}
</style>
"""