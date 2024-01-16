import os, sys
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, '.env')
load_dotenv(ENV_PATH)

cred_filepath = os.getenv('FIREBASE_CRED_PATH')

cred = credentials.Certificate(cred_filepath)
firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://trading-app-caf8e-default-rtdb.firebaseio.com/'
    })

def fetch_collection_data_firebase(collection):
    ref = db.reference(collection)
    data = ref.get()
    return data

def update_fields_firebase(collection, username,data, field_key=None):
    # Create a reference to the user or to the specific field
    if field_key is None:
        ref = db.reference(f'{collection}/{username}')
    else:
        ref = db.reference(f'{collection}/{username}/{field_key}')

    
    ref.update(data)  # Update only the specific field
