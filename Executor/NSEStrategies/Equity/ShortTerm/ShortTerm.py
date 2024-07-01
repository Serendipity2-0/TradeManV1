import pandas as pd
import yfinance as yf
import os
from dotenv import load_dotenv
import sys
import sqlite3
DIR = os.getcwd()
sys.path.append(DIR)
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)


from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter import (
    fetch_sql_table_from_db as fetch_table_from_db,
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
    fetch_strategy_users
)


logger = LoggerSetup()

stock_pick_db_path = os.getenv("today_stock_data_db_path")

def get_today_stocks():
    """
    Get today's stocks.

    Returns:
        pandas.DataFrame: DataFrame containing today's stocks.
    """
    try:
        conn = sqlite3.connect(stock_pick_db_path)

        # Load the data from the identified table "CombinedStocks"
        df = pd.read_sql_query("SELECT * FROM CombinedStocks", conn)

        # Filter the rows where Short_Momentum, Short_EMABBConfluence, or Short_MeanReversion column is 1
        shortterm_stocks_df = df[
            (df['Short_Momentum'] == 1) |
            (df['Short_EMABBConfluence'] == 1) |
            (df['Short_MeanReversion'] == 1)
        ]

        # Sort by AthLtpRatio in descending order and get the top 5 stocks
        top_5_stocks_df = shortterm_stocks_df.sort_values(by='AthLtpRatio', ascending=False).head(5)
        return top_5_stocks_df
    except Exception as e:
        logger.error("Error getting today's stocks")


def main():
    """
    Retrieves short term momentum, mean reversion and EMA-BB confluence stocks.
    Combines and sorts stocks by ATH to LTP ratio.
    Exports sorted list to CSV and returns top picks.

    Args:
        stock_data_dict (dict): A dictionary containing stock data.

    Returns:
        list: A sorted list of short term stock picks.
    """
    # Example usage
    from Executor.NSEStrategies.Equity.Equity import pystocks_obj,strategy_name,strategy_type,order_type,product_type,signals_to_fb 
    top5_stocks_df = get_today_stocks()
    symbol_list = top5_stocks_df["Symbol"].tolist()
     
    # Display the filtered and sorted DataFrame
    logger.info(f"Stocks selected for Today:{symbol_list}")
    
    trade_id_mapping = {}
    
    users = fetch_strategy_users("PyStocks")
    for user in users:
        holdings = fetch_table_from_db(user["Tr_No"], "Holdings")
        py_holdings = holdings[holdings["trade_id"].str.startswith("PS")]
        current_holdings_count = len(py_holdings)
        logger.debug(
            f"Current holdings for user {user['Tr_No']}: {current_holdings_count}"
        )

        if current_holdings_count < 5:
            needed_orders = 5 - current_holdings_count
            for index, symbol in enumerate(symbol_list):
                if needed_orders == 0:
                    break  # Stop processing if no more orders are needed

                new_base = pystocks_obj.reload_strategy(pystocks_obj.StrategyName)
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
                        "trade_mode": os.getenv("TRADE_MODE")
                    }
                ]
                order_to_place = assign_trade_id(order_details)
                qty_amplifier = fetch_qty_amplifier(strategy_name, strategy_type)
                strategy_amplifier = fetch_strategy_amplifier(strategy_name)
                update_qty_user_firebase(
                    strategy_name, ltp, 1, qty_amplifier, strategy_amplifier
                )
                signals_to_fb(order_to_place, trade_id)
                order_status = place_order_single_user([user], order_to_place)
                logger.debug(f"Orders placed for {symbol}: {order_to_place}")

                # Should come up with a better way to check for failed orders

                if os.getenv("TRADE_MODE") != "PAPER":
                    if user["Tr_No"] == "Tr00" and any(
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
                f"Updated holdings count for user {user['Tr_No']} should be 5"
            )


if "__main__" == __name__:
    main()
