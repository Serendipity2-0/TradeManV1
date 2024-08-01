import os
import sys

DIR = os.getcwd()
sys.path.append(DIR)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()


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
    logger.debug(f"Checking orders for strategy: {strategy_key}")
    logger.debug(f"Strategy data: {strategy_data}")

    strategy_order_ids = set()
    if isinstance(strategy_data, dict):
        trade_state = strategy_data.get("TradeState", {})
        logger.debug(f"Trade state: {trade_state}")
        orders_from_firebase = trade_state.get("orders", [])
        logger.debug(f"Orders from firebase: {orders_from_firebase}")

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
