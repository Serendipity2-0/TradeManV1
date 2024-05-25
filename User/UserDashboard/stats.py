import pandas as pd
import numpy as np
import streamlit as st

# Load your data into DataFrame `df`
df = pd.DataFrame()  # Replace with actual loading code

# Implementing functions for each metric


def net_trade_points(df, is_signals=True):
    """Calculate Net Trade Points."""
    column_for_calc = "trade_points" if is_signals else "net_pnl"
    return df[column_for_calc].sum()


def number_of_wins(df, is_signals=True):
    """Calculate Number of Wins."""
    column_for_calc = "trade_points" if is_signals else "net_pnl"
    return len(df[df[column_for_calc] > 0])


def number_of_losses(df, is_signals=True):
    """Calculate Number of Losses."""
    column_for_calc = "trade_points" if is_signals else "net_pnl"
    return len(df[df[column_for_calc] < 0])


def avg_profit_loss(df, is_signals=True):
    """Calculate Avg. Profit/Loss (Expectancy $)."""
    column_for_calc = "trade_points" if is_signals else "net_pnl"
    return df[column_for_calc].mean()


def avg_profit_loss_percent(df, is_signals=True):
    """Calculate Avg. Profit/Loss % (Expectancy %)."""
    column_for_calc = "trade_points" if is_signals else "net_pnl"
    df["profit_percent"] = df[column_for_calc] / df["entry_price"] * 100
    return df["profit_percent"].mean()


def max_trade_drawdown(df, is_signals=True):
    """Calculate Max. Trade Drawdown."""
    column_for_calc = "trade_points" if is_signals else "net_pnl"
    return df[column_for_calc].min()


def max_system_drawdown(df, is_signals=True):
    """Calculate Max. System Drawdown."""
    column_for_calc = "trade_points" if is_signals else "net_pnl"
    cumulative_net_pnl = df[column_for_calc].cumsum()
    return cumulative_net_pnl.min()


def recovery_factor(df):
    """Calculate Recovery Factor."""
    net_profit = net_trade_points(df)
    max_dd = max_system_drawdown(df)
    return net_profit / -max_dd if max_dd < 0 else 0


def car_maxdd(df, annual_return):
    """Calculate CAR/MaxDD."""
    max_dd_percent = max_system_drawdown(df) / df["entry_price"].iloc[0] * 100
    return annual_return / -max_dd_percent if max_dd_percent < 0 else 0


def standard_error(df, is_signals=True):
    """Calculate Standard Error."""
    column_for_calc = "trade_points" if is_signals else "net_pnl"
    return df[column_for_calc].std()


def risk_reward_ratio(df, is_signals=True):
    """Calculate Risk-Reward Ratio."""
    column_for_calc = "trade_points" if is_signals else "net_pnl"
    avg_return = df[column_for_calc].mean()
    std_dev = standard_error(df)
    return avg_return / std_dev if std_dev != 0 else 0


def ulcer_index(df, is_signals=True):
    """Calculate Ulcer Index."""
    column_for_calc = "trade_points" if is_signals else "net_pnl"
    drawdown = df[column_for_calc].cumsum().cummin() - df[column_for_calc].cumsum()
    return np.sqrt(np.mean(drawdown**2))


def number_of_trades(df, is_signals=True):
    """Calculate the total number of trades."""
    return len(df)


def consecutive_wins(df, is_signals=True):
    """Calculate the longest streak of consecutive wins."""
    column_for_calc = "trade_points" if is_signals else "net_pnl"
    df["win"] = df[column_for_calc] > 0  # True if win, False otherwise
    df["group"] = (
        df["win"] != df["win"].shift()
    ).cumsum()  # Grouping consecutive wins or losses
    wins = df[df["win"] == True].groupby("group").size()  # Count in each group of wins
    max_consecutive_wins = wins.max() if not wins.empty else 0
    return max_consecutive_wins


def consecutive_losses(df, is_signals=True):
    """Calculate the longest streak of consecutive losses."""
    column_for_calc = "trade_points" if is_signals else "net_pnl"
    df["loss"] = df[column_for_calc] < 0  # True if loss, False otherwise
    df["group"] = (
        df["loss"] != df["loss"].shift()
    ).cumsum()  # Grouping consecutive wins or losses
    losses = (
        df[df["loss"] == True].groupby("group").size()
    )  # Count in each group of losses
    max_consecutive_losses = losses.max() if not losses.empty else 0
    return max_consecutive_losses


###########################################################################################################


def format_statistics(statistics):
    formatted_stats = {}
    for key, value in statistics.items():
        if isinstance(value, float):
            # Limiting float to 2 decimal places
            formatted_stats[key] = f"{value:.2f}"
        else:
            formatted_stats[key] = value
    return formatted_stats


# Display the statistics in Streamlit
def return_statistics(df, is_signals):
    statistics = {
        "Net Trade Points": net_trade_points(df, is_signals),
        "No of Trades": number_of_trades(df, is_signals),
        "No of Wins": number_of_wins(df, is_signals),
        "No of Losses": number_of_losses(df, is_signals),
        "No of Cons Win": consecutive_wins(df, is_signals),
        "No of Cons Loss": consecutive_losses(df, is_signals),
        "Avg. Profit/Loss (Expectancy Rs)": avg_profit_loss(df, is_signals),
        "Avg. Profit/Loss % (Expectancy %)": avg_profit_loss_percent(df, is_signals),
        "Max. Trade Drawdown": max_trade_drawdown(df, is_signals),
        "Max. System Drawdown": max_system_drawdown(df, is_signals),
        "Recovery Factor": recovery_factor(df),
        "CAR/MaxDD": car_maxdd(
            df, 0.1
        ),  # Assume 10% annual return or replace with actual calculation
        "Standard Error": standard_error(df, is_signals),
        "Risk-Reward Ratio": risk_reward_ratio(df, is_signals),
        "Ulcer Index": ulcer_index(df, is_signals),
    }
    formatted_stats = format_statistics(statistics)
    return formatted_stats
