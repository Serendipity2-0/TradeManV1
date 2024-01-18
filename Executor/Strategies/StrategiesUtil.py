from pydantic import BaseModel, Field, validator
from typing import List, Dict, Union, Optional
from datetime import time
import os,sys
import json
import datetime as dt
import pandas as pd
from dotenv import load_dotenv

DIR = os.getcwd()
sys.path.append(DIR)
ENV_PATH = os.path.join(DIR, '.env')
load_dotenv(ENV_PATH)
fno_info_path = os.getenv('FNO_INFO_PATH')

from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import update_fields_firebase
from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import fetch_collection_data_firebase
from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import get_single_ltp
from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import fetch_active_users_from_firebase
from Executor.ExecutorUtils.OrderCenter.OrderCenterUtils import calculate_qty_for_strategies

# Sub-models for various parameter types
class EntryParams(BaseModel):
    EntryTime: str
    HedgeMultiplier: int
    InstrumentToday: str
    SLMultipler: int
    StrikeMultiplier: int

class ExitParams(BaseModel):
    SLType: str
    SqroffTime: time

class ExtraInformation(BaseModel):
    QtyCalc: str

class GeneralParams(BaseModel):
    ExpiryType: str
    HedgeTransactionType: str
    MainTransactionType: str
    OrderType: str
    ProductType: str
    StrategyType: str
    TimeFrame: str
    TradeView: str

class TodayOrder(BaseModel):
    EntryPrc: float
    EntryTime: time
    ExitPrc: float
    ExitTime: time
    MarginUsed: float
    MaxLoss: float
    PeakProfit: float
    Signal: str
    StartegyStats: Dict[str, str]
    Trade_id: str

class StrategyBase(BaseModel):
    Description: str
    EntryParams: EntryParams
    ExitParams: ExitParams
    ExtraInformation: ExtraInformation
    GeneralParams: GeneralParams
    Instruments: List[str]
    NextTradeId: str
    StrategyName: str
    StrategyPrefix: str
    TodayOrders: Dict[str, TodayOrder]

    @classmethod
    def load_from_db(cls, strategy_name: str):
        data = fetch_collection_data_firebase('strategies', document=strategy_name)
        if data is None:
            raise ValueError(f"No data found for strategy {strategy_name}")
        return cls.parse_obj(data)

###########################################################################
    def get_option_type(self,prediction,strategy_option_mode):
        if strategy_option_mode == "OS":
            return 'CE' if prediction == 'Bearish' else 'PE'
        elif strategy_option_mode == "OB":
            return 'CE' if prediction == 'Bullish' else 'PE'
        else:
            print("Invalid option mode")
    
    def get_hedge_option_type(self,prediction):
        if prediction == 'Bearish':
            return 'CE' 
        elif prediction == 'Bullish':
            return 'PE'
        else:
            print("Invalid option mode")
    
    def get_transaction_type(self,prediction):
        if prediction == 'Bearish':
            return 'SELL' 
        elif prediction == 'Bullish':
            return 'BUY'
        else:
            print("Invalid option mode")
    
   
    def get_token_from_info(self,base_symbol):
        fno_info_df = pd.read_csv(fno_info_path)
        token = fno_info_df.loc[fno_info_df['base_symbol'] == base_symbol, 'token'].values
        if len(token) == 0:
            return f"{base_symbol} not found"
        return token[0]
    
    def determine_expiry_index(self):
        day = dt.datetime.today().weekday()
        if day == 0:  # Monday
            return "MIDCPNIFTY","288009"
        elif day == 1:  # Tuesday
            return "FINNIFTY","257801"
        elif day == 2:  # Wednesday
            return "BANKNIFTY","260105"
        elif day == 3:  # Thursday
            return "NIFTY","256265"
        elif day == 4:  # Friday
            return "SENSEX","265"
        else:
            return "No expiry today"

    def round_strike_prc(self,ltp,base_symbo): #TODO: Add support for other base symbols using a csv list
        strike_step = self.get_strike_step(base_symbo)
        return round(ltp / strike_step) * strike_step
    
    def get_strike_step(self, base_symbol):
        strike_step_df = pd.read_csv(fno_info_path)
        strike_step = strike_step_df.loc[strike_step_df['base_symbol'] == base_symbol, 'strike_step_size'].values[0]
        return strike_step

    def calculate_current_atm_strike_prc(self,base_symbol, token = None, prediction=None, strike_prc_multiplier=None):
        if token is None:
            token = int(self.get_token_from_info(base_symbol))
        ltp = get_single_ltp(token)
        base_strike = self.round_strike_prc(ltp, base_symbol)
        multiplier = self.get_strike_step(base_symbol)
        if strike_prc_multiplier:
            adjustment = multiplier * (strike_prc_multiplier if prediction == 'Bearish' else -strike_prc_multiplier)
            return base_strike + adjustment
        else:
            return base_strike
        
    def get_hedge_strikeprc(self,base_symbol,token, prediction, hedge_multiplier): 
        ltp = get_single_ltp(token)
        strike_prc = self.round_strike_prc(ltp, base_symbol)
        strike_prc_multiplier = self.get_strike_step(base_symbol)
        bear_strikeprc = strike_prc + (hedge_multiplier * strike_prc_multiplier)
        bull_strikeprc = strike_prc - (hedge_multiplier * strike_prc_multiplier)
        hedge_strikeprc = bear_strikeprc if prediction == 'Bearish' else bull_strikeprc
        return hedge_strikeprc
    
    def get_square_off_transaction(self,prediction):
        if prediction == 'Bearish':
            return 'BUY'
        elif prediction == 'Bullish':
            return'SELL'
        else:
            print("Invalid prediction")

    def get_strike_multiplier(self,base_symbol):
        fno_info_df = pd.read_csv(fno_info_path)
        strike_multiplier = fno_info_df.loc[fno_info_df['base_symbol'] == base_symbol, 'strike_multiplier'].values
        if len(strike_multiplier) == 0:
            return f"{base_symbol} not found"
        return strike_multiplier[0]
    
    def get_hedge_multiplier(self,base_symbol):
        fno_info_df = pd.read_csv(fno_info_path)
        hedge_multiplier = fno_info_df.loc[fno_info_df['base_symbol'] == base_symbol, 'hedge_multiplier'].values
        if len(hedge_multiplier) == 0:
            return f"{base_symbol} not found"
        return hedge_multiplier[0]
    
    def get_stoploss_multiplier(self,base_symbol):
        fno_info_df = pd.read_csv(fno_info_path)
        stoploss_multiplier = fno_info_df.loc[fno_info_df['base_symbol'] == base_symbol, 'stoploss_multiplier'].values
        if len(stoploss_multiplier) == 0:
            return f"{base_symbol} not found"
        return stoploss_multiplier[0]
    
def get_previous_dates(num_dates):
    dates = []
    current_date = dt.date.today()

    while len(dates) < num_dates:
        current_date -= dt.timedelta(days=1)

        if current_date.weekday() >= 5 or current_date in holidays:
            continue

        dates.append(current_date.strftime("%Y-%m-%d"))

    return dates

def fetch_users_for_strategy(strategy_name):
    active_users = fetch_active_users_from_firebase()
    strategy_users = []
    for user in active_users:
        if strategy_name in user['Strategies']:
            strategy_users.append(user)
    return strategy_users

def fetch_freecash_firebase(strategy_name):
    accounts = fetch_users_for_strategy(strategy_name)  # Assuming there is a function to fetch accounts from Firebase
    freecash_dict = {}
    for account in accounts:
        freecash_dict[account['Tr_No']] = account['Accounts']['FreeCash']
    return freecash_dict

def fetch_risk_per_trade_firebase(strategy_name):
    users = fetch_users_for_strategy(strategy_name)
    risk_per_trade = {}
    for user in users:
        risk_per_trade[user['Tr_No']] = user['Strategies'][strategy_name]['RiskPerTrade']
    return risk_per_trade

def update_qty_user_firebase(strategy_name,avg_sl_points,lot_size):
    strategy_users = fetch_users_for_strategy(strategy_name)
    free_cash_dict = fetch_freecash_firebase(strategy_name)
    risk_per_trade = fetch_risk_per_trade_firebase(strategy_name)
    for user in strategy_users:
        if user['Tr_No'] in risk_per_trade:
            risk = risk_per_trade[user['Tr_No']]
        if user['Tr_No'] in free_cash_dict:
            capital = free_cash_dict[user['Tr_No']]        
        qty = calculate_qty_for_strategies(capital, risk, avg_sl_points, lot_size)
        user['Strategies'][strategy_name]['Qty'] = qty
        
        update_fields_firebase('new_clients', user['Tr_No'], {'Qty': qty}, f'Strategies/{strategy_name}')

# method to take        
def assign_trade_id(orders_to_place):
    for order in orders_to_place:
        # Determine the last part of the trade_id based on order_mode
        if order['order_mode'] in ['Main', 'HedgeEntry']:
            trade_id_suffix = 'entry'
        elif order['order_mode'] == 'SL':
            trade_id_suffix = 'exit'
        else:
            trade_id_suffix = 'unknown'

        # Reconstruct the trade_id
        trade_id = f"{order['trade_id']}_{order['signal'].lower()}_{order['order_mode'].lower()}_{trade_id_suffix}"

        # Update the trade_id in the order
        order['trade_id'] = trade_id

    return orders_to_place

        
        
    
    
        
