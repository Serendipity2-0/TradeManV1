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
    logger.debug(f"Fetching free cash for {user_details['BrokerUsername']}")
    limits = thefirstock.firstock_Limits(userId=user_details['BrokerUsername'])
    free_cash = limits.get("data", {}).get("cash", 0)
    return float(free_cash)

def fetch_firstock_holdings_value(user):
    try:
        logger.debug(f"Fetching holdings for {user['Broker']['BrokerUsername']}")
        holdings = thefirstock.firstock_Holding(userId=user['Broker']['BrokerUsername'])
        holdings = holdings.get("data")
        return sum(stock['uploadPrice'] * stock['holdQuantity'] for stock in holdings)
    except Exception as e:
        logger.error(f"Error fetching holdings for user: {user['Broker']['BrokerUsername']}: {e}")
        return 0.0

def firstock_todays_tradebook(user_details):
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
    try:
        positionBook = thefirstock.firstock_PositionBook(userId=user['Broker']['BrokerUsername'])
        positionBook = positionBook.get("data")
        return positionBook
    except Exception as e:
        logger.error(f"Error fetching open orders for user: {user['Broker']['BrokerUsername']}: {e}")

def calculate_transaction_type(transaction_type):
    if transaction_type == "BUY" or transaction_type == "B":
        transaction_type = "B"
    elif transaction_type == "SELL" or transaction_type == "S":
        transaction_type = "S"
    else:
        raise ValueError("Invalid transaction_type in order_details")
    return transaction_type

def calculate_order_type(order_type):
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
        segment_type = Instrument().get_segment_by_exchange_token(str(exchange_token))
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
                "order_status": order_status
            }
    
    return results

def firstock_modify_orders_for_users(order_details, users_credentials):
    from Executor.ExecutorUtils.OrderCenter.OrderCenterUtils import retrieve_order_id
    from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import Instrument

    order_id_dict = retrieve_order_id(
        order_details.get("username"),
        order_details.get("strategy"),
        order_details.get("exchange_token"),
    )
    new_stoploss = order_details.get("limit_prc", 0.0)
    trigger_price = order_details.get("trigger_prc", None)
    segement = Instrument().get_segment_by_exchange_token(str(order_details.get("exchange_token")))
    trading_symbol = Instrument().get_trading_symbol_by_exchange_token(str(order_details.get("exchange_token")))
    price_type = order_details.get("order_type")
    if price_type == "stoploss":
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
            logger.info("firstock order modified", modifyOrder)
    except Exception as e:
        message = f"Order placement failed: {e} for {order_details['username']}"
        logger.error(message)
        discord_bot(message, order_details.get("strategy"))
        return None

def firstock_create_sl_counter_order(trade, user):

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
    try:
        cancelOrder = thefirstock.firstock_cancelOrder(
                        userId=user["Broker"]["BrokerUsername"],
                        orderNumber=trade['orderNumber']
                        )
    except Exception as e:
        logger.error(f"Error cancelling order: {e}")
        return None
    
def firstock_create_hedge_counter_order(trade, user):
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
    try:
        pb = thefirstock.firstock_PositionBook(userId=user['Broker']['BrokerUsername'])
        positions = pb.get('data',{})
        unrealized_total_pnl = sum(float(position['unrealizedMTOM']) for position in positions)
        realized_total_pnl = sum(float(position['RealizedPNL']) for position in positions)
        total_pnl = unrealized_total_pnl + realized_total_pnl
        return total_pnl
    except Exception as e:
        logger.error(f"Error fetching pnl for user: {user['Broker']['BrokerUsername']}: {e}")
        return None