import os
import sys
import sqlite3
import pandas as pd
from dotenv import load_dotenv
from time import sleep
import datetime as dt

DIR = os.getcwd()
sys.path.append(DIR)
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter import (
    read_strategy_table as read_strategy_table,
    get_db_connection,
    create_holding_strategy_table,
)
from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import (
    Instrument as instrument_obj,
    get_single_ltp,
)
from Executor.NSEStrategies.NSEStrategiesUtil import (
    update_qty_user_firebase,
    assign_trade_id,
    place_order_single_user,
    fetch_qty_amplifier,
    fetch_strategy_amplifier,
    fetch_strategy_users,
    StrategyBase,
)
import Executor.ExecutorUtils.ExeUtils as ExeUtils
from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
    fetch_user_json_from_firebase,
)
from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import (
    send_messsage_via_discord,
)


logger = LoggerSetup()
LONG_RATIO = "Long_Ratio"
LONG_COMBO = "Long_Combo"
TODAY_STOCK_DATA_DB_PATH = os.getenv("TODAY_STOCK_DATA_DB_PATH")


class LongTerm(StrategyBase):
    def get_general_params(self):
        return self.GeneralParams

    def get_entry_params(self):
        return self.EntryParams

    def get_exit_params(self):
        return self.ExitParams

    def get_raw_field(self, field_name: str):
        return super().get_raw_field(field_name)


longterm_obj = LongTerm.load_from_db("LongTerm")
strategy_name = longterm_obj.StrategyName
order_type = longterm_obj.GeneralParams.OrderType
product_type = longterm_obj.GeneralParams.ProductType
strategy_type = longterm_obj.GeneralParams.StrategyType
desired_start_time_str = longterm_obj.get_entry_params().EntryTime
longterm_prefix = longterm_obj.StrategyPrefix
num_stocks = longterm_obj.ExtraInformation.StocksPerStrategy


def get_today_stocks():
    """
    Get today's stocks.

    Returns:
        pandas.DataFrame: DataFrame containing today's stocks.
    """
    try:
        conn = sqlite3.connect(TODAY_STOCK_DATA_DB_PATH)

        # Load the data from the identified table "CombinedStocks"
        df = pd.read_sql_query("SELECT * FROM CombinedStocks", conn)

        # Filter the rows where any column name starting with "Long_" is equal to 1
        longterm_stocks_df = df[df.filter(regex="Long_").eq(1).any(axis=1)]

        # Sort by AthLtpRatio in descending order and get the top 5 stocks
        longterm_stocks = longterm_stocks_df.sort_values(
            by="AthLtpRatio", ascending=False
        )
        return longterm_stocks
    except Exception as e:
        logger.error(f"Error getting today's stocks{e}")
        return pd.DataFrame()


def main():
    """
    Retrieves and processes today's top stock picks, places orders for users if needed.
    """
    start_hour, start_minute, _ = map(int, desired_start_time_str.split(":"))
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

    from Executor.NSEStrategies.Equity.Equity import signals_to_fb

    selected_stocks_df = get_today_stocks()
    symbol_list = selected_stocks_df["Symbol"].tolist()

    long_term_setups = [
        col for col in selected_stocks_df.columns if col.startswith("Long_")
    ]
    logger.info(f"Longterm setups: {long_term_setups}")

    if symbol_list == []:
        logger.info("No stocks selected for today in Longterm")
        return
    else:
        logger.info(f"Stocks selected for today for Longterm: {symbol_list}")

    trade_id_mapping = {}

    for setup_name in long_term_setups:
        setup_symbol_list = selected_stocks_df[selected_stocks_df[setup_name] == 1][
            "Symbol"
        ].tolist()
        logger.debug(f"Stocks for {setup_name}: {setup_symbol_list}")
        users = fetch_strategy_users(
            setup_name.upper(), "Equity", "LongTerm"
        )  # TODO refactor the name
        for user in users:
            db_path = os.path.join(
                os.getenv("USR_TRADELOG_EQUITY_DB_FOLDER"), f"{user['Tr_No']}_equity.db"
            )
            conn = get_db_connection(db_path)
            try:
                holdings = read_strategy_table(conn, "Holdings")
            except Exception:
                # create a new table
                create_holding_strategy_table(conn, "Holdings")
            holdings = read_strategy_table(conn, "Holdings")
            longterm_holdings = holdings[
                holdings["trade_id"].str.startswith(longterm_prefix)
            ]
            setup_holdings = longterm_holdings[
                longterm_holdings["setup"].isin([setup_name.upper()])
            ]
            current_holdings_count = len(setup_holdings)
            logger.debug(
                f"Current holdings for user {user['Tr_No']} for Longterm for {setup_name}: {current_holdings_count}"
            )

            if current_holdings_count < 3:
                needed_orders = 3 - current_holdings_count
                for index, symbol in enumerate(setup_symbol_list):
                    if needed_orders == 0:
                        break  # Stop processing if no more orders are needed

                    logger.info(f"Setup for {symbol}: {setup_name}")
                    new_base = longterm_obj.reload_strategy(strategy_name)
                    if symbol not in trade_id_mapping:
                        trade_id_mapping[symbol] = new_base.NextTradeId

                    trade_id = trade_id_mapping[symbol]

                    exchange_token = instrument_obj().get_exchange_token_by_name(
                        symbol, "NSE"
                    )
                    ltp = get_single_ltp(exchange_token=exchange_token, segment="NSE")
                    ltp = round(ltp * 20) / 20
                    order_details = [
                        {
                            "strategy": strategy_name,
                            "signal": "Long",
                            "base_symbol": symbol,
                            "exchange_token": exchange_token,
                            "transaction_type": "BUY",
                            "order_type": order_type,
                            "product_type": product_type,
                            "order_mode": "MainEntry",
                            "trade_id": trade_id,
                            "limit_prc": ltp,
                            "trade_mode": os.getenv("TRADE_MODE"),
                            "setup": setup_name.upper(),
                        }
                    ]
                    order_to_place = assign_trade_id(order_details)
                    qty_amplifier = fetch_qty_amplifier(strategy_name, strategy_type)
                    strategy_amplifier = fetch_strategy_amplifier(strategy_name)
                    update_qty_user_firebase(
                        strategy_name=setup_name.upper(),
                        avg_sl_points_or_ltp=ltp,
                        qty_amplifier=qty_amplifier,
                        strategy_amplifier=strategy_amplifier,
                        asset_segment="Equity",
                        asset_term="LongTerm",
                        num_stocks=num_stocks,
                    )
                    logger.info(order_to_place)
                    signals_to_fb(strategy_name, order_to_place, trade_id)
                    updated_user = fetch_user_json_from_firebase(user["Tr_No"])
                    order_status = place_order_single_user(
                        [updated_user], order_to_place
                    )
                    logger.debug(f"Orders placed for {symbol}: {order_to_place}")
                    send_messsage_via_discord(
                        f"Entry Long Term Orders placed for {symbol}: with trade_id {trade_id} at {ltp}",
                        strategy_name,
                    )

                    # Should come up with a better way to check for failed orders

                    if os.getenv("TRADE_MODE") != "PAPER":
                        if user["Tr_No"] == os.getenv(
                            "ZERODHA_PRIMARY_ACCOUNT"
                        ) and any(
                            order["order_status"] == "FAIL" for order in order_status
                        ):
                            # Reassign the trade ID to the next symbol if there is one
                            if index + 1 < len(symbol_list):
                                next_symbol = symbol_list[index + 1]
                                trade_id_mapping[next_symbol] = trade_id
                                logger.debug(
                                    f"Trade ID {trade_id} reassigned from {symbol} to {next_symbol}"
                                )

                    needed_orders -= 1

                logger.debug(
                    f"Updated holdings count for user {user['Tr_No']} should be 3"
                )


if "__main__" == __name__:
    main()
