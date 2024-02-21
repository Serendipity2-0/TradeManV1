import streamlit as st
from datetime import date
from PIL import Image
import io
import os,sys
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials,db



DIR = os.getcwd()
sys.path.append(DIR)
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

cred_filepath = os.getenv("FIREBASE_CRED_PATH")
firebase_db_url = os.getenv("FIREBASE_DATABASE_URL")
FIREBASE_USER_COLLECTION = os.getenv("FIREBASE_USER_COLLECTION")

cred = credentials.Certificate(cred_filepath)
firebase_admin.initialize_app(cred, {"databaseURL": firebase_db_url})


def upload_client_data_to_firebase(user_dict):
    ref = db.reference(FIREBASE_USER_COLLECTION)
    # Use the new_tr_no as a key for the new entry
    new_ref = ref.child("Tr13") # TODO: get the new_tr_no from the admin fb db
    new_ref.set(user_dict)
    # ref.push(user_dict)
    return "Data uploaded successfully"


def register_page():

    # Set the title for the Streamlit app
    st.markdown("<h3 style='color: darkblue'>Register</h3>", unsafe_allow_html=True)

    # Take inputs for client information
    name = st.text_input("Name:", key="name_input")
    UserName = st.text_input("Username:", key="Username_input")
    email = st.text_input("Email:", key="email_input")
    Password = st.text_input("Password:", type="password", key="Password_input")
    phone = st.text_input("Phone Number:", key="phone_input")
    dob = st.date_input(
        "Date of Birth:", min_value=date(1950, 1, 1), key="dob_input"
    ).strftime("%d-%m-%Y")
    aadhar = st.text_input("Aadhar Card No:", key="aadhar_input")
    pan = st.text_input("Pan Card No:", key="pan_input")
    bank_name = st.text_input("Bank Name:", key="bank_name_input")
    bank_account = st.text_input("Bank Account No:", key="bank_account_input")
    broker = st.selectbox(
        "Brokers",
        ["Zerodha", "Alice Blue"],
        key="broker_input",
    )
    
    # Risk Profile Section
    st.markdown("## Risk Profile")
    area_of_investment = st.multiselect(
        "Area of Investment:", ["Debt", "Equity", "FnO"], key="area_of_investment"
    )
    commission = st.selectbox(
        "Commission:", ["50-50", "75-25"], key="commission"
    )
    drawdown_tolerance = st.slider(
        "Drawdown Tolerance (%):", min_value=1, max_value=100, key="drawdown_tolerance"
    )
    expected_horizon = st.number_input(
        "Expected Horizon (months):", min_value=1, key="expected_horizon"
    )
    withdrawal_frequency = st.selectbox(
        "Withdrawal Frequency:", ["OnRequest", "Weekly"], key="withdrawal_frequency"
    )
 

    # Add a submit button
    submit = st.button("Submit", key="submit_button")

    # Check if the submit button is clicked
    if submit:
        st.balloons()
        # Check if all the fields are filled before submitting
        if (
            name
            and dob
            and phone
            and email
            and aadhar
            and pan
            and bank_account
        ):
            # Validate PAN Card Number (should be in uppercase)
            pan = pan.upper()

            # Validate Phone Number (should be 10 digits)
            if len(phone) != 10:
                st.error("Phone Number should be 10 digits")
                return

            # Validate Aadhaar Card Number (should be 12 digits)
            if len(aadhar) != 12:
                st.error("Aadhaar Card No should be 12 digits")
                return
            
            
            # Convert client data to dictionary for firebase compatibility
            client_data_dict = {
                "Name": name,
                "Username": UserName,
                "Email": email,
                "Password": Password,
                "Phone Number": phone,
                "Date of Birth": dob,
                "Aadhar Card No": aadhar,
                "PAN Card No": pan,
                "Bank Name": bank_name,
                "Bank Account No": bank_account,
                "Broker": broker,
                "RiskProfile": {
                    "AreaOfInvestment": area_of_investment,
                    "Commission": commission,
                    "DrawdownTolerance": str(drawdown_tolerance),
                    "Duration": str(expected_horizon),
                    "WithdrawalFrequency": withdrawal_frequency
                }
                
            }
            
            # Persist the client data to Firebase Realtime Database
            upload_client_data_to_firebase(client_data_dict)

            
        else:
            # If not all fields are filled, show an error message
            unfilled_fields = []
            if not name:
                unfilled_fields.append("Name")
            if not dob:
                unfilled_fields.append("Date of Birth")
            if not phone:
                unfilled_fields.append("Phone Number")
            if not email:
                unfilled_fields.append("Email")
            if not aadhar:
                unfilled_fields.append("Aadhar Card No")
            if not pan:
                unfilled_fields.append("Pan Card No")
            if not bank_account:
                unfilled_fields.append("Bank Account No")
           

            error_message = "Please fill the following fields: " + ", ".join(
                unfilled_fields
            )
            st.error(error_message)
    # Function to convert percentage string to float
    def percentage_string_to_float(percentage_str):
        return float(percentage_str.strip("%")) / 100


if __name__ == "__main__":
    register_page()
