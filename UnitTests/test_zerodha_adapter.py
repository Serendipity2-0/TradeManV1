import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv
import pandas as pd

# from kiteconnect import KiteConnect


# Add the necessary path
DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

# Load environment variables
ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

# Import the functions to test
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

#  from Executor.Strategies.StrategiesUtil import (
#     get_strategy_name_from_trade_id,
#     get_signal_from_trade_id,
#     calculate_transaction_type_sl,
# )
# from Executor.ExecutorUtils.NotificationCenter.Discord.discord_adapter import (
#     discord_bot,
# )

from Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter import (
    create_kite_obj,
    zerodha_fetch_free_cash,
    get_csv_kite,
    fetch_zerodha_holdings_value,
    simplify_zerodha_order,
    zerodha_todays_tradebook,
    calculate_transaction_type,
    calculate_order_type,
    calculate_product_type,
    calculate_segment_type,
    get_avg_prc,
    get_order_status,
    get_order_details,
    # kite_place_orders_for_users,
    kite_modify_orders_for_users,
    kite_create_sl_counter_order,
    kite_create_cancel_order,
    kite_create_hedge_counter_order,
    process_kite_ledger,
    calculate_kite_net_values,
    fetch_open_orders,
    get_zerodha_pnl,
    get_order_tax,
    get_margin_utilized,
    get_broker_payin,
)

# Set up the logger
logger = LoggerSetup()

# Mock user details for testing
mock_user_details = {
    "ApiKey": "test_api_key",
    "SessionId": "test_session_id",
    "BrokerUsername": "test_username",
}


@pytest.fixture
def mock_kite():
    kite = MagicMock()
    kite.margins.return_value = {"equity": {"cash": 10000}}
    kite.instruments.return_value = [
        {"exchange_token": "12345", "tradingsymbol": "TEST"}
    ]
    kite.holdings.return_value = [{"average_price": 100, "quantity": 10}]
    kite.orders.return_value = [
        {
            "status": "COMPLETE",
            "average_price": 100,
            "quantity": 10,
            "order_timestamp": "2023-01-01 00:00:00",
            "tag": "test_tag",
        }
    ]
    kite.order_history.return_value = [{"status": "COMPLETE", "average_price": 100}]
    return kite


@patch(
    "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter.KiteConnect",
    autospec=True,
)
def test_create_kite_obj(mock_kiteconnect):
    kite = create_kite_obj(
        api_key=mock_user_details["ApiKey"], access_token=mock_user_details["SessionId"]
    )
    assert kite is not None


@patch(
    "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter.KiteConnect",
    autospec=True,
)
def test_zerodha_fetch_free_cash(mock_kiteconnect, mock_kite):
    mock_kiteconnect.return_value = mock_kite
    free_cash = zerodha_fetch_free_cash(mock_user_details)
    assert free_cash == 10000


@patch(
    "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter.KiteConnect",
    autospec=True,
)
def test_get_csv_kite(mock_kiteconnect, mock_kite):
    mock_kiteconnect.return_value = mock_kite
    instrument_df = get_csv_kite({"Broker": mock_user_details})
    assert instrument_df is not None
    assert instrument_df["exchange_token"].iloc[0] == "12345"


@patch(
    "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter.KiteConnect",
    autospec=True,
)
def test_fetch_zerodha_holdings_value(mock_kiteconnect, mock_kite):
    mock_kiteconnect.return_value = mock_kite
    holdings_value = fetch_zerodha_holdings_value({"Broker": mock_user_details})
    assert holdings_value == 1000


def test_simplify_zerodha_order():
    order_detail = {
        "tradingsymbol": "TESTFUT",
        "average_price": 100,
        "quantity": 10,
        "order_timestamp": "2023-01-01 00:00:00",
        "tag": "test_tag_entry",
        "transaction_type": "BUY",
    }
    simplified_order = simplify_zerodha_order(order_detail)
    assert simplified_order is not None, "simplify_zerodha_order returned None"
    assert simplified_order["trade_id"] == "test_tag_entry"
    assert simplified_order["avg_price"] == 100


@patch(
    "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter.KiteConnect",
    autospec=True,
)
def test_zerodha_todays_tradebook(mock_kiteconnect, mock_kite):
    mock_kiteconnect.return_value = mock_kite
    mock_kite.orders.return_value = [
        {
            "status": "COMPLETE",
            "average_price": 100,
            "quantity": 10,
            "order_timestamp": "2023-01-01 00:00:00",
            "tag": "test_tag",
        }
    ]
    trades = zerodha_todays_tradebook(mock_user_details)
    assert trades is not None, "zerodha_todays_tradebook returned None"
    assert trades[0]["status"] == "COMPLETE"


def test_calculate_transaction_type():
    kite = MagicMock()
    kite.TRANSACTION_TYPE_BUY = "BUY"
    transaction_type = calculate_transaction_type(kite, "BUY")
    assert transaction_type == kite.TRANSACTION_TYPE_BUY


def test_calculate_order_type():
    kite = MagicMock()
    kite.ORDER_TYPE_MARKET = "MARKET"
    order_type = calculate_order_type(kite, "market")
    assert order_type == kite.ORDER_TYPE_MARKET


def test_calculate_product_type():
    kite = MagicMock()
    kite.PRODUCT_NRML = "NRML"
    product_type = calculate_product_type(kite, "NRML")
    assert product_type == kite.PRODUCT_NRML


def test_calculate_segment_type():
    kite = MagicMock()
    kite.EXCHANGE_NSE = "NSE"
    segment_type = calculate_segment_type(kite, "NSE")
    assert segment_type == kite.EXCHANGE_NSE


@patch(
    "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter.KiteConnect",
    autospec=True,
)
def test_get_avg_prc(mock_kiteconnect, mock_kite):
    mock_kiteconnect.return_value = mock_kite
    avg_price = get_avg_prc(mock_kite, 12345)
    assert avg_price == 100


@patch(
    "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter.KiteConnect",
    autospec=True,
)
def test_get_order_status(mock_kiteconnect, mock_kite):
    mock_kiteconnect.return_value = mock_kite
    mock_kite.order_history.return_value = [
        {"status": "COMPLETE", "average_price": 100}
    ]
    status = get_order_status(mock_kite, 12345)
    assert status == "COMPLETE"


@patch(
    "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter.KiteConnect",
    autospec=True,
)
@patch(
    "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter.KiteConnect",
    autospec=True,
)
def test_get_order_details(mock_kiteconnect):
    # Create a mock instance for KiteConnect
    mock_kite = mock_kiteconnect.return_value

    # Set the return value for the orders method
    mock_kite.orders.return_value = [
        {
            "strategy": "ExpiryTrader",
            "signal": "SH",
            "base_symbol": "FINNIFTY",
            "exchange_token": "55215",
            "transaction_type": "BUY",
            "order_type": "Market",
            "product_type": "MIS",
            "order_mode": "HO",
            "trade_id": "ET223_SH_HO_EN",
            "trade_mode": "LIVE",
        },
        {
            "strategy": "ExpiryTrader",
            "signal": "SH",
            "base_symbol": "FINNIFTY",
            "exchange_token": "55219",
            "transaction_type": "SELL",
            "order_type": "Market",
            "product_type": "MIS",
            "order_mode": "MO",
            "trade_id": "ET223_SH_MO_EN",
            "trade_mode": "LIVE",
        },
        {
            "strategy": "ExpiryTrader",
            "signal": "SH",
            "base_symbol": "FINNIFTY",
            "exchange_token": "55219",
            "transaction_type": "BUY",
            "order_type": "Stoploss",
            "product_type": "MIS",
            "limit_prc": 0.1,
            "trigger_prc": -0.9,
            "order_mode": "SL",
            "trade_id": "ET223_SH_SL_EX",
            "trade_mode": "LIVE",
        },
    ]

    # Call the function under test
    orders = get_order_details(mock_user_details)

    # Debug output
    print("Orders returned by get_order_details:", orders)

    # Perform assertions
    assert orders is not None, "get_order_details returned None"
    assert len(orders) == 3, "Unexpected number of orders returned"
    assert orders[0]["strategy"] == "ExpiryTrader"
    assert orders[0]["transaction_type"] == "BUY"
    assert orders[0]["order_type"] == "Market"
    assert orders[1]["transaction_type"] == "SELL"
    assert orders[2]["order_type"] == "Stoploss"


@patch(
    "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter.KiteConnect",
    autospec=True,
)
def test_kite_modify_orders_for_users(mock_kiteconnect, mock_kite):
    mock_kiteconnect.return_value = mock_kite
    order_details = {
        "username": "test_user",
        "strategy": "test_strategy",
        "exchange_token": "12345",
        "limit_prc": 100,
        "trigger_prc": 105,
    }
    mock_kite.modify_order.return_value = {"status": "SUCCESS"}
    kite_modify_orders_for_users(order_details, mock_user_details)
    mock_kite.modify_order.assert_called()


@patch(
    "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter.KiteConnect",
    autospec=True,
)
def test_kite_create_sl_counter_order(mock_kiteconnect, mock_kite):
    mock_kiteconnect.return_value = mock_kite
    trade = {
        "tag": "test_tag",
        "instrument_token": "12345",
        "transaction_type": "BUY",
        "product": "NRML",
        "quantity": 1,
    }
    mock_kite.place_order.return_value = {"order_mode": "Counter"}
    counter_order = kite_create_sl_counter_order(trade, mock_user_details)
    assert counter_order is not None, "kite_create_sl_counter_order returned None"
    assert counter_order["order_mode"] == "Counter"


@patch(
    "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter.KiteConnect",
    autospec=True,
)
def test_kite_create_cancel_order(mock_kiteconnect, mock_kite):
    mock_kiteconnect.return_value = mock_kite
    trade = {
        "order_id": 12345,
    }
    kite_create_cancel_order(trade, mock_user_details)
    mock_kite.cancel_order.assert_called()


@patch(
    "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter.KiteConnect",
    autospec=True,
)
def test_kite_create_hedge_counter_order(mock_kiteconnect, mock_kite):
    mock_kiteconnect.return_value = mock_kite
    trade = {
        "tag": "test_tag",
        "instrument_token": "12345",
        "transaction_type": "BUY",
        "product": "NRML",
        "quantity": 1,
    }
    mock_kite.place_order.return_value = {"order_mode": "Hedge"}
    hedge_order = kite_create_hedge_counter_order(trade, mock_user_details)
    assert hedge_order is not None, "kite_create_hedge_counter_order returned None"
    assert hedge_order["order_mode"] == "Hedge"


def test_process_kite_ledger():
    ledger_data = pd.DataFrame(
        {
            "particulars": [
                "Funds added using UPI",
                "Net obligation for Equity F&O",
                "AMC for Demat Account",
            ],
            "debit": [0, 1000, 10],
            "credit": [100, 0, 0],
        }
    )
    ledger_data.to_csv("test_ledger.csv", index=False)
    categorized_dfs = process_kite_ledger("test_ledger.csv")
    assert "Deposits" in categorized_dfs
    assert "Trades" in categorized_dfs
    assert "Charges" in categorized_dfs


def test_calculate_kite_net_values():
    categorized_dfs = {
        "Deposits": pd.DataFrame({"debit": [0], "credit": [100]}),
        "Trades": pd.DataFrame({"debit": [1000], "credit": [0]}),
        "Charges": pd.DataFrame({"debit": [10], "credit": [0]}),
    }
    net_values = calculate_kite_net_values(categorized_dfs)
    assert net_values["Deposits"] == -100
    assert net_values["Trades"] == 1000
    assert net_values["Charges"] == 10


@patch(
    "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter.KiteConnect",
    autospec=True,
)
def test_fetch_open_orders(mock_kiteconnect, mock_kite):
    mock_kiteconnect.return_value = mock_kite
    mock_kite.orders.return_value = [{"status": "OPEN"}]
    open_orders = fetch_open_orders(mock_user_details)
    assert open_orders is not None, "fetch_open_orders returned None"
    assert open_orders[0]["status"] == "OPEN"


@patch(
    "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter.KiteConnect",
    autospec=True,
)
def test_get_zerodha_pnl(mock_kiteconnect, mock_kite):
    mock_kiteconnect.return_value = mock_kite
    mock_kite.pnl.return_value = {"net": 0}
    pnl = get_zerodha_pnl({"Broker": mock_user_details})
    assert pnl == 0


@pytest.mark.asyncio
@patch(
    "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter.KiteConnect",
    autospec=True,
)
async def test_get_order_tax(mock_kiteconnect, mock_kite):
    mock_kiteconnect.return_value = mock_kite
    order = {
        "exchange_token": "12345",
        "product_type": "NRML",
        "transaction_type": "B",
        "order_type": "market",
        "qty": 1,
    }
    mock_kite.order_tax.return_value = {"tax": 10}
    tax = await get_order_tax(order, mock_user_details, "zerodha")
    assert tax is not None, "get_order_tax returned None"
    assert tax["tax"] == 10


@patch(
    "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter.KiteConnect",
    autospec=True,
)
def test_get_margin_utilized(mock_kiteconnect, mock_kite):
    mock_kiteconnect.return_value = mock_kite
    mock_kite.margins.return_value = {"equity": {"utilized": 1000}}
    margin = get_margin_utilized(mock_user_details)
    assert margin is not None, "get_margin_utilized returned None"
    assert margin["equity"]["utilized"] == 1000


@patch(
    "Executor.ExecutorUtils.BrokerCenter.Brokers.Zerodha.zerodha_adapter.KiteConnect",
    autospec=True,
)
def test_get_broker_payin(mock_kiteconnect, mock_kite):
    mock_kiteconnect.return_value = mock_kite
    payin = get_broker_payin({"Broker": mock_user_details})
    assert payin is not None, "get_broker_payin returned None"
    assert payin == 1000


if __name__ == "__main__":
    pytest.main()
