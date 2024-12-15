import os
import pandas as pd
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter import (
    read_strategy_table,
    get_db_connection,
    create_holding_strategy_table,
)
from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import (
    Instrument as instrument_obj,
)
from Executor.ExecutorUtils.InstrumentCenter.ltp_utils import get_single_ltp
from Executor.NSEStrategies.NSEStrategiesUtil import (
    assign_trade_id,
    fetch_qty_amplifier,
    fetch_strategy_amplifier,
    fetch_strategy_users,
    StrategyBase,
)
from Executor.ExecutorUtils.ExeDBUtils.MongoUtils.exemongo_adapter import (
    update_fields_mongodb,
    get_client_by_tr_no,
)
from Executor.ExecutorUtils.OrderCenter.order_utils import place_order_single_user_sync
from Executor.ExecutorUtils.EquityCenter.EquityCenterUtils import (
    check_symbol_for_erros,
    is_today_holiday,
    should_wait_for_start_time,
    get_selected_stocks,
    send_signals_via_discord,
)
from Executor.NSEStrategies.Equity.MidTerm.MidTermDBUtils import get_today_stocks
from Executor.NSEStrategies.Equity.MidTerm.MidTermConfig import (
    midterm_obj,
    strategy_name,
    order_type,
    product_type,
    strategy_type,
    desired_start_time_str,
    midterm_prefix,
    num_stocks,
    transaction_type,
    TRADE_MODE,
    STRATEGIES_DB,
)

logger = LoggerSetup()


class MidTerm(StrategyBase):
    """
    MidTerm trading strategy class that inherits from StrategyBase.
    Implements mid-term trading strategies for equity markets.
    """
    def get_general_params(self):
        """Get general strategy parameters."""
        return self.GeneralParams

    def get_exit_params(self):
        """Get exit parameters for the strategy."""
        return self.ExitParams

    def get_raw_field(self, field_name: str):
        """Get a raw field value by name."""
        return super().get_raw_field(field_name)


def update_qty_user_mongodb(strategy_name, avg_sl_points_or_ltp, qty_amplifier, strategy_amplifier, asset_segment, asset_term, num_stocks):
    """
    Update quantity information in MongoDB.

    Args:
        strategy_name (str): Name of the strategy
        avg_sl_points_or_ltp (float): Average stop loss points or last traded price
        qty_amplifier (float): Quantity amplifier
        strategy_amplifier (float): Strategy amplifier
        asset_segment (str): Asset segment
        asset_term (str): Asset term
        num_stocks (int): Number of stocks

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        data = {
            "avg_sl_points_or_ltp": avg_sl_points_or_ltp,
            "qty_amplifier": qty_amplifier,
            "strategy_amplifier": strategy_amplifier,
            "asset_segment": asset_segment,
            "asset_term": asset_term,
            "num_stocks": num_stocks
        }
        return update_fields_mongodb(STRATEGIES_DB, strategy_name, data, "quantity_info")
    except Exception as e:
        logger.error(f"Error updating quantity info in MongoDB: {e}")
        return False


def signals_to_mongodb(strategy_name, order_details, trade_id):
    """
    Update signals in MongoDB.

    Args:
        strategy_name (str): Name of the strategy
        order_details (list): List of order details
        trade_id (str): Trade ID

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        data = {
            "order_details": order_details,
            "trade_id": trade_id,
            "timestamp": pd.Timestamp.now().isoformat()
        }
        return update_fields_mongodb(STRATEGIES_DB, strategy_name, data, "signals")
    except Exception as e:
        logger.error(f"Error updating signals in MongoDB: {e}")
        return False


def process_holdings_for_user(user, setup_symbol_list, setup_name):
    """
    Process the holdings for a user.

    Args:
        user (dict): The user dictionary
        setup_symbol_list (list): List of symbols for the setup
        setup_name (str): Name of the setup

    Returns:
        None
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
    Manage holdings and place orders for a user.

    Args:
        user (dict): The user dictionary
        holdings (DataFrame): Current holdings
        setup_symbol_list (list): List of symbols for the setup
        setup_name (str): Name of the setup

    Returns:
        None
    """
    if holdings.empty:
        logger.error(f"No holdings found for user {user['Tr_No']} for {setup_name}")
        current_holdings_count = 0
        holdings_symbol_list = []
    else:
        midterm_holdings = holdings[holdings["trade_id"].str.startswith(midterm_prefix)]
        setup_holdings = midterm_holdings[
            midterm_holdings["setup"].isin([setup_name.upper()])
        ]
        holdings_symbol_list = setup_holdings["trading_symbol"].tolist()
        current_holdings_count = len(setup_holdings)
        logger.warning(setup_symbol_list)

    logger.debug(
        f"Current holdings for user {user['Tr_No']} for Midterm for {setup_name}: {current_holdings_count}"
    )

    if current_holdings_count < 3:
        needed_orders = 3 - current_holdings_count
        trade_id_mapping = {}
        
        for index, symbol in enumerate(setup_symbol_list):
            if needed_orders == 0:
                break

            logger.info(f"Setup for {symbol}: {setup_name}")
            new_base = midterm_obj.reload_strategy(strategy_name)
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
                    "strategy": strategy_name,
                    "signal": "Long",
                    "base_symbol": symbol,
                    "exchange_token": exchange_token,
                    "transaction_type": transaction_type,
                    "order_type": order_type,
                    "product_type": product_type,
                    "order_mode": "MainEntry",
                    "trade_id": trade_id,
                    "limit_prc": ltp,
                    "trade_mode": TRADE_MODE,
                    "setup": setup_name.upper(),
                }
            ]
            
            order_to_place = assign_trade_id(order_details)
            qty_amplifier = fetch_qty_amplifier(strategy_name, strategy_type)
            strategy_amplifier = fetch_strategy_amplifier(strategy_name)
            
            update_qty_user_mongodb(
                strategy_name=setup_name.upper(),
                avg_sl_points_or_ltp=ltp,
                qty_amplifier=qty_amplifier,
                strategy_amplifier=strategy_amplifier,
                asset_segment=strategy_type,
                asset_term=strategy_name,
                num_stocks=num_stocks,
            )
            
            signals_to_mongodb(strategy_name, order_to_place, trade_id)
            updated_user = get_client_by_tr_no(user["Tr_No"])
            order_status = place_order_single_user_sync([updated_user], order_to_place)
            
            for order_detail in order_status:
                if "PASS" in order_detail["order_status"]:
                    logger.debug(f"Order placed successfully for {symbol}: {order_detail}")
                    if TRADE_MODE != "PAPER":
                        needed_orders -= 1
                elif "ASM/GSM" in order_detail["order_status"]:
                    logger.debug(f"ASM/GSM issue with {symbol}")
                    if TRADE_MODE != "PAPER" and index + 1 < len(setup_symbol_list):
                        next_symbol = setup_symbol_list[index + 1]
                        trade_id_mapping[next_symbol] = trade_id
                        logger.debug(
                            f"Trade ID {trade_id} reassigned from {symbol} to {next_symbol}"
                        )
                    elif TRADE_MODE == "PAPER":
                        logger.debug(
                            f"ASM/GSM issue with {symbol} in PAPER mode; no trade ID reassignment."
                        )
                    else:
                        logger.error(
                            f"No more symbols to reassign trade ID {trade_id} after ASM/GSM issue with {symbol}"
                        )
                else:
                    logger.warning(
                        f"Order failed for {symbol} but continuing: {order_detail['order_status']}"
                    )
                    if TRADE_MODE != "PAPER":
                        needed_orders -= 1

        logger.debug(f"Updated holdings count for user {user['Tr_No']} should be 3")


def process_users(setup_name, setup_symbol_list):
    """
    Process users for a given setup.

    Args:
        setup_name (str): Name of the setup
        setup_symbol_list (list): List of symbols for the setup

    Returns:
        None
    """
    users = fetch_strategy_users(setup_name.upper(), "Equity", strategy_name)
    for user in users:
        process_holdings_for_user(user, setup_symbol_list, setup_name)


def main():
    """
    Main function to run the MidTerm strategy.
    Orchestrates the entire trading process including:
    - Holiday checks
    - Time checks
    - Stock selection
    - Signal generation
    - Order processing
    """
    if is_today_holiday():
        logger.info("Skipping execution as today is a holiday.")
        return

    if should_wait_for_start_time(desired_start_time_str):
        return

    # Get stocks from database
    selected_stocks_df = get_today_stocks()
    if selected_stocks_df.empty:
        logger.info("No stocks selected for today in MidTerm")
        return

    # Get strategy-specific stocks
    symbol_list, short_term_setups = get_selected_stocks(
        strategy_name, selected_stocks_df
    )
    if not symbol_list:
        logger.info("No stocks selected for today in MidTerm")
        return

    logger.info(f"Stocks selected for today for MidTerm: {symbol_list}")

    # Process each setup
    for setup_name in short_term_setups:
        setup_symbol_list = selected_stocks_df[selected_stocks_df[setup_name] == 1][
            "Symbol"
        ].tolist()
        send_signals_via_discord(
            setup_symbol_list, setup_name, strategy_name, TRADE_MODE
        )
        process_users(setup_name, setup_symbol_list)


if __name__ == "__main__":
    main()
