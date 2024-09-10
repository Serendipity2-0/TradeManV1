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

import schemas
import app
from .userapi_utils import get_next_trader_number

"""
This is the main API for the user application.
It defines the routes for the user application and includes the router for the user API.
The main function is called when the application is run.

To run the application, you can use the following command:
python main.py

In this script we create a route and include the schema required for that route.
Then we use the data from the user and pass it to function which are in app.py
"""


app_fastapi = FastAPI()

app_fastapi.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app_user = APIRouter()
app_admin = APIRouter()


@app_fastapi.get("/swagger", include_in_schema=False)
def overridden_swagger():
    """
    This is the swagger page for the user application.
    It is used to display the API documentation.
    """
    return get_swagger_ui_html(openapi_url="openapi.json", title="Trademan")


@app_user.post("/login")
def login(user_credentials: schemas.LoginUserDetails):
    """
    This is the route for logging in a user.
    It takes a LoginUserDetails object as input and returns a response.
    We are storing the user details in a dictionary and then passing it to the check_credentials function in app.py.
    """
    # Authentication function to check credentials
    trader_no = app.check_credentials(user_credentials)
    if trader_no:
        return {"message": "Login successful", "trader_no": trader_no}
    else:
        raise HTTPException(status_code=401, detail="Incorrect email or password")


@app_user.get("/register/user-id")
def get_user_id():
    """
    This is the route for getting the user id.
    It takes a UserDetails object as input and returns a response.
    We are storing the user details in a dictionary and then passing it to the register_user function in app.py.
    """
    try:
        user_id = get_next_trader_number()
        return {"message": "User id generated successfully", "user_id": user_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app_user.post("/register/profile")
def register_profile(user_id: str, profile_details: schemas.Profile_):
    """
    This is the route for storing the profile data for a new user.
    It takes the profile values as input and stores them in the user_data_collection dictionary.
    We are storing the user details in a dictionary and then passing it to the register_user function in app.py.
    """
    try:
        response = app.store_profile_data(user_id, profile_details.dict())
        return {"message": "Profile updated successfully", "response": response}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app_user.post("/register/active")
def update_active_status(user_id: str, active_details: schemas.Active_):
    """
    This is the route for updating the active status of a user.
    It takes the active status as input and stores it in the user_data_collection dictionary.
    We are storing the user details in a dictionary and then passing it to the register_user function in app.py.
    """
    try:
        active_status = active_details.root
        response = app.store_active_status(user_id, active_status)
        return {"message": "Active status updated successfully", "response": response}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app_user.post("/register/broker")
def register_broker(user_id: str, broker_details: schemas.Broker_):
    """
    This is the route for storing the broker data for a new user.
    It takes the broker values as input and stores them in the user_data_collection dictionary.
    We are storing the user details in a dictionary and then passing it to the register_user function in app.py.
    """
    try:
        response = app.store_broker_data(user_id, broker_details.dict())
        return {"message": "Broker updated successfully", "response": response}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app_user.post("/register/accounts")
def register_accounts(user_id: str, account_details: schemas.Accounts_):
    """
    This is the route for storing the accounts data for a new user.
    It takes the account values and the segments as input and stores them in the user_data_collection dictionary.
    We are storing the user details in a dictionary and then passing it to the register_user function in app.py.
    """
    try:
        response = app.store_accounts_data(user_id, account_details.dict())
        return {"message": "Accounts updated successfully", "response": response}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app_user.post("/register/strategies")
def update_strategies(user_id: str, strategy_details: schemas.Strategies_):
    """
    This is the route for updating the strategies data for a new user.
    It takes the strategies values as input and stores them in the user_data_collection dictionary.
    We are storing the user details in a dictionary and then passing it to the register_user function in app.py.
    """
    try:
        response = app.store_strategies_data(user_id, strategy_details.dict())
        return {"message": "Strategies updated successfully", "response": response}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app_user.post("/register/tr-no")
def update_tr_no(user_id: str, strategy_details: schemas.Tr_No_):
    """
    This is the route for updating the trader number for a new user.
    It takes the trader number as input and stores it in the user_data_collection dictionary.
    We are storing the user details in a dictionary and then passing it to the register_user function in app.py.
    """
    try:
        tr_no = strategy_details.root
        response = app.update_tr_no(user_id, tr_no)
        return {"message": "Trader number updated successfully", "response": response}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app_user.post("/register")
def register_user(user_id: str):
    """
    This is the route for registering a new user.
    It takes a UserDetails object as input and returns a response.
    We are storing the user details in a dictionary and then passing it to the register_user function in app.py.
    """
    try:
        return app.merge_and_register_user(user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app_user.get("/profile-page")
def profile_page(tr_no: str):
    """
    Retrieves the profile page for a specific user by their user ID.

    Args:
    user_id: The unique identifier of the user.

    Returns:
    dict: The user profile information.
    """
    try:
        return app.get_user_profile(tr_no)
    except KeyError:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app_user.get("/portfolio-stats-view")
def portfolio_stats_view(tr_no: str):
    """
    Retrieves the portfolio stats view for a specific user by their user ID.

    Args:
    user_id: The unique identifier of the user.

    Returns:
    dict: The portfolio stats view.
    """
    try:
        return app.get_portfolio_stats(tr_no)
    except KeyError:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app_user.get("/monthly-returns")
def monthly_returns(
    tr_no: str, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)
):
    """
    Retrieves the paginated monthly returns data for a specific user by their user ID.

    Args:
    tr_no: The unique identifier of the user.
    page: The page number (default: 1).
    page_size: The number of items per page (default: 20, max: 100).

    Returns:
    dict: The paginated monthly returns data.
    """
    try:
        monthly_data = app.monthly_returns_data(tr_no, page, page_size)
        total_items = monthly_data["total_items"]
        items = monthly_data["items"]

        # Calculate pagination
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated_items = items[start_index:end_index]

        return {
            "items": paginated_items,
            "total_items": total_items,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_items + page_size - 1) // page_size,
        }
    except KeyError:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app_user.get("/weekly-cummulative-returns")
def weekly_cummulative_returns(
    tr_no: str, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)
):
    """
    Retrieves the paginated weekly cummulative returns data for a specific user by their user ID.

    Args:
    tr_no: The unique identifier of the user.
    page: The page number (default: 1).
    page_size: The number of items per page (default: 20, max: 100).

    Returns:
    dict: The paginated weekly cummulative returns data.
    """
    try:
        weekly_data = app.weekly_cummulative_returns_data(tr_no, page, page_size)
        total_items = weekly_data["total_items"]
        items = weekly_data["items"]

        # Calculate pagination
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated_items = items[start_index:end_index]

        return {
            "items": paginated_items,
            "total_items": total_items,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_items + page_size - 1) // page_size,
        }
    except KeyError:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app_user.get("/individual-strategy-data")
def individual_strategy_performance(
    tr_no: str,
    strategy_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    Retrieves the individual strategy data for a specific user by their user ID and strategy name.

    Args:
    tr_no: The unique identifier of the user.
    strategy_name: The name of the strategy.
    page: The page number (default: 1).
    page_size: The number of items per page (default: 20, max: 100).

    Returns:
    dict: The paginated individual strategy data.
    """
    try:
        strategy_data = app.individual_strategy_data(
            tr_no, strategy_name, page, page_size
        )
        total_items = strategy_data["total_items"]
        items = strategy_data["items"]

        return {
            "items": items.to_dict("records"),  # Convert DataFrame to list of dicts
            "total_items": int(total_items),  # Ensure this is a Python int
            "page": page,
            "page_size": page_size,
            "total_pages": (total_items + page_size - 1) // page_size,
        }
    except KeyError:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app_user.get("/strategy-graph-data")
def strategy_graph_data(tr_no: str, strategy_name: str):
    """
    Retrieves the strategy graph data for a specific user by their user ID and strategy name.

    Args:
        tr_no (str): The user's ID.
        strategy_name (str): The name of the strategy.

    Returns:
        dict: The strategy graph data for the specified user and strategy.
    """
    try:
        graph_data = app.strategy_graph_data(tr_no, strategy_name)
        return graph_data
    except KeyError:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app_user.get("/strategy-statistics")
def get_strategy_statistics(tr_no: str, strategy_name: str):
    """
    Endpoint to retrieve strategy statistics for a specific user's strategy.

    Args:
    tr_no: The unique identifier of the user.
    strategy_name: The name of the strategy.

    Returns:
    dict: The calculated strategy statistics.
    """
    try:
        statistics = app.strategy_statistics(tr_no, strategy_name)

        if statistics is None:
            raise HTTPException(
                status_code=404,
                detail=f"No data found for Strategy {strategy_name} for {tr_no}",
            )

        return statistics

    except KeyError:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app_user.get("/user-broker-transactions")
def user_broker_transactions(
    tr_no: str,
    mode: str,
    page: int = Query(1, ge=1),
    pagesize: int = Query(10, ge=1),
    fromdate: Optional[date] = None,
    todate: Optional[date] = None,
):
    """
    Retrieves the transactions data for a specific user by their user ID, optionally filtering by date and paginating the results.

    Args:
        tr_no: The unique identifier of the user.
        mode: The mode of transactions to retrieve(Debt, Equity, Derivatives).
        page: The page number of results to return.
        pagesize: The number of items per page.
        fromdate: Start date for filtering transactions (YYYY-MM-DD). Defaults to None.
        todate: End date for filtering transactions (YYYY-MM-DD). Defaults to None.

    Returns:
        dict: A dictionary containing the paginated transactions data and the total number of results.
    """
    try:
        transactions_data = app.broker_bank_transactions_data(
            tr_no, mode, fromdate, todate
        )
        total_results = len(
            transactions_data
        )  # Calculate the total number of transactions
        start = (page - 1) * pagesize
        end = start + pagesize
        paginated_data = transactions_data[start:end]

        # Prepare the response data including total results
        return {
            "total_results": total_results,
            "transactions": json.loads(paginated_data.to_json(orient="records")),
        }
    except KeyError:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app_user.get("/user-segments")
def get_user_segments(tr_no: str):
    """
    Fetches the segments of a user.
    """
    return app.get_user_segments(tr_no)


@app_user.get("/users-strategy")
def get_strategies_for_user(tr_no: str):
    """
    Retrieves the users associated with a specific strategy.

    Args:
        tr_no (str): The user's ID.

    Returns:
        list: A list of strategy names associated with the user.

    Raises:
        HTTPException: If there's an error fetching from the database.
    """
    try:
        return app.get_strategies_for_user(tr_no)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app_user.get("/users-holdings")
def get_users_holdings(tr_no: str, mode: str):
    """
    Retrieves the users' equity holdings.

    Args:
        tr_no (str): The user's ID.
        mode (str): The mode of holdings to retrieve.(Equity, Debt, Derivatives)

    Returns:
        list: A list of equity holdings for the user.

    Raises:
        HTTPException: If there's an error fetching from the database.
    """

    try:
        return app.get_users_holdings(tr_no, mode)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app_user.get("/tradestate")
def get_tradestate(tr_no: str, strategy_name: str):
    """
    Retrieves the trade state (holdings with today's date) for a specific user.

    Args:
    tr_no (str): The trader number of the user.

    Returns:
    dict: A dictionary containing the trade state data.
    """
    try:
        trade_state = app.get_tradestate(tr_no, strategy_name)
        return trade_state
    except KeyError:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app_admin.get("/strategy-params/{strategy_name}")
def get_strategy_params(
    strategy_name: str = Path(..., description="Name of the strategy"),
):
    """
    Fetch current parameters for a specific strategy.

    This endpoint retrieves the current parameters for a given strategy from the Firebase database.

    Args:
        strategy_name (str): The name of the strategy to fetch.

    Returns:
        dict: The current parameters for the strategy.

    Raises:
        HTTPException: If there's an error fetching from the database or if the strategy is not found.
    """
    try:
        return app.get_strategy_params(strategy_name)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching strategy parameters: {str(e)}"
        )


@app_admin.put("/strategy-params/{strategy_name}/{section}")
def modify_strategy_params(
    strategy_name: str = Path(..., description="Name of the strategy"),
    section: str = Path(
        ..., description="Section of the strategy parameters to update"
    ),
    updated_params: Dict[str, Any] = Body(
        ..., description="Updated parameters for the strategy section"
    ),
):
    """
    Modify parameters for a specific section of a strategy.
    NOTE:
    1. For variables that are lists, the response should be sent as a list.
        For example, if the section is "Instruments", the response should be sent as a list of instruments.
        {"Instruments": ["NSE", "BSE"]}
    2. If the section is "EntryParams", the response should be sent as a dictionary.
        {"EntryTime": "09:15", "ExitTime": "15:30"}
    3. If the section is "Root-level values", the response should be sent as a dictionary.
        Example: section : Description and request body should be like this
        {"Description": "New Description"}

    This endpoint allows updating the parameters of a specific section for a given strategy.
    It also logs the changes and sends a notification via Discord.

    Args:
        strategy_name (str): The name of the strategy to update.
        section (str): The section of the strategy parameters to update.
        updated_params (Dict[str, Any]): A dictionary containing the updated parameters for the section.

    Returns:
        dict: A message indicating successful update.

    Raises:
        HTTPException: If there's an error updating the database or if the strategy or section is not found.
    """
    try:
        app.modify_strategy_params(strategy_name, section, updated_params)
        return {"message": "Strategy parameters updated successfully!"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error updating strategy parameters: {str(e)}"
        )


@app_admin.put("/market-info-params")
def update_market_info_params(
    updated_market_info: schemas.MarketInfoParams = Body(
        ..., description="Updated market info parameters"
    )
):
    """
    Update market info parameters.

    This endpoint allows updating the market info parameters in the Firebase database.
    It also logs the changes and sends a notification via Discord.

    Args:
        updated_market_info (Dict[str, Any]): A dictionary containing the updated market info parameters.

    Returns:
        dict: A message indicating successful update.

    Raises:
        HTTPException: If there's an error updating the database.
    """
    try:
        app.update_market_info_params(updated_market_info)
        return {"message": "Market info updated successfully!"}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error updating market info: {str(e)}"
        )


@app_admin.get("/market-info-params")
def get_market_info_params():
    """
    Fetch current market info parameters.

    This endpoint retrieves the current market info parameters from the Firebase database.

    Returns:
        dict: The current market info parameters.

    Raises:
        HTTPException: If there's an error fetching from the database.
    """
    try:
        return app.get_market_info_params()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching market info: {str(e)}"
        )


@app_admin.put("/strategy-qty-amplifier")
def update_strategy_qty_amplifier(
    strategy: str = Body(..., description="Strategy name or 'all' for all strategies"),
    amplifier: float = Body(..., description="New StrategyQtyAmplifier value"),
):
    """
    Update StrategyQtyAmplifier for a specific strategy or all strategies.

    Args:
        strategy (str): The name of the strategy to update, or 'all' for all strategies.
        amplifier (float): The new StrategyQtyAmplifier value.

    Returns:
        dict: A message indicating successful update.

    Raises:
        HTTPException: If there's an error updating the database.
    """
    try:
        app.update_strategy_qty_amplifier(strategy, amplifier)
        return {"message": "StrategyQtyAmplifier updated successfully!"}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error updating StrategyQtyAmplifier: {str(e)}"
        )


@app_admin.get("/user-strategy-risk-params")
def get_user_risk_params(
    strategy: str = Query(..., description="The trading strategy to fetch"),
    trader_numbers: Optional[List[str]] = Query(
        None, description="List of trader numbers to fetch, or omit for all traders"
    ),
):
    """
    NOTE: only derivatives strategy has risk percentage at user level. for equity risk please refer the strategy params

    Fetch current strategy parameters for one or multiple users.

    This endpoint retrieves the current strategy parameters including risk percentage,
    and for PyStocks strategy, the sector and cap for one or multiple users.

    Args:
        strategy (str): The trading strategy to fetch.
        trader_numbers (Optional[List[str]]): List of trader numbers to fetch, or omit for all traders.

    Returns:
        dict: A dictionary containing the current strategy parameters for the specified users.

    Raises:
        HTTPException: If there's an error fetching the data or if the input is invalid.
    """
    try:
        return app.get_user_risk_params(strategy, trader_numbers)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching user strategy parameters: {str(e)}"
        )


@app_admin.put("/user-strategy-risk-params")
def update_user_risk_params(
    strategy: str = Query(..., description="The trading strategy to update"),
    trader_numbers: List[str] = Query(
        ..., description="List of trader numbers to update, or ['all'] for all traders"
    ),
    risk_percentage: float = Query(
        ..., ge=0.0, le=10.0, description="Risk percentage to set"
    ),
):
    """
    NOTE: only derivatives strategy has risk percentage at user level. for equity risk please refer the strategy params
    Modify strategy parameters for one or multiple users.

    This endpoint allows updating the risk percentage for a given strategy under derivatives and user in the Firebase database.

    Args:
        strategy (str): The trading strategy to update.
        trader_numbers (List[str]): List of trader numbers to update, or ['all'] for all traders.
        risk_percentage (float): Risk percentage to set (between 0.0 and 10.0).

    Returns:
        dict: A message indicating successful update.

    Raises:
        HTTPException: If there's an error updating the database or if the input is invalid.
    """
    try:
        return app.update_user_risk_params(strategy, trader_numbers, risk_percentage)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error updating user strategy parameters: {str(e)}"
        )


@app_admin.get("/user-list-details")
def get_user_list_from_db():
    """
    Fetches the list of users from the database.

    Returns:
        list: A list of user names.
    """

    try:
        userslist = app.get_user_list_from_db()
        return userslist
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching user list: {str(e)}"
        )


@app_admin.get("/strategy-list")
def get_strategy_list():
    """
    Fetches the list of strategies from the database.

    Returns:
        list: A list of strategy names.
    """
    try:
        return app.get_strategy_list()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching strategy list: {str(e)}"
        )


@app_admin.get("/complete-strategy-list")
def get_complete_strategy_list():
    """
    Fetches the list of strategies from the database.

    Returns:
        list: A list of strategy names.
    """
    return app.get_complete_strategy_list()


@app_admin.get("/user-details-username")
def get_user_details_by_username(username: str):
    """
    Fetches the details of a user by username.

    Args:
        username (str): The username of the user.

    Returns:
        list: A list of user details.
    """
    try:
        return app.fetch_user_details_by_username(username)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching user details: {str(e)}"
        )


@app_admin.post("/update-user-section")
def update_user_section(user_id: str, section: str, details: dict):
    """
    Update a specific section of user details.
    NOTE: For fields Active and Tr_No, the request should be sent as dict like this {"Active": true} or {"Tr_No": "Tr1"}

    Args:
        user_id (str): The ID of the user to update.
        section (UserSection): The section of user details to update.
        details (dict): The new details for the specified section.

    Returns:
        dict: A message indicating successful update and the updated section.
    """
    try:
        updated_section = app.update_user_section(user_id, section, details)
        return {
            "message": f"Successfully updated {section} for user {user_id}",
            "updated_section": updated_section,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error updating {section} for user {user_id}: {str(e)}",
        )


@app_admin.get("/fetch-users-for-strategy")
def fetch_users_for_strategy(strategy: str):
    """
    Retrieve users who have opted for a specific strategy.

    Args:
        strategy (str): The name of the strategy.

    Returns:
        UserResponse: A list of dicts containing user details who have opted for the strategy.

    Raises:
        HTTPException: If there's an error fetching the users or if the strategy is not found.
    """
    try:
        return app.fetch_users_for_strategy(strategy)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching users for strategy: {str(e)}"
        )


@app_admin.get("/aum")
def get_aum():
    """
    Calculates the Assets Under Management (AUM) for all active users.

    Returns:
        dict: A dictionary containing the AUM for Equity, Debt, Derivatives, and Portfolio.
    """
    try:
        aum = app.get_aum_from_firebase()
        return aum
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating AUM: {str(e)}")


@app_admin.get("/total-base-capital")
def get_total_base_capital():
    """
    Calculates the total CurrentBaseCapital for all active users.

    Returns:
        dict: A dictionary containing the total base capital.
    """
    try:
        total_base_capital = app.get_total_base_capital_from_firebase()
        return total_base_capital
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error calculating total base capital: {str(e)}"
        )


@app_admin.get("/strategy-signals")
def get_strategy_signals(
    strategy_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    Retrieves the strategy signals for a specific strategy.

    Args:
        strategy_name (str): The name of the strategy.

    Returns:
        dict: The strategy signals for the specified strategy.
    """
    try:
        return app.get_strategy_signals(strategy_name, page, page_size)
    except KeyError:
        raise HTTPException(status_code=404, detail="Strategy not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app_admin.get("/strategy-signals-graph-data")
def strategy_signals_graph_data(strategy_name: str):
    """
    Retrieves the strategy signals graph data for a specific strategy.
    """
    try:
        return app.strategy_signals_graph_data(strategy_name)
    except KeyError:
        raise HTTPException(status_code=404, detail="Strategy not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app_admin.get("/active-users-account-data")
def get_active_users_data_endpoint():
    """
    Retrieves data for all active users including their account values and holdings.

    Returns:
        dict: A dictionary containing the DataFrame of active users' data and any warnings.
    """
    try:
        data = app.get_active_users_data_from_firebase()
        return data.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching active users data: {str(e)}"
        )


@app_admin.get("/order-modes")
def get_order_modes():
    """
    Fetches the list of order modes.

    Returns:
        OrderModeResponse: A list of order modes. i.e [Complete order or Repair order]
    """
    try:
        return app.get_order_modes()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching order modes: {str(e)}"
        )


@app_admin.get("/qty-calculation-mode")
def get_qty_calculation_mode():
    """
    Fetches the qty calculation mode.

    Returns:
        list: A list of qty calculation modes.
    """
    try:
        return app.get_qty_calculation_mode()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching qty calculation mode: {str(e)}"
        )


@app_admin.get("/fetch-complete-order")
def fetch_complete_order_symbols(strategy_name: str):
    """
    Fetch complete order symbols from the strategy collection.

    Args:
        strategy_name (str): The name of the strategy.

    Returns:
        list: A list of today's orders.
    """
    try:
        return app.fetch_today_order(strategy_name)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing complete order: {str(e)}"
        )


@app_admin.post("/place-complete-order")
def place_complete_order(complete_order_input: schemas.CompleteOrderInput):
    """_summary_

    Args:
        strategy_name (str): The name of the strategy.(Ex: ExpiryTrader, LongTerm)
        users (list): The list of users.
        symbols (list): The list of symbols.
        qty_calculation_mode (str): _description_
        trade_id (str): The trade id of the stock.
        qty (float, optional): The quantity of the stock. Defaults to None.

    Raises:
        HTTPException: If there's an error processing the complete order.

    Returns:
        dict: A message indicating successful update.
    """
    try:
        return app.place_complete_order(
            strategy_name=complete_order_input.strategy_name,
            users=complete_order_input.users,
            symbols=complete_order_input.symbols,
            qty_calculation_mode=complete_order_input.qty_calculation_mode,
            trade_id=complete_order_input.trade_id,
            qty=complete_order_input.qty,
            setup_name=complete_order_input.setup_name,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing complete order: {str(e)}"
        )


@app_admin.post("/place-repair-order")
def place_repair_order(repair_order_input: schemas.RepairOrderInput):
    """
    Place a repair order for a given strategy.

    This endpoint allows placing a repair order for a given strategy.

    Args:
        repair_order_input (schemas.RepairOrderInput): The input for the repair order.

    Returns:
        dict: A message indicating successful update.
    """
    try:
        return app.place_repair_order(
            strategy_name=repair_order_input.strategy_name,
            users=repair_order_input.users,
            symbols=repair_order_input.symbols,
            qty_calculation_mode=repair_order_input.qty_calculation_mode,
            trade_id=repair_order_input.trade_id,
            qty=repair_order_input.qty,
            setup_name=repair_order_input.setup_name,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing repair order: {str(e)}"
        )


@app_admin.get("/error-logs")
def get_error_logs():
    """
    Fetches the error logs from the log file.

    Returns:
        dict: A dictionary containing the error logs.
    """
    result = app.get_error_logs()
    return result.to_dict(orient="records")


@app_admin.delete("/delete-user/{tr_no}")
def delete_user(tr_no: str):
    """
    Delete a user from Firebase.

    Args:
        user_id (str): The ID of the user to delete.

    Raises:
        HTTPException: If there's an error deleting the user.

    Returns:
        dict: A message indicating successful deletion.
    """
    try:
        app.delete_user(tr_no)
        return {"message": f"User {tr_no} successfully deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting user: {str(e)}")


app_fastapi.include_router(app_user, prefix="/v1/user", tags=["user"])
app_fastapi.include_router(app_admin, prefix="/v1/admin", tags=["admin"])


def main_api():
    uvicorn.run("main:app_fastapi", host="0.0.0.0", port=8082, reload=False)


if __name__ == "__main__":
    main_api()
