from pydantic import BaseModel, Field, validator
from typing import List, Dict, Union, Optional
from datetime import time
import os,sys
import json

DIR = os.getcwd()
sys.path.append(DIR)

from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import fetch_collection_data_firebase

# Sub-models for various parameter types
class EntryParams(BaseModel):
    EntryTime: time
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
        ltp = self.get_single_ltp(token)
        base_strike = self.round_strike_prc(ltp, base_symbol)
        multiplier = self.get_strike_step(base_symbol)
        if strike_prc_multiplier:
            adjustment = multiplier * (strike_prc_multiplier if prediction == 'Bearish' else -strike_prc_multiplier)
            return base_strike + adjustment
        else:
            return base_strike
        
    def get_hedge_strikeprc(self,base_symbol,token, prediction, hedge_multiplier): 
        ltp = self.get_single_ltp(token)
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