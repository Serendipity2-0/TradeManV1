import datetime as dt
import os
import re
import sys
from datetime import time
from typing import Dict, List, Optional, Union
import asyncio
import pandas as pd
from dotenv import load_dotenv
from pydantic import BaseModel

DIR = os.getcwd()
sys.path.append(DIR)
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

fno_info_path = os.getenv("FNO_INFO_PATH")
user_db_collection = os.getenv("FIREBASE_USER_COLLECTION")
STRATEGIES_DB = os.getenv("FIREBASE_STRATEGY_COLLECTION")

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import (
    fetch_collection_data_firebase,
    update_fields_firebase,
)
from Executor.ExecutorUtils.ExeUtils import holidays

logger = LoggerSetup()


# Sub-models for various parameter types
class EntryParams(BaseModel):
    EntryTime: str
    HedgeMultiplier: Optional[int] = None
    InstrumentToday: Optional[Union[str, dict]] = None
    SLMultiplier: Optional[float] = None
    StrikeMultiplier: Optional[int] = None
    HeikinAshiMAPeriod: Optional[int] = None
    SupertrendPeriod: Optional[int] = None
    SupertrendMultiplier: Optional[int] = None
    EMAPeriod: Optional[int] = None

    class Config:
        extra = "allow"


class ExitParams(BaseModel):
    SLType: str
    SquareOffTime: Optional[str] = None
    LastBuyTime: Optional[str] = None
    AvgSLPoints: Optional[float] = None

    class Config:
        extra = "allow"


class ExtraInformation(BaseModel):
    QtyCalc: str
    PriceRef: Optional[Dict[str, List[int]]] = None
    Interval: Optional[str] = None
    HedgeDistance: Optional[int] = None
    Prediction: Optional[str] = None
    HedgeExchangeToken: Optional[int] = None
    FuturesExchangeToken: Optional[int] = None
    MultiLeg: Optional[bool] = None

    class Config:
        extra = "allow"


class GeneralParams(BaseModel):
    ExpiryType: Union[str, List[str]]
    HedgeTransactionType: Optional[str] = None
    MainTransactionType: Optional[str] = None
    TransactionType: Optional[str] = None
    OrderType: str
    ProductType: str
    StrategyType: Optional[str] = None
    TimeFrame: str
    ATRPeriod: Optional[int] = None
    IndicesTokens: Optional[Dict[str, int]] = None

    class Config:
        extra = "allow"


class StrategyInfo(BaseModel):
    Direction: Optional[str]
    MarginUsed: Optional[float]
    PeakLoss: Optional[float]
    PeakProfit: Optional[float]

    class Config:
        extra = "allow"


class TodayOrder(BaseModel):
    EntryPrc: Optional[float] = None
    EntryTime: Optional[dt.datetime] = None
    ExitPrc: Optional[float] = None
    ExitTime: Optional[time] = None
    Signal: Optional[str] = None
    StrategyInfo: Optional[Dict[str, Union[str, float]]] = None
    TradeId: Optional[str] = None

    class Config:
        extra = "allow"


class MarketInfoParams(BaseModel):
    OBQtyAmplifier: Optional[float] = None
    OSQtyAmplifier: Optional[float] = None
    TradeView: str


class StrategyBase(BaseModel):
    Description: str
    EntryParams: EntryParams
    ExitParams: ExitParams
    ExtraInformation: ExtraInformation
    GeneralParams: GeneralParams
    Instruments: List[str]
    NextTradeId: Optional[str] = None
    StrategyName: str
    StrategyPrefix: Optional[str] = None
    MarketInfoParams: MarketInfoParams
    TodayOrders: Optional[Dict[str, TodayOrder]] = None

    class Config:
        extra = "allow"

    def __init__(self, **data):
        """
        The above Python function is an `__init__` method that initializes an object with the provided data
        and stores the raw data in an attribute.
        """
        super().__init__(**data)
        self._raw_data = data

    def get_raw_field(self, field_name: str):
        """
        The `get_raw_field` function retrieves a specific field from the raw data using the field name as a
        key.

        :param field_name: The `field_name` parameter in the `get_raw_field` method is a string that
        represents the name of the field you want to retrieve from the `_raw_data` dictionary
        :type field_name: str
        :return: The `get_raw_field` method is returning the value associated with the `field_name` key in
        the `_raw_data` dictionary. If the key does not exist in the dictionary, it will return `None`.
        """
        return self._raw_data.get(field_name, None)

    @classmethod
    def load_from_db(cls, strategy_name: str):
        """
        The `load_from_db` function retrieves data for a strategy from a Firebase collection and parses it
        into an object.

        :param cls: In the given code snippet, `cls` is a conventional name used to represent the class
        itself within a class method. It is used to refer to the class object on which the method is being
        called. In this context, `cls` is used as a reference to the class that contains the `
        :param strategy_name: The `strategy_name` parameter is a string that represents the name of the
        strategy that you want to load from the database. It is used as a key to fetch the corresponding
        data from the database
        :type strategy_name: str
        :return: An instance of the class `cls` with data parsed from the database for the specified
        `strategy_name` is being returned.
        """
        data = fetch_collection_data_firebase(STRATEGIES_DB, document=strategy_name)
        if data is None:
            raise ValueError(f"No data found for strategy {strategy_name}")
        return cls.parse_obj(data)

    @staticmethod
    def reload_strategy(strategy_name: str):
        """
        The `reload_strategy` function reloads a strategy from the database based on the provided strategy
        name.

        :param strategy_name: The `strategy_name` parameter in the `reload_strategy` function is a string
        that represents the name of the strategy to be reloaded from the database
        :type strategy_name: str
        :return: The `reload_strategy` function is returning an instance of a strategy loaded from the
        database using the `StrategyBase.load_from_db` method.
        """
        return StrategyBase.load_from_db(strategy_name)

    ###########################################################################
    def get_option_type(self, prediction, strategy_option_mode):
        """
        The `get_option_type` function determines the option type (CE or PE) based on the given prediction and strategy option mode.

        :param prediction: The market prediction, either "Bullish" or "Bearish"
        :type prediction: str
        :param strategy_option_mode: The option mode, either "OB" or "OS"
        :type strategy_option_mode: str
        :return: The option type (CE or PE)
        """
        if strategy_option_mode == "OS":
            return "CE" if prediction == "Bearish" else "PE"
        elif strategy_option_mode == "OB":
            return "CE" if prediction == "Bullish" else "PE"
        else:
            logger.error("Invalid option mode")

    def get_hedge_option_type(self, prediction):
        """
        The `get_hedge_option_type` function determines the hedge option type (CE or PE) based on the given prediction.

        :param prediction: The market prediction, either "Bullish" or "Bearish"
        :type prediction: str
        :return: The hedge option type (CE or PE)
        """
        if prediction == "Bearish":
            return "CE"
        elif prediction == "Bullish":
            return "PE"
        else:
            logger.error("Invalid option mode")

    def get_transaction_type(self, prediction):
        """
        The `get_transaction_type` function determines the transaction type (BUY or SELL) based on the given prediction.

        :param prediction: The market prediction, either "Bullish" or "Bearish"
        :type prediction: str
        :return: The transaction type (BUY or SELL)
        """
        if prediction == "Bearish":
            return "SELL"
        elif prediction == "Bullish":
            return "BUY"
        else:
            logger.error("Invalid option mode")

    def get_token_from_info(self, base_symbol):
        """
        The `get_token_from_info` function retrieves the token for a given base symbol from the fno_info CSV file.

        :param base_symbol: The base symbol for which to retrieve the token
        :type base_symbol: str
        :return: The token associated with the base symbol
        """
        fno_info_df = pd.read_csv(fno_info_path)
        token = fno_info_df.loc[
            fno_info_df["base_symbol"] == base_symbol, "token"
        ].values
        if len(token) == 0:
            return f"{base_symbol} not found"
        return token[0]

    def determine_expiry_index(self):
        """
        The `determine_expiry_index` function determines the expiry index based on the current day of the week.

        :return: The expiry index and its corresponding token
        """
        day = dt.datetime.today().weekday()
        if day == 0:  # Monday
            return "MIDCPNIFTY", "288009"
        elif day == 1:  # Tuesday
            return "FINNIFTY", "257801"
        elif day == 2:  # Wednesday
            return "BANKNIFTY", "260105"
        elif day == 3:  # Thursday
            return "NIFTY", "256265"
        elif day == 4:  # Friday
            return "SENSEX", "265"
        elif day == 5:  # Saturday
            return "MIDCPNIFTY", "288009"
        elif day == 6:  # Sunday
            return "MIDCPNIFTY", "288009"
        else:
            return "No expiry today"

    def round_strike_prc(self, ltp, base_symbol):
        """
        The `round_strike_prc` function rounds the last traded price (ltp) to the nearest strike price based on the strike step size for the given base symbol.

        :param ltp: The last traded price
        :type ltp: float
        :param base_symbol: The base symbol for which to round the strike price
        :type base_symbol: str
        :return: The rounded strike price
        """
        strike_step = self.get_strike_step(base_symbol)
        return round(ltp / strike_step) * strike_step

    def get_strike_step(self, base_symbol):
        """
        The `get_strike_step` function retrieves the strike step size for a given base symbol from the fno_info CSV file.

        :param base_symbol: The base symbol for which to retrieve the strike step size
        :type base_symbol: str
        :return: The strike step size
        """
        strike_step_df = pd.read_csv(fno_info_path)
        strike_step = strike_step_df.loc[
            strike_step_df["base_symbol"] == base_symbol, "strike_step_size"
        ].values[0]
        return strike_step

    def calculate_current_atm_strike_prc(
        self,
        base_symbol,
        token=None,
        prediction=None,
        strike_prc_multiplier=None,
        strategy_type=None,
    ):
        """
        The `calculate_current_atm_strike_prc` function calculates the current at-the-money (ATM) strike price based on the given parameters.

        :param base_symbol: The base symbol
        :type base_symbol: str
        :param token: The token associated with the base symbol (optional)
        :type token: int
        :param prediction: The market prediction, either "Bullish" or "Bearish" (optional)
        :type prediction: str
        :param strike_prc_multiplier: The strike price multiplier (optional)
        :type strike_prc_multiplier: float
        :param strategy_type: The strategy type, either "OB" or "OS" (optional)
        :type strategy_type: str
        :return: The calculated ATM strike price
        """
        from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import (
            get_single_ltp,
        )

        if token is None:
            token = int(self.get_token_from_info(base_symbol))
        ltp = get_single_ltp(token)
        base_strike = self.round_strike_prc(ltp, base_symbol)
        multiplier = self.get_strike_step(base_symbol)
        if strike_prc_multiplier:
            if prediction == "Bearish" and strategy_type == "OB":
                adjusted_multiplier = multiplier * (-strike_prc_multiplier)
            elif prediction == "Bullish" and strategy_type == "OB":
                adjusted_multiplier = multiplier * strike_prc_multiplier
            elif prediction == "Bearish" and strategy_type == "OS":
                adjusted_multiplier = multiplier * strike_prc_multiplier
            elif prediction == "Bullish" and strategy_type == "OS":
                adjusted_multiplier = multiplier * (-strike_prc_multiplier)
            else:
                logger.error("Invalid prediction")
            return base_strike + adjusted_multiplier
        else:
            return base_strike

    def get_hedge_strikeprc(self, base_symbol, token, prediction, hedge_multiplier):
        """
        The `get_hedge_strikeprc` function calculates the hedge strike price based on the given parameters.

        :param base_symbol: The base symbol
        :type base_symbol: str
        :param token: The token associated with the base symbol
        :type token: int
        :param prediction: The market prediction, either "Bullish" or "Bearish"
        :type prediction: str
        :param hedge_multiplier: The hedge multiplier
        :type hedge_multiplier: int
        :return: The calculated hedge strike price
        """
        from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import (
            get_single_ltp,
        )

        ltp = get_single_ltp(token)
        strike_prc = self.round_strike_prc(ltp, base_symbol)
        strike_prc_multiplier = self.get_strike_step(base_symbol)
        bear_strikeprc = strike_prc + (hedge_multiplier * strike_prc_multiplier)
        bull_strikeprc = strike_prc - (hedge_multiplier * strike_prc_multiplier)
        hedge_strikeprc = bear_strikeprc if prediction == "Bearish" else bull_strikeprc
        return hedge_strikeprc

    def get_square_off_transaction(self, prediction):
        """
        The `get_square_off_transaction` function determines the square-off transaction type (BUY or SELL) based on the given prediction.

        :param prediction: The market prediction, either "Bullish" or "Bearish"
        :type prediction: str
        :return: The square-off transaction type (BUY or SELL)
        """
        if prediction == "Bearish":
            return "BUY"
        elif prediction == "Bullish":
            return "SELL"
        else:
            logger.error("Invalid prediction")

    def get_strike_multiplier(self, base_symbol):
        """
        The `get_strike_multiplier` function retrieves the strike multiplier for a given base symbol from the fno_info CSV file.

        :param base_symbol: The base symbol for which to retrieve the strike multiplier
        :type base_symbol: str
        :return: The strike multiplier
        """
        fno_info_df = pd.read_csv(fno_info_path)
        strike_multiplier = fno_info_df.loc[
            fno_info_df["base_symbol"] == base_symbol, "strike_multiplier"
        ].values
        if len(strike_multiplier) == 0:
            return f"{base_symbol} not found"
        return strike_multiplier[0]

    def get_hedge_multiplier(self, base_symbol):
        """
        The `get_hedge_multiplier` function retrieves the hedge multiplier for a given base symbol from the fno_info CSV file.

        :param base_symbol: The base symbol for which to retrieve the hedge multiplier
        :type base_symbol: str
        :return: The hedge multiplier
        """
        fno_info_df = pd.read_csv(fno_info_path)
        hedge_multiplier = fno_info_df.loc[
            fno_info_df["base_symbol"] == base_symbol, "hedge_multiplier"
        ].values
        if len(hedge_multiplier) == 0:
            return f"{base_symbol} not found"
        return hedge_multiplier[0]

    def get_stoploss_multiplier(self, base_symbol):
        """
        The `get_stoploss_multiplier` function retrieves the stoploss multiplier for a given base symbol from the fno_info CSV file.

        :param base_symbol: The base symbol for which to retrieve the stoploss multiplier
        :type base_symbol: str
        :return: The stoploss multiplier
        """
        fno_info_df = pd.read_csv(fno_info_path)
        stoploss_multiplier = fno_info_df.loc[
            fno_info_df["base_symbol"] == base_symbol, "stoploss_multiplier"
        ].values
        if len(stoploss_multiplier) == 0:
            return f"{base_symbol} not found"
        return stoploss_multiplier[0]

    def update_strategy_info(self, strategy_name):
        """
        The `update_strategy_info` function updates the strategy information with the current instruments and strategy name.

        :param strategy_name: The name of the strategy
        :type strategy_name: str
        :return: The updated strategy information
        """
        strategy_info = {}
        strategy_info["Instruments"] = self.Instruments
        strategy_info["StrategyName"] = strategy_name
        return strategy_info


def get_previous_dates(num_dates):
    """
    The `get_previous_dates` function retrieves the previous `num_dates` business dates, excluding weekends and holidays.

    :param num_dates: The number of previous business dates to retrieve
    :type num_dates: int
    :return: A list of previous business dates as strings
    """
    dates = []
    current_date = dt.date.today()

    while len(dates) < num_dates:
        current_date -= dt.timedelta(days=1)

        if current_date.weekday() >= 5 or current_date in holidays:
            continue

        dates.append(current_date.strftime("%Y-%m-%d"))

    return dates


def fetch_strategy_users(strategy_name):
    """
    The `fetch_strategy_users` function retrieves the list of users associated with the given strategy from Firebase.

    :param strategy_name: The name of the strategy
    :type strategy_name: str
    :return: A list of users associated with the strategy
    """
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
        fetch_active_users_from_firebase,
    )

    try:
        active_users = fetch_active_users_from_firebase()
        strategy_users = []
        for user in active_users:
            if strategy_name in user["Strategies"]:
                strategy_users.append(user)
        return strategy_users
    except Exception as e:
        logger.error(f"Error fetching strategy users: {e}")
        return None


def fetch_freecash_firebase(strategy_name):
    """
    The `fetch_freecash_firebase` function retrieves the free cash available for each user associated with the given strategy from Firebase.

    :param strategy_name: The name of the strategy
    :type strategy_name: str
    :return: A dictionary with user transaction numbers as keys and free cash values as values
    """
    try:
        accounts = fetch_strategy_users(
            strategy_name
        )  # Assuming there is a function to fetch accounts from Firebase
        freecash_dict = {}
        freecash_key = dt.datetime.now().strftime("%d%b%y") + "_FreeCash"
        for account in accounts:
            freecash_dict[account["Tr_No"]] = account["Accounts"][freecash_key]
        return freecash_dict
    except Exception as e:
        logger.error(f"Error fetching free cash: {e}")
        return None


def fetch_risk_per_trade_firebase(strategy_name):
    """
    The `fetch_risk_per_trade_firebase` function retrieves the risk per trade value for each user associated with the given strategy from Firebase.

    :param strategy_name: The name of the strategy
    :type strategy_name: str
    :return: A dictionary with user transaction numbers as keys and risk per trade values as values
    """
    try:
        users = fetch_strategy_users(strategy_name)
        risk_per_trade = {}
        for user in users:
            risk_per_trade[user["Tr_No"]] = user["Strategies"][strategy_name][
                "RiskPerTrade"
            ]
        return risk_per_trade
    except Exception as e:
        logger.error(f"Error fetching risk per trade: {e}")
        return None


def update_qty_user_firebase(
    strategy_name, avg_sl_points, lot_size, qty_amplifier=None, strategy_amplifier=None
):
    """
    The `update_qty_user_firebase` function updates the quantity for each user associated with the given strategy based on their free cash and risk per trade.

    :param strategy_name: The name of the strategy
    :type strategy_name: str
    :param avg_sl_points: The average stop loss points
    :type avg_sl_points: float
    :param lot_size: The lot size
    :type lot_size: int
    :param qty_amplifier: The quantity amplifier (optional)
    :type qty_amplifier: float
    :param strategy_amplifier: The strategy amplifier (optional)
    :type strategy_amplifier: float
    """
    from Executor.ExecutorUtils.OrderCenter.OrderCenterUtils import (
        calculate_qty_for_strategies,
    )

    strategy_users = fetch_strategy_users(strategy_name)
    free_cash_dict = fetch_freecash_firebase(strategy_name)
    risk_per_trade = fetch_risk_per_trade_firebase(strategy_name)
    try:
        for user in strategy_users:
            if user["Tr_No"] in risk_per_trade:
                risk = risk_per_trade[user["Tr_No"]]
            if user["Tr_No"] in free_cash_dict:
                capital = free_cash_dict[user["Tr_No"]]
            qty = calculate_qty_for_strategies(
                capital,
                risk,
                avg_sl_points,
                lot_size,
                qty_amplifier,
                strategy_amplifier,
            )
            user["Strategies"][strategy_name]["Qty"] = qty

            update_fields_firebase(
                user_db_collection,
                user["Tr_No"],
                {"Qty": qty},
                f"Strategies/{strategy_name}",
            )
    except Exception as e:
        logger.error(f"Error updating qty for user: {e}")


def assign_trade_id(orders_to_place):
    """
    The `assign_trade_id` function assigns trade IDs to the orders to be placed based on the order mode and signal.

    :param orders_to_place: A list of orders to place
    :type orders_to_place: list
    :return: The list of orders with updated trade IDs
    """
    for order in orders_to_place:
        # Determine the last part of the trade_id based on order_mode
        if order["order_mode"] in ["Main", "HedgeEntry", "MainEntry"]:
            trade_id_suffix = "EN"
        elif order["order_mode"] in ["SL", "Trailing", "HedgeExit", "MainExit"]:
            trade_id_suffix = "EX"
        else:
            trade_id_suffix = "unknown"

        if order["order_mode"] == "HedgeEntry" or order["order_mode"] == "HedgeExit":
            order["order_mode"] = "HO"
        if (
            order["order_mode"] == "Main"
            or order["order_mode"] == "MainEntry"
            or order["order_mode"] == "MainExit"
        ):
            order["order_mode"] = "MO"
        if order["order_mode"] == "SL" or order["order_mode"] == "Trailing":
            order["order_mode"] = "SL"

        if order["signal"] == "Long":
            order["signal"] = "LG"
        if order["signal"] == "Short":
            order["signal"] = "SH"

        # Reconstruct the trade_id
        trade_id = f"{order['trade_id']}_{order['signal']}_{order['order_mode']}_{trade_id_suffix}"

        # Update the trade_id in the order
        order["trade_id"] = trade_id

    return orders_to_place


def fetch_previous_trade_id(trade_id):
    """
    The `fetch_previous_trade_id` function retrieves the previous trade ID by decrementing the numeric part of the given trade ID.

    :param trade_id: The current trade ID
    :type trade_id: str
    :return: The previous trade ID
    """
    # trade_id = MP123
    numeric_digits = re.findall(r"\d+", trade_id)
    if numeric_digits:
        # Decrement the numeric digits by 1
        previous_trade_id = str(int(numeric_digits[0]) - 1)
        # Replace the numeric digits in trade_id with the decremented value
        trade_id = trade_id.replace(numeric_digits[0], previous_trade_id)

    return trade_id


def update_signal_firebase(strategy_name, signal, trade_id=None):
    """
    The `update_signal_firebase` function updates the signal for a given strategy in Firebase.

    :param strategy_name: The name of the strategy
    :type strategy_name: str
    :param signal: The signal to update
    :type signal: dict
    :param trade_id: The trade ID (optional)
    :type trade_id: str
    """
    trade = signal["TradeId"].split("_")[3]
    trade_no = signal["TradeId"].split("_")[0]
    if trade == "EN":
        trade_prefix = "entry"
    elif trade == "EX":
        trade_prefix = "exit"
    else:
        logger.error("Invalid trade")

    trade = trade_no + "_" + trade_prefix

    update_fields_firebase(STRATEGIES_DB, strategy_name, {trade: signal}, "TodayOrders")

    if trade_id:
        update_next_trade_id_firebase(strategy_name, trade_id)
    else:
        update_next_trade_id_firebase(strategy_name, signal["TradeId"])


def update_next_trade_id_firebase(strategy_name, trade_id):
    """
    The `update_next_trade_id_firebase` function updates the next trade ID for a given strategy in Firebase.

    :param strategy_name: The name of the strategy
    :type strategy_name: str
    :param trade_id: The current trade ID
    :type trade_id: str
    """
    # trade_id = MP123
    numeric_digits = re.findall(r"\d+", trade_id)
    if numeric_digits:
        # Increment the numeric digits by 1
        next_trade_id = str(int(numeric_digits[0]) + 1)
        # Replace the numeric digits in trade_id with the incremented value
        trade_id = trade_id.replace(numeric_digits[0], next_trade_id)

    update_fields_firebase(STRATEGIES_DB, strategy_name, {"NextTradeId": trade_id})


def place_order_strategy_users(strategy_name, orders_to_place, order_qty_mode=None):
    """
    The `place_order_strategy_users` function places orders for all users associated with the given strategy.

    :param strategy_name: The name of the strategy
    :type strategy_name: str
    :param orders_to_place: The orders to place
    :type orders_to_place: list
    :param order_qty_mode: The order quantity mode (optional)
    :type order_qty_mode: str
    """
    from Executor.ExecutorUtils.OrderCenter.OrderCenterUtils import (
        place_order_for_strategy,
    )

    strategy_users = fetch_strategy_users(strategy_name)
    asyncio.run(
        place_order_for_strategy(strategy_users, orders_to_place, order_qty_mode)
    )
    pass


def place_order_single_user(user_details, orders_to_place, order_qty_mode=None):
    """
    The `place_order_single_user` function places orders for a single user.

    :param user_details: The details of the user
    :type user_details: dict
    :param orders_to_place: The orders to place
    :type orders_to_place: list
    :param order_qty_mode: The order quantity mode (optional)
    :type order_qty_mode: str
    :return: The result of placing the order
    """
    from Executor.ExecutorUtils.OrderCenter.OrderCenterUtils import (
        place_order_for_strategy,
    )

    return place_order_for_strategy(user_details, orders_to_place, order_qty_mode)


def update_stoploss_orders(strategy_name, orders_to_modify):
    """
    The `update_stoploss_orders` function updates the stop loss orders for all users associated with the given strategy.

    :param strategy_name: The name of the strategy
    :type strategy_name: str
    :param orders_to_modify: The orders to modify
    :type orders_to_modify: list
    """
    # I fetch the users for the strategy and then pass the users and orders to modify to the modify_orders_for_strategy function
    from Executor.ExecutorUtils.OrderCenter.OrderCenterUtils import (
        modify_orders_for_strategy,
    )

    strategy_users = fetch_strategy_users(strategy_name)
    modify_orders_for_strategy(strategy_users, orders_to_modify)
    pass


def calculate_stoploss(
    ltp, main_transaction_type, stoploss_multiplier=None, price_ref=None
):
    """
    The `calculate_stoploss` function calculates the stop loss based on the given parameters.

    :param ltp: The last traded price
    :type ltp: float
    :param main_transaction_type: The main transaction type (BUY or SELL)
    :type main_transaction_type: str
    :param stoploss_multiplier: The stop loss multiplier (optional)
    :type stoploss_multiplier: float
    :param price_ref: The price reference (optional)
    :type price_ref: float
    :return: The calculated stop loss
    """
    if stoploss_multiplier:
        stoploss = calculate_multipler_stoploss(
            main_transaction_type, ltp, stoploss_multiplier
        )
    elif price_ref:
        stoploss = calculate_priceref_stoploss(main_transaction_type, ltp, price_ref)
    else:
        raise ValueError("Invalid stoploss calculation in order_details")
    return stoploss


def calculate_multipler_stoploss(main_transaction_type, ltp, stoploss_multiplier):
    """
    The `calculate_multipler_stoploss` function calculates the stop loss based on the stop loss multiplier.

    :param main_transaction_type: The main transaction type (BUY or SELL)
    :type main_transaction_type: str
    :param ltp: The last traded price
    :type ltp: float
    :param stoploss_multiplier: The stop loss multiplier
    :type stoploss_multiplier: float
    :return: The calculated stop loss
    """
    if main_transaction_type == "BUY":
        stoploss = round(float(ltp - (ltp * stoploss_multiplier)), 1)
    elif main_transaction_type == "SELL":
        stoploss = round(float(ltp + (ltp * stoploss_multiplier)), 1)
    logger.debug(
        f"stoploss: {stoploss}, ltp: {ltp}, stoploss_multiplier: {stoploss_multiplier}"
    )
    if stoploss < 0:
        return 1

    return stoploss


def calculate_priceref_stoploss(main_transaction_type, ltp, price_ref):
    """
    The `calculate_priceref_stoploss` function calculates the stop loss based on the price reference.

    :param main_transaction_type: The main transaction type (BUY or SELL)
    :type main_transaction_type: str
    :param ltp: The last traded price
    :type ltp: float
    :param price_ref: The price reference
    :type price_ref: float
    :return: The calculated stop loss
    """
    if main_transaction_type == "BUY":
        stoploss = round(float(ltp - price_ref), 1)
    elif main_transaction_type == "SELL":
        stoploss = round(float(ltp + price_ref), 1)

    if stoploss < 0:
        return 1

    return stoploss


def calculate_trigger_price(sl_transaction_type, stoploss):
    """
    The `calculate_trigger_price` function calculates the trigger price based on the stop loss and stop loss transaction type.

    :param sl_transaction_type: The stop loss transaction type (BUY or SELL)
    :type sl_transaction_type: str
    :param stoploss: The stop loss
    :type stoploss: float
    :return: The calculated trigger price
    """
    if sl_transaction_type == "BUY":
        trigger_price = round(float(stoploss - 1), 1)
    elif sl_transaction_type == "SELL":
        trigger_price = round(float(stoploss + 1), 1)
    return trigger_price


def calculate_transaction_type_sl(transaction_type):
    """
    The `calculate_transaction_type_sl` function calculates the stop loss transaction type based on the main transaction type.

    :param transaction_type: The main transaction type (BUY or SELL)
    :type transaction_type: str
    :return: The stop loss transaction type (BUY or SELL)
    """
    if transaction_type == "BUY" or transaction_type == "B":
        transaction_type_sl = "SELL"
    elif transaction_type == "SELL" or transaction_type == "S":
        transaction_type_sl = "BUY"
    return transaction_type_sl


def calculate_target(option_ltp, price_ref):
    """
    The `calculate_target` function calculates the target price based on the option last traded price and the price reference.

    :param option_ltp: The option last traded price
    :type option_ltp: float
    :param price_ref: The price reference
    :type price_ref: float
    :return: The calculated target price
    """
    return option_ltp + (price_ref / 2)


def base_symbol_token(base_symbol):
    """
    The `base_symbol_token` function retrieves the token for a given base symbol from the fno_info CSV file.

    :param base_symbol: The base symbol for which to retrieve the token
    :type base_symbol: str
    :return: The token associated with the base symbol
    """
    fno_info_df = pd.read_csv(fno_info_path)
    token = fno_info_df.loc[fno_info_df["base_symbol"] == base_symbol, "token"].values
    if len(token) == 0:
        return f"{base_symbol} not found"
    return token[0]


def get_strategy_name_from_trade_id(trade_id):
    """
    The `get_strategy_name_from_trade_id` function retrieves the strategy name based on the given trade ID.

    :param trade_id: The trade ID
    :type trade_id: str
    :return: The strategy name
    """
    # trade_id = MP123
    strategy_prefix = trade_id[:2]
    strategies = fetch_collection_data_firebase(STRATEGIES_DB)
    # iterate over the strategies dict and find the strategy name for the strategy prefix
    for strategy, strategy_details in strategies.items():
        if strategy_details["StrategyPrefix"] == strategy_prefix:
            return strategy
    return None


def get_signal_from_trade_id(trade_id):
    """
    The `get_signal_from_trade_id` function retrieves the signal (Long or Short) based on the given trade ID.

    :param trade_id: The trade ID
    :type trade_id: str
    :return: The signal (Long or Short)
    """
    # trade_id = ET12_SH_MO_EX if SH its short and if LG its long after the first _
    signal = trade_id.split("_")[1]
    if signal == "SH":
        return "Short"
    elif signal == "LG":
        return "Long"
    else:
        return None


def fetch_qty_amplifier(strategy_name, strategy_type):
    """
    The `fetch_qty_amplifier` function retrieves the quantity amplifier for a given strategy and strategy type from Firebase.

    :param strategy_name: The name of the strategy
    :type strategy_name: str
    :param strategy_type: The strategy type, either "OS", "OB", or "Equity"
    :type strategy_type: str
    :return: The quantity amplifier
    """
    try:
        strategy_data = fetch_collection_data_firebase(STRATEGIES_DB, strategy_name)
        if strategy_type == "OS":
            qty_amplifier = strategy_data.get("MarketInfoParams", {}).get(
                "OSQtyAmplifier", 1
            )
        elif strategy_type == "OB":
            qty_amplifier = strategy_data.get("MarketInfoParams", {}).get(
                "OBQtyAmplifier", 1
            )
        elif strategy_type == "Equity":
            qty_amplifier = strategy_data.get("MarketInfoParams", {}).get(
                "EquityQtyAmplifier", 1
            )
        return qty_amplifier
    except Exception as e:
        logger.error(f"Error fetching qty amplifier for strategy {strategy_name}: {e}")
        return 1


def fetch_strategy_amplifier(strategy_name):
    """
    The `fetch_strategy_amplifier` function retrieves the strategy amplifier for a given strategy from Firebase.

    :param strategy_name: The name of the strategy
    :type strategy_name: str
    :return: The strategy amplifier
    """
    try:
        strategy_data = fetch_collection_data_firebase(STRATEGIES_DB, strategy_name)
        amplifier = strategy_data.get("MarketInfoParams", {}).get(
            "StrategyQtyAmplifier", 1
        )
        return amplifier
    except Exception as e:
        logger.error(
            f"Error fetching strategy amplifier for strategy {strategy_name}: {e}"
        )
        return 1
