from pydantic import BaseModel, RootModel
from pydantic.fields import Field
from typing import Optional
from typing import List, Dict
from datetime import datetime


class Equity_(BaseModel):
    CapitalAllocation: int = Field(..., example=100)
    Equity_FreeCash: float = Field(..., alias="Equity_FreeCash", example=141558.6)
    Equity_Holdings: float = Field(..., alias="Equity_Holdings", example=81028)
    Equity_AccountValue: float = Field(
        ..., alias="Equity_AccountValue", example=141558.6
    )


class Debt_(BaseModel):
    CapitalAllocation: int = Field(..., example=50)
    Debt_FreeCash: float = Field(..., alias="Debt_FreeCash", example=50000.0)
    Debt_Holdings: float = Field(..., alias="Debt_Holdings", example=25000)
    Debt_AccountValue: float = Field(..., alias="Debt_AccountValue", example=100000.0)


class Derivatives_(BaseModel):
    CapitalAllocation: int = Field(..., example=150)
    Derivatives_FreeCash: float = Field(
        ..., alias="Derivatives_FreeCash", example=75000.0
    )
    Derivatives_Holdings: float = Field(
        ..., alias="Derivatives_Holdings", example=30000
    )
    Derivatives_AccountValue: float = Field(
        ..., alias="Derivatives_AccountValue", example=100000.0
    )


class Portfolio_(BaseModel):
    Portfolio_FreeCash: float = Field(..., alias="Portfolio_FreeCash", example=75000.0)
    Portfolio_Holdings: float = Field(..., alias="Portfolio_Holdings", example=30000)
    Portfolio_AccountValue: float = Field(
        ..., alias="Portfolio_AccountValue", example=100000.0
    )


class Accounts_(BaseModel):
    CurrentBaseCapital: float = Field(..., alias="CurrentBaseCapital", example=100000.0)
    Equity: Optional[Equity_] = Field(
        default=None,
        example={
            "CapitalAllocation": 100,
            "Equity_FreeCash": 141558.6,
            "Equity_Holdings": 81028,
            "Equity_AccountValue": 141558.6,
        },
    )
    Debt: Optional[Debt_] = Field(
        default=None,
        example={
            "CapitalAllocation": 50,
            "Debt_FreeCash": 50000.0,
            "Debt_Holdings": 25000,
            "Debt_AccountValue": 100000.0,
        },
    )
    Derivatives: Optional[Derivatives_] = Field(
        default=None,
        example={
            "CapitalAllocation": 150,
            "Derivatives_FreeCash": 75000.0,
            "Derivatives_Holdings": 30000,
            "Derivatives_AccountValue": 100000.0,
        },
    )
    Portfolio: Portfolio_


class Active_(RootModel[bool]):
    pass


class Broker_(BaseModel):
    ApiKey: str = Field(..., example="")
    ApiSecret: str = Field(..., example="")
    BrokerName: str = Field(..., example="Zerodha")
    BrokerPassword: str = Field(..., example="")
    BrokerUsername: str = Field(..., example="")
    SessionId: Optional[str] = Field(default="", example="")
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


class Strategies_(BaseModel):
    Equity: Optional[Dict]
    Debt: Optional[Dict]
    Derivatives: Optional[Dict]


class LoginUserDetails(BaseModel):
    Email: str
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


class OrderChoice(BaseModel):
    choice: str


class RepairOrderInput(BaseModel):
    strategy_name: str
    users: List[str]
    symbols: List[str]
    qty_calculation_mode: str
    trade_id: str
    qty: Optional[float] = None
    setup_name: Optional[str] = None


class CompleteOrderInput(BaseModel):
    strategy_name: str
    users: List[str]
    symbols: List[str]
    qty_calculation_mode: str
    trade_id: str
    qty: Optional[float] = None
    setup_name: Optional[str] = None
