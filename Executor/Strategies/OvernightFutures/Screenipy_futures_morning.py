import os
import sys
from dotenv import load_dotenv
import datetime as dt
from time import sleep

# Set up paths and import modules
DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.Strategies.StrategiesUtil import StrategyBase
import Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils as InstrumentCenterUtils
from Executor.ExecutorUtils.ExeUtils import holidays
from Executor.Strategies.StrategiesUtil import assign_trade_id, fetch_previous_trade_id, place_order_strategy_users

strategy_obj = StrategyBase.load_from_db("OvernightFutures")
instrument_obj = InstrumentCenterUtils.Instrument()

strategy_name = strategy_obj.StrategyName

prediction = strategy_obj.ExtraInformation.Prediction
hedge_exchange_token = strategy_obj.ExtraInformation.HedgeExchangeToken
futures_exchange_token = strategy_obj.ExtraInformation.FuturesExchangeToken

hedge_transcation_type = strategy_obj.GeneralParams.HedgeTransactionType

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
    },
]


def is_yesterday_holiday(today):
    """Check if yesterday was a holiday."""
    yesterday = today - dt.timedelta(days=1)
    return yesterday in holidays


def main():
    global orders_to_place
    now = dt.datetime.now()

    # Check if today is the day after a holiday
    if is_yesterday_holiday(now.date()):
        print("Skipping execution as yesterday was a holiday.")
        return

    desired_end_time_str = strategy_obj.ExitParams.SquareOffTime
    start_hour, start_minute, start_second = map(int, desired_end_time_str.split(":"))
    wait_time = (
        dt.datetime(now.year, now.month, now.day, start_hour, start_minute) - now
    )
    if wait_time.total_seconds() > 0:
        print(f"Waiting for {wait_time} before starting the bot")
        sleep(wait_time.total_seconds())

    orders_to_place = assign_trade_id(orders_to_place)

    print(orders_to_place)
    place_order_strategy_users(strategy_name,orders_to_place)


if __name__ == "__main__":
    main()
