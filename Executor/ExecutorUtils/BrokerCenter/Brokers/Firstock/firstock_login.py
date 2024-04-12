from thefirstock import thefirstock
import pyotp
import os,sys

DIR = os.getcwd()
sys.path.append(DIR) 

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()

def login_in_firstock(user_details):
    try:
        totp = pyotp.TOTP(user_details["TotpAccess"])
        totp = totp.now()
        login = thefirstock.firstock_login(
            userId = user_details["BrokerUsername"],
            password = user_details["BrokerPassword"],
            TOTP= totp,
            vendorCode= user_details["BrokerVendorCode"],
            apiKey= user_details["ApiKey"],
        )
        logger.info(f"Session Id for {user_details['BrokerUsername']}: {login.get('data', {}).get('susertoken')}")
        return login.get('data', {}).get('susertoken')
    except Exception as e:
        logger.error(f"Error fetching login for Firstock: {e}")
        return None

