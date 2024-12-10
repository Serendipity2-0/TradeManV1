"""
This module serves as the main entry point for broker-related functionality.
It imports and exposes functions from the modularized broker modules.
"""

import os
import sys
from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

# Import all functionality from modularized files
from .broker_login import (
    all_broker_login,
    update_session_id,
    fetch_active_users,
    fetch_primary_accounts,
    fetch_primary_broker_list,
)

from .broker_orders import (
    place_order_for_brokers,
    modify_order_for_brokers,
    get_today_orders_for_brokers,
    get_today_open_orders_for_brokers,
    create_counter_order_details,
    cancel_normal_orders,
    create_hedge_counter_order_details,
    get_orders_tax,
    get_order_margin,
    get_basket_order_margins,
)

from .broker_utils import (
    fetch_freecash_for_user,
    get_primary_account_obj,
    download_csv_for_brokers,
    fetch_holdings_value_for_user_broker,
    fetch_user_json,
    fetch_user_credentials,
    fetch_strategy_details_for_user,
    fetch_active_strategies_all_users,
    get_broker_pnl,
    get_broker_payin,
    get_avg_prc_broker_key,
    get_order_id_broker_key,
    get_trading_symbol_broker_key,
    get_qty_broker_key,
    get_time_stamp_broker_key,
    get_trade_id_broker_key,
    convert_date_str_to_standard_format,
    convert_to_standard_format,
)

# Re-export all the functions to maintain backward compatibility
__all__ = [
    # Login related functions
    'all_broker_login',
    'update_session_id',
    'fetch_active_users',
    'fetch_primary_accounts',
    'fetch_primary_broker_list',
    
    # Order related functions
    'place_order_for_brokers',
    'modify_order_for_brokers',
    'get_today_orders_for_brokers',
    'get_today_open_orders_for_brokers',
    'create_counter_order_details',
    'cancel_normal_orders',
    'create_hedge_counter_order_details',
    'get_orders_tax',
    'get_order_margin',
    'get_basket_order_margins',
    
    # Utility functions
    'fetch_freecash_for_user',
    'get_primary_account_obj',
    'download_csv_for_brokers',
    'fetch_holdings_value_for_user_broker',
    'fetch_user_json',
    'fetch_user_credentials',
    'fetch_strategy_details_for_user',
    'fetch_active_strategies_all_users',
    'get_broker_pnl',
    'get_broker_payin',
    'get_avg_prc_broker_key',
    'get_order_id_broker_key',
    'get_trading_symbol_broker_key',
    'get_qty_broker_key',
    'get_time_stamp_broker_key',
    'get_trade_id_broker_key',
    'convert_date_str_to_standard_format',
    'convert_to_standard_format',
]
