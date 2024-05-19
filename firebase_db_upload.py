import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import json,math

# Fetch the service account key JSON file contents
cred = credentials.Certificate('/Users/amolkittur/Desktop/TradeManV1/Executor/ExecutorUtils/ExeDBUtils/ExeFirebaseAdapter/firebase_credentials.json')

# Initialize the app with a service account, granting admin privileges
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://trademanv1-default-rtdb.asia-southeast1.firebasedatabase.app/'
})

with open('/Users/amolkittur/Desktop/TradeManV1/clients.json', 'r') as file:
# with open('/Users/amolkittur/Desktop/TradeManV1/strategies.json', 'r') as file:
    data = json.load(file)

# Set the reference for the data upload
# ref = db.reference('temp_strategies')  # Replace with your desired reference path
ref = db.reference('temp_clients')  # Replace with your desired reference path
# ref = db.reference('trademan_clients')  # Replace with your desired reference path

#upload the data
ref.set(data)
print("Data uploaded successfully")