import datetime as dt
import os
import re
import sys
from datetime import time
from typing import Dict, List, Optional, Union

import pandas as pd
from dotenv import load_dotenv
from pydantic import BaseModel, Field, validator

DIR = os.getcwd()
sys.path.append(DIR)
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)
fno_info_path = os.getenv("FNO_INFO_PATH")

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


from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import (
    fetch_collection_data_firebase,
    push_orders_firebase,
    update_fields_firebase,
)
from Executor.ExecutorUtils.ExeUtils import holidays


# Sub-models for various parameter types
class EntryParams(BaseModel):
    EntryTime: str
    HedgeMultiplier: Optional[int] = None
    InstrumentToday: Optional[Union[str, dict]] = None
    SLMultipler: Optional[int] = None
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
    StrategyInfo: Optional[Dict[str, str]] = None
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
        super().__init__(**data)
        self._raw_data = data

    def get_raw_field(self, field_name: str):
        return self._raw_data.get(field_name, None)

    @classmethod
    def load_from_db(cls, strategy_name: str):
        # TODO: Add synthetic data for testing
        data = fetch_collection_data_firebase("strategies", document=strategy_name)
        if data is None:
            raise ValueError(f"No data found for strategy {strategy_name}")
        return cls.parse_obj(data)

    ###########################################################################
    def get_option_type(self, prediction, strategy_option_mode):
        if strategy_option_mode == "OS":
            return "CE" if prediction == "Bearish" else "PE"
        elif strategy_option_mode == "OB":
            return "CE" if prediction == "Bullish" else "PE"
        else:
            logger.error("Invalid option mode")

    def get_hedge_option_type(self, prediction):
        if prediction == "Bearish":
            return "CE"
        elif prediction == "Bullish":
            return "PE"
        else:
            logger.error("Invalid option mode")

    def get_transaction_type(self, prediction):
        if prediction == "Bearish":
            return "SELL"
        elif prediction == "Bullish":
            return "BUY"
        else:
            logger.error("Invalid option mode")

    def get_token_from_info(self, base_symbol):
        fno_info_df = pd.read_csv(fno_info_path)
        token = fno_info_df.loc[
            fno_info_df["base_symbol"] == base_symbol, "token"
        ].values
        if len(token) == 0:
            return f"{base_symbol} not found"
        return token[0]

    def determine_expiry_index(self):
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

    def round_strike_prc(
        self, ltp, base_symbol
    ):  # TODO: Add support for other base symbols using a csv list
        strike_step = self.get_strike_step(base_symbol)
        return round(ltp / strike_step) * strike_step

    def get_strike_step(self, base_symbol):
        strike_step_df = pd.read_csv(fno_info_path)
        strike_step = strike_step_df.loc[
            strike_step_df["base_symbol"] == base_symbol, "strike_step_size"
        ].values[0]
        return strike_step

    def calculate_current_atm_strike_prc(
        self, base_symbol, token=None, prediction=None, strike_prc_multiplier=None
    ):
        from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import (
            get_single_ltp,
        )

        if token is None:
            token = int(self.get_token_from_info(base_symbol))
        ltp = get_single_ltp(token)
        base_strike = self.round_strike_prc(ltp, base_symbol)
        multiplier = self.get_strike_step(base_symbol)
        # TODO: Check this logic
        if strike_prc_multiplier:
            adjustment = multiplier * (
                -strike_prc_multiplier
                if prediction == "Bearish"
                else strike_prc_multiplier
            )
            return base_strike + adjustment
        else:
            return base_strike

    def get_hedge_strikeprc(self, base_symbol, token, prediction, hedge_multiplier):
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
        if prediction == "Bearish":
            return "BUY"
        elif prediction == "Bullish":
            return "SELL"
        else:
            logger.error("Invalid prediction")

    def get_strike_multiplier(self, base_symbol):
        fno_info_df = pd.read_csv(fno_info_path)
        strike_multiplier = fno_info_df.loc[
            fno_info_df["base_symbol"] == base_symbol, "strike_multiplier"
        ].values
        if len(strike_multiplier) == 0:
            return f"{base_symbol} not found"
        return strike_multiplier[0]

    def get_hedge_multiplier(self, base_symbol):
        fno_info_df = pd.read_csv(fno_info_path)
        hedge_multiplier = fno_info_df.loc[
            fno_info_df["base_symbol"] == base_symbol, "hedge_multiplier"
        ].values
        if len(hedge_multiplier) == 0:
            return f"{base_symbol} not found"
        return hedge_multiplier[0]

    def get_stoploss_multiplier(self, base_symbol):
        fno_info_df = pd.read_csv(fno_info_path)
        stoploss_multiplier = fno_info_df.loc[
            fno_info_df["base_symbol"] == base_symbol, "stoploss_multiplier"
        ].values
        if len(stoploss_multiplier) == 0:
            return f"{base_symbol} not found"
        return stoploss_multiplier[0]

    def update_strategy_info(self, strategy_name):
        strategy_info = {}
        strategy_info["Instruments"] = self.Instruments
        strategy_info["StrategyName"] = strategy_name
        return strategy_info


def get_previous_dates(num_dates):
    dates = []
    current_date = dt.date.today()

    while len(dates) < num_dates:
        current_date -= dt.timedelta(days=1)

        if current_date.weekday() >= 5 or current_date in holidays:
            continue

        dates.append(current_date.strftime("%Y-%m-%d"))

    return dates


def fetch_strategy_users(strategy_name):
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
        fetch_active_users_from_firebase,
    )

    active_users = fetch_active_users_from_firebase()
    strategy_users = []
    for user in active_users:
        if strategy_name in user["Strategies"]:
            strategy_users.append(user)
    return strategy_users


def fetch_freecash_firebase(strategy_name):
    accounts = fetch_strategy_users(
        strategy_name
    )  # Assuming there is a function to fetch accounts from Firebase
    freecash_dict = {}
    freecash_key = dt.datetime.now().strftime("%d%b%y") + "_FreeCash"
    for account in accounts:
        freecash_dict[account["Tr_No"]] = account["Accounts"][freecash_key]
    return freecash_dict


def fetch_risk_per_trade_firebase(strategy_name):
    users = fetch_strategy_users(strategy_name)
    risk_per_trade = {}
    for user in users:
        risk_per_trade[user["Tr_No"]] = user["Strategies"][strategy_name][
            "RiskPerTrade"
        ]
    return risk_per_trade


def update_qty_user_firebase(strategy_name, avg_sl_points, lot_size):
    from Executor.ExecutorUtils.OrderCenter.OrderCenterUtils import (
        calculate_qty_for_strategies,
    )

    strategy_users = fetch_strategy_users(strategy_name)
    free_cash_dict = fetch_freecash_firebase(strategy_name)
    risk_per_trade = fetch_risk_per_trade_firebase(strategy_name)
    for user in strategy_users:
        if user["Tr_No"] in risk_per_trade:
            risk = risk_per_trade[user["Tr_No"]]
        if user["Tr_No"] in free_cash_dict:
            capital = free_cash_dict[user["Tr_No"]]
        qty = calculate_qty_for_strategies(capital, risk, avg_sl_points, lot_size)
        user["Strategies"][strategy_name]["Qty"] = qty

        update_fields_firebase(
            "new_clients", user["Tr_No"], {"Qty": qty}, f"Strategies/{strategy_name}"
        )


# TODO: shorten the trade_ids
def assign_trade_id(orders_to_place):
    for order in orders_to_place:
        # Determine the last part of the trade_id based on order_mode
        if order["order_mode"] in ["Main", "HedgeEntry"]:
            trade_id_suffix = "EN"
        elif order["order_mode"] in ["SL", "Trailling", "HedgeExit"]:
            trade_id_suffix = "EX"
        else:
            trade_id_suffix = "unknown"

        if order["order_mode"] == "HedgeEntry" or order["order_mode"] == "HedgeExit":
            order["order_mode"] = "HO"
        if order["order_mode"] == "Main":
            order["order_mode"] = "MO"
        if order["order_mode"] == "SL" or order["order_mode"] == "Trailling":
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
    # trade_id = MP123
    numeric_digits = re.findall(r"\d+", trade_id)
    if numeric_digits:
        # Decrement the numeric digits by 1
        previous_trade_id = str(int(numeric_digits[0]) - 1)
        # Replace the numeric digits in trade_id with the decremented value
        trade_id = trade_id.replace(numeric_digits[0], previous_trade_id)

    return trade_id


def update_signal_firebase(strategy_name, signal, trade_id=None):

    trade = signal["TradeId"].split("_")[3]
    trade_no = signal["TradeId"].split("_")[0]
    if trade == "EN":
        trade_prefix = "entry"
    elif trade == "EX":
        trade_prefix = "exit"
    else:
        logger.error("Invalid trade")

    trade = trade_no + "_" + trade_prefix

    update_fields_firebase("strategies", strategy_name, {trade: signal}, "TodayOrders")

    if trade_id:
        update_next_trade_id_firebase(strategy_name, trade_id)
    else:
        update_next_trade_id_firebase(strategy_name, signal["TradeId"])


def update_next_trade_id_firebase(strategy_name, trade_id):
    # trade_id = MP123
    numeric_digits = re.findall(r"\d+", trade_id)
    if numeric_digits:
        # Increment the numeric digits by 1
        next_trade_id = str(int(numeric_digits[0]) + 1)
        # Replace the numeric digits in trade_id with the incremented value
        trade_id = trade_id.replace(numeric_digits[0], next_trade_id)

    update_fields_firebase("strategies", strategy_name, {"NextTradeId": trade_id})


def place_order_strategy_users(strategy_name, orders_to_place):
    from Executor.ExecutorUtils.OrderCenter.OrderCenterUtils import (
        place_order_for_strategy,
    )

    strategy_users = fetch_strategy_users(strategy_name)
    place_order_for_strategy(strategy_users, orders_to_place)
    pass


def update_stoploss_orders(strategy_name, orders_to_modify):
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
    if main_transaction_type == "BUY":
        stoploss = round(float(ltp - (ltp * stoploss_multiplier)), 1)
    elif main_transaction_type == "SELL":
        stoploss = round(float(ltp + (ltp * stoploss_multiplier)), 1)

    if stoploss < 0:
        return 1

    return stoploss


def calculate_priceref_stoploss(main_transaction_type, ltp, price_ref):
    if main_transaction_type == "BUY":
        stoploss = round(float(ltp - price_ref), 1)
    elif main_transaction_type == "SELL":
        stoploss = round(float(ltp + price_ref), 1)

    if stoploss < 0:
        return 1

    return stoploss


def calculate_trigger_price(sl_transaction_type, stoploss):
    if sl_transaction_type == "BUY":
        trigger_price = round(float(stoploss - 1), 1)
    elif sl_transaction_type == "SELL":
        trigger_price = round(float(stoploss + 1), 1)
    return trigger_price


def calculate_transaction_type_sl(transaction_type):
    if transaction_type == "BUY" or transaction_type == "B":
        transaction_type_sl = "SELL"
    elif transaction_type == "SELL" or transaction_type == "S":
        transaction_type_sl = "BUY"
    return transaction_type_sl


def calculate_target(option_ltp, price_ref):
    return option_ltp + (price_ref / 2)


def base_symbol_token(base_symbol):
    fno_info_df = pd.read_csv(fno_info_path)
    token = fno_info_df.loc[fno_info_df["base_symbol"] == base_symbol, "token"].values
    if len(token) == 0:
        return f"{base_symbol} not found"
    return token[0]


def get_strategy_name_from_trade_id(trade_id):
    # trade_id = MP123
    strategy_prefix = trade_id[:2]
    strategies = fetch_collection_data_firebase("strategies")
    # iterate over the strategies dict and find the strategy name for the strategy prefix
    for strategy, strategy_details in strategies.items():
        if strategy_details["StrategyPrefix"] == strategy_prefix:
            return strategy
    return None


def get_signal_from_trade_id(trade_id):
    # trade_id = ET12_SH_MO_EX if SH its short and if LG its long after the first _
    signal = trade_id.split("_")[1]
    if signal == "SH":
        return "Short"
    elif signal == "LG":
        return "Long"
    else:
        return None
