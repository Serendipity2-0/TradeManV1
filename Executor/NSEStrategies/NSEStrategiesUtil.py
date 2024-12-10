"""
This module serves as the main entry point for NSE strategy functionality.
It imports and exposes functions from the modularized strategy modules.
"""

# Re-export all models
from .strategy_models import (
    EntryParams,
    ExitParams,
    ExtraInformation,
    GeneralParams,
    StrategyInfo,
    TodayOrder,
    MarketInfoParams,
    StrategyBase,
)

# Re-export all database functions
from .strategy_db import (
    load_strategy_from_db,
    fetch_strategy_users,
    update_qty_user_mongodb,
    update_signal_mongodb,
    update_next_trade_id_mongodb,
    get_strategy_name_from_trade_id,
    fetch_qty_amplifier,
    fetch_strategy_amplifier,
)

# Re-export all utility functions
from .strategy_utils import (
    get_previous_dates,
    assign_trade_id,
    calculate_stoploss,
    calculate_multipler_stoploss,
    calculate_priceref_stoploss,
    calculate_trigger_price,
    calculate_transaction_type_sl,
    calculate_target,
    get_signal_from_trade_id,
    get_order_mode,
    get_transaction_type,
    get_token_from_info,
    determine_expiry_index,
    round_strike_prc,
    get_strike_step,
    calculate_current_atm_strike_prc,
    get_hedge_strikeprc,
    get_square_off_transaction,
    get_option_type,
    get_hedge_option_type,
    get_transaction_type_from_prediction,
)

# Re-export everything for backward compatibility
__all__ = [
    # Models
    'EntryParams',
    'ExitParams',
    'ExtraInformation',
    'GeneralParams',
    'StrategyInfo',
    'TodayOrder',
    'MarketInfoParams',
    'StrategyBase',
    
    # Database functions
    'load_strategy_from_db',
    'fetch_strategy_users',
    'update_qty_user_mongodb',
    'update_signal_mongodb',
    'update_next_trade_id_mongodb',
    'get_strategy_name_from_trade_id',
    'fetch_qty_amplifier',
    'fetch_strategy_amplifier',
    
    # Utility functions
    'get_previous_dates',
    'assign_trade_id',
    'calculate_stoploss',
    'calculate_multipler_stoploss',
    'calculate_priceref_stoploss',
    'calculate_trigger_price',
    'calculate_transaction_type_sl',
    'calculate_target',
    'get_signal_from_trade_id',
    'get_order_mode',
    'get_transaction_type',
    'get_token_from_info',
    'determine_expiry_index',
    'round_strike_prc',
    'get_strike_step',
    'calculate_current_atm_strike_prc',
    'get_hedge_strikeprc',
    'get_square_off_transaction',
    'get_option_type',
    'get_hedge_option_type',
    'get_transaction_type_from_prediction',
]
