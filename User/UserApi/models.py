from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class HandLoans(Base):
    __tablename__ = "5HandLoans"

    accID = Column(String, primary_key=True, index=True)
    Balance = Column(Float)
    # Add any other columns that actually exist in your 5HandLoans table


class TransactionsPast(Base):
    __tablename__ = "TransactionsPast"

    TrNo = Column(Integer, primary_key=True)
    Date = Column(DateTime)
    Description = Column(Text)
    Amount = Column(Float)
    PaymentMode = Column(String)
    AccID = Column(String, index=True)
    Department = Column(String)
    Comments = Column(Text)
    Category = Column(String)
    DeductedReceivedThrough = Column(String)
    ZohoMatch = Column(String)
    ExpectedPaymentDate = Column(Float)


class FreedomFuture(Base):
    __tablename__ = "FreedomFuture"

    TrNo = Column(Integer, primary_key=True)
    Date = Column(DateTime)
    Description = Column(Text)
    Amount = Column(Float)
    PaymentMode = Column(String)
    AccID = Column(String, index=True)
    Department = Column(String)
