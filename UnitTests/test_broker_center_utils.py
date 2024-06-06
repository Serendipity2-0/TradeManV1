import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# Mock environment variables
@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("ZERODHA_BROKER", "Zerodha")
    monkeypatch.setenv("ALICEBLUE_BROKER", "AliceBlue")
    monkeypatch.setenv("FIRSTOCK_BROKER", "Firstock")
    monkeypatch.setenv("FIREBASE_USER_COLLECTION", "temp_clients")
    monkeypatch.setenv("FIREBASE_STRATEGY_COLLECTION", "temp_strategies")


# Example mock data for user credentials
mock_user_credentials = {
    "BrokerName": "Zerodha",
    "BrokerUsername": "test_user",
    "SessionId": "test_session",
    "ApiKey": "test_api_key",
}

# Example mock order details
mock_order_details = {"broker": "Zerodha", "order_id": "12345"}


@pytest.fixture
def mock_logger():
    with patch("Executor.ExecutorUtils.LoggingCenter.logger_utils.LoggerSetup") as mock:
        yield mock


@pytest.fixture
def mock_firebase_utils():
    with patch(
        "Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter"
    ) as mock:
        yield mock


@pytest.fixture
def mock_zerodha_adapter():
    with patch(
        "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter"
    ) as mock:
        yield mock


@pytest.fixture
def mock_alice_adapter():
    with patch(
        "Executor.ExecutorUtils.BrokerCenter.Brokers.AliceBlue.alice_adapter"
    ) as mock:
        yield mock


@pytest.fixture
def mock_firstock_adapter():
    with patch(
        "Executor.ExecutorUtils.BrokerCenter.Brokers.Firstock.firstock_adapter"
    ) as mock:
        yield mock


# Test function for place_order_for_brokers
def test_place_order_for_brokers(
    mock_env, mock_zerodha_adapter, mock_alice_adapter, mock_firstock_adapter
):
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
        place_order_for_brokers,
    )

    mock_zerodha_adapter.kite_place_orders_for_users.return_value = {
        "status": "success"
    }
    mock_alice_adapter.ant_place_orders_for_users.return_value = {"status": "success"}
    mock_firstock_adapter.firstock_place_orders_for_users.return_value = {
        "status": "success"
    }

    response = place_order_for_brokers(mock_order_details, mock_user_credentials)
    assert response["status"] == "success"


# Test function for modify_order_for_brokers
def test_modify_order_for_brokers(
    mock_env, mock_zerodha_adapter, mock_alice_adapter, mock_firstock_adapter
):
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
        modify_order_for_brokers,
    )

    mock_zerodha_adapter.kite_modify_orders_for_users.return_value = {
        "status": "modified"
    }
    mock_alice_adapter.ant_modify_orders_for_users.return_value = {"status": "modified"}
    mock_firstock_adapter.firstock_modify_orders_for_users.return_value = {
        "status": "modified"
    }

    response = modify_order_for_brokers(mock_order_details, mock_user_credentials)
    assert response["status"] == "modified"


# Test function for fetch_active_users_from_firebase
def test_fetch_active_users_from_firebase(mock_env, mock_firebase_utils):
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
        fetch_active_users_from_firebase,
    )

    mock_firebase_utils.fetch_collection_data_firebase.return_value = {
        "user1": {"Active": True, "Broker": {"BrokerUsername": "user1"}},
        "user2": {"Active": False, "Broker": {"BrokerUsername": "user2"}},
    }

    active_users = fetch_active_users_from_firebase()
    assert len(active_users) == 1
    assert active_users[0]["Broker"]["BrokerUsername"] == "user1"


# Test function for all_broker_login
def test_all_broker_login(
    mock_env,
    mock_firebase_utils,
    mock_logger,
    mock_zerodha_adapter,
    mock_alice_adapter,
    mock_firstock_adapter,
):
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import all_broker_login

    active_users = [
        {
            "Broker": {"BrokerName": "zerodha", "BrokerUsername": "user1"},
            "Tr_No": "123",
        },
        {
            "Broker": {"BrokerName": "aliceblue", "BrokerUsername": "user2"},
            "Tr_No": "124",
        },
        {
            "Broker": {"BrokerName": "firstock", "BrokerUsername": "user3"},
            "Tr_No": "125",
        },
    ]

    mock_zerodha_adapter.login_in_zerodha.return_value = "session_id_1"
    mock_alice_adapter.login_in_aliceblue.return_value = "session_id_2"
    mock_firstock_adapter.login_in_firstock.return_value = "session_id_3"

    updated_users = all_broker_login(active_users)

    assert updated_users[0]["Broker"]["SessionId"] == "session_id_1"
    assert updated_users[1]["Broker"]["SessionId"] == "session_id_2"
    assert updated_users[2]["Broker"]["SessionId"] == "session_id_3"


# Test function for fetch_list_of_strategies_from_firebase
def test_fetch_list_of_strategies_from_firebase(mock_env, mock_firebase_utils):
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
        fetch_list_of_strategies_from_firebase,
    )

    mock_firebase_utils.fetch_collection_data_firebase.return_value = {
        "user1": {
            "Active": True,
            "Broker": {"BrokerUsername": "user1"},
            "Strategies": ["Strategy1"],
        },
        "user2": {
            "Active": True,
            "Broker": {"BrokerUsername": "user2"},
            "Strategies": ["Strategy2"],
        },
    }

    strategies = fetch_list_of_strategies_from_firebase()
    assert len(strategies) == 2
    assert "Strategy1" in strategies
    assert "Strategy2" in strategies


# Test function for fetch_users_for_strategies_from_firebase
def test_fetch_users_for_strategies_from_firebase(mock_env, mock_firebase_utils):
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
        fetch_users_for_strategies_from_firebase,
    )

    mock_firebase_utils.fetch_collection_data_firebase.return_value = {
        "user1": {
            "Active": True,
            "Broker": {"BrokerUsername": "user1"},
            "Strategies": ["Strategy1"],
        },
        "user2": {
            "Active": True,
            "Broker": {"BrokerUsername": "user2"},
            "Strategies": ["Strategy2", "Strategy1"],
        },
    }

    users = fetch_users_for_strategies_from_firebase("Strategy1")
    assert len(users) == 2
    assert users[0]["Broker"]["BrokerUsername"] == "user1"
    assert users[1]["Broker"]["BrokerUsername"] == "user2"


# Test function for fetch_primary_accounts_from_firebase
def test_fetch_primary_accounts_from_firebase(mock_env, mock_firebase_utils):
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
        fetch_primary_accounts_from_firebase,
    )

    mock_firebase_utils.fetch_collection_data_firebase.return_value = {
        "user1": {
            "Active": True,
            "Broker": {"BrokerUsername": "user1", "Tr_No": "primary_account"},
        },
        "user2": {"Active": True, "Broker": {"BrokerUsername": "user2"}},
    }

    primary_account = fetch_primary_accounts_from_firebase("primary_account")
    assert primary_account["Broker"]["BrokerUsername"] == "user1"


# Test function for fetch_freecash_for_user
def test_fetch_freecash_for_user(
    mock_env, mock_zerodha_adapter, mock_alice_adapter, mock_firstock_adapter
):
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
        fetch_freecash_for_user,
    )

    user = {"Broker": {"BrokerName": "zerodha", "BrokerUsername": "user1"}}
    mock_zerodha_adapter.zerodha_fetch_free_cash.return_value = 1000.0

    free_cash = fetch_freecash_for_user(user)
    assert free_cash == 1000.0


# Test function for download_csv_for_brokers
def test_download_csv_for_brokers(mock_env, mock_zerodha_adapter, mock_alice_adapter):
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
        download_csv_for_brokers,
    )

    primary_account = {"Broker": {"BrokerName": "zerodha"}}
    mock_zerodha_adapter.get_csv_kite.return_value = "/path/to/zerodha.csv"

    csv_path = download_csv_for_brokers(primary_account)
    assert csv_path == "/path/to/zerodha.csv"


# Test function for fetch_holdings_value_for_user_broker
def test_fetch_holdings_value_for_user_broker(
    mock_env, mock_zerodha_adapter, mock_alice_adapter, mock_firstock_adapter
):
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
        fetch_holdings_value_for_user_broker,
    )

    user = {"Broker": {"BrokerName": "zerodha", "BrokerUsername": "user1"}}
    mock_zerodha_adapter.fetch_zerodha_holdings_value.return_value = 5000.0

    holdings_value = fetch_holdings_value_for_user_broker(user)
    assert holdings_value == 5000.0


# Test function for fetch_user_credentials_firebase
def test_fetch_user_credentials_firebase(mock_env, mock_firebase_utils):
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
        fetch_user_credentials_firebase,
    )

    mock_firebase_utils.fetch_collection_data_firebase.return_value = {
        "user1": {"Broker": {"BrokerUsername": "user1"}},
        "user2": {"Broker": {"BrokerUsername": "user2"}},
    }

    credentials = fetch_user_credentials_firebase("user1")
    assert credentials["BrokerUsername"] == "user1"


# Test function for fetch_strategy_details_for_user
def test_fetch_strategy_details_for_user(mock_env, mock_firebase_utils):
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
        fetch_strategy_details_for_user,
    )

    mock_firebase_utils.fetch_collection_data_firebase.return_value = {
        "user1": {
            "Broker": {"BrokerUsername": "user1"},
            "Strategies": ["Strategy1", "Strategy2"],
        },
    }

    strategies = fetch_strategy_details_for_user("user1")
    assert len(strategies) == 2
    assert "Strategy1" in strategies


# Test function for fetch_active_strategies_all_users
def test_fetch_active_strategies_all_users(mock_env, mock_firebase_utils):
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
        fetch_active_strategies_all_users,
    )

    mock_firebase_utils.fetch_collection_data_firebase.return_value = {
        "user1": {
            "Active": True,
            "Broker": {"BrokerUsername": "user1"},
            "Strategies": ["Strategy1"],
        },
        "user2": {
            "Active": True,
            "Broker": {"BrokerUsername": "user2"},
            "Strategies": ["Strategy2"],
        },
    }

    strategies = fetch_active_strategies_all_users()
    assert len(strategies) == 2
    assert "Strategy1" in strategies
    assert "Strategy2" in strategies


# Test function for get_today_orders_for_brokers
def test_get_today_orders_for_brokers(
    mock_env, mock_zerodha_adapter, mock_alice_adapter, mock_firstock_adapter
):
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
        get_today_orders_for_brokers,
    )

    user = {"Broker": {"BrokerName": "zerodha", "BrokerUsername": "user1"}}
    mock_zerodha_adapter.zerodha_todays_tradebook.return_value = [
        {"status": "COMPLETE", "trade_id": "1"}
    ]

    orders = get_today_orders_for_brokers(user)
    assert len(orders) == 1
    assert orders[0]["status"] == "COMPLETE"


# Test function for get_today_open_orders_for_brokers
def test_get_today_open_orders_for_brokers(
    mock_env, mock_zerodha_adapter, mock_alice_adapter, mock_firstock_adapter
):
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
        get_today_open_orders_for_brokers,
    )

    user = {"Broker": {"BrokerName": "zerodha", "BrokerUsername": "user1"}}
    mock_zerodha_adapter.fetch_open_orders.return_value = [
        {"status": "OPEN", "order_id": "1"}
    ]

    open_orders = get_today_open_orders_for_brokers(user)
    assert len(open_orders) == 1
    assert open_orders[0]["status"] == "OPEN"


# Test function for create_counter_order_details
def test_create_counter_order_details(
    mock_env, mock_zerodha_adapter, mock_alice_adapter, mock_firstock_adapter
):
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
        create_counter_order_details,
    )

    user = {"Broker": {"BrokerName": "zerodha", "BrokerUsername": "user1"}}
    tradebook = [{"status": "TRIGGER PENDING", "product": "MIS", "tag": "1"}]

    mock_zerodha_adapter.kite_create_cancel_order.return_value = True
    mock_zerodha_adapter.kite_create_sl_counter_order.return_value = {
        "status": "created"
    }

    counter_orders = create_counter_order_details(tradebook, user)
    assert len(counter_orders) == 1
    assert counter_orders[0]["status"] == "created"


# Test function for create_hedge_counter_order_details
def test_create_hedge_counter_order_details(
    mock_env, mock_zerodha_adapter, mock_alice_adapter, mock_firstock_adapter
):
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
        create_hedge_counter_order_details,
    )

    user = {"Broker": {"BrokerName": "zerodha", "BrokerUsername": "user1"}}
    tradebook = [{"status": "COMPLETE", "product": "MIS", "tag": "HO_EN"}]
    open_orders = {"net": [{"instrument_token": "1", "product": "MIS", "quantity": 10}]}

    mock_zerodha_adapter.kite_create_hedge_counter_order.return_value = {
        "status": "created"
    }

    hedge_counter_orders = create_hedge_counter_order_details(
        tradebook, user, open_orders
    )
    assert len(hedge_counter_orders) == 1
    assert hedge_counter_orders[0]["status"] == "created"


# Test function for get_avg_prc_broker_key
def test_get_avg_prc_broker_key():
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
        get_avg_prc_broker_key,
    )

    assert get_avg_prc_broker_key("Zerodha") == "average_price"
    assert get_avg_prc_broker_key("AliceBlue") == "Avgprc"
    assert get_avg_prc_broker_key("Firstock") == "averagePrice"


# Test function for get_order_id_broker_key
def test_get_order_id_broker_key():
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
        get_order_id_broker_key,
    )

    assert get_order_id_broker_key("Zerodha") == "order_id"
    assert get_order_id_broker_key("AliceBlue") == "Nstordno"
    assert get_order_id_broker_key("Firstock") == "orderNumber"


# Test function for get_trading_symbol_broker_key
def test_get_trading_symbol_broker_key():
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
        get_trading_symbol_broker_key,
    )

    assert get_trading_symbol_broker_key("Zerodha") == "tradingsymbol"
    assert get_trading_symbol_broker_key("AliceBlue") == "Trsym"
    assert get_trading_symbol_broker_key("Firstock") == "tradingSymbol"


# Test function for get_qty_broker_key
def test_get_qty_broker_key():
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import get_qty_broker_key

    assert get_qty_broker_key("Zerodha") == "quantity"
    assert get_qty_broker_key("AliceBlue") == "Qty"
    assert get_qty_broker_key("Firstock") == "quantity"


# Test function for get_time_stamp_broker_key
def test_get_time_stamp_broker_key():
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
        get_time_stamp_broker_key,
    )

    assert get_time_stamp_broker_key("Zerodha") == "order_timestamp"
    assert get_time_stamp_broker_key("AliceBlue") == "OrderedTime"
    assert get_time_stamp_broker_key("Firstock") == "orderTime"


# Test function for get_trade_id_broker_key
def test_get_trade_id_broker_key():
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
        get_trade_id_broker_key,
    )

    assert get_trade_id_broker_key("Zerodha") == "tag"
    assert get_trade_id_broker_key("AliceBlue") == "remarks"
    assert get_trade_id_broker_key("Firstock") == "remarks"


# Test function for convert_date_str_to_standard_format
def test_convert_date_str_to_standard_format():
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
        convert_date_str_to_standard_format,
    )

    assert (
        convert_date_str_to_standard_format("2024-01-31 09:20:03")
        == "2024-01-31 09:20:03"
    )
    assert (
        convert_date_str_to_standard_format("23-Jan-2024 09:20:04")
        == "2024-01-23 09:20:04"
    )
    assert (
        convert_date_str_to_standard_format("23/01/2024 09:20:05")
        == "2024-01-23 09:20:05"
    )


# Test function for convert_to_standard_format
def test_convert_to_standard_format():
    from datetime import datetime
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
        convert_to_standard_format,
    )

    assert convert_to_standard_format("2024-01-31 09:20:03") == "2024-01-31 09:20:03"
    assert (
        convert_to_standard_format(datetime(2024, 1, 31, 9, 20, 3))
        == "2024-01-31 09:20:03"
    )


# Test function for get_ledger_for_user
def test_get_ledger_for_user(
    mock_env, mock_zerodha_adapter, mock_alice_adapter, mock_firstock_adapter
):
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
        get_ledger_for_user,
    )

    user = {"Broker": {"BrokerName": "zerodha", "BrokerUsername": "user1"}}
    mock_zerodha_adapter.zerodha_get_ledger.return_value = {"balance": 1000.0}

    ledger = get_ledger_for_user(user)
    assert ledger["balance"] == 1000.0


# Test function for process_user_ledger
def test_process_user_ledger(
    mock_env, mock_zerodha_adapter, mock_alice_adapter, mock_firstock_adapter
):
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
        process_user_ledger,
    )

    user = {"Broker": {"BrokerName": "zerodha", "BrokerUsername": "user1"}}
    ledger = {"balance": 1000.0}
    mock_zerodha_adapter.process_kite_ledger.return_value = {"processed_balance": 900.0}

    processed_ledger = process_user_ledger(user, ledger)
    assert processed_ledger["processed_balance"] == 900.0


# Test function for calculate_user_net_values
def test_calculate_user_net_values(
    mock_env, mock_zerodha_adapter, mock_alice_adapter, mock_firstock_adapter
):
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
        calculate_user_net_values,
    )

    user = {"Broker": {"BrokerName": "zerodha", "BrokerUsername": "user1"}}
    categorized_df = MagicMock()
    mock_zerodha_adapter.calculate_kite_net_values.return_value = {"net_value": 8000.0}

    net_values = calculate_user_net_values(user, categorized_df)
    assert net_values["net_value"] == 8000.0


# Test function for get_primary_account_obj
def test_get_primary_account_obj(mock_env, mock_zerodha_adapter, mock_firebase_utils):
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
        get_primary_account_obj,
    )

    mock_firebase_utils.fetch_collection_data_firebase.return_value = {
        "primary_account": {"Broker": {"ApiKey": "api_key", "SessionId": "session_id"}}
    }
    mock_zerodha_adapter.create_kite_obj.return_value = MagicMock()

    obj = get_primary_account_obj()
    assert obj is not None


# Test function for get_broker_pnl
def test_get_broker_pnl(
    mock_env, mock_zerodha_adapter, mock_alice_adapter, mock_firstock_adapter
):
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import get_broker_pnl

    user = {"Broker": {"BrokerName": "zerodha", "BrokerUsername": "user1"}}
    mock_zerodha_adapter.get_zerodha_pnl.return_value = {"pnl": 500.0}

    pnl = get_broker_pnl(user)
    assert pnl["pnl"] == 500.0


# Test function for get_orders_tax
def test_get_orders_tax(
    mock_env, mock_zerodha_adapter, mock_alice_adapter, mock_firstock_adapter
):
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import get_orders_tax

    orders_to_place = [{"order_id": "1"}]
    mock_zerodha_adapter.get_order_tax.return_value = {"tax": 10.0}

    tax = get_orders_tax(orders_to_place, mock_user_credentials)
    assert tax["tax"] == 10.0


# Test function for get_order_margin
def test_get_order_margin(
    mock_env, mock_zerodha_adapter, mock_alice_adapter, mock_firstock_adapter
):
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import get_order_margin

    orders_to_place = [{"order_id": "1"}]
    mock_zerodha_adapter.get_margin_utilized.return_value = {"margin": 100.0}

    margin = get_order_margin(orders_to_place, mock_user_credentials)
    assert margin["margin"] == 100.0


def test_get_broker_payin(
    mock_env, mock_zerodha_adapter, mock_alice_adapter, mock_firstock_adapter
):
    from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import get_broker_payin

    user = {"Broker": {"BrokerName": "zerodha", "BrokerUsername": "user1"}}
    mock_zerodha_adapter.get_broker_payin.return_value = {"payin": 1000.0}
    mock_alice_adapter.get_broker_payin.return_value = {"payin": 2000.0}
    mock_firstock_adapter.get_broker_payin.return_value = {"payin": 3000.0}

    payin = get_broker_payin(user)
    assert payin["payin"] == 1000.0

    user = {"Broker": {"BrokerName": "alice", "BrokerUsername": "user2"}}
    payin = get_broker_payin(user)
    assert payin["payin"] == 2000.0

    user = {"Broker": {"BrokerName": "firstock", "BrokerUsername": "user3"}}
    payin = get_broker_payin(user)
    assert payin["payin"] == 3000.0
