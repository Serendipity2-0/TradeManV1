import os
import sys
import datetime as dt
from dotenv import load_dotenv
from pya3 import *

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

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


from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import (
    discord_bot,
)
from Executor.Strategies.StrategiesUtil import (
    get_strategy_name_from_trade_id,
    get_signal_from_trade_id,
    calculate_transaction_type_sl,
)


# This function fetches the available free cash balance for a user from the Aliceblue trading platform.
def alice_fetch_free_cash(user_details):
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

    # Merge the DataFrames
    merged_df = pd.concat(
        [nfo_df_filtered, nse_df_filtered, bfo_df_filtered], ignore_index=True
    )
    merged_df["Token"] = merged_df["Token"].astype(str)
    merged_df.to_csv("merged_alice_ins.csv", index=False)
    return merged_df


# This function downloads the instrument csv files from Aliceblue trading platform
def get_ins_csv_alice(user_details):
    logger.debug(f"Fetching instruments for ALICE using {user_details['Broker']['BrokerUsername']}")
    alice = Aliceblue(
        user_id=user_details["Broker"]["BrokerUsername"],
        api_key=user_details["Broker"]["ApiKey"],
        session_id=user_details["Broker"]["SessionId"],
    )
    alice.get_contract_master("NFO")
    alice.get_contract_master("BFO")
    alice.get_contract_master("NSE")
    alice_instrument_merged = merge_ins_csv_files()
    return alice_instrument_merged


# This function fetches the holdings in the user account
def fetch_aliceblue_holdings(username, api_key, session_id):
    alice = Aliceblue(username, api_key, session_id)
    holdings = alice.get_holding_positions()
    return holdings


def simplify_aliceblue_order(detail):
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


def create_alice_obj(user_details):
    return Aliceblue(
        user_id=user_details["BrokerUsername"],
        api_key=user_details["ApiKey"],
        session_id=user_details["SessionId"],
    )


def aliceblue_todays_tradebook(user):
    alice = create_alice_obj(user)
    orders = alice.get_order_history("")
    if orders.get("stat") == "Not_Ok":
        return None
    return orders


def calculate_transaction_type(transaction_type):
    if transaction_type == "BUY":
        transaction_type = TransactionType.Buy
    elif transaction_type == "SELL":
        transaction_type = TransactionType.Sell
    else:
        raise ValueError("Invalid transaction_type in order_details")
    return transaction_type


def calculate_order_type(order_type):
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
    order_status = alice.get_order_history(order_id)
    if order_status["Status"] == "rejected":
        return "FAIL"


def ant_place_orders_for_users(orders_to_place, users_credentials):
    from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import (
        Instrument as Instru,
    )

    results = {
        "exchange_token": None,
        "order_id": None,
        "qty": None,
        "time_stamp": None,
        "trade_id": None,
        "message": None,
    }

    alice = create_alice_obj(
        users_credentials
    )  # Create an Aliceblue instance with user's broker credentials
    strategy = orders_to_place["strategy"]
    exchange_token = orders_to_place["exchange_token"]
    qty = orders_to_place.get("qty", 1)  # Default quantity to 1 if not specified
    product = orders_to_place.get("product_type")
    transaction_type = calculate_transaction_type(
        orders_to_place.get("transaction_type")
    )
    order_type = calculate_order_type(orders_to_place.get("order_type"))
    product_type = calculate_product_type(product)

    if product == "CNC":
        segment = "NSE"
    else:
        segment = Instru().get_segment_by_exchange_token(str(exchange_token))

    limit_prc = orders_to_place.get("limit_prc", None)
    trigger_price = orders_to_place.get("trigger_prc", None)

    if limit_prc is not None:
        limit_prc = round(float(limit_prc), 2)
        if limit_prc < 0:
            limit_prc = 1.0
    else:
        limit_prc = 0.0

    if trigger_price is not None:
        trigger_price = round(float(trigger_price), 2)
        if trigger_price < 0:
            trigger_price = 1.5

    try:
        # logger.debug(f"transaction_type: {transaction_type}")
        # logger.debug(f"order_type: {order_type}")
        # logger.debug(f"product_type: {product_type}")
        # logger.debug(f"segment: {segment}")
        # logger.debug(f"exchange_token: {exchange_token}")
        # logger.debug(f"qty: {qty}")
        # logger.debug(f"limit_prc: {limit_prc}")
        # logger.debug(f"trigger_price: {trigger_price}")
        # logger.debug(f"instrument: {alice.get_instrument_by_token(segment, int(exchange_token))}")
        # logger.debug(f"trade_id: {orders_to_place.get('trade_id', '')}")
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
            "trade_id": orders_to_place.get("trade_id", "")
        }

    return results

def ant_modify_orders_for_users(order_details, user_credentials):
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


def ant_create_hedge_counter_order(trade, user):
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


def ant_create_cancel_orders(trade, user):
    alice = create_alice_obj(user_details=user["Broker"])
    alice.cancel_order(trade["Nstordno"])


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
    # Calculate net values for each category
    net_values = {
        category: df["Debit"].sum() - df["Credit"].sum()
        for category, df in categorized_dfs.items()
    }
    return net_values

def fetch_open_orders(user):
    alice = create_alice_obj(user['Broker'])
    Net_position = alice.get_netwise_positions()
    open_position= Alice_Wrapper.open_net_position(Net_position)
    return open_position