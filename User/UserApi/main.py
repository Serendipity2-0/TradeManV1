"""
Main FastAPI application entry point.
"""

import uvicorn
from fastapi.openapi.docs import get_swagger_ui_html
import os, sys
from fastapi.middleware.cors import CORSMiddleware
import json
from datetime import date
from fastapi import FastAPI, HTTPException, Query, APIRouter, Body, Path
from typing import Optional, Dict, Any, List

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

from User.UserApi import schemas
from User.UserUtils.auth_api_utils import (
    check_credentials,
    store_profile_data,
    store_broker_data,
    store_accounts_data,
    store_strategies_data,
    update_tr_no,
    merge_and_register_user,
    get_user_profile,
)
from User.UserUtils.portfolio_api_utils import (
    get_monthly_returns_data as monthly_returns_data,
    get_weekly_cumulative_returns_data as weekly_cummulative_returns_data,
    calculate_strategy_statistics as strategy_statistics,
)
from User.UserUtils.transaction_api_utils import (
    get_individual_strategy_data as individual_strategy_data,
    strategy_graph_data,
    get_broker_bank_transactions_data as broker_bank_transactions_data,
    get_users_db_holdings as get_users_holdings,
)
from User.UserUtils.strategy_api_utils import (
    get_strategy_params,
    modify_strategy_params,
    update_market_info_params,
    get_market_info_params,
    update_strategy_qty_amplifier,
    get_user_risk_params,
    update_user_risk_params,
    get_strategy_list,
    get_complete_strategy_list,
    fetch_users_for_strategy,
    get_order_modes,
    get_qty_calculation_mode,
    fetch_today_order,
    fetch_list_of_nse_instruments,
    fetch_tradingsymbol_by_name,
    get_strategies_for_user,
)
from User.UserUtils.admin_api_utils import (
    calculate_aum as get_aum_from_firebase,
    get_total_base_capital as get_total_base_capital_from_firebase,
    calculate_active_users_data as get_active_users_data_from_firebase,
)
from User.UserUtils.userapi_utils import (
    get_next_trader_number,
    get_user_segments,
)
from User.UserUtils.debt_api_utils import (
    import_transactions,
    
)

"""
This is the main API for the user application.
It defines the routes for the user application and includes the router for the user API.
The main function is called when the application is run.

To run the application, you can use the following command:
python main.py

In this script we create a route and include the schema required for that route.
Then we use the data from the user and pass it to function which are in app.py
"""

from User.UserApi.app import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8082)
