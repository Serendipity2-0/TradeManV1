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
    Extracts timestamp, module, and error message from a log line.
    
    :param line: A log line in the format "YYYY-MM-DD HH:MM:SS.mmm | ERROR    | <module_path>:<something> - <error_message>"
    :return: Tuple (timestamp, module, error_message) if the pattern matches; (None, None, None) otherwise.
    """
    pattern = r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) \| ERROR    \| (.+?):(.+?) - (.+)$"
    match = re.search(pattern, line)
    if match:
        timestamp = match.group(1)
        full_module_path = match.group(2).strip()
        module = full_module_path.split('.')[-1]  # Get the last part of the module path
        error_message = match.group(4).strip()
        return timestamp, module, error_message
    else:
        logger.debug(f"No pattern match for line: {line}")
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

    with open(ERROR_LOG_PATH, 'r') as file:
        for line in file:
            if "| ERROR    |" in line:
                timestamp, module, error_message = extract_error_details_with_timestamp(line)
                if module and error_message:
                    timestamps.append(timestamp)
                    modules.append(module)
                    errors.append(error_message)

    if not errors:
        logger.debug("No errors found in the log.")
        return pd.DataFrame()  # Return an empty DataFrame if there are no errors

    error_counts = Counter(errors)
    unique_errors = {}
    for timestamp, module, error in zip(timestamps, modules, errors):
        if error in unique_errors:
            unique_errors[error]['Timestamp'] = timestamp
        else:
            unique_errors[error] = {'Timestamp': timestamp, 'Module': module, 'Count': error_counts[error]}

    error_df = pd.DataFrame([{
        'Timestamp': details['Timestamp'],
        'Module': details['Module'],
        'Error': error,
        'Count': details['Count']
    } for error, details in unique_errors.items()])

    error_df_sorted = error_df.sort_values(by='Timestamp', ascending=False).reset_index(drop=True)

    with open(os.path.join(DIR_PATH, ERROR_LOG_CSV_PATH), 'a') as f:
        error_df_sorted.to_csv(f, header=f.tell()==0, index=False)

    return error_df_sorted
