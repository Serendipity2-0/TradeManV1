from pydantic import BaseModel
from pydantic.fields import Field
from typing import Optional
from typing import List, Dict
import datetime


class Accounts_(BaseModel):
    CurrentBaseCapital: int = Field(..., example=0)
    CurrentWeekCapital: int | None = Field(default=0, example=0)
    Drawdown: int | None = Field(default=0, example=0)
    NetAdditions: int | None = Field(default=0, example=0)
    NetCharges: int | None = Field(default=0, example=0)
    NetCommission: int | None = Field(default=0, example=0)
    NetPnL: int | None = Field(default=0, example=0)
    NetWithdrawals: int | None = Field(default=0, example=0)
    PnLWithdrawals: int | None = Field(default=0, example=0)


class Active_(BaseModel):
    Active: bool = Field(default=False, example=False)


class Broker_(BaseModel):
    ApiKey: str = Field(..., example="")
    ApiSecret: str = Field(..., example="")
    BrokerName: str = Field(..., example="Zerodha")
    BrokerPassword: str = Field(..., example="")
    BrokerUsername: str = Field(..., example="")
    SessionId: str | None = Field(default="", example="")
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


class LoginUserDetails(BaseModel):
    Email: str
    # Phone_Number: str
    Password: str


class ProfilePage(BaseModel):
    Name: str
    Email: str
    Phone_Number: str
    Date_of_Birth: str
    Aadhar_Card_No: str
    PAN_Card_No: str
    Bank_Name: str
    Bank_Account_No: str
    BrokerName: Optional[str] = None
    Strategies: Optional[List[str]] = None


class ClientData(BaseModel):
    profile: ProfilePage
    strategies: Optional[List[str]] = None
