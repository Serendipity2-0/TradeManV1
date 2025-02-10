"""
Strategy-related utility functions.
"""

import os
from typing import Dict, List, Optional
from dotenv import load_dotenv
from fastapi import HTTPException
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import (
    fetch_collection_data_firebase,
    update_fields_firebase,
)
from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import Instrument
from Executor.NSEStrategies.NSEStrategiesUtil import (
    update_qty_user_firebase,
    fetch_qty_amplifier,
    fetch_strategy_amplifier,
    get_order_mode,
    get_transaction_type,
)

DIR_PATH = os.getcwd()
ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

logger = LoggerSetup()

STRATEGIES_FB_COLLECTION = os.getenv("FIREBASE_STRATEGY_COLLECTION")
MARKET_INFO_FB_COLLECTION = os.getenv("MARKET_INFO_FB_COLLECTION")

def get_strategy_params(strategy_name: str) -> Dict:
    """
    Get parameters for a specific strategy.

    Args:
        strategy_name (str): The name of the strategy.

    Returns:
        Dict: The strategy parameters.
    """
    try:
        return fetch_collection_data_firebase(STRATEGIES_FB_COLLECTION, strategy_name)
    except Exception as e:
        logger.error(f"Error getting strategy parameters: {e}")
        raise

def modify_strategy_params(strategy_name: str, section: str, updated_params: Dict) -> None:
    """
    Modify parameters for a specific section of a strategy.

    Args:
        strategy_name (str): The name of the strategy.
        section (str): The section to update.
        updated_params (Dict): The updated parameters.
    """
    try:
        update_fields_firebase(STRATEGIES_FB_COLLECTION, strategy_name, updated_params, section)
    except Exception as e:
        logger.error(f"Error modifying strategy parameters: {e}")
        raise

def update_market_info_params(updated_market_info: Dict) -> None:
    """
    Update market info parameters.

    Args:
        updated_market_info (Dict): The updated market info parameters.
    """
    try:
        update_fields_firebase(MARKET_INFO_FB_COLLECTION, None, updated_market_info)
    except Exception as e:
        logger.error(f"Error updating market info parameters: {e}")
        raise

def get_market_info_params() -> Dict:
    """
    Get current market info parameters.

    Returns:
        Dict: The market info parameters.
    """
    try:
        return fetch_collection_data_firebase(MARKET_INFO_FB_COLLECTION)
    except Exception as e:
        logger.error(f"Error getting market info parameters: {e}")
        raise

def update_strategy_qty_amplifier(strategy: str, amplifier: float) -> None:
    """
    Update quantity amplifier for a strategy.

    Args:
        strategy (str): The strategy name or 'all'.
        amplifier (float): The new amplifier value.
    """
    try:
        if strategy == "all":
            strategies = fetch_collection_data_firebase(STRATEGIES_FB_COLLECTION)
            for strategy_name in strategies:
                update_fields_firebase(
                    STRATEGIES_FB_COLLECTION,
                    strategy_name,
                    {"StrategyQtyAmplifier": amplifier}
                )
        else:
            update_fields_firebase(
                STRATEGIES_FB_COLLECTION,
                strategy,
                {"StrategyQtyAmplifier": amplifier}
            )
    except Exception as e:
        logger.error(f"Error updating strategy quantity amplifier: {e}")
        raise

def get_user_risk_params(strategy: str, trader_numbers: Optional[List[str]] = None) -> Dict:
    """
    Get risk parameters for users.

    Args:
        strategy (str): The strategy name.
        trader_numbers (Optional[List[str]]): List of trader numbers.

    Returns:
        Dict: The risk parameters.
    """
    try:
        strategy_data = fetch_collection_data_firebase(STRATEGIES_FB_COLLECTION, strategy)
        if not strategy_data:
            raise HTTPException(status_code=404, detail=f"Strategy {strategy} not found")
        
        risk_params = {}
        if trader_numbers:
            for tr_no in trader_numbers:
                user_data = fetch_collection_data_firebase(os.getenv("FIREBASE_USER_COLLECTION"), tr_no)
                if user_data and "Strategies" in user_data:
                    risk_params[tr_no] = user_data["Strategies"].get(strategy, {}).get("RiskPercentage")
        return risk_params
    except Exception as e:
        logger.error(f"Error getting user risk parameters: {e}")
        raise

def update_user_risk_params(strategy: str, trader_numbers: List[str], risk_percentage: float) -> Dict:
    """
    Update risk parameters for users.

    Args:
        strategy (str): The strategy name.
        trader_numbers (List[str]): List of trader numbers.
        risk_percentage (float): The new risk percentage.

    Returns:
        Dict: Status message.
    """
    try:
        for tr_no in trader_numbers:
            update_fields_firebase(
                os.getenv("FIREBASE_USER_COLLECTION"),
                tr_no,
                {"RiskPercentage": risk_percentage},
                f"Strategies/{strategy}"
            )
        return {"message": "Risk parameters updated successfully"}
    except Exception as e:
        logger.error(f"Error updating user risk parameters: {e}")
        raise

def get_strategy_list() -> List[str]:
    """
    Get list of strategies.

    Returns:
        List[str]: List of strategy names.
    """
    try:
        strategies = fetch_collection_data_firebase(STRATEGIES_FB_COLLECTION)
        return list(strategies.keys())
    except Exception as e:
        logger.error(f"Error getting strategy list: {e}")
        raise

def get_complete_strategy_list() -> List[str]:
    """
    Get complete list of strategies.

    Returns:
        List[str]: Complete list of strategy names.
    """
    try:
        strategies = fetch_collection_data_firebase(STRATEGIES_FB_COLLECTION)
        return list(strategies.keys())
    except Exception as e:
        logger.error(f"Error getting complete strategy list: {e}")
        raise

def fetch_users_for_strategy(strategy: str) -> List[Dict]:
    """
    Get users for a strategy.

    Args:
        strategy (str): The strategy name.

    Returns:
        List[Dict]: List of users.
    """
    try:
        users = fetch_collection_data_firebase(os.getenv("FIREBASE_USER_COLLECTION"))
        strategy_users = []
        for tr_no, user_data in users.items():
            if user_data.get("Active", False) and "Strategies" in user_data:
                if strategy in user_data["Strategies"].get("Equity", {}) or \
                   strategy in user_data["Strategies"].get("Derivatives", {}):
                    strategy_users.append({
                        "tr_no": tr_no,
                        "name": user_data.get("Profile", {}).get("Name", ""),
                        "active": True
                    })
        return strategy_users
    except Exception as e:
        logger.error(f"Error fetching users for strategy: {e}")
        raise

def get_order_modes() -> List[str]:
    """
    Get available order modes.

    Returns:
        List[str]: List of order modes.
    """
    return ["Complete", "Repair"]

def get_qty_calculation_mode() -> List[str]:
    """
    Get available quantity calculation modes.

    Returns:
        List[str]: List of quantity calculation modes.
    """
    return ["Auto", "Manual"]

def fetch_today_order(strategy_name: str) -> List[Dict]:
    """
    Get today's orders for a strategy.

    Args:
        strategy_name (str): The strategy name.

    Returns:
        List[Dict]: List of orders.
    """
    try:
        strategy_data = fetch_collection_data_firebase(STRATEGIES_FB_COLLECTION, strategy_name)
        return strategy_data.get("TodayOrders", [])
    except Exception as e:
        logger.error(f"Error fetching today's orders: {e}")
        raise

def fetch_list_of_nse_instruments() -> List[str]:
    """
    Get list of NSE instruments.

    Returns:
        List[str]: List of instruments.
    """
    try:
        return Instrument().fetch_complete_instruments_by_segment("NSE")
    except Exception as e:
        logger.error(f"Error fetching NSE instruments: {e}")
        raise

def fetch_tradingsymbol_by_name(name: str) -> str:
    """
    Get trading symbol by name.

    Args:
        name (str): The instrument name.

    Returns:
        str: The trading symbol.
    """
    try:
        return Instrument().fetch_trading_symbol_by_name(name)
    except Exception as e:
        logger.error(f"Error fetching trading symbol: {e}")
        raise

def get_strategies_for_user(trader_number: str) -> Dict[str, List[str]]:
    """
    Get all strategies assigned to a user.

    Args:
        trader_number (str): The trader number of the user.

    Returns:
        Dict[str, List[str]]: Dictionary containing lists of strategies by category (Equity, Derivatives, etc.)
    """
    try:
        user_data = fetch_collection_data_firebase(os.getenv("FIREBASE_USER_COLLECTION"), trader_number)
        if not user_data:
            raise HTTPException(status_code=404, detail=f"User {trader_number} not found")
        
        strategies = user_data.get("Strategies", {})
        return {
            "Equity": list(strategies.get("Equity", {}).keys()),
            "Derivatives": list(strategies.get("Derivatives", {}).keys()),
            "Debt": list(strategies.get("Debt", {}).keys())
        }
    except Exception as e:
        logger.error(f"Error getting strategies for user: {e}")
        raise
