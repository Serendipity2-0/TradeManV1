import os
import sys
from dotenv import load_dotenv
import pytest
from unittest.mock import patch, MagicMock
import math
import logging


# Add the necessary path
DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

# Load environment variables
ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

# Import functions from the module
from Executor.ExecutorUtils.OrderCenter.OrderCenterUtils import (
    calculate_qty_for_strategies,
    modify_orders_for_strategy,
    retrieve_order_id,
)

# Configure logger to display debug output during tests
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


@pytest.fixture
def sample_data():
    return {
        "strategy_users": [
            {
                "Broker": {"BrokerUsername": "user1", "BrokerName": "broker1"},
                "Tr_No": "123",
                "Strategies": {"test_strategy": {"Qty": 10}},
            }
        ],
        "order_details": [
            {"strategy": "test_strategy", "trade_id": "1", "order_mode": "Normal"}
        ],
        "order_with_avg_sl_points": {
            "capital": 100000,
            "risk": 2,
            "avg_sl_points": 10,
            "lot_size": 25,
            "qty_amplifier": 5,
            "strategy_amplifier": 10,
        },
        "order_without_avg_sl_points": {
            "capital": 100000,
            "risk": 2,
            "avg_sl_points": None,
            "lot_size": 25,
            "qty_amplifier": None,
            "strategy_amplifier": None,
        },
    }


def test_calculate_qty_basic():
    # Test with basic input values
    result = calculate_qty_for_strategies(
        capital=10000, risk=1, avg_sl_points=10, lot_size=100
    )
    assert result == 100  # Expected quantity for basic scenario


def test_calculate_qty_with_qty_amplifier():
    # Test with a quantity amplifier
    result = calculate_qty_for_strategies(
        capital=10000, risk=1, avg_sl_points=10, lot_size=100, qty_amplifier=10
    )
    expected_quantity = math.ceil(((10000 * 0.01) / 10) * 1.1 / 100) * 100
    assert result == expected_quantity  # Expected quantity adjusted by 10%


def test_calculate_qty_with_strategy_amplifier():
    # Test with a strategy amplifier
    result = calculate_qty_for_strategies(
        capital=10000, risk=1, avg_sl_points=10, lot_size=100, strategy_amplifier=20
    )
    expected_quantity = math.ceil(((10000 * 0.01) / 10) * 1.2 / 100) * 100
    assert result == expected_quantity  # Expected quantity adjusted by 20%


def test_calculate_qty_no_avg_sl_points():
    # Define parameters
    capital = 10000  # Total capital available
    risk = 1  # 1% of capital to be risked
    lot_size = 50  # Size of each lot

    # Call the function
    result = calculate_qty_for_strategies(
        capital=capital, risk=risk, avg_sl_points=None, lot_size=lot_size
    )

    # Calculate the expected quantity
    qty_multiplier = 1  # No quantity amplifier provided
    strategy_multiplier = 1  # No strategy amplifier provided

    # Adjusted risk percentage
    adjusted_risk_percentage = risk / (qty_multiplier * strategy_multiplier)

    # Calculate the amount of capital to be risked
    risked_capital = capital * (adjusted_risk_percentage / 100)

    # Correct calculation of number of lots
    # Capital risked divided by lot size gives the number of lots
    number_of_lots = risked_capital / lot_size

    # Expected quantity is the number of lots rounded up to the nearest lot size
    expected_quantity = math.ceil(number_of_lots) * lot_size
    print(f"Expected quantity: {expected_quantity}")
    print(f"Result: {result}")
    # Assert that the result matches the expected quantity
    assert (
        result == expected_quantity
    ), f"Expected {expected_quantity}, but got {result}"


def test_calculate_qty_division_by_zero():
    # Test to handle division by zero
    result = calculate_qty_for_strategies(
        capital=10000, risk=0, avg_sl_points=10, lot_size=100
    )
    assert result == 0  # Division by zero should return 0


def test_calculate_qty_zero_avg_sl_points():
    # Test with zero avg_sl_points to simulate division by zero
    result = calculate_qty_for_strategies(
        capital=10000, risk=1, avg_sl_points=0, lot_size=100
    )
    assert result == 0  # Division by zero should return 0


def test_calculate_qty_general_error():
    # Test with invalid input causing a general error
    result = calculate_qty_for_strategies(
        capital="invalid", risk=1, avg_sl_points=10, lot_size=100
    )
    assert result == 0  # Invalid input should cause general error and return 0


@patch(
    "Executor.ExecutorUtils.OrderCenter.OrderCenterUtils.fetch_user_credentials_firebase"
)
@patch("Executor.ExecutorUtils.OrderCenter.OrderCenterUtils.modify_order_for_brokers")
def test_modify_orders_for_strategy(
    mock_modify_order_for_brokers, mock_fetch_user_credentials_firebase, sample_data
):
    strategy_users = sample_data["strategy_users"]
    order_details = sample_data["order_details"]

    modify_orders_for_strategy(strategy_users, order_details)
    assert mock_modify_order_for_brokers.called


@patch(
    "Executor.ExecutorUtils.OrderCenter.OrderCenterUtils.fetch_strategy_details_for_user"
)
def test_retrieve_order_id(mock_fetch_strategy_details_for_user):
    mock_fetch_strategy_details_for_user.return_value = {
        "test_strategy": {
            "TradeState": {
                "orders": [
                    {
                        "order_id": "1",
                        "exchange_token": 100,
                        "trade_id": "1EX",
                        "qty": 10,
                    },
                    {
                        "order_id": "2",
                        "exchange_token": 200,
                        "trade_id": "2EX",
                        "qty": 20,
                    },
                ]
            }
        }
    }

    account_name = "user1"
    strategy = "test_strategy"
    exchange_token = 100

    result = retrieve_order_id(account_name, strategy, exchange_token)
    assert result == {"1": 10}
