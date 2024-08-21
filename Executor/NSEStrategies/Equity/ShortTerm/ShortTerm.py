import pandas as pd
import os
from dotenv import load_dotenv
import sys
import sqlite3

DIR = os.getcwd()
sys.path.append(DIR)
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

TRADE_MODE = os.getenv("TRADE_MODE")

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter import (
    read_strategy_table as read_strategy_table,
    get_db_connection as get_db_connection,
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
from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
    fetch_user_json_from_firebase,
)
from Executor.ExecutorUtils.EquityCenter.EquityCenterUtils import (
    check_symbol_for_erros,
    is_today_holiday,
    should_wait_for_start_time,
    get_selected_stocks,
    send_signals_via_discord,
)

logger = LoggerSetup()

TODAY_STOCK_DATA_DB_PATH = os.getenv("TODAY_STOCK_DATA_DB_PATH")


class ShortTerm(StrategyBase):
    def get_general_params(self):
        return self.GeneralParams

    def get_entry_params(self):
        return self.EntryParams

    def get_exit_params(self):
        return self.ExitParams

    def get_raw_field(self, field_name: str):
        return super().get_raw_field(field_name)


shortterm_obj = ShortTerm.load_from_db("ShortTerm")
strategy_name = shortterm_obj.StrategyName
order_type = shortterm_obj.GeneralParams.OrderType
product_type = shortterm_obj.GeneralParams.ProductType
strategy_type = shortterm_obj.GeneralParams.StrategyType
desired_start_time_str = shortterm_obj.get_entry_params().EntryTime
shortterm_prefix = shortterm_obj.StrategyPrefix
num_stocks = shortterm_obj.ExtraInformation.StocksPerStrategy
transaction_type = shortterm_obj.GeneralParams.TransactionType


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

        # Filter the rows where any column name starting with "Short_" is equal to 1
        shortterm_stocks_df = df[df.filter(regex="Short_").eq(1).any(axis=1)]

        # Sort by AthLtpRatio in descending order and get the top 5 stocks
        shortterm_stocks = shortterm_stocks_df.sort_values(
            by="AthLtpRatio", ascending=False
        )
        return shortterm_stocks
    except Exception as e:
        logger.error(f"Error getting today's stocks{e}")
        return pd.DataFrame()


def process_users(setup_name, setup_symbol_list):
    """
    Process the users for the strategy.

    Args:
        setup_name (str): The name of the setup.
        setup_symbol_list (list): The list of symbols.
    """
    users = fetch_strategy_users(setup_name.upper(), "Equity", strategy_name)
    for user in users:
        process_holdings_for_user(user, setup_symbol_list, setup_name)


def process_holdings_for_user(user, setup_symbol_list, setup_name):
    """
    Process the holdings for the user.

    Args:
        user (dict): The user dictionary.
        setup_symbol_list (list): The list of symbols.
        setup_name (str): The name of the setup.
    """
    db_path = os.path.join(
        os.getenv("USR_TRADELOG_EQUITY_DB_FOLDER"), f"{user['Tr_No']}_equity.db"
    )
    conn = get_db_connection(db_path)
    try:
        holdings = read_strategy_table(conn, "Holdings")
    except Exception:
        create_holding_strategy_table(conn, "Holdings")
        holdings = read_strategy_table(conn, "Holdings")
    try:
        manage_holdings_and_place_orders(user, holdings, setup_symbol_list, setup_name)
    except Exception as e:
        logger.error(
            f"Error processing holdings for user {user['Tr_No']} for {setup_name}: {e}"
        )


def manage_holdings_and_place_orders(user, holdings, setup_symbol_list, setup_name):
    """
    Manage the holdings and place the orders.

    Args:
        user (dict): The user dictionary.
        holdings (DataFrame): The holdings DataFrame.
        setup_symbol_list (list): The list of symbols.
        setup_name (str): The name of the setup.

    Returns:
        None
    """
    from Executor.NSEStrategies.Equity.Equity import signals_to_fb

    shortterm_holdings = holdings[holdings["trade_id"].str.startswith(shortterm_prefix)]
    setup_holdings = shortterm_holdings[
        shortterm_holdings["setup"].isin([setup_name.upper()])
    ]

    holdings_symbol_list = setup_holdings["trading_symbol"].tolist()
    current_holdings_count = len(setup_holdings)
    logger.warning(setup_symbol_list)
    logger.debug(
        f"Current holdings for user {user['Tr_No']} for Shortterm for {setup_name}: {current_holdings_count}"
    )

    if current_holdings_count < 3:
        needed_orders = 3 - current_holdings_count
        trade_id_mapping = {}
        for index, symbol in enumerate(setup_symbol_list):
            if needed_orders == 0:
                break  # Stop processing if no more orders are needed

            logger.info(f"Setup for {symbol}: {setup_name}")
            new_base = shortterm_obj.reload_strategy(strategy_name)
            if symbol not in trade_id_mapping:
                trade_id_mapping[symbol] = new_base.NextTradeId

            trade_id = trade_id_mapping[symbol]
            exchange_token = instrument_obj().get_exchange_token_by_name(symbol, "NSE")

            if not check_symbol_for_erros(symbol, exchange_token, holdings_symbol_list):
                logger.error(f"Symbol {symbol} has errors, skipping")
                continue

            ltp = get_single_ltp(exchange_token=exchange_token, segment="NSE")
            ltp = round(ltp * 20) / 20
            order_details = [
                {
                    "strategy": setup_name.upper(),
                    "signal": "Long",
                    "base_symbol": symbol,
                    "exchange_token": exchange_token,
                    "transaction_type": transaction_type,
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
                strategy_name=strategy_name,
                avg_sl_points_or_ltp=ltp,
                qty_amplifier=qty_amplifier,
                strategy_amplifier=strategy_amplifier,
                asset_segment=strategy_type,
                asset_term=strategy_name,
                num_stocks=num_stocks,
            )
            signals_to_fb(strategy_name, order_to_place, trade_id)
            updated_user = fetch_user_json_from_firebase(user["Tr_No"])
            order_status = place_order_single_user([updated_user], order_to_place)
            logger.debug(f"Orders placed for {symbol}: {order_to_place}")

            if TRADE_MODE != "PAPER":
                if user["Tr_No"] == os.getenv("ZERODHA_PRIMARY_ACCOUNT") and any(
                    order["order_status"] == "FAIL" for order in order_status
                ):
                    # Reassign the trade ID to the next symbol if there is one
                    if index + 1 < len(setup_symbol_list):
                        next_symbol = setup_symbol_list[index + 1]
                        trade_id_mapping[next_symbol] = trade_id
                        logger.debug(
                            f"Trade ID {trade_id} reassigned from {symbol} to {next_symbol}"
                        )

            needed_orders -= 1

        logger.debug(f"Updated holdings count for user {user['Tr_No']} should be 3")


def main():
    """
    Main function to run the strategy.

    Returns:
        None
    """
    if is_today_holiday():
        logger.info("Skipping execution as today is a holiday.")
        return

    if should_wait_for_start_time(desired_start_time_str):
        return

    selected_stocks_df = get_today_stocks()
    symbol_list, short_term_setups = get_selected_stocks(
        strategy_name, selected_stocks_df
    )
    if not symbol_list:
        logger.info("No stocks selected for today in ShortTerm")
        return
    else:
        logger.info(f"Stocks selected for today for ShortTerm: {symbol_list}")

    for setup_name in short_term_setups:
        setup_symbol_list = selected_stocks_df[selected_stocks_df[setup_name] == 1][
            "Symbol"
        ].tolist()
        send_signals_via_discord(
            setup_symbol_list, setup_name, strategy_name, TRADE_MODE
        )
        process_users(setup_name, setup_symbol_list)


if "__main__" == __name__:
    main()
