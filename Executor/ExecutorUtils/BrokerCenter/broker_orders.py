"""
This module handles all broker order-related operations.
"""

import os
import sys
import traceback
from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

ZERODHA = os.getenv("ZERODHA_BROKER")
ALICEBLUE = os.getenv("ALICEBLUE_BROKER")
FIRSTOCK = os.getenv("FIRSTOCK_BROKER")

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
import Executor.ExecutorUtils.BrokerCenter.Brokers.AliceBlue.alice_adapter as alice_adapter
import Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter as zerodha_adapter
import Executor.ExecutorUtils.BrokerCenter.Brokers.Firstock.firstock_adapter as firstock_adapter

logger = LoggerSetup()

async def place_order_for_brokers(order_details, user_credentials):
    """
    Places an order for a given broker.

    Args:
        order_details (dict): Details of the order to be placed.
        user_credentials (dict): Credentials of the user placing the order.

    Returns:
        dict: Response from the broker API.
    """
    if order_details["broker"] == ZERODHA:
        return await zerodha_adapter.kite_place_orders_for_users(
            order_details, user_credentials
        )
    elif order_details["broker"] == ALICEBLUE:
        return await alice_adapter.ant_place_orders_for_users(
            order_details, user_credentials
        )
    elif order_details["broker"] == FIRSTOCK:
        return await firstock_adapter.firstock_place_orders_for_users(
            order_details, user_credentials
        )


def modify_order_for_brokers(order_details, user_credentials):
    """
    Modifies an order for a given broker.

    Args:
        order_details (dict): Details of the order to be modified.
        user_credentials (dict): Credentials of the user modifying the order.

    Returns:
        dict: Response from the broker API.
    """
    if order_details["broker"] == ZERODHA:
        return zerodha_adapter.kite_modify_orders_for_users(
            order_details, user_credentials
        )
    elif order_details["broker"] == ALICEBLUE:
        return alice_adapter.ant_modify_orders_for_users(
            order_details, user_credentials
        )
    elif order_details["broker"] == FIRSTOCK:
        return firstock_adapter.firstock_modify_orders_for_users(
            order_details, user_credentials
        )


def get_today_orders_for_brokers(user):
    """
    Fetches today's orders for a user based on their broker.

    Args:
        user (dict): User account details.

    Returns:
        list: List of today's orders.
    """
    if user["Broker"]["BrokerName"] == ZERODHA:
        try:
            logger.debug(
                f"Fetching today's orders for {user['Broker']['BrokerUsername']}"
            )
            kite_data = zerodha_adapter.zerodha_todays_tradebook(user["Broker"])
            if kite_data:
                kite_data = [
                    trade
                    for trade in kite_data
                    if trade["status"] != "REJECTED" or trade["status"] != "CANCELLED"
                ]
        except Exception as e:
            logger.error(
                f"Error while fetching today's orders for {user['Broker']['BrokerUsername']}: {e}"
            )
            kite_data = []
        return kite_data
    elif user["Broker"]["BrokerName"] == ALICEBLUE:
        try:
            logger.debug(
                f"Fetching today's tradebook for {user['Broker']['BrokerUsername']}"
            )
            alice_data = alice_adapter.aliceblue_todays_tradebook(user["Broker"])
            if alice_data:
                alice_data = [
                    trade
                    for trade in alice_data
                    if trade["Status"] != "rejected" or trade["Status"] != "cancelled"
                ]
        except Exception as e:
            logger.error(
                f"Error while fetching today's tradebook for {user['Broker']['BrokerUsername']}: {e}"
            )
            alice_data = []
        return alice_data
    elif user["Broker"]["BrokerName"] == FIRSTOCK:
        try:
            logger.debug(
                f"Fetching today's tradebook for {user['Broker']['BrokerUsername']}"
            )
            firstock_data = firstock_adapter.firstock_todays_tradebook(user["Broker"])
            if firstock_data:
                firstock_data = [
                    trade
                    for trade in firstock_data
                    if trade["status"] != "REJECTED" or trade["status"] != "CANCELLED"
                ]
        except Exception as e:
            logger.error(
                f"Error while fetching today's tradebook for {user['Broker']['BrokerUsername']}: {e}"
            )
            firstock_data = []
        return firstock_data


def get_today_open_orders_for_brokers(user):
    """
    Fetches today's open orders for a user based on their broker.

    Args:
        user (dict): User account details.

    Returns:
        list: List of today's open orders.
    """
    if user["Broker"]["BrokerName"] == ZERODHA:
        kite_data = zerodha_adapter.fetch_kite_open_orders(user)
        return kite_data
    elif user["Broker"]["BrokerName"] == ALICEBLUE:
        alice_data = alice_adapter.fetch_alice_open_orders(user)
        return alice_data
    elif user["Broker"]["BrokerName"] == FIRSTOCK:
        firstock_data = firstock_adapter.fetch_firstock_open_orders(user)
        return firstock_data


def create_counter_order_details(tradebook, user):
    """
    Creates counter order details based on the tradebook and user details.

    Args:
        tradebook (list): List of trades.
        user (dict): User account details.

    Returns:
        list: List of counter order details.
    """
    counter_order_details = []
    try:
        if not tradebook:
            logger.warning(
                f"Tradebook is empty for user {user['Broker']['BrokerUsername']}"
            )
            return []
        for trade in tradebook:
            if user["Broker"]["BrokerName"] == ZERODHA:
                if trade["status"] == "TRIGGER PENDING" and trade["product"] == "MIS":
                    zerodha_adapter.kite_create_cancel_order(trade, user)
                    counter_order = zerodha_adapter.kite_create_sl_counter_order(
                        trade, user
                    )
                    counter_order_details.append(counter_order)
                    logger.info(
                        f"Created counter orders for {user['Broker']['BrokerName']} for user {user['Broker']['BrokerUsername']} for trade_id {trade['tag']}"
                    )
            elif user["Broker"]["BrokerName"] == ALICEBLUE:
                if trade["Status"] == "trigger pending" and trade["Pcode"] == "MIS":
                    alice_adapter.ant_create_cancel_orders(trade, user)
                    counter_order = alice_adapter.ant_create_counter_order(trade, user)
                    counter_order_details.append(counter_order)
                    logger.info(
                        f"Created counter orders for {user['Broker']['BrokerName']} for user {user['Broker']['BrokerUsername']} for trade_id {trade['remarks']}"
                    )
            elif user["Broker"]["BrokerName"] == FIRSTOCK:
                if trade["status"] == "TRIGGER_PENDING" and trade["product"] == "I":
                    firstock_adapter.firstock_create_cancel_order(trade, user)
                    counter_order = firstock_adapter.firstock_create_sl_counter_order(
                        trade, user
                    )
                    counter_order_details.append(counter_order)
                    logger.info(
                        f"Created counter orders for {user['Broker']['BrokerName']} for user {user['Broker']['BrokerUsername']} for trade_id {trade['remarks']}"
                    )
        return counter_order_details
    except Exception as e:
        logger.error(
            f"Error while creating counter orders for {user['Broker']['BrokerName']} for user {user['Broker']['BrokerUsername']}: {e}"
        )
        logger.error(traceback.format_exc())
        return []


def cancel_normal_orders(tradebook, user):
    """
    Cancels normal orders based on the tradebook and user details.

    Args:
        tradebook (list): List of trades.
        user (dict): User account details.

    Returns:
        list: List of canceled orders.
    """
    try:
        if not tradebook:
            logger.warning(
                f"Tradebook is empty for user {user['Broker']['BrokerUsername']}"
            )
            return []
        for trade in tradebook:
            if user["Broker"]["BrokerName"] == ZERODHA:
                if trade["status"] == "TRIGGER PENDING" and trade["product"] == "NRML":
                    zerodha_adapter.kite_create_cancel_order(trade, user)
            if user["Broker"]["BrokerName"] == ALICEBLUE:
                if trade["Status"] == "trigger pending" and trade["Pcode"] == "NRML":
                    alice_adapter.ant_create_cancel_orders(trade, user)
            if user["Broker"]["BrokerName"] == FIRSTOCK:
                if trade["status"] == "TRIGGER_PENDING" and trade["product"] == "C":
                    firstock_adapter.firstock_create_cancel_order(trade, user)
    except Exception as e:
        logger.error(
            f"Error while cancelling normal orders for {user['Broker']['BrokerName']} for user {user['Broker']['BrokerUsername']}: {e}"
        )
        logger.error(traceback.format_exc())
        return []


def create_hedge_counter_order_details(tradebook, user, open_orders):
    """
    Creates hedge counter order details based on the tradebook, user details, and open orders.

    Args:
        tradebook (list): List of trades.
        user (dict): User account details.
        open_orders (list): List of open orders.

    Returns:
        list: List of hedge counter order details.
    """
    if not tradebook:
        logger.warning(
            f"Tradebook is empty for user {user['Broker']['BrokerUsername']}"
        )
        return []
    hedge_counter_order = []
    if user["Broker"]["BrokerName"] == ZERODHA:
        try:
            open_order_tokens = {
                position["instrument_token"]
                for position in open_orders["net"]
                if position["product"] == "MIS" and position["quantity"] != 0
            }
            for trade in tradebook:
                if trade["tag"] is None:
                    continue

                if (
                    trade["status"] == "COMPLETE"
                    and trade["product"] == "MIS"
                    and "HO_EN" in trade["tag"]
                    and "HO_EX" not in trade["tag"]
                    and trade["instrument_token"] in open_order_tokens
                ):
                    counter_order = zerodha_adapter.kite_create_hedge_counter_order(
                        trade, user
                    )
                    if counter_order not in hedge_counter_order:
                        hedge_counter_order.append(counter_order)
                        logger.info(
                            f"Created hedge counter orders for {user['Broker']['BrokerName']} for user {user['Broker']['BrokerUsername']} for trade_id {trade['tag']}"
                        )
        except Exception as e:
            logger.error(
                f"Error while creating hedge counter orders for {user['Broker']['BrokerName']} for user {user['Broker']['BrokerUsername']}: {e}"
            )
    elif user["Broker"]["BrokerName"] == ALICEBLUE:
        try:
            open_order_tokens = {
                position["Token"]: abs(int(position["Netqty"]))
                for position in open_orders
                if position["Pcode"] == "MIS" and position["Netqty"] != "0.00"
            }
            for trade in tradebook:
                if trade["remarks"] is None:
                    continue

                trade_token_str = str(trade["token"])
                if (
                    trade["Status"] == "complete"
                    and trade["Pcode"] == "MIS"
                    and "HO_EN" in trade["remarks"]
                    and "HO_EX" not in trade["remarks"]
                    and trade_token_str in open_order_tokens
                ):
                    counter_order = alice_adapter.ant_create_hedge_counter_order(
                        trade, user
                    )
                    if counter_order not in hedge_counter_order:
                        hedge_counter_order.append(counter_order)
                        logger.info(
                            f"Created hedge counter orders for {user['Broker']['BrokerName']} for user {user['Broker']['BrokerUsername']} for trade_id {trade['remarks']}"
                        )
        except Exception as e:
            logger.error(
                f"Error while creating hedge counter orders for {user['Broker']['BrokerName']} for user {user['Broker']['BrokerUsername']}: {e}"
            )
    elif user["Broker"]["BrokerName"] == FIRSTOCK:
        try:
            open_order_tokens = {
                position["token"]
                for position in open_orders
                if position["product"] == "I" and position["netQuantity"] != "0"
            }
            for trade in tradebook:
                remarks = trade.get("remarks", "")
                if not remarks:
                    continue

                if (
                    trade["status"] == "COMPLETE"
                    and trade["product"] == "I"
                    and "HO_EN" in trade["remarks"]
                    and "HO_EX" not in trade["remarks"]
                    and trade["token"] in open_order_tokens
                ):
                    counter_order = firstock_adapter.firstock_create_hedge_counter_order(
                        trade, user
                    )
                    if counter_order not in hedge_counter_order:
                        hedge_counter_order.append(counter_order)
                        logger.info(
                            f"Created hedge counter orders for {user['Broker']['BrokerName']} for user {user['Broker']['BrokerUsername']} for trade_id {trade['remarks']}"
                        )
        except Exception as e:
            logger.error(
                f"Error while creating hedge counter orders for {user['Broker']['BrokerName']} for user {user['Broker']['BrokerUsername']}: {e}"
            )
    return hedge_counter_order


def get_orders_tax(orders_to_place, user_credentials):
    """
    Fetches the order tax for a user based on their broker.

    Args:
        orders_to_place (list): List of orders to place.
        user_credentials (dict): User credentials.

    Returns:
        dict: Order tax details.
    """
    if user_credentials["BrokerName"] == ZERODHA:
        return zerodha_adapter.get_kite_order_tax(
            orders_to_place, user_credentials["BrokerName"]
        )
    elif user_credentials["BrokerName"] == ALICEBLUE:
        return zerodha_adapter.get_kite_order_tax(
            orders_to_place, user_credentials["BrokerName"]
        )
    elif user_credentials["BrokerName"] == FIRSTOCK:
        return zerodha_adapter.get_kite_order_tax(
            orders_to_place, user_credentials["BrokerName"]
        )
    else:
        return None


def get_order_margin(orders_to_place, user_credentials):
    """
    Fetches the order margin for a user based on their broker.

    Args:
        orders_to_place (list): List of orders to place.
        user_credentials (dict): User credentials.

    Returns:
        dict: Order margin details.
    """
    if user_credentials["BrokerName"] == ZERODHA:
        return zerodha_adapter.get_margin_utilized(user_credentials)
    elif user_credentials["BrokerName"] == ALICEBLUE:
        return alice_adapter.get_margin_utilized(user_credentials)
    elif user_credentials["BrokerName"] == FIRSTOCK:
        return firstock_adapter.get_margin_utilized(user_credentials)
    else:
        return None


def get_basket_order_margins(orders_to_place, user_credentials):
    """
    Fetches the basket order margins for a user based on their broker.

    Args:
        orders_to_place (list): List of orders to place.
        user_credentials (dict): User credentials.

    Returns:
        dict: Basket order margins.
    """
    if user_credentials["BrokerName"] == ZERODHA:
        return zerodha_adapter.get_basket_margin(orders_to_place=orders_to_place)
    elif user_credentials["BrokerName"] == ALICEBLUE:
        return alice_adapter.get_basket_margin(user_credentials)
    elif user_credentials["BrokerName"] == FIRSTOCK:
        return firstock_adapter.get_basket_margin(orders_to_place=orders_to_place)
    else:
        return None
