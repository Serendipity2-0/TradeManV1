import requests
from telethon.sync import TelegramClient
import os, sys
from dotenv import load_dotenv

DIR = os.getcwd()
sys.path.append(DIR)  # Add the current directory to the system path

# Load environment variables from the trademan.env file
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()


# Retrieve API details and contact number from the environment variables
api_id = os.getenv("TELETHON_API_ID")
api_hash = os.getenv("TELETHON_API_HASH")


def telegram_msg_bot(message, token):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": "YOUR_CHAT_ID", "text": message}
    response = requests.post(url, json=data)
    if response.status_code == 200:
        logger.info("Message sent successfully!")
    else:
        logger.error("Failed to send message.")


def send_telegram_message(phone_number, message):
    global api_id, api_hash
    # Define the session file path
    session_filepath = os.path.join(
        DIR, "Executor/ExecutorUtils/NotificationCenter/Telegram/+918618221715.session"
    )

    # Create a Telegram client and send the message
    with TelegramClient(session_filepath, api_id, api_hash) as client:
        while message:
            chunk, message = message[:4096], message[4096:]
            client.send_message(phone_number, chunk, parse_mode="md")

def send_file_via_telegram(file_path, file_name):
    phone_number = os.getenv("OMKAR_PHONE_NUMBER")
    global api_id, api_hash
    # Define the session file path
    session_filepath = os.path.join(
        DIR, "Executor/ExecutorUtils/NotificationCenter/Telegram/+918618221715.session"
    )

    # Create a Telegram client and send the file
    with TelegramClient(session_filepath, api_id, api_hash) as client:
        client.send_file(phone_number, file_path, caption=file_name)

def send_consoildated_report_via_telegram_to_group(file_path):
    bot_token = os.getenv("SERENDIPITY_TELEGRAM_BOT_TOKEN")
    bot_chatID = os.getenv("TELEGRAM_REPORT_GROUP_ID")

    url = f'https://api.telegram.org/bot{bot_token}/sendDocument'

    payload = {
        'chat_id': bot_chatID,
    }

    files = {
        'document': open(file_path, 'rb')
    }

    response = requests.post(url, data=payload, files=files)
    logger.info(response.text)
