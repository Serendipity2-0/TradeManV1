import os
import sys
import datetime as dt
from dotenv import load_dotenv
from typing import Optional

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.NSEStrategies.NSEStrategiesUtil import StrategyBase, get_previous_dates
from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import (
    fetch_collection_data_firebase,
    update_fields_firebase,
)
from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
    fetch_primary_accounts_from_firebase,
    STRATEGY_FB_DB,
)
from Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter import (
    create_kite_obj,
)
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()

strategy_obj = StrategyBase.load_from_db("MPWizard")
zerodha_primary = os.getenv("ZERODHA_PRIMARY_ACCOUNT")


def get_price_reference_firebase(strategy_name, instrument):
    """
    Fetch the price reference for the given strategy and instrument from Firebase.

    Parameters:
    strategy_name (str): The name of the strategy.
    instrument (str): The instrument for which to fetch the price reference.

    Returns:
    int: The price reference value for today, or 0 if not found.
    """
    # Here we are using a mock strategy JSON for demonstration purposes
    strategy_data = fetch_collection_data_firebase(STRATEGY_FB_DB)
    today_index = dt.datetime.today().weekday()
    key = f"{instrument}OptRef"
    price_ref_values = strategy_data[strategy_name]["ExtraInformation"].get(key, [])
    if price_ref_values:
        return price_ref_values[today_index]
    else:
        return 0


def calculate_average_range(historical_data):
    """
    Calculate the average range (High - Low) from the historical data.

    Parameters:
    historical_data (list): A list of historical data dictionaries containing 'high' and 'low' prices.

    Returns:
    float: The average range calculated from the historical data.
    """
    total_range = 0
    for day_data in historical_data:
        total_range += day_data["high"] - day_data["low"]
    return total_range / len(historical_data)


def get_average_range_and_update_json(days):
    """
    Calculate and update the average range in the JSON file for the specified number of days.

    Parameters:
    days (int): The number of days to consider for calculating the average range.
    """
    # fetch primary account
    primary_account_session_id = fetch_primary_accounts_from_firebase(zerodha_primary)
    kite = create_kite_obj(
        api_key=primary_account_session_id["Broker"]["ApiKey"],
        access_token=primary_account_session_id["Broker"]["SessionId"],
    )

    previous_dates = get_previous_dates(days)
    indices_tokens = strategy_obj.GeneralParams.IndicesTokens
    instruments = strategy_obj.Instruments

    for instrument in instruments:
        # Fetch the instrument token
        instrument_token = indices_tokens.get(instrument, None)
        if instrument_token is None:
            logger.error(f"Instrument token for {instrument} not found.")
            continue

        # Fetch historical data for the instrument
        historical_data = kite.historical_data(
            instrument_token,
            from_date=previous_dates[-1],
            to_date=previous_dates[0],
            interval="day",
        )

        # Calculate the average range
        average_range = calculate_average_range(historical_data)
        # #I want to update the average range inside InstrumentToday for the instrument in the entry_params
        field_path = f"EntryParams/InstrumentToday/{instrument}"
        update_fields_firebase(
            STRATEGY_FB_DB,
            strategy_obj.StrategyName,
            {"ATR5D": round(average_range, 2)},
            field_path,
        )


def determine_ib_level(ratio):
    """
    Determine the IB Level based on the given ratio.

    Parameters:
    ratio (float): The ratio of the current range to the average range.

    Returns:
    str: The IB Level, which can be "Small", "Medium", or "Big".
    """
    if ratio <= 0.3333:
        return "Small"
    elif 0.3333 < ratio <= 0.6666:
        return "Medium"
    else:
        return "Big"


def get_price_ref_for_today(instrument: str, extra_info=None) -> Optional[int]:
    """
    Get the price reference for today for the specified instrument.

    Parameters:
    instrument (str): The instrument for which to fetch the price reference.
    extra_info (Optional[dict]): Optional extra information dictionary. If not provided, the strategy's extra information is used.

    Returns:
    Optional[int]: The price reference for today, or None if not found.
    """
    # Get the current day of the week (0=Monday, 6=Sunday)
    if extra_info is None:
        extra_info = strategy_obj.ExtraInformation

    day_of_week = dt.datetime.now().weekday()

    # Check if PriceRef for the instrument is available
    if extra_info.PriceRef and instrument in extra_info.PriceRef:
        price_ref_list = extra_info.PriceRef[instrument]
        # Ensure there are 7 values, one for each day of the week
        if len(price_ref_list) == 7:
            return price_ref_list[day_of_week]
        else:
            logger.error(
                f"Invalid number of price references for {instrument}. Expected 7, got {len(price_ref_list)}."
            )
            return None
    else:
        logger.error(f"No price reference found for instrument {instrument}.")
        return None


def get_high_low_range_and_update_json():
    """
    Calculate and update the high-low range in the JSON file for the current day.
    """
    # today = dt.date.today().strftime('%Y-%m-%d')
    primary_account_session_id = fetch_primary_accounts_from_firebase(zerodha_primary)
    kite = create_kite_obj(
        api_key=primary_account_session_id["Broker"]["ApiKey"],
        access_token=primary_account_session_id["Broker"]["SessionId"],
    )
    today = dt.datetime.now().date()
    start_time = dt.datetime.combine(today, dt.time(9, 15))
    end_time = dt.datetime.combine(today, dt.time(10, 30))
    indices_tokens = strategy_obj.GeneralParams.IndicesTokens
    instruments = strategy_obj.Instruments
    for instrument in instruments:

        # Fetch the instrument token
        instrument_token = indices_tokens.get(instrument, None)
        if instrument_token is None:
            logger.error(f"Instrument token for {indices_tokens} not found.")
            continue

        data = kite.historical_data(instrument_token, start_time, end_time, "hour")
        if data:
            high, low = data[0]["high"], data[0]["low"]
            range_ = high - low
            entry_params = strategy_obj.EntryParams
            price_ref = get_price_ref_for_today(
                instrument, strategy_obj.ExtraInformation
            )
            average_atr = entry_params.InstrumentToday[instrument]["ATR5D"]
            instrument_token = entry_params.InstrumentToday[instrument]["Token"]
            entry_params = {
                instrument: {
                    "TriggerPoints": {"IBHigh": high, "IBLow": low},
                    "IBValue": range_,
                    "IBLevel": determine_ib_level(range_ / average_atr),
                    "Token": instrument_token,
                    "PriceRef": price_ref,
                    "ATR5D": average_atr,
                }
            }
            field_location = "EntryParams/InstrumentToday"
            update_fields_firebase(
                STRATEGY_FB_DB, strategy_obj.StrategyName, entry_params, field_location
            )


def calculate_option_type(ib_level, cross_type, trade_view):
    """
    Calculate the option type based on IB Level, cross type, and trade view.

    Parameters:
    ib_level (str): The IB Level, which can be "Small", "Medium", or "Big".
    cross_type (str): The cross type, which can be "UpCross" or "DownCross".
    trade_view (str): The trade view, which can be "Bullish" or "Bearish".

    Returns:
    str: The option type, which can be "CE" or "PE".
    """
    if ib_level == "Big":
        return "PE" if cross_type == "UpCross" else "CE"
    elif ib_level == "Small":
        return "PE" if cross_type == "DownCross" else "CE"
    elif ib_level == "Medium":
        return "PE" if trade_view == "Bearish" else "CE"
    else:
        logger.error(f"Unknown IB Level: {ib_level}")
    return None
