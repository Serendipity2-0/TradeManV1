from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os, sys

DIR_PATH = os.getcwd()
sys.path.append(DIR_PATH)

ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

# This is now just the folder path
DATABASE_FOLDER = os.getenv("USR_TRADELOG_DEBT_DB_FOLDER")

Base = declarative_base()


def get_engine_for_user(tr_no):
    """
    Creates a database engine for a given user.

    Args:
        tr_no (str): The trader number.

    Returns:
        Engine: The database engine.
    """
    db_file = f"{tr_no}_debt.db"
    db_path = os.path.join(DATABASE_FOLDER, db_file)

    # Create the directory if it doesn't exist
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # Create an empty file if it doesn't exist
    if not os.path.exists(db_path):
        open(db_path, "a").close()

    engine = create_engine(f"sqlite:///{db_path}")
    return engine


def get_db_session(tr_no):
    """
    Get a database session for a given user.

    Args:
        tr_no (str): The trader number.

    Returns:
        Session: The database session.
    """
    engine = get_engine_for_user(tr_no)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def init_db(tr_no):
    """
    Initialize the database for a given user.

    Args:
        tr_no (str): The trader number.
    """
    engine = get_engine_for_user(tr_no)
    Base.metadata.create_all(bind=engine)
