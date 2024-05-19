import streamlit as st
import os, sys
from time import sleep

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

from Executor.ExecutorUtils.NotificationCenter.Telegram.telegram_adapter import send_telegram_message
from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import fetch_active_users_from_firebase


def send_notice():
    # Create a text input field
    user_input = st.text_area("Enter your message", "")

    # Create a submit button
    if st.button("Send Notice"):
        st.text(f"You submitted:\n{user_input}")
        # Send the message to all active users
        active_users = fetch_active_users_from_firebase()
        for user in active_users:
            send_telegram_message(user["Profile"]["PhoneNumber"], user_input)
            sleep(1)





