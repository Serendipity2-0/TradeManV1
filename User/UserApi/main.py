import uvicorn
from fastapi.openapi.docs import get_swagger_ui_html
import os, sys
from fastapi.middleware.cors import CORSMiddleware
import json
from datetime import date
from fastapi import FastAPI, HTTPException, Query, APIRouter


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


@app_user.get("/profilepage")
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


@app_user.get("/portfoliostatsview")
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


@app_user.get("/monthlyreturns")
def monthly_returns(tr_no: str):
    """
    Retrieves the monthly returns data for a specific user by their user ID.

    Args:
    user_id: The unique identifier of the user.

    Returns:
    dict: The monthly returns data.
    """
    try:
        monthly_data = app.monthly_returns_data(tr_no)
        return json.loads(monthly_data.to_json(orient="records"))
    except KeyError:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app_user.get("/weeklycummulativereturns")
def weekly_cummulative_returns(tr_no: str):
    """
    Retrieves the weekly cummulative returns data for a specific user by their user ID.

    Args:
    user_id: The unique identifier of the user.

    Returns:
    dict: The weekly cummulative returns data.
    """
    try:
        weekly_data = app.weekly_cummulative_returns_data(tr_no)
        return json.loads(weekly_data.to_json(orient="records"))
    except KeyError:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app_user.get("/individualstrategydata")
def individual_strategy_performance(tr_no: str, strategy_name: str):
    """
    Retrieves the individual strategy data for a specific user by their user ID and strategy name.

    Args:
    user_id: The unique identifier of the user.
    strategy_name: The name of the strategy.

    Returns:
    dict: The individual strategy data.
    """
    try:
        strategy_data = app.individual_strategy_data(tr_no, strategy_name)
        return json.loads(strategy_data.to_json(orient="records"))
    except KeyError:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app_user.get("/equitytransactions")
def equity_transactions(
    tr_no: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1),
    from_date: date = None,
    to_date: date = None,
):
    """
    Retrieves the transactions data for a specific user by their user ID, optionally filtering by date and paginating the results.

    Args:
        tr_no: The unique identifier of the user.
        page: The page number of results to return.
        page_size: The number of items per page.
        from_date: Start date for filtering transactions.(YYYY-MM-DD). Defaults to None.
        to_date: End date for filtering transactions.(YYYY-MM-DD). Defaults to None.

    Returns:
        dict: The paginated transactions data.
    """
    try:
        transactions_data = app.equity_broker_bank_transactions_data(
            tr_no, from_date, to_date
        )
        # Implement pagination
        start = (page - 1) * page_size
        end = start + page_size
        paginated_data = transactions_data[start:end]
        return json.loads(paginated_data.to_json(orient="records"))
    except KeyError:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


app_fastapi.include_router(app_user, prefix="/v1/user")


def main_api():
    uvicorn.run("main:app_fastapi", host="0.0.0.0", port=8002, reload=True)


if __name__ == "__main__":
    main_api()
