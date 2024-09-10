"""
This module provides a PostgresConnection class for managing connections to a PostgreSQL database.

The PostgresConnection class handles the initialization of the database connection,
creation of database sessions, and proper disposal of connections when no longer needed.
It uses the configuration from db/__init__.py and implements connection pooling for
better performance and resource management.

Classes:
    PostgresConnection: Manages PostgreSQL database connections and sessions.

Usage:
    connection = PostgresConnection()
    session = connection.get_session()
    # Use the session for database operations
    connection.dispose()
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from . import db_config

class PostgresConnection:
    def __init__(self):
        self._initialize()

    def _initialize(self):
        pg_config = db_config['postgres']
        connection_string = f"postgresql://{pg_config['user']}:{pg_config['password']}@{pg_config['host']}:{pg_config['port']}/{pg_config['name']}"

        self.engine = create_engine(
            connection_string,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,
        )
        self.Session = sessionmaker(bind=self.engine)

    def get_session(self):
        return self.Session()

    def dispose(self):
        self.engine.dispose()

# Usage remains the same
