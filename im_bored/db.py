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


def get_random_uncompleted_activity_filtered(
    activity_types=None,
    tag_ids=None,
    duration=None,
    vibe_id=None
):
    """Get a random uncompleted activity with advanced filtering.

    Args:
        activity_types: Optional list of types to filter by
        tag_ids: Optional list of tag IDs (activity must have ALL these tags)
        duration: Optional duration filter ('5min', '15min', '30min', '1h', '1h+')
        vibe_id: Optional vibe ID (will apply vibe's tag filters)

    Returns:
        dict: Activity data or None if no matching activities exist
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # If vibe_id is provided, get its tags
        if vibe_id is not None:
            cursor.execute("""
                SELECT tag_id FROM vibe_tags WHERE vibe_id = ?
            """, (vibe_id,))
            vibe_tag_ids = [row[0] for row in cursor.fetchall()]

            # Combine with any additional tag filters
            if tag_ids:
                tag_ids = list(set(tag_ids + vibe_tag_ids))
            else:
                tag_ids = vibe_tag_ids

        # Build the query
        query = "SELECT * FROM activities WHERE completed = 0"
        params = []

        # Filter by type
        if activity_types:
            placeholders = ','.join('?' * len(activity_types))
            query += f" AND type IN ({placeholders})"
            params.extend(activity_types)

        # Filter by duration
        if duration:
            query += " AND duration = ?"
            params.append(duration)

        # Filter by tags (activity must have ALL specified tags)
        if tag_ids:
            query += """ AND id IN (
                SELECT activity_id FROM activity_tags
                WHERE tag_id IN ({})
                GROUP BY activity_id
                HAVING COUNT(DISTINCT tag_id) = ?
            )""".format(','.join('?' * len(tag_ids)))
            params.extend(tag_ids)
            params.append(len(tag_ids))

        # Random selection
        query += " ORDER BY RANDOM() LIMIT 1"

        cursor.execute(query, params)
        activity = cursor.fetchone()
        return dict(activity) if activity else None


def update_activity_duration(activity_id: int, duration: str | None):
    """Update the duration of an activity.

    Args:
        activity_id: The ID of the activity
        duration: Duration value ('5min', '15min', '30min', '1h', '1h+') or None

    Returns:
        bool: True if update was successful, False if activity not found
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE activities SET duration = ? WHERE id = ?",
            (duration, activity_id)
        )
        return cursor.rowcount > 0


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


# ============================================================================
# Tag Management Functions
# ============================================================================

def get_all_tags():
    """Get all tags from the database.

    Returns:
        list[dict]: List of all tags with id, name, created_at
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tags ORDER BY name")
        return [dict(row) for row in cursor.fetchall()]


def get_tag_by_name(name: str):
    """Get a tag by its name.

    Args:
        name: The tag name to search for

    Returns:
        dict | None: Tag data or None if not found
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tags WHERE name = ?", (name,))
        row = cursor.fetchone()
        return dict(row) if row else None


def create_tag(name: str):
    """Create a new tag.

    Args:
        name: The tag name

    Returns:
        int: The ID of the created tag, or existing tag ID if already exists
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO tags (name) VALUES (?)", (name,))
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # Tag already exists, return its ID
            cursor.execute("SELECT id FROM tags WHERE name = ?", (name,))
            return cursor.fetchone()[0]


def delete_tag(tag_id: int):
    """Delete a tag from the database.

    Args:
        tag_id: The ID of the tag to delete

    Returns:
        bool: True if deletion was successful, False if tag not found
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
        return cursor.rowcount > 0


def get_tags_for_activity(activity_id: int):
    """Get all tags associated with an activity.

    Args:
        activity_id: The ID of the activity

    Returns:
        list[dict]: List of tags for this activity
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.* FROM tags t
            JOIN activity_tags at ON t.id = at.tag_id
            WHERE at.activity_id = ?
            ORDER BY t.name
        """, (activity_id,))
        return [dict(row) for row in cursor.fetchall()]


def add_tag_to_activity(activity_id: int, tag_id: int):
    """Associate a tag with an activity.

    Args:
        activity_id: The ID of the activity
        tag_id: The ID of the tag

    Returns:
        bool: True if successful, False if already exists or error
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO activity_tags (activity_id, tag_id) VALUES (?, ?)",
                (activity_id, tag_id)
            )
            return True
        except sqlite3.IntegrityError:
            # Already exists
            return False


def remove_tag_from_activity(activity_id: int, tag_id: int):
    """Remove a tag association from an activity.

    Args:
        activity_id: The ID of the activity
        tag_id: The ID of the tag

    Returns:
        bool: True if deletion was successful, False if association not found
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM activity_tags WHERE activity_id = ? AND tag_id = ?",
            (activity_id, tag_id)
        )
        return cursor.rowcount > 0


def parse_tags_from_description(description: str):
    """Parse hashtags from a description string.

    Args:
        description: The description text that may contain #hashtags

    Returns:
        tuple[str, list[str]]: (clean_description, list_of_tag_names)
            Example: "Clean kitchen #indoor #15min" -> ("Clean kitchen", ["indoor", "15min"])
    """
    import re

    # Find all hashtags
    tag_pattern = r'#(\w+)'
    tags = re.findall(tag_pattern, description)

    # Remove hashtags from description
    clean_description = re.sub(tag_pattern, '', description).strip()
    # Clean up multiple spaces
    clean_description = re.sub(r'\s+', ' ', clean_description)

    return clean_description, tags


def add_activity_with_tags(activity_type: str, description: str, tag_names: list[str], duration: str | None = None):
    """Add a new activity with tags in a single transaction.

    Args:
        activity_type: The type/category of the activity
        description: The activity description
        tag_names: List of tag names (will be created if they don't exist)
        duration: Optional duration ('5min', '15min', '30min', '1h', '1h+')

    Returns:
        int: The ID of the newly created activity
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Insert activity
        cursor.execute(
            "INSERT INTO activities (type, description, completed, duration) VALUES (?, ?, ?, ?)",
            (activity_type, description, 0, duration)
        )
        activity_id = cursor.lastrowid

        # Create tags and associate them
        for tag_name in tag_names:
            # Create tag (or get existing) - do it within this connection
            try:
                cursor.execute("INSERT INTO tags (name) VALUES (?)", (tag_name,))
                tag_id = cursor.lastrowid
            except sqlite3.IntegrityError:
                # Tag already exists, get its ID
                cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
                tag_id = cursor.fetchone()[0]

            # Associate with activity
            try:
                cursor.execute(
                    "INSERT INTO activity_tags (activity_id, tag_id) VALUES (?, ?)",
                    (activity_id, tag_id)
                )
            except sqlite3.IntegrityError:
                # Already associated, skip
                pass

        return activity_id


# ============================================================================
# Vibe Management Functions
# ============================================================================

def get_all_vibes():
    """Get all vibes with their associated tags.

    Returns:
        list[dict]: List of all vibes, each with a 'tags' key containing associated tags
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM vibes ORDER BY name")
        vibes = [dict(row) for row in cursor.fetchall()]

        # Fetch tags for each vibe
        for vibe in vibes:
            cursor.execute("""
                SELECT t.* FROM tags t
                JOIN vibe_tags vt ON t.id = vt.tag_id
                WHERE vt.vibe_id = ?
                ORDER BY t.name
            """, (vibe['id'],))
            vibe['tags'] = [dict(row) for row in cursor.fetchall()]

        return vibes


def get_vibe_by_id(vibe_id: int):
    """Get a vibe by its ID with associated tags.

    Args:
        vibe_id: The vibe ID to search for

    Returns:
        dict | None: Vibe data with tags, or None if not found
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM vibes WHERE id = ?", (vibe_id,))
        row = cursor.fetchone()

        if not row:
            return None

        vibe = dict(row)

        # Fetch associated tags
        cursor.execute("""
            SELECT t.* FROM tags t
            JOIN vibe_tags vt ON t.id = vt.tag_id
            WHERE vt.vibe_id = ?
            ORDER BY t.name
        """, (vibe_id,))
        vibe['tags'] = [dict(row) for row in cursor.fetchall()]

        return vibe


def get_vibe_by_name(name: str):
    """Get a vibe by its name with associated tags.

    Args:
        name: The vibe name to search for

    Returns:
        dict | None: Vibe data with tags, or None if not found
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM vibes WHERE name = ?", (name,))
        row = cursor.fetchone()

        if not row:
            return None

        vibe = dict(row)

        # Fetch associated tags
        cursor.execute("""
            SELECT t.* FROM tags t
            JOIN vibe_tags vt ON t.id = vt.tag_id
            WHERE vt.vibe_id = ?
            ORDER BY t.name
        """, (vibe['id'],))
        vibe['tags'] = [dict(row) for row in cursor.fetchall()]

        return vibe


def create_vibe(name: str, description: str, tag_ids: list[int]):
    """Create a new vibe with associated tags.

    Args:
        name: The vibe name
        description: Description of the vibe
        tag_ids: List of tag IDs to associate with this vibe

    Returns:
        int: The ID of the created vibe
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Insert vibe
        cursor.execute(
            "INSERT INTO vibes (name, description) VALUES (?, ?)",
            (name, description)
        )
        vibe_id = cursor.lastrowid

        # Associate tags
        for tag_id in tag_ids:
            cursor.execute(
                "INSERT INTO vibe_tags (vibe_id, tag_id) VALUES (?, ?)",
                (vibe_id, tag_id)
            )

        return vibe_id


def update_vibe(vibe_id: int, name: str, description: str, tag_ids: list[int]):
    """Update a vibe's details and tag associations.

    Args:
        vibe_id: The ID of the vibe to update
        name: New name
        description: New description
        tag_ids: New list of tag IDs (replaces existing associations)

    Returns:
        bool: True if update was successful, False if vibe not found
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Update vibe
        cursor.execute(
            "UPDATE vibes SET name = ?, description = ? WHERE id = ?",
            (name, description, vibe_id)
        )

        if cursor.rowcount == 0:
            return False

        # Remove old tag associations
        cursor.execute("DELETE FROM vibe_tags WHERE vibe_id = ?", (vibe_id,))

        # Add new tag associations
        for tag_id in tag_ids:
            cursor.execute(
                "INSERT INTO vibe_tags (vibe_id, tag_id) VALUES (?, ?)",
                (vibe_id, tag_id)
            )

        return True


def delete_vibe(vibe_id: int):
    """Delete a vibe from the database.

    Args:
        vibe_id: The ID of the vibe to delete

    Returns:
        bool: True if deletion was successful, False if vibe not found
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM vibes WHERE id = ?", (vibe_id,))
        return cursor.rowcount > 0


def get_tags_for_vibe(vibe_id: int):
    """Get all tags associated with a vibe.

    Args:
        vibe_id: The ID of the vibe

    Returns:
        list[dict]: List of tags for this vibe
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.* FROM tags t
            JOIN vibe_tags vt ON t.id = vt.tag_id
            WHERE vt.vibe_id = ?
            ORDER BY t.name
        """, (vibe_id,))
        return [dict(row) for row in cursor.fetchall()]


# ============================================================================
# Decision Events & Analytics Functions
# ============================================================================

def log_decision_event(
    activity_id: int,
    outcome: str,
    vibe_id: int | None = None,
    filter_tags: list[int] | None = None,
    session_id: str | None = None
):
    """Log a decision event.

    Args:
        activity_id: The ID of the activity that was shown
        outcome: 'COMPLETED', 'SKIPPED', or 'IGNORED'
        vibe_id: Optional vibe ID that was active
        filter_tags: Optional list of tag IDs that were active filters
        session_id: Optional session ID for grouping decisions

    Returns:
        int: The ID of the created event
    """
    import json

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Convert filter_tags to JSON string
        filter_tags_json = json.dumps(filter_tags) if filter_tags else None

        cursor.execute("""
            INSERT INTO decision_events (activity_id, outcome, vibe_id, filter_tags, session_id)
            VALUES (?, ?, ?, ?, ?)
        """, (activity_id, outcome, vibe_id, filter_tags_json, session_id))

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
            - vibe_usage: Dict of vibe names to usage counts
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Calculate date threshold if days is specified
        if days is not None:
            cursor.execute("""
                SELECT datetime('now', '-' || ? || ' days')
            """, (days,))
            since_date = cursor.fetchone()[0]
            where_clause = "WHERE created_at >= ?"
            params = (since_date,)
        else:
            where_clause = ""
            params = ()

        # Total rolls
        cursor.execute(f"""
            SELECT COUNT(*) FROM decision_events
            {where_clause}
        """, params)
        total_rolls = cursor.fetchone()[0]

        # Outcome counts
        cursor.execute(f"""
            SELECT outcome, COUNT(*) FROM decision_events
            {where_clause}
            GROUP BY outcome
        """, params)
        outcome_counts = {row[0]: row[1] for row in cursor.fetchall()}

        completed_count = outcome_counts.get('COMPLETED', 0)
        skipped_count = outcome_counts.get('SKIPPED', 0)
        ignored_count = outcome_counts.get('IGNORED', 0)

        # Completion rate
        completion_rate = (completed_count / total_rolls * 100) if total_rolls > 0 else 0
        skip_rate = (skipped_count / total_rolls * 100) if total_rolls > 0 else 0

        # Most completed activities
        if days is not None:
            completed_where = "WHERE de.created_at >= ? AND de.outcome = 'COMPLETED'"
            skipped_where = "WHERE de.created_at >= ? AND de.outcome = 'SKIPPED'"
            vibe_where = "WHERE de.created_at >= ? AND de.vibe_id IS NOT NULL"
            query_params = (since_date,)
        else:
            completed_where = "WHERE de.outcome = 'COMPLETED'"
            skipped_where = "WHERE de.outcome = 'SKIPPED'"
            vibe_where = "WHERE de.vibe_id IS NOT NULL"
            query_params = ()

        cursor.execute(f"""
            SELECT a.id, a.description, a.type, COUNT(*) as count
            FROM decision_events de
            JOIN activities a ON de.activity_id = a.id
            {completed_where}
            GROUP BY a.id
            ORDER BY count DESC
            LIMIT 5
        """, query_params)
        most_completed = [dict(row) for row in cursor.fetchall()]

        # Most skipped activities
        cursor.execute(f"""
            SELECT a.id, a.description, a.type, COUNT(*) as count
            FROM decision_events de
            JOIN activities a ON de.activity_id = a.id
            {skipped_where}
            GROUP BY a.id
            ORDER BY count DESC
            LIMIT 5
        """, query_params)
        most_skipped = [dict(row) for row in cursor.fetchall()]

        # Vibe usage
        cursor.execute(f"""
            SELECT v.name, COUNT(*) as count
            FROM decision_events de
            JOIN vibes v ON de.vibe_id = v.id
            {vibe_where}
            GROUP BY v.id
            ORDER BY count DESC
        """, query_params)
        vibe_usage = {row[0]: row[1] for row in cursor.fetchall()}

        return {
            'total_rolls': total_rolls,
            'completed_count': completed_count,
            'skipped_count': skipped_count,
            'ignored_count': ignored_count,
            'completion_rate': completion_rate,
            'skip_rate': skip_rate,
            'most_completed': most_completed,
            'most_skipped': most_skipped,
            'vibe_usage': vibe_usage,
            'days': days
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
        cursor.execute("""
            SELECT * FROM decision_events
            WHERE activity_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (activity_id, limit))
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
