import os, sys
from dotenv import load_dotenv
from datetime import datetime
import csv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)
PARAMS_UPDATE_LOG_CSV_PATH = os.getenv("PARAMS_UPDATE_LOG_CSV_PATH")

def log_changes(updated_data, section_info=None):
    """
    The function `log_changes` logs updated data along with section information to a CSV file with date
    and time stamp.
    
    :param updated_data: The `updated_data` parameter is the data that has been updated and will be
    logged in the CSV file. It should be provided as an argument when calling the `log_changes` function
    :param section_info: Section_info is an optional parameter that can be passed to the log_changes
    function. It is used to provide additional information about the section being updated in the log
    entry. If section_info is provided, it will be included in the log entry under the "section_info"
    column in the CSV log file
    """
    filename = PARAMS_UPDATE_LOG_CSV_PATH
    headers = ["date", "updated_info", "section_info"]
    date_str = datetime.now().strftime("%d%b%y %I:%M%p")  # Format: 23Feb24 9:43AM

    with open(filename, mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        
        # Write headers if file is being created for the first time
        if not os.path.isfile(filename):
            writer.writeheader()

        log_entry = {
            "date": date_str,
            "updated_info": str(updated_data),  # Corrected key to match header
            "section_info": section_info if section_info else ""
        }
        
        writer.writerow(log_entry)