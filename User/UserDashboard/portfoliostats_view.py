import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import calendar
import os, sys
from dotenv import load_dotenv
from babel.numbers import format_currency

DIR = os.getcwd()
sys.path.append(DIR)
ENV_PATH = os.path.join(DIR, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.ExeUtils import get_previous_trading_day

ACTIVE_STRATEGIES = os.getenv("ACTIVE_STRATEGIES")
USR_TRADELOG_DB_FOLDER = os.getenv("USR_TRADELOG_DB_FOLDER")
user_db_collection = os.getenv("FIREBASE_USER_COLLECTION")

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()



class PortfolioStats:
    def __init__(self, dtd_data, account_value):
        # Ensure dtd_data is a DataFrame
        if not isinstance(dtd_data, pd.DataFrame):
            raise ValueError("dtd_data must be a pandas DataFrame")
        self.dtd_data = dtd_data
        self.dtd_data["exit_time"] = pd.to_datetime(self.dtd_data["exit_time"])
        self.account_value = account_value
        self._ensure_datetime_format()

    def _ensure_datetime_format(self):
        """Ensure 'Date' is in datetime format and extract common attributes."""
        self.dtd_data["Date"] = pd.to_datetime(self.dtd_data["exit_time"])
        self.dtd_data["Month"] = self.dtd_data["Date"].dt.month_name()
        self.dtd_data["Year"] = self.dtd_data["Date"].dt.year

    def show_equity_curve(self):
        # Ensure 'Date' is in datetime format and sort it
        self.dtd_data["Date"] = pd.to_datetime(self.dtd_data["Date"])
        self.dtd_data.sort_values("Date", inplace=True)

        # Calculate the cumulative NetPnL to simulate the equity curve
        self.dtd_data["Cumulative NetPnL"] = self.dtd_data["net_pnl"].cumsum()
        self.dtd_data["Equity"] = (
            self.account_value + self.dtd_data["Cumulative NetPnL"]
        )

        # Calculate the running maximum of the equity to date
        running_max = self.dtd_data["Equity"].cummax()

        # Calculate the drawdown in terms of amount and percentage
        self.dtd_data["Drawdown"] = self.dtd_data["Equity"] - running_max
        self.dtd_data["Drawdown Percent"] = (
            self.dtd_data["Drawdown"] / running_max
        ) * 100

        # Plotting the Equity and Drawdown graphs
        fig, axs = plt.subplots(2, 1, figsize=(10, 8))

        # Equity Graph
        axs[0].plot(
            self.dtd_data["Date"],
            self.dtd_data["Equity"],
            label="Equity Curve",
            color="blue",
        )
        axs[0].set_title("Equity Graph")
        axs[0].set_xlabel("Date")
        axs[0].set_ylabel("Equity")
        axs[0].grid(True)

        # Drawdown Graph
        axs[1].fill_between(
            self.dtd_data["Date"],
            0,
            self.dtd_data["Drawdown Percent"],
            color="red",
            step="post",
        )
        axs[1].set_title("Drawdown Graph")
        axs[1].set_xlabel("Date")
        axs[1].set_ylabel("Drawdown (%)")
        axs[1].grid(True)

        plt.tight_layout()  # Adjust the layout
        return fig

    def calculate_monthly_returns(self):
        """Calculate and return monthly absolute returns."""
        monthly_absolute_returns = (
            self.dtd_data.groupby(["Year", "Month"])["net_pnl"].sum().reset_index()
        )
        monthly_absolute_returns.columns = [
            "Year",
            "Month",
            "Monthly Absolute Returns (Rs.)",
        ]
        # Apply currency formatting using Babel
        monthly_absolute_returns['Monthly Absolute Returns (Rs.)'] = monthly_absolute_returns['Monthly Absolute Returns (Rs.)'].apply(
            lambda x: format_currency(x, 'INR', locale='en_IN')
        )
        return monthly_absolute_returns

    # def calculate_weekly_returns(self):
    #     """Calculate and return weekly absolute returns and cumulative returns."""
    #     logger.debug(f"self.dtd_data: {self.dtd_data.head()}")
    #     # Calculate week ending (Saturday) date
    #     self.dtd_data["Week_Ending_Date"] = self.dtd_data["Date"] + pd.to_timedelta(
    #         (5 - self.dtd_data["Date"].dt.weekday), unit="d"
    #     )

    #     # Calculate weekly absolute returns and cumulative returns
    #     weekly_absolute_returns = (
    #         self.dtd_data.groupby(["Week_Ending_Date"])["net_pnl"].sum().reset_index()
    #     )
    #     weekly_absolute_returns["abs_cum_returns"] = weekly_absolute_returns[
    #         "net_pnl"
    #     ].cumsum()
    #     weekly_absolute_returns = weekly_absolute_returns.sort_values(
    #         by="Week_Ending_Date"
    #     )
    #     weekly_absolute_returns["Week_Ending_Date"] = weekly_absolute_returns[
    #         "Week_Ending_Date"
    #     ].dt.strftime("%d%b%y")

    #     # Assign and reorder columns
    #     weekly_absolute_returns = weekly_absolute_returns[
    #         ["Week_Ending_Date", "net_pnl", "abs_cum_returns"]
    #     ]
    #     weekly_absolute_returns.columns = [
    #         "Week_Ending_Date",
    #         "Weekly Absolute Returns (Rs.)",
    #         "abs_cum_returns",
    #     ]
    #     logger.debug(f"weekly_absolute_returns: {weekly_absolute_returns.head()}")
    #     return weekly_absolute_returns
    

    def calculate_weekly_returns(self):
        """Calculate and return weekly absolute returns and cumulative returns."""

        # Ensure 'Date' is in datetime format
        self.dtd_data['Date'] = pd.to_datetime(self.dtd_data['exit_time'])

        # Calculate week ending (Saturday) date correctly and remove the time component
        self.dtd_data["Week_Ending_Date"] = (
            self.dtd_data["Date"] + pd.to_timedelta((5 - self.dtd_data["Date"].dt.weekday) % 7, unit="d")
        ).dt.normalize()  # This removes the time part, normalizing to midnight

        # Group by Week_Ending_Date and sum net_pnl for each group
        weekly_absolute_returns = self.dtd_data.groupby("Week_Ending_Date").agg(
            Weekly_Absolute_Returns=pd.NamedAgg(column="net_pnl", aggfunc="sum")
        ).reset_index()

        # Calculate cumulative returns
        weekly_absolute_returns["Cumulative Absolute Returns (Rs.)"] = weekly_absolute_returns["Weekly_Absolute_Returns"].cumsum()

        # Sort by Week_Ending_Date for clarity
        weekly_absolute_returns = weekly_absolute_returns.sort_values(by="Week_Ending_Date")

        # Format Week_Ending_Date for readability
        weekly_absolute_returns["Week_Ending_Date"] = weekly_absolute_returns["Week_Ending_Date"].dt.strftime("%d%b%y")

        # Rename columns appropriately
        weekly_absolute_returns.rename(columns={"Weekly_Absolute_Returns": "Weekly Absolute Returns (Rs.)"}, inplace=True)

        # Apply Indian currency formatting to the 'Weekly Absolute Returns (Rs.)'
        weekly_absolute_returns['Weekly Absolute Returns (Rs.)'] = weekly_absolute_returns['Weekly Absolute Returns (Rs.)'].apply(
            lambda x: format_currency(x, 'INR', locale='en_IN')
        )

        # Apply Indian currency formatting to the 'Cumulative Absolute Returns (Rs.)'
        weekly_absolute_returns['Cumulative Absolute Returns (Rs.)'] = weekly_absolute_returns['Cumulative Absolute Returns (Rs.)'].apply(
            lambda x: format_currency(x, 'INR', locale='en_IN')
        )

        return weekly_absolute_returns

    def calculate_weekly_withdrawals(self, new_df):

        # Ensure 'exit_time' is in datetime format
        new_df["exit_time"] = pd.to_datetime(new_df["exit_time"])

        # Calculate week ending (Saturday) date for each transaction
        new_df["Week_Ending_Date"] = new_df["exit_time"] + pd.to_timedelta(
            (5 - new_df["exit_time"].dt.weekday), unit="d"
        )

        # Filter for withdrawals and group by week
        withdrawals_df = new_df[new_df["transaction_type"] == "Withdrawal"]
        weekly_withdrawals = (
            withdrawals_df.groupby("Week_Ending_Date")["net_pnl"].sum().reset_index()
        )

        # Rename columns for clarity
        weekly_withdrawals.columns = ["Week_Ending_Date", "withdrawals"]

        # Calculate cumulative sum of withdrawals
        weekly_withdrawals["cumulative_withdrawals"] = weekly_withdrawals[
            "withdrawals"
        ].cumsum()

        return weekly_withdrawals

    def calculate_weekly_deposits(self, new_df):
        """Calculate weekly deposits and cumulative base capital."""
        # Ensure 'exit_time' is in datetime format
        new_df["exit_time"] = pd.to_datetime(new_df["exit_time"])

        # Calculate week ending (Saturday) date for each transaction
        new_df["Week_Ending_Date"] = new_df["exit_time"] + pd.to_timedelta(
            (5 - new_df["exit_time"].dt.weekday), unit="d"
        )

        # Filter for base deposits and group by week
        deposits_df = new_df[new_df["transaction_type"] == "Base Deposit"]
        weekly_deposits = (
            deposits_df.groupby("Week_Ending_Date")["net_pnl"].sum().reset_index()
        )

        # Rename columns for clarity
        weekly_deposits.columns = ["Week_Ending_Date", "deposit"]

        # Calculate cumulative sum of deposits
        weekly_deposits["current_base_cap"] = weekly_deposits["deposit"].cumsum()

        return weekly_deposits

    def add_financial_metrics(self, weekly_table, new_df):
        # Calculate weekly withdrawals and deposits
        weekly_withdrawals = self.calculate_weekly_withdrawals(new_df)
        weekly_deposits = self.calculate_weekly_deposits(new_df)

        # Format date columns for merging
        weekly_withdrawals["Week_Ending_Date"] = weekly_withdrawals[
            "Week_Ending_Date"
        ].dt.strftime("%d%b%y")
        weekly_deposits["Week_Ending_Date"] = weekly_deposits[
            "Week_Ending_Date"
        ].dt.strftime("%d%b%y")
        weekly_table["Week_Ending_Date"] = weekly_table["Week_Ending_Date"].astype(str)

        # Merge weekly_table with weekly_withdrawals and weekly_deposits
        weekly_table = weekly_table.merge(
            weekly_withdrawals, on="Week_Ending_Date", how="left"
        ).merge(weekly_deposits, on="Week_Ending_Date", how="left")

        # Handle missing values for withdrawals and deposits
        weekly_table["withdrawals"] = weekly_table["withdrawals"].fillna(0)
        weekly_table["cumulative_withdrawals"] = (
            weekly_table["cumulative_withdrawals"].fillna(method="ffill").fillna(0)
        )
        weekly_table["deposit"] = weekly_table["deposit"].fillna(0)
        weekly_table["current_base_cap"] = (
            weekly_table["current_base_cap"].fillna(method="ffill").fillna(0)
        )

        # Calculate 'ontable_pnl' as 'abs_cum_returns' - 'cumulative_withdrawals'
        weekly_table["ontable_pnl"] = (
            weekly_table["abs_cum_returns"] + weekly_table["cumulative_withdrawals"]
        )

        # Calculate 'exp_acc_value' as 'ontable_pnl' + 'current_base_cap'
        weekly_table["exp_acc_value"] = (
            weekly_table["ontable_pnl"] + weekly_table["current_base_cap"]
        )

        return weekly_table

    def max_impact_day(self):
        """Identify the days with the maximum profit and maximum loss, and format results in Indian currency."""
        
        # Get rows for the day with the maximum loss and maximum profit
        max_loss_day = self.dtd_data.loc[self.dtd_data["net_pnl"].idxmin()]
        max_profit_day = self.dtd_data.loc[self.dtd_data["net_pnl"].idxmax()]

        # Extract dates and pnl values
        max_loss_day_date = max_loss_day["Date"]
        max_loss_day_value = max_loss_day["net_pnl"]

        max_profit_day_date = max_profit_day["Date"]
        max_profit_day_value = max_profit_day["net_pnl"]

        # Prepare data for DataFrame
        max_impact_data = [
            {"Event": "Max Loss Day", "Date": max_loss_day_date, "NetPnL": max_loss_day_value},
            {"Event": "Max Profit Day", "Date": max_profit_day_date, "NetPnL": max_profit_day_value}
        ]

        # Create DataFrame
        max_impact_df = pd.DataFrame(max_impact_data)

        # Format Date for readability
        max_impact_df["Date"] = pd.to_datetime(max_impact_df["Date"]).dt.strftime("%d-%b-%Y")

        # Apply Indian currency formatting to the 'NetPnL' column
        max_impact_df['NetPnL'] = max_impact_df['NetPnL'].apply(
            lambda x: format_currency(x, 'INR', locale='en_IN')
        )

        return max_impact_df

    def portfolio_stats(self):
        """Calculate various statistics for the portfolio."""
        # Ensure 'Date' is in datetime format for calculations
        self.dtd_data['Date'] = pd.to_datetime(self.dtd_data['Date'])

        # Basic financial calculations
        net_profit = self.dtd_data["net_pnl"].sum()
        max_drawdown = -self.dtd_data["Drawdown"].min()
        average_loss = self.dtd_data[self.dtd_data["net_pnl"] < 0]["net_pnl"].mean()

        # More complex financial metrics
        recovery_factor = net_profit / max_drawdown if max_drawdown != 0 else float('nan')
        annual_return = net_profit / len(self.dtd_data["Year"].unique())
        annual_std = self.dtd_data.groupby("Year")["net_pnl"].sum().std()
        risk_return_ratio = annual_return / annual_std if annual_std != 0 else float('nan')

        # Time-related financial metrics
        days = (self.dtd_data["Date"].max() - self.dtd_data["Date"].min()).days
        cagr = ((self.dtd_data["Equity"].iloc[-1] / self.account_value) ** (365.0 / days) - 1) * 100

        # Behavioral finance metrics
        wins = self.dtd_data[self.dtd_data["net_pnl"] > 0]["net_pnl"].sum()
        losses = -self.dtd_data[self.dtd_data["net_pnl"] < 0]["net_pnl"].sum()
        win_loss_ratio = wins / losses if losses != 0 else float('nan')
        total_losses = -losses

        # Risk management metrics
        daily_return = self.dtd_data["net_pnl"] / self.account_value
        sharpe_ratio = daily_return.mean() / daily_return.std() if daily_return.std() != 0 else float('nan')

        # Calculating consecutive losses, consecutive wins
        self.dtd_data["Win"] = self.dtd_data["net_pnl"] > 0
        consecutive_losses = self.dtd_data[~self.dtd_data["Win"]].groupby((self.dtd_data["Win"] != self.dtd_data["Win"].shift()).cumsum()).size().max()
        consecutive_wins = self.dtd_data[self.dtd_data["Win"]].groupby((self.dtd_data["Win"] != self.dtd_data["Win"].shift()).cumsum()).size().max()

        # Gain to Pain Ratio: Total Returns / Absolute Sum of All Losses
        gain_to_pain_ratio = net_profit / total_losses if total_losses != 0 else float('nan')

        # Kelly Criterion: (Winning Probability * Average Win) / Average Loss - (Losing Probability * Average Loss) / Average Win
        winning_prob = len(self.dtd_data[self.dtd_data["net_pnl"] > 0]) / len(self.dtd_data)
        average_win = wins / len(self.dtd_data[self.dtd_data["net_pnl"] > 0])
        losing_prob = 1 - winning_prob
        kelly_criterion = (winning_prob * average_win / -average_loss) - (losing_prob * -average_loss / average_win) if average_win != 0 and average_loss != 0 else float('nan')

        # Use Babel to format currency for the specified stats
        formatted_net_profit = format_currency(net_profit, 'INR', locale='en_IN')
        formatted_max_drawdown = format_currency(max_drawdown, 'INR', locale='en_IN')
        formatted_average_loss = format_currency(average_loss, 'INR', locale='en_IN')

        # Constructing the results dictionary
        stats_dict = {
            "Net Profit": formatted_net_profit,
            "Max Drawdown": formatted_max_drawdown,
            "Recovery Factor": round(recovery_factor,2),
            "Risk-Return Ratio": round(risk_return_ratio,2),
            "Average Loss": formatted_average_loss,
            "CAGR (%)": round(cagr,2),
            "Win-Loss Ratio": round(win_loss_ratio,2),
            "Sharpe Ratio": round(sharpe_ratio,2),
            "Max Consecutive Losses": consecutive_losses,
            "Max Consecutive Wins": consecutive_wins,
            "Gain to Pain Ratio": round(gain_to_pain_ratio,2),
            "Kelly Criterion": round(kelly_criterion,2),
        }

        # Converting dictionary to DataFrame for better presentation
        stats_df = pd.DataFrame(list(stats_dict.items()), columns=['Statistic', 'Value'])

        return stats_df