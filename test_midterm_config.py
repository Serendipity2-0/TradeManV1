"""
Configuration file for MidTerm strategy testing.
Contains all test-related configurations, mock data, and environment settings.
"""

import os
from Executor.NSEStrategies.strategy_models import (
    StrategyBase,
    EntryParams,
    ExitParams,
    ExtraInformation,
    GeneralParams,
    MarketInfoParams,
)

# Environment Variables
ENV_VARS = {
    "PYTHONPATH": "/Users/omkar/Desktop/TradeManV1",
    "TRADE_MODE": "PAPER",
    "USR_TRADELOG_EQUITY_DB_FOLDER": "Data/UserSQLDB",
    "MONGO_STRATEGY_COLLECTION": "strategies",
    "MONGO_USER_COLLECTION": "clients",
    "MONGO_ADMIN_COLLECTION": "v1admin",
    "PRIMARY_BROKER": "PAPER"
}

# Test User Configuration (Based on actual MongoDB schema)
TEST_USER = {
    "_id": "TEST001",
    "Accounts": {
        "CurrentBaseCapital": 43281,
        "CurrentWeekCapital": 0,
        "Equity": {
            "CapitalAllocation": 100,
            "Equity_AccountValue": 41252,
            "Equity_FreeCash": 20586,
            "Equity_Holdings": 20666
        },
        "Portfolio": {
            "Portfolio_AccountValue": 41252,
            "Portfolio_FreeCash": 20586,
            "Portfolio_Holdings": 20666
        }
    },
    "Active": True,
    "Broker": {
        "ApiKey": "test_api_key",
        "ApiSecret": "test_secret",
        "BrokerName": "PAPER",
        "BrokerPassword": "test_password",
        "BrokerUsername": "testuser",
        "SessionId": "test_session",
        "TotpAccess": "test_totp"
    },
    "Profile": {
        "Name": "Test User",
        "Email": "test@example.com",
        "PhoneNumber": "+1234567890"
    },
    "Strategies": {
        "Equity": {
            "MidTerm": {
                "AllocationPercent": 50,
                "Mid_tfMomentum": {
                    "AllocationPercent": 100,
                    "Active": True,
                    "Qty": 1,
                    "TradeState": {
                        "orders": []
                    }
                }
            }
        }
    },
    "Tr_No": "TEST001",
    "document_id": "TEST001"
}

# Test Strategy Configuration (Based on actual MongoDB schema)
TEST_STRATEGY = StrategyBase(
    Description="Stocks to buy for MidTerm and is triggered once a week",
    EntryParams=EntryParams(
        EntryTime="09:20:00",
        SLMultiplier=18
    ),
    ExitParams=ExitParams(
        RiskPerTrade=18,
        SLType="FixedSL",
        SqroffTime="15:05:00"
    ),
    ExtraInformation=ExtraInformation(
        QtyCalc="DuringEntry",
        StocksPerStrategy=3,
        TFEMALargeValue=200,
        TFEMAMarketCapThreshold=999,
        TFEMAMediumValue=63,
        TFEMAROEThreshold=15,
        TFEMARSIUpperThreshold=55,
        TFEMASMAValue=20,
        TFEMAShortValue=9,
        TFEMASmallValue=21,
        TFEMAVolumeMultiplier=2,
        TFMomentumEMAThreshold=200,
        TFMomentumGrossProfitGrowth=1000000000,
        TFMomentumNetIncome=100000000,
        TFMomentumRSILowerThreshold=50,
        TFMomentumRSIUpperThreshold=55,
        TFMomentumSMAValue=20,
        TFMomentumTotalRevenue=1000000000
    ),
    GeneralParams=GeneralParams(
        ExpiryType="Weekly",
        OrderType="Limit",
        ProductType="CNC",
        SlOrderType="Stoploss",
        SlTransactionType="SELL",
        StrategyType="Equity",
        TimeFrame="SingleEntry",
        TransactionType="BUY"
    ),
    Instruments=["NSE"],
    NextTradeId="MT1",
    StrategyName="MidTerm",
    StrategyPrefix="MT",
    MarketInfoParams=MarketInfoParams(
        OBQtyAmplifier=1,
        OSQtyAmplifier=1,
        TradeView="Bullish"
    )
)

# Test Data Configuration
TEST_DATA = {
    "setup_symbol_list": ["63MOONS"],
    "setup_name": "Mid_tfMomentum",
    "mock_ltp": 100.0,
    "mock_exchange_token": "123456",
    "mock_qty_amplifier": 1.0,
    "mock_strategy_amplifier": 1.0
}

# Holdings DataFrame Columns
HOLDINGS_COLUMNS = [
    "trade_id",
    "trading_symbol",
    "setup",
    "quantity",
    "entry_price",
    "current_price",
    "pnl",
    "status"
]

# Mock Response Templates
MOCK_ORDER_RESPONSE = {
    "status": "success",
    "message": "Order placed successfully",
    "order_id": "TEST123"
}

MOCK_ORDER_STATUS = {
    "user": TEST_USER["Tr_No"],
    "symbol": TEST_DATA["setup_symbol_list"][0],
    "order_status": "PASS",
    "message": "Order placed successfully",
    "trade_id": TEST_STRATEGY.NextTradeId,
    "avg_prc": TEST_DATA["mock_ltp"],
    "qty": 1,
    "setup": TEST_DATA["setup_name"].upper(),
    "tax": 1.0,
    "time_stamp": "2024-12-15 22:00:00"
}

# MongoDB Mock Data
MOCK_MONGO_DATA = {
    "quantity_info": {
        "avg_sl_points_or_ltp": TEST_DATA["mock_ltp"],
        "qty_amplifier": TEST_DATA["mock_qty_amplifier"],
        "strategy_amplifier": TEST_DATA["mock_strategy_amplifier"],
        "asset_segment": "Equity",
        "asset_term": "MidTerm",
        "num_stocks": 3
    },
    "signals": {
        "order_details": [{
            "strategy": "MidTerm",
            "signal": "Long",
            "base_symbol": "63MOONS",
            "exchange_token": TEST_DATA["mock_exchange_token"],
            "transaction_type": "BUY",
            "order_type": "Limit",
            "product_type": "CNC",
            "order_mode": "MainEntry",
            "trade_id": TEST_STRATEGY.NextTradeId,
            "limit_prc": TEST_DATA["mock_ltp"],
            "trade_mode": "PAPER",
            "setup": TEST_DATA["setup_name"].upper()
        }],
        "trade_id": TEST_STRATEGY.NextTradeId,
        "timestamp": "2024-12-15T22:00:00"
    }
}

# Function to set environment variables
def setup_environment():
    """Set up environment variables for testing"""
    for key, value in ENV_VARS.items():
        os.environ[key] = value
