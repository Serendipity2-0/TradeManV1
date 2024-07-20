import os
import sys
from dotenv import load_dotenv
import datetime as dt
from time import sleep

# Set up paths and import modules
DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

TRADE_MODE = os.getenv("TRADE_MODE")
ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.NSEStrategies.NSEStrategiesUtil import StrategyBase
import Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils as InstrumentCenterUtils
from Executor.ExecutorUtils.ExeUtils import holidays
from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import (
    discord_bot,
)
from Executor.NSEStrategies.NSEStrategiesUtil import (
    assign_trade_id,
    fetch_previous_trade_id,
    place_order_strategy_users,
)
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()

strategy_obj = StrategyBase.load_from_db("OvernightFutures")
instrument_obj = InstrumentCenterUtils.Instrument()

strategy_name = strategy_obj.StrategyName

prediction = strategy_obj.ExtraInformation.Prediction
hedge_exchange_token = strategy_obj.ExtraInformation.HedgeExchangeToken
futures_exchange_token = strategy_obj.ExtraInformation.FuturesExchangeToken

hedge_transcation_type = strategy_obj.get_raw_field("GeneralParams").get(
    "HedgeSqroffTransactionType"
)

order_type = strategy_obj.GeneralParams.OrderType
product_type = strategy_obj.GeneralParams.ProductType
base_symbol = strategy_obj.Instruments[0]
previous_trade_prefix = fetch_previous_trade_id(strategy_obj.NextTradeId)


signal = "Long" if prediction == "Bullish" else "Short"

orders_to_place = [
    {
        "strategy": strategy_name,
        "signal": signal,
        "base_symbol": base_symbol,
        "exchange_token": futures_exchange_token,
        "transaction_type": strategy_obj.get_square_off_transaction(prediction),
        "order_type": order_type,
        "product_type": product_type,
        "order_mode": "MainExit",
        "strategy_mode": "CarryForward",
        "trade_id": previous_trade_prefix,
        "trade_mode": TRADE_MODE,
    },
    {
        "strategy": strategy_name,
        "signal": signal,
        "base_symbol": base_symbol,
        "exchange_token": hedge_exchange_token,
        "transaction_type": hedge_transcation_type,
        "order_type": order_type,
        "product_type": product_type,
        "order_mode": "HedgeExit",
        "strategy_mode": "CarryForward",
        "trade_id": previous_trade_prefix,
        "trade_mode": TRADE_MODE,
    },
]


def is_today_holiday(today):
    """
    Check if today is a holiday.

    Args:
        today (datetime.date): The date to check.

    Returns:
        bool: True if today is a holiday, False otherwise.
    """
    return today in holidays


def main():
    """
    The main function checks if today is a holiday, waits until a specified time, assigns trade IDs to
    orders, places orders based on a strategy, and sends a notification via Discord.
    :return: If today is a holiday or the day after a holiday, the function will return without
    executing further code. Otherwise, it will wait for a specific time before starting the bot, assign
    trade IDs to orders, log the orders, place the orders based on the strategy, and send a message to a
    Discord bot indicating that exit orders have been placed for a specific strategy.
    """

    global orders_to_place
    # Check if today is the day after a holiday
    now = dt.datetime.now()
    yesterday = now - dt.timedelta(days=1)

    if now.date() in holidays or yesterday.date() in holidays:
        logger.info("Skipping execution as today is a holiday.")
        return

    desired_end_time_str = strategy_obj.ExitParams.SquareOffTime
    start_hour, start_minute, start_second = map(int, desired_end_time_str.split(":"))
    wait_time = (
        dt.datetime(now.year, now.month, now.day, start_hour, start_minute) - now
    )
    if wait_time.total_seconds() > 0:
        logger.info(f"Waiting for {wait_time} before starting the bot")
        sleep(wait_time.total_seconds())

    orders_to_place = assign_trade_id(orders_to_place)

    logger.debug(orders_to_place)
    place_order_strategy_users(strategy_name, orders_to_place, "Holdings")
    discord_bot(f"Exit Orders placed for {strategy_name}", strategy_name)


if __name__ == "__main__":
    main()
