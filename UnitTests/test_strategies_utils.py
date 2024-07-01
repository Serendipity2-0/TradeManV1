import pytest
from unittest.mock import patch, MagicMock
import datetime as dt
from pydantic import ValidationError
import sys, os
from dotenv import load_dotenv
import pandas as pd

# Add the necessary path
DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

# Load environment variables
ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

# Import the functions to test
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

from Executor.Strategies.StrategiesUtil import (
    EntryParams,
    ExitParams,
    ExtraInformation,
    GeneralParams,
    MarketInfoParams,
    StrategyInfo,
    TodayOrder,
    StrategyBase,
    get_previous_dates,
    fetch_strategy_users,
    fetch_freecash_firebase,
    fetch_risk_per_trade_firebase,
    update_qty_user_firebase,
    assign_trade_id,
    fetch_previous_trade_id,
    update_signal_firebase,
    place_order_strategy_users,
    place_order_single_user,
    update_stoploss_orders,
    calculate_stoploss,
    calculate_multipler_stoploss,
    calculate_priceref_stoploss,
    calculate_trigger_price,
    calculate_transaction_type_sl,
    calculate_target,
    base_symbol_token,
    get_strategy_name_from_trade_id,
    get_signal_from_trade_id,
    fetch_qty_amplifier,
    fetch_strategy_amplifier,
)

# Set up the logger
logger = LoggerSetup()


@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    monkeypatch.setenv("FNO_INFO_PATH", "test_fno_info.csv")
    monkeypatch.setenv("FIREBASE_USER_COLLECTION", "test_users")
    monkeypatch.setenv("FIREBASE_STRATEGY_COLLECTION", "test_strategies")


@pytest.fixture
def mock_fno_info():
    return pd.DataFrame(
        {
            "base_symbol": ["NIFTY", "BANKNIFTY"],
            "token": [256265, 260105],
            "strike_step_size": [50, 100],
            "strike_multiplier": [1, 1],
            "hedge_multiplier": [2, 2],
            "stoploss_multiplier": [0.02, 0.02],
        }
    )


# Patching fetch_collection_data_firebase function
@pytest.fixture
def mock_fetch_collection_data_firebase():
    with patch(
        "Executor.Strategies.StrategiesUtil.fetch_collection_data_firebase"
    ) as mock:
        mock.return_value = [
            {
                "Tr_No": "123",
                "Accounts": {
                    "13May24_FreeCash": 995513.3,
                    "17May24_AccountValue": 628570.89,
                    "17May24_FreeCash": 628570.89,
                    "17May24_Holdings": 0,
                    "18May24_AccountValue": 628570.89,
                    "18May24_FreeCash": 628570.89,
                    "18May24_Holdings": 0,
                    "CurrentBaseCapital": 2500000,
                    "CurrentWeekCapital": 11232.68,
                    "Drawdown": 0,
                    "NetAdditions": -9998218,
                    "NetCharges": 40964.96,
                    "NetCommission": 0,
                    "NetPnL": -796502.94,
                    "NetWithdrawals": 8122168.41,
                    "PnLWithdrawals": 494593.78,
                },
                "Strategies": {
                    "TestStrat": {"SomeField": "SomeValue", "RiskPerTrade": 10}
                },
            }
        ]
        yield mock


@pytest.fixture
def mock_fetch_collection_freecash_data_firebase():
    with patch(
        "Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils.fetch_active_users_from_firebase"
    ) as mock:
        # Define the current date key for FreeCash
        current_date_key = dt.datetime.now().strftime("%d%b%y") + "_FreeCash"
        # Provide mock data in the expected format
        mock.return_value = [
            {
                "Tr_No": "123",
                "Accounts": {
                    "13May24_FreeCash": 995513.3,
                    "17May24_AccountValue": 628570.89,
                    "17May24_FreeCash": 628570.89,
                    "17May24_Holdings": 0,
                    "18May24_AccountValue": 628570.89,
                    "18May24_FreeCash": 628570.89,
                    "18May24_Holdings": 0,
                    current_date_key: 628570.89,  # Mock today's date key
                },
                "Strategies": {"TestStrat": {"SomeField": "SomeValue"}},
            },
            {
                "Tr_No": "124",
                "Accounts": {
                    current_date_key: 500000.0  # Another mock user with different FreeCash
                },
                "Strategies": {"TestStrat": {"SomeField": "SomeValue"}},
            },
        ]
        yield mock


@pytest.fixture
def mock_fetch_risk_per_trade_data_firebase():
    with patch(
        "Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils.fetch_active_users_from_firebase"
    ) as mock:
        mock.return_value = [
            {
                "Tr_No": "123",
                "Strategies": {
                    "TestStrat": {"SomeField": "SomeValue", "RiskPerTrade": 10}
                },
            },
            {"Tr_No": "124", "Strategies": {"OtherStrat": {"SomeField": "SomeValue"}}},
            {
                "Tr_No": "125",
                "Strategies": {
                    "TestStrat": {"SomeField": "SomeValue", "RiskPerTrade": 20}
                },
            },
        ]
        yield mock


@pytest.fixture
def mock_fetch_active_users_from_firebase():
    with patch(
        "Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils.fetch_active_users_from_firebase"
    ) as mock:
        # Provide mock data in the expected format
        mock.return_value = [
            {"Tr_No": "123", "Strategies": {"TestStrat": {"SomeField": "SomeValue"}}},
            {"Tr_No": "124", "Strategies": {"OtherStrat": {"SomeField": "SomeValue"}}},
            {"Tr_No": "125", "Strategies": {"TestStrat": {"SomeField": "SomeValue"}}},
        ]
        yield mock


# Optionally, you can add another fixture for more complex setups
@pytest.fixture
def setup_firebase_mock_data():
    # This can be used to provide more complex mock data if required
    return {
        "Tr_No": "123",
        "Strategies": {"TestStrat": {"SomeField": "SomeValue"}},
        "Accounts": {"10Jun24_FreeCash": 1000},
    }


# Test StrategyBase initialization
def test_strategy_base_initialization():
    entry_params = EntryParams(EntryTime="09:15")
    exit_params = ExitParams(SLType="Fixed")
    extra_info = ExtraInformation(QtyCalc="Dynamic")
    general_params = GeneralParams(
        ExpiryType="Monthly", OrderType="Limit", ProductType="MIS", TimeFrame="15m"
    )
    market_info_params = MarketInfoParams(TradeView="Bullish")

    strategy_base = StrategyBase(
        Description="Test Strategy",
        EntryParams=entry_params,
        ExitParams=exit_params,
        ExtraInformation=extra_info,
        GeneralParams=general_params,
        Instruments=["NIFTY"],
        StrategyName="TestStrat",
        MarketInfoParams=market_info_params,
    )

    assert strategy_base.Description == "Test Strategy"
    assert strategy_base.EntryParams.EntryTime == "09:15"
    assert strategy_base.GeneralParams.ExpiryType == "Monthly"


# Test invalid StrategyBase initialization
def test_strategy_base_initialization_invalid():
    with pytest.raises(ValidationError):
        StrategyBase(Description="Test Strategy")


# Test get_previous_dates
def test_get_previous_dates():
    previous_dates = get_previous_dates(5)
    assert len(previous_dates) == 5


def test_fetch_strategy_users(mock_fetch_active_users_from_firebase):
    # Call the function under test
    users = fetch_strategy_users("TestStrat")

    # Check that the returned list has the expected number of users
    assert len(users) == 2, f"Expected 2 users, but got {len(users)}"

    # Validate the content of the returned users
    user_ids = [user["Tr_No"] for user in users]
    assert "123" in user_ids, "'123' not found in user IDs"
    assert "125" in user_ids, "'125' not found in user IDs"

    # Ensure no other user IDs are present
    assert "124" not in user_ids, "'124' should not be in the returned user IDs"


# Test fetch_freecash_firebase
def test_fetch_freecash_firebase(mock_fetch_collection_freecash_data_firebase):
    freecash = fetch_freecash_firebase("TestStrat")
    # Ensure that "123" is a key in the returned dictionary
    assert "123" in freecash, "Key '123' not found in freecash"
    # Validate the free cash value
    assert (
        freecash["123"] == 628570.89
    ), f"Expected 628570.89, but got {freecash['123']}"


# Test fetch_risk_per_trade_firebase
def test_fetch_risk_per_trade_firebase(mock_fetch_risk_per_trade_data_firebase):
    risk_per_trade = fetch_risk_per_trade_firebase("TestStrat")
    # Check that "123" is a key in the returned dictionary
    assert "123" in risk_per_trade, "Key '123' not found in risk_per_trade"
    # Validate the risk per trade value
    assert risk_per_trade["123"] == 10, f"Expected 10, but got {risk_per_trade['123']}"


# Test assign_trade_id
def test_assign_trade_id():
    orders_to_place = [{"trade_id": "MP123", "order_mode": "Main", "signal": "Long"}]
    updated_orders = assign_trade_id(orders_to_place)
    assert updated_orders[0]["trade_id"] == "MP123_LG_MO_EN"


# Test fetch_previous_trade_id
def test_fetch_previous_trade_id():
    trade_id = "MP123"
    previous_trade_id = fetch_previous_trade_id(trade_id)
    assert previous_trade_id == "MP122"


# Test update_signal_firebase
def test_update_signal_firebase(mock_fetch_collection_data_firebase):
    mock_fetch_collection_data_firebase.return_value = None
    with patch(
        "Executor.Strategies.StrategiesUtil.update_fields_firebase"
    ) as mock_update:
        update_signal_firebase("TestStrat", {"TradeId": "MP123_LG_MO_EN"}, "MP123")
        mock_update.assert_called()


# Test place_order_strategy_users
def test_place_order_strategy_users(mock_fetch_collection_data_firebase):
    mock_fetch_collection_data_firebase.return_value = [
        {"Tr_No": "123", "Strategies": ["TestStrat"]}
    ]
    with patch(
        "Executor.ExecutorUtils.OrderCenter.OrderCenterUtils.place_order_for_strategy"
    ) as mock_place_order:
        place_order_strategy_users("TestStrat", [{"trade_id": "MP123"}])
        mock_place_order.assert_called()


# Test place_order_single_user
def test_place_order_single_user(mock_fetch_collection_data_firebase):
    mock_fetch_collection_data_firebase.return_value = [
        {
            "Tr_No": "123",
            "Accounts": {"17May24_FreeCash": 628570.89},
            "Strategies": ["TestStrat"],
        }
    ]
    with patch(
        "Executor.ExecutorUtils.OrderCenter.OrderCenterUtils.place_order_for_strategy"
    ) as mock_place_order:
        place_order_single_user({"Tr_No": "123"}, [{"trade_id": "MP123"}])
        mock_place_order.assert_called()


# Test update_stoploss_orders
def test_update_stoploss_orders(mock_fetch_collection_data_firebase):
    mock_fetch_collection_data_firebase.return_value = [
        {"Tr_No": "123", "Strategies": ["TestStrat"]}
    ]
    with patch(
        "Executor.ExecutorUtils.OrderCenter.OrderCenterUtils.modify_orders_for_strategy"
    ) as mock_modify_orders:
        update_stoploss_orders("TestStrat", [{"trade_id": "MP123"}])
        mock_modify_orders.assert_called()


# Test calculate_stoploss
def test_calculate_stoploss():
    stoploss = calculate_stoploss(100, "BUY", 0.02)
    assert stoploss == 98


# Test calculate_multipler_stoploss
def test_calculate_multipler_stoploss():
    stoploss = calculate_multipler_stoploss("BUY", 100, 0.02)
    assert stoploss == 98


# Test calculate_priceref_stoploss
def test_calculate_priceref_stoploss():
    stoploss = calculate_priceref_stoploss("BUY", 100, 2)
    assert stoploss == 98


# Test calculate_trigger_price
def test_calculate_trigger_price():
    trigger_price = calculate_trigger_price("BUY", 98)
    assert trigger_price == 97


# Test calculate_transaction_type_sl
def test_calculate_transaction_type_sl():
    transaction_type_sl = calculate_transaction_type_sl("BUY")
    assert transaction_type_sl == "SELL"


# Test calculate_target
def test_calculate_target():
    target = calculate_target(100, 10)
    assert target == 105


# Test base_symbol_token
def test_base_symbol_token(mock_fno_info):
    mock_fno_info.to_csv("test_fno_info.csv", index=False)
    token = base_symbol_token("NIFTY")
    assert token == 256265
    os.remove("test_fno_info.csv")


# Test get_strategy_name_from_trade_id
def test_get_strategy_name_from_trade_id(mock_fetch_collection_data_firebase):
    mock_fetch_collection_data_firebase.return_value = {
        "TestStrat": {"StrategyPrefix": "MP"}
    }
    strategy_name = get_strategy_name_from_trade_id("MP123")
    assert strategy_name == "TestStrat"


# Test get_signal_from_trade_id
def test_get_signal_from_trade_id():
    signal = get_signal_from_trade_id("MP123_LG_MO_EX")
    assert signal == "Long"


# Test fetch_qty_amplifier
def test_fetch_qty_amplifier(mock_fetch_collection_data_firebase):
    mock_fetch_collection_data_firebase.return_value = {
        "MarketInfoParams": {"OSQtyAmplifier": 2}
    }
    qty_amplifier = fetch_qty_amplifier("TestStrat", "OS")
    assert qty_amplifier == 2


# Test fetch_strategy_amplifier
def test_fetch_strategy_amplifier(mock_fetch_collection_data_firebase):
    mock_fetch_collection_data_firebase.return_value = {
        "MarketInfoParams": {"StrategyQtyAmplifier": 1.5}
    }
    amplifier = fetch_strategy_amplifier("TestStrat")
    assert amplifier == 1.5


# Clean up
def teardown_function():
    if os.path.exists("test_fno_info.csv"):
        os.remove("test_fno_info.csv")
