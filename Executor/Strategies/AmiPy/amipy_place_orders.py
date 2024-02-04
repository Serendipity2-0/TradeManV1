import os,sys
import datetime as dt

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

from loguru import logger
ERROR_LOG_PATH = os.getenv('ERROR_LOG_PATH')
logger.add(ERROR_LOG_PATH,level="TRACE", rotation="00:00",enqueue=True,backtrace=True, diagnose=True)


from Executor.Strategies.StrategiesUtil import StrategyBase
from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import Instrument
from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import discord_bot

strategy_obj = StrategyBase.load_from_db('AmiPy')
instrument_obj = Instrument()


def place_orders(strike_prc, signal):
    strategy_name = strategy_obj.StrategyName
    order_type = strategy_obj.GeneralParams.OrderType
    product_type = strategy_obj.GeneralParams.ProductType

    base_symbol = strategy_obj.Instruments[0]
    expiry_date = instrument_obj.get_expiry_by_criteria(base_symbol, strike_prc, "CE", "current_week")

    orders_to_place = []

    main_CE_exchange_token = instrument_obj.get_exchange_token_by_criteria(base_symbol, strike_prc, "CE", expiry_date)
    main_PE_exchange_token = instrument_obj.get_exchange_token_by_criteria(base_symbol, strike_prc, "PE", expiry_date)

    main_orders = [
        {"exchange_token": main_CE_exchange_token, "order_mode": "Main"},
        {"exchange_token": main_PE_exchange_token, "order_mode": "Main"}
    ]
    
    if "Short" in signal:
        hedge_ce_strike_prc = strike_prc + strategy_obj.ExtraInformation.HedgeDistance
        hedge_pe_strike_prc = strike_prc - strategy_obj.ExtraInformation.HedgeDistance

        hedge_CE_exchange_token = instrument_obj.get_exchange_token_by_criteria(base_symbol, hedge_ce_strike_prc, "CE", expiry_date)
        hedge_PE_exchange_token = instrument_obj.get_exchange_token_by_criteria(base_symbol, hedge_pe_strike_prc, "PE", expiry_date)

        hedge_orders = [
            {"exchange_token": hedge_CE_exchange_token, "order_mode": "Hedge"},
            {"exchange_token": hedge_PE_exchange_token, "order_mode": "Hedge"}
        ]
        hedge_transaction_type = "BUY" if "ShortSignal" in signal else "SELL"
        main_transaction_type = "SELL" if "ShortSignal" in signal else "BUY"

        if signal == "ShortCoverSignal":
            orders_to_place.extend(main_orders)  # Add main orders first
            orders_to_place.extend(hedge_orders)  # Then add hedge orders
        else:
            orders_to_place.extend(hedge_orders)  # For other short signals, hedge orders first
            orders_to_place.extend(main_orders)  # Then main orders

    else:  # Long Orders
        main_transaction_type = "BUY" if "LongSignal" in signal else "SELL"
        hedge_transaction_type = None  # No hedge orders for long positions
        orders_to_place.extend(main_orders)
   
    trade_type  = "entry" if signal == "ShortSignal" or signal == "LongSignal" else "exit"

    trade_id = strategy_obj.NextTradeId

    for order in orders_to_place:
        transaction_type = hedge_transaction_type if "Hedge" in order['order_mode'] else main_transaction_type
        order.update({
            "strategy": strategy_name,
            "base_symbol": base_symbol,
            "transaction_type": transaction_type,
            "order_type": order_type,
            "product_type": product_type,
            "trade_id": trade_id
        })
    message_for_orders(trade_type,signal,main_CE_exchange_token,main_PE_exchange_token, hedge_CE_exchange_token, hedge_PE_exchange_token)
    logger.info(orders_to_place)
        # place_order.place_order_for_strategy(strategy_name, orders_to_place)

def message_for_orders(trade_type,signal,main_CE_exchange_token,main_PE_exchange_token, hedge_CE_exchange_token, hedge_PE_exchange_token):
    
    main_trade_CE_symbol = instrument_obj.get_trading_symbol_by_exchange_token(main_CE_exchange_token)
    main_trade_PE_symbol = instrument_obj.get_trading_symbol_by_exchange_token(main_PE_exchange_token)
    if hedge_CE_exchange_token:
        hedge_trade_CE_symbol = instrument_obj.get_trading_symbol_by_exchange_token(hedge_CE_exchange_token)
    else:
        hedge_trade_CE_symbol = None 
    if hedge_PE_exchange_token:
        hedge_trade_PE_symbol = instrument_obj.get_trading_symbol_by_exchange_token(hedge_PE_exchange_token)
    else:
        hedge_trade_PE_symbol = None

    message = ( f"{trade_type} Order for Amipy\n"
            f"signal : {signal}\n"
            f"main_CE_symbol : {main_trade_CE_symbol}\n"
            f"main_PE_symbol : {main_trade_PE_symbol}\n"
            f"Hedge CE Trade {hedge_trade_CE_symbol} \n"
            f"Hedge PE Trade {hedge_trade_PE_symbol} \n")
    logger.info(message)    
    
    discord_bot(message, strategy_obj.StrategyName)