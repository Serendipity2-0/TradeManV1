import asyncio
import os
import sys

import pyotp
from thefirstock import thefirstock

DIR = os.getcwd()
sys.path.append(DIR)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()


async def login_in_firstock(user_details):
    """
    Asynchronously logs in to the Firstock platform using the provided user details and returns the session token if successful.

    :param user_details: Dictionary containing user details for login
    :return: The session ID (susertoken) for the user's broker account or None if login fails
    """
    try:
        totp = pyotp.TOTP(user_details["TotpAccess"])
        totp_code = totp.now()

        # Wrap the synchronous login call in an executor to make it non-blocking
        login = await asyncio.to_thread(
            thefirstock.firstock_login,
            userId=user_details["BrokerUsername"],
            password=user_details["BrokerPassword"],
            TOTP=totp_code,
            vendorCode=user_details["ApiSecret"],
            apiKey=user_details["ApiKey"],
        )

        if login.get("data", {}).get("susertoken"):
            session_id = login["data"]["susertoken"]
            logger.info(
                f"Session Id for {user_details['BrokerUsername']}: {session_id}"
            )
            return session_id
        else:
            raise Exception(f"Error fetching login for Firstock: {login}")
    except Exception as e:
        logger.error(f"Error fetching login for Firstock: {e}")
        return None
