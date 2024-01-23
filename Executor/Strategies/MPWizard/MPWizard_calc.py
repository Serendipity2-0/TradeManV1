import os
import sys
import datetime as dt
from dotenv import load_dotenv
from typing import Optional

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, '.env')
load_dotenv(ENV_PATH)

from Executor.Strategies.StrategiesUtil import StrategyBase,get_previous_dates
from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import fetch_collection_data_firebase,update_fields_firebase
from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import fetch_primary_accounts_from_firebase
from Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter import create_kite_obj

# import MarketUtils.general_calc as general_calc
# import Brokers.BrokerUtils.Broker as Broker
# import Brokers.Zerodha.kite_utils as kite_utils
# # import Strategies.StrategyBase as StrategyBase
# import MarketUtils.Calculations.qty_calc as qty_calc

# _,STRATEGY_PATH = general_calc.get_strategy_json('MPWizard')
strategy_obj = StrategyBase.load_from_db('MPWizard')
zerodha_primary = os.getenv('ZERODHA_PRIMARY_ACCOUNT')

def get_price_reference_firebase(strategy_name, instrument):
    # Here we are using a mock strategy JSON for demonstration purposes
    strategy_data = fetch_collection_data_firebase('strategies')
    today_index = dt.datetime.today().weekday()
    key = f"{instrument}OptRef"
    price_ref_values = strategy_data[strategy_name]['ExtraInformation'].get(key, [])
    if price_ref_values:
        return price_ref_values[today_index]
    else:
        return 0

def calculate_average_range(historical_data):
    """
    Calculate the average range (High - Low) from the historical data.
    """
    total_range = 0
    for day_data in historical_data:
        total_range += day_data['high'] - day_data['low']
    return total_range / len(historical_data)

def get_average_range_and_update_json(days):
    """
    Calculate and update the average range in the JSON file.
    """
    #fetch primary account
    primary_account_session_id = fetch_primary_accounts_from_firebase(zerodha_primary)
    kite = create_kite_obj(api_key=primary_account_session_id['Broker']['ApiKey'], access_token=primary_account_session_id['Broker']['SessionId'])

    previous_dates = get_previous_dates(days)
    indices_tokens = strategy_obj.GeneralParams.IndicesTokens
    instruments = strategy_obj.Instruments
    
    for instrument in instruments:
        # Fetch the instrument token
        instrument_token = indices_tokens.get(instrument, None)
        if instrument_token is None:
            print(f"Instrument token for {instrument} not found.")
            continue
        
        # Fetch historical data for the instrument
        historical_data = kite.historical_data(instrument_token, from_date = previous_dates[-1], to_date=previous_dates[0], interval = 'day')
        
        # Calculate the average range
        average_range = calculate_average_range(historical_data)
        # #I want to update the average range inside InstrumentToday for the instrument in the entry_params
        field_path = f'EntryParams/InstrumentToday/{instrument}'
        update_fields_firebase('strategies', strategy_obj.StrategyName, {'ATR5D':round(average_range, 2)}, field_path)

get_average_range_and_update_json(5)

def determine_ib_level(ratio):
    """
    Determine the IB Level based on the given ratio.
    """
    if ratio <= 0.3333:
        return "Small"
    elif 0.3333 < ratio <= 0.6666:
        return "Medium"
    else:
        return "Big"

def get_price_ref_for_today(instrument: str, extra_info) -> Optional[int]:
    # Get the current day of the week (0=Monday, 6=Sunday)
    day_of_week = dt.datetime.now().weekday()

    # Check if PriceRef for the instrument is available
    if extra_info.PriceRef and instrument in extra_info.PriceRef:
        price_ref_list = extra_info.PriceRef[instrument]
        # Ensure there are 7 values, one for each day of the week
        if len(price_ref_list) == 7:
            return price_ref_list[day_of_week]
        else:
            print(f"Invalid number of price references for {instrument}. Expected 7, got {len(price_ref_list)}.")
            return None
    else:
        print(f"No price reference found for instrument {instrument}.")
        return None

def get_high_low_range_and_update_json():
    """
    Calculate and update the high-low range in the JSON file.
    """
    # today = dt.date.today().strftime('%Y-%m-%d')
    primary_account_session_id = fetch_primary_accounts_from_firebase(zerodha_primary)
    kite = create_kite_obj(api_key=primary_account_session_id['Broker']['ApiKey'], access_token=primary_account_session_id['Broker']['SessionId'])
    today = dt.datetime.now().date()
    start_time = dt.datetime.combine(today, dt.time(9, 15))
    end_time = dt.datetime.combine(today, dt.time(10, 30))
    indices_tokens = strategy_obj.GeneralParams.IndicesTokens
    instruments = strategy_obj.Instruments
    for instrument in instruments:

        # Fetch the instrument token
        instrument_token = indices_tokens.get(instrument, None)
        if instrument_token is None:
            print(f"Instrument token for {indices_tokens} not found.")
            continue

        data = kite.historical_data(instrument_token, start_time, end_time, 'hour')
        if data:
            high, low = data[0]['high'], data[0]['low']
            range_ = high - low
            entry_params = strategy_obj.EntryParams
            price_ref = get_price_ref_for_today(instrument, strategy_obj.ExtraInformation)
            average_atr = entry_params.InstrumentToday[instrument]['ATR5D']
            instrument_token = entry_params.InstrumentToday[instrument]['Token']
            entry_params = {instrument: {'TriggerPoints': {'IBHigh': high, 'IBLow': low}, 'IBValue': range_, 'IBLevel': determine_ib_level(range_ / average_atr), 'Token': instrument_token, 'PriceRef': price_ref, 'ATR5D': average_atr}}
            field_location = f'EntryParams/InstrumentToday'
            update_fields_firebase('strategies', strategy_obj.StrategyName, entry_params, field_location)


get_high_low_range_and_update_json()

def calculate_option_type(ib_level,cross_type,trade_view):
    if ib_level == 'Big':
        return 'PE' if cross_type == 'UpCross' else 'CE'
    elif ib_level == 'Small':
        return 'PE' if cross_type == 'DownCross' else 'CE'
    elif ib_level == 'Medium':
        return 'PE' if trade_view == 'Bearish' else 'CE'
    else:
        print(f"Unknown IB Level: {ib_level}")
    return None