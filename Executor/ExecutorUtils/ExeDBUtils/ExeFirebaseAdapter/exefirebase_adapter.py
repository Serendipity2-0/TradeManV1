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
firebase_db_url = os.getenv('FIREBASE_DATABASE_URL')

cred = credentials.Certificate(cred_filepath)
firebase_admin.initialize_app(cred, {
        'databaseURL': firebase_db_url
    })

def fetch_collection_data_firebase(collection,document=None):
    # Create a reference to the collection
    ref = db.reference(collection)
    if document is None:
        return ref.get()
    else:
        data= ref.child(document).get()
        return data

def update_fields_firebase(collection, document, data, field_key=None):
    # Create a reference to the user or to the specific field
    if field_key is None:
        ref = db.reference(f'{collection}/{document}')
    else:
        ref = db.reference(f'{collection}/{document}/{field_key}')
    ref.update(data)  # Update only the specific field
