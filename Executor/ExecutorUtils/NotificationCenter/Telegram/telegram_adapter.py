import requests
from telethon.sync import TelegramClient
import os, sys
from dotenv import load_dotenv
import asyncio
import nest_asyncio

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


def send_telegram_message(phone_number, message):
    """
    Send a message to a specified phone number via Telegram.

    Args:
        phone_number (str): The recipient's phone number.
        message (str): The message to be sent. Messages longer than 4096 characters will be sent in chunks.

    This function uses the Telethon library to create a Telegram client and send the message.
    """
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


async def send_telegram_message_async(
    phone_number, message, session_filepath, api_id, api_hash
):
    """
    Asynchronously send a message to a specified phone number via Telegram.

    Args:
        phone_number (str): The recipient's phone number.
        message (str): The message to be sent. Messages longer than 4096 characters will be sent in chunks.
        session_filepath (str): The path to the session file.
        api_id (str): The API ID for the Telegram client.
        api_hash (str): The API hash for the Telegram client.

    This function uses the Telethon library to create a Telegram client and send the message asynchronously.
    """
    async with TelegramClient(session_filepath, api_id, api_hash) as client:
        while message:
            chunk, message = message[:4096], message[4096:]
            await client.send_message(phone_number, chunk, parse_mode="md")


def send_telegram_async_message(phone_number, message):
    """
    Send a message to a specified phone number via Telegram asynchronously.

    Args:
        phone_number (str): The recipient's phone number.
        message (str): The message to be sent. Messages longer than 4096 characters will be sent in chunks.

    This function creates a new event loop and runs the asynchronous send_telegram_message_async function.
    """
    global api_id, api_hash
    # Define the session file path
    session_filepath = os.path.join(
        DIR, "Executor/ExecutorUtils/NotificationCenter/Telegram/+918618221715.session"
    )

    # Create a new event loop and set it as the current loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Run the asynchronous function
        loop.run_until_complete(
            send_telegram_message_async(
                phone_number, message, session_filepath, api_id, api_hash
            )
        )
    finally:
        # Close the loop at the end of the script
        loop.close()


def send_file_via_telegram(recipient, file_path, file_name, is_group=False):
    """
    Send a file to a specified recipient via Telegram.

    Args:
        recipient (str): The recipient's phone number or group ID.
        file_path (str): The path to the file to be sent.
        file_name (str): The name of the file.
        is_group (bool, optional): Whether the recipient is a group. Defaults to False.

    This function uses the Telethon library to create a Telegram client and send the file.
    """
    global api_id, api_hash
    # Define the session file path
    session_filepath = os.path.join(
        DIR, "Executor/ExecutorUtils/NotificationCenter/Telegram/+918618221715.session"
    )

    # Create a Telegram client and send the file
    with TelegramClient(session_filepath, api_id, api_hash) as client:
        client.send_file(recipient, file_path, caption=file_name)


def send_message_to_group(group_id, message, is_group=True):
    """
    Send a message to a specified group via Telegram.

    Args:
        group_id (str): The ID of the group.
        message (str): The message to be sent.
        is_group (bool, optional): Indicates that the recipient is a group. Defaults to True.

    This function uses the Telethon library to create a Telegram client and send the message to the group.
    """
    global api_id, api_hash
    # Define the session file path
    session_filepath = os.path.join(
        DIR, "Executor/ExecutorUtils/NotificationCenter/Telegram/+918618221715.session"
    )

    # Create a Telegram client and send the message
    with TelegramClient(session_filepath, api_id, api_hash) as client:
        client.send_message(group_id, message, parse_mode="md")
