def test_register_user_with_valid_details():
    from fastapi.testclient import TestClient
    from User.UserApi.main import app_user

    client = TestClient(app_user)

    user_details = {
        "Accounts": {
            "CurrentBaseCapital": 1000,
            "CurrentWeekCapital": 500,
            "Drawdown": 0,
            "NetAdditions": 100,
            "NetCharges": 10,
            "NetCommission": 5,
            "NetPnL": 50,
            "NetWithdrawals": 20,
            "PnLWithdrawals": 10,
        },
        "Active": {"Active": True},
        "Broker": {
            "ApiKey": "api_key",
            "ApiSecret": "api_secret",
            "BrokerName": "Zerodha",
            "BrokerPassword": "password",
            "BrokerUsername": "username",
            "SessionId": "",
            "TotpAccess": "totp_access",
        },
        "Profile": {
            "AadharCardNo": "123456789012",
            "AccountStartDate": "2023-01-01",
            "BankAccountNo": "1234567890",
            "BankName": "State Bank of India",
            "DOB": "1990-01-01",
            "Email": "test@example.com",
            "GmailPassword": "gmail_password",
            "Name": "Omkar Hegde",
            "PANCardNo": "ABCDE1234F",
            "PhoneNumber": "9876543210",
            "RiskProfile": {},
            "pwd": "password",
            "usr": "username",
        },
        "Strategies": {
            "Strategy1": {"Qty": 10, "RiskPerTrade": 0.75, "StrategyName": "MPWizard"}
        },
    }

    response = client.post("/register", json=user_details)
    assert response.status_code == 200
