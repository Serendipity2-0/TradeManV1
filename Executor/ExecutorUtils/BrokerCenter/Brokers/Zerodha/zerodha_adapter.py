import datetime

import pandas as pd
from kiteconnect import KiteConnect
import os


from Executor.Strategies.StrategiesUtil import (
    get_strategy_name_from_trade_id,
    get_signal_from_trade_id,
    calculate_transaction_type_sl,
)
from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import (
    discord_bot,
)

from loguru import logger

ERROR_LOG_PATH = os.getenv("ERROR_LOG_PATH")
logger.add(
    ERROR_LOG_PATH,
    level="TRACE",
    rotation="00:00",
    enqueue=True,
    backtrace=True,
    diagnose=True,
)


def create_kite_obj(user_details=None, api_key=None, access_token=None):
    if api_key and access_token:
        return KiteConnect(api_key=api_key, access_token=access_token)
    elif user_details:
        return KiteConnect(
            api_key=user_details["ApiKey"], access_token=user_details["SessionId"]
        )
    else:
        raise ValueError(
            "Either user_details or api_key and access_token must be provided"
        )


def zerodha_fetch_free_cash(user_details):
    logger.debug(f"Fetching free cash for {user_details['BrokerUsername']}")
    kite = KiteConnect(api_key=user_details["ApiKey"])
    kite.set_access_token(user_details["SessionId"])
    # Fetch the account balance details
    try:
        balance_details = kite.margins(segment="equity")
        cash_balance = balance_details["cash"]
        if cash_balance == 0 and "cash" not in balance_details:
            # Look for 'cash' in nested dictionaries
            for key, value in balance_details.items():
                if isinstance(value, dict) and "cash" in value:
                    cash_balance = value.get("cash", 0)
                    break
    except Exception as e:
        logger.error(f"Error fetching free cash: {e} for {user_details['BrokerUsername']}")
        return 0
    logger.info(f"Free cash for {user_details['BrokerUsername']}: {cash_balance}")
    return cash_balance


def get_csv_kite(user_details):
    logger.debug(f"Fetching instruments for KITE using {user_details['Broker']['BrokerUsername']}")
    kite = KiteConnect(api_key=user_details["Broker"]["ApiKey"])
    kite.set_access_token(user_details["Broker"]["SessionId"])
    instrument_dump = kite.instruments()
    instrument_df = pd.DataFrame(instrument_dump)
    instrument_df["exchange_token"] = instrument_df["exchange_token"].astype(str)
    return instrument_df


def fetch_zerodha_holdings(api_key, access_token):
    kite = KiteConnect(api_key=api_key, access_token=access_token)
    holdings = kite.holdings()
    return holdings


def simplify_zerodha_order(detail):
    trade_symbol = detail["tradingsymbol"]

    # Check if the tradingsymbol is of futures type
    if trade_symbol.endswith("FUT"):
        strike_price = 0
        option_type = "FUT"
    else:
        strike_price = int(trade_symbol[-7:-2])  # Convert to integer to store as number
        option_type = trade_symbol[-2:]

    trade_id = detail["tag"]
    if trade_id.endswith("_entry"):
        order_type = "entry"
    elif trade_id.endswith("_exit"):
        order_type = "exit"

    return {
        "trade_id": trade_id,  # This is the order_id for zerodha
        "avg_price": detail["average_price"],
        "qty": detail["quantity"],
        "time": detail["order_timestamp"].strftime("%d/%m/%Y %H:%M:%S"),
        "strike_price": strike_price,
        "option_type": option_type,
        "trading_symbol": trade_symbol,
        "trade_type": detail["transaction_type"],
        "order_type": order_type,
    }


def zerodha_todays_tradebook(user):
    kite = create_kite_obj(api_key=user["ApiKey"], access_token=user["SessionId"])
    orders = kite.orders()
    return orders


def calculate_transaction_type(kite, transaction_type):
    if transaction_type == "BUY":
        transaction_type = kite.TRANSACTION_TYPE_BUY
    elif transaction_type == "SELL":
        transaction_type = kite.TRANSACTION_TYPE_SELL
    else:
        raise ValueError("Invalid transaction_type in order_details")
    return transaction_type


def calculate_order_type(kite, order_type):
    if order_type.lower() == "stoploss":
        order_type = kite.ORDER_TYPE_SL
    elif order_type.lower() == "market":
        order_type = kite.ORDER_TYPE_MARKET
    elif order_type.lower() == "limit":
        order_type = kite.ORDER_TYPE_LIMIT
    else:
        raise ValueError("Invalid order_type in order_details")
    return order_type


def calculate_product_type(kite, product_type):
    if product_type == "NRML":
        product_type = kite.PRODUCT_NRML
    elif product_type == "MIS":
        product_type = kite.PRODUCT_MIS
    elif product_type == "CNC":
        product_type = kite.PRODUCT_CNC
    else:
        raise ValueError("Invalid product_type in order_details")
    return product_type


def calculate_segment_type(kite, segment_type):
    # Prefix to indicate the exchange type
    prefix = "EXCHANGE_"

    # Construct the attribute name
    attribute_name = prefix + segment_type

    # Get the attribute from the kite object, or raise an error if it doesn't exist
    if hasattr(kite, attribute_name):
        return getattr(kite, attribute_name)
    else:
        raise ValueError(f"Invalid segment_type '{segment_type}' in order_details")


def get_avg_prc(kite, order_id):
    if not order_id:
        raise Exception("Order_id not found")

    order_history = kite.order_history(order_id=order_id)
    for order in order_history:
        if order.get("status") == "COMPLETE":
            avg_prc = order.get("average_price", 0.0)
            break
    return avg_prc

def get_order_status(kite, order_id):
    order_history = kite.order_history(order_id=order_id)
    for order in order_history:
        if order.get("status") == "REJECTED":
            return order.get('status_message')
        elif order.get("status") == "COMPLETE" or order.get("status") == "TRIGGER PENDING":
            return "PASS"

def get_order_details(user):
    kite = create_kite_obj(api_key=user["api_key"], access_token=user["access_token"])
    orders = kite.orders()
    return orders

def kite_place_orders_for_users(orders_to_place, users_credentials):
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

    kite = create_kite_obj(
        user_details=users_credentials
    )  # Create a KiteConnect instance with user's broker credentials
    order_id = None

    strategy = orders_to_place["strategy"]
    exchange_token = orders_to_place["exchange_token"]
    qty = orders_to_place.get("qty", 1)  # Default quantity to 1 if not specified
    product = orders_to_place.get("product_type")

    transaction_type = calculate_transaction_type(
        kite, orders_to_place.get("transaction_type")
    )
    order_type = calculate_order_type(kite, orders_to_place.get("order_type"))
    product_type = calculate_product_type(kite, product)
    if product == "CNC":
        segment_type = kite.EXCHANGE_NSE
        trading_symbol = Instrument().get_trading_symbol_by_exchange_token(
            exchange_token, "NSE"
        )
    else:
        segment_type = Instrument().get_segment_by_exchange_token(str(exchange_token))
        trading_symbol = Instrument().get_trading_symbol_by_exchange_token(
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

    try:
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
        order_id = kite.place_order(
            variety=kite.VARIETY_REGULAR,
            exchange=segment_type,
            price=limit_prc,
            tradingsymbol=trading_symbol,
            transaction_type=transaction_type,
            quantity=qty,
            trigger_price=trigger_price,
            product=product_type,
            order_type=order_type,
            tag=orders_to_place.get("trade_id", None),
        )

        logger.success(f"Order placed. ID is: {order_id}")
        # #TODO: Fetch the order status of the order_id and check if it is complete
        order_status = get_order_status(kite, order_id)
        if order_status != "PASS":
            message = f"Order placement failed: {order_status} for {orders_to_place['username']}"
            discord_bot(message, strategy)

    except Exception as e:
        message = f"Order placement failed: {e} for {orders_to_place['username']}"
        logger.error(message)
        discord_bot(message, strategy)
        
    results = {
                "exchange_token": int(exchange_token),
                "order_id": order_id,
                "qty": qty,
                "time_stamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "trade_id": orders_to_place.get("trade_id", "")
            }
    
    return results


def kite_modify_orders_for_users(order_details, users_credentials):
    from Executor.ExecutorUtils.OrderCenter.OrderCenterUtils import retrieve_order_id

    kite = create_kite_obj(
        user_details=users_credentials
    )  # Create a KiteConnect instance with user's broker credentials
    order_id_dict = retrieve_order_id(
        order_details.get("username"),
        order_details.get("strategy"),
        order_details.get("exchange_token"),
    )
    new_stoploss = order_details.get("limit_prc", 0.0)
    trigger_price = order_details.get("trigger_prc", None)

    try:
        for order_id, qty in order_id_dict.items():
            modify_order = kite.modify_order(
                variety=kite.VARIETY_REGULAR,
                order_id=order_id,
                price=new_stoploss,
                trigger_price=trigger_price,
            )
            logger.info("zerodha order modified", modify_order)
    except Exception as e:
        message = f"Order placement failed: {e} for {order_details['username']}"
        logger.error(message)
        discord_bot(message, order_details.get("strategy"))
        return None


def kite_create_sl_counter_order(trade, user):
    from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import Instrument

    strategy_name = get_strategy_name_from_trade_id(trade["tag"])
    exchange_token = Instrument().get_exchange_token_by_token(trade["instrument_token"])
    counter_order = {
        "strategy": strategy_name,
        "signal": get_signal_from_trade_id(trade["tag"]),
        "base_symbol": "NIFTY",  # WARNING: dummy base symbol
        "exchange_token": exchange_token,
        "transaction_type": trade["transaction_type"],
        "order_type": "MARKET",
        "product_type": trade["product"],
        "trade_id": trade["tag"],
        "order_mode": "Counter",
        "qty": trade["quantity"],
    }
    return counter_order


def kite_create_cancel_order(trade, user):
    kite = create_kite_obj(user_details=user["Broker"])
    kite.cancel_order(variety=kite.VARIETY_REGULAR, order_id=trade["order_id"])


def kite_create_hedge_counter_order(trade, user):
    from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import Instrument

    strategy_name = get_strategy_name_from_trade_id(trade["tag"])
    exchange_token = Instrument().get_exchange_token_by_token(trade["instrument_token"])
    # i want to replace EN to EX in the trade['tag']
    trade_id = trade['tag'].replace('EN', 'EX')


    counter_order = {
        "strategy": strategy_name,
        "signal": get_signal_from_trade_id(trade["tag"]),
        "base_symbol": "NIFTY",  # WARNING: dummy base symbol
        "exchange_token": exchange_token,
        "transaction_type": calculate_transaction_type_sl(trade["transaction_type"]),
        "order_type": "MARKET",
        "product_type": trade["product"],
        "trade_id": trade_id,
        "order_mode": "Hedge",
        "qty": trade["quantity"],
    }
    return counter_order


def process_kite_ledger(csv_file_path):
    # Define patterns for categorizing transactions
    patterns = {
        "Deposits": [
            "Funds added using UPI",
            "Opening Balance",
            "Funds added using payment gateway from YY0222",
        ],
        "Withdrawals": [
            "Funds transferred back as part of quarterly settlement",
            "Payout of",
        ],
        "Charges": [
            "Being payment gateway charges debited",
            "DPCharges",
            "Reversal of Brokerage",
            "Kite Connect API Charges",
            "Call and Trade charges",
            "AMC for Demat Account",
            "DP Charges for Sale of",
        ],
        "Trades": [
            "Net obligation for Equity F&O",
            "Net settlement for Equity",
            "Net obligation for Currency F&O",
        ],
    }

    # Load the CSV file
    ledger_data = pd.read_csv(csv_file_path)

    # Function to categorize a transaction
    def categorize_transaction(particulars):
        for category, patterns_list in patterns.items():
            for pattern in patterns_list:
                if pattern in particulars:
                    return category
        return "Other"

    # Categorize each transaction
    ledger_data["Category"] = ledger_data["particulars"].apply(categorize_transaction)

    # Filter out transactions with 'Closing Balance'
    ledger_data_filtered = ledger_data[ledger_data["particulars"] != "Closing Balance"]

    # Create dataframes for each category
    categorized_dfs = {
        category: ledger_data_filtered[ledger_data_filtered["Category"] == category]
        for category in patterns.keys()
    }

    other_transactions_final = ledger_data_filtered[
        ledger_data_filtered["Category"] == "Other"
    ]
    other_transactions_final.to_csv(f"kite_other.csv", index=False)

    # save categorized_dfs to csv as {category}.csv
    for category, df in categorized_dfs.items():
        df.to_csv(f"kite_{category}.csv", index=False)

    return categorized_dfs


def calculate_kite_net_values(categorized_dfs):
    # Calculate net values for each category
    net_values = {
        category: df["debit"].sum() - df["credit"].sum()
        for category, df in categorized_dfs.items()
    }
    return net_values

def fetch_open_orders(user_details):
    kite = create_kite_obj(user_details['Broker'])
    positions = kite.positions()
    return positions
    