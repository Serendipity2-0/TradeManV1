"""
This module contains trade-related utility functions for NSE strategies.
"""

import datetime as dt
import os
from typing import Any, Dict, List, Optional, Union
from dotenv import load_dotenv

DIR = os.getcwd()
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.ExeUtils import holidays
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()

def get_previous_dates(num_dates: int) -> List[str]:
    """
    Get previous business dates excluding weekends and holidays.

    Args:
        num_dates (int): Number of previous dates to retrieve.

    Returns:
        List[str]: List of previous business dates in YYYY-MM-DD format.
    """
    dates = []
    current_date = dt.date.today()

    while len(dates) < num_dates:
        current_date -= dt.timedelta(days=1)
        if current_date.weekday() >= 5 or current_date in holidays:
            continue
        dates.append(current_date.strftime("%Y-%m-%d"))

    return dates

def assign_trade_id(orders_to_place: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Assign trade IDs to orders based on order mode and signal.

    Args:
        orders_to_place (List[Dict[str, Any]]): List of orders to process.

    Returns:
        List[Dict[str, Any]]: Orders with updated trade IDs.
    """
    for order in orders_to_place:
        # Determine trade_id suffix
        if order["order_mode"] in ["Main", "HedgeEntry", "MainEntry"]:
            trade_id_suffix = "EN"
        elif order["order_mode"] in ["SL", "Trailing", "HedgeExit", "MainExit"]:
            trade_id_suffix = "EX"
        else:
            trade_id_suffix = "unknown"

        # Update order mode
        if order["order_mode"] in ["HedgeEntry", "HedgeExit"]:
            order["order_mode"] = "HO"
        elif order["order_mode"] in ["Main", "MainEntry", "MainExit"]:
            order["order_mode"] = "MO"
        elif order["order_mode"] in ["SL", "Trailing"]:
            order["order_mode"] = "SL"

        # Update signal
        if order["signal"] == "Long":
            order["signal"] = "LG"
        elif order["signal"] == "Short":
            order["signal"] = "SH"

        # Create final trade_id
        order["trade_id"] = (
            f"{order['trade_id']}_{order['signal']}_{order['order_mode']}_{trade_id_suffix}"
        )

    return orders_to_place

def get_signal_from_trade_id(trade_id: str) -> Optional[str]:
    """
    Extract signal type from trade ID.

    Args:
        trade_id (str): Trade ID.

    Returns:
        Optional[str]: "Long", "Short", or None if invalid.
    """
    signal = trade_id.split("_")[1]
    if signal == "SH":
        return "Short"
    elif signal == "LG":
        return "Long"
    return None

def get_order_mode(trade_id: str) -> Optional[str]:
    """
    Extract order mode from trade ID.

    Args:
        trade_id (str): Trade ID.

    Returns:
        Optional[str]: Order mode or None if not found.
    """
    if "MO_EN" in trade_id:
        return "MainEntry"
    elif "MO_EX" in trade_id:
        return "MainExit"
    elif "HO_EN" in trade_id:
        return "HedgeEntry"
    elif "HO_EX" in trade_id:
        return "HedgeExit"
    return None

def get_transaction_type(trade_id: str) -> str:
    """
    Extract transaction type from trade ID.

    Args:
        trade_id (str): Trade ID.

    Returns:
        str: Transaction type or "unknown" if not recognized.
    """
    if "LG_MO_EN" in trade_id:
        return "BUY"
    elif "LG_MO_EX" in trade_id:
        return "SELL"
    elif "SH_MO_EN" in trade_id:
        return "SELL"
    elif "SH_MO_EX" in trade_id:
        return "BUY"
    elif "HO_EN" in trade_id:
        return "BUY"
    elif "HO_EX" in trade_id:
        return "SELL"
    return "unknown"

def get_transaction_type_from_prediction(prediction: str) -> Optional[str]:
    """
    Get transaction type based on prediction.

    Args:
        prediction (str): Market prediction.

    Returns:
        Optional[str]: Transaction type or None if invalid.
    """
    if prediction == "Bearish":
        return "SELL"
    elif prediction == "Bullish":
        return "BUY"
    logger.error("Invalid option mode")
    return None

def get_option_type(prediction: str, strategy_option_mode: str) -> Optional[str]:
    """
    Get option type based on prediction and strategy mode.

    Args:
        prediction (str): Market prediction.
        strategy_option_mode (str): Strategy option mode.

    Returns:
        Optional[str]: Option type or None if invalid.
    """
    if strategy_option_mode == "OS":
        return "CE" if prediction == "Bearish" else "PE"
    elif strategy_option_mode == "OB":
        return "CE" if prediction == "Bullish" else "PE"
    logger.error("Invalid option mode")
    return None

def get_hedge_option_type(prediction: str) -> Optional[str]:
    """
    Get hedge option type based on prediction.

    Args:
        prediction (str): Market prediction.

    Returns:
        Optional[str]: Option type or None if invalid.
    """
    if prediction == "Bearish":
        return "CE"
    elif prediction == "Bullish":
        return "PE"
    logger.error("Invalid option mode")
    return None
