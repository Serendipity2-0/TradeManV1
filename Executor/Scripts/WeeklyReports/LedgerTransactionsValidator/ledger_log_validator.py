import pandas as pd
import numpy as np
from datetime import datetime


# Function to process the Excel file
def process_excel_file(file_path):
    sheet_names = [
        "AmiPy",
        "MPWizard",
        "ExpiryTrader",
        "OvernightFutures",
        "Stocks",
        "ExtraTrades",
        "ErrorTrade",
    ]
    all_data = []

    for sheet in sheet_names:
        try:
            df = pd.read_excel(file_path, sheet_name=sheet)
            if "exit_time" in df.columns and "net_pnl" in df.columns:
                df["exit_time"] = pd.to_datetime(df["exit_time"]).dt.date
                df = df.groupby("exit_time")["net_pnl"].sum().reset_index()
                df.columns = ["Date", "NetPnL"]
                all_data.append(df)
            else:
                print(f"Sheet '{sheet}' does not contain required columns.")
        except Exception as e:
            print(f"Error processing sheet {sheet}: {e}")

    if all_data:
        combined_df = pd.concat(all_data)
        combined_df = combined_df.groupby("Date")["NetPnL"].sum().reset_index()
        combined_df["Day"] = combined_df["Date"].apply(lambda x: x.strftime("%A"))
        combined_df.reset_index(inplace=True)
        combined_df.rename(columns={"index": "Sl No"}, inplace=True)
        return combined_df
    else:
        return pd.DataFrame(columns=["Sl No", "Date", "Day", "NetPnL"])


# Function to process the CSV file
def process_csv_file(file_path):
    try:
        df = pd.read_csv(file_path)
        if (
            "posting_date" in df.columns
            and "debit" in df.columns
            and "credit" in df.columns
        ):
            df["posting_date"] = pd.to_datetime(df["posting_date"]).dt.date
            df["NetPnL_broker"] = df["credit"] - df["debit"]
            df = df.groupby("posting_date")["NetPnL_broker"].sum().reset_index()
            df.columns = ["Date", "NetPnL_broker"]
            df["Day"] = df["Date"].apply(lambda x: x.strftime("%A"))
            df.reset_index(inplace=True)
            df.rename(columns={"index": "Sl No"}, inplace=True)
            return df
        else:
            print("CSV file does not contain required columns.")
            return pd.DataFrame(columns=["Sl No", "Date", "Day", "NetPnL_broker"])
    except Exception as e:
        print(f"Error processing CSV file: {e}")
        return pd.DataFrame(columns=["Sl No", "Date", "Day", "NetPnL_broker"])


# Function to merge dataframes and process
def compare_log_ledger(excel_file_path, csv_file_path):
    # Process the Excel and CSV files
    excel_df = process_excel_file(excel_file_path)
    csv_df = process_csv_file(csv_file_path)

    # Merge the dataframes
    merged_df = pd.merge(
        excel_df, csv_df, left_on=["Date", "Day"], right_on=["Date", "Day"], how="outer"
    )
    merged_df.fillna(0, inplace=True)
    merged_df["DifferencePnL"] = merged_df["NetPnL_broker"] - merged_df["NetPnL"]
    merged_df["DiffPercent"] = merged_df["DifferencePnL"] / merged_df["NetPnL"] * 100
    final_df = merged_df[
        [
            "Sl No_x",
            "Date",
            "Day",
            "NetPnL",
            "NetPnL_broker",
            "DifferencePnL",
            "DiffPercent",
        ]
    ]
    final_df.rename(columns={"Sl No_x": "Sl No"}, inplace=True)

    return final_df


# Run the script
excel_file_path = r"C:\Users\user\OneDrive\Desktop\TradeManV1\SampleData\ledger\kite\omkar.xlsx"  # Replace with the actual file path
csv_file_path = r"C:\Users\user\OneDrive\Desktop\TradeManV1\SampleData\ledger\kite\kite_Trades.csv"  # Replace with the actual file path

final_df = compare_log_ledger(excel_file_path, csv_file_path)
final_df.to_csv(
    r"C:\Users\user\OneDrive\Desktop\TradeManV1\SampleData\ledger\kite\log_ledger_compare.csv",
    index=False,
)
