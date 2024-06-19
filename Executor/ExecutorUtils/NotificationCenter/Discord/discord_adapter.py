import requests
import os, sys
from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()


def discord_bot(message, strategy):
    """
    Send a message to a Discord channel using a bot.

    This function sends a message to a Discord channel specified by the strategy name.
    It retrieves the bot token and channel ID from environment variables.

    Args:
        message (str): The message to be sent to the Discord channel.
        strategy (str): The strategy name, used to determine the specific Discord channel.

    Returns:
        response: The response object returned by the requests.post() method.

    Raises:
        ValueError: If the request to Discord returns a status code other than 200.

    Environment Variables:
        discord_bot_token (str): The token for the Discord bot.
        {strategy.lower()}_channel_id (str): The channel ID for the specified strategy.
    """
    try:
        token = os.getenv("discord_bot_token")
        channel_id = os.getenv(f"{strategy.lower()}_channel_id")

        url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
        headers = {
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
        }
        data = {"content": message}

        response = requests.post(url, headers=headers, json=data)

        if response.status_code != 200:
            raise ValueError(
                f"Request to discord returned an error {response.status_code}, the response is:\n{response.text}"
            )
        return response
    except Exception as e:
        logger.error(f"Error in sending message to Discord: {e}")


def discord_admin_bot(message):
    """
    Send a message to the admin Discord channel using a bot.

    This function sends a message to a predefined admin Discord channel.
    It retrieves the bot token from environment variables and uses a hardcoded channel ID.

    Args:
        message (str): The message to be sent to the Discord admin channel.

    Returns:
        response: The response object returned by the requests.post() method.

    Raises:
        ValueError: If the request to Discord returns a status code other than 200.

    Environment Variables:
        discord_bot_token (str): The token for the Discord bot.
    """
    token = os.getenv("discord_bot_token")
    channel_id = "1169540251325313034"

    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    headers = {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
    }
    data = {"content": message}

    response = requests.post(url, headers=headers, json=data)

    if response.status_code != 200:
        raise ValueError(
            f"Request to discord returned an error {response.status_code}, the response is:\n{response.text}"
        )
    return response
