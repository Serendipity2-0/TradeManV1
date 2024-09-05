from .postgres_connection import PostgresConnection
from .mongo_connection import MongoConnection
from .models import CompletedTrades, Holdings, Signals
from bson.objectid import ObjectId


class PostgresRepo:
    def __init__(self, db_connection: PostgresConnection):
        self.db = db_connection

    def create(self, model):
        with self.db.get_session() as session:
            session.add(model)
            session.commit()
            return model

    def read(self, model_class, trade_id):
        with self.db.get_session() as session:
            return session.query(model_class).get(trade_id)

    def update(self, model):
        with self.db.get_session() as session:
            session.merge(model)
            session.commit()
            return model

    def delete(self, model):
        with self.db.get_session() as session:
            session.delete(model)
            session.commit()

    def list(self, model_class, **filters):
        with self.db.get_session() as session:
            query = session.query(model_class)
            for attr, value in filters.items():
                query = query.filter(getattr(model_class, attr) == value)
            return query.all()


class MongoRepo:
    def __init__(self, mongo_connection: MongoConnection, collection_name: str):
        self.mongo = mongo_connection
        self.collection = self.mongo.get_collection(collection_name)

    def create(self, document):
        result = self.collection.insert_one(document)
        return result.inserted_id

    def read(self, document_id):
        return self.collection.find_one({"_id": ObjectId(document_id)})

    def update(self, document_id, update_data):
        result = self.collection.update_one(
            {"_id": ObjectId(document_id)}, {"$set": update_data}
        )
        return result.modified_count

    def delete(self, document_id):
        result = self.collection.delete_one({"_id": ObjectId(document_id)})
        return result.deleted_count

    def list(self, **filters):
        return list(self.collection.find(filters))


class Repo:
    def __init__(
        self, postgres_connection: PostgresConnection, mongo_connection: MongoConnection
    ):
        self.postgres = PostgresRepo(postgres_connection)
        self.mongo = {
            "completed_trades": MongoRepo(mongo_connection, "completed_trades"),
            "holdings": MongoRepo(mongo_connection, "holdings"),
            "signals": MongoRepo(mongo_connection, "signals"),
        }

    def create(self, model, use_mongo=False):
        if use_mongo:
            collection = self._get_mongo_collection(model.__class__)
            return collection.create(model.to_dict())
        else:
            return self.postgres.create(model)

    def read(self, model_class, trade_id, use_mongo=False):
        if use_mongo:
            collection = self._get_mongo_collection(model_class)
            return collection.read(trade_id)
        else:
            return self.postgres.read(model_class, trade_id)

    def update(self, model, use_mongo=False):
        if use_mongo:
            collection = self._get_mongo_collection(model.__class__)
            return collection.update(str(model.trade_id), model.to_dict())
        else:
            return self.postgres.update(model)

    def delete(self, model, use_mongo=False):
        if use_mongo:
            collection = self._get_mongo_collection(model.__class__)
            return collection.delete(str(model.trade_id))
        else:
            return self.postgres.delete(model)

    def list(self, model_class, use_mongo=False, **filters):
        if use_mongo:
            collection = self._get_mongo_collection(model_class)
            return collection.list(**filters)
        else:
            return self.postgres.list(model_class, **filters)

    def _get_mongo_collection(self, model_class):
        if model_class == CompletedTrades:
            return self.mongo["completed_trades"]
        elif model_class == Holdings:
            return self.mongo["holdings"]
        elif model_class == Signals:
            return self.mongo["signals"]
        else:
            raise ValueError(f"Unknown model class: {model_class}")


# Usage example:
# postgres_connection = PostgresConnection()
# mongo_connection = MongoConnection()
# repo = Repo(postgres_connection, mongo_connection)
#
# # Create a new completed trade in PostgreSQL
# new_trade = CompletedTrades(user_id="user123", strategy="strategy1", trading_symbol="AAPL", ...)
# created_trade = repo.create(new_trade)
#
# # Read a holding from MongoDB
# holding = repo.read(Holdings, trade_id=1, use_mongo=True)
#
# # Update a signal in PostgreSQL
# signal = repo.read(Signals, trade_id=1)
# signal.exit_price = 150.5
# updated_signal = repo.update(signal)
#
# # Delete a completed trade from MongoDB
# repo.delete(completed_trade, use_mongo=True)
#
# # List all holdings for a specific user from PostgreSQL
# user_holdings = repo.list(Holdings, user_id="user123")
#
# # List all signals for a specific strategy from MongoDB
# strategy_signals = repo.list(Signals, use_mongo=True, strategy="strategy1")


"""
This module provides repository classes for database operations on both PostgreSQL and MongoDB.

It includes separate repository classes for PostgreSQL and MongoDB operations,
as well as a main Repo class that combines both to provide a unified interface
for database operations. This allows for flexible switching between databases
for different operations.

Classes:
    PostgresRepo: Handles CRUD operations for PostgreSQL database.
    MongoRepo: Handles CRUD operations for MongoDB collections.
    Repo: Main repository class that uses both PostgresRepo and MongoRepo
          to provide a unified interface for database operations.

The Repo class allows specifying whether to use MongoDB or PostgreSQL for each
operation, making it easy to use different databases for different data or operations
as needed.

Usage:
    postgres_connection = PostgresConnection()
    mongo_connection = MongoConnection()
    repo = Repo(postgres_connection, mongo_connection)
    
    # Use repo for database operations, specifying use_mongo=True for MongoDB operations
    new_trade = CompletedTrades(...)
    repo.create(new_trade, use_mongo=False)
"""
