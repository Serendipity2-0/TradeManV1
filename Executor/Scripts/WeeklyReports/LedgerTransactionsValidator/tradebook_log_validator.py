import pandas as pd
from datetime import timedelta

# Define file paths
tradebook_file_path = r"C:\Users\user\OneDrive\Desktop\TradeManV1\SampleData\ledger\kite\tradebook-YY0222-FO.csv"
logbook_file_path = (
    r"C:\Users\user\OneDrive\Desktop\TradeManV1\SampleData\ledger\kite\omkar.xlsx"
)


# Read and preprocess tradebook
def process_tradebook(file_path):
    df = pd.read_csv(file_path)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df["order_execution_time"] = pd.to_datetime(df["order_execution_time"])
    return df


# Read and preprocess logbook
def process_logbook(file_path, sheet_names):
    all_data = []
    for sheet in sheet_names:
        df = pd.read_excel(file_path, sheet_name=sheet)
        df["entry_time"] = pd.to_datetime(df["entry_time"])
        df["exit_time"] = pd.to_datetime(df["exit_time"])
        all_data.append(df)
    return pd.concat(all_data)


# Matching trades
def match_trades(tradebook_df, logbook_df):
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
