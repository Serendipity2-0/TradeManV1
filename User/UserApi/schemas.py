from pydantic import BaseModel
from pydantic.fields import Field
from typing import Optional
from typing import List, Dict
import datetime


# {
#   "Accounts": {
#     "CurrentBaseCapital": , # cumpulary
#     "CurrentWeekCapital": ,
#     "Drawdown": 0,
#     "NetAdditions": ,
#     "NetCharges": ,
#     "NetCommission": 0,
#     "NetPnL": ,
#     "NetWithdrawals": ,
#     "PnLWithdrawals": 
#   },
#   "Active": false,
#   "Broker": { # compusary
#     "ApiKey": "",
#     "ApiSecret": "",
#     "BrokerName": "",
#     "BrokerPassword": "",
#     "BrokerUsername": "",
#     "SessionId": "", # not compulsary initialize with ""
#     "TotpAccess": ""
#   },
#   "Profile": { # compulsary
#     "AadharCardNo": "--",
#     "AccountStartDate": "--",
#     "BankAccountNo": "--",
#     "BankName": "State Bank of India",
#     "DOB": "--",
#     "Email": "--",
#     "GmailPassword": "",
#     "Name": "",
#     "PANCardNo": "--",
#     "PhoneNumber": "+--",
#     "RiskProfile": {
#       "AreaOfInvestment": [
#         "Debt",
#         "Equity",
#         "FnO"
#       ],
#       "Commission": "",
#       "DrawdownTolerance": "",
#       "Duration": "",
#       "WithdrawalFrequency": ""
#     },
#     "pwd": "a",
#     "usr": "0"
#   },
#   "Strategies": {
#     "MPWizard": {
#       "Qty": , intitialize with 0
#       "RiskPerTrade": , compulasry
#       "StrategyName": "" compulasry
#     }
#   },
#   "Tr_No": "" # compulasry
# }





class Accounts_(BaseModel):
    CurrentBaseCapital: int = Field(..., example=0)
    CurrentWeekCapital: int|None = Field(default=0, example=0)
    Drawdown: int|None = Field(default=0, example=0)
    NetAdditions: int|None = Field(default=0, example=0)
    NetCharges: int|None = Field(default=0, example=0)
    NetCommission: int|None = Field(default=0, example=0)
    NetPnL: int|None = Field(default=0, example=0)
    NetWithdrawals: int|None = Field(default=0, example=0)
    PnLWithdrawals: int|None = Field(default=0, example=0)

class Active_(BaseModel):
    Active: bool = Field(default=False, example=False)

class Broker_(BaseModel):
    ApiKey: str = Field(..., example="")
    ApiSecret: str = Field(..., example="")
    BrokerName: str = Field(..., example="Zerodha")
    BrokerPassword: str = Field(..., example="")
    BrokerUsername: str = Field(..., example="")
    SessionId: str|None = Field(default="", example="")
    TotpAccess: str = Field(..., example="")

class Profile_(BaseModel):
    AadharCardNo: str = Field(..., example="")
    AccountStartDate: str = Field(..., example="")
    BankAccountNo: str = Field(..., example="")
    BankName: str = Field(..., example="State Bank of India")
    DOB: str = Field(..., example="")
    Email: str = Field(..., example="")
    GmailPassword: str = Field(..., example="")
    Name: str = Field(..., example="Omkar Hegde")
    PANCardNo: str = Field(..., example="")
    PhoneNumber: str = Field(..., example="")
    RiskProfile: dict = Field(...)
    pwd: str = Field(..., example="")
    usr: str = Field(..., example="")


    
    

class Strategy_(BaseModel):
    Qty: int = Field(default=0, example=0)
    RiskPerTrade: float = Field(..., example=0.75)
    StrategyName: str = Field(..., example="MPWizard")


class UserDetails(BaseModel):
    # use this to add more schemas
    Accounts: Accounts_ 
    Active: Active_ 
    Broker: Broker_ 
    Profile: Profile_ 
    Strategies: Dict[str, Strategy_] 

    