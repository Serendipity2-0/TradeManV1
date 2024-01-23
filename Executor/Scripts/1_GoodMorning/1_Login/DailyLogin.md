Name: Login
Status: In Progress
Description:1. Print Shree Ganeshaya Namha
            2. Print Market is Supreme
            3. Fetch active users from firebase
            4. Login into respective accounts and fetch session_id and access_token and store it in firebase
            5. Calculate qty based on the account current value
            6. Clear all completed orders from the user/strategies/orders in firebase
SampleData: user_sample.json
Dependencies: [BrokerUtils, OrderCenterUtils, ExeFirebaseUtils]
Notification : On failure


NOTES:
1. For AliceBlue:
    pip install pycryptodome==3.18.0
    pip install pyotp==2.8.0

2. For Zerodha:
    pip install undetected-chromedriver==3.5.0
    pip install webdriver-manager==4.0.0
    pip install selenium==4.9.1