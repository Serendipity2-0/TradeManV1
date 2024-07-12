import os
import sys
import datetime
from dotenv import load_dotenv

# Load settings
DIR = os.getcwd()
sys.path.append(DIR)
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

import Executor.ExecutorUtils.ExeUtils as ExeUtils
from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
    fetch_users_for_strategies_from_firebase as fetch_active_users,
)
from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter import (
    read_strategy_table,
    get_db_connection,
)
from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import (
    get_single_ltp,
    Instrument,
)
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.NSEStrategies.Equity.EquityStopLoss.EquityStopLossUtils import (
    calculate_sl,
)
from Executor.NSEStrategies.NSEStrategiesUtil import (
    assign_trade_id,
    place_order_single_user,
)
from Executor.NSEStrategies.Equity.ShortTerm.ShortTerm import shortterm_obj
from Executor.NSEStrategies.Equity.MidTerm.MidTerm import midterm_obj
from Executor.NSEStrategies.Equity.LongTerm.LongTerm import longterm_obj

# Initialize logger
logger = LoggerSetup()

# Strategy configurations
strategies = [
    (shortterm_obj, "ShortTerm"),
    (midterm_obj, "MidTerm"),
    (longterm_obj, "LongTerm"),
]

trade_mode = os.getenv("TRADE_MODE")


def main():
    now = datetime.datetime.now()
    if now.date() in ExeUtils.holidays:
        logger.info("Skipping execution as today is a holiday.")
        return

    for strategy_obj, strategy_type in strategies:
        users = fetch_active_users(
            strategy_obj.StrategyName
        )  # Fetch users dynamically based on the strategy name
        for user in users:
            db_path = os.path.join(
                os.getenv("USR_TRADELOG_EQUITY_DB_FOLDER"), f"{user['Tr_No']}_equity.db"
            )
            conn = get_db_connection(db_path)
            holdings = read_strategy_table(conn, "Holdings")
            strategy_prefix = strategy_obj.StrategyPrefix
            strategy_holdings = holdings[
                holdings["trade_id"].str.startswith(strategy_prefix)
            ]
            process_holdings(strategy_obj, strategy_holdings, user)


def process_holdings(strategy_obj, holdings, user):
    strategy_name = strategy_obj.StrategyName
    transaction_type = strategy_obj.get_raw_field("GeneralParams").get(
        "SlTransactionType"
    )
    product_type = strategy_obj.GeneralParams.ProductType
    order_type = strategy_obj.get_raw_field("GeneralParams").get("SlOrderType")

    for index, row in holdings.iterrows():
        symbol = row["trading_symbol"]
        exchange_token = Instrument().get_exchange_token_by_name(symbol, "NSE")
        ltp = get_single_ltp(exchange_token=exchange_token, segment="NSE")
        buy_price = float(row["entry_price"])
        setup_name = row["setup"]
        sl = calculate_sl(
            setup_name, buy_price, strategy_obj.EntryParams.SLMultiplier, ltp
        )
        trade_id = row["trade_id"].split("_")[0]

        logger.debug("LTP", ltp, "Buy Price", buy_price, "SL", sl)
        order_details = [
            {
                "strategy": strategy_name,
                "signal": "Long",
                "base_symbol": symbol,
                "exchange_token": exchange_token,
                "transaction_type": transaction_type,
                "order_type": order_type,
                "product_type": product_type,
                "order_mode": "SL",
                "trade_id": trade_id,
                "trade_mode": trade_mode,
                "limit_prc": sl,
                "trigger_prc": sl + 0.3,
                "setup": setup_name,
            }
        ]
        order_to_place = assign_trade_id(order_details)
        logger.debug(f"Orders to place: {order_to_place}")
        place_order_single_user([user], order_to_place)


if __name__ == "__main__":
    main()
