import os
import sys

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

from Executor.ExecutorUtils.BrokerCenter.Brokers.AliceBlue.alice_adapter import (
    merge_ins_csv_files,
)


# Ensure successful merging of NFO, BFO, and NSE CSV files with valid credentials
def test_successful_merge_with_valid_credentials(mocker):
    import pandas as pd

    # Mock the pd.read_csv function to return sample dataframes
    mock_nfo_df = pd.DataFrame(
        {
            "Exch": ["NFO"],
            "Exchange Segment": ["NSE"],
            "Symbol": ["ABC"],
            "Token": [123],
            "Instrument Type": ["OPT"],
            "Option Type": ["CE"],
            "Strike Price": [1000],
            "Instrument Name": ["ABC"],
            "Formatted Ins Name": ["ABC"],
            "Trading Symbol": ["ABC"],
            "Expiry Date": ["2023-12-31"],
            "Lot Size": [75],
            "Tick Size": [0.05],
        }
    )
    mock_bfo_df = pd.DataFrame(
        {
            "Exch": ["BFO"],
            "Exchange Segment": ["BSE"],
            "Symbol": ["XYZ"],
            "Token": [456],
            "Instrument Type": ["FUT"],
            "Option Type": [None],
            "Strike Price": [None],
            "Instrument Name": ["XYZ"],
            "Formatted Ins Name": ["XYZ"],
            "Trading Symbol": ["XYZ"],
            "Expiry Date": ["2023-12-31"],
            "Lot Size": [50],
            "Tick Size": [0.1],
        }
    )
    mock_nse_df = pd.DataFrame(
        {
            "Exch": ["NSE"],
            "Exchange Segment": ["NSE"],
            "Symbol": ["LMN"],
            "Token": [789],
            "Instrument Type": ["EQ"],
            "Option Type": [None],
            "Strike Price": [None],
            "Instrument Name": ["LMN"],
            "Formatted Ins Name": ["LMN"],
            "Trading Symbol": ["LMN"],
            "Expiry Date": [None],
            "Lot Size": [1],
            "Tick Size": [0.01],
        }
    )

    mocker.patch("pandas.read_csv", side_effect=[mock_nfo_df, mock_bfo_df, mock_nse_df])

    # Set up valid credentials here before calling the function
    # cred_filepath = "<valid_certificate_path>"
    # os.environ["FIREBASE_CERTIFICATE"] = cred_filepath

    # Call the function
    result = merge_ins_csv_files()

    # Assert the result is not None and is a DataFrame
    assert result is not None
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 3  # Ensure all rows are merged


def test_fetches_holdings_successfully_with_valid_user_credentials(mocker):
    from Executor.ExecutorUtils.BrokerCenter.Brokers.AliceBlue.alice_adapter import (
        fetch_aliceblue_holdings_value,
    )

    # Mocking Aliceblue and its methods
    mock_alice = mocker.Mock()
    mock_alice.get_holding_positions.return_value = {
        "stat": "Ok",
        "HoldingVal": [
            {"Price": "100.0", "HUqty": "10"},
            {"Price": "200.0", "HUqty": "5"},
        ],
    }
    mocker.patch(
        "Executor.ExecutorUtils.BrokerCenter.Brokers.AliceBlue.alice_adapter.Aliceblue",
        return_value=mock_alice,
    )

    user = {
        "Broker": {
            "BrokerUsername": "valid_user",
            "ApiKey": "valid_api_key",
            "SessionId": "valid_session_id",
        }
    }

    result = fetch_aliceblue_holdings_value(user)
    assert result == 2000.0
