"""Service layer for im_bored application.

This module provides a clean, interface-agnostic API for all business logic operations.
Functions in this module are designed to be easily wrappable by FastMCP or other interfaces.
"""

from typing import Any

from im_bored import db

# ============================================================================
# Activity Management Services
# ============================================================================


def add_activity(
    type: str,
    description: str,
    tags: list[str] | None = None,
    duration: str | None = None,
    completable: bool = False,
    recurrence_days: int | None = None,
    due_date: str | None = None,
    archived: bool = False,
) -> int:
    """Add a new activity to the database for when users are bored or to create todo items.

    Args:
        type: Activity type/category (e.g., 'read', 'exercise', 'cook', 'general'). Can be any string.
        description: Clear, specific description of the activity (e.g., 'Read "Project Hail Mary" by Andy Weir').
        tags: Optional list of tag names for filtering (e.g., ['cozy', 'indoor', 'active']). Do not include # symbols.
        duration: Optional time estimate. Must be one of: '5min', '15min', '30min', '1h', '1h+'. Use this to filter by available time.
        completable: Set to True for todo items that should be marked done when finished. Set to False for repeatable activities.
        recurrence_days: For recurring tasks only. Number of days between occurrences (e.g., 7 for weekly, 30 for monthly). Cannot be used with due_date.
        due_date: Due date in ISO format YYYY-MM-DD (e.g., '2026-01-15'). Only for tasks with specific deadlines. Cannot be used with recurrence_days.
        archived: Set to True to create as archived (hidden from default views but kept in database).

    Returns:
        The ID of the newly created activity.
    """
    if recurrence_days is not None and due_date is not None:
        raise ValueError("Cannot use both recurrence_days and due_date")

    # Add the activity with all its properties
    # db.add_activity_with_tags handles tag creation internally
    activity_id = db.add_activity_with_tags(
        activity_type=type,
        description=description,
        tag_names=tags if tags else [],
        duration=duration,
        completable=completable,
        recurrence_days=recurrence_days,
        due_date=due_date,
    )
    assert activity_id is not None  # db function always returns int

    # Archive if requested (db function doesn't support archived parameter)
    if archived:
        db.archive_activity(activity_id)

    return activity_id


def list_activities(
    type: str | None = None,
    tags: list[str] | None = None,
    duration: str | None = None,
    completable_only: bool = False,
    completed_only: bool = False,
    show_archived: bool = False,
) -> list[dict]:
    """Retrieve all activities with optional filtering by type, tags, duration, completion status, and archive status.

    Args:
        type: Filter to a single activity type (e.g., 'read', 'exercise'). Use None to show all types.
        tags: Filter to activities that have ALL of these tags (e.g., ['cozy', 'indoor']). Use None for no tag filtering.
        duration: Filter by duration: '5min', '15min', '30min', '1h', '1h+'. Use None to show all durations.
        completable_only: Set to True to only show todo items (completable activities). Set to False to show all activities.
        completed_only: Set to True to only show completed activities. Set to False to show incomplete or all activities.
        show_archived: Set to True to include archived activities in results. Set to False to hide archived activities.

    Returns:
        List of activity dictionaries with their details and tags.
    """
    # Build filters dict for internal use
    filters: dict[str, Any] = {}
    if type:
        filters["type"] = type
    if tags:
        filters["tags"] = tags
    if duration:
        filters["duration"] = duration
    if completable_only:
        filters["completable_only"] = True
    if completed_only:
        filters["completed_only"] = True

    # Get all activities from database
    with db.get_db_connection() as conn:
        cursor = conn.cursor()

        # Build SQL query with filters
        query = """
            SELECT id, type, description, completed, completable, duration,
                   recurrence_days, last_completed_at, due_date, next_due_date,
                   archived, created_at, updated_at
            FROM activities
            WHERE 1=1
        """
        params = []

        # Apply filters
        if not show_archived:
            query += " AND archived = 0"

        if filters.get("type"):
            query += " AND type = ?"
            params.append(filters["type"])

        if filters.get("duration"):
            query += " AND duration = ?"
            params.append(filters["duration"])

        if filters.get("completable_only"):
            query += " AND completable = 1"

        if filters.get("completed_only"):
            query += " AND completed = 1"
        elif filters.get("completable_only"):
            # If showing completable only (todo list), exclude completed by default
            query += " AND completed = 0"

        query += " ORDER BY created_at DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Convert to dicts and add tags
        activities = []
        for row in rows:
            activity = {
                "id": row[0],
                "type": row[1],
                "description": row[2],
                "completed": bool(row[3]),
                "completable": bool(row[4]),
                "duration": row[5],
                "recurrence_days": row[6],
                "last_completed_at": row[7],
                "due_date": row[8],
                "next_due_date": row[9],
                "archived": bool(row[10]),
                "created_at": row[11],
                "updated_at": row[12],
            }

            # Add tags for this activity
            activity["tags"] = db.get_tags_for_activity(activity["id"])

            # Filter by tags if specified
            if filters.get("tags"):
                activity_tag_names = {tag["name"] for tag in activity["tags"]}
                required_tags = set(filters["tags"])
                if not required_tags.issubset(activity_tag_names):
                    continue

            activities.append(activity)

        return activities


def get_activity_details(activity_id: int) -> dict:
    """Get full details for a specific activity including all fields and associated tags.

    Args:
        activity_id: The activity ID to retrieve.

    Returns:
        Dictionary with activity details and tags.
    """
    activity = db.get_activity_by_id(activity_id)
    if not activity:
        raise ValueError(f"Activity {activity_id} not found")

    # Add tags
    activity["tags"] = db.get_tags_for_activity(activity_id)

    return activity


def remove_activity(activity_id: int) -> None:
    """Permanently delete an activity from the database.

    Args:
        activity_id: The activity ID to permanently delete.
    """
    activity = db.get_activity_by_id(activity_id)
    if not activity:
        raise ValueError(f"Activity {activity_id} not found")

    db.delete_activity(activity_id)


def archive_activity(activity_id: int) -> None:
    """Archive an activity to hide it from default views while keeping it in the database.

    Args:
        activity_id: The activity ID to archive.
    """
    activity = db.get_activity_by_id(activity_id)
    if not activity:
        raise ValueError(f"Activity {activity_id} not found")

    if activity.get("archived"):
        raise ValueError(f"Activity {activity_id} is already archived")

    db.archive_activity(activity_id)


def unarchive_activity(activity_id: int) -> None:
    """Restore an archived activity to make it visible in default views again.

    Args:
        activity_id: The activity ID to unarchive.
    """
    activity = db.get_activity_by_id(activity_id)
    if not activity:
        raise ValueError(f"Activity {activity_id} not found")

    if not activity.get("archived"):
        raise ValueError(f"Activity {activity_id} is not archived")

    db.unarchive_activity(activity_id)


# ============================================================================
# Todo Management Services
# ============================================================================


def list_todos(
    type: str | None = None,
    tags: list[str] | None = None,
    duration: str | None = None,
) -> list[dict]:
    """Get all incomplete todo items (completable activities that haven't been completed).

    Args:
        type: Filter to a single activity type (e.g., 'read', 'exercise'). Use None to show all types.
        tags: Filter to todos that have ALL of these tags (e.g., ['urgent', 'home']). Use None for no tag filtering.
        duration: Filter by duration: '5min', '15min', '30min', '1h', '1h+'. Use None to show all durations.

    Returns:
        List of incomplete todo item dictionaries.
    """
    return list_activities(
        type=type,
        tags=tags,
        duration=duration,
        completable_only=True,
        completed_only=False,
        show_archived=False,
    )


def complete_activity(activity_id: int) -> None:
    """Mark an activity as complete. For recurring tasks, this updates the next_due_date.

    Args:
        activity_id: The activity ID to mark as complete.
    """
    activity = db.get_activity_by_id(activity_id)
    if not activity:
        raise ValueError(f"Activity {activity_id} not found")

    db.update_activity_completion(activity_id, completed=True)


def uncomplete_activity(activity_id: int) -> None:
    """Mark an activity as incomplete (undo completion).

    Args:
        activity_id: The activity ID to mark as incomplete.
    """
    activity = db.get_activity_by_id(activity_id)
    if not activity:
        raise ValueError(f"Activity {activity_id} not found")

    db.update_activity_completion(activity_id, completed=False)


def log_activity_completion(activity_id: int) -> None:
    """Log manual activity completion with analytics tracking for statistics.

    Args:
        activity_id: The activity ID to log completion for.
    """
    activity = db.get_activity_by_id(activity_id)
    if not activity:
        raise ValueError(f"Activity {activity_id} not found")

    # Log the decision event
    db.log_decision_event(
        activity_id=activity_id,
        outcome="COMPLETED",
        filter_tags=None,
        session_id=None,
    )

    # Mark as completed if it's a completable activity
    if activity.get("completable"):
        db.update_activity_completion(activity_id, completed=True)


# ============================================================================
# Random Selection Services
# ============================================================================


def get_random_activity(
    types: list[str] | None = None,
    tags: list[str] | None = None,
    duration: str | None = None,
) -> dict:
    """Get a random uncompleted activity suggestion based on optional filters.

    Args:
        types: Filter to specific activity types (e.g., ['read', 'exercise', 'cook']). Use None to select from all types.
        tags: Filter to activities with ALL of these tags (e.g., ['cozy', 'indoor']). Use None for no tag filtering.
        duration: Filter by duration: '5min', '15min', '30min', '1h', '1h+'. Use None to select from all durations.

    Returns:
        Dictionary with the randomly selected activity details.
    """
    # Resolve tag names to tag IDs
    filter_tag_ids = []
    if tags:
        for tag_name in tags:
            tag = db.get_tag_by_name(tag_name)
            if not tag:
                raise ValueError(f"Tag '{tag_name}' not found")
            filter_tag_ids.append(tag["id"])

    # Get random activity
    activity = db.get_random_uncompleted_activity_filtered(
        activity_types=types,
        tag_ids=filter_tag_ids if filter_tag_ids else None,
        duration=duration,
    )

    if not activity:
        raise ValueError("No matching activities found")

    # Add tags for the activity
    activity["tags"] = db.get_tags_for_activity(activity["id"])

    return activity


# ============================================================================
# Tag Management Services
# ============================================================================


def list_tags() -> list[dict]:
    """Get all tags in the database.

    Returns:
        List of all tag dictionaries.
    """
    return db.get_all_tags()


def create_tag(name: str) -> int:
    """Create a new tag or return existing tag ID if it already exists.

    Args:
        name: Tag name to create.

    Returns:
        The ID of the created or existing tag.
    """
    # Check if tag already exists
    existing_tag = db.get_tag_by_name(name)
    if existing_tag:
        return existing_tag["id"]

    tag_id = db.create_tag(name)
    assert tag_id is not None  # db function always returns int
    return tag_id


def delete_tag(name: str) -> None:
    """Delete a tag from the database.

    Args:
        name: Tag name to delete.
    """
    tag = db.get_tag_by_name(name)
    if not tag:
        raise ValueError(f"Tag '{name}' not found")

    db.delete_tag(tag["id"])


def get_tag_details(name: str) -> dict:
    """Get tag details by name.

    Args:
        name: Tag name to retrieve.

    Returns:
        Dictionary with tag details.
    """
    tag = db.get_tag_by_name(name)
    if not tag:
        raise ValueError(f"Tag '{name}' not found")

    return tag


# ============================================================================
# Category Services
# ============================================================================


def list_categories() -> list[str]:
    """Get all unique activity types used in the database.

    Returns:
        Sorted list of unique activity type strings.
    """
    types = db.get_all_types()
    return sorted(types)


# ============================================================================
# Analytics Services
# ============================================================================


def get_stats(days: int | None = None) -> dict:
    """Get activity completion statistics for a specified time period.

    Args:
        days: Number of days to analyze. Use None for all-time statistics.

    Returns:
        Dictionary with statistics including completion counts and rates.
    """
    return db.get_decision_stats(days=days)


def reset_stats() -> int:
    """Clear all decision event statistics and return the number of events cleared.

    Returns:
        Number of decision events that were deleted.
    """
    return db.clear_all_decision_events()


# ============================================================================
# System Services
# ============================================================================


def ensure_database() -> None:
    """Ensure database exists and is initialized at the default path.

    If the database doesn't exist, it will be created and initialized.
    """
    db_path = db.get_db_path()

    if not db_path.exists():
        # Initialize database at default location
        db.initialize_database(db_path)


def reset_recurring_activities() -> int:
    """Reset expired recurring activities and return the number of activities reset.

    Returns:
        Number of recurring activities that were reset.
    """
    return db.reset_expired_recurring_activities()
