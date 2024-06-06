import pytest
import pandas as pd
import sqlite3
import os, sys
import json
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from dotenv import load_dotenv


# Add the necessary path
DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

# Load environment variables
ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

# Import the functions to test
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

# Import the functions to test
from Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils import (
    Instrument,
    get_single_ltp,
    get_single_quote,
)

# Set up the logger
logger = LoggerSetup()


# Fixture to load the instrument dataframe from the SQLite database
@pytest.fixture
def mock_instrument_dataframe():
    db_path = "D:/TradeManV1/Data/instrument.db"
    conn = sqlite3.connect(db_path)
    query = "SELECT * FROM instrument_master"  # Adjust this query based on your table structure
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


# Mocking get_db_connection and read_sql_query from exesql_adapter
@pytest.fixture(autouse=True)
def mock_db_functions(mocker, mock_instrument_dataframe):
    mocker.patch(
        "Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter.get_db_connection",
        return_value=MagicMock(),
    )
    mocker.patch("pandas.read_sql_query", return_value=mock_instrument_dataframe)


# Mock logger
@pytest.fixture(autouse=True)
def mock_logger(mocker):
    mocker.patch(
        "Executor.ExecutorUtils.LoggingCenter.logger_utils.LoggerSetup",
        return_value=MagicMock(),
    )


# Mock KiteConnect
@pytest.fixture
def mock_kite_connect(mocker):
    kite_mock = MagicMock()
    kite_mock.ltp.return_value = {"2001": {"last_price": 100}}
    kite_mock.quote.return_value = {"2001": {"last_price": 100}}
    mocker.patch("kiteconnect.KiteConnect", return_value=kite_mock)
    return kite_mock


# Mock Firebase fetch function
@pytest.fixture(autouse=True)
def mock_firebase_fetch(mocker):
    mock_data = {"Broker": {"ApiKey": "fake_api_key", "SessionId": "fake_session_id"}}
    mocker.patch(
        "Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils.fetch_primary_accounts_from_firebase",
        return_value=mock_data,
    )


# Load JSON test data
@pytest.fixture
def load_json_data():
    with open("D:/TradeManV1/UnitTests/Instrument_TestData.json") as f:
        data = json.load(f)
    return data


# Tests for the Instrument class
def test_get_expiry_by_criteria_current_week(mock_instrument_dataframe):
    inst = Instrument()
    inst._dataframe = mock_instrument_dataframe
    expiry = inst.get_expiry_by_criteria("NIFTY", 23000, "CE", "current_week")
    assert expiry is not None


def test_get_expiry_by_criteria_next_week(mock_instrument_dataframe):
    inst = Instrument()
    inst._dataframe = mock_instrument_dataframe
    expiry = inst.get_expiry_by_criteria("NIFTY", 23000, "CE", "next_week")
    assert expiry is not None


def test_get_expiry_by_criteria_current_month(mock_instrument_dataframe):
    inst = Instrument()
    inst._dataframe = mock_instrument_dataframe
    expiry = inst.get_expiry_by_criteria("EURINR", 0.0, "FUT", "current_month")
    assert expiry is not None


def test_get_expiry_by_criteria_next_month(mock_instrument_dataframe):
    inst = Instrument()
    inst._dataframe = mock_instrument_dataframe
    expiry = inst.get_expiry_by_criteria("EURINR", 0.0, "FUT", "next_month")
    assert expiry is not None


def test_get_exchange_token_by_criteria(mock_instrument_dataframe):
    inst = Instrument()
    inst._dataframe = mock_instrument_dataframe
    expiry = mock_instrument_dataframe["expiry"].iloc[0]
    token = inst.get_exchange_token_by_criteria("NIFTYJUN24FUT", 0.0, "XX", expiry)

    filtered_df = mock_instrument_dataframe[
        (mock_instrument_dataframe["expiry"] == expiry)
        & (mock_instrument_dataframe["Trading Symbol"] == "NIFTYJUN24FUT")
        & (mock_instrument_dataframe["Option Type"] == "XX")
    ]
    expected_token = (
        filtered_df["exchange_token"].values[0] if not filtered_df.empty else None
    )
    assert token == expected_token


def test_get_kite_token_by_exchange_token(mock_instrument_dataframe):
    inst = Instrument()
    inst._dataframe = mock_instrument_dataframe
    token = inst.get_kite_token_by_exchange_token("1010822")
    expected_token = mock_instrument_dataframe[
        mock_instrument_dataframe["exchange_token"] == "1010822"
    ]["instrument_token"]
    expected_token = int(expected_token.values[0]) if not expected_token.empty else None
    assert token == expected_token


def test_get_lot_size_by_exchange_token(mock_instrument_dataframe):
    inst = Instrument()
    inst._dataframe = mock_instrument_dataframe
    lot_size = inst.get_lot_size_by_exchange_token("1010822")
    expected_lot_size = mock_instrument_dataframe[
        mock_instrument_dataframe["exchange_token"] == "1010822"
    ]["lot_size"]
    expected_lot_size = (
        expected_lot_size.values[0] if not expected_lot_size.empty else None
    )
    assert lot_size == expected_lot_size


def test_get_trading_symbol_by_exchange_token(mock_instrument_dataframe):
    inst = Instrument()
    inst._dataframe = mock_instrument_dataframe
    trading_symbol = inst.get_trading_symbol_by_exchange_token("1010822")
    expected_symbol = mock_instrument_dataframe[
        mock_instrument_dataframe["exchange_token"] == "1010822"
    ]["tradingsymbol"]
    expected_symbol = expected_symbol.values[0] if not expected_symbol.empty else None
    assert trading_symbol == expected_symbol


def test_get_full_format_trading_symbol_by_exchange_token(mock_instrument_dataframe):
    inst = Instrument()
    inst._dataframe = mock_instrument_dataframe
    trading_symbol = inst.get_full_format_trading_symbol_by_exchange_token("1010822")
    expected_symbol = mock_instrument_dataframe[
        mock_instrument_dataframe["exchange_token"] == "1010822"
    ]["Trading Symbol"]
    expected_symbol = expected_symbol.values[0] if not expected_symbol.empty else None
    assert trading_symbol == expected_symbol


def test_get_base_symbol_by_exchange_token(mock_instrument_dataframe):
    inst = Instrument()
    inst._dataframe = mock_instrument_dataframe
    base_symbol = inst.get_base_symbol_by_exchange_token("1010822")
    expected_symbol = mock_instrument_dataframe[
        mock_instrument_dataframe["exchange_token"] == "1010822"
    ]["name"]
    expected_symbol = expected_symbol.values[0] if not expected_symbol.empty else None
    assert base_symbol == expected_symbol


def test_get_exchange_by_exchange_token(mock_instrument_dataframe):
    inst = Instrument()
    inst._dataframe = mock_instrument_dataframe
    exchange = inst.get_exchange_by_exchange_token("1010822")
    expected_exchange = mock_instrument_dataframe[
        mock_instrument_dataframe["exchange_token"] == "1010822"
    ]["exchange"]
    expected_exchange = (
        expected_exchange.values[0] if not expected_exchange.empty else None
    )
    assert exchange == expected_exchange


def test_get_exchange_token_by_token(mock_instrument_dataframe):
    inst = Instrument()
    inst._dataframe = mock_instrument_dataframe
    exchange_token = inst.get_exchange_token_by_token("258770438")
    expected_token = mock_instrument_dataframe[
        mock_instrument_dataframe["instrument_token"] == 258770438
    ]["exchange_token"]
    expected_token = expected_token.values[0] if not expected_token.empty else None
    assert exchange_token == expected_token


def test_get_exchange_token_by_name(mock_instrument_dataframe):
    inst = Instrument()
    inst._dataframe = mock_instrument_dataframe
    exchange_token = inst.get_exchange_token_by_name("MCX")
    expected_token = mock_instrument_dataframe[
        mock_instrument_dataframe["name"] == "MCX"
    ]["exchange_token"]
    expected_token = expected_token.values[0] if not expected_token.empty else None
    assert exchange_token == expected_token


def test_get_instrument_type_by_exchange_token(mock_instrument_dataframe):
    inst = Instrument()
    inst._dataframe = mock_instrument_dataframe
    instrument_type = inst.get_instrument_type_by_exchange_token("1010822")
    expected_type = mock_instrument_dataframe[
        mock_instrument_dataframe["exchange_token"] == "1010822"
    ]["instrument_type"]
    expected_type = expected_type.values[0] if not expected_type.empty else None
    assert instrument_type == expected_type


def test_get_token_by_name(mock_instrument_dataframe):
    inst = Instrument()
    inst._dataframe = mock_instrument_dataframe
    token = inst.get_token_by_name("RISHABH")
    expected_token = mock_instrument_dataframe[
        mock_instrument_dataframe["Symbol"] == "RISHABH"
    ]["instrument_token"]
    expected_token = expected_token.values[0] if not expected_token.empty else None
    assert str(token) == str(expected_token)


def test_get_symbols_with_expiry_today(mock_instrument_dataframe):
    inst = Instrument()
    inst._dataframe = mock_instrument_dataframe
    today = datetime.now().strftime("%Y-%m-%d")
    symbols_with_expiry_today = inst.get_symbols_with_expiry_today(
        "BCD-FUT", ["EURINR"]
    )
    expected_symbols = mock_instrument_dataframe[
        (mock_instrument_dataframe["expiry"] == today)
        & (mock_instrument_dataframe["name"] == "EURINR")
    ]["name"].tolist()
    assert symbols_with_expiry_today == expected_symbols


def test_fetch_base_symbol_token():
    inst = Instrument()
    token = inst.fetch_base_symbol_token("NIFTY")
    assert token == "256265"


def test_get_margin_multiplier():
    inst = Instrument()
    multiplier = inst.get_margin_multiplier("NIFTY21JUL15000CE")
    assert multiplier == 546


# Tests for the remaining methods outside the class
def test_weekly_expiry_type():
    inst = Instrument()
    if datetime.today().weekday() == 3:
        assert inst.weekly_expiry_type() == "next_week"
    else:
        assert inst.weekly_expiry_type() == "current_week"


def test_monthly_expiry_type():
    inst = Instrument()
    today = datetime.now().date()
    next_month = today.replace(day=28) + timedelta(days=4)
    last_day_of_current_month = next_month - timedelta(days=next_month.day)
    last_thursday_of_current_month = last_day_of_current_month
    while last_thursday_of_current_month.weekday() != 3:
        last_thursday_of_current_month -= timedelta(days=1)

    if today == last_thursday_of_current_month:
        assert inst.monthly_expiry_type() == "next_month"
    elif today < last_thursday_of_current_month:
        assert inst.monthly_expiry_type() == "current_month"
    else:
        if today <= last_day_of_current_month:
            assert inst.monthly_expiry_type() == "current_month"
        else:
            assert inst.monthly_expiry_type() == "next_month"


# Run tests
if __name__ == "__main__":
    pytest.main(["-v"])
