"""Service layer for im_bored application.

This module provides a clean, interface-agnostic API for all business logic operations.
Functions in this module are designed to be easily wrappable by FastMCP or other interfaces.
"""

from typing import Annotated, Any
from im_bored import db


# ============================================================================
# Activity Management Services
# ============================================================================


def add_activity(
    type: Annotated[str, "Activity type/category (e.g., 'read', 'exercise', 'cook', 'general'). Can be any string."],
    description: Annotated[str, "Clear, specific description of the activity (e.g., 'Read \"Project Hail Mary\" by Andy Weir')"],
    tags: Annotated[list[str] | None, "Optional list of tag names for filtering (e.g., ['cozy', 'indoor', 'active']). Do not include # symbols."] = None,
    duration: Annotated[str | None, "Optional time estimate. Must be one of: '5min', '15min', '30min', '1h', '1h+'. Use this to filter by available time."] = None,
    completable: Annotated[bool, "Set to True for todo items that should be marked done when finished. Set to False for repeatable activities."] = False,
    recurrence_days: Annotated[int | None, "For recurring tasks only. Number of days between occurrences (e.g., 7 for weekly, 30 for monthly)."] = None,
    due_date: Annotated[str | None, "Due date in ISO format YYYY-MM-DD (e.g., '2026-01-15'). Only for tasks with specific deadlines."] = None,
    archived: Annotated[bool, "Set to True to create as archived (hidden from default views but kept in database)."] = False,
) -> int:
    """Add a new activity to the database. Use this to create activities users can do when bored, or to add tasks to their todo list."""
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
    type: Annotated[str | None, "Filter to a single activity type (e.g., 'read', 'exercise'). Leave None for all types."] = None,
    tags: Annotated[list[str] | None, "Filter to activities that have ALL of these tags (e.g., ['indoor', 'cozy']). Leave None for no tag filtering."] = None,
    duration: Annotated[str | None, "Filter by time duration. Must be one of: '5min', '15min', '30min', '1h', '1h+'. Leave None for any duration."] = None,
    completable_only: Annotated[bool, "If True, only show todo items (completable activities). If False, show all activities."] = False,
    completed_only: Annotated[bool, "If True, only show completed activities. If False and completable_only is True, shows incomplete todos."] = False,
    show_archived: Annotated[bool, "If True, include archived activities in results. If False, hide archived activities."] = False,
) -> list[dict]:
    """Get all activities with optional filtering. Use this to browse available activities or see what the user has logged. By default, returns all non-archived activities."""
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
    """Get full details for a specific activity.

    Parameters:
        activity_id: The activity ID

    Returns:
        dict: Activity details with all fields and tags

    Raises:
        ValueError: If activity not found
    """
    activity = db.get_activity_by_id(activity_id)
    if not activity:
        raise ValueError(f"Activity {activity_id} not found")

    # Add tags
    activity["tags"] = db.get_tags_for_activity(activity_id)

    return activity


def remove_activity(activity_id: int) -> None:
    """Permanently delete an activity.

    Parameters:
        activity_id: The activity ID to delete

    Raises:
        ValueError: If activity not found
    """
    activity = db.get_activity_by_id(activity_id)
    if not activity:
        raise ValueError(f"Activity {activity_id} not found")

    db.delete_activity(activity_id)


def archive_activity(activity_id: int) -> None:
    """Archive an activity (hide from default views).

    Parameters:
        activity_id: The activity ID to archive

    Raises:
        ValueError: If activity not found or already archived
    """
    activity = db.get_activity_by_id(activity_id)
    if not activity:
        raise ValueError(f"Activity {activity_id} not found")

    if activity.get("archived"):
        raise ValueError(f"Activity {activity_id} is already archived")

    db.archive_activity(activity_id)


def unarchive_activity(activity_id: int) -> None:
    """Restore an archived activity.

    Parameters:
        activity_id: The activity ID to unarchive

    Raises:
        ValueError: If activity not found or not archived
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
    type: Annotated[str | None, "Filter to a single activity type (e.g., 'read', 'chores'). Leave None for all types."] = None,
    tags: Annotated[list[str] | None, "Filter to todos that have ALL of these tags (e.g., ['urgent', 'home']). Leave None for no tag filtering."] = None,
    duration: Annotated[str | None, "Filter by time estimate. Must be one of: '5min', '15min', '30min', '1h', '1h+'. Leave None for any duration."] = None,
) -> list[dict]:
    """Get incomplete completable activities (todo list). Returns the user's active todo list - tasks marked as completable that haven't been completed yet."""
    return list_activities(
        type=type,
        tags=tags,
        duration=duration,
        completable_only=True,
        completed_only=False,
        show_archived=False
    )


def complete_activity(activity_id: int) -> None:
    """Mark an activity as complete.

    For recurring tasks, this updates the next_due_date.

    Parameters:
        activity_id: The activity ID to mark as complete

    Raises:
        ValueError: If activity not found
    """
    activity = db.get_activity_by_id(activity_id)
    if not activity:
        raise ValueError(f"Activity {activity_id} not found")

    db.update_activity_completion(activity_id, completed=True)


def uncomplete_activity(activity_id: int) -> None:
    """Mark an activity as incomplete.

    Parameters:
        activity_id: The activity ID to mark as incomplete

    Raises:
        ValueError: If activity not found
    """
    activity = db.get_activity_by_id(activity_id)
    if not activity:
        raise ValueError(f"Activity {activity_id} not found")

    db.update_activity_completion(activity_id, completed=False)


def log_activity_completion(activity_id: int, vibe_name: str | None = None) -> None:
    """Log manual activity completion with analytics tracking.

    Parameters:
        activity_id: The activity ID to log
        vibe_name: Optional vibe context for analytics

    Raises:
        ValueError: If activity not found or vibe not found
    """
    activity = db.get_activity_by_id(activity_id)
    if not activity:
        raise ValueError(f"Activity {activity_id} not found")

    # Resolve vibe name to vibe ID if provided
    vibe_id = None
    if vibe_name:
        vibe = db.get_vibe_by_name(vibe_name)
        if not vibe:
            raise ValueError(f"Vibe '{vibe_name}' not found")
        vibe_id = vibe["id"]

    # Log the decision event
    db.log_decision_event(
        activity_id=activity_id,
        vibe_id=vibe_id,
        filter_tags=None,
        outcome="COMPLETED",
        session_id=None,
    )

    # Mark as completed if it's a completable activity
    if activity.get("completable"):
        db.update_activity_completion(activity_id, completed=True)


# ============================================================================
# Random Selection Services
# ============================================================================


def get_random_activity(
    types: Annotated[list[str] | None, "Filter to specific activity types (e.g., ['read', 'exercise', 'cook']). Leave None for all types."] = None,
    tags: Annotated[list[str] | None, "Filter to activities with ALL of these tags (e.g., ['indoor', 'cozy']). Leave None for no tag filtering."] = None,
    duration: Annotated[str | None, "Filter by time available. Must be one of: '5min', '15min', '30min', '1h', '1h+'. Leave None for any duration."] = None,
    vibe_name: Annotated[str | None, "Apply a vibe filter (uses the vibe's tag preferences). Vibe tags are combined with the tags parameter."] = None,
) -> dict:
    """Get a random uncompleted activity suggestion. Returns a random activity that hasn't been completed yet, optionally filtered by criteria. Great for helping users decide what to do when they're bored."""
    # Resolve vibe name to vibe ID and extract tag IDs
    vibe_id = None
    vibe_tag_ids = []
    if vibe_name:
        vibe = db.get_vibe_by_name(vibe_name)
        if not vibe:
            raise ValueError(f"Vibe '{vibe_name}' not found")
        vibe_id = vibe["id"]
        vibe_tags = db.get_tags_for_vibe(vibe_id)
        vibe_tag_ids = [tag["id"] for tag in vibe_tags]

    # Resolve tag names to tag IDs
    filter_tag_ids = []
    if tags:
        for tag_name in tags:
            tag = db.get_tag_by_name(tag_name)
            if not tag:
                raise ValueError(f"Tag '{tag_name}' not found")
            filter_tag_ids.append(tag["id"])

    # Combine vibe tags and filter tags
    all_tag_ids = list(set(vibe_tag_ids + filter_tag_ids))

    # Get random activity
    activity = db.get_random_uncompleted_activity_filtered(
        activity_types=types,
        tag_ids=all_tag_ids if all_tag_ids else None,
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
    """Get all tags.

    Returns:
        list[dict]: List of tag dicts with id, name, created_at
    """
    return db.get_all_tags()


def create_tag(name: str) -> int:
    """Create a new tag.

    Parameters:
        name: Tag name

    Returns:
        int: Tag ID (existing or newly created)
    """
    # Check if tag already exists
    existing_tag = db.get_tag_by_name(name)
    if existing_tag:
        return existing_tag["id"]

    tag_id = db.create_tag(name)
    assert tag_id is not None  # db function always returns int
    return tag_id


def delete_tag(name: str) -> None:
    """Delete a tag.

    Parameters:
        name: Tag name to delete

    Raises:
        ValueError: If tag not found
    """
    tag = db.get_tag_by_name(name)
    if not tag:
        raise ValueError(f"Tag '{name}' not found")

    db.delete_tag(tag["id"])


def get_tag_details(name: str) -> dict:
    """Get tag details by name.

    Parameters:
        name: Tag name

    Returns:
        dict: Tag details

    Raises:
        ValueError: If tag not found
    """
    tag = db.get_tag_by_name(name)
    if not tag:
        raise ValueError(f"Tag '{name}' not found")

    return tag


# ============================================================================
# Vibe Management Services
# ============================================================================


def list_vibes() -> list[dict]:
    """Get all vibes with their associated tags.

    Returns:
        list[dict]: List of vibe dicts, each with tags included
    """
    vibes = db.get_all_vibes()

    # Add tags for each vibe
    for vibe in vibes:
        vibe["tags"] = db.get_tags_for_vibe(vibe["id"])

    return vibes


def create_vibe(name: str, description: str, tag_names: list[str]) -> int:
    """Create a new vibe.

    Parameters:
        name: Vibe name
        description: Vibe description
        tag_names: List of tag names to associate with this vibe

    Returns:
        int: Vibe ID

    Raises:
        ValueError: If tag names are empty or invalid tags
    """
    if not tag_names:
        raise ValueError("Vibe must have at least one tag")

    # Resolve tag names to tag IDs
    tag_ids = []
    for tag_name in tag_names:
        tag = db.get_tag_by_name(tag_name)
        if not tag:
            raise ValueError(f"Tag '{tag_name}' not found")
        tag_ids.append(tag["id"])

    vibe_id = db.create_vibe(name, description, tag_ids)
    assert vibe_id is not None  # db function always returns int
    return vibe_id


def update_vibe(
    name: str,
    new_description: str | None = None,
    tag_names: list[str] | None = None,
) -> None:
    """Update a vibe's details.

    Parameters:
        name: Current vibe name
        new_description: Optional new description
        tag_names: Optional new list of tag names

    Raises:
        ValueError: If vibe not found or invalid tags
    """
    vibe = db.get_vibe_by_name(name)
    if not vibe:
        raise ValueError(f"Vibe '{name}' not found")

    # Use existing values if not provided
    description = (
        new_description if new_description is not None else vibe["description"]
    )

    # Resolve tag names if provided
    if tag_names is not None:
        if not tag_names:
            raise ValueError("Vibe must have at least one tag")

        tag_ids = []
        for tag_name in tag_names:
            tag = db.get_tag_by_name(tag_name)
            if not tag:
                raise ValueError(f"Tag '{tag_name}' not found")
            tag_ids.append(tag["id"])
    else:
        # Keep existing tags
        existing_tags = db.get_tags_for_vibe(vibe["id"])
        tag_ids = [tag["id"] for tag in existing_tags]

    db.update_vibe(vibe["id"], name, description, tag_ids)


def delete_vibe(name: str) -> None:
    """Delete a vibe.

    Parameters:
        name: Vibe name to delete

    Raises:
        ValueError: If vibe not found
    """
    vibe = db.get_vibe_by_name(name)
    if not vibe:
        raise ValueError(f"Vibe '{name}' not found")

    db.delete_vibe(vibe["id"])


def get_vibe_details(name: str) -> dict:
    """Get vibe details by name.

    Parameters:
        name: Vibe name

    Returns:
        dict: Vibe details with tags included

    Raises:
        ValueError: If vibe not found
    """
    vibe = db.get_vibe_by_name(name)
    if not vibe:
        raise ValueError(f"Vibe '{name}' not found")

    # Add tags
    vibe["tags"] = db.get_tags_for_vibe(vibe["id"])

    return vibe


# ============================================================================
# Category Services
# ============================================================================


def list_categories() -> list[str]:
    """Get all unique activity types.

    Returns:
        list[str]: Sorted list of activity type strings
    """
    types = db.get_all_types()
    return sorted(types)


# ============================================================================
# Analytics Services
# ============================================================================


def get_stats(days: int | None = None) -> dict:
    """Get activity completion statistics.

    Parameters:
        days: Number of days to analyze (None = all time)

    Returns:
        dict: Statistics with keys like total_rolls, completed_count, etc.
    """
    return db.get_decision_stats(days=days)


def reset_stats() -> int:
    """Clear all decision event statistics.

    Returns:
        int: Number of events cleared
    """
    return db.clear_all_decision_events()


# ============================================================================
# System Services
# ============================================================================


def ensure_database() -> None:
    """Ensure database exists and is initialized.

    Creates database at default path if it doesn't exist.
    This is a non-interactive version for MCP usage.

    Raises:
        Exception: If database cannot be created
    """
    from pathlib import Path

    db_path = db.get_db_path()

    if not db_path.exists():
        # Initialize database at default location
        db.initialize_database(db_path)


def reset_recurring_activities() -> int:
    """Reset expired recurring activities.

    Returns:
        int: Number of activities reset
    """
    return db.reset_expired_recurring_activities()
