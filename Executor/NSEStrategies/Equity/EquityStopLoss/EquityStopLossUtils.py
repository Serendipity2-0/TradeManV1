import os
import sys
from dotenv import load_dotenv
import datetime

# Load holdings data
DIR = os.getcwd()
sys.path.append(DIR)
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

import Executor.ExecutorUtils.ExeUtils as ExeUtils
from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
    fetch_users_for_strategies_from_firebase as fetch_active_users,
)
from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter import (
    fetch_sql_table_from_db as fetch_table_from_db,
)
from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import get_single_ltp

from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import Instrument
from Executor.NSEStrategies.NSEStrategiesUtil import (
    StrategyBase,
    assign_trade_id,
    place_order_single_user,
)
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()
SHORT_EMABBCONFLUENCE = os.getenv("SHORT_EMABBCONFLUENCE")
SHORT_MOMENTUM = os.getenv("SHORT_MOMENTUM")
SHORT_MEANREVERSION = os.getenv("SHORT_MEANREVERSION")
MID_TFMOMENTUM = os.getenv("MID_TFMOMENTUM")
MID_TFEMA = os.getenv("MID_TFEMA")
LONG_RATIO = os.getenv("LONG_RATIO")
LONG_COMBO = os.getenv("LONG_COMBO")


def calculate_full_trailing_sl(buy_price, stoploss_multiplier, ltp):
    """
    Calculates the full trailing stoploss for a given buy price, stoploss multiplier and ltp.
    """
    try:
        per_change = (ltp - buy_price) / buy_price * 100
        sl = buy_price - (buy_price * stoploss_multiplier / 100)
        if (
            per_change // stoploss_multiplier > 0
            and per_change // stoploss_multiplier != 1
        ):
            for interation in range(int(per_change // stoploss_multiplier)):
                sl = sl + (buy_price * stoploss_multiplier / 100)
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
    if setup_name == SHORT_MOMENTUM:
        return calculate_full_trailing_sl(buy_price, stoploss_multiplier, ltp)
    if setup_name == SHORT_EMABBCONFLUENCE:  # TODO
        return calculate_half_trailing_sl(buy_price, stoploss_multiplier, ltp)
    if setup_name == SHORT_MEANREVERSION:  # TODO:
        return calculate_fixed_sl(buy_price, stoploss_multiplier, ltp)
