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

import User.UserApi.schemas as schemas
import User.UserApi.app as app

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


@app_user.post("/register")
def register_user(user_detail: schemas.UserDetails):
    """
    This is the route for registering a new user.
    It takes a UserDetails object as input and returns a response.
    We are storing the user details in a dictionary and then passing it to the register_user function in app.py.
    """
    try:
        return app.register_user(user_detail)
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

        return {
            "items": json.loads(items.to_json(orient="records")),
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

        return {
            "items": json.loads(items.to_json(orient="records")),
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
            raise HTTPException(status_code=404, detail="Strategy not found")

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
        mode (str): The mode of holdings to retrieve.

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


@app_user.get("/strategy-params/{strategy_name}")
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


@app_user.put("/strategy-params/{strategy_name}/{section}")
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
def modify_user_strategy_params(
    strategy: str = Query(..., description="The trading strategy to update"),
    trader_numbers: List[str] = Query(
        ..., description="List of trader numbers to update, or ['all'] for all traders"
    ),
    risk_percentage: float = Query(
        ..., ge=0.0, le=10.0, description="Risk percentage to set"
    ),
    sector: Optional[str] = Query(None, description="Sector for PyStocks strategy"),
    cap: Optional[str] = Query(None, description="Cap for PyStocks strategy"),
):
    """
    Modify strategy parameters for one or multiple users.

    This endpoint allows updating the risk percentage and, for PyStocks strategy,
    the sector and cap for one or multiple users.

    Args:
        strategy (str): The trading strategy to update.
        trader_numbers (List[str]): List of trader numbers to update, or ['all'] for all traders.
        risk_percentage (float): Risk percentage to set (between 0.0 and 10.0).
        sector (Optional[str]): Sector for PyStocks strategy.
        cap (Optional[str]): Cap for PyStocks strategy.

    Returns:
        dict: A message indicating successful update.

    Raises:
        HTTPException: If there's an error updating the database or if the input is invalid.
    """
    try:
        return app.update_user_risk_params(
            strategy, trader_numbers, risk_percentage, sector, cap
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error updating user strategy parameters: {str(e)}"
        )


app_fastapi.include_router(app_user, prefix="/v1/user", tags=["user"])
app_fastapi.include_router(app_admin, prefix="/v1/admin", tags=["admin"])


def main_api():
    uvicorn.run("main:app_fastapi", host="0.0.0.0", port=8002, reload=True)


if __name__ == "__main__":
    main_api()
