from thefirstock import thefirstock
import pyotp
import os, sys

DIR = os.getcwd()
sys.path.append(DIR)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()


def login_in_firstock(user_details):
    """
    The function `login_in_firstock` attempts to log in to the Firstock platform using the provided user
    details and returns the session token if successful.

    :param user_details: The `login_in_firstock` function takes a dictionary `user_details` as input,
    which should contain the following key-value pairs:
    :return: The function `login_in_firstock` is returning the session ID for the user's broker account.
    It retrieves the session ID after successfully logging in to the Firstock platform using the
    provided user details such as broker username, password, TOTP, vendor code, and API key. If the
    login is successful, it returns the session ID (susertoken) for the user's broker account. If
    """
    try:
        totp = pyotp.TOTP(user_details["TotpAccess"])
        totp = totp.now()
        login = thefirstock.firstock_login(
            userId=user_details["BrokerUsername"],
            password=user_details["BrokerPassword"],
            TOTP=totp,
            vendorCode=user_details["ApiSecret"],
            apiKey=user_details["ApiKey"],
        )
        if login.get("data", {}).get("susertoken"):
            logger.info(
                f"Session Id for {user_details['BrokerUsername']}: {login.get('data', {}).get('susertoken')}"
            )
            return login.get("data", {}).get("susertoken")
        else:
            raise Exception(f"Error fetching login for Firstock: {login}")
    except Exception as e:
        raise Exception(f"Error fetching login for Firstock: {e}")
