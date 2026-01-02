"""Database utilities for im_bored application."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

# Database path relative to this module
DB_PATH = Path(__file__).parent.parent / "data" / "activities.db"


@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_random_uncompleted_activity(activity_types=None):
    """Get a random uncompleted activity from the database.

    Args:
        activity_types: Optional list of types to filter by

    Returns:
        dict: Activity data or None if no uncompleted activities exist
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if activity_types:
            placeholders = ','.join('?' * len(activity_types))
            cursor.execute(
                f"SELECT * FROM activities WHERE completed = 0 AND type IN ({placeholders}) ORDER BY RANDOM() LIMIT 1",
                activity_types
            )
        else:
            cursor.execute(
                "SELECT * FROM activities WHERE completed = 0 ORDER BY RANDOM() LIMIT 1"
            )
        activity = cursor.fetchone()
        return dict(activity) if activity else None


def get_all_activities():
    """Get all activities grouped by type.

    Returns:
        dict: Activities grouped by type, with each type containing a list of activities
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM activities ORDER BY id")
        activities = [dict(row) for row in cursor.fetchall()]

    # Group by type
    grouped = {}
    for activity in activities:
        activity_type = activity['type']
        if activity_type not in grouped:
            grouped[activity_type] = []
        grouped[activity_type].append(activity)

    return grouped


def get_all_types():
    """Get all unique activity types.

    Returns:
        list: Sorted list of unique activity type strings
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT type FROM activities ORDER BY type")
        types = [row['type'] for row in cursor.fetchall()]
    return types


def add_activity(activity_type: str, description: str):
    """Add a new activity to the database.

    Args:
        activity_type: The type/category of the activity
        description: The activity description

    Returns:
        int: The ID of the newly created activity
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO activities (type, description, completed) VALUES (?, ?, ?)",
            (activity_type, description, 0)
        )
        return cursor.lastrowid


def update_activity_completion(activity_id: int, completed: bool):
    """Toggle the completion status of an activity.

    Args:
        activity_id: The ID of the activity to update
        completed: True to mark complete, False for incomplete

    Returns:
        bool: True if update was successful, False if activity not found
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE activities SET completed = ? WHERE id = ?",
            (1 if completed else 0, activity_id)
        )
        return cursor.rowcount > 0


def delete_activity(activity_id: int):
    """Delete an activity from the database.

    Args:
        activity_id: The ID of the activity to delete

    Returns:
        bool: True if deletion was successful, False if activity not found
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM activities WHERE id = ?", (activity_id,))
        return cursor.rowcount > 0
