import firebase_admin
from firebase_admin import credentials, initialize_app, get_app
from firebase_admin import db
import json,math
import datetime
import os,sys
from dotenv import load_dotenv

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
EOD_JSON_DIR = os.path.join(DIR_PATH, "Data/FBJsonData")
load_dotenv(ENV_PATH)

cred_filepath = os.getenv("FIREBASE_CRED_PATH")

# Firebase database URL
database_url = os.getenv("FIREBASE_DATABASE_URL")

# Fetch the service account key JSON file contents
cred = credentials.Certificate(cred_filepath)

app_name = 'TradeManV1'

try:
    firebase_app = firebase_admin.get_app(app_name)
except ValueError:
    firebase_app = firebase_admin.initialize_app(cred, {"databaseURL": database_url}, name=app_name)



def file_upload(json_path,collection_name):
    with open(json_path, 'r') as file:
        data = json.load(file)

    # Set the reference for the data upload
    ref = db.reference(collection_name)# Replace with your desired reference path

    #upload the data
    ref.set(data)

def update_fields_firebase(collection, document, data, field_key=None):
    if field_key is None:
        ref = db.reference(f"{collection}/{document}")
    else:
        ref = db.reference(f"{collection}/{document}/{field_key}")
    ref.update(data)

def download_json(path, status):
    # Get the current date and time
    now = datetime.datetime.now()
    date_time = now.strftime("%d%b")

    # Set the reference for the data download
    ref = db.reference(path)  # Replace with your desired reference path

    # Download the data
    data = ref.get()

    # Save the data to a file with the current date and time
    file_name = f"{date_time}_{status}.json"
    with open(f"{EOD_JSON_DIR}/{file_name}", 'w') as file:
        json.dump(data, file,indent=4)
