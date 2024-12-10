"""
This module contains Pydantic model classes for NSE strategies.
"""

import datetime as dt
from datetime import time
from typing import Dict, List, Optional, Union
from pydantic import BaseModel

class EntryParams(BaseModel):
    EntryTime: str
    HedgeMultiplier: Optional[int] = None
    InstrumentToday: Optional[Union[str, dict]] = None
    SLMultiplier: Optional[float] = None
    StrikeMultiplier: Optional[int] = None
    HeikinAshiMAPeriod: Optional[int] = None
    SupertrendPeriod: Optional[int] = None
    SupertrendMultiplier: Optional[int] = None
    EMAPeriod: Optional[int] = None

    class Config:
        extra = "allow"


class ExitParams(BaseModel):
    SLType: str
    SquareOffTime: Optional[str] = None
    LastBuyTime: Optional[str] = None
    AvgSLPoints: Optional[float] = None

    class Config:
        extra = "allow"


class ExtraInformation(BaseModel):
    QtyCalc: str
    PriceRef: Optional[Dict[str, List[int]]] = None
    Interval: Optional[str] = None
    HedgeDistance: Optional[int] = None
    Prediction: Optional[str] = None
    HedgeExchangeToken: Optional[int] = None
    FuturesExchangeToken: Optional[int] = None
    MultiLeg: Optional[bool] = None

    class Config:
        extra = "allow"


class GeneralParams(BaseModel):
    ExpiryType: Union[str, List[str]]
    HedgeTransactionType: Optional[str] = None
    MainTransactionType: Optional[str] = None
    TransactionType: Optional[str] = None
    OrderType: str
    ProductType: str
    StrategyType: Optional[str] = None
    TimeFrame: str
    ATRPeriod: Optional[int] = None
    IndicesTokens: Optional[Dict[str, int]] = None

    class Config:
        extra = "allow"


class StrategyInfo(BaseModel):
    Direction: Optional[str]
    MarginUsed: Optional[float]
    PeakLoss: Optional[float]
    PeakProfit: Optional[float]

    class Config:
        extra = "allow"


class TodayOrder(BaseModel):
    EntryPrc: Optional[float] = None
    EntryTime: Optional[dt.datetime] = None
    ExitPrc: Optional[float] = None
    ExitTime: Optional[time] = None
    Signal: Optional[str] = None
    StrategyInfo: Optional[Dict[str, Union[str, float]]] = None
    TradeId: Optional[str] = None

    class Config:
        extra = "allow"


class MarketInfoParams(BaseModel):
    OBQtyAmplifier: Optional[float] = None
    OSQtyAmplifier: Optional[float] = None
    TradeView: str


class StrategyBase(BaseModel):
    Description: str
    EntryParams: EntryParams
    ExitParams: ExitParams
    ExtraInformation: ExtraInformation
    GeneralParams: GeneralParams
    Instruments: List[str]
    NextTradeId: Optional[str] = None
    StrategyName: str
    StrategyPrefix: Optional[str] = None
    MarketInfoParams: MarketInfoParams
    TodayOrders: Optional[Dict[str, TodayOrder]] = None

    class Config:
        extra = "allow"

    def __init__(self, **data):
        """Initialize with raw data storage."""
        super().__init__(**data)
        self._raw_data = data

    def get_raw_field(self, field_name: str):
        """Get a field from the raw data."""
        return self._raw_data.get(field_name, None)

    def update_strategy_info(self, strategy_name):
        """Update strategy information."""
        return {
            "Instruments": self.Instruments,
            "StrategyName": strategy_name
        }
