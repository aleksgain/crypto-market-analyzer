"""Datetime utilities for the Market Analyzer API."""

from datetime import datetime, timezone

def get_utc_now():
    """Return current datetime with UTC timezone."""
    return datetime.now(timezone.utc)

def ensure_timezone(dt):
    """Ensure a datetime has timezone information.
    
    Args:
        dt: A datetime object
        
    Returns:
        datetime: A datetime object with timezone information
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt 