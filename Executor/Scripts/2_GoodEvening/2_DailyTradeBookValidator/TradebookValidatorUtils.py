import os
import sys
from datetime import datetime
from dotenv import load_dotenv


DIR = os.getcwd()
sys.path.append(DIR)

ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()
from Executor.ExecutorUtils.NotificationCenter.Telegram.telegram_adapter import (
    send_message_to_group,
)

ERROR_GROUP_ID = os.getenv("ERROR_CHAT_ID")


def check_strategy_path(asset_class, term, strategy_key, strategy_data, order_id):
    """
    Helper function to check a strategy for the given order_id.

    :param asset_class: The asset class (e.g., "Equity" or "Derivatives")
    :param term: The term (e.g., "MidTerm") or None for Derivatives
    :param strategy_key: The strategy key
    :param strategy_data: The strategy data dictionary
    :param order_id: The order ID to search for
    :return: The update path if found, None otherwise
    """
    if isinstance(strategy_data, dict):
        trade_state = strategy_data.get("TradeState", {})
        orders_from_firebase = trade_state.get("orders", [])

        if not orders_from_firebase:
            log_message = f"No orders found for asset class: {asset_class}"
            log_message += f", term: {term}" if term else ""
            log_message += f", strategy: {strategy_key}"
            logger.info(log_message)
            return None

        for i, order in enumerate(orders_from_firebase):
            if order is not None and str(order.get("order_id")) == order_id:
                path = f"Strategies/{asset_class}"
                path += f"/{term}" if term else ""
                path += f"/{strategy_key}/TradeState/orders/{i}"
                return path

    return None


def check_strategy_orders(user, asset_class, term, strategy_key, strategy_data, today):
    """
    Helper function to check orders for a specific strategy.

    :param user: A dictionary containing user details.
    :param asset_class: The asset class (e.g., "Equity" or "Derivatives")
    :param term: The term (e.g., "MidTerm") or None for Derivatives
    :param strategy_key: The strategy key
    :param strategy_data: The strategy data dictionary
    :param today: Today's date string
    :return: A set of order IDs for the strategy
    """

    strategy_order_ids = set()
    if isinstance(strategy_data, dict):
        trade_state = strategy_data.get("TradeState", {})
        orders_from_firebase = trade_state.get("orders", [])
        logger.debug(f"len(orders_from_firebase): {len(orders_from_firebase)}")

        if not orders_from_firebase:
            log_message = (
                f"No orders today for user: {user['Broker']['BrokerUsername']}"
            )
            log_message += f" for asset class: {asset_class}"
            log_message += f", term: {term}" if term else ""
            log_message += f", strategy: {strategy_key}"
            return strategy_order_ids

        for order in orders_from_firebase:
            if order is not None:
                order_id_str = str(order["order_id"])
                order_date_timestamp = order.get("time_stamp", "").split(" ")[0]
                logger.debug(
                    f"Checking order: {order_id_str}, date: {order_date_timestamp}, today: {today}"
                )
                if order_date_timestamp == today:
                    strategy_order_ids.add(order_id_str)
                    logger.debug(
                        f"Added order ID: {order_id_str} for strategy: {strategy_key}"
                    )

    logger.debug(f"Found {len(strategy_order_ids)} orders for strategy: {strategy_key}")
    return strategy_order_ids


def verify_firebase_orders(user):
    today = datetime.now().strftime("%Y-%m-%d")
    for asset_class in user["Strategies"]:
        if asset_class == "Equity":
            for term in user["Strategies"][asset_class]:
                for strategy in user["Strategies"][asset_class][term]:
                    strategy_data = user["Strategies"][asset_class][term][strategy]
                    pending_orders = check_strategy_orders(
                        user, asset_class, term, strategy, strategy_data, today
                    )
                    if pending_orders:
                        message = (
                            f"Orders with avg_prc None found for strategy: {strategy}"
                        )
                        send_message_to_group(ERROR_GROUP_ID, message)
                        logger.error(
                            f"Orders with avg_prc None found for strategy: {strategy}"
                        )
        if asset_class == "Derivatives":
            for strategy in user["Strategies"][asset_class]:
                strategy_data = user["Strategies"][asset_class][strategy]
                pending_orders = check_strategy_orders(
                    user, asset_class, None, strategy, strategy_data, today
                )
                if pending_orders:
                    message = f"Orders with avg_prc None found for strategy: {strategy}"
                    send_message_to_group(ERROR_GROUP_ID, message)
                    logger.error(
                        f"Orders with avg_prc None found for strategy: {strategy}"
                    )
