"""Database utilities for im_bored application."""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

# Environment file location (in project root)
ENV_FILE = Path(__file__).parent.parent / ".env"

# Default database path
DEFAULT_DB_PATH = Path(os.getcwd()) / "data" / "im_bored" / "activities.db"


def get_db_path() -> Path:
    """Get the database path from .env file or use default.

    Returns:
        Path: The configured database path or default
    """
    # Check environment variable first
    env_path = os.environ.get("IM_BORED_DB_PATH")
    if env_path:
        return Path(env_path)

    # Check .env file
    if ENV_FILE.exists():
        with open(ENV_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("IM_BORED_DB_PATH="):
                    path_str = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if path_str:
                        return Path(path_str)

    return DEFAULT_DB_PATH


def set_db_path(path: Path):
    """Save the database path to .env file.

    Args:
        path: Path to the database file
    """
    lines = []
    found = False

    # Read existing .env if it exists
    if ENV_FILE.exists():
        with open(ENV_FILE, "r") as f:
            for line in f:
                if line.strip().startswith("IM_BORED_DB_PATH="):
                    lines.append(f'IM_BORED_DB_PATH="{path}"\n')
                    found = True
                else:
                    lines.append(line)

    # If not found, add it
    if not found:
        lines.append(f'IM_BORED_DB_PATH="{path}"\n')

    # Write back to .env
    with open(ENV_FILE, "w") as f:
        f.writelines(lines)


# Get the current database path
DB_PATH = get_db_path()


def initialize_database(db_path: Path | None = None):
    """Initialize a new database with the full schema.

    Args:
        db_path: Path where the database should be created.
                If None, uses the default DB_PATH.
    """
    if db_path is None:
        db_path = DB_PATH

    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Create and initialize the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Create activities table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                description TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completable INTEGER NOT NULL DEFAULT 0,
                completed INTEGER NOT NULL DEFAULT 0,
                recurrence_days INTEGER CHECK(recurrence_days IS NULL OR recurrence_days > 0),
                last_completed_at TIMESTAMP,
                due_date TIMESTAMP,
                next_due_date TIMESTAMP,
                archived INTEGER NOT NULL DEFAULT 0
            )
        """
        )

        # Create indexes for activities
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_activities_type ON activities(type)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_activities_completed ON activities(completed)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_activities_recurrence ON activities(recurrence_days)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_activities_due_date ON activities(due_date)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_activities_next_due_date ON activities(next_due_date)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_activities_archived ON activities(archived)"
        )

        # Create timestamp trigger for activities
        cursor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS update_activities_timestamp
            AFTER UPDATE ON activities
            FOR EACH ROW
            BEGIN
                UPDATE activities SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
        """
        )

        conn.commit()

    finally:
        conn.close()


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
            placeholders = ",".join("?" * len(activity_types))
            cursor.execute(
                f"SELECT * FROM activities WHERE completed = 0 AND type IN ({placeholders}) ORDER BY RANDOM() LIMIT 1",
                activity_types,
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
        activity_type = activity["type"]
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
        types = [row["type"] for row in cursor.fetchall()]
    return types


def update_activity_completion(activity_id: int, completed: bool):
    """Toggle the completion status of an activity.

    For recurring tasks, also updates last_completed_at and next_due_date when marking as complete.

    Args:
        activity_id: The ID of the activity to update
        completed: True to mark complete, False for incomplete

    Returns:
        bool: True if update was successful, False if activity not found
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Get activity info to check if it's recurring
        cursor.execute(
            "SELECT recurrence_days FROM activities WHERE id = ?", (activity_id,)
        )
        row = cursor.fetchone()
        if not row:
            return False

        recurrence_days = row[0]

        if completed and recurrence_days is not None:
            # For recurring tasks, update last_completed_at and next_due_date
            cursor.execute(
                """
                UPDATE activities
                SET completed = 1,
                    last_completed_at = CURRENT_TIMESTAMP,
                    next_due_date = datetime(CURRENT_TIMESTAMP, '+' || ? || ' days')
                WHERE id = ?
            """,
                (recurrence_days, activity_id),
            )
        else:
            # For non-recurring tasks or marking incomplete
            cursor.execute(
                "UPDATE activities SET completed = ? WHERE id = ?",
                (1 if completed else 0, activity_id),
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


def archive_activity(activity_id: int):
    """Archive an activity (hides it from default views but keeps in database).

    Args:
        activity_id: The ID of the activity to archive

    Returns:
        bool: True if archival was successful, False if activity not found
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE activities SET archived = 1 WHERE id = ?", (activity_id,)
        )
        return cursor.rowcount > 0


def unarchive_activity(activity_id: int):
    """Unarchive an activity (restores it to default views).

    Args:
        activity_id: The ID of the activity to unarchive

    Returns:
        bool: True if unarchival was successful, False if activity not found
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE activities SET archived = 0 WHERE id = ?", (activity_id,)
        )
        return cursor.rowcount > 0


def add_activity(
    activity_type: str,
    description: str,
    completable: bool = False,
    recurrence_days: int | None = None,
    due_date: str | None = None,
):
    """Add a new activity in a single transaction.

    Args:
        activity_type: The type/category of the activity
        description: The activity description
        completable: Whether this is a completable one-off activity (default: False)
        recurrence_days: Optional recurrence period in days (requires completable=True)
        due_date: Optional due date for scheduled tasks (requires completable=True)

    Returns:
        int: The ID of the newly created activity
    """
    # Validation
    if recurrence_days is not None and not completable:
        raise ValueError("recurrence_days requires completable=True")
    if due_date is not None and not completable:
        raise ValueError("due_date requires completable=True")
    if recurrence_days is not None and due_date is not None:
        raise ValueError("Cannot have both recurrence_days and due_date")

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Calculate next_due_date for recurring tasks
        next_due_date = None
        if recurrence_days is not None:
            cursor.execute(
                "SELECT datetime('now', '+' || ? || ' days')", (recurrence_days,)
            )
            next_due_date = cursor.fetchone()[0]

        # Insert activity
        cursor.execute(
            """INSERT INTO activities
               (type, description, completed, completable, recurrence_days, due_date, next_due_date)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                activity_type,
                description,
                0,
                1 if completable else 0,
                recurrence_days,
                due_date,
                next_due_date,
            ),
        )
        activity_id = cursor.lastrowid

        return activity_id


# ============================================================================
# Decision Events & Analytics Functions
# ============================================================================


def log_decision_event(
    activity_id: int,
    outcome: str,
    session_id: str | None = None,
):
    """Log a decision event.

    Args:
        activity_id: The ID of the activity that was shown
        outcome: 'COMPLETED', 'SKIPPED', or 'IGNORED'
        session_id: Optional session ID for grouping decisions

    Returns:
        int: The ID of the created event
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO decision_events (activity_id, outcome, session_id)
            VALUES (?, ?, ?)
        """,
            (activity_id, outcome, session_id),
        )

        return cursor.lastrowid


def get_decision_stats(days: int | None = None):
    """Get analytics statistics for the last N days, or all time if days is None.

    Args:
        days: Number of days to analyze, or None for all time (default: None)

    Returns:
        dict: Statistics including:
            - total_rolls: Total number of decisions
            - completed_count: Number of COMPLETED outcomes
            - skipped_count: Number of SKIPPED outcomes
            - ignored_count: Number of IGNORED outcomes
            - completion_rate: Percentage of completed activities
            - skip_rate: Percentage of skipped activities
            - most_completed: List of most completed activities
            - most_skipped: List of most skipped activities
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Calculate date threshold if days is specified
        if days is not None:
            cursor.execute(
                """
                SELECT datetime('now', '-' || ? || ' days')
            """,
                (days,),
            )
            since_date = cursor.fetchone()[0]
            where_clause = "WHERE created_at >= ?"
            params = (since_date,)
        else:
            where_clause = ""
            params = ()

        # Total rolls
        cursor.execute(
            f"""
            SELECT COUNT(*) FROM decision_events
            {where_clause}
        """,
            params,
        )
        total_rolls = cursor.fetchone()[0]

        # Outcome counts
        cursor.execute(
            f"""
            SELECT outcome, COUNT(*) FROM decision_events
            {where_clause}
            GROUP BY outcome
        """,
            params,
        )
        outcome_counts = {row[0]: row[1] for row in cursor.fetchall()}

        completed_count = outcome_counts.get("COMPLETED", 0)
        skipped_count = outcome_counts.get("SKIPPED", 0)
        ignored_count = outcome_counts.get("IGNORED", 0)

        # Completion rate
        completion_rate = (
            (completed_count / total_rolls * 100) if total_rolls > 0 else 0
        )
        skip_rate = (skipped_count / total_rolls * 100) if total_rolls > 0 else 0

        # Most completed activities
        if days is not None:
            completed_where = "WHERE de.created_at >= ? AND de.outcome = 'COMPLETED'"
            skipped_where = "WHERE de.created_at >= ? AND de.outcome = 'SKIPPED'"
            query_params = (since_date,)
        else:
            completed_where = "WHERE de.outcome = 'COMPLETED'"
            skipped_where = "WHERE de.outcome = 'SKIPPED'"
            query_params = ()

        cursor.execute(
            f"""
            SELECT a.id, a.description, a.type, COUNT(*) as count
            FROM decision_events de
            JOIN activities a ON de.activity_id = a.id
            {completed_where}
            GROUP BY a.id
            ORDER BY count DESC
            LIMIT 5
        """,
            query_params,
        )
        most_completed = [dict(row) for row in cursor.fetchall()]

        # Most skipped activities
        cursor.execute(
            f"""
            SELECT a.id, a.description, a.type, COUNT(*) as count
            FROM decision_events de
            JOIN activities a ON de.activity_id = a.id
            {skipped_where}
            GROUP BY a.id
            ORDER BY count DESC
            LIMIT 5
        """,
            query_params,
        )
        most_skipped = [dict(row) for row in cursor.fetchall()]

        return {
            "total_rolls": total_rolls,
            "completed_count": completed_count,
            "skipped_count": skipped_count,
            "ignored_count": ignored_count,
            "completion_rate": completion_rate,
            "skip_rate": skip_rate,
            "most_completed": most_completed,
            "most_skipped": most_skipped,
            "days": days,
        }


def get_activity_decision_history(activity_id: int, limit: int = 10):
    """Get recent decision events for a specific activity.

    Args:
        activity_id: The ID of the activity
        limit: Maximum number of events to return

    Returns:
        list[dict]: List of decision events with timestamps
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM decision_events
            WHERE activity_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """,
            (activity_id, limit),
        )
        return [dict(row) for row in cursor.fetchall()]


def clear_all_decision_events():
    """Clear all decision events (reset statistics).

    Returns:
        int: Number of events deleted
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM decision_events")
        count = cursor.fetchone()[0]
        cursor.execute("DELETE FROM decision_events")
        return count


def get_activity_by_id(activity_id: int):
    """Get an activity by its ID.

    Args:
        activity_id: The ID of the activity

    Returns:
        dict | None: Activity data or None if not found
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM activities WHERE id = ?", (activity_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


# ============================================================================
# Recurring Task Management Functions
# ============================================================================


def reset_expired_recurring_activities():
    """Reset recurring tasks that have passed their next_due_date.

    This function should be called at program startup to ensure recurring tasks
    are up-to-date. For tasks that have passed their due date, it:
    - Marks them as incomplete (if they were completed)
    - Rolls their next_due_date forward from the current time

    Returns:
        int: Number of activities reset
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Get all recurring activities where next_due_date has passed
        cursor.execute(
            """
            SELECT id, recurrence_days
            FROM activities
            WHERE recurrence_days IS NOT NULL
              AND completable = 1
              AND next_due_date IS NOT NULL
              AND datetime('now') >= datetime(next_due_date)
        """
        )

        activities_to_reset = cursor.fetchall()
        reset_count = 0

        for activity_id, recurrence_days in activities_to_reset:
            # Reset to incomplete and roll next_due_date forward from now
            cursor.execute(
                """
                UPDATE activities
                SET completed = 0,
                    next_due_date = datetime('now', '+' || ? || ' days')
                WHERE id = ?
            """,
                (recurrence_days, activity_id),
            )
            reset_count += 1

        return reset_count


def parse_recurrence_to_days(recurrence_str: str) -> tuple[int, str | None]:
    """Parse a recurrence string into days.

    Accepts formats like:
    - "7days" or "7d" -> 7 days
    - "2weeks" or "2w" -> 14 days
    - "1month" or "1m" -> 30 days

    Args:
        recurrence_str: The recurrence string to parse

    Returns:
        tuple[int, str | None]: (days, warning_message)
        - days: The number of days
        - warning_message: Optional warning about approximations (e.g., for months)

    Raises:
        ValueError: If the format is invalid
    """
    import re

    recurrence_str = recurrence_str.lower().strip()

    # Match patterns like "7days", "7d", "2weeks", "2w", "1month", "1m"
    match = re.match(r"^(\d+)\s*(days?|d|weeks?|w|months?|m)$", recurrence_str)

    if not match:
        raise ValueError(
            f"Invalid recurrence format: '{recurrence_str}'. "
            "Use formats like '7days', '2weeks', or '1month'"
        )

    count = int(match.group(1))
    unit = match.group(2)

    warning = None

    if unit in ("days", "day", "d"):
        days = count
    elif unit in ("weeks", "week", "w"):
        days = count * 7
    elif unit in ("months", "month", "m"):
        days = count * 30
        warning = f"Using approximate month length: {count} month(s) = {days} days"
    else:
        raise ValueError(f"Unknown time unit: {unit}")

    return days, warning
