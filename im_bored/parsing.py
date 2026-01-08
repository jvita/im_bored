"""Parsing utilities for im_bored application."""

import re
from datetime import datetime


def parse_activity(activity: str) -> dict:
    """Parse an activity string into a structured dictionary.

    Format: [type] description #tag1 #tag2 --duration 15min --completable --recurring 2weeks --due 2026-01-15
    If no type is specified, defaults to 'general'
    Hashtags are extracted as tags
    --duration flag specifies duration
    --completable flag marks this as a one-off to-do activity
    --recurring flag specifies recurrence period
    --due flag specifies due date

    Args:
        activity: The activity string to parse

    Returns:
        dict: Parsed activity with keys:
            - type: Activity type (str)
            - description: Clean description without tags/flags (str)
            - tags: List of tag names (list[str])
            - duration: Duration string or None (str | None)
            - completed: Always 0 for new activities (int)
            - completable: Whether this is a completable todo (bool)
            - recurrence_days: Recurrence period in days or None (int | None)
            - recurrence_warning: Warning message if recurrence parsing had issues (str | None)
            - due_date: Due date in ISO format or None (str | None)

    Raises:
        ValueError: If both --recurring and --due are specified, or if date format is invalid
    """
    from im_bored.db import parse_tags_from_description, parse_recurrence_to_days

    # Extract type
    type_pattern = r"^\[(.*?)\]\s*"
    match = re.match(type_pattern, activity)

    if match:
        activity_type = match.group(1).strip()
        remaining = activity[match.end() :].strip()
    else:
        activity_type = "general"
        remaining = activity.strip()

    # Extract completable flag
    completable = False
    if "--completable" in remaining:
        completable = True
        remaining = remaining.replace("--completable", "").strip()

    # Extract recurring flag
    recurring_match = re.search(r"--recurring\s+(\S+)", remaining)
    recurrence_days = None
    recurrence_warning = None
    if recurring_match:
        completable = True
        recurrence_str = recurring_match.group(1)
        recurrence_days, recurrence_warning = parse_recurrence_to_days(recurrence_str)
        remaining = remaining.replace(recurring_match.group(0), "").strip()

    # Extract due date flag
    due_match = re.search(r"--due\s+(\S+)", remaining)
    due_date = None
    if due_match:
        completable = True
        if recurrence_days is not None:
            raise ValueError("Cannot use both --recurring and --due flags")
        due_date = due_match.group(1)
        # Validate date format (basic check)
        try:
            datetime.fromisoformat(due_date)
        except ValueError:
            raise ValueError(
                f"Invalid date format: {due_date}. Use ISO format like 2026-01-15"
            )
        remaining = remaining.replace(due_match.group(0), "").strip()

    # Extract duration flag
    duration_match = re.search(r"--duration\s+(\S+)", remaining)
    duration = None
    if duration_match:
        duration_str = duration_match.group(1)
        # Validate duration
        if duration_str in ["5min", "15min", "30min", "1h", "1h+"]:
            duration = duration_str
        remaining = remaining.replace(duration_match.group(0), "").strip()

    # Extract hashtags and clean description
    clean_description, tags = parse_tags_from_description(remaining)

    return {
        "type": activity_type,
        "description": clean_description,
        "tags": tags,
        "duration": duration,
        "completed": 0,
        "completable": completable,
        "recurrence_days": recurrence_days,
        "recurrence_warning": recurrence_warning,
        "due_date": due_date,
    }


def format_recurrence_days(days: int) -> str:
    """Format recurrence days into a human-readable string.

    Args:
        days: Number of days

    Returns:
        str: Formatted string like "every 7d", "every 2w", "every 1m"

    Examples:
        >>> format_recurrence_days(7)
        'every 1w'
        >>> format_recurrence_days(30)
        'every 1m'
        >>> format_recurrence_days(5)
        'every 5d'
    """
    if days % 30 == 0 and days >= 30:
        months = days // 30
        return f"every {months}m"
    elif days % 7 == 0 and days >= 7:
        weeks = days // 7
        return f"every {weeks}w"
    else:
        return f"every {days}d"
