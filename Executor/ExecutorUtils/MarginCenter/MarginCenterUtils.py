import os
import sys
import datetime as dt
from time import sleep
from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

TRADE_MODE = os.getenv("TRADE_MODE")

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
    get_basket_order_margins,
    fetch_freecash_for_user,
)

logger = LoggerSetup()


def check_margin_required(orders_to_place, user):
    try:
        required_margin = get_basket_order_margins(
            orders_to_place=orders_to_place, user_credentials=user["Broker"]
        )
        account_freecash = fetch_freecash_for_user(user=user)
        if account_freecash < required_margin:
            return False
        else:
            return True
    except Exception as e:
        logger.error(f"Error checking Margin Required {e}")
