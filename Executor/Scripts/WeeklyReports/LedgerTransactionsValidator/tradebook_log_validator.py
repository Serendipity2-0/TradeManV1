import pandas as pd
from datetime import timedelta

# Define file paths
tradebook_file_path = r"C:\Users\user\OneDrive\Desktop\TradeManV1\SampleData\ledger\kite\tradebook-YY0222-FO.csv"
logbook_file_path = (
    r"C:\Users\user\OneDrive\Desktop\TradeManV1\SampleData\ledger\kite\omkar.xlsx"
)


# Read and preprocess tradebook
def process_tradebook(file_path):
    """
    Reads and preprocesses the tradebook CSV file.

    This function reads the tradebook from the specified CSV file path, converts the 'trade_date'
    and 'order_execution_time' columns to datetime format, and returns the preprocessed DataFrame.

    :param file_path: The path to the tradebook CSV file.
    :return: A preprocessed DataFrame containing the tradebook data.
    """
    df = pd.read_csv(file_path)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df["order_execution_time"] = pd.to_datetime(df["order_execution_time"])
    return df


# Read and preprocess logbook
def process_logbook(file_path, sheet_names):
    """
    Reads and preprocesses the logbook Excel file from multiple sheets.

    This function reads the logbook from the specified Excel file path, converts the 'entry_time'
    and 'exit_time' columns to datetime format for each specified sheet, and combines the data
    from all sheets into a single DataFrame.

    :param file_path: The path to the logbook Excel file.
    :param sheet_names: A list of sheet names to be read from the Excel file.
    :return: A combined DataFrame containing the logbook data from all specified sheets.
    """
    all_data = []
    for sheet in sheet_names:
        df = pd.read_excel(file_path, sheet_name=sheet)
        df["entry_time"] = pd.to_datetime(df["entry_time"])
        df["exit_time"] = pd.to_datetime(df["exit_time"])
        all_data.append(df)
    return pd.concat(all_data)


# Matching trades
def match_trades(tradebook_df, logbook_df):
    """
    Matches trades between the tradebook and logbook DataFrames.

    This function iterates through the tradebook DataFrame and attempts to match trades with the logbook
    DataFrame based on the 'order_execution_time' within a 1-minute window and matching quantities.
    Matched trades are collected, and unmatched trades are identified for both tradebook and logbook.

    :param tradebook_df: A DataFrame containing the tradebook data.
    :param logbook_df: A DataFrame containing the logbook data.
    :return: A tuple containing the matched trades, unmatched tradebook entries, and unmatched logbook entries.
    """
    matched_trades = []
    unmatched_tradebook = tradebook_df.copy()
    unmatched_logbook = logbook_df.copy()

    for index, trade in tradebook_df.iterrows():
        trade_time = trade["order_execution_time"]
        trade_qty = trade["quantity"]
        matching_window = [
            trade_time - timedelta(minutes=1),
            trade_time + timedelta(minutes=1),
        ]

        matched = logbook_df[
            (logbook_df["entry_time"] >= matching_window[0])
            & (logbook_df["entry_time"] <= matching_window[1])
            & (logbook_df["qty"] <= trade_qty)
        ]

        if not matched.empty:
            matched_trades.append(matched)
            unmatched_tradebook.drop(index, inplace=True)
            unmatched_logbook = unmatched_logbook[
                ~unmatched_logbook.index.isin(matched.index)
            ]
            trade_qty -= matched["qty"].sum()

            if trade_qty <= 0:
                continue

    print(f"Matched trades: {len(matched_trades)}")
    print(f"Unmatched tradebook: {len(unmatched_tradebook)}")
    print(f"Unmatched logbook: {len(unmatched_logbook)}")

    return matched_trades, unmatched_tradebook, unmatched_logbook


# Main function to process trades
def process_trades(tradebook_path, logbook_path):
    """
    Processes trades by reading tradebook and logbook files, matching trades, and saving results.

    This function reads the tradebook and logbook files, preprocesses them, matches trades between
    the tradebook and logbook, and saves the matched trades to an Excel file and unmatched trades
    to CSV files.

    :param tradebook_path: The path to the tradebook CSV file.
    :param logbook_path: The path to the logbook Excel file.
    """
    tradebook_df = process_tradebook(tradebook_path)
    sheet_names = [
        "AmiPy",
        "MPWizard",
        "ExpiryTrader",
        "OvernightFutures",
        "Stocks",
        "ExtraTrades",
        "ErrorTrade",
    ]
    logbook_df = process_logbook(logbook_path, sheet_names)

    matched_trades, unmatched_tradebook, unmatched_logbook = match_trades(
        tradebook_df, logbook_df
    )

    # Save matched trades to Excel and unmatched trades to CSV
    matched_trades_df = pd.concat(matched_trades)
    matched_trades_df.to_excel("matched_trades.xlsx", index=False)
    unmatched_tradebook.to_csv("unmatched_tradebook.csv", index=False)
    unmatched_logbook.to_csv("unmatched_logbook.csv", index=False)


# Execute the processing
process_trades(tradebook_file_path, logbook_file_path)
