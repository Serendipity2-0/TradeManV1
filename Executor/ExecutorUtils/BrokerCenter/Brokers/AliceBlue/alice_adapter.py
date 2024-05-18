import os
import sys
import datetime as dt
from dotenv import load_dotenv
from pya3 import *

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import (
    discord_bot,discord_admin_bot
)
from Executor.Strategies.StrategiesUtil import (
    get_strategy_name_from_trade_id,
    get_signal_from_trade_id,
    calculate_transaction_type_sl,
)

logger = LoggerSetup()

# This function fetches the available free cash balance for a user from the Aliceblue trading platform.
def alice_fetch_free_cash(user_details):
    """
    The function `alice_fetch_free_cash` fetches the available free cash balance for a user from
    Aliceblue brokerage platform.
    
    :param user_details: The `alice_fetch_free_cash` function seems to be fetching the free cash
    available for a user from a brokerage platform using the Aliceblue API. The function takes
    `user_details` as a parameter, which likely contains information about the user's brokerage account,
    such as their username, API key, and
    :return: The function `alice_fetch_free_cash` returns the free cash available for a user's brokerage
    account.
    """
    logger.debug(f"Fetching free cash for {user_details['BrokerUsername']}")
    alice = Aliceblue(
        user_details["BrokerUsername"],
        user_details["ApiKey"],
        session_id=user_details["SessionId"],
    )
    try:
        cash_margin_available = alice.get_balance()
        for item in cash_margin_available:
            if isinstance(item, dict) and "cashmarginavailable" in item:
                cash_margin_available = item.get("cashmarginavailable", 0)
    except Exception as e:
        logger.error(f"Error fetching free cash: {e}")
        return 0.0
    logger.info(f"Free cash for {user_details['BrokerUsername']}: {cash_margin_available}")
    return float(cash_margin_available)


def merge_ins_csv_files():
    """
    The function `merge_ins_csv_files` reads and merges specific columns from NFO, BFO, and NSE CSV
    files, then saves the merged data to a new CSV file.
    :return: The function `merge_ins_csv_files` returns the merged DataFrame containing the columns
    specified in the `columns_to_keep` list. If the merging process is successful, it saves the merged
    DataFrame to a CSV file named "merged_alice_ins.csv" and returns the merged DataFrame. If an error
    occurs during the merging process, it logs the error and returns `None`.
    """
    columns_to_keep = [
        "Exch",
        "Exchange Segment",
        "Symbol",
        "Token",
        "Instrument Type",
        "Option Type",
        "Strike Price",
        "Instrument Name",
        "Formatted Ins Name",
        "Trading Symbol",
        "Expiry Date",
        "Lot Size",
        "Tick Size",
    ]

    folder_path = os.path.join(DIR_PATH)
    ins_files = ["NFO.csv", "BFO.csv", "NSE.csv"]
    file_paths = [os.path.join(folder_path, file) for file in ins_files]

    nfo_df = pd.read_csv(file_paths[0])
    bfo_df = pd.read_csv(file_paths[1])
    nse_df = pd.read_csv(file_paths[2])

    nse_df["Option Type"] = None
    nse_df["Strike Price"] = None
    nse_df["Expiry Date"] = None

    nfo_df_filtered = nfo_df[columns_to_keep]
    nse_df_filtered = nse_df[columns_to_keep]
    bfo_df_filtered = bfo_df[columns_to_keep]

    try:
        # Merge the DataFrames
        merged_df = pd.concat(
            [nfo_df_filtered, nse_df_filtered, bfo_df_filtered], ignore_index=True
        )
        merged_df["Token"] = merged_df["Token"].astype(str)
        merged_df.to_csv("merged_alice_ins.csv", index=False)
        return merged_df
    except Exception as e:
        logger.error(f"Error merging instrument files: {e}")
        return None


# This function downloads the instrument csv files from Aliceblue trading platform
def get_ins_csv_alice(user_details):
    """
    The function `get_ins_csv_alice` fetches instruments for ALICE using user details provided and
    merges the instrument CSV files.
    
    :param user_details: The `get_ins_csv_alice` function seems to be fetching instruments for ALICE
    using the provided user details. The user details typically include information about the broker
    such as the username, API key, and session ID
    :return: The function `get_ins_csv_alice` is returning the merged instrument CSV files for ALICE
    after fetching instruments for NFO, BFO, and NSE using the provided user details. If an error occurs
    during the process, it will return `None`.
    """
    logger.debug(f"Fetching instruments for ALICE using {user_details['Broker']['BrokerUsername']}")
    alice = Aliceblue(
        user_id=user_details["Broker"]["BrokerUsername"],
        api_key=user_details["Broker"]["ApiKey"],
        session_id=user_details["Broker"]["SessionId"],
    )
    try:
        alice.get_contract_master("NFO")
        alice.get_contract_master("BFO")
        alice.get_contract_master("NSE")
        alice_instrument_merged = merge_ins_csv_files()
        return alice_instrument_merged
    except Exception as e:
        logger.error(f"Error fetching instruments: {e}")
        return None

def fetch_aliceblue_holdings_value(user):
    """
    The function fetches the total invested value of holdings for a user using Aliceblue API.
    
    :param user: The `fetch_aliceblue_holdings_value` function takes a `user` parameter, which is
    expected to be a dictionary containing information about the user's broker account. The user
    dictionary should have the following structure:
    :return: The function `fetch_aliceblue_holdings_value` returns the total invested value of the
    user's holdings in Aliceblue. If there is an error during the process, it logs the error and returns
    0.0.
    """
    try:
        alice = Aliceblue(user["Broker"]["BrokerUsername"], user["Broker"]["ApiKey"], session_id=user["Broker"]["SessionId"])
        holdings = alice.get_holding_positions()

        invested_value = 0
        if holdings.get("stat") == "Not_Ok":
            invested_value = 0
        else:
            for stock in holdings['HoldingVal']:
                average_price = float(stock['Price'])
                quantity = float(stock['HUqty'])
                invested_value += average_price * quantity
        return invested_value
    except Exception as e:
        logger.error(f"Error fetching holdings for user: {user['Broker']['BrokerUsername']}: {e}")
        return 0.0


def simplify_aliceblue_order(detail):
    """
    The function `simplify_aliceblue_order` processes order details and returns a simplified dictionary
    representation of the order.
    
    :param detail: The `simplify_aliceblue_order` function takes in a dictionary `detail` containing
    various details of an order. It processes the details and returns a simplified version of the order
    information
    :return: The function `simplify_aliceblue_order` is returning a dictionary containing simplified
    order details. The keys in the dictionary include "trade_id", "avg_price", "qty", "time",
    "strike_price", "option_type", "trading_symbol", "trade_type", and "order_type". The function
    handles different scenarios based on the input details and returns the simplified order information.
    If an
    """
    try:
        if detail["optionType"] == "XX":
            strike_price = 0
            option_type = "FUT"
        else:
            strike_price = int(detail["strikePrice"])
            option_type = detail["optionType"]

        trade_id = detail["remarks"]

        if trade_id.endswith("_entry"):
            order_type = "entry"
        elif trade_id.endswith("_exit"):
            order_type = "exit"

        return {
            "trade_id": trade_id,
            "avg_price": float(detail["Avgprc"]),
            "qty": int(detail["Qty"]),
            "time": detail["OrderedTime"],
            "strike_price": strike_price,
            "option_type": option_type,
            "trading_symbol": detail["Trsym"],
            "trade_type": "BUY" if detail["Trantype"] == "B" else "SELL",
            "order_type": order_type,
        }
    except Exception as e:
        logger.error(f"Error simplifying order details: {e}")
        return None


def create_alice_obj(user_details):
    """
    The function `create_alice_obj` creates an instance of the Aliceblue class using user details such
    as BrokerUsername, ApiKey, and SessionId.
    
    :param user_details: The `user_details` parameter is expected to be a dictionary containing the
    following keys:
    :return: An Aliceblue object with the user details provided, including BrokerUsername, ApiKey, and
    SessionId.
    """
    return Aliceblue(
        user_id=user_details["BrokerUsername"],
        api_key=user_details["ApiKey"],
        session_id=user_details["SessionId"],
    )


def aliceblue_todays_tradebook(user):
    """
    The function `aliceblue_todays_tradebook` fetches the order history for a user from an AliceBlue
    trading account, handling potential errors.
    
    :param user: The `user` parameter in the `aliceblue_todays_tradebook` function is likely used to
    identify the user for whom the tradebook is being fetched. It is passed to the `create_alice_obj`
    function to create an object representing the user's account and then used to retrieve the
    :return: The function `aliceblue_todays_tradebook(user)` will return the tradebook orders for the
    user if the orders are successfully fetched. If there is an error during the process, it will return
    `None`.
    """
    try:
        alice = create_alice_obj(user)
        orders = alice.get_order_history("")
        if isinstance(orders, dict):
            if orders.get("stat") == "Not_Ok":
                return None
        return orders
    except Exception as e:
        logger.error(f"Error fetching tradebook: {e}")
        return None


def calculate_transaction_type(transaction_type):
    """
    The function `calculate_transaction_type` converts a string transaction type to an enum value.
    
    :param transaction_type: The `calculate_transaction_type` function you provided seems to be
    converting a transaction type string ("BUY" or "SELL") into an enum value (TransactionType.Buy or
    TransactionType.Sell)
    :return: The function `calculate_transaction_type` is returning the corresponding `TransactionType`
    enum value based on the input `transaction_type` string. If the input is "BUY", it returns
    `TransactionType.Buy`, if the input is "SELL", it returns `TransactionType.Sell`. If the input is
    neither "BUY" nor "SELL", it raises a ValueError indicating that the transaction_type is invalid
    """
    if transaction_type == "BUY":
        transaction_type = TransactionType.Buy
    elif transaction_type == "SELL":
        transaction_type = TransactionType.Sell
    else:
        raise ValueError("Invalid transaction_type in order_details")
    return transaction_type


def calculate_order_type(order_type):
    """
    The function `calculate_order_type` converts a given order type string to a corresponding OrderType
    enum value.
    
    :param order_type: The `calculate_order_type` function takes an `order_type` as input and converts
    it to an `OrderType` enum value based on the following conditions:
    :return: The function `calculate_order_type` is returning the corresponding `OrderType` based on the
    input `order_type`. The return value will be the appropriate `OrderType` enum value based on the
    conditions specified in the function.
    """
    if order_type.lower() == "stoploss":
        order_type = OrderType.StopLossLimit
    elif order_type.lower() == "market" or order_type.lower() == "mis":
        order_type = OrderType.Market
    elif order_type.lower() == "limit":
        order_type = OrderType.Limit
    else:
        raise ValueError("Invalid order_type in order_details")
    return order_type


def calculate_product_type(product_type):
    """
    The function `calculate_product_type` converts a string representation of a product type to an enum
    value.
    
    :param product_type: It looks like the `calculate_product_type` function is designed to convert a
    string representation of a product type into an enum value. The function checks the input
    `product_type` string and maps it to the corresponding enum value from the `ProductType` enum
    :return: The function `calculate_product_type` is returning the corresponding `ProductType` enum
    value based on the input `product_type` string. If the input `product_type` is "NRML", it returns
    `ProductType.Normal`, if it is "MIS", it returns `ProductType.Intraday`, and if it is "CNC", it
    returns `ProductType.Delivery`. If the
    """
    if product_type == "NRML":
        product_type = ProductType.Normal
    elif product_type == "MIS":
        product_type = ProductType.Intraday
    elif product_type == "CNC":
        product_type = ProductType.Delivery
    else:
        raise ValueError("Invalid product_type in order_details")
    return product_type


def get_order_status(alice, order_id):
    """
    The function `get_order_status` retrieves the status of an order and returns "PASS" if the status is
    not "rejected", otherwise it returns "FAIL".
    
    :param alice: Alice is an object or instance of a class that has a method
    `get_order_history(order_id)` which is used to retrieve the status of a specific order identified by
    `order_id`
    :param order_id: The `order_id` parameter is the unique identifier for a specific order that you
    want to retrieve the status of. It is used as input to the `get_order_status` function to fetch the
    status of the order from the `alice` object
    :return: The function `get_order_status` will return either "PASS" if the order status is not
    "rejected", or "FAIL" if there is an error fetching the order status or if the order status is
    "rejected".
    """
    try:
        order_status = alice.get_order_history(order_id)
        if order_status["Status"] == "rejected":
            return "FAIL"
        return "PASS"
    except Exception as e:
        logger.error(f"Error fetching order status: {e}")
        return "FAIL"


def ant_place_orders_for_users(orders_to_place, users_credentials):
    """
    The function `ant_place_orders_for_users` places orders for users based on the provided parameters
    and returns the order details.
    
    :param orders_to_place: It seems like the code snippet you provided is a function named
    `ant_place_orders_for_users` that is responsible for placing orders for users based on the input
    parameters. The function takes two parameters:
    :param users_credentials: It seems like the definition of the `users_credentials` parameter is
    missing in the provided code snippet. Could you please provide more information about what data or
    credentials are expected to be passed in the `users_credentials` parameter when calling the
    `ant_place_orders_for_users` function? This will help in understanding
    :return: The function `ant_place_orders_for_users` returns a dictionary `results` containing
    information about the order placement process. The dictionary includes keys such as
    "exchange_token", "order_id", "qty", "time_stamp", "trade_id", "order_status", and "tax".
    """
    from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import Instrument,get_single_ltp

    results = {
        "exchange_token": None,
        "order_id": None,
        "qty": None,
        "time_stamp": None,
        "trade_id": None,
        "message": None,
    }

    alice = create_alice_obj(users_credentials)  
    strategy = orders_to_place["strategy"]
    exchange_token = orders_to_place["exchange_token"]
    qty = orders_to_place.get("qty", 1) 
    product = orders_to_place.get("product_type")
    transaction_type = calculate_transaction_type(
        orders_to_place.get("transaction_type")
    )
    order_type = calculate_order_type(orders_to_place.get("order_type"))
    product_type = calculate_product_type(product)

    if product == "CNC":
        segment = "NSE"
    else:
        segment = Instrument().get_segment_by_exchange_token(str(exchange_token))

    limit_prc = orders_to_place.get("limit_prc", None)
    trigger_price = orders_to_place.get("trigger_prc", None)

    if limit_prc is not None:
        limit_prc = round(float(limit_prc), 2)
        if limit_prc < 0:
            limit_prc = 1.0
    elif segment == "BFO":
        if orders_to_place.get("order_type") == "Market":
            order_type = OrderType.Limit
            limit_prc = get_single_ltp(exchange_token=exchange_token, segment="BFO-OPT")
            limit_prc = round(float(limit_prc), 2)
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
        logger.debug(f"segment: {segment}")
        logger.debug(f"exchange_token: {exchange_token}")
        logger.debug(f"qty: {qty}")
        logger.debug(f"limit_prc: {limit_prc}")
        logger.debug(f"trigger_price: {trigger_price}")
        logger.debug(f"instrument: {alice.get_instrument_by_token(segment, int(exchange_token))}")
        logger.debug(f"trade_id: {orders_to_place.get('trade_id', '')}")
        results = {
            "exchange_token": int(exchange_token),
            "order_id": 123456789,
            "qty": qty,
            "time_stamp": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "trade_id": orders_to_place.get("trade_id", "")
        }
        return results

    try:
        order_id = alice.place_order(
            transaction_type=transaction_type,
            instrument=alice.get_instrument_by_token(segment, int(exchange_token)),
            quantity=qty,
            order_type=order_type,
            product_type=product_type,
            price=limit_prc,
            trigger_price=trigger_price,
            stop_loss=None,
            square_off=None,
            trailing_sl=None,
            is_amo=False,
            order_tag=orders_to_place.get("trade_id", None),
        )
        logger.success(f"Order placed. ID is: {order_id}")
        order_status = get_order_status(alice, order_id["NOrdNo"])
        if order_status == "FAIL":
            order_history = alice.get_order_history(order_id["NOrdNo"])
            message = f"Order placement failed, Reason: {order_history['RejReason']} for {orders_to_place['username']}"
            discord_bot(message, strategy)

    except Exception as e:
        message = f"Order placement failed: {e} for {orders_to_place['username']}"
        logger.error(message)
        discord_bot(message, strategy)
    
    results = {
            "exchange_token": int(exchange_token),
            "order_id": order_id["NOrdNo"],
            "qty": qty,
            "time_stamp": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "trade_id": orders_to_place.get("trade_id", ""),
            "order_status": order_status,
            "tax":orders_to_place.get("tax", 0)
        }

    return results

def ant_modify_orders_for_users(order_details, user_credentials):
    """
    The function `ant_modify_orders_for_users` modifies orders for a user based on the provided order
    details and user credentials.
    
    :param order_details: order_details is a dictionary containing details of an order, such as
    username, strategy, exchange token, transaction type, order type, product type, segment, limit
    price, trigger price, and quantity
    :param user_credentials: User credentials typically include information such as username, password,
    API key, and any other necessary authentication details that are required to access a user's account
    or perform actions on behalf of the user. These credentials are used to authenticate and authorize
    the user before allowing them to interact with the system or perform specific tasks
    :return: The function `ant_modify_orders_for_users` is returning `None` in case of an exception
    occurring during the order modification process.
    """
    from Executor.ExecutorUtils.OrderCenter.OrderCenterUtils import retrieve_order_id

    alice = create_alice_obj(user_credentials)
    order_id_dict = retrieve_order_id(
        order_details.get("username"),
        order_details.get("strategy"),
        order_details.get("exchange_token"),
    )

    transaction_type = calculate_transaction_type(order_details.get("transaction_type"))
    order_type = calculate_order_type(order_details.get("order_type"))
    product_type = calculate_product_type(order_details.get("product_type"))
    segment = order_details.get("segment")
    exchange_token = order_details.get("exchange_token")
    new_stoploss = order_details.get("limit_prc", 0.0)
    trigger_price = order_details.get("trigger_prc", None)
    try:
        for order_id, qty in order_id_dict.items():
            modify_order = alice.modify_order(
                transaction_type=transaction_type,
                order_id=str(order_id),
                instrument=alice.get_instrument_by_token(segment, exchange_token),
                quantity=qty,
                order_type=order_type,
                product_type=product_type,
                price=new_stoploss,
                trigger_price=trigger_price,
            )
            logger.info("alice modify_order", modify_order)
    except Exception as e:
        message = f"Order placement failed: {e} for {order_details['username']}"
        logger.error(message)
        discord_bot(message, order_details.get("strategy"))
        return None


def ant_create_counter_order(trade, user):
    """
    The function `ant_create_counter_order` creates a counter order based on trade information extracted
    from a trade object.
    
    :param trade: The `trade` parameter seems to be a dictionary containing information related to a
    trade. It includes keys such as "remarks", "token", "Trantype", "Pcode", "Qty", etc. The function
    `ant_create_counter_order` is designed to create a counter order based on the
    :param user: The `user` parameter is likely a user object or identifier that is being passed to the
    `ant_create_counter_order` function. It may contain information about the user who is initiating the
    trade or performing some action related to the trade. This information could be used within the
    function for logging, permissions,
    :return: The function `ant_create_counter_order` is returning a dictionary `counter_order`
    containing various details related to a trade, such as strategy name, signal, base symbol, exchange
    token, transaction type, order type, product type, trade ID, order mode, and quantity. If an error
    occurs during the process, the function will log the error and return `None`.
    """
    try:
        strategy_name = get_strategy_name_from_trade_id(trade["remarks"])
        counter_order = {
            "strategy": strategy_name,
            "signal": get_signal_from_trade_id(trade["remarks"]),
            "base_symbol": "NIFTY",  # WARNING: dummy base symbol
            "exchange_token": trade["token"],
            "transaction_type": "BUY" if trade["Trantype"] == "B" else "SELL",
            "order_type": "MARKET",
            "product_type": trade["Pcode"],
            "trade_id": trade["remarks"],
            "order_mode": "Counter",
            "qty": trade["Qty"],
        }
        return counter_order
    except Exception as e:
        logger.error(f"Error creating counter order: {e}")
        return None


def ant_create_hedge_counter_order(trade, user):
    """
    The function `ant_create_hedge_counter_order` creates a counter order based on trade information,
    with error handling in place.
    
    :param trade: The `trade` parameter in the `ant_create_hedge_counter_order` function seems to be a
    dictionary containing information related to a trade. It likely includes the following key-value
    pairs:
    :param user: The `user` parameter is not used in the `ant_create_hedge_counter_order` function. It
    is passed as an argument but not utilized within the function. If you intended to use the `user`
    parameter in some way, you would need to modify the function to incorporate it into the logic
    :return: The function `ant_create_hedge_counter_order` is returning a dictionary object
    `counter_order` containing various details related to a trade, such as strategy name, signal, base
    symbol, exchange token, transaction type, order type, product type, trade ID, order mode, and
    quantity. If an error occurs during the process, it will return `None`.
    """
    try:
        trade_id = trade["remarks"].replace("EN", "EX")
        counter_order = {
            "strategy": get_strategy_name_from_trade_id(trade["remarks"]),
            "signal": get_signal_from_trade_id(trade["remarks"]),
            "base_symbol": "NIFTY",  # WARNING: dummy base symbol
            "exchange_token": int(trade["token"]),
            "transaction_type": calculate_transaction_type_sl(trade["Trantype"]),
            "order_type": "MARKET",
            "product_type": trade["Pcode"],
            "trade_id": trade_id,
            "order_mode": "Hedge",
            "qty": trade["Qty"],
        }
        return counter_order
    except Exception as e:
        logger.error(f"Error creating hedge counter order: {e}")
        return None


def ant_create_cancel_orders(trade, user):
    """
    The function `ant_create_cancel_orders` attempts to cancel a trade order using an object created
    with user details, logging any errors encountered.
    
    :param trade: The `trade` parameter seems to be a dictionary containing information related to a
    trade. It likely includes details such as the order number (`Nstordno`) that needs to be cancelled
    :param user: The `user` parameter seems to be a dictionary containing user details, and
    specifically, it looks like it contains information related to a broker. In the code snippet
    provided, the user details related to the broker are accessed using `user["Broker"]`
    :return: None
    """
    try:
        alice = create_alice_obj(user_details=user["Broker"])
        alice.cancel_order(trade["Nstordno"])
    except Exception as e:
        logger.error(f"Error cancelling order: {e}")
        return None


def process_alice_ledger(excel_file_path):
    # Read the Excel file starting from row 4 (5th row, 0-indexed)
    all_data = pd.read_excel(excel_file_path, header=None, skiprows=4)

    # Filtering out rows where all values are NaN across columns A:K (indexes 0 to 10)
    filtered_data = all_data.dropna(how="all", subset=all_data.columns[:11])

    # Drop the NaN column headers by selecting only those columns whose first row is not NaN
    filtered_data = filtered_data.loc[:, filtered_data.iloc[0].notna()]

    # Filtering out header rows by identifying rows that match the header pattern
    headers = [
        "Date",
        "Voucher",
        "VoucherNo",
        "Code",
        "Narration",
        "ChqNo",
        "Debit",
        "Credit",
        "Running Bal",
    ]
    filtered_data = filtered_data[~filtered_data[0].astype(str).str.contains("Date")]

    # Assigning proper header to the filtered data
    filtered_data.columns = headers + list(filtered_data.columns[len(headers) :])

    # Define patterns for categorization with updated rules
    patterns = {
        "Deposits": [
            "PAYMENT DONE VIA : RAZORPAY NET",
            "RECEIVED AMOUNT THROUGH HDFC-CMS(OTH)",
            "PAYMENT DONE VIA : RAZORPAY UPI",
        ],
        "Withdrawals": ["PAYOUT OF FUNDS"],
        "Charges": [
            "CGST",
            "SGST",
            "BENEFICIARY CHARGES",
            "DP MAINTENANCE CHARGES FOR THE PERIOD",
            "CALL AND TRADE OR SQUARE OFF CHARGES FOR",
            "BENEFICIARY CHARGES FOR SETT NO",
            "BEING PAYMENT GATEWAY CHARGES DEBITED -",
        ],
        "Trades": ["BILL ENTRY FOR FO-", "BILL ENTRY FOR M-", "BILL ENTRY FOR Z-"],
        "ignore": [
            "INTER EXCHANGE SETL JV FROM NSEFNO TO BSECASH",
            "INTER EXCHANGE SETL JV FROM BSECASH TO NSEFNO",
            "Narration",
        ],
    }

    # Apply categorization patterns
    def categorize_transaction(narration):
        if pd.isna(narration):
            return "ignore"
        for category, pattern_list in patterns.items():
            for pattern in pattern_list:
                if pattern in narration:
                    return category
        return "Other"

    # Apply categorization patterns
    filtered_data["Category"] = filtered_data.apply(
        lambda row: categorize_transaction(row["Narration"]), axis=1
    )

    # Recalculate the net values for each category after re-categorization
    categorized_dfs_final = {
        category: filtered_data[filtered_data["Category"] == category]
        for category in patterns
        if category != "ignore"
    }

    # Save each categorized dataframe to a CSV file
    for category, df in categorized_dfs_final.items():
        logger.debug(f"Saving {category} transactions to CSV...")
        df.to_csv(f"{category}_transactions.csv", index=False)

    # Check for any 'Other' transactions left and save to CSV
    other_transactions_final = filtered_data[filtered_data["Category"] == "Other"]
    other_transactions_final.to_csv("Other_transactions_final.csv", index=False)

    return categorized_dfs_final


def calculate_alice_net_values(categorized_dfs):
    """
    The function `calculate_alice_net_values` calculates the net values for each category based on the
    debit and credit values in the input categorized dataframes.
    
    :param categorized_dfs: It seems like you were about to provide more information about the
    `categorized_dfs` parameter, but it seems to be missing. Could you please provide the details or the
    structure of the `categorized_dfs` parameter so that I can assist you further with the
    `calculate_alice_net_values
    :return: The function `calculate_alice_net_values` returns a dictionary where the keys are
    categories and the values are the net values calculated as the sum of "Debit" minus the sum of
    "Credit" for each category's DataFrame in the input `categorized_dfs`.
    """
    # Calculate net values for each category
    net_values = {
        category: df["Debit"].sum() - df["Credit"].sum()
        for category, df in categorized_dfs.items()
    }
    return net_values

def fetch_open_orders(user):
    """
    The function fetches open orders for a given user using an Alice object and returns the open
    positions.
    
    :param user: The `fetch_open_orders` function seems to be designed to fetch open orders for a given
    user. It takes a `user` parameter as input, which likely contains information about the user, such
    as their broker details
    :return: The function `fetch_open_orders` is attempting to fetch open orders for a given user. If
    successful, it will return the open net position. If an error occurs during the process, it will log
    the error and return `None`.
    """
    try:
        alice = create_alice_obj(user['Broker'])
        Net_position = alice.get_netwise_positions()
        open_position= Alice_Wrapper.open_net_position(Net_position)
        return open_position
    except Exception as e:
        logger.error(f"Error fetching open orders: {e}")
        return None

def get_alice_pnl(user):
    """
    The function `get_alice_pnl` retrieves the total profit and loss (PnL) for a user's positions using
    an Alice object and logs any errors encountered.
    
    :param user: The `get_alice_pnl` function seems to be designed to calculate the total profit and
    loss (PnL) for a user's positions using an object called `alice` and the `get_netwise_positions`
    method. If any errors occur during the process, it logs the error and
    :return: The function `get_alice_pnl` returns the total profit and loss (PnL) for the user's
    positions obtained from the Alice object created using the user's broker information. If an error
    occurs during the process, it logs the error and returns `None`.
    """
    try:
        alice = create_alice_obj(user['Broker'])
        positions = alice.get_netwise_positions()
        total_pnl = sum(float(position['MtoM']) for position in positions)
        return total_pnl
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
    discord_admin_bot("get_order_margin for alice blue has not been implemented yet")