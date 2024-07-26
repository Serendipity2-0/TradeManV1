import os
import sys
from dotenv import load_dotenv
import datetime

# Load holdings data
DIR = os.getcwd()
sys.path.append(DIR)
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()
SHORT_MOMENTUM = "SHORT_MOMENTUM"
SHORT_EMABBCONFLUENCE = "SHORT_EMABBCONFLUENCE"
SHORT_MEANREVERSION = "SHORT_MEANREVERSION"
MID_TFMOMENTUM = "MID_TFMOMENTUM"
MID_TFEMA = "MID_TFEMA"
LONG_RATIO = "LONG_RATIO"
LONG_COMBO = "LONG_COMBO"


def calculate_full_trailing_sl(buy_price, stoploss_multiplier, ltp):
    """
    Calculates the full trailing stoploss for a given buy price, stoploss multiplier and ltp.
    """
    try:
        per_change = (ltp - buy_price) / buy_price * 100
        sl = buy_price - (buy_price * stoploss_multiplier / 100)

        if per_change > stoploss_multiplier:
            adjustments = int(per_change // stoploss_multiplier)
            sl += (buy_price * stoploss_multiplier / 100) * adjustments
            sl = round(sl, 1)

        return sl
    except Exception as e:
        logger.error(f"Error in calculate_full_trailing_sl: {e}")
        return None


def calculate_half_trailing_sl(buy_price, stoploss_multiplier, ltp):
    """
    Calculates the half trailing stoploss for a given buy price, stoploss multiplier and ltp.
    """
    try:
        per_change = (ltp - buy_price) / buy_price * 100
        sl = buy_price - (buy_price * stoploss_multiplier / 100)
        if (per_change / 2) // (stoploss_multiplier / 2) > 0:
            sl = sl + (buy_price * (stoploss_multiplier / 2) / 100)
            sl = round(sl, 1)
            return sl
    except Exception as e:
        logger.error(f"Error in calculate_half_trailing_sl: {e}")
        return None


def calculate_fixed_sl(buy_price, stoploss_multiplier, ltp):
    """
    Calculates the fixed stoploss for a given buy price, stoploss multiplier and ltp.
    """
    try:
        sl = buy_price - (buy_price * stoploss_multiplier / 100)
        return sl
    except Exception as e:
        logger.error(f"Error in calculate_fixed_sl: {e}")
        return None


def calculate_sl(setup_name, buy_price, stoploss_multiplier, ltp):
    """
    Calculates the stoploss for a given setup name, buy price, stoploss multiplier and ltp.
    """
    if setup_name == SHORT_MOMENTUM or setup_name == MID_TFMOMENTUM:
        return calculate_full_trailing_sl(buy_price, stoploss_multiplier, ltp)
    if setup_name == SHORT_EMABBCONFLUENCE or setup_name == MID_TFEMA:  # TODO
        return calculate_half_trailing_sl(buy_price, stoploss_multiplier, ltp)
    if setup_name == SHORT_MEANREVERSION:  # TODO:
        return calculate_fixed_sl(buy_price, stoploss_multiplier, ltp)
