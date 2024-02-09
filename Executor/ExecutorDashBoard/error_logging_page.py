from loguru import logger
import os,sys
from dotenv import load_dotenv
import pandas as pd
import re

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

from loguru import logger

ERROR_LOG_PATH = os.getenv("ERROR_LOG_PATH")
logger.add(
    ERROR_LOG_PATH,
    level="TRACE",
    rotation="00:00",
    enqueue=True,
    backtrace=True,
    diagnose=True,
)

# Resetting the lists to ensure clean data collection
timestamps = []
modules = []
errors = []

# Adjust the function to extract the timestamp as well
def extract_error_details_with_timestamp(line):
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
    # Re-process the log file with the corrected function
    with open(ERROR_LOG_PATH, 'r') as file:
        for line in file:
            if "| ERROR    |" in line:
                timestamp, module, error_message = extract_error_details_with_timestamp(line)
                if module and error_message:
                    timestamps.append(timestamp)
                    modules.append(module)
                    errors.append(error_message)

    # Now, create the DataFrame with the corrected lists
    error_df_with_timestamp = pd.DataFrame({
        'Timestamp': pd.to_datetime(timestamps),
        'ErNo': range(1, len(timestamps) + 1),
        'Module': modules,
        'Error': errors
    })
    
    error_df_sorted = error_df_with_timestamp.sort_values(by='Timestamp', ascending=False).reset_index(drop=True)
    logger.debug(error_df_sorted)
    
    error_df_sorted.to_csv(os.path.join(DIR_PATH, "error_log.csv"), index=False)
    
    return error_df_sorted


