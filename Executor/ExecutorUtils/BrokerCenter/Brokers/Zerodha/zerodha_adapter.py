import datetime
import pandas as pd
from kiteconnect import KiteConnect
import os, sys
from six.moves.urllib.parse import urljoin
import aiohttp
import json
import kiteconnect.exceptions as ex

DIR = os.getcwd()
sys.path.append(DIR)

from Executor.NSEStrategies.NSEStrategiesUtil import (
    get_strategy_name_from_trade_id,
    get_signal_from_trade_id,
    calculate_transaction_type_sl,
)
from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import (
    discord_bot,
)
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()


class async_KiteConnect(KiteConnect):
    async def place_order(
        self,
        variety,
        exchange,
        tradingsymbol,
        transaction_type,
        quantity,
        product,
        order_type,
        price=None,
        validity=None,
        validity_ttl=None,
        disclosed_quantity=None,
        trigger_price=None,
        iceberg_legs=None,
        iceberg_quantity=None,
        auction_number=None,
        tag=None,
    ):
        """Place an order."""
        params = locals()
        del params["self"]

        for k in list(params.keys()):
            if params[k] is None:
                del params[k]

        order_id = await self._post(
            "order.place", url_args={"variety": variety}, params=params
        )
        return order_id["order_id"]

    async def _post(
        self, route, url_args=None, params=None, is_json=False, query_params=None
    ):
        """Alias for sending a POST request."""
        return await self._request(
            route,
            "POST",
            url_args=url_args,
            params=params,
            is_json=is_json,
            query_params=query_params,
        )

    async def async_post(
        self,
        url,
        json,
        data,
        params,
        headers,
        verify,
        allow_redirects,
        timeout,
        proxies,
    ):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=json,
                data=data,
                params=params,
                headers=headers,
                # ssl=verify,
                # allow_redirects=allow_redirects,
                timeout=timeout,
                # proxy_auth=proxies
            ) as response:
                return response.status, await response.read(), response.headers

    async def basket_order_margins(self, params, consider_positions=True, mode=None):
        """
        Calculate total margins required for basket of orders including margin benefits

        - `params` is list of orders to fetch basket margin
        - `consider_positions` is a boolean to consider users positions
        - `mode` is margin response mode type. compact - Compact mode will only give the total margins
        """
        return await self._post(
            "order.margins.basket",
            params=params,
            is_json=True,
            query_params={"consider_positions": "true", "mode": mode},
        )

    async def _request(
        self,
        route,
        method,
        url_args=None,
        params=None,
        is_json=False,
        query_params=None,
    ):
        """Make an HTTP request."""
        # Form a restful URL
        if url_args:
            uri = self._routes[route].format(**url_args)
        else:
            uri = self._routes[route]

        url = urljoin(self.root, uri)

        # Custom headers
        headers = {
            "X-Kite-Version": self.kite_header_version,
            "User-Agent": self._user_agent(),
        }

        if self.api_key and self.access_token:
            # set authorization header
            auth_header = self.api_key + ":" + self.access_token
            headers["Authorization"] = "token {}".format(auth_header)

        if self.debug:
            logger.debug(
                "Request: {method} {url} {params} {headers}".format(
                    method=method, url=url, params=params, headers=headers
                )
            )

        # prepare url query params
        if method in ["GET", "DELETE"]:
            query_params = params

        try:
            status_code, content, headers = await self.async_post(
                url,
                json=params if (method in ["POST", "PUT"] and is_json) else None,
                data=params if (method in ["POST", "PUT"] and not is_json) else None,
                params=query_params,
                headers=headers,
                verify=not self.disable_ssl,
                allow_redirects=True,
                timeout=self.timeout,
                proxies=self.proxies,
            )
        # Any requests lib related exceptions are raised here - https://requests.readthedocs.io/en/latest/api/#exceptions
        except Exception as e:
            raise e

        if self.debug:
            logger.debug(
                "Response: {code} {content}".format(code=status_code, content=content)
            )

        # Validate the content type.
        if "json" in headers["content-type"]:
            try:
                data = json.loads(content.decode("utf-8"))
            except ValueError:
                raise ex.DataException(
                    "Couldn't parse the JSON response received from the server: {content}".format(
                        content=content
                    )
                )

            # api error
            if data.get("status") == "error" or data.get("error_type"):
                # Call session hook if its registered and TokenException is raised
                if (
                    self.session_expiry_hook
                    and status_code == 403
                    and data["error_type"] == "TokenException"
                ):
                    self.session_expiry_hook()

                # native Kite errors
                exp = getattr(ex, data.get("error_type"), ex.GeneralException)
                raise exp(data["message"], code=status_code)

            return data["data"]
        elif "csv" in headers["content-type"]:
            return content
        else:
            raise ex.DataException(
                "Unknown Content-Type ({content_type}) with response: ({content})".format(
                    content_type=headers["content-type"], content=content
                )
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


def create_async_kite_obj(user_details=None, api_key=None, access_token=None):
    if api_key and access_token:
        return async_KiteConnect(api_key=api_key, access_token=access_token)
    elif user_details:
        return async_KiteConnect(
            api_key=user_details["ApiKey"], access_token=user_details["SessionId"]
        )
    else:
        raise ValueError(
            "Either user_details or api_key and access_token must be provided"
        )


def zerodha_fetch_free_cash(user_details):
    """
    Fetches and returns the free cash balance from a Zerodha account using user credentials.

    Args:
        user_details (dict): Dictionary containing the API credentials.

    Returns:
        float: The free cash balance in the user's account.

    Raises:
        Exception: If there is an issue fetching the balance.
    """
    logger.debug(f"Fetching free cash for {user_details['BrokerUsername']}")
    kite = KiteConnect(
        api_key=user_details["ApiKey"], access_token=user_details["SessionId"]
    )
    try:
        # Fetch the account balance details
        balance_details = kite.margins(segment="equity")
        # Extract the 'cash' value
        cash_balance = balance_details.get("cash", 0)

        # If 'cash' key is not at the top level, we need to find where it is
        if cash_balance == 0 and "cash" not in balance_details:
            # Look for 'cash' in nested dictionaries
            for key, value in balance_details.items():
                if isinstance(value, dict) and "cash" in value:
                    cash_balance = value.get("cash", 0)
                    break
        logger.info(
            f"Free cash fetched for {user_details['BrokerUsername']}: {cash_balance}"
        )
        return cash_balance
    except Exception as e:
        logger.error(
            f"Error fetching free cash: {e} for {user_details['BrokerUsername']}"
        )
        return 0


def get_csv_kite(user_details):
    """
    Fetches instrument data from Kite and returns it as a pandas DataFrame.

    Args:
        user_details (dict): Dictionary containing user API credentials.

    Returns:
        DataFrame: A DataFrame of instruments from Kite, or None if there is an error.

    Raises:
        Exception: If fetching instruments fails.
    """
    logger.debug(
        f"Fetching instruments for KITE using {user_details['Broker']['BrokerUsername']}"
    )
    try:
        kite = KiteConnect(
            api_key=user_details["Broker"]["ApiKey"],
            access_token=user_details["Broker"]["SessionId"],
        )
        instrument_dump = kite.instruments()
        instrument_df = pd.DataFrame(instrument_dump)
        instrument_df["exchange_token"] = instrument_df["exchange_token"].astype(str)
        return instrument_df
    except Exception as e:
        logger.error(
            f"Error fetching instruments for KITE: {e} for {user_details['Broker']['BrokerUsername']}"
        )
        return None


def fetch_zerodha_holdings_value(user):
    """
    Calculates and returns the total value of all holdings in a user's Zerodha account.

    Args:
        user (dict): Dictionary containing user's broker credentials.

    Returns:
        float: Total value of holdings, or 0.0 if there is an error.

    Raises:
        Exception: If fetching holdings fails.
    """
    try:
        kite = KiteConnect(
            api_key=user["Broker"]["ApiKey"], access_token=user["Broker"]["SessionId"]
        )
        holdings = kite.holdings()
        return sum(stock["average_price"] * stock["quantity"] for stock in holdings)
    except Exception as e:
        logger.error(
            f"Error fetching holdings for user {user['Broker']['BrokerUsername']}: {e}"
        )
        return 0.0


def simplify_zerodha_order(detail):
    """
    Simplifies order details into a more manageable dictionary format, focusing on key aspects.

    Args:
        detail (dict): Dictionary containing the order details.

    Returns:
        dict: Simplified version of the order details.

    Raises:
        Exception: If there is an error during processing.
    """
    logger.debug(f"Processing order details: {detail['tag']}")
    try:
        trade_symbol = detail["tradingsymbol"]

        # Check if the tradingsymbol is of futures type
        if trade_symbol.endswith("FUT"):
            strike_price = 0
            option_type = "FUT"
        else:
            strike_price = int(
                trade_symbol[-7:-2]
            )  # Convert to integer to store as number
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
    except Exception as e:
        logger.error(f"Error simplifying order details: {e}")
        return None


def zerodha_todays_tradebook(user):
    """
    Fetches and returns the list of today's trades from a user's Zerodha account.

    Args:
        user (dict): Dictionary containing the user's API credentials.

    Returns:
        list: List of today's trades or None if there is an error or no trades.

    Raises:
        Exception: If there is an error fetching the tradebook.
    """
    try:
        kite = KiteConnect(api_key=user["ApiKey"], access_token=user["SessionId"])
        orders = kite.orders()
        if not orders:
            return None
        return orders
    except Exception as e:
        logger.error(f"Error fetching tradebook for KITE: {e}")
        return None


def calculate_transaction_type(kite, transaction_type):
    """
    Converts a transaction type string into the corresponding KiteConnect constant.

    Args:
        kite (KiteConnect): The KiteConnect instance.
        transaction_type (str): The transaction type as a string, e.g., "BUY" or "SELL".

    Returns:
        str: The corresponding KiteConnect constant for the transaction type.

    Raises:
        ValueError: If the transaction type is invalid.
    """
    if transaction_type == "BUY":
        transaction_type = kite.TRANSACTION_TYPE_BUY
    elif transaction_type == "SELL":
        transaction_type = kite.TRANSACTION_TYPE_SELL
    else:
        raise ValueError("Invalid transaction_type in order_details")
    return transaction_type


def calculate_order_type(kite, order_type):
    """
    Determines and returns the Kite order type based on the given string.

    Args:
    kite: A KiteConnect object.
    order_type (str): The type of order as a string.

    Returns:
    str: The order type as defined in the KiteConnect constants.

    Raises:
    ValueError: If the provided order_type is not recognized.
    """
    if order_type.lower() == "stoploss" or order_type.lower() == "sl":
        order_type = kite.ORDER_TYPE_SL
    elif order_type.lower() == "market" or order_type.lower() == "mis":
        order_type = kite.ORDER_TYPE_MARKET
    elif order_type.lower() == "limit":
        order_type = kite.ORDER_TYPE_LIMIT
    else:
        raise ValueError("Invalid order_type in order_details")
    return order_type


def calculate_product_type(kite, product_type):
    """
    Determines and returns the Kite product type based on the given string.

    Args:
    kite: A KiteConnect object.
    product_type (str): The type of product as a string.

    Returns:
    str: The product type as defined in the KiteConnect constants.

    Raises:
    ValueError: If the provided product_type is not recognized.
    """
    if product_type == "NRML":
        product_type = kite.PRODUCT_NRML
    elif product_type == "MIS":
        product_type = kite.PRODUCT_MIS
    elif product_type == "CNC":
        product_type = kite.PRODUCT_CNC
    else:
        raise ValueError("Invalid product_type in order_details")
    return product_type


def get_order_status(user_credentials, order_id):
    """
    Fetches and returns the order status for a given order ID.

    Args:
    kite: A KiteConnect object.
    order_id (int): The ID of the order.

    Returns:
    str: The status of the order, or "FAIL" if the order cannot be fetched or does not pass.

    Raises:
    Exception: If any errors occur during the fetching of the order status.
    """
    try:
        kite = KiteConnect(
            api_key=user_credentials["ApiKey"],
            access_token=user_credentials["SessionId"],
        )
        order_history = kite.order_history(order_id=order_id)
        for order in order_history:
            if order.get("status") == "REJECTED":
                return order.get("status_message")
            elif (
                order.get("status") == "COMPLETE"
                or order.get("status") == "TRIGGER PENDING"
                or order.get("status") == "OPEN"
            ):
                return "PASS"
        return "FAIL"
    except Exception as e:
        logger.error(f"Error fetching order status for order_id {order_id}: {e}")
        return "FAIL"


async def kite_place_orders_for_users(orders_to_place, users_credentials):
    from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import (
        Instrument,
        get_single_ltp,
    )

    results = {
        "avg_prc": None,
        "exchange_token": None,
        "order_id": None,
        "qty": None,
        "time_stamp": None,
        "trade_id": None,
        "message": None,
    }

    kite = create_async_kite_obj(
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
        segment_type = Instrument().get_exchange_by_exchange_token(str(exchange_token))
        trading_symbol = Instrument().get_trading_symbol_by_exchange_token(
            str(exchange_token), segment_type
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
            "time_stamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "trade_id": orders_to_place.get("trade_id", ""),
        }
        return results

    order_status = None

    try:
        order_id = await kite.place_order(
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
        order_status = get_order_status(users_credentials, order_id)
        if order_status != "PASS":
            message = f"Order placement failed: {order_status} for {orders_to_place['username']}"
            discord_bot(message, strategy)

    except Exception as e:
        message = f"Order placement failed: {e} for {orders_to_place['username']}"
        logger.error(message)
        discord_bot(message, strategy)
        order_status = "FAIL"

    results = {
        "exchange_token": int(exchange_token),
        "order_id": order_id,
        "qty": qty,
        "time_stamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "trade_id": orders_to_place.get("trade_id", ""),
        "order_status": order_status,
    }

    return results


def kite_modify_orders_for_users(order_details, users_credentials):
    """
    Modifies existing orders for users based on provided order details and user credentials.

    Args:
        order_details (dict): A dictionary containing the details needed to modify an order including:
            - username (str): Username associated with the order.
            - strategy (str): Strategy under which the order was placed.
            - exchange_token (str): Token identifying the exchange where the order was placed.
            - limit_prc (float, optional): New limit price for the order.
            - trigger_prc (float, optional): New trigger price for the order.
        users_credentials (dict): Credentials of the users whose orders are being modified.

    Returns:
        None: Returns None if the order modification was successful or if it failed.

    Raises:
        Exception: If the order modification fails due to API error or data validation issues.
    """
    from Executor.ExecutorUtils.OrderCenter.OrderCenterUtils import retrieve_order_id

    kite = create_async_kite_obj(
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
                quantity=qty,
            )
            logger.info("zerodha order modified", modify_order)
    except Exception as e:
        message = f"Order placement failed: {e} for {order_details['username']}"
        logger.error(message)
        discord_bot(message, order_details.get("strategy"))
        return None


def kite_create_sl_counter_order(trade, user):
    """
    Creates a stop-loss counter order based on a given trade and user details.

    Args:
        trade (dict): Trade details required to create the counter order.
        user (dict): User details needed for API credentials.

    Returns:
        dict: A dictionary containing the details of the counter order if successful, or None if it fails.

    Raises:
        Exception: If creating the counter order fails.
    """
    from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import Instrument

    try:
        strategy_name = get_strategy_name_from_trade_id(trade["tag"])
        exchange_token = Instrument().get_exchange_token_by_token(
            trade["instrument_token"]
        )
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
    except Exception as e:
        logger.error(f"Error creating counter order: {e}")
        return None


def kite_create_cancel_order(trade, user):
    """
    Cancels an existing order based on the trade and user details.

    Args:
        trade (dict): Trade details for the order that needs to be cancelled.
        user (dict): User details needed for API credentials.

    Returns:
        None: Returns None if the order cancellation was successful or failed.

    Raises:
        Exception: If cancelling the order fails.
    """
    try:
        kite = create_async_kite_obj(user_details=user["Broker"])
        kite.cancel_order(variety=kite.VARIETY_REGULAR, order_id=trade["order_id"])
    except Exception as e:
        logger.error(f"Error cancelling order: {e}")
        return None


def kite_create_hedge_counter_order(trade, user):
    """
    Creates a hedge counter order for a given trade and user.

    Args:
        trade (dict): Details of the trade for which the hedge order is to be created.
        user (dict): User details necessary for API credentials.

    Returns:
        dict: A dictionary containing the hedge order details if successful, or None if it fails.

    Raises:
        Exception: If creating the hedge order fails.
    """
    from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import Instrument

    try:
        strategy_name = get_strategy_name_from_trade_id(trade["tag"])
        exchange_token = Instrument().get_exchange_token_by_token(
            trade["instrument_token"]
        )
        # i want to replace EN to EX in the trade['tag']
        trade_id = trade["tag"].replace("EN", "EX")

        counter_order = {
            "strategy": strategy_name,
            "signal": get_signal_from_trade_id(trade["tag"]),
            "base_symbol": "NIFTY",  # WARNING: dummy base symbol
            "exchange_token": exchange_token,
            "transaction_type": calculate_transaction_type_sl(
                trade["transaction_type"]
            ),
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


def process_kite_ledger(csv_file_path):
    """
    Processes and categorizes transactions from a CSV file containing Kite ledger data.

    Args:
        csv_file_path (str): The file path to the CSV file containing the ledger data.

    Returns:
        dict: A dictionary of categorized DataFrames corresponding to each transaction category.

    Raises:
        Exception: If there is an issue reading the CSV file or processing the data.
    """
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
    other_transactions_final.to_csv("kite_other.csv", index=False)

    # save categorized_dfs to csv as {category}.csv
    for category, df in categorized_dfs.items():
        df.to_csv(f"kite_{category}.csv", index=False)

    return categorized_dfs


def calculate_kite_net_values(categorized_dfs):
    """
    Calculates net values for each transaction category from categorized DataFrames.

    Args:
        categorized_dfs (dict): A dictionary of DataFrames for each transaction category.

    Returns:
        dict: A dictionary containing the net values for each category.
    """
    # Calculate net values for each category
    net_values = {
        category: df["debit"].sum() - df["credit"].sum()
        for category, df in categorized_dfs.items()
    }
    return net_values


def fetch_kite_open_orders(user_details):
    """
    Fetches open orders from Kite for a given user.

    Args:
        user_details (dict): User details required to access their Kite account.

    Returns:
        list: A list of open orders if successful, None otherwise.

    Raises:
        Exception: If fetching the orders fails.
    """
    try:
        kite = KiteConnect(
            api_key=user_details["Broker"]["ApiKey"],
            access_token=user_details["Broker"]["SessionId"],
        )
        positions = kite.positions()
        return positions
    except Exception as e:
        logger.error(f"Error fetching open orders for KITE: {e}")
        return None


def get_zerodha_pnl(user):
    """
    Retrieves the profit and loss for a given user's Zerodha account.

    Args:
        user (dict): User details needed to access their Zerodha account.

    Returns:
        float: The total profit or loss.

    Raises:
        Exception: If there is an error in fetching the profit and loss data.
    """
    try:
        kite = KiteConnect(
            api_key=user["Broker"]["ApiKey"], access_token=user["Broker"]["SessionId"]
        )
        positions = kite.positions()["net"]
        total_pnl = sum(position["pnl"] for position in positions)
        return total_pnl
    except Exception as e:
        logger.error(
            f"Error fetching pnl for user: {user['Broker']['BrokerUsername']}: {e}"
        )
        return None


async def get_kite_order_tax(order, user_credentials, broker):
    """
    Calculates the required tax for an order based on the order details and user credentials.

    Args:
        order (dict): Details of the order for which tax needs to be calculated.
        user_credentials (dict): Credentials required for accessing the user's trading account.
        broker (str): Name of the broker to apply specific adjustments if needed.

    Returns:
        float: The calculated tax for the order.

    Raises:
        Exception: If there is an error in calculating the tax.
    """
    from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import Instrument
    from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import (
        get_single_ltp,
    )
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
        fetch_primary_accounts_from_firebase,
    )

    zerodha_primary = os.getenv("ZERODHA_PRIMARY_ACCOUNT")
    basket_order = []
    primary_account_session_id = fetch_primary_accounts_from_firebase(zerodha_primary)

    kite = create_async_kite_obj(
        api_key=primary_account_session_id["Broker"]["ApiKey"],
        access_token=primary_account_session_id["Broker"]["SessionId"],
    )
    exchange_token = order["exchange_token"]
    product = order.get("product_type")
    transaction_type = order.get("transaction_type")
    if transaction_type == "B":
        transaction_type = "BUY"
    elif transaction_type == "S":
        transaction_type = "SELL"

    transaction_type = calculate_transaction_type(kite, transaction_type)
    order_type = calculate_order_type(kite, order.get("order_type"))
    # TODO: This is a temporary fix for firstock untill firstock starts providing the tax
    if product == "I":
        product = "MIS"
    elif product == "C":
        product = "CNC"
    product_type = calculate_product_type(kite, product)
    if product == "CNC":
        segment_type = kite.EXCHANGE_NSE
        trading_symbol = Instrument().get_trading_symbol_by_exchange_token(
            exchange_token, "NSE"
        )
    else:
        segment_type = Instrument().get_exchange_by_exchange_token(str(exchange_token))
        trading_symbol = Instrument().get_trading_symbol_by_exchange_token(
            str(exchange_token)
        )

    limit_prc = order.get("limit_prc", None)
    trigger_price = order.get("trigger_prc", None)

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

    tax_order = {
        "variety": kite.VARIETY_REGULAR,
        "exchange": segment_type,
        "price": limit_prc,
        "tradingsymbol": trading_symbol,
        "transaction_type": transaction_type,
        "quantity": order["qty"],
        "trigger_price": trigger_price,
        "product": product_type,
        "order_type": order_type,
    }
    basket_order.append(tax_order)
    tax_details = await kite.basket_order_margins(basket_order, mode="compact")
    tax = tax_details["orders"][0]["charges"]["total"]
    tax = round(tax, 2)
    if broker.lower() == "aliceblue":
        tax = float(tax) - 5
    return tax


def get_margin_utilized(user_credentials):
    """
    Calculates and returns the margin utilized in a user's trading account.

    Args:
        user_credentials (dict): User credentials required to access their trading account.

    Returns:
        float: The margin utilized.

    Raises:
        Exception: If there is an error in fetching the margin details.
    """
    kite = create_async_kite_obj(user_details=user_credentials)
    live_bal = kite.margins().get("equity", {}).get("available", {}).get("live_balance")
    opening_bal = (
        kite.margins().get("equity", {}).get("available", {}).get("opening_balance")
    )
    funds_utilized = opening_bal - live_bal
    return funds_utilized


def get_broker_payin(user):
    """
    Retrieves the intraday payin amount for a given user's broker account.

    Args:
        user (dict): User details needed to access their broker account.

    Returns:
        float: The intraday payin amount.

    Raises:
        Exception: If there is an error in fetching the payin amount.
    """
    kite = create_async_kite_obj(user_details=user["Broker"])
    payin = float(
        kite.margins().get("equity", {}).get("available", {}).get("intraday_payin", 0)
    )
    return payin
