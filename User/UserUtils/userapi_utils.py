"""
Main API utility module that coordinates functionality between specialized utility modules.
"""

import os
import sys
from dotenv import load_dotenv
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.ExeUtils import (
    EQUITY_STRATEGY_LIST,
    DERIVATIVES_STRATEGY_LIST,
    DEBT_STRATEGY_LIST,
)

# Import specialized utility modules
from .admin_api_utils import (
    all_users_data,
    get_next_trader_number,
    update_new_client_data_to_db,
    update_next_trader_number,
    log_changes_via_webapp,
    calculate_aum,
    get_total_base_capital,
    calculate_active_users_data,
)
from .portfolio_api_utils import (
    get_user_segments,
    create_portfolio_stats,
    get_monthly_returns_data,
    get_weekly_cumulative_returns_data,
    calculate_strategy_statistics,
)
from .debt_api_utils import (
    read_and_validate_excel_data,
    process_transactions,
    process_acc_transactions,
    update_firebase_data,
)
from .transaction_api_utils import (
    get_individual_strategy_data,
    strategy_graph_data,
    get_broker_bank_transactions_data,
    get_base_capital,
    get_users_db_holdings,
    serialize_transactions,
)
from .common_utils import (
    safe_str,
    safe_float,
    safe_int,
    parse_date,
    get_current_week_start_end,
    get_current_month_name,
    get_date_range,
)

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

logger = LoggerSetup()

# Re-export all utility functions for backward compatibility
__all__ = [
    # Admin utilities
    'all_users_data',
    'get_next_trader_number',
    'update_new_client_data_to_db',
    'update_next_trader_number',
    'log_changes_via_webapp',
    'calculate_aum',
    'get_total_base_capital',
    'calculate_active_users_data',
    
    # Portfolio utilities
    'get_user_segments',
    'create_portfolio_stats',
    'get_monthly_returns_data',
    'get_weekly_cumulative_returns_data',
    'calculate_strategy_statistics',
    
    # Debt utilities
    'read_and_validate_excel_data',
    'process_transactions',
    'process_acc_transactions',
    'update_firebase_data',
    
    # Transaction utilities
    'get_individual_strategy_data',
    'strategy_graph_data',
    'get_broker_bank_transactions_data',
    'get_base_capital',
    'get_users_db_holdings',
    'serialize_transactions',
    
    # Common utilities
    'safe_str',
    'safe_float',
    'safe_int',
    'parse_date',
    'get_current_week_start_end',
    'get_current_month_name',
    'get_date_range',
]
