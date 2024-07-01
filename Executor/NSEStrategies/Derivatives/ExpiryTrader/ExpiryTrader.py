import os
import sys
import datetime as dt
from time import sleep
from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

TRADE_MODE = os.getenv("TRADE_MODE")

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()

from Executor.NSEStrategies.NSEStrategiesUtil import StrategyBase
from Executor.NSEStrategies.NSEStrategiesUtil import (
    update_qty_user_firebase,
    assign_trade_id,
    update_signal_firebase,
    place_order_strategy_users,
    calculate_stoploss,
    calculate_transaction_type_sl,
    calculate_trigger_price,
    fetch_qty_amplifier,
    fetch_strategy_amplifier,
)

import Executor.ExecutorUtils.ExeUtils as ExeUtils
import Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils as InstrumentCenterUtils
from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import (
    discord_bot,
)


class ExpiryTrader(StrategyBase):
    def get_general_params(self):
        return self.GeneralParams

    def get_entry_params(self):
        return self.EntryParams

    def get_exit_params(self):
        return self.ExitParams

    def get_raw_field(self, field_name: str):
        return super().get_raw_field(field_name)


expiry_trader_obj = ExpiryTrader.load_from_db("ExpiryTrader")
instrument_obj = InstrumentCenterUtils.Instrument()


def message_for_orders(trade_type, prediction, main_trade_symbol, hedge_trade_symbol):
    """
    Sends a message containing the details of the orders placed for the strategy.

    :param trade_type: Type of trade (e.g., Live).
    :param prediction: Direction of the trade (e.g., Short).
    :param main_trade_symbol: Symbol of the main trade.
    :param hedge_trade_symbol: Symbol of the hedge trade.
    """
    message = (
        f"{trade_type} Trade for {strategy_name}\n"
        f"Direction : {prediction}\n"
        f"Main Trade : {main_trade_symbol}\n"
        f"Hedge Trade {hedge_trade_symbol} \n"
    )
    logger.info(message)
    discord_bot(message, strategy_name)


hedge_transaction_type = expiry_trader_obj.get_general_params().HedgeTransactionType
main_transaction_type = expiry_trader_obj.get_general_params().MainTransactionType

# Extract strategy parameters
base_symbol, today_expiry_token = expiry_trader_obj.determine_expiry_index()
strategy_name = expiry_trader_obj.StrategyName
next_trade_prefix = expiry_trader_obj.NextTradeId
prediction = expiry_trader_obj.MarketInfoParams.TradeView
order_type = expiry_trader_obj.get_general_params().OrderType
product_type = expiry_trader_obj.get_general_params().ProductType

strike_prc_multiplier = expiry_trader_obj.EntryParams.StrikeMultiplier
hedge_multiplier = expiry_trader_obj.EntryParams.HedgeMultiplier
stoploss_multiplier = expiry_trader_obj.EntryParams.SLMultiplier
desired_start_time_str = expiry_trader_obj.get_entry_params().EntryTime
strategy_type = expiry_trader_obj.GeneralParams.StrategyType

logger.debug(
    f"Values from Firebase for {strategy_name}: {base_symbol}, {today_expiry_token}, {prediction}, {order_type}, {product_type}, {strike_prc_multiplier}, {hedge_multiplier}, {stoploss_multiplier}, {desired_start_time_str}, {strategy_type}"
)

start_hour, start_minute, start_second = map(int, desired_start_time_str.split(":"))

main_strikeprc = expiry_trader_obj.calculate_current_atm_strike_prc(
    base_symbol, today_expiry_token, prediction, strike_prc_multiplier, strategy_type
)
hedge_strikeprc = expiry_trader_obj.get_hedge_strikeprc(
    base_symbol, today_expiry_token, prediction, hedge_multiplier
)
main_option_type = expiry_trader_obj.get_option_type(prediction, "OS")
hedge_option_type = expiry_trader_obj.get_hedge_option_type(prediction)

today_expiry = instrument_obj.get_expiry_by_criteria(
    base_symbol, main_strikeprc, main_option_type, "current_week"
)
hedge_exchange_token = instrument_obj.get_exchange_token_by_criteria(
    base_symbol, hedge_strikeprc, hedge_option_type, today_expiry
)
main_exchange_token = instrument_obj.get_exchange_token_by_criteria(
    base_symbol, main_strikeprc, main_option_type, today_expiry
)

ltp = InstrumentCenterUtils.get_single_ltp(exchange_token=main_exchange_token)
lot_size = instrument_obj.get_lot_size_by_exchange_token(main_exchange_token)

qty_amplifier = fetch_qty_amplifier(strategy_name, strategy_type)
strategy_amplifier = fetch_strategy_amplifier(strategy_name)
update_qty_user_firebase(
    strategy_name, ltp, lot_size, qty_amplifier, strategy_amplifier
)

main_trade_symbol = instrument_obj.get_trading_symbol_by_exchange_token(
    main_exchange_token
)
hedge_trade_symbol = instrument_obj.get_trading_symbol_by_exchange_token(
    hedge_exchange_token
)

stoploss_transaction_type = calculate_transaction_type_sl(main_transaction_type)
limit_prc = calculate_stoploss(
    ltp, main_transaction_type, stoploss_multiplier=stoploss_multiplier
)
logger.debug(
    f"stoploss_transaction_type: {stoploss_transaction_type}, limit_prc: {limit_prc}"
)
trigger_prc = calculate_trigger_price(stoploss_transaction_type, limit_prc)

orders_to_place = [
    {
        "strategy": strategy_name,
        "signal": "Short",
        "base_symbol": base_symbol,
        "exchange_token": hedge_exchange_token,
        "transaction_type": hedge_transaction_type,
        "order_type": order_type,
        "product_type": product_type,
        "order_mode": "HedgeEntry",
        "trade_id": next_trade_prefix,
        "trade_mode": TRADE_MODE,
    },
    {
        "strategy": strategy_name,
        "signal": "Short",
        "base_symbol": base_symbol,
        "exchange_token": main_exchange_token,
        "transaction_type": main_transaction_type,
        "order_type": order_type,
        "product_type": product_type,
        "order_mode": "Main",
        "trade_id": next_trade_prefix,
        "trade_mode": TRADE_MODE,
    },
    {
        "strategy": strategy_name,
        "signal": "Short",
        "base_symbol": base_symbol,
        "exchange_token": main_exchange_token,
        "transaction_type": stoploss_transaction_type,
        "order_type": "Stoploss",
        "product_type": product_type,
        "limit_prc": limit_prc,
        "trigger_prc": trigger_prc,
        "order_mode": "SL",
        "trade_id": next_trade_prefix,
        "trade_mode": TRADE_MODE,
    },
]

orders_to_place = assign_trade_id(orders_to_place)


def main():
    """
    Main function to execute the strategy.

    This function waits until the desired start time and then places the orders
    based on the strategy parameters and current market conditions.
    """
    global strategy_name, prediction
    now = dt.datetime.now()

    if now.date() in ExeUtils.holidays:
        logger.info("Skipping execution as today is a holiday.")
        return

    if now.time() < dt.time(9, 0):
        logger.info("Time is before 9:00 AM, Waiting to execute.")
    else:
        wait_time = (
            dt.datetime(now.year, now.month, now.day, start_hour, start_minute) - now
        )

        if wait_time.total_seconds() > 0:
            logger.info(f"Waiting for {wait_time} before starting the bot")
            sleep(wait_time.total_seconds())

        main_trade_id = None
        logger.info(f"orders_to_place{orders_to_place}")

        for order in orders_to_place:
            if order.get("order_mode") == "MO":
                main_trade_id = order.get("trade_id")
                main_trade_id_prefix = main_trade_id.split("_")[0]

        signals_to_log = {
            "TradeId": main_trade_id,
            "Signal": "Short",
            "EntryTime": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Orders": orders_to_place,
            "StrategyInfo": {
                "direction": prediction,
                "sl_multipler": stoploss_multiplier,
                "strike_multipler": strike_prc_multiplier,
                "hedge_multipler": hedge_multiplier,
                "trade_id": main_trade_id_prefix,
            },
            "Status": "Open",
        }

        update_signal_firebase(strategy_name, signals_to_log, next_trade_prefix)

        message_for_orders("Live", prediction, main_trade_symbol, hedge_trade_symbol)

        place_order_strategy_users(strategy_name, orders_to_place)


if __name__ == "__main__":
    main()
