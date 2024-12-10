"""
This module defines the SQLAlchemy ORM models for the application's database schema.

It includes a base model class and specific model classes for completed trades,
holdings, and signals. These models represent the structure of the database tables
and provide methods for converting model instances to dictionaries.

Classes:
    BaseModel: Abstract base class for all models, defining common fields.
    CompletedTrades: Model for completed trading transactions.
    Holdings: Model for current holdings.
    Signals: Model for trading signals.

Each model class includes relevant fields and a to_dict() method for easy
conversion to a dictionary format, which is useful for serialization and
working with MongoDB.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class BaseModel(Base):
    __abstract__ = True

    trade_id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)
    strategy = Column(String, nullable=False)
    trading_symbol = Column(String, nullable=False)
    signal = Column(String)
    entry_time = Column(DateTime)
    entry_price = Column(Float)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class CompletedTrades(BaseModel):
    __tablename__ = "completed_trades"

    exit_time = Column(DateTime)
    exit_price = Column(Float)
    hedge_entry_price = Column(Float)
    hedge_exit_price = Column(Float)
    trade_points = Column(Float)
    qty = Column(Integer)
    pnl = Column(Float)
    tax = Column(Float)
    net_pnl = Column(Float)

    def to_dict(self):
        return {
            'trade_id': self.trade_id,
            'user_id': self.user_id,
            'strategy': self.strategy,
            'trading_symbol': self.trading_symbol,
            'signal': self.signal,
            'entry_time': self.entry_time,
            'entry_price': self.entry_price,
            'exit_time': self.exit_time,
            'exit_price': self.exit_price,
            'hedge_entry_price': self.hedge_entry_price,
            'hedge_exit_price': self.hedge_exit_price,
            'trade_points': self.trade_points,
            'qty': self.qty,
            'pnl': self.pnl,
            'tax': self.tax,
            'net_pnl': self.net_pnl,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


class Holdings(BaseModel):
    __tablename__ = "holdings"

    hedge_entry_price = Column(Float)
    qty = Column(Integer)
    margin_utilised = Column(Float)
    tax = Column(Float)
    setup = Column(Float)


class Signals(BaseModel):
    __tablename__ = "signals"

    exit_time = Column(DateTime)
    exit_price = Column(Float)
    hedge_entry_price = Column(Float)
    hedge_exit_price = Column(Float)
    trade_points = Column(Float)
    comments = Column(String)
