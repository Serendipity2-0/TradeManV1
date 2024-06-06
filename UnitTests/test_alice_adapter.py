import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv
import pandas as pd
from pya3 import Aliceblue, TransactionType, OrderType, ProductType

# Add the necessary path
DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

# Load environment variables
ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

# Import the functions to test
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup


from Executor.Strategies.StrategiesUtil import (
    get_strategy_name_from_trade_id,
    get_signal_from_trade_id,
)
from Executor.ExecutorUtils.BrokerCenter.Brokers.AliceBlue.alice_adapter import (
    AsyncAliceBlue,
    alice_fetch_free_cash,
    merge_ins_csv_files,
    get_ins_csv_alice,
    fetch_aliceblue_holdings_value,
    simplify_aliceblue_order,
    create_alice_obj,
    aliceblue_todays_tradebook,
    calculate_transaction_type,
    calculate_order_type,
    calculate_product_type,
    get_order_status,
    ant_place_orders_for_users,
    ant_modify_orders_for_users,
    ant_create_counter_order,
    ant_create_hedge_counter_order,
    ant_create_cancel_orders,
    process_alice_ledger,
    calculate_alice_net_values,
    fetch_open_orders,
    get_alice_pnl,
    get_margin_utilized,
    get_broker_payin,
)

# Set up the logger
logger = LoggerSetup()


@pytest.fixture
def user_details():
    return {
        "Broker": {
            "BrokerUsername": "test_user",
            "ApiKey": "test_api_key",
            "SessionId": "test_session_id",
        }
    }


@pytest.fixture
def mock_alice_blue():
    with patch(
        "Executor.ExecutorUtils.BrokerCenter.Brokers.AliceBlue.alice_adapter.Aliceblue"
    ) as MockAliceBlue:
        yield MockAliceBlue


def test_alice_fetch_free_cash(user_details, mock_alice_blue):
    mock_alice_instance = mock_alice_blue.return_value
    mock_alice_instance.get_balance.return_value = [{"cashmarginavailable": 1000.0}]

    result = alice_fetch_free_cash(user_details["Broker"])
    assert result == 1000.0


def test_merge_ins_csv_files():
    with patch("pandas.read_csv") as mock_read_csv, patch(
        "pandas.DataFrame.to_csv"
    ) as mock_to_csv:
        nfo_df = pd.DataFrame(
            {
                "Exch": ["NFO"],
                "Exchange Segment": ["segment"],
                "Symbol": ["symbol"],
                "Token": ["token"],
                "Instrument Type": ["type"],
                "Option Type": ["option"],
                "Strike Price": ["strike"],
                "Instrument Name": ["name"],
                "Formatted Ins Name": ["formatted"],
                "Trading Symbol": ["symbol"],
                "Expiry Date": ["date"],
                "Lot Size": ["size"],
                "Tick Size": ["size"],
            }
        )
        bfo_df = nfo_df.copy()
        nse_df = nfo_df.copy()
        mock_read_csv.side_effect = [nfo_df, bfo_df, nse_df]

        result = merge_ins_csv_files()

        assert result is not None
        mock_to_csv.assert_called_once_with("merged_alice_ins.csv", index=False)


def test_get_ins_csv_alice(user_details, mock_alice_blue):
    mock_alice_instance = mock_alice_blue.return_value
    mock_alice_instance.get_contract_master.return_value = None
    with patch(
        "Executor.ExecutorUtils.BrokerCenter.Brokers.AliceBlue.alice_adapter.merge_ins_csv_files"
    ) as mock_merge_ins_csv_files:
        mock_merge_ins_csv_files.return_value = "merged_data"
        result = get_ins_csv_alice(user_details)
        assert result == "merged_data"


def test_fetch_aliceblue_holdings_value(user_details, mock_alice_blue):
    mock_alice_instance = mock_alice_blue.return_value
    mock_alice_instance.get_holding_positions.return_value = {
        "HoldingVal": [{"Price": "100", "HUqty": "5"}]
    }

    result = fetch_aliceblue_holdings_value(user_details)
    assert result == 500.0


def test_simplify_aliceblue_order():
    order_detail = {
        "optionType": "XX",
        "strikePrice": "0",
        "remarks": "test_entry",
        "Avgprc": "100.0",
        "Qty": "10",
        "OrderedTime": "2022-01-01 00:00:00",
        "Trsym": "TEST",
        "Trantype": "B",
    }

    result = simplify_aliceblue_order(order_detail)
    expected_result = {
        "trade_id": "test_entry",
        "avg_price": 100.0,
        "qty": 10,
        "time": "2022-01-01 00:00:00",
        "strike_price": 0,
        "option_type": "FUT",
        "trading_symbol": "TEST",
        "trade_type": "BUY",
        "order_type": "entry",
    }

    assert result == expected_result


def test_create_alice_obj(user_details):
    alice_obj = create_alice_obj(user_details["Broker"])
    assert isinstance(alice_obj, AsyncAliceBlue)


def test_aliceblue_todays_tradebook(user_details, mock_alice_blue):
    mock_alice_instance = mock_alice_blue.return_value
    mock_alice_instance.get_order_history.return_value = {"stat": "Ok", "data": []}

    with patch(
        "Executor.ExecutorUtils.BrokerCenter.Brokers.AliceBlue.alice_adapter.Aliceblue.get_order_history"
    ) as mock_get_order_history:
        mock_get_order_history.return_value = {"stat": "Ok", "data": []}
        result = aliceblue_todays_tradebook("AliceBlue")
        assert result == {"stat": "Ok", "data": []}


def test_calculate_transaction_type():
    assert calculate_transaction_type("BUY") == TransactionType.Buy
    assert calculate_transaction_type("SELL") == TransactionType.Sell
    with pytest.raises(ValueError):
        calculate_transaction_type("INVALID")


def test_calculate_order_type():
    assert calculate_order_type("stoploss") == OrderType.StopLossLimit
    assert calculate_order_type("market") == OrderType.Market
    assert calculate_order_type("limit") == OrderType.Limit
    with pytest.raises(ValueError):
        calculate_order_type("INVALID")


def test_calculate_product_type():
    assert calculate_product_type("NRML") == ProductType.Normal
    assert calculate_product_type("MIS") == ProductType.Intraday
    assert calculate_product_type("CNC") == ProductType.Delivery
    with pytest.raises(ValueError):
        calculate_product_type("INVALID")


def test_get_order_status(user_details, mock_alice_blue):
    mock_alice_instance = mock_alice_blue.return_value
    mock_alice_instance.get_order_history.return_value = {"Status": "rejected"}

    alice = create_alice_obj(user_details["Broker"])
    result = get_order_status(alice, "test_order_id")
    assert result == "FAIL"


@pytest.mark.asyncio
async def test_ant_place_orders_for_users(user_details, mock_alice_blue):
    orders_to_place = {
        "strategy": "test_strategy",
        "exchange_token": "123456",
        "qty": 1,
        "product_type": "CNC",
        "transaction_type": "BUY",
        "order_type": "market",
    }

    alice = create_alice_obj(user_details["Broker"])
    alice.async_place_order = MagicMock(return_value={"NOrdNo": "test_order_id"})

    with patch(
        "Executor.ExecutorUtils.BrokerCenter.Brokers.AliceBlue.alice_adapter.get_order_status",
        return_value="PASS",
    ):
        result = await ant_place_orders_for_users(
            orders_to_place, user_details["Broker"]
        )
        assert result["order_id"] == "test_order_id"


def test_ant_modify_orders_for_users(user_details):
    order_details = {
        "username": "test_user",
        "strategy": "test_strategy",
        "exchange_token": "123456",
        "transaction_type": "BUY",
        "order_type": "market",
        "product_type": "CNC",
        "segment": "NSE",
        "limit_prc": 100.0,
        "trigger_prc": None,
    }

    alice = create_alice_obj(user_details["Broker"])
    alice.modify_order = MagicMock()

    with patch(
        "Executor.ExecutorUtils.BrokerCenter.Brokers.AliceBlue.alice_adapter.retrieve_order_id",
        return_value={"order_id": 10},
    ):
        ant_modify_orders_for_users(order_details, user_details["Broker"])
        alice.modify_order.assert_called_once()


def test_ant_create_counter_order():
    trade = {
        "remarks": "test_remarks",
        "token": "123456",
        "Trantype": "B",
        "Pcode": "CNC",
        "Qty": "10",
    }

    result = ant_create_counter_order(trade, {})
    assert result["strategy"] == get_strategy_name_from_trade_id(trade["remarks"])
    assert result["signal"] == get_signal_from_trade_id(trade["remarks"])


def test_ant_create_hedge_counter_order():
    trade = {
        "remarks": "test_remarks",
        "token": "123456",
        "Trantype": "B",
        "Pcode": "CNC",
        "Qty": "10",
    }

    result = ant_create_hedge_counter_order(trade, {})
    assert result["strategy"] == get_strategy_name_from_trade_id(trade["remarks"])
    assert result["signal"] == get_signal_from_trade_id(trade["remarks"])


def test_ant_create_cancel_orders(user_details):
    trade = {"Nstordno": "test_order_no"}

    alice = create_alice_obj(user_details["Broker"])
    alice.cancel_order = MagicMock()

    ant_create_cancel_orders(trade, user_details)
    alice.cancel_order.assert_called_once_with(trade["Nstordno"])


def test_process_alice_ledger():
    with patch("pandas.read_excel") as mock_read_excel:
        mock_df = MagicMock()
        mock_read_excel.return_value = mock_df
        mock_df.dropna.return_value = mock_df
        mock_df.iloc = MagicMock()
        mock_df.iloc[0] = mock_df
        mock_df.notna.return_value = [True] * len(mock_df.columns)

        result = process_alice_ledger("test_path")
        assert result is not None


def test_calculate_alice_net_values():
    categorized_dfs = {
        "Deposits": pd.DataFrame({"Debit": [100], "Credit": [50]}),
        "Withdrawals": pd.DataFrame({"Debit": [200], "Credit": [100]}),
    }

    result = calculate_alice_net_values(categorized_dfs)
    assert result == {"Deposits": 50, "Withdrawals": 100}


def test_fetch_open_orders(user_details, mock_alice_blue):
    mock_alice_instance = mock_alice_blue.return_value
    mock_alice_instance.get_netwise_positions.return_value = []

    result = fetch_open_orders(user_details["Broker"])
    assert result == []


def test_get_alice_pnl(mock_alice_blue):
    mock_alice_instance = mock_alice_blue.return_value
    mock_alice_instance.get_netwise_positions.return_value = [{"MtoM": "100.0"}]

    result = get_alice_pnl("AliceBlue")
    assert result == 100.0


def test_get_margin_utilized():
    with patch(
        "Executor.ExecutorUtils.BrokerCenter.Brokers.AliceBlue.alice_adapter.discord_admin_bot"
    ) as mock_discord_admin_bot:
        get_margin_utilized({})
        mock_discord_admin_bot.assert_called_once_with(
            "get_order_margin for alice blue has not been implemented yet"
        )


def test_get_broker_payin():
    with patch(
        "Executor.ExecutorUtils.BrokerCenter.Brokers.AliceBlue.alice_adapter.discord_admin_bot"
    ) as mock_discord_admin_bot:
        get_broker_payin({})
        mock_discord_admin_bot.assert_called_once_with(
            "get_broker_payin for alice blue has not been implemented yet"
        )
