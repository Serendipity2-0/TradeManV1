"""
Test script for MidTerm strategy.
Uses configurations from test_midterm_config.py for easier maintenance.
"""

import pandas as pd
import numpy as np
from unittest.mock import patch, AsyncMock, MagicMock
import asyncio
from test_midterm_config import (
    TEST_USER,
    TEST_STRATEGY,
    TEST_DATA,
    HOLDINGS_COLUMNS,
    MOCK_ORDER_RESPONSE,
    MOCK_ORDER_STATUS,
    MOCK_MONGO_DATA,
    setup_environment,
)
from Executor.NSEStrategies.Equity.MidTerm.MidTerm import manage_holdings_and_place_orders

# Mock classes
class MockKite:
    def ltp(self, token):
        return {str(token): {"last_price": TEST_DATA["mock_ltp"]}}

class MockInstrument:
    def __init__(self):
        # Create a mock DataFrame with required columns
        self._dataframe = pd.DataFrame({
            'name': ['63MOONS'],
            'instrument_token': [123456],
            'exchange_token': [TEST_DATA["mock_exchange_token"]],
            'tradingsymbol': ['63MOONS'],
            'exchange': ['NSE'],
            'segment': ['NSE'],
            'instrument_type': ['EQ'],
            'lot_size': [1],
            'Trading Symbol': ['63MOONS-EQ'],
            'Symbol': ['63MOONS']
        })

    def get_exchange_token_by_name(self, name, segment=None):
        if segment:
            filtered = self._dataframe[
                (self._dataframe['name'] == name) & 
                (self._dataframe['segment'] == segment)
            ]
        else:
            filtered = self._dataframe[self._dataframe['name'] == name]
        
        if not filtered.empty:
            return str(filtered.iloc[0]['exchange_token'])
        return None

    def get_kite_token_by_exchange_token(self, exchange_token, segment=None):
        if segment:
            filtered = self._dataframe[
                (self._dataframe['exchange_token'] == exchange_token) & 
                (self._dataframe['segment'] == segment)
            ]
        else:
            filtered = self._dataframe[self._dataframe['exchange_token'] == exchange_token]
        
        if not filtered.empty:
            return int(filtered.iloc[0]['instrument_token'])
        return None

# Mock functions
def mock_get_primary_account_obj(*args, **kwargs):
    """Mock function to return a mock kite object"""
    return MockKite()

def mock_get_client_by_tr_no(*args, **kwargs):
    """Mock function to return the test user"""
    return TEST_USER.copy()

def mock_update_fields_mongodb(collection, document_id, data, field_key=None):
    """Mock function to simulate MongoDB updates"""
    if field_key in MOCK_MONGO_DATA:
        return True
    return True

def mock_check_symbol_for_erros(*args, **kwargs):
    """Mock function to simulate symbol validation"""
    return True

def mock_fetch_qty_amplifier(*args, **kwargs):
    """Mock function to return quantity amplifier"""
    return TEST_DATA["mock_qty_amplifier"]

def mock_fetch_strategy_amplifier(*args, **kwargs):
    """Mock function to return strategy amplifier"""
    return TEST_DATA["mock_strategy_amplifier"]

def mock_place_order_single_user_sync(users, order_details):
    """Mock function to simulate synchronous order placement"""
    return [MOCK_ORDER_STATUS]

def mock_reload_strategy(*args, **kwargs):
    """Mock function to return the mock strategy"""
    return TEST_STRATEGY

def main():
    """Main test function"""
    # Set up environment
    setup_environment()

    # Create empty holdings DataFrame
    holdings = pd.DataFrame(columns=HOLDINGS_COLUMNS)

    print("Starting test with setup:", TEST_DATA["setup_name"])
    print("Symbol list:", TEST_DATA["setup_symbol_list"])

    # Mock the strategy base
    TEST_STRATEGY.reload_strategy = mock_reload_strategy

    # Create mock instrument instance
    mock_instrument = MockInstrument()

    # Apply mocks
    with patch('Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils.get_primary_account_obj', mock_get_primary_account_obj), \
         patch('Executor.ExecutorUtils.ExeDBUtils.MongoUtils.exemongo_adapter.get_client_by_tr_no', mock_get_client_by_tr_no), \
         patch('Executor.ExecutorUtils.ExeDBUtils.MongoUtils.exemongo_adapter.update_fields_mongodb', mock_update_fields_mongodb), \
         patch('Executor.ExecutorUtils.InstrumentCenter.InstrumentCenterUtils.Instrument', return_value=mock_instrument), \
         patch('Executor.ExecutorUtils.EquityCenter.EquityCenterUtils.check_symbol_for_erros', mock_check_symbol_for_erros), \
         patch('Executor.ExecutorUtils.OrderCenter.order_utils.place_order_single_user_sync', mock_place_order_single_user_sync), \
         patch('Executor.NSEStrategies.NSEStrategiesUtil.fetch_qty_amplifier', mock_fetch_qty_amplifier), \
         patch('Executor.NSEStrategies.NSEStrategiesUtil.fetch_strategy_amplifier', mock_fetch_strategy_amplifier), \
         patch('Executor.NSEStrategies.Equity.MidTerm.MidTermConfig.midterm_obj', TEST_STRATEGY):
        
        try:
            manage_holdings_and_place_orders(
                TEST_USER.copy(),  # Pass a copy to prevent modifications to the original
                holdings,
                TEST_DATA["setup_symbol_list"],
                TEST_DATA["setup_name"]
            )
            print("Test completed successfully")
        except Exception as e:
            print(f"Error occurred: {str(e)}")
            import traceback
            print(traceback.format_exc())

if __name__ == "__main__":
    main()
