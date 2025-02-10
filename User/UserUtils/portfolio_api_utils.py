"""
Portfolio and strategy analytics utility functions.
"""

import os
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from dotenv import load_dotenv
from babel.numbers import format_currency
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup
from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_adapter import (
    fetch_collection_data_firebase,
)
from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_adapter import get_db_connection
from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_utils import get_db_table_names
from Executor.ExecutorUtils.BrokerCenter.BrokerCenterUtils import (
    fetch_active_strategies_all_users,
)
from Executor.ExecutorUtils.ExeUtils import (
    EQUITY_STRATEGY_LIST,
    DERIVATIVES_STRATEGY_LIST,
    DEBT_STRATEGY_LIST,
)

DIR_PATH = os.getcwd()
ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

logger = LoggerSetup()

ACTIVE_STRATEGIES = fetch_active_strategies_all_users()
USER_DB_EQUITY_PATH = os.getenv("USR_TRADELOG_EQUITY_DB_FOLDER")
USER_DB_DERIVATIVES_PATH = os.getenv("USR_TRADELOG_DERIVATIVES_DB_FOLDER")
USER_DB_DEBT_PATH = os.getenv("USR_TRADELOG_DEBT_DB_FOLDER")

MODE_TO_DB = {
    "Equity": ("equity", USER_DB_EQUITY_PATH),
    "Derivatives": ("derivatives", USER_DB_DERIVATIVES_PATH),
    "Debt": ("debt", USER_DB_DEBT_PATH),
}

def get_user_segments(tr_no: str) -> List[str]:
    """
    Fetches the segments for a user from the Firebase database.

    Args:
        tr_no (str): The user's ID.

    Returns:
        list: A list of segments for the user.
    """
    try:
        user_data = fetch_collection_data_firebase(os.getenv("FIREBASE_USER_COLLECTION"), tr_no)
        return list(user_data.get("Strategies", {}).keys())
    except Exception as e:
        logger.error(f"Error fetching user segments for {tr_no}: {e}")
        return []

def create_portfolio_stats(db_path: str) -> Optional[pd.DataFrame]:
    """
    Fetches portfolio stats for a user from a specific database file.

    Args:
        db_path (str): The path to the database file.

    Returns:
        Optional[pd.DataFrame]: The portfolio stats data as a pandas DataFrame
        with the columns 'exit_time', 'trade_id', 'net_pnl', and 'segment'.
        Returns None if there's an error or no data.
    """
    try:
        dtd_data_list = []
        conn = get_db_connection(db_path)
        table_names = get_db_table_names(conn)

        segment = "equity" if "_equity.db" in db_path else "derivatives"

        user_strategy_table_names = [
            table for table in table_names if table in ACTIVE_STRATEGIES
        ]

        for table in user_strategy_table_names:
            data = pd.read_sql_query(f"SELECT * FROM {table}", conn)

            required_columns = ["exit_time", "trade_id", "net_pnl"]
            if all(item in data.columns for item in required_columns):
                df = data[required_columns].copy()
                df["segment"] = segment
                dtd_data_list.append(df)
            else:
                missing_cols = set(required_columns) - set(data.columns)
                logger.error(f"Missing columns {missing_cols} in table {table}")

        if dtd_data_list:
            dtd_data = pd.concat(dtd_data_list, ignore_index=True)
            return dtd_data
        else:
            logger.error(f"No data frames to concatenate in {db_path}")
            return None
    except Exception as e:
        logger.error(f"Error fetching portfolio stats from {db_path}: {e}")
        return None

def get_monthly_returns_data(
    user_stats: pd.DataFrame, page: int, page_size: int
) -> Dict:
    """
    Calculates the paginated monthly returns for a given DataFrame of portfolio stats data.

    Args:
        user_stats (pd.DataFrame): The DataFrame of portfolio stats data.
        page: The page number.
        page_size: The number of items per page.

    Returns:
        dict: A dictionary containing the paginated DataFrame of monthly returns and total items.
    """
    try:
        user_stats["exit_time"] = pd.to_datetime(user_stats["exit_time"], errors="coerce")
        user_stats = user_stats.dropna(subset=["exit_time"])

        user_stats["Year"] = user_stats["exit_time"].dt.year
        user_stats["Month"] = user_stats["exit_time"].dt.strftime("%B")
        user_stats["net_pnl"] = pd.to_numeric(user_stats["net_pnl"], errors="coerce")

        monthly_absolute_returns = (
            user_stats.groupby(["Year", "Month"])["net_pnl"]
            .sum()
            .reset_index()
            .rename(columns={"net_pnl": "Monthly Absolute Returns (Rs.)"})
        )

        monthly_absolute_returns["Monthly Absolute Returns (Rs.)"] = (
            monthly_absolute_returns["Monthly Absolute Returns (Rs.)"]
            .apply(lambda x: format_currency(x, "INR", locale="en_IN"))
        )

        month_order = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        monthly_absolute_returns["Month"] = pd.Categorical(
            monthly_absolute_returns["Month"], categories=month_order, ordered=True
        )
        monthly_absolute_returns = monthly_absolute_returns.sort_values(
            ["Year", "Month"], ascending=[False, False]
        )

        total_items = len(monthly_absolute_returns)
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated_data = monthly_absolute_returns.iloc[start_index:end_index]

        return {
            "items": paginated_data.to_dict(orient="records"),
            "total_items": total_items,
        }

    except Exception as e:
        logger.error(f"Error calculating monthly returns: {e}")
        return {"items": [], "total_items": 0}

def get_weekly_cumulative_returns_data(
    user_stats: pd.DataFrame, page: int, page_size: int
) -> Dict:
    """
    Calculates the paginated weekly cumulative returns for a given DataFrame of portfolio stats data.

    Args:
        user_stats (pd.DataFrame): The DataFrame of portfolio stats data.
        page: The page number.
        page_size: The number of items per page.

    Returns:
        dict: A dictionary containing the paginated DataFrame of weekly returns and total items.
    """
    try:
        user_stats["Date"] = pd.to_datetime(user_stats["exit_time"], errors="coerce")
        user_stats = user_stats.dropna(subset=["Date"])
        user_stats["Year"] = user_stats["Date"].dt.year
        user_stats["Month"] = user_stats["Date"].dt.month
        user_stats["Week_Ending_Date"] = (
            user_stats["Date"] + pd.to_timedelta(
                (5 - user_stats["Date"].dt.weekday) % 7, unit="d"
            )
        ).dt.normalize()
        user_stats["net_pnl"] = pd.to_numeric(user_stats["net_pnl"], errors="coerce")

        weekly_absolute_returns = (
            user_stats.groupby("Week_Ending_Date")
            .agg(Weekly_Absolute_Returns=pd.NamedAgg(column="net_pnl", aggfunc="sum"))
            .reset_index()
        )

        weekly_absolute_returns["Cumulative Absolute Returns (Rs.)"] = (
            weekly_absolute_returns["Weekly_Absolute_Returns"].cumsum()
        )
        weekly_absolute_returns = weekly_absolute_returns.sort_values(
            by="Week_Ending_Date"
        )

        weekly_absolute_returns["Week_Ending_Date"] = (
            weekly_absolute_returns["Week_Ending_Date"].dt.strftime("%d%b%y")
        )
        weekly_absolute_returns.rename(
            columns={"Weekly_Absolute_Returns": "Weekly Absolute Returns (Rs.)"},
            inplace=True,
        )

        for col in ["Weekly Absolute Returns (Rs.)", "Cumulative Absolute Returns (Rs.)"]:
            weekly_absolute_returns[col] = weekly_absolute_returns[col].apply(
                lambda x: format_currency(x, "INR", locale="en_IN")
            )

        total_items = len(weekly_absolute_returns)
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated_data = weekly_absolute_returns.iloc[start_index:end_index]

        return {
            "items": paginated_data.to_dict(orient="records"),
            "total_items": total_items,
        }

    except Exception as e:
        logger.error(f"Error calculating weekly returns: {e}")
        return {"items": [], "total_items": 0}

def calculate_strategy_statistics(df: pd.DataFrame, is_signals: bool) -> Optional[Dict]:
    """
    Calculate strategy statistics from a DataFrame.

    Args:
        df: DataFrame containing strategy data.
        is_signals: Boolean indicating if the strategy is a signals strategy.

    Returns:
        Dict: Calculated strategy statistics.
    """
    if df.empty:
        return None

    column_for_calc = "trade_points" if is_signals else "net_pnl"

    if "trade_points" not in df.columns:
        logger.error("trade_points not in df.columns")
        return None

    try:
        df[column_for_calc] = df[column_for_calc].astype(float)
        positive_trades = df[df[column_for_calc] > 0.0]
        negative_trades = df[df[column_for_calc] < 0.0]

        cols = ["entry_price", "exit_price", "trade_points", "pnl", "net_pnl"]
        for col in cols:
            df[col] = df[col].astype(float)

        df["win"] = df[column_for_calc] > 0
        df["group"] = (df["win"] != df["win"].shift()).cumsum()

        net_trade_points = df[column_for_calc].sum()
        num_trades = len(df)
        num_wins = len(positive_trades)
        num_losses = len(negative_trades)
        consecutive_wins = df[df["win"]].groupby("group").size().max() if num_wins > 0 else 0
        consecutive_losses = df[~df["win"]].groupby("group").size().max() if num_losses > 0 else 0

        avg_profit_loss = df[column_for_calc].mean()
        df["profit_percent"] = df[column_for_calc] / df["entry_price"] * 100
        avg_profit_loss_percent = df["profit_percent"].mean()
        max_trade_drawdown = df[column_for_calc].min()
        cumulative_net_pnl = df[column_for_calc].cumsum()
        max_system_drawdown = cumulative_net_pnl.min()

        recovery_factor = (
            net_trade_points / -max_system_drawdown if max_system_drawdown < 0 else 0
        )

        annual_return = 0.1  # Assume 10% annual return
        max_dd_percent = max_system_drawdown / df["entry_price"].iloc[0] * 100
        car_maxdd = annual_return / -max_dd_percent if max_dd_percent < 0 else 0

        std_error = df[column_for_calc].std()
        risk_reward_ratio = avg_profit_loss / std_error if std_error != 0 else 0

        drawdown = cumulative_net_pnl.cummin() - cumulative_net_pnl
        ulcer_index = float(np.sqrt(np.mean(drawdown**2)))

        statistics = {
            "Net Trade Points": net_trade_points,
            "No of Trades": num_trades,
            "No of Wins": num_wins,
            "No of Losses": num_losses,
            "No of Cons Win": consecutive_wins,
            "No of Cons Loss": consecutive_losses,
            "Avg. Profit/Loss (Expectancy Rs)": avg_profit_loss,
            "Avg. Profit/Loss % (Expectancy %)": avg_profit_loss_percent,
            "Max. Trade Drawdown": max_trade_drawdown,
            "Max. System Drawdown": max_system_drawdown,
            "Recovery Factor": recovery_factor,
            "CAR/MaxDD": car_maxdd,
            "Standard Error": std_error,
            "Risk-Reward Ratio": risk_reward_ratio,
            "Ulcer Index": ulcer_index,
        }

        # Format floats to 2 decimal places
        formatted_stats = {}
        for key, value in statistics.items():
            if isinstance(value, float):
                formatted_stats[key] = f"{value:.2f}"
            else:
                formatted_stats[key] = value

        return formatted_stats

    except Exception as e:
        logger.error(f"Error calculating strategy statistics: {e}")
        return None
