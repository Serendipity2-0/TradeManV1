import io
import os
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

    # Extract client data from the dictionary
    Name = client_data.get("Name", "")
    Username = client_data.get("Username", "")
    Email = client_data.get("Email", "")
    Phone_Number = client_data.get("Phone Number", "")
    Date_of_Birth = client_data.get("Date of Birth", "")
    Aadhar_Card_No = client_data.get("Aadhar Card No", "")
    PAN_Card_No = client_data.get("PAN Card No", "")
    Bank_Name = client_data.get("Bank Name", "")
    Bank_Account_No = client_data.get("Bank Account No", "")
    Strategy_list = client_data.get("Strategy list", [])
    Comments = client_data.get("Comments", "")
    Smart_Contract = client_data.get("Smart Contract", "")

    # Create a DataFrame to display the client data in tabular form
    data = {
        "Field": [
            "Name",
            "Username",
            "Email",
            "Phone Number",
            "Date of Birth",
            "Aadhar Card No",
            "PAN Card No",
            "Bank Name",
            "Bank Account No",
            "Comments",
            "Smart Contract",
        ],
        "Value": [
            str(Name),
            str(Username),
            str(Email),
            str(Phone_Number),
            str(Date_of_Birth),
            str(Aadhar_Card_No),
            str(PAN_Card_No),
            str(Bank_Name),
            str(Bank_Account_No),
            str(Comments),
            str(Smart_Contract),
        ],
    }
    df = pd.DataFrame(data)
    # Display the DataFrame as a table with CSS styling and remove index column
    st.markdown(table_style, unsafe_allow_html=True)
    st.write(df.to_html(index=False, escape=False), unsafe_allow_html=True)

    # Display the broker list in vertical tabular form
    st.write("Broker")
    
    # Display the strategy list in vertical tabular form
    st.subheader("Strategies")
    if isinstance(Strategy_list, list) and len(Strategy_list) > 0:
        strategy_data = {"Strategy Name": [], "Broker": [], "Percentage Allocated": []}
        for strategy in Strategy_list:
            strategy_name = strategy.get("strategy_name", "")
            broker = strategy.get("broker", "")

            for selected_strategy in strategy_name:
                for selected_broker in broker:
                    perc_allocated_key = f"strategy_perc_allocated_{selected_strategy}_{selected_broker}_0"
                    percentage_allocated = strategy.get(perc_allocated_key, "")

                    strategy_data["Strategy Name"].append(selected_strategy)
                    strategy_data["Broker"].append(selected_broker)
                    strategy_data["Percentage Allocated"].append(percentage_allocated)

        strategy_df = pd.DataFrame(strategy_data)
        # Display the DataFrame as a table with CSS styling and remove index column
        st.markdown(table_style, unsafe_allow_html=True)
        st.write(strategy_df.to_html(index=False, escape=False), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

   

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