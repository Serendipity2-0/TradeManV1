import requests
from telethon.sync import TelegramClient
import os, sys
from dotenv import load_dotenv

DIR = os.getcwd()
sys.path.append(DIR)  # Add the current directory to the system path

# Load environment variables from the trademan.env file
ENV_PATH = os.path.join(DIR, 'trademan.env')
load_dotenv(ENV_PATH)

from loguru import logger
ERROR_LOG_PATH = os.getenv('ERROR_LOG_PATH')
logger.add(ERROR_LOG_PATH,level="TRACE", rotation="00:00",enqueue=True,backtrace=True, diagnose=True)


# Retrieve API details and contact number from the environment variables
api_id = os.getenv('TELETHON_API_ID')
api_hash = os.getenv('TELETHON_API_HASH')


def telegram_msg_bot(message, token):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {
        "chat_id": "YOUR_CHAT_ID",
        "text": message
    }
    response = requests.post(url, json=data)
    if response.status_code == 200:
        logger.info("Message sent successfully!")
    else:
        logger.error("Failed to send message.")

def send_telegram_message(phone_number, message):
    global api_id, api_hash
    # Define the session file path
    session_filepath = os.path.join(DIR, "Executor/ExecutorUtils/NotificationCenter/Telegram/+918618221715.session")
    
    # Create a Telegram client and send the message
    with TelegramClient(session_filepath, api_id, api_hash) as client:
        while message:
            chunk, message = message[:4096], message[4096:]
            client.send_message(phone_number, chunk, parse_mode='md')

