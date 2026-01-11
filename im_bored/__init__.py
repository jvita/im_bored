"""im_bored - A CLI tool for managing activities and todos."""

from im_bored.services import (
    add_activity,
    archive_activity,
    complete_activity,
    get_activity_details,
    get_random_activity,
    get_stats,
    list_activities,
    list_categories,
    list_todos,
    log_activity_completion,
    remove_activity,
    reset_stats,
    unarchive_activity,
    uncomplete_activity,
)

__all__ = [
    "add_activity",
    "archive_activity",
    "complete_activity",
    "get_activity_details",
    "get_random_activity",
    "get_stats",
    "list_activities",
    "list_categories",
    "list_todos",
    "log_activity_completion",
    "remove_activity",
    "reset_stats",
    "unarchive_activity",
    "uncomplete_activity",
]
