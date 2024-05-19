import os
import sys
import datetime as dt
from dotenv import load_dotenv
from datetime import datetime
from thefirstock import thefirstock

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import (
    discord_bot,
)
from Executor.Strategies.StrategiesUtil import (
    get_strategy_name_from_trade_id,
    get_signal_from_trade_id,
    calculate_transaction_type_sl,
)

logger = LoggerSetup()

def firstock_fetch_free_cash(user_details):
    """
    This Python function fetches the amount of free cash available for a user from a brokerage platform
    called "firstock".
    
    :param user_details: The `firstock_fetch_free_cash` function takes a dictionary `user_details` as a
    parameter. This dictionary likely contains information about a user, such as their `BrokerUsername`
    :return: The function `firstock_fetch_free_cash` is returning the free cash amount for a given user,
    which is fetched from the `thefirstock.firstock_Limits` API using the user's broker username. The
    free cash amount is then converted to a float and returned.
    """
    logger.debug(f"Fetching free cash for {user_details['BrokerUsername']}")
    limits = thefirstock.firstock_Limits(userId=user_details['BrokerUsername'])
    free_cash = limits.get("data", {}).get("cash", 0)
    return float(free_cash)

def fetch_firstock_holdings_value(user):
    """
    The function fetches the total value of a user's stock holdings by multiplying the upload price of
    each stock by its quantity held.
    
    :param user: The `fetch_firstock_holdings_value` function is designed to fetch the total value of a
    user's stock holdings from the `thefirstock` platform. It takes a `user` object as input, which
    likely contains information about the user's broker account, such as the broker's username
    :return: The function `fetch_firstock_holdings_value` is returning the total value of all stock
    holdings for a given user. It calculates this value by multiplying the upload price of each stock by
    the quantity of that stock held, and then summing up these values for all stocks in the user's
    holdings. If an error occurs during the process of fetching the holdings, the function will return
    0.0
    """
    try:
        logger.debug(f"Fetching holdings for {user['Broker']['BrokerUsername']}")
        holdings = thefirstock.firstock_Holding(userId=user['Broker']['BrokerUsername'])
        holdings = holdings.get("data")
        return sum(stock['uploadPrice'] * stock['holdQuantity'] for stock in holdings)
    except Exception as e:
        logger.error(f"Error fetching holdings for user: {user['Broker']['BrokerUsername']}: {e}")
        return 0.0

def firstock_todays_tradebook(user_details):
    """
    This Python function retrieves the tradebook orders for a user using the firstock API.
    
    :param user_details: The `firstock_todays_tradebook` function takes a `user_details` parameter,
    which is expected to be a dictionary containing information about the user. The function attempts to
    fetch the trade book for the user specified by the 'BrokerUsername' key in the `user_details`
    dictionary
    :return: The function `firstock_todays_tradebook` is returning the trade orders for the user
    specified in the `user_details` dictionary. If there are no orders or if an exception occurs during
    the process, it will return `None`.
    """
    try:
        tradeBook = thefirstock.firstock_orderBook(
            userId=user_details['BrokerUsername']
        )
        orders = tradeBook.get("data")
        if not orders:
            return None
        return orders
    except Exception as e:
        logger.error(f"Error fetching tradebook for user: {user_details['BrokerUsername']}: {e}")
        return None

def fetch_open_orders(user):
    """
    The function fetches open orders for a user from a stock position book using their broker username.
    
    :param user: The `fetch_open_orders` function seems to be attempting to fetch open orders for a user
    from a stock position book. The `user` parameter likely contains information about the user,
    including their broker username
    :return: The function `fetch_open_orders` is attempting to fetch open orders for a user by accessing
    the position book using the user's broker username. If successful, it returns the data from the
    position book. If an exception occurs during the process, an error message is logged.
    """
    try:
        positionBook = thefirstock.firstock_PositionBook(userId=user['Broker']['BrokerUsername'])
        positionBook = positionBook.get("data")
        return positionBook
    except Exception as e:
        logger.error(f"Error fetching open orders for user: {user['Broker']['BrokerUsername']}: {e}")

def calculate_transaction_type(transaction_type):
    """
    The function `calculate_transaction_type` standardizes transaction types to "B" for buy and "S" for
    sell.
    
    :param transaction_type: The `calculate_transaction_type` function takes a transaction type as input
    and standardizes it to either "B" for buy or "S" for sell. If the input is "BUY" or "B", it will be
    converted to "B". If the input is "SELL" or "S
    :return: The function `calculate_transaction_type` returns the standardized transaction type ("B"
    for "BUY" or "S" for "SELL") after processing the input transaction type provided as an argument to
    the function.
    """
    if transaction_type == "BUY" or transaction_type == "B":
        transaction_type = "B"
    elif transaction_type == "SELL" or transaction_type == "S":
        transaction_type = "S"
    else:
        raise ValueError("Invalid transaction_type in order_details")
    return transaction_type

def calculate_order_type(order_type):
    """
    The function `calculate_order_type` converts different order types to standardized abbreviations.
    
    :param order_type: The `calculate_order_type` function takes an `order_type` as input and converts
    it to a standardized format. Here are the mappings for different input values:
    :return: The function `calculate_order_type` returns the updated order type based on the input
    `order_type`. The updated order type is returned as a string value.
    """
    if order_type.lower() == "stoploss":
        order_type = "SL-LMT"
    elif order_type.lower() == "market" or order_type.lower() == "mis":
        order_type = "MKT"
    elif order_type.lower() == "limit":
        order_type = "LMT"
    else:
        raise ValueError("Invalid order_type in order_details")
    return order_type

def calculate_product_type(product_type):
    """
    The function `calculate_product_type` takes a product type abbreviation as input and returns a
    standardized abbreviation based on predefined mappings.
    
    :param product_type: The `calculate_product_type` function takes a `product_type` as input and
    returns a standardized product type based on the mapping provided in the function
    :return: The function `calculate_product_type` returns the standardized product type based on the
    input `product_type`. If the input is "NRML" or "M", it returns "M". If the input is "MIS" or "I",
    it returns "I". If the input is "CNC" or "C", it returns "C". If the input does not match any of
    these
    """
    if product_type == "NRML" or product_type == "M":
        product_type = "M"
    elif product_type == "MIS" or product_type == "I":
        product_type = "I"
    elif product_type == "CNC" or product_type == "C":
        product_type = "C"
    else:
        raise ValueError("Invalid product_type in order_details")
    return product_type

def get_order_status(user_id, order_id):
    """
    The function `get_order_status` retrieves the status of a user's order and returns "PASS" if the
    order is complete or trigger pending, and "FAIL" if the order is rejected or encounters an error.
    
    :param user_id: User ID is the unique identifier of the user for whom we are checking the order
    status. It is used to retrieve the order information specific to that user
    :param order_id: The `order_id` parameter is used to identify a specific order in the system. It is
    a unique identifier associated with each order placed by a user. In the provided code snippet, the
    `order_id` is used to retrieve the order history and check the status of the order. If the `
    :return: The function `get_order_status` returns a string indicating the status of the order. It
    returns "PASS" if the order status is "COMPLETE" or "TRIGGER_PENDING", "FAIL" if the order status is
    "REJECTED", and "FAIL" if there is an error during the execution of the function.
    """
    if not order_id:
        raise Exception("Order_id not found")
    
    try:
        singleOrderHistory = thefirstock.firstock_SingleOrderHistory(
                orderNumber= str(order_id.get('data', {}).get('orderNumber', {})),
                userId = user_id
                )
        for order in singleOrderHistory.get("data"):
            if order.get('status') == 'REJECTED':
                return "FAIL"
            elif order.get('status') == "COMPLETE" or order.get("status") == "TRIGGER_PENDING":
                return "PASS"
        return "FAIL"
    except Exception as e:
        logger.error(f"Error in get_order_status: {e}")
        return "FAIL"

def firstock_place_orders_for_users(orders_to_place, users_credentials):
    """
    The function `firstock_place_orders_for_users` places orders for users based on the provided order
    details and user credentials.
    
    :param orders_to_place: The `orders_to_place` parameter seems to contain information about the order
    to be placed. It includes details such as the strategy, exchange token, quantity, product type,
    transaction type, order type, limit price, trigger price, trade mode, and trade ID
    :param users_credentials: The `users_credentials` parameter likely contains information about the
    user's credentials needed to authenticate and interact with a trading platform or API. This could
    include the user's BrokerUsername, API keys, tokens, or any other authentication details required to
    place orders on behalf of the user
    :return: The function `firstock_place_orders_for_users` is returning a dictionary `results`
    containing information about the order placement. The dictionary includes keys such as
    "exchange_token", "order_id", "qty", "time_stamp", "trade_id", "order_status", and "tax". The
    function returns this dictionary with the relevant information filled in based on the order
    placement process.
    """
    from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import Instrument,get_single_ltp

    results = {
        "avg_prc": None,
        "exchange_token": None,
        "order_id": None,
        "qty": None,
        "time_stamp": None,
        "trade_id": None,
        "message": None,
    }

    order_id = None

    strategy = orders_to_place["strategy"]
    exchange_token = orders_to_place["exchange_token"]
    qty = orders_to_place.get("qty", 1)  # Default quantity to 1 if not specified
    product = orders_to_place.get("product_type")

    transaction_type = calculate_transaction_type(orders_to_place.get("transaction_type"))
    order_type = calculate_order_type(orders_to_place.get("order_type"))
    product_type = calculate_product_type(product)
    if product == "CNC":
        product_type = "C"
        trading_symbol = Instrument().get_full_format_trading_symbol_by_exchange_token(
            exchange_token, "NSE"
        )
    else:
        segment_type = Instrument().get_exchange_by_exchange_token(str(exchange_token))
        trading_symbol = Instrument().get_full_format_trading_symbol_by_exchange_token(
            str(exchange_token)
        )

    limit_prc = orders_to_place.get("limit_prc", None)
    trigger_price = orders_to_place.get("trigger_prc", None)

    if limit_prc is not None:
        limit_prc = round(float(limit_prc), 2)
        if limit_prc < 0:
            limit_prc = 1.0
    elif product == "CNC":
        limit_prc = get_single_ltp(exchange_token=exchange_token, segment="NSE")
    else:
        limit_prc = 0.0

    if trigger_price is not None:
        trigger_price = round(float(trigger_price), 2)
        if trigger_price < 0:
            trigger_price = 1.5

    if orders_to_place.get("trade_mode") == "PAPER":
        logger.debug("Placing paper trade order")
        logger.debug(f"transaction_type: {transaction_type}")
        logger.debug(f"order_type: {order_type}")
        logger.debug(f"product_type: {product_type}")
        logger.debug(f"segment: {segment_type}")
        logger.debug(f"exchange_token: {exchange_token}")
        logger.debug(f"qty: {qty}")
        logger.debug(f"limit_prc: {limit_prc}")
        logger.debug(f"trigger_price: {trigger_price}")
        logger.debug(f"instrument: {trading_symbol}")
        logger.debug(f"trade_id: {orders_to_place.get('trade_id', '')}")
        results = {
                "exchange_token": int(exchange_token),
                "order_id": 123456789,
                "qty": qty,
                "time_stamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "trade_id": orders_to_place.get("trade_id", "")
            }
        return results


    try:
        order_id = thefirstock.firstock_placeOrder(
                    userId = users_credentials['BrokerUsername'],
                    exchange = segment_type,
                    tradingSymbol=trading_symbol,
                    quantity=str(qty),
                    price=str(limit_prc),
                    product=product_type,
                    transactionType=transaction_type,
                    priceType=order_type,
                    retention="DAY",
                    triggerPrice=str(trigger_price),
                    remarks=orders_to_place.get("trade_id", None)
                )
        logger.success(f"Order placed. ID is: {order_id.get('data', {}).get('orderNumber', {})}")
        # #TODO: Fetch the order status of the order_id and check if it is complete
        order_status = get_order_status(users_credentials['BrokerUsername'], order_id)
        if order_status != "PASS":
            message = f"Order placement failed: {order_status} for {orders_to_place['username']}"
            discord_bot(message, strategy)

    except Exception as e:
        message = f"Order placement failed: {e} for {orders_to_place['username']}"
        logger.error(message)
        discord_bot(message, strategy)
        
    results = {
                "exchange_token": int(exchange_token),
                "order_id": order_id.get('data', {}).get('orderNumber', {}),
                "qty": qty,
                "time_stamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "trade_id": orders_to_place.get("trade_id", ""),
                "order_status": order_status,
                "tax":orders_to_place.get("tax", 0)
            }
    
    return results

def firstock_modify_orders_for_users(order_details, users_credentials):
    """
    The function `firstock_modify_orders_for_users` modifies orders for users using order details and
    user credentials.
    
    :param order_details: order_details is a dictionary containing details of an order to be modified.
    It includes keys such as "username", "strategy", "exchange_token", "limit_prc", "trigger_prc", and
    "order_type"
    :param users_credentials: The `users_credentials` parameter likely contains information about the
    user's credentials needed for authentication and authorization purposes. This could include the
    user's broker username, API keys, tokens, or any other necessary information to interact with the
    trading platform or service. It is used in the function `firstock_modify_orders
    :return: The function `firstock_modify_orders_for_users` is returning `None` in case of an exception
    occurring during the order modification process.
    """
    from Executor.ExecutorUtils.OrderCenter.OrderCenterUtils import retrieve_order_id
    from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import Instrument

    order_id_dict = retrieve_order_id(
        order_details.get("username"),
        order_details.get("strategy"),
        order_details.get("exchange_token"),
    )
    new_stoploss = order_details.get("limit_prc", 0.0)
    trigger_price = order_details.get("trigger_prc", None)
    segement = Instrument().get_exchange_by_exchange_token(str(order_details.get("exchange_token")))
    trading_symbol = Instrument().get_full_format_trading_symbol_by_exchange_token(str(order_details.get("exchange_token")))
    price_type = order_details.get("order_type")
    if price_type.lower() == "stoploss":
        price_type = "SL-LMT"    

    try:
        for order_id, qty in order_id_dict.items():
            modifyOrder = thefirstock.firstock_ModifyOrder(
                userId = users_credentials['BrokerUsername'],
                orderNumber = str(order_id),
                quantity = str(qty),
                price = str(new_stoploss),
                triggerPrice = str(trigger_price),
                exchange = segement,
                tradingSymbol = trading_symbol,
                priceType = price_type
            )
            logger.info(f"firstock order modified: {modifyOrder}")
    except Exception as e:
        message = f"Order placement failed: {e} for {order_details['username']}"
        logger.error(message)
        discord_bot(message, order_details.get("strategy"))
        return None

def firstock_create_sl_counter_order(trade, user):
    """
    The function `firstock_create_sl_counter_order` creates a counter order based on trade information,
    handling exceptions if any occur.
    
    :param trade: The `trade` parameter seems to be a dictionary containing information related to a
    trade. It includes keys such as "remarks", "token", "transactionType", "product", "quantity", etc
    :param user: The `user` parameter is likely used to identify the user for whom the counter order is
    being created. It may contain information such as the user's ID, username, or any other relevant
    details needed for processing the order
    :return: The function `firstock_create_sl_counter_order` is returning a dictionary `counter_order`
    containing various details related to a trade order. If an error occurs during the process, it
    returns `None`.
    """

    try:
        strategy_name = get_strategy_name_from_trade_id(trade["remarks"])
        counter_order = {
            "strategy": strategy_name,
            "signal": get_signal_from_trade_id(trade["remarks"]),
            "base_symbol": "NIFTY",  # WARNING: dummy base symbol
            "exchange_token": trade['token'],
            "transaction_type": trade["transactionType"],
            "order_type": "MARKET",
            "product_type": trade["product"],
            "trade_id": trade["remarks"],
            "order_mode": "Counter",
            "qty": trade["quantity"],
        }
        return counter_order
    except Exception as e:
        logger.error(f"Error creating counter order: {e}")
        return None
    
def firstock_create_cancel_order(trade, user):
    """
    The function `firstock_create_cancel_order` attempts to cancel an order using the
    `thefirstock.firstock_cancelOrder` method and logs an error if unsuccessful.
    
    :param trade: The `trade` parameter likely represents a trade order that the user wants to cancel.
    It may contain information such as the order number that uniquely identifies the trade order
    :param user: The `user` parameter seems to be a dictionary containing information about the user,
    including their broker details. It likely has a structure similar to this:
    :return: The function `firstock_create_cancel_order` is returning `None` in case there is an error
    while cancelling the order.
    """
    try:
        cancelOrder = thefirstock.firstock_cancelOrder(
                        userId=user["Broker"]["BrokerUsername"],
                        orderNumber=trade['orderNumber']
                        )
    except Exception as e:
        logger.error(f"Error cancelling order: {e}")
        return None
    
def firstock_create_hedge_counter_order(trade, user):
    """
    The function `firstock_create_hedge_counter_order` creates a counter order based on a trade and user
    input, replacing 'EN' with 'EX' in the trade remarks.
    
    :param trade: The `trade` parameter in the `firstock_create_hedge_counter_order` function seems to
    be a dictionary containing information related to a trade. It includes keys such as "remarks",
    "token", "transactionType", "product", "quantity", etc
    :param user: The `user` parameter is likely a user object or identifier that is being passed to the
    `firstock_create_hedge_counter_order` function. It may contain information about the user who is
    initiating or involved in the trade for which the hedge counter order is being created. This
    information could include user-specific
    :return: The function `firstock_create_hedge_counter_order` is returning a dictionary named
    `counter_order` containing various details related to a trade order.
    """
    try:
        strategy_name = get_strategy_name_from_trade_id(trade["remarks"])
        # i want to replace EN to EX in the trade['tag']
        trade_id = trade['remarks'].replace('EN', 'EX')


        counter_order = {
            "strategy": strategy_name,
            "signal": get_signal_from_trade_id(trade["remarks"]),
            "base_symbol": "NIFTY",  # WARNING: dummy base symbol
            "exchange_token": trade['token'],
            "transaction_type": calculate_transaction_type_sl(trade["transactionType"]),
            "order_type": "MARKET",
            "product_type": trade["product"],
            "trade_id": trade_id,
            "order_mode": "Hedge",
            "qty": trade["quantity"],
        }
        return counter_order
    except Exception as e:
        logger.error(f"Error creating counter order: {e}")
        return None
    
def firstock_get_ledger(user):
    logger.info("This needs to be implemented")

def process_firstock_ledger(ledger, user):
    logger.info("This needs to be implemented")

def calculate_firstock_net_values(user, categorized_dfs):
    logger.info("This needs to be implemented")

def get_firstock_pnl(user):
    """
    The function `get_firstock_pnl` calculates the total profit and loss (PnL) for a user's positions in
    a trading platform called "firstock".
    
    :param user: The `get_firstock_pnl` function takes a user dictionary as input and calculates the
    total profit and loss (PnL) for the user's positions in their trading account using the Firstock API
    :return: The function `get_firstock_pnl` is returning the total profit and loss (PnL) for a user's
    positions in their trading account. It calculates the unrealized total PnL, realized total PnL, and
    then sums them up to get the total PnL. If there is an error during the process, it logs the error
    and returns `None`.
    """
    try:
        pb = thefirstock.firstock_PositionBook(userId=user['Broker']['BrokerUsername'])
        positions = pb.get('data',{})
        unrealized_total_pnl = sum(float(position['unrealizedMTOM']) for position in positions)
        realized_total_pnl = sum(float(position['RealizedPNL']) for position in positions)
        total_pnl = unrealized_total_pnl + realized_total_pnl
        return float(total_pnl)
    except Exception as e:
        logger.error(f"Error fetching pnl for user: {user['Broker']['BrokerUsername']}: {e}")
        return None
    
def get_order_margin(orders,user_credentials,broker):
    """
    Calculates the required margin for an order based on the order details and user credentials.

    Args:
        order (dict): Details of the order for which margin needs to be calculated.
        user_credentials (dict): Credentials required for accessing the user's trading account.
        broker (str): Name of the broker to apply specific adjustments if needed.

    Returns:
        float: The calculated margin for the order.

    Raises:
        Exception: If there is an error in calculating the margin.
    """
    from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import Instrument
    from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import get_single_ltp

    basket_order = []

    for order in orders:
        order_details = thefirstock.firstock_SingleOrderHistory(orderNumber=order["order_id"],userId=user_credentials["BrokerUsername"])
        for order in order_details["data"]:
            if order["status"] == "COMPLETE" or order["status"] == "TRIGGER PENDING" or order["status"] == "REJECTED":
                product = order["product"]
                transaction_type = order["transactionType"]
                quantity = order["quantity"]
                exchange = order["exchange"]
                pricetype = order["priceType"]
                tradingsymbol = order["tradingSymbol"]

        if pricetype == "MKT":
            price = "0"
        elif pricetype == "LMT":
            price = get_single_ltp(exchange_token=exchange,segment="NSE")

        margin_order = {
                        "exchange": exchange,
                        "tradingSymbol": tradingsymbol,
                        "quantity": quantity,
                        "transactionType": transaction_type,
                        "price": price,
                        "product": product,
                        "priceType": pricetype
                    }

        basket_order.append(margin_order)
    basket_margin = thefirstock.firstock_BasketMargin(basket_order,userId=user_credentials["BrokerUsername"])
    margin = basket_margin["data"]["marginused"]
    return float(margin)

def get_broker_payin(user):
    limits = thefirstock.firstock_Limits(userId=user["Broker"]["BrokerUsername"])
    payin = float(limits.get("data", {}).get("payin", 0))
    return payin