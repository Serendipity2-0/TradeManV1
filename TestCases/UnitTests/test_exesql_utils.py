import os, sys
import sqlite3
import pandas as pd
import tempfile
import pytest
import time
import psutil

from dotenv import load_dotenv
from openpyxl import load_workbook

# Add the necessary path
DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

# Load environment variables
ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

# Import the functions to test
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

from Executor.ExecutorUtils.ExeDBUtils.SQLUtils.exesql_utils import (
    db_to_excel,
    excel_to_db,
)

# Set up the logger
logger = LoggerSetup()


def force_release_file_lock(file_path):
    """Forcefully release the file lock if it exists."""
    for proc in psutil.process_iter():
        try:
            for item in proc.open_files():
                if item.path == file_path:
                    proc.kill()
        except Exception:
            continue


@pytest.fixture
def setup_test_environment():
    # Create dedicated temporary directories for databases and excel files
    db_dir = tempfile.mkdtemp(dir=os.getcwd())
    excel_dir = tempfile.mkdtemp(dir=os.getcwd())

    # Create a sample SQLite database
    sample_db_path = os.path.join(db_dir, "sample.db")
    conn = sqlite3.connect(sample_db_path)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT)")
    cursor.execute("INSERT INTO test_table (name) VALUES ('Alice'), ('Bob')")
    conn.commit()
    conn.close()

    yield db_dir, excel_dir

    # Cleanup temporary directories with retry mechanism
    def safe_remove(file_path):
        retries = 5
        while retries > 0:
            try:
                os.remove(file_path)
                break
            except PermissionError:
                force_release_file_lock(file_path)
                time.sleep(0.5)  # Increase the sleep time for more retries
                retries -= 1
        if retries == 0:
            raise PermissionError(
                f"Failed to remove {file_path} after several attempts"
            )

    for root, dirs, files in os.walk(db_dir, topdown=False):
        for name in files:
            safe_remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(db_dir)

    for root, dirs, files in os.walk(excel_dir, topdown=False):
        for name in files:
            safe_remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(excel_dir)


def test_db_to_excel(setup_test_environment):
    db_folder, excel_folder = setup_test_environment

    # Convert the database to Excel
    db_to_excel(db_folder, excel_folder)

    # Check if the Excel file is created
    excel_file = os.path.join(excel_folder, "sample.xlsx")
    assert os.path.exists(excel_file), "Excel file was not created."

    # Check if the data is correctly exported to Excel
    df = pd.read_excel(excel_file, sheet_name="test_table")
    assert len(df) == 2, "Excel file does not contain the expected number of rows."
    assert (
        df.iloc[0]["name"] == "Alice"
    ), "Excel file does not contain the correct data."


def test_excel_to_db(setup_test_environment):
    db_folder, excel_folder = setup_test_environment

    # First convert the database to Excel
    db_to_excel(db_folder, excel_folder)

    # Ensure the Excel file is properly closed before proceeding
    excel_file = os.path.join(excel_folder, "sample.xlsx")
    if not os.path.exists(excel_file):
        raise FileNotFoundError(f"{excel_file} does not exist.")

    # Explicitly close the Excel file to release any locks
    wb = load_workbook(excel_file)
    wb.close()

    # Then convert the Excel file back to database
    excel_to_db(excel_folder, db_folder)

    # Check if the database file is created
    db_file = os.path.join(db_folder, "sample.db")
    assert os.path.exists(db_file), "Database file was not created."

    # Check if the data is correctly imported to the database
    conn = sqlite3.connect(db_file)
    df = pd.read_sql_query("SELECT * FROM test_table", conn)
    conn.close()

    assert len(df) == 2, "Database does not contain the expected number of rows."
    assert df.iloc[0]["name"] == "Alice", "Database does not contain the correct data."


if __name__ == "__main__":
    pytest.main(["-v", __file__])
