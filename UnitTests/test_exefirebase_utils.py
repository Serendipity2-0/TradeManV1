import os, sys
import pytest
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials


# Add the necessary path
DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

# Load environment variables
ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

# Initialize Firebase
cred_path = os.getenv("FIREBASE_CRED_PATH")
database_url = os.getenv("FIREBASE_DATABASE_URL")
if cred_path is None:
    raise ValueError("FIREBASE_CRED_PATH environment variable is not set.")
if database_url is None:
    raise ValueError("FIREBASE_DATABASE_URL environment variable is not set.")

if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred, {"databaseURL": database_url})

# Import the functions to test
from Executor.ExecutorUtils.LoggingCenter.logger_utils import LoggerSetup

from Executor.ExecutorUtils.ExeDBUtils.ExeFirebaseAdapter.exefirebase_utils import (
    file_upload,
    update_fields_firebase,
    download_json,
)

# Set up the logger
logger = LoggerSetup()

# Define the directory where the JSON files will be saved
EOD_JSON_DIR = os.path.join(os.getcwd(), "Data/FBJsonData")


@pytest.fixture(scope="module", autouse=True)
def setup_directory():
    # Ensure the directory exists before running tests
    if not os.path.exists(EOD_JSON_DIR):
        os.makedirs(EOD_JSON_DIR)
    yield
    # Cleanup code if necessary


def test_file_upload():
    # Determine the base directory (assuming this script is in the same directory as the test)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # Create the relative path to the JSON file
    test_json_path = os.path.join(
        BASE_DIR, "IntegrationTest", "TestData", "test_data.json"
    )

    # Ensure the file exists before proceeding (optional check)
    if not os.path.exists(test_json_path):
        raise FileNotFoundError(f"JSON file not found: {test_json_path}")

    test_collection_name = "test"

    # Call the file_upload function (assume it's defined elsewhere)
    file_upload(test_json_path, test_collection_name)

    print(f"Uploaded data from {test_json_path} to {test_collection_name} in Firebase.")


def test_update_fields_firebase():
    test_collection = "testCollection"
    test_document = "testDocument"
    test_data = {"field1": "value1", "field2": "value2"}
    update_fields_firebase(test_collection, test_document, test_data)
    print(
        f"Updated fields in {test_document} of {test_collection} with {test_data} in Firebase."
    )


def test_download_json():
    test_path = "testPath"
    test_status = "testStatus"
    download_json(test_path, test_status)
    print(
        f"Downloaded data from {test_path} in Firebase and saved as JSON with status {test_status}."
    )


if __name__ == "__main__":
    pytest.main(["-v", __file__])
