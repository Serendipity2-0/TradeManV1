import os
import sys
import datetime as dt
from time import sleep
from dotenv import load_dotenv
import random

from pprint import pprint

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

from Executor.Strategies.StrategiesUtil import StrategyBase
from Executor.Strategies.StrategiesUtil import update_qty_user_firebase, assign_trade_id, update_signal_firebase, place_order_strategy_users

import Executor.ExecutorUtils.ExeUtils as ExeUtils
import Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils as InstrumentCenterUtils
from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import discord_bot

ENV_PATH = os.path.join(DIR_PATH, 'trademan.env')
load_dotenv(ENV_PATH)

class Mahadev(StrategyBase):
    def get_general_params(self):
        return self.GeneralParams
    
    def get_entry_params(self):
        return self.EntryParams
    
    def get_exit_params(self):
        return self.ExitParams
    
    def get_raw_field(self, field_name: str):
        return super().get_raw_field(field_name)
    
strategy_obj = Mahadev.load_from_db('Mahadev')
instrument_obj = InstrumentCenterUtils.Instrument()

start_hour, start_minute, start_second = map(int, strategy_obj.get_entry_params().EntryTime.split(':'))

def namaha():
    hedge_transaction_type = strategy_obj.get_raw_field("GeneralParams").get('NamahaHedgeTransactionType')
    main_transaction_type = strategy_obj.get_raw_field("GeneralParams").get('NamahaMainTransactionType')

    # Extract strategy parameters
    base_symbol, today_expiry_token = strategy_obj.determine_expiry_index()
    strategy_name = strategy_obj.StrategyName
    next_trade_prefix = strategy_obj.get_raw_field("NamahaNextTradeId")
    prediction = strategy_obj.get_general_params().TradeView
    order_type = strategy_obj.get_general_params().OrderType
    product_type = strategy_obj.get_general_params().ProductType

    strike_prc_multiplier = strategy_obj.get_strike_multiplier(base_symbol)
    hedge_multiplier = strategy_obj.get_hedge_multiplier(base_symbol)
    stoploss_mutiplier = strategy_obj.get_stoploss_multiplier(base_symbol)
    desired_start_time_str = strategy_obj.get_entry_params().EntryTime

    start_hour, start_minute, start_second = map(int, desired_start_time_str.split(':'))

    main_strikeprc = strategy_obj.calculate_current_atm_strike_prc(base_symbol,today_expiry_token, prediction, strike_prc_multiplier)
    hedge_strikeprc = strategy_obj.get_hedge_strikeprc(base_symbol, today_expiry_token, prediction, hedge_multiplier)
    main_option_type = strategy_obj.get_option_type(prediction, "OS")
    hedge_option_type = strategy_obj.get_hedge_option_type(prediction)

    today_expiry = instrument_obj.get_expiry_by_criteria(base_symbol,main_strikeprc,main_option_type, "current_week")
    hedge_exchange_token = instrument_obj.get_exchange_token_by_criteria(base_symbol,hedge_strikeprc,hedge_option_type, today_expiry)
    main_exchange_token = instrument_obj.get_exchange_token_by_criteria(base_symbol,main_strikeprc, main_option_type,today_expiry)

    ltp = InstrumentCenterUtils.get_single_ltp(exchange_token = main_exchange_token)
    lot_size = instrument_obj.get_lot_size_by_exchange_token(main_exchange_token)

    update_qty_user_firebase(strategy_name,ltp,lot_size)
    message_for_orders("Live",prediction,main_exchange_token,hedge_exchange_token, strategy_name)

    orders_to_place = [
        {  
            "strategy": strategy_name,
            "signal":"Short",
            "base_symbol": base_symbol,
            "exchange_token" : hedge_exchange_token,     
            "transaction_type": hedge_transaction_type,  
            "order_type" : order_type, 
            "product_type" : product_type,
            "order_mode" : "HedgeEntry",
            "trade_id" : next_trade_prefix 
        },
        {
            "strategy": strategy_name,
            "signal":"Short",
            "base_symbol": base_symbol,
            "exchange_token" : main_exchange_token,     
            "transaction_type": main_transaction_type, 
            "order_type" : order_type, 
            "product_type" : product_type,
            "order_mode" : "Main",
            "trade_id" : next_trade_prefix
        },
        {
            "strategy": strategy_name,
            "signal":"Short",
            "base_symbol": base_symbol,
            "exchange_token" : main_exchange_token,     
            "transaction_type": hedge_transaction_type, 
            "order_type" : "Stoploss",
            "product_type" : product_type,
            "stoploss_mutiplier": stoploss_mutiplier,
            "order_mode" : "SL",
            "trade_id" : next_trade_prefix
        }
        ]

    orders_to_place = assign_trade_id(orders_to_place)
    pprint(orders_to_place)
    return orders_to_place

namaha()

def om():
    next_trade_prefix = strategy_obj.get_raw_field("OmNextTradeId")
    result = random.choice(['Heads', 'Tails'])
    base_symbol,_ = strategy_obj.determine_expiry_index()
    strike_prc = strategy_obj.calculate_current_atm_strike_prc(base_symbol)
    option_type = 'CE' if result == 'Heads' else 'PE'
    today_expiry = instrument_obj.get_expiry_by_criteria(base_symbol,strike_prc,option_type, "current_week")
    exchange_token = instrument_obj.get_exchange_token_by_criteria(base_symbol,strike_prc, option_type,today_expiry)
    message_for_orders("Live",result,exchange_token,exchange_token, strategy_obj.StrategyName)

    orders_to_place = [
        {  
        "strategy": strategy_obj.StrategyName,
        "signal":"Long",
        "base_symbol": base_symbol,
        "exchange_token" : exchange_token,     
        "transaction_type": strategy_obj.get_raw_field("GeneralParams").get('OmMainTransactionType'),  
        "order_type" : strategy_obj.get_general_params().OrderType, 
        "product_type" : strategy_obj.get_general_params().ProductType,
        "order_mode" : "Main",
        "trade_id" : next_trade_prefix
        }]
    orders_to_place = assign_trade_id(orders_to_place)
    pprint(orders_to_place)
    return orders_to_place

om()


def message_for_orders(trade_type,prediction,main_trade_symbol,hedge_trade_symbol,strategy_name):
    #TODO: add noftication for the orders 
    message = ( f"{trade_type} Trade for {strategy_name}\n"
            f"Direction : {prediction}\n"
            f"Main Trade : {main_trade_symbol}\n"
            f"Hedge Trade {hedge_trade_symbol} \n")    
    print(message)
    discord_bot(message, strategy_name)
    

def main():
    now = dt.datetime.now()

    if now.date() in ExeUtils.holidays:
        print("Skipping execution as today is a holiday.")
        return

    if now.time() < dt.time(9, 0):
        print("Time is before 9:00 AM, Waiting to execute.")
    else:
        wait_time = dt.datetime(now.year, now.month, now.day, start_hour, start_minute) - now
        
        if wait_time.total_seconds() > 0:
            print(f"Waiting for {wait_time} before starting the bot")
            sleep(wait_time.total_seconds())
        
        om_next_trade_prefix = strategy_obj.get_raw_field("OmNextTradeId")
        namaha_next_trade_prefix = strategy_obj.get_raw_field("NamahaNextTradeId")

        om_signals_to_log = {
                        "TradeId" : om_next_trade_prefix,
                        "Signal" : "Short",
                        "EntryTime" : dt.datetime.now().strftime("%H:%M"),
                        "Status" : "Open"}
        namaha_signals_to_log = {
                        "TradeId" : namaha_next_trade_prefix,
                        "Signal" : "Short",
                        "EntryTime" : dt.datetime.now().strftime("%H:%M"),
                        "Status" : "Open"
                        }

        update_signal_firebase(strategy_obj.StrategyName,om_signals_to_log)
        update_signal_firebase(strategy_obj.StrategyName,namaha_signals_to_log)

        # message_for_orders("Live",prediction,main_trade_symbol,hedge_trade_symbol)
        om_orders = om()
        namaha_orders = namaha()
        place_order_strategy_users('OM',om_orders)
        place_order_strategy_users('Namaha',namaha_orders)




if __name__ == "__main__":
    main()