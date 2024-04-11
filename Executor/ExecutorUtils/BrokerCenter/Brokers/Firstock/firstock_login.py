from thefirstock import thefirstock

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()


def login_in_firstock(user_details):
    try:
        login = thefirstock.firstock_login(
            userId = user_details["BrokerUsername"],
            password = user_details["BrokerPassword"],
            TOTP= user_details["TotpAccess"],
            vendorCode= user_details["BrokerVendorCode"],
            apiKey= user_details["BrokerApiKey"],
        )
        logger.info(f"Session Id for {user_details['BrokerUsername']}: {login.data['susertoken']}")
        return login.data["susertoken"]
    except Exception as e:
        logger.error(f"Error fetching login for Firstock: {e}")
        return None

