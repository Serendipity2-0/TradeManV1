"""
Common utility functions used across different modules.
"""

import pandas as pd
from datetime import datetime, timedelta
from fastapi import HTTPException
from typing import Optional
import os
from dotenv import load_dotenv

DIR_PATH = os.getcwd()
ENV_PATH = os.path.join(DIR_PATH, "trademan.env")
load_dotenv(ENV_PATH)

def safe_str(value) -> Optional[str]:
    """
    Converts a value to string, handling NaN values.

    Args:
        value: The value to convert to string.

    Returns:
        str: The string representation of the value, or None if the value is NaN.
    """
    if pd.isna(value):
        return None
    return str(value)

def safe_float(value) -> Optional[float]:
    """
    Converts a value to float, handling NaN values.

    Args:
        value: The value to convert to float.

    Returns:
        float: The float representation of the value, or None if the value is NaN.
    """
    if pd.isna(value):
        return None
    try:
        return float(value)
    except ValueError:
        return None

def safe_int(value) -> Optional[int]:
    """
    Converts a value to int, handling NaN values.

    Args:
        value: The value to convert to int.

    Returns:
        int: The int representation of the value, or None if the value is NaN.
    """
    if pd.isna(value):
        return None
    try:
        return int(value)
    except ValueError:
        return None

def parse_date(date_str: str) -> datetime:
    """
    Parses a date string in YYYY-MM-DD format into a datetime object.

    Args:
        date_str (str): The date string in YYYY-MM-DD format.

    Returns:
        datetime: The parsed datetime object.
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date format: {date_str}. Expected YYYY-MM-DD.",
        )

def get_current_week_start_end() -> tuple[datetime, datetime]:
    """
    Returns the start and end dates of the current week (Monday to Sunday).

    Returns:
        tuple[datetime, datetime]: The start and end dates of the current week.
    """
    today = datetime.now()
    week_start = today - timedelta(days=today.weekday())  # Monday
    week_end = week_start + timedelta(days=6)  # Sunday
    return week_start, week_end

def get_current_month_name() -> str:
    """
    Returns the current month's name.

    Returns:
        str: The current month's name.
    """
    return datetime.now().strftime("%B")

def get_date_range(weekStart: str, weekEnd: str) -> tuple[datetime, datetime]:
    """
    Gets the start and end dates for a given week range.

    Args:
        weekStart (str): The start date of the week in YYYY-MM-DD format.
        weekEnd (str): The end date of the week in YYYY-MM-DD format.

    Returns:
        tuple[datetime, datetime]: The start and end dates.
    """
    if weekStart:
        start_date = parse_date(weekStart)
    else:
        start_date, _ = get_current_week_start_end()
    
    if weekEnd:
        end_date = parse_date(weekEnd)
    else:
        _, end_date = get_current_week_start_end()
        if not weekStart:
            end_date = start_date + timedelta(days=6)

    if start_date > end_date:
        raise HTTPException(
            status_code=400, detail="weekStart cannot be after weekEnd."
        )

    return start_date, end_date
