"""
This module contains utility functions for NSE strategies that don't interact with the database.
"""

import datetime as dt
import os
import pandas as pd
from typing import List, Dict, Union, Optional, Any
from dotenv import load_dotenv

DIR = os.getcwd()
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

fno_info_path = os.getenv("FNO_INFO_PATH")

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.ExeUtils import holidays
from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import get_single_ltp

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
        order["trade_id"] = f"{order['trade_id']}_{order['signal']}_{order['order_mode']}_{trade_id_suffix}"

    return orders_to_place


def calculate_stoploss(
    ltp: float,
    main_transaction_type: str,
    stoploss_multiplier: Optional[float] = None,
    price_ref: Optional[float] = None
) -> float:
    """
    Calculate stop loss based on transaction type and either multiplier or price reference.

    Args:
        ltp (float): Last traded price.
        main_transaction_type (str): Transaction type ("BUY" or "SELL").
        stoploss_multiplier (Optional[float]): Stop loss multiplier.
        price_ref (Optional[float]): Price reference.

    Returns:
        float: Calculated stop loss price.

    Raises:
        ValueError: If neither stoploss_multiplier nor price_ref is provided.
    """
    if stoploss_multiplier:
        return calculate_multipler_stoploss(main_transaction_type, ltp, stoploss_multiplier)
    elif price_ref:
        return calculate_priceref_stoploss(main_transaction_type, ltp, price_ref)
    else:
        raise ValueError("Invalid stoploss calculation: need either multiplier or price reference")


def calculate_multipler_stoploss(main_transaction_type: str, ltp: float, stoploss_multiplier: float) -> float:
    """
    Calculate stop loss using multiplier method.

    Args:
        main_transaction_type (str): Transaction type ("BUY" or "SELL").
        ltp (float): Last traded price.
        stoploss_multiplier (float): Stop loss multiplier.

    Returns:
        float: Calculated stop loss price.
    """
    if main_transaction_type == "BUY":
        stoploss = round(float(ltp - (ltp * stoploss_multiplier)), 1)
    elif main_transaction_type == "SELL":
        stoploss = round(float(ltp + (ltp * stoploss_multiplier)), 1)
    
    logger.debug(f"stoploss: {stoploss}, ltp: {ltp}, stoploss_multiplier: {stoploss_multiplier}")
    return max(stoploss, 1)


def calculate_priceref_stoploss(main_transaction_type: str, ltp: float, price_ref: float) -> float:
    """
    Calculate stop loss using price reference method.

    Args:
        main_transaction_type (str): Transaction type ("BUY" or "SELL").
        ltp (float): Last traded price.
        price_ref (float): Price reference.

    Returns:
        float: Calculated stop loss price.
    """
    if main_transaction_type == "BUY":
        stoploss = round(float(ltp - price_ref), 1)
    elif main_transaction_type == "SELL":
        stoploss = round(float(ltp + price_ref), 1)

    return max(stoploss, 1)


def calculate_trigger_price(sl_transaction_type: str, stoploss: float) -> float:
    """
    Calculate trigger price based on stop loss.

    Args:
        sl_transaction_type (str): Stop loss transaction type ("BUY" or "SELL").
        stoploss (float): Stop loss price.

    Returns:
        float: Calculated trigger price.
    """
    if sl_transaction_type == "BUY":
        return round(float(stoploss - 1), 1)
    elif sl_transaction_type == "SELL":
        return round(float(stoploss + 1), 1)


def calculate_transaction_type_sl(transaction_type: str) -> str:
    """
    Calculate stop loss transaction type based on main transaction type.

    Args:
        transaction_type (str): Main transaction type ("BUY"/"B" or "SELL"/"S").

    Returns:
        str: Stop loss transaction type.
    """
    if transaction_type in ["BUY", "B"]:
        return "SELL"
    elif transaction_type in ["SELL", "S"]:
        return "BUY"


def calculate_target(option_ltp: float, price_ref: float) -> float:
    """
    Calculate target price.

    Args:
        option_ltp (float): Option last traded price.
        price_ref (float): Price reference.

    Returns:
        float: Calculated target price.
    """
    return option_ltp + (price_ref / 2)


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


def get_token_from_info(base_symbol: str) -> Union[str, int]:
    """
    Get token for a base symbol from fno_info CSV.

    Args:
        base_symbol (str): Base symbol.

    Returns:
        Union[str, int]: Token or error message if not found.
    """
    fno_info_df = pd.read_csv(fno_info_path)
    token = fno_info_df.loc[
        fno_info_df["base_symbol"] == base_symbol, "token"
    ].values
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


def round_strike_prc(ltp: float, base_symbol: str) -> float:
    """
    Round last traded price to nearest strike price.

    Args:
        ltp (float): Last traded price.
        base_symbol (str): Base symbol.

    Returns:
        float: Rounded strike price.
    """
    strike_step = get_strike_step(base_symbol)
    return round(ltp / strike_step) * strike_step


def get_strike_step(base_symbol: str) -> float:
    """
    Get strike step size for a base symbol.

    Args:
        base_symbol (str): Base symbol.

    Returns:
        float: Strike step size.
    """
    strike_step_df = pd.read_csv(fno_info_path)
    return strike_step_df.loc[
        strike_step_df["base_symbol"] == base_symbol, "strike_step_size"
    ].values[0]


def calculate_current_atm_strike_prc(
    base_symbol: str,
    token: Optional[int] = None,
    prediction: Optional[str] = None,
    strike_prc_multiplier: Optional[float] = None,
    strategy_type: Optional[str] = None,
) -> float:
    """
    Calculate current ATM strike price.

    Args:
        base_symbol (str): Base symbol.
        token (Optional[int]): Token.
        prediction (Optional[str]): Market prediction.
        strike_prc_multiplier (Optional[float]): Strike price multiplier.
        strategy_type (Optional[str]): Strategy type.

    Returns:
        float: Calculated ATM strike price.
    """
    if token is None:
        token = int(get_token_from_info(base_symbol))
    
    ltp = get_single_ltp(token)
    base_strike = round_strike_prc(ltp, base_symbol)
    multiplier = get_strike_step(base_symbol)
    
    if strike_prc_multiplier:
        if prediction == "Bearish" and strategy_type == "OB":
            adjusted_multiplier = multiplier * (-strike_prc_multiplier)
        elif prediction == "Bullish" and strategy_type == "OB":
            adjusted_multiplier = multiplier * strike_prc_multiplier
        elif prediction == "Bearish" and strategy_type == "OS":
            adjusted_multiplier = multiplier * strike_prc_multiplier
        elif prediction == "Bullish" and strategy_type == "OS":
            adjusted_multiplier = multiplier * (-strike_prc_multiplier)
        else:
            logger.error("Invalid prediction")
            return base_strike
        return base_strike + adjusted_multiplier
    
    return base_strike


def get_hedge_strikeprc(
    base_symbol: str,
    token: int,
    prediction: str,
    hedge_multiplier: int
) -> float:
    """
    Calculate hedge strike price.

    Args:
        base_symbol (str): Base symbol.
        token (int): Token.
        prediction (str): Market prediction.
        hedge_multiplier (int): Hedge multiplier.

    Returns:
        float: Calculated hedge strike price.
    """
    ltp = get_single_ltp(token)
    strike_prc = round_strike_prc(ltp, base_symbol)
    strike_prc_multiplier = get_strike_step(base_symbol)
    
    bear_strikeprc = strike_prc + (hedge_multiplier * strike_prc_multiplier)
    bull_strikeprc = strike_prc - (hedge_multiplier * strike_prc_multiplier)
    
    return bear_strikeprc if prediction == "Bearish" else bull_strikeprc


def get_square_off_transaction(prediction: str) -> Optional[str]:
    """
    Get square off transaction type based on prediction.

    Args:
        prediction (str): Market prediction.

    Returns:
        Optional[str]: Transaction type or None if invalid.
    """
    if prediction == "Bearish":
        return "BUY"
    elif prediction == "Bullish":
        return "SELL"
    logger.error("Invalid prediction")
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
