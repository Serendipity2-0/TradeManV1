"""
This module contains core strategy utility functions for NSE strategies.
Handles expiry index determination and token information.
"""

import datetime as dt
import os
from typing import Union, Optional, Dict, List, Any
import pandas as pd
from dotenv import load_dotenv

DIR = os.getcwd()
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

fno_info_path = os.getenv("FNO_INFO_PATH")

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from .trade_utils import (
    get_previous_dates,
    assign_trade_id,
    get_signal_from_trade_id,
    get_order_mode,
    get_transaction_type,
    get_transaction_type_from_prediction,
    get_option_type,
    get_hedge_option_type,
)
from .price_utils import (
    calculate_stoploss,
    calculate_multipler_stoploss,
    calculate_priceref_stoploss,
    calculate_trigger_price,
    calculate_transaction_type_sl,
    calculate_target,
    round_strike_prc,
    get_strike_step,
    calculate_current_atm_strike_prc,
    get_hedge_strikeprc,
    get_square_off_transaction,
)

logger = LoggerSetup()

def get_token_from_info(base_symbol: str) -> Union[str, int]:
    """
    Get token for a base symbol from fno_info CSV.

    Args:
        base_symbol (str): Base symbol.

    Returns:
        Union[str, int]: Token or error message if not found.
    """
    fno_info_df = pd.read_csv(fno_info_path)
    token = fno_info_df.loc[fno_info_df["base_symbol"] == base_symbol, "token"].values
    if len(token) == 0:
        return f"{base_symbol} not found"
    return token[0]

def determine_expiry_index() -> tuple:
    """
    Determine expiry index based on current day.

    Returns:
        tuple: (index name, token).
    """
    day = dt.datetime.today().weekday()
    if day == 0:  # Monday
        return "MIDCPNIFTY", "288009"
    elif day == 1:  # Tuesday
        return "FINNIFTY", "257801"
    elif day == 2:  # Wednesday
        return "BANKNIFTY", "260105"
    elif day == 3:  # Thursday
        return "NIFTY", "256265"
    elif day == 4:  # Friday
        return "SENSEX", "265"
    elif day in [5, 6]:  # Weekend
        return "MIDCPNIFTY", "288009"
    return "No expiry today", ""

# Re-export commonly used functions from trade_utils and price_utils
__all__ = [
    # From trade_utils
    'get_previous_dates',
    'assign_trade_id',
    'get_signal_from_trade_id',
    'get_order_mode',
    'get_transaction_type',
    'get_transaction_type_from_prediction',
    'get_option_type',
    'get_hedge_option_type',
    
    # From price_utils
    'calculate_stoploss',
    'calculate_multipler_stoploss',
    'calculate_priceref_stoploss',
    'calculate_trigger_price',
    'calculate_transaction_type_sl',
    'calculate_target',
    'round_strike_prc',
    'get_strike_step',
    'calculate_current_atm_strike_prc',
    'get_hedge_strikeprc',
    'get_square_off_transaction',
    
    # From this module
    'get_token_from_info',
    'determine_expiry_index',
]
