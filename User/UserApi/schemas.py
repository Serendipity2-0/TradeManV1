from pydantic import BaseModel
from pydantic.fields import Field
from typing import Optional
from typing import List, Dict
import datetime


class Equity(BaseModel):
    CapitalAllocation: int = Field(..., example=100)
    Equity_FreeCash: float = Field(
        ..., alias="11Jul24_Equity_FreeCash", example=141558.6
    )
    Equity_Holdings: float = Field(..., alias="11Jul24_Equity_Holdings", example=81028)


class Accounts_(BaseModel):
    Equity: Equity
    Portfolio_AccountValue_01Jul24: float = Field(
        ..., alias="01Jul24_Portfolio_AccountValue", example=141559
    )
    Portfolio_FreeCash_01Jul24: float = Field(
        ..., alias="01Jul24_Portfolio_FreeCash", example=141558.6
    )
    Portfolio_Holdings_01Jul24: float = Field(
        ..., alias="01Jul24_Portfolio_Holdings", example=81028
    )
    Portfolio_FreeCash_02Jul24: float = Field(
        ..., alias="02Jul24_Portfolio_FreeCash", example=141507.7
    )
    Portfolio_AccountValue_02Jul24: float = Field(
        ..., alias="02Jul24_Portfolio_AccountValue", example=141507.7
    )
    Portfolio_Holdings_02Jul24: float = Field(
        ..., alias="02Jul24_Portfolio_Holdings", example=81028
    )


class Broker_(BaseModel):
    ApiKey: str = Field(..., example="")
    ApiSecret: str = Field(..., example="")
    BrokerName: str = Field(..., example="Zerodha")
    BrokerPassword: str = Field(..., example="")
    BrokerUsername: str = Field(..., example="")
    SessionId: str | None = Field(default="", example="")
    TotpAccess: str = Field(..., example="")


class RiskProfile_(BaseModel):
    AreaOfInvestment: List[str] = Field(..., example=["Debt", "Equity", "Derivatives"])
    Commission: str = Field(..., example="50-50")
    DrawdownTolerance: str = Field(..., example="35")
    Duration: str = Field(..., example="12 months")
    WithdrawalFrequency: str = Field(..., example="OnRequest")


class Profile_(BaseModel):
    AadharCardNo: str = Field(..., example="234")
    AccountStartDate: str = Field(..., example="03Jul23")
    BankAccountNo: str = Field(..., example="234")
    BankName: str = Field(..., example="State Bank of India")
    DOB: str = Field(..., example="25Apr90")
    Email: str = Field(..., example="nightysky123123asdkk@gmail.com")
    GmailPassword: str = Field(..., example="a")
    Name: str = Field(..., example="Omkar Hegde")
    PANCardNo: str = Field(..., example="asddfasdf")
    PhoneNumber: str = Field(..., example="+asdfsadf")
    RiskProfile: RiskProfile_ = Field(...)
    pwd: str = Field(..., example="a")
    usr: str = Field(..., example="0")


class StrategyDetail_(BaseModel):
    AllocationPercent: float = Field(..., example=33.33)
    Qty: int = Field(..., example=28)
    RiskPerTrade: float = Field(..., example=1)
    StrategyName: str = Field(..., example="Midterm_Strategy1")


class SubStrategy_(BaseModel):
    AllocationPercent: int = Field(..., example=50)
    Strategy1: StrategyDetail_
    Strategy2: StrategyDetail_
    Strategy3: StrategyDetail_


class EquityStrategy_(BaseModel):
    MidTerm: SubStrategy_


class Strategies_(BaseModel):
    Equity: EquityStrategy_


class UserDetails(BaseModel):
    Accounts: Accounts_
    Active: bool = Field(default=False, example=False)  # Changed to boolean
    Broker: Broker_
    Profile: Profile_
    Strategies: Strategies_


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


class MarketInfoParams(BaseModel):
    TradeView: str
    EquityQtyAmplifier: float
    OBQtyAmplifier: float
    OSQtyAmplifier: float
