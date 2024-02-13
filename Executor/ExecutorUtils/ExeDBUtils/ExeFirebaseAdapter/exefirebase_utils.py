import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import json,math
import datetime

# Fetch the service account key JSON file contents
cred = credentials.Certificate('/Users/amolkittur/Desktop/TradeManV1/firebase_credentials.json')

# Initialize the app with a service account, granting admin privileges
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://trading-app-caf8e-default-rtdb.firebaseio.com/'
})

def file_upload(collection_name):
    with open('/Users/amolkittur/Desktop/TradeManV1/clients.json', 'r') as file:
        data = json.load(file)
        print(data)

    # Set the reference for the data upload
    ref = db.reference(collection_name)# Replace with your desired reference path

    #upload the data
    ref.set(data)
    print("Data uploaded successfully")


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
    with open(file_name, 'w') as file:
        json.dump(data, file,indent=4)

    print(f"Data downloaded successfully to {file_name}")

def main():
    # file_upload("trademan_clients")
    # update_fields_firebase()
    download_json("new_clients", "orders")

# main()