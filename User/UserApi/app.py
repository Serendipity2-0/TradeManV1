"""
FastAPI application module for user-related endpoints.
"""

import os
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query
from datetime import datetime, date
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from User.UserApi import schemas
from User.UserUtils.userapi_utils import (
    # Admin utilities
    all_users_data,
    get_next_trader_number,
    update_new_client_data_to_db,
    update_next_trader_number,
    log_changes_via_webapp,
    calculate_aum,
    get_total_base_capital,
    calculate_active_users_data,
    
    # Portfolio utilities
    get_user_segments,
    create_portfolio_stats,
    get_monthly_returns_data,
    get_weekly_cumulative_returns_data,
    calculate_strategy_statistics,
    
    # Debt utilities
    read_and_validate_excel_data,
    process_transactions,
    process_acc_transactions,
    update_firebase_data,
    
    # Transaction utilities
    get_individual_strategy_data,
    strategy_graph_data,
    get_broker_bank_transactions_data,
    get_base_capital,
    get_users_db_holdings,
    serialize_transactions,
    
    # Common utilities
    safe_str,
    safe_float,
    safe_int,
    parse_date,
    get_current_week_start_end,
    get_current_month_name,
    get_date_range,
)

# Import authentication utilities
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

# Import constants
from User.UserUtils.portfolio_api_utils import MODE_TO_DB

from fastapi.openapi.docs import get_swagger_ui_html

app = FastAPI()

# Add swagger endpoint
@app.get("/swagger", include_in_schema=False)
def swagger_ui_html():
    """
    Custom Swagger UI endpoint.
    """
    return get_swagger_ui_html(openapi_url="/openapi.json", title="TradeMan API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication endpoints
@app.post("/login")
def login(user_credentials: schemas.LoginUserDetails) -> Dict:
    """
    Login endpoint for user authentication.

    Args:
        user_credentials: User login credentials.

    Returns:
        Dict: Login response with trader number if successful.
    """
    trader_no = check_credentials(user_credentials.dict())
    if trader_no:
        return {"message": "Login successful", "trader_no": trader_no}
    else:
        raise HTTPException(status_code=401, detail="Incorrect email or password")

@app.get("/register/user-id")
def get_user_id() -> Dict:
    """
    Get a new user ID for registration.

    Returns:
        Dict: Response containing the new user ID.
    """
    try:
        user_id = get_next_trader_number()
        return {"message": "User id generated successfully", "user_id": user_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/register/profile")
def register_profile(user_id: str, profile_details: schemas.Profile_) -> Dict:
    """
    Register user profile information.

    Args:
        user_id: User ID.
        profile_details: Profile information.

    Returns:
        Dict: Response containing the stored profile data.
    """
    try:
        response = store_profile_data(user_id, profile_details.dict())
        return {"message": "Profile updated successfully", "response": response}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/register/broker")
def register_broker(user_id: str, broker_details: schemas.Broker_) -> Dict:
    """
    Register user broker information.

    Args:
        user_id: User ID.
        broker_details: Broker information.

    Returns:
        Dict: Response containing the stored broker data.
    """
    try:
        response = store_broker_data(user_id, broker_details.dict())
        return {"message": "Broker updated successfully", "response": response}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/register/accounts")
def register_accounts(user_id: str, account_details: schemas.Accounts_) -> Dict:
    """
    Register user account information.

    Args:
        user_id: User ID.
        account_details: Account information.

    Returns:
        Dict: Response containing the stored account data.
    """
    try:
        response = store_accounts_data(user_id, account_details.dict())
        return {"message": "Accounts updated successfully", "response": response}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/register/strategies")
def register_strategies(user_id: str, strategy_details: schemas.Strategies_) -> Dict:
    """
    Register user strategy information.

    Args:
        user_id: User ID.
        strategy_details: Strategy information.

    Returns:
        Dict: Response containing the stored strategy data.
    """
    try:
        response = store_strategies_data(user_id, strategy_details.dict())
        return {"message": "Strategies updated successfully", "response": response}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/register/tr-no")
def update_trader_number(user_id: str, tr_no_details: schemas.Tr_No_) -> Dict:
    """
    Update user's trader number.

    Args:
        user_id: User ID.
        tr_no_details: Trader number information.

    Returns:
        Dict: Response containing the updated trader number.
    """
    try:
        tr_no = tr_no_details.root
        response = update_tr_no(user_id, tr_no)
        return {"message": "Trader number updated successfully", "response": response}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/register")
def register_user(user_id: str) -> Dict:
    """
    Complete user registration.

    Args:
        user_id: User ID.

    Returns:
        Dict: Response containing the registered user data.
    """
    try:
        return merge_and_register_user(user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# User endpoints
@app.get("/users")
def get_all_users() -> Dict:
    """
    Get all users data.
    """
    return all_users_data()

@app.get("/users/{tr_no}/segments")
def get_segments(tr_no: str) -> List[str]:
    """
    Get segments for a specific user.
    """
    return get_user_segments(tr_no)

@app.get("/users/{tr_no}/portfolio-stats")
def get_portfolio_stats(tr_no: str, mode: str) -> Dict:
    """
    Get portfolio statistics for a specific user.
    """
    try:
        db_name, folder_path = MODE_TO_DB[mode]
        db_path = os.path.join(folder_path, f"{tr_no}_{db_name}.db")
        return create_portfolio_stats(db_path)
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid mode: {mode}")

@app.get("/users/{tr_no}/monthly-returns")
def get_monthly_returns(
    tr_no: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
) -> Dict:
    """
    Get monthly returns for a specific user.
    """
    user_stats = create_portfolio_stats(tr_no)
    if user_stats is None:
        return {"items": [], "total_items": 0}
    return get_monthly_returns_data(user_stats, page, page_size)

@app.get("/users/{tr_no}/weekly-returns")
def get_weekly_returns(
    tr_no: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
) -> Dict:
    """
    Get weekly returns for a specific user.
    """
    user_stats = create_portfolio_stats(tr_no)
    if user_stats is None:
        return {"items": [], "total_items": 0}
    return get_weekly_cumulative_returns_data(user_stats, page, page_size)

@app.get("/users/{tr_no}/strategy/{strategy_name}")
def get_strategy_data(
    tr_no: str,
    strategy_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
) -> Dict:
    """
    Get strategy data for a specific user and strategy.
    """
    return get_individual_strategy_data(tr_no, strategy_name, page, page_size)

@app.get("/users/{tr_no}/strategy/{strategy_name}/graph")
def get_strategy_graph(tr_no: str, strategy_name: str) -> Dict:
    """
    Get strategy graph data for a specific user and strategy.
    """
    return strategy_graph_data(tr_no, strategy_name)

@app.get("/users/{tr_no}/holdings/{mode}")
def get_holdings(tr_no: str, mode: str) -> List[Dict]:
    """
    Get holdings for a specific user and mode.
    """
    return get_users_db_holdings(tr_no, mode)

@app.get("/users/{tr_no}/transactions/{mode}")
def get_transactions(
    tr_no: str,
    mode: str,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
) -> Dict:
    """
    Get transactions for a specific user and mode.
    """
    return get_broker_bank_transactions_data(tr_no, mode, from_date, to_date)

# Admin endpoints
@app.get("/admin/aum")
def get_aum() -> Dict[str, float]:
    """
    Get Assets Under Management.
    """
    return calculate_aum()

@app.get("/admin/base-capital")
def get_base_capital_total() -> float:
    """
    Get total base capital.
    """
    return get_total_base_capital()

@app.get("/admin/active-users")
def get_active_users_data() -> Dict:
    """
    Get data for all active users.
    """
    return calculate_active_users_data()

@app.post("/admin/import-transactions")
def import_transactions(month: Optional[str] = None) -> Dict:
    """
    Import transactions for a specific month.
    """
    if not month:
        month = get_current_month_name()
    
    try:
        filtered_transactions, accounts_df = read_and_validate_excel_data(month)
        total_transactions_imported, errors = process_transactions(filtered_transactions, accounts_df)
        
        return {
            "success": True,
            "transactions_imported": total_transactions_imported,
            "errors": errors,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }

@app.post("/admin/update-client")
def update_client(trader_number: str, user_dict: Dict) -> Dict:
    """
    Update client data.
    """
    try:
        update_new_client_data_to_db(trader_number, user_dict)
        update_next_trader_number()
        return {"success": True}
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }

@app.post("/admin/log-changes")
def log_changes(updated_data: Dict, section_info: Optional[str] = None) -> Dict:
    """
    Log changes made via webapp.
    """
    try:
        log_changes_via_webapp(updated_data, section_info)
        return {"success": True}
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }
