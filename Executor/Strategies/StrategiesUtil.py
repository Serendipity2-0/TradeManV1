from pydantic import BaseModel, Field, validator
from typing import List, Dict, Union, Optional
from datetime import time

# Helper function to validate time format
def validate_time_format(time_string: str) -> time:
    # Implement logic to parse and validate time format
    pass

# Sub-models for various parameter types
class EntryParams(BaseModel):
    EMAPeriod: Optional[int]
    EntryTime: str
    HeikinAshiMAPeriod: Optional[int]
    SupertrendMultiplier: Optional[int]
    SupertrendPeriod: Optional[int]
    TSLStepSize: Optional[float]
    # Additional fields for other strategies
    # ...

class ExitParams(BaseModel):
    LastBuyTime: Optional[str]
    SLType: str
    SquareOffTime: Optional[str]
    # Additional fields for other strategies
    # ...

class ExtraInformation(BaseModel):
    HedgeDistance: Optional[int]
    Interval: Optional[str]
    # Additional fields for other strategies
    # ...

class GeneralParams(BaseModel):
    ExpiryType: Union[str, List[str]]
    NiftyToken: Optional[str]
    OrderType: str
    ProductType: str
    Segment: str
    TimeFrame: str
    TradeView: str
    # Additional fields for other strategies
    # ...

class SignalEntry(BaseModel):
    ShortCoverSignal: Optional[dict]
    ShortSignal: Optional[dict]
    # Additional fields for other strategies
    # ...

# Main strategy model
class Strategy(BaseModel):
    Description: str
    EntryParams: Optional[EntryParams]
    ExitParams: Optional[ExitParams]
    ExtraInformation: Optional[ExtraInformation]
    GeneralParams: Optional[GeneralParams]
    Instruments: List[str]
    NextTradeId: Optional[str]
    SignalEntry: Optional[SignalEntry]
    StrategyName: str
    TodayOrders: List[str]

# Main collection model
class StrategyBase(BaseModel):
    strategies: Dict[str, Strategy]

    @validator('strategies', pre=True)
    def validate_strategies(cls, value):
        # Custom validation logic for strategies
        return value

#TODO: give strategy name and return strategyobj
    @classmethod
    def load_strategy(cls, strategy_name: str) -> Optional[Strategy]:
        try:
            
            # Parse and extract the specific strategy data
            strategies_collection = cls.parse_obj(data)
            if strategy_name in strategies_collection.strategies:
                return strategies_collection.strategies[strategy_name]
            else:
                return None
        except (FileNotFoundError, IOError, json.JSONDecodeError) as e:
            # Handle file not found, I/O errors, or JSON parsing errors
            print(f"Error reading file: {e}")
            return None

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