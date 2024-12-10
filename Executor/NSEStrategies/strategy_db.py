"""
This module handles all database interactions for NSE strategies.
"""

import os
import re
from dotenv import load_dotenv
from typing import Optional, List, Dict, Any

DIR = os.getcwd()
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

CLIENTS_USER_DB = os.getenv("MONGO_USER_COLLECTION", "trademan_clients")
STRATEGIES_DB = os.getenv("MONGO_STRATEGY_COLLECTION", "strategies")

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.ExeDBUtils.MongoUtils.exemongo_adapter import (
    fetch_collection_data_mongodb,
    update_fields_mongodb,
)
from .strategy_models import StrategyBase

logger = LoggerSetup()


def load_strategy_from_db(strategy_name: str) -> Dict[str, Any]:
    """
    Load strategy data from MongoDB.

    Args:
        strategy_name (str): The name of the strategy.

    Returns:
        dict: Strategy data from MongoDB.

    Raises:
        ValueError: If strategy not found.
    """
    data = fetch_collection_data_mongodb(STRATEGIES_DB)
    if data and strategy_name in data:
        return data[strategy_name]
    raise ValueError(f"No data found for strategy {strategy_name}")


def fetch_strategy_users(strategy_name: str, asset_segment: str, asset_term: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch users associated with a strategy from MongoDB.

    Args:
        strategy_name (str): The name of the strategy.
        asset_segment (str): The asset segment (e.g., "Equity", "Derivatives").
        asset_term (Optional[str]): The asset term (e.g., "Mid Term").

    Returns:
        List[Dict[str, Any]]: List of users associated with the strategy.
    """
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import fetch_active_users

    try:
        active_users = fetch_active_users()
        strategy_users = []
        for user in active_users:
            path = user["Strategies"]
            if asset_segment is not None:
                path = path.get(asset_segment, {})
            if asset_term is not None:
                path = path.get(asset_term, {})
            if strategy_name in path:
                strategy_users.append(user)
        return strategy_users
    except Exception as e:
        logger.error(f"Error fetching strategy users: {e}")
        return []


def update_qty_user_mongodb(
    strategy_name: str,
    avg_sl_points_or_ltp: float,
    lot_size: Optional[int] = None,
    asset_segment: Optional[str] = None,
    asset_term: Optional[str] = None,
    qty_amplifier: Optional[float] = None,
    strategy_amplifier: Optional[float] = None,
    num_stocks: Optional[int] = None,
) -> None:
    """
    Update quantity for users associated with a strategy in MongoDB.

    Args:
        strategy_name (str): The name of the strategy.
        avg_sl_points_or_ltp (float): Average stop loss points or last traded price.
        lot_size (Optional[int]): Lot size for derivatives.
        asset_segment (Optional[str]): Asset segment (e.g., "Equity", "Derivatives").
        asset_term (Optional[str]): Asset term (e.g., "Mid Term").
        qty_amplifier (Optional[float]): Quantity amplifier.
        strategy_amplifier (Optional[float]): Strategy amplifier.
        num_stocks (Optional[int]): Number of stocks.
    """
    from Executor.ExecutorUtils.OrderCenter.OrderCenterUtils import (
        calculate_qty_for_derivatives,
        calculate_qty_for_equity,
    )

    try:
        strategy_users = fetch_strategy_users(strategy_name, asset_segment, asset_term)

        for user in strategy_users:
            strategies = user["Strategies"]
            if asset_segment == "Equity":
                equity_free_cash = user["Accounts"]["Equity"]["Equity_FreeCash"]
                term_data = strategies["Equity"].get(asset_term, {})
                term_allocation = term_data.get("AllocationPercent", 0) / 100
                term_free_cash = equity_free_cash * term_allocation

                for strat, strat_data in term_data.items():
                    if isinstance(strat_data, dict) and "AllocationPercent" in strat_data:
                        if strat == strategy_name:
                            strat_allocation = strat_data["AllocationPercent"] / 100
                            strat_free_cash = term_free_cash * strat_allocation
                            if num_stocks is not None:
                                strat_free_cash = strat_free_cash / num_stocks
                            qty = calculate_qty_for_equity(
                                strat_free_cash, avg_sl_points_or_ltp
                            )

                            # Update the quantity in MongoDB
                            update_fields_mongodb(
                                CLIENTS_USER_DB,
                                user["document_id"],
                                {f"Strategies.Equity.{asset_term}.{strategy_name}.Qty": qty}
                            )
                            logger.info(f"Updated quantity for {strat}: {qty}")
                            break

            elif asset_segment == "Derivatives":
                derivative_free_cash = user["Accounts"]["Derivatives"]["Derivatives_FreeCash"]
                asset_data = strategies["Derivatives"]
                if strategy_name in asset_data:
                    asset_free_cash = derivative_free_cash * (
                        asset_data[strategy_name].get("AllocationPercent", 0) / 100
                    )
                    qty = calculate_qty_for_derivatives(
                        asset_free_cash,
                        asset_data[strategy_name]["RiskPerTrade"],
                        avg_sl_points_or_ltp,
                        lot_size,
                        qty_amplifier,
                        strategy_amplifier,
                    )

                    # Update the quantity in MongoDB
                    update_fields_mongodb(
                        CLIENTS_USER_DB,
                        user["document_id"],
                        {f"Strategies.Derivatives.{strategy_name}.Qty": qty}
                    )
                    logger.info(f"Updated quantity for {strategy_name}: {qty}")

    except Exception as e:
        logger.error(f"Error updating qty for user: {e}")


def update_signal_mongodb(strategy_name: str, signal: Dict[str, Any], trade_id: Optional[str] = None) -> None:
    """
    Update signal for a strategy in MongoDB.

    Args:
        strategy_name (str): The name of the strategy.
        signal (Dict[str, Any]): The signal data to update.
        trade_id (Optional[str]): The trade ID.
    """
    trade = signal["TradeId"].split("_")[3]
    trade_no = signal["TradeId"].split("_")[0]
    trade_prefix = "entry" if trade == "EN" else "exit" if trade == "EX" else None
    
    if not trade_prefix:
        logger.error("Invalid trade")
        return

    trade = f"{trade_no}_{trade_prefix}"
    
    # Update the signal in MongoDB
    update_fields_mongodb(
        STRATEGIES_DB,
        strategy_name,
        {f"TodayOrders.{trade}": signal}
    )

    if trade_id:
        update_next_trade_id_mongodb(strategy_name, trade_id)
    else:
        update_next_trade_id_mongodb(strategy_name, signal["TradeId"])


def update_next_trade_id_mongodb(strategy_name: str, trade_id: str) -> None:
    """
    Update next trade ID for a strategy in MongoDB.

    Args:
        strategy_name (str): The name of the strategy.
        trade_id (str): The current trade ID.
    """
    numeric_digits = re.findall(r"\d+", trade_id)
    if numeric_digits:
        next_trade_id = str(int(numeric_digits[0]) + 1)
        trade_id = trade_id.replace(numeric_digits[0], next_trade_id)

    update_fields_mongodb(
        STRATEGIES_DB,
        strategy_name,
        {"NextTradeId": trade_id}
    )


def get_strategy_name_from_trade_id(trade_id: str) -> Optional[str]:
    """
    Get strategy name from trade ID using MongoDB.

    Args:
        trade_id (str): The trade ID.

    Returns:
        Optional[str]: The strategy name if found, None otherwise.
    """
    strategy_prefix = trade_id[:2]
    strategies = fetch_collection_data_mongodb(STRATEGIES_DB)
    if strategies:
        for strategy, strategy_details in strategies.items():
            if strategy_details.get("StrategyPrefix") == strategy_prefix:
                return strategy
    return None


def fetch_qty_amplifier(strategy_name: str, strategy_type: str) -> float:
    """
    Fetch quantity amplifier from MongoDB.

    Args:
        strategy_name (str): The name of the strategy.
        strategy_type (str): The strategy type ("OS", "OB", or "Equity").

    Returns:
        float: The quantity amplifier (defaults to 1).
    """
    try:
        strategy_data = fetch_collection_data_mongodb(STRATEGIES_DB)
        if strategy_data and strategy_name in strategy_data:
            strategy_info = strategy_data[strategy_name]
            if strategy_type == "OS":
                return strategy_info.get("MarketInfoParams", {}).get("OSQtyAmplifier", 1)
            elif strategy_type == "OB":
                return strategy_info.get("MarketInfoParams", {}).get("OBQtyAmplifier", 1)
            elif strategy_type == "Equity":
                return strategy_info.get("MarketInfoParams", {}).get("EquityQtyAmplifier", 1)
        return 1
    except Exception as e:
        logger.error(f"Error fetching qty amplifier for strategy {strategy_name}: {e}")
        return 1


def fetch_strategy_amplifier(strategy_name: str) -> float:
    """
    Fetch strategy amplifier from MongoDB.

    Args:
        strategy_name (str): The name of the strategy.

    Returns:
        float: The strategy amplifier (defaults to 1).
    """
    try:
        strategy_data = fetch_collection_data_mongodb(STRATEGIES_DB)
        if strategy_data and strategy_name in strategy_data:
            return strategy_data[strategy_name].get("MarketInfoParams", {}).get("StrategyQtyAmplifier", 1)
        return 1
    except Exception as e:
        logger.error(f"Error fetching strategy amplifier for strategy {strategy_name}: {e}")
        return 1
