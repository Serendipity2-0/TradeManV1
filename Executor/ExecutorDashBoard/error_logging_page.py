import os,sys
from dotenv import load_dotenv
import pandas as pd
import re
from collections import Counter

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

logger = LoggerSetup()

ERROR_LOG_PATH = os.getenv('ERROR_LOG_PATH')
ERROR_LOG_CSV_PATH = os.getenv("ERROR_LOG_CSV_PATH")

# Resetting the lists to ensure clean data collection
timestamps = []
modules = []
errors = []

# Adjust the function to extract the timestamp as well
def extract_error_details_with_timestamp(line):
    """
    The function `extract_error_details_with_timestamp` extracts timestamp, module, and error message
    from a log line with a specific format.
    
    :param line: The function `extract_error_details_with_timestamp` takes a log line as input and
    extracts the timestamp, module name, and error message from it. The log line should be in the format
    specified by the regular expression pattern in the function
    :return: The function `extract_error_details_with_timestamp` returns a tuple containing the
    timestamp, module, and error message extracted from the input line if the pattern matches. If there
    is no match, it returns a tuple of None values.
    """
    pattern = r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) \| ERROR    \| (.+?):(.+?) - (.+)$"
    match = re.search(pattern, line)
    if match:
        timestamp = match.group(1)
        full_module_path = match.group(2).strip()
        module = full_module_path.split('.')[-1]
        error_message = match.group(4).strip()
        return timestamp, module, error_message
    return None, None, None


def read_n_process_err_log():
    """
    The function reads and processes an error log file, extracts error details, counts occurrences of
    each error message, aggregates unique errors with their latest timestamp, module, and count,
    converts the data to a DataFrame, and appends the processed data to a CSV file.
    :return: The function `read_n_process_err_log` returns a DataFrame containing unique error messages
    along with their latest timestamp, module, occurrence count, and sorted by timestamp in descending
    order. This DataFrame is also logged using the `logger.debug` function and appended to an existing
    CSV file specified by `ERROR_LOG_CSV_PATH`.
    """
    timestamps, modules, errors = [], [], []
    
    # Re-process the log file with the corrected function
    with open(ERROR_LOG_PATH, 'r') as file:
        for line in file:
            if "| ERROR    |" in line:
                timestamp, module, error_message = extract_error_details_with_timestamp(line)
                if module and error_message:
                    timestamps.append(timestamp)
                    modules.append(module)
                    errors.append(error_message)
    
    # Count occurrences of each error message
    error_counts = Counter(errors)
    
    # Create a dictionary to aggregate unique errors with their latest timestamp, module, and count
    unique_errors = {}
    for timestamp, module, error in zip(timestamps, modules, errors):
        # If error is already encountered, update the timestamp to the latest one
        if error in unique_errors:
            unique_errors[error]['Timestamp'] = timestamp  # Update to the latest timestamp
        else:
            unique_errors[error] = {'Timestamp': timestamp, 'Module': module, 'Count': error_counts[error]}
    
    # Convert the unique_errors dictionary to a DataFrame
    error_df = pd.DataFrame([
        {
            'Timestamp': details['Timestamp'],
            'Count': details['Count'],  # Using Count instead of ErNo
            'Module': details['Module'],
            'Error': error
        }
        for error, details in unique_errors.items()
    ])
    
    # Adding the occurrence count to each error message
    error_df['Error'] = error_df.apply(lambda x: f"{x['Error']}", axis=1)
    
    error_df_sorted = error_df.sort_values(by='Timestamp', ascending=False).reset_index(drop=True)
    logger.debug(error_df_sorted)
    
    # Append the error log to existing csv file # WARN: Add variable in TradeMan.env for csv path
    with open(os.path.join(DIR_PATH, ERROR_LOG_CSV_PATH), 'a') as f:
        error_df_sorted.to_csv(f, header=f.tell()==0, index=False)
    
    return error_df_sorted


