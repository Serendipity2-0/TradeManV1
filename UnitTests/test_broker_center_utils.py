from datetime import datetime
import os, sys
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from dotenv import load_dotenv

# Add the necessary path
DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

# Load environment variables
ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

# Import the functions to test
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
    place_order_for_brokers,
    modify_order_for_brokers,
    all_broker_login,
    fetch_active_users_from_firebase,
    fetch_list_of_strategies_from_firebase,
    fetch_users_for_strategies_from_firebase,
    fetch_primary_accounts_from_firebase,
    fetch_freecash_for_user,
    download_csv_for_brokers,
    fetch_holdings_value_for_user_broker,
    fetch_user_credentials_firebase,
    fetch_strategy_details_for_user,
    fetch_active_strategies_all_users,
    get_today_orders_for_brokers,
    get_today_open_orders_for_brokers,
    create_counter_order_details,
    create_hedge_counter_order_details,
    get_avg_prc_broker_key,
    get_order_id_broker_key,
    get_trading_symbol_broker_key,
    get_qty_broker_key,
    get_time_stamp_broker_key,
    get_trade_id_broker_key,
    convert_date_str_to_standard_format,
    convert_to_standard_format,
    process_user_ledger,
    calculate_user_net_values,
    get_primary_account_obj,
    get_broker_pnl,
    get_orders_tax,
    get_order_margin,
    get_broker_payin,
)

logger = LoggerSetup()


@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("ZERODHA_BROKER", "Zerodha")
    monkeypatch.setenv("ALICEBLUE_BROKER", "AliceBlue")
    monkeypatch.setenv("FIRSTOCK_BROKER", "Firstock")
    monkeypatch.setenv("FIREBASE_USER_COLLECTION", "clients_users")
    monkeypatch.setenv("FIREBASE_STRATEGY_COLLECTION", "strategies")


# Example for testing place_order_for_brokers
@pytest.mark.asyncio
async def test_place_order_for_brokers(mock_env):
    order_details = {"broker": "Zerodha"}
    user_credentials = {"username": "test_user"}

    with patch(
        "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter.kite_place_orders_for_users",
        new_callable=AsyncMock,
    ) as mock_order:
        mock_order.return_value = {"status": "success"}
        response = await place_order_for_brokers(order_details, user_credentials)
        assert response == {"status": "success"}

    order_details["broker"] = "AliceBlue"
    with patch(
        "Executor.ExecutorUtils.BrokerCenter.Brokers.AliceBlue.alice_adapter.ant_place_orders_for_users",
        new_callable=AsyncMock,
    ) as mock_order:
        mock_order.return_value = {"status": "success"}
        response = await place_order_for_brokers(order_details, user_credentials)
        assert response == {"status": "success"}

    order_details["broker"] = "Firstock"
    with patch(
        "Executor.ExecutorUtils.BrokerCenter.Brokers.Firstock.firstock_adapter.firstock_place_orders_for_users",
        new_callable=AsyncMock,
    ) as mock_order:
        mock_order.return_value = {"status": "success"}
        response = await place_order_for_brokers(order_details, user_credentials)
        assert response == {"status": "success"}


# Example for testing modify_order_for_brokers
def test_modify_order_for_brokers(mock_env):
    order_details = {"broker": "Zerodha"}
    user_credentials = {"username": "test_user"}

    with patch(
        "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter.kite_modify_orders_for_users"
    ) as mock_modify:
        mock_modify.return_value = {"status": "modified"}
        response = modify_order_for_brokers(order_details, user_credentials)
        assert response == {"status": "modified"}

    order_details["broker"] = "AliceBlue"
    with patch(
        "Executor.ExecutorUtils.BrokerCenter.Brokers.AliceBlue.alice_adapter.ant_modify_orders_for_users"
    ) as mock_modify:
        mock_modify.return_value = {"status": "modified"}
        response = modify_order_for_brokers(order_details, user_credentials)
        assert response == {"status": "modified"}

    order_details["broker"] = "Firstock"
    with patch(
        "Executor.ExecutorUtils.BrokerCenter.Brokers.Firstock.firstock_adapter.firstock_modify_orders_for_users"
    ) as mock_modify:
        mock_modify.return_value = {"status": "modified"}
        response = modify_order_for_brokers(order_details, user_credentials)
        assert response == {"status": "modified"}


# Example for testing all_broker_login
def test_all_broker_login(mock_env):
    active_users = [
        {"Broker": {"BrokerName": "Zerodha", "BrokerUsername": "user1"}},
        {"Broker": {"BrokerName": "AliceBlue", "BrokerUsername": "user2"}},
        {"Broker": {"BrokerName": "Firstock", "BrokerUsername": "user3"}},
    ]

    with patch(
        "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.kite_login.login_in_zerodha",
        return_value="session1",
    ):
        with patch(
            "Executor.ExecutorUtils.BrokerCenter.Brokers.AliceBlue.alice_login.login_in_aliceblue",
            return_value="session2",
        ):
            with patch(
                "Executor.ExecutorUtils.BrokerCenter.Brokers.Firstock.firstock_login.login_in_firstock",
                return_value="session3",
            ):

                updated_users = all_broker_login(active_users)
                assert len(updated_users) == 3


# Example for testing fetch_active_users_from_firebase
def test_fetch_active_users_from_firebase(mock_env):
    with patch(
        "Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter.fetch_collection_data_firebase"
    ) as mock_fetch:
        mock_fetch.return_value = {
            "user1": {"Active": True, "Details": "Details1"},
            "user2": {"Active": False, "Details": "Details2"},
            "user3": {"Active": True, "Details": "Details3"},
        }
        active_users = fetch_active_users_from_firebase()
        assert len(active_users) == 2


# Example for testing fetch_list_of_strategies_from_firebase
def test_fetch_list_of_strategies_from_firebase(mock_env):
    # Mock fetch_active_users_from_firebase to return expected data
    with patch(
        "Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils.fetch_active_users_from_firebase"
    ) as mock_fetch_users:
        mock_fetch_users.return_value = [
            {"Strategies": ["Strategy1", "Strategy2"]},
            {"Strategies": ["Strategy3"]},
        ]

        # Now calling fetch_list_of_strategies_from_firebase should get data from the mocked fetch_active_users_from_firebase
        strategies = fetch_list_of_strategies_from_firebase()

        # Check if the strategies list has 3 unique strategies
        assert len(strategies) == 3
        assert "Strategy1" in strategies
        assert "Strategy2" in strategies
        assert "Strategy3" in strategies


# Example for testing fetch_users_for_strategies_from_firebase


def test_fetch_users_for_strategies_from_firebase(mock_env):
    strategy_name = "Strategy1"

    # Mock fetch_active_users_from_firebase to return expected data
    with patch(
        "Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils.fetch_active_users_from_firebase"
    ) as mock_fetch_users:
        mock_fetch_users.return_value = [
            {"Strategies": ["Strategy1", "Strategy2"], "Active": True},
            {"Strategies": ["Strategy3"], "Active": True},
            {"Strategies": ["Strategy1"], "Active": True},
            {"Strategies": ["Strategy4"], "Active": False},  # Inactive user
        ]

        # Now calling fetch_users_for_strategies_from_firebase should get data from the mocked fetch_active_users_from_firebase
        users = fetch_users_for_strategies_from_firebase(strategy_name)

        # Check if the number of users with 'Strategy1' is 2
        assert len(users) == 2
        assert {"Strategies": ["Strategy1", "Strategy2"], "Active": True} in users
        assert {"Strategies": ["Strategy1"], "Active": True} in users


# Example for testing fetch_primary_accounts_from_firebase
def test_fetch_primary_accounts_from_firebase(mock_env):
    with patch(
        "Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter.fetch_collection_data_firebase"
    ) as mock_fetch:
        mock_fetch.return_value = {
            "user1": {"Tr_No": "primary1", "Broker": {"BrokerUsername": "user1"}},
            "user2": {"Tr_No": "primary2", "Broker": {"BrokerUsername": "user2"}},
        }
        account = fetch_primary_accounts_from_firebase("primary1")
        assert account["Broker"]["BrokerUsername"] == "user1"


# Example for testing fetch_freecash_for_user
def test_fetch_freecash_for_user(mock_env):
    user = {"Broker": {"BrokerName": "Zerodha", "BrokerUsername": "user1"}}

    with patch(
        "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter.zerodha_fetch_free_cash"
    ) as mock_cash:
        mock_cash.return_value = "10000"
        free_cash = fetch_freecash_for_user(user)
        assert free_cash == 10000.0


# Example for testing download_csv_for_brokers
def test_download_csv_for_brokers(mock_env):
    primary_account = {"Broker": {"BrokerName": "Zerodha"}}

    with patch(
        "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter.get_csv_kite"
    ) as mock_csv:
        mock_csv.return_value = "/path/to/csv"
        csv_path = download_csv_for_brokers(primary_account)
        assert csv_path == "/path/to/csv"


# Example for testing fetch_holdings_value_for_user_broker
def test_fetch_holdings_value_for_user_broker(mock_env):
    user = {"Broker": {"BrokerName": "Zerodha"}}

    with patch(
        "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter.fetch_zerodha_holdings_value"
    ) as mock_holdings:
        mock_holdings.return_value = 50000
        holdings_value = fetch_holdings_value_for_user_broker(user)
        assert holdings_value == 50000


# Example for testing fetch_user_credentials_firebase
def test_fetch_user_credentials_firebase(mock_env):
    broker_user_name = "user1"

    with patch(
        "Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter.fetch_collection_data_firebase"
    ) as mock_fetch:
        mock_fetch.return_value = {
            "user1": {"Broker": {"BrokerUsername": "user1"}},
            "user2": {"Broker": {"BrokerUsername": "user2"}},
        }
        credentials = fetch_user_credentials_firebase(broker_user_name)
        assert credentials["BrokerUsername"] == "user1"


# Example for testing fetch_strategy_details_for_user
def test_fetch_strategy_details_for_user(mock_env):
    username = "user1"

    with patch(
        "Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter.fetch_collection_data_firebase"
    ) as mock_fetch:
        mock_fetch.return_value = {
            "user1": {
                "Broker": {"BrokerUsername": "user1"},
                "Strategies": ["Strategy1", "Strategy2"],
            },
            "user2": {
                "Broker": {"BrokerUsername": "user2"},
                "Strategies": ["Strategy3"],
            },
        }
        strategies = fetch_strategy_details_for_user(username)
        assert len(strategies) == 2


# Example for testing fetch_active_strategies_all_users
def test_fetch_active_strategies_all_users(mock_env):
    with patch(
        "Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter.fetch_collection_data_firebase"
    ) as mock_fetch:
        mock_fetch.return_value = {
            "user1": {"Active": True, "Strategies": ["Strategy1", "Strategy2"]},
            "user2": {"Active": True, "Strategies": ["Strategy3"]},
            "user3": {"Active": False, "Strategies": ["Strategy4"]},
        }
        active_strategies = fetch_active_strategies_all_users()
        assert len(active_strategies) == 3

    # Example for testing get_today_orders_for_brokersdef test_get_today_orders_for_brokers(mock_env):
    user = {"Broker": {"BrokerName": "Zerodha", "BrokerUsername": "test_user"}}

    with patch(
        "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter.zerodha_todays_tradebook"
    ) as mock_orders:
        mock_orders.return_value = [{"status": "COMPLETE"}, {"status": "PENDING"}]

        orders = get_today_orders_for_brokers(user)

        assert len(orders) == 2
        assert {"status": "COMPLETE"} in orders
        assert {"status": "PENDING"} in orders


# Example for testing get_today_open_orders_for_brokers
def test_get_today_open_orders_for_brokers(mock_env):
    user = {"Broker": {"BrokerName": "Zerodha"}}

    with patch(
        "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter.fetch_open_orders"
    ) as mock_open_orders:
        mock_open_orders.return_value = [{"order_id": "order1"}, {"order_id": "order2"}]
        open_orders = get_today_open_orders_for_brokers(user)
        assert len(open_orders) == 2


# Example for testing create_counter_order_details
def test_create_counter_order_details(mock_env):
    tradebook = [{"status": "TRIGGER PENDING", "product": "MIS", "tag": "test_tag"}]
    user = {"Broker": {"BrokerName": "Zerodha", "BrokerUsername": "test_user"}}

    with patch(
        "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter.kite_create_cancel_order"
    ) as mock_cancel:
        with patch(
            "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter.kite_create_sl_counter_order"
        ) as mock_counter:
            mock_cancel.return_value = None
            mock_counter.return_value = {"order": "counter_order"}
            counter_orders = create_counter_order_details(tradebook, user)
            assert len(counter_orders) == 1
            assert counter_orders[0] == {"order": "counter_order"}


# Example for testing create_hedge_counter_order_details
def test_create_hedge_counter_order_details(mock_env):
    tradebook = [
        {
            "status": "COMPLETE",
            "product": "MIS",
            "tag": "HO_EN",
            "instrument_token": "token1",
        }
    ]
    user = {"Broker": {"BrokerName": "Zerodha", "BrokerUsername": "test_user"}}
    open_orders = {
        "net": [{"instrument_token": "token1", "product": "MIS", "quantity": 10}]
    }

    with patch(
        "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter.kite_create_hedge_counter_order"
    ) as mock_hedge:
        mock_hedge.return_value = {"order": "hedge_order"}
        hedge_orders = create_hedge_counter_order_details(tradebook, user, open_orders)
        assert len(hedge_orders) == 1
        assert hedge_orders[0] == {"order": "hedge_order"}


# Example for testing convert_date_str_to_standard_format
def test_convert_date_str_to_standard_format():
    date_str = "2024-01-31 09:20:03"
    assert convert_date_str_to_standard_format(date_str) == "2024-01-31 09:20:03"

    date_str = "23-Jan-2024 09:20:04"
    assert convert_date_str_to_standard_format(date_str) == "2024-01-23 09:20:04"

    date_str = "23/01/2024 09:20:05"
    assert convert_date_str_to_standard_format(date_str) == "2024-01-23 09:20:05"

    date_str = "Invalid date"
    assert convert_date_str_to_standard_format(date_str) == "Invalid date format"


# Example for testing convert_to_standard_format
def test_convert_to_standard_format():
    date_str = "2024-01-31 09:20:03"
    assert convert_to_standard_format(date_str) == "2024-01-31 09:20:03"

    date_obj = datetime.strptime("2024-01-31 09:20:03", "%Y-%m-%d %H:%M:%S")
    assert convert_to_standard_format(date_obj) == "2024-01-31 09:20:03"


# Example for testing get_avg_prc_broker_key
def test_get_avg_prc_broker_key():
    assert get_avg_prc_broker_key("Zerodha") == "average_price"
    assert get_avg_prc_broker_key("AliceBlue") == "Avgprc"
    assert get_avg_prc_broker_key("Firstock") == "averagePrice"


# Example for testing get_order_id_broker_key
def test_get_order_id_broker_key():
    assert get_order_id_broker_key("Zerodha") == "order_id"
    assert get_order_id_broker_key("AliceBlue") == "Nstordno"
    assert get_order_id_broker_key("Firstock") == "orderNumber"


# Example for testing get_trading_symbol_broker_key
def test_get_trading_symbol_broker_key():
    assert get_trading_symbol_broker_key("Zerodha") == "tradingsymbol"
    assert get_trading_symbol_broker_key("AliceBlue") == "Trsym"
    assert get_trading_symbol_broker_key("Firstock") == "tradingSymbol"


# Example for testing get_qty_broker_key
def test_get_qty_broker_key():
    assert get_qty_broker_key("Zerodha") == "quantity"
    assert get_qty_broker_key("AliceBlue") == "Qty"
    assert get_qty_broker_key("Firstock") == "quantity"


# Example for testing get_time_stamp_broker_key
def test_get_time_stamp_broker_key():
    assert get_time_stamp_broker_key("Zerodha") == "order_timestamp"
    assert get_time_stamp_broker_key("AliceBlue") == "OrderedTime"
    assert get_time_stamp_broker_key("Firstock") == "orderTime"


# Example for testing get_trade_id_broker_key
def test_get_trade_id_broker_key():
    assert get_trade_id_broker_key("Zerodha") == "tag"
    assert get_trade_id_broker_key("AliceBlue") == "remarks"
    assert get_trade_id_broker_key("Firstock") == "remarks"


# Example for testing process_user_ledger
def test_process_user_ledger(mock_env):
    user = {"Broker": {"BrokerName": "Zerodha"}}
    ledger = {"balance": "10000"}

    with patch(
        "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter.process_kite_ledger"
    ) as mock_process:
        mock_process.return_value = {"processed_balance": "9000"}
        processed_ledger = process_user_ledger(user, ledger)
        assert processed_ledger["processed_balance"] == "9000"


# Example for testing calculate_user_net_values
def test_calculate_user_net_values(mock_env):
    user = {"Broker": {"BrokerName": "Zerodha"}}
    categorized_df = MagicMock()

    with patch(
        "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter.calculate_kite_net_values"
    ) as mock_calc:
        mock_calc.return_value = {"net_value": 15000}
        net_values = calculate_user_net_values(user, categorized_df)
        assert net_values["net_value"] == 15000


# Example for testing get_primary_account_obj
# def test_get_primary_account_obj(mock_env):
#     with patch(
#         "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter.create_kite_obj"
#     ) as mock_obj:
#         mock_obj.return_value = MagicMock()
#         obj = get_primary_account_obj()
#         assert obj is not None


# Example for testing get_broker_pnl
def test_get_broker_pnl(mock_env):
    user = {"Broker": {"BrokerName": "Zerodha"}}

    with patch(
        "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter.get_zerodha_pnl"
    ) as mock_pnl:
        mock_pnl.return_value = {"pnl": 500}
        pnl = get_broker_pnl(user)
        assert pnl["pnl"] == 500


# Example for testing get_orders_tax@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_get_orders_tax(mock_env):
    orders_to_place = [{"order_id": "order1"}]
    user_credentials = {"BrokerName": "Zerodha"}

    with patch(
        "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter.get_order_tax",
        new_callable=AsyncMock,
    ) as mock_tax:
        mock_tax.return_value = {"tax": 100}
        tax = await get_orders_tax(orders_to_place, user_credentials)
        assert tax["tax"] == 100


# Example for testing get_order_margin
def test_get_order_margin(mock_env):
    orders_to_place = [{"order_id": "order1"}]
    user_credentials = {"BrokerName": "Zerodha"}

    with patch(
        "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter.get_margin_utilized"
    ) as mock_margin:
        mock_margin.return_value = {"margin": 200}
        margin = get_order_margin(orders_to_place, user_credentials)
        assert margin["margin"] == 200


# Example for testing get_broker_payin
def test_get_broker_payin(mock_env):
    user = {"Broker": {"BrokerName": "Zerodha"}}

    with patch(
        "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter.get_broker_payin"
    ) as mock_payin:
        mock_payin.return_value = {"payin": 300}
        payin = get_broker_payin(user)
        assert payin["payin"] == 300
