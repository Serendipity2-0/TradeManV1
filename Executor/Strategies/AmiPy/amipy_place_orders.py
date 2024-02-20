import os, sys
import datetime as dt
from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")

load_dotenv(ENV_PATH)
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


from Executor.Strategies.StrategiesUtil import (
    StrategyBase,
    assign_trade_id,
    update_qty_user_firebase,
    update_signal_firebase,
    fetch_previous_trade_id,
    place_order_strategy_users,
)
from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import Instrument
from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import (
    discord_bot,    
)
from Executor.ExecutorUtils.InstrumentCenter.FNOInfoBase import FNOInfo

strategy_obj = StrategyBase.load_from_db("AmiPy")
instrument_obj = Instrument()

avg_sl_points = strategy_obj.ExitParams.AvgSLPoints
lot_size = FNOInfo().get_lot_size_by_base_symbol(strategy_obj.Instruments[0])
next_trade_prefix = strategy_obj.NextTradeId

def message_for_orders(
    trade_type,
    signal,
    main_CE_exchange_token,
    main_PE_exchange_token,
    hedge_CE_exchange_token,
    hedge_PE_exchange_token,
):

    main_trade_CE_symbol = instrument_obj.get_trading_symbol_by_exchange_token(
        main_CE_exchange_token
    )
    main_trade_PE_symbol = instrument_obj.get_trading_symbol_by_exchange_token(
        main_PE_exchange_token
    )
    if hedge_CE_exchange_token:
        hedge_trade_CE_symbol = instrument_obj.get_trading_symbol_by_exchange_token(
            hedge_CE_exchange_token
        )
    else:
        hedge_trade_CE_symbol = None
    if hedge_PE_exchange_token:
        hedge_trade_PE_symbol = instrument_obj.get_trading_symbol_by_exchange_token(
            hedge_PE_exchange_token
        )
    else:
        hedge_trade_PE_symbol = None

    message = (
        f"{trade_type} Order for Amipy\n"
        f"signal : {signal}\n"
        f"main_CE_symbol : {main_trade_CE_symbol}\n"
        f"main_PE_symbol : {main_trade_PE_symbol}\n"
        f"Hedge CE Trade {hedge_trade_CE_symbol} \n"
        f"Hedge PE Trade {hedge_trade_PE_symbol} \n"
    )
    logger.info(message)

    discord_bot(message, strategy_obj.StrategyName)

def signal_to_log_firebase(orders_to_place,signal):
    for order in orders_to_place:
            if order.get("order_mode") == "MO":
                main_trade_id = order.get("trade_id")
                main_trade_id_prefix = main_trade_id.split("_")[0]
    
    if signal == "ShortSignal" or signal == "LongSignal":
        signals_to_log = {
                "TradeId": main_trade_id,
                "Signal": signal,
                "EntryTime": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Orders" : orders_to_place,
                "StrategyInfo": {
                    "trade_id": main_trade_id_prefix,
                    "signal": signal,
                    "hedge_multiplier": strategy_obj.ExtraInformation.HedgeDistance,
                    "ema_period": strategy_obj.EntryParams.EMAPeriod,
                    "heikin_ashi_period": strategy_obj.EntryParams.HeikinAshiMAPeriod,
                    "super_trend_multiplier": strategy_obj.EntryParams.SupertrendMultiplier,
                    "super_trend_period": strategy_obj.EntryParams.SupertrendPeriod,
                }
            }
        update_signal_firebase(strategy_obj.StrategyName, signals_to_log, next_trade_prefix)

def place_orders(strike_prc, signal):
    global avg_sl_points, lot_size
    strategy_name = strategy_obj.StrategyName
    order_type = strategy_obj.GeneralParams.OrderType
    product_type = strategy_obj.GeneralParams.ProductType

    base_symbol = strategy_obj.Instruments[0]
    expiry_date = instrument_obj.get_expiry_by_criteria(
        base_symbol, strike_prc, "CE", "current_week"
    )

    orders_to_place = []

    main_CE_exchange_token = instrument_obj.get_exchange_token_by_criteria(
        base_symbol, strike_prc, "CE", expiry_date
    )
    main_PE_exchange_token = instrument_obj.get_exchange_token_by_criteria(
        base_symbol, strike_prc, "PE", expiry_date
    )

    if "Short" in signal:
        hedge_ce_strike_prc = strike_prc + strategy_obj.ExtraInformation.HedgeDistance
        hedge_pe_strike_prc = strike_prc - strategy_obj.ExtraInformation.HedgeDistance

        hedge_CE_exchange_token = instrument_obj.get_exchange_token_by_criteria(
            base_symbol, hedge_ce_strike_prc, "CE", expiry_date
        )
        hedge_PE_exchange_token = instrument_obj.get_exchange_token_by_criteria(
            base_symbol, hedge_pe_strike_prc, "PE", expiry_date
        )

        if signal == "ShortSignal":
            main_order_mode = "MainEntry"
            hedge_order_mode = "HedgeEntry"
        else:
            main_order_mode = "MainExit"
            hedge_order_mode = "HedgeExit"

        main_orders = [
        {"exchange_token": main_CE_exchange_token, "order_mode": main_order_mode},
        {"exchange_token": main_PE_exchange_token, "order_mode": main_order_mode},
    ]

        hedge_orders = [
            {"exchange_token": hedge_CE_exchange_token, "order_mode": hedge_order_mode},
            {"exchange_token": hedge_PE_exchange_token, "order_mode": hedge_order_mode},
        ]
        hedge_transaction_type = "BUY" if "ShortSignal" in signal else "SELL"
        main_transaction_type = "SELL" if "ShortSignal" in signal else "BUY"

        if signal == "ShortCoverSignal":
            orders_to_place.extend(main_orders)  # Add main orders first
            orders_to_place.extend(hedge_orders)  # Then add hedge orders
        else:
            orders_to_place.extend(
                hedge_orders
            )  # For other short signals, hedge orders first
            orders_to_place.extend(main_orders)  # Then main orders

    else:  # Long Orders
        main_transaction_type = "BUY" if "LongSignal" in signal else "SELL"
        hedge_transaction_type = None  # No hedge orders for long positions
        orders_to_place.extend(main_orders)

    trade_type = (
        "entry" if signal == "ShortSignal" or signal == "LongSignal" else "exit"
    )
    
    trade_id = strategy_obj.NextTradeId

    for order in orders_to_place:
        transaction_type = (
            hedge_transaction_type
            if "Hedge" in order["order_mode"]
            else main_transaction_type
        )
        order.update(
            {
                "signal": "Short" if "Short" in signal else "Long",
                "strategy": strategy_name,
                "base_symbol": base_symbol,
                "transaction_type": transaction_type,
                "order_type": order_type,
                "product_type": product_type,
                "trade_id": trade_id,
            }
        )

    
    orders_to_place = assign_trade_id(orders_to_place)
    update_qty_user_firebase(strategy_name, avg_sl_points, lot_size)
    signal_to_log_firebase(orders_to_place,signal)
    

    message_for_orders(
        trade_type,
        signal,
        main_CE_exchange_token,
        main_PE_exchange_token,
        hedge_CE_exchange_token,
        hedge_PE_exchange_token,
    )
    logger.info(orders_to_place)
    place_order_strategy_users(strategy_name, orders_to_place)