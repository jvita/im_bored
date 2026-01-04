import argparse
import os
import re

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from im_bored.db import DB_PATH, get_db_connection

console = Console()


def parse_activity(activity: str) -> dict:
    """Parse an activity string into a structured dictionary.

    Format: [type] description #tag1 #tag2 --duration 15min --completable --recurring 2weeks --due 2026-01-15
    If no type is specified, defaults to 'general'
    Hashtags are extracted as tags
    --duration flag specifies duration
    --completable flag marks this as a one-off to-do activity
    --recurring flag specifies recurrence period (requires --completable)
    --due flag specifies due date (requires --completable)
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
        if not completable:
            raise ValueError("--recurring requires --completable flag")
        recurrence_str = recurring_match.group(1)
        recurrence_days, recurrence_warning = parse_recurrence_to_days(recurrence_str)
        remaining = remaining.replace(recurring_match.group(0), "").strip()

    # Extract due date flag
    due_match = re.search(r"--due\s+(\S+)", remaining)
    due_date = None
    if due_match:
        if not completable:
            raise ValueError("--due requires --completable flag")
        if recurrence_days is not None:
            raise ValueError("Cannot use both --recurring and --due flags")
        due_date = due_match.group(1)
        # Validate date format (basic check)
        try:
            from datetime import datetime
            datetime.fromisoformat(due_date)
        except ValueError:
            raise ValueError(f"Invalid date format: {due_date}. Use ISO format like 2026-01-15")
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


def create_panel(data, title, width=None, show_completable=False):
    from datetime import datetime

    table = Table(
        show_header=True,
        show_edge=False,
        pad_edge=False,
        box=None,
        header_style="cyan",
        row_styles=["", "yellow"],
    )
    table.add_column("ID", justify="right", width=3)

    table.add_column("Description")

    for ei, entry in data:
        # Build description with tags and duration
        desc = entry["description"]
        is_archived = entry.get("archived", 0) == 1

        # Check if overdue (only for scheduled tasks with due_date)
        is_overdue = False
        if entry.get("due_date") and not entry["completed"]:
            try:
                due = datetime.fromisoformat(entry["due_date"])
                is_overdue = datetime.now() > due
            except (ValueError, TypeError):
                pass

        # Add checkbox indicator for completable activities
        if show_completable and entry.get("completable"):
            if entry.get("recurrence_days"):
                # Recurring task - use ⟳ symbol
                checkbox = "✓" if entry["completed"] else "⟳"
            else:
                # Regular completable or scheduled task
                checkbox = "✓" if entry["completed"] else "☐"
            desc = f"{checkbox} {desc}"

        # Add tags if present
        if entry.get("tags"):
            tag_str = " ".join(f"[dim]#{tag['name']}[/dim]" for tag in entry["tags"])
            desc = f"{desc} {tag_str}"

        # Add duration if present
        if entry.get("duration"):
            desc = f"{desc} [dim cyan]({entry['duration']})[/dim cyan]"

        # Add due date if present
        if entry.get("due_date"):
            due_str = entry["due_date"]
            if is_overdue:
                desc = f"[red]{desc} (due: {due_str})[/red]"
            else:
                desc = f"{desc} [dim](due: {due_str})[/dim]"

        # Apply styling based on archived status
        if is_archived:
            # Dim archived activities and add [archived] label
            desc = f"[dim]{desc} [italic]\\[archived][/italic][/dim]"
            id_str = f"[dim]{ei}[/dim]"
        else:
            id_str = str(ei)

        table.add_row(id_str, desc)

    return Panel(
        table,
        title=title,
        border_style="magenta",
        width=width,
    )


def main():
    # Reset expired recurring activities before doing anything else
    from im_bored.db import reset_expired_recurring_activities

    # Check database exists first
    if os.path.exists(DB_PATH):
        try:
            reset_expired_recurring_activities()
        except Exception:
            # Silently ignore errors (e.g., if columns don't exist yet)
            pass

    # Load arguments
    parser = argparse.ArgumentParser(description="im-bored CLI")
    parser.add_argument(
        "--type", type=str, help="Filter activities by type (for default command)"
    )
    parser.add_argument(
        "--duration",
        type=str,
        help="Filter activities by duration (for default command)",
    )
    parser.add_argument(
        "--tags",
        type=str,
        help="Filter activities by tags (comma-separated, for default command)",
    )

    subparser = parser.add_subparsers(dest="command")

    add_parser = subparser.add_parser("add", help="Add a new activity")
    add_parser.add_argument(
        "activity", type=str, help="The activity to add", nargs=argparse.REMAINDER
    )

    complete_parser = subparser.add_parser(
        "complete", help="Mark an activity as complete"
    )
    complete_parser.add_argument(
        "index", type=int, help="The ID of the activity to complete"
    )

    incomplete_parser = subparser.add_parser(
        "incomplete", help="Mark an activity as incomplete"
    )
    incomplete_parser.add_argument(
        "index", type=int, help="The ID of the activity to mark as incomplete"
    )

    remove_parser = subparser.add_parser("remove", help="Remove an activity")
    remove_parser.add_argument(
        "index", type=int, help="The ID of the activity to remove"
    )

    archive_parser = subparser.add_parser("archive", help="Archive an activity (hides from default view, keeps history)")
    archive_parser.add_argument(
        "index", type=int, help="The ID of the activity to archive"
    )

    unarchive_parser = subparser.add_parser("unarchive", help="Unarchive an activity")
    unarchive_parser.add_argument(
        "index", type=int, help="The ID of the activity to unarchive"
    )

    activities_parser = subparser.add_parser(
        "activities", help="List all activities (excluding to-do)"
    )
    activities_parser.add_argument(
        "--type", type=str, nargs="+", help="Filter by activity types"
    )
    activities_parser.add_argument("--tags", type=str, nargs="+", help="Filter by tags")
    activities_parser.add_argument(
        "--duration", type=str, nargs="+", help="Filter by duration"
    )
    activities_parser.add_argument(
        "--completed", action="store_true", help="Show only completed activities"
    )
    activities_parser.add_argument(
        "--show-archived", action="store_true", help="Show archived activities"
    )

    todo_parser = subparser.add_parser("todo", help="Show the to-do list")
    todo_parser.add_argument(
        "--type", type=str, nargs="+", help="Filter by activity types"
    )
    todo_parser.add_argument("--tags", type=str, nargs="+", help="Filter by tags")
    todo_parser.add_argument(
        "--duration", type=str, nargs="+", help="Filter by duration"
    )

    # Categories command
    subparser.add_parser("categories", help="List all activity categories")

    # Tag management commands
    tags_parser = subparser.add_parser("tags", help="Manage tags")
    tags_subparser = tags_parser.add_subparsers(dest="tags_command")

    tags_subparser.add_parser("list", help="List all tags")

    tags_create_parser = tags_subparser.add_parser("create", help="Create a new tag")
    tags_create_parser.add_argument("name", type=str, help="Tag name")

    tags_delete_parser = tags_subparser.add_parser("delete", help="Delete a tag")
    tags_delete_parser.add_argument("name", type=str, help="Tag name")

    # Vibe management commands
    vibes_parser = subparser.add_parser("vibes", help="Manage vibes")
    vibes_subparser = vibes_parser.add_subparsers(dest="vibes_command")

    vibes_subparser.add_parser("list", help="List all vibes")

    vibes_create_parser = vibes_subparser.add_parser("create", help="Create a new vibe")
    vibes_create_parser.add_argument("name", type=str, help="Vibe name")

    vibes_edit_parser = vibes_subparser.add_parser("edit", help="Edit a vibe's tags")
    vibes_edit_parser.add_argument("name", type=str, help="Vibe name")

    vibes_delete_parser = vibes_subparser.add_parser("delete", help="Delete a vibe")
    vibes_delete_parser.add_argument("name", type=str, help="Vibe name")

    # Add --vibe flag to default command
    parser.add_argument(
        "--vibe", type=str, help="Filter activities by vibe (for default command)"
    )
    parser.add_argument(
        "--show-archived", action="store_true", help="Show archived activities (for default command)"
    )

    # Stats command
    stats_parser = subparser.add_parser("stats", help="Show analytics and statistics")
    stats_parser.add_argument(
        "--days",
        type=int,
        help="Number of days to analyze. If not provided, uses all stats.",
    )
    stats_parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset all statistics (clear decision events)",
    )

    # Random command - pick a random activity with filtering
    random_parser = subparser.add_parser("random", help="Pick a random activity")
    random_parser.add_argument(
        "--type", type=str, help="Filter activities by type"
    )
    random_parser.add_argument(
        "--duration",
        type=str,
        help="Filter activities by duration",
    )
    random_parser.add_argument(
        "--tags",
        type=str,
        help="Filter activities by tags (comma-separated)",
    )
    random_parser.add_argument(
        "--vibe", type=str, help="Filter activities by vibe"
    )

    # Log command - manually log an activity as completed
    log_parser = subparser.add_parser(
        "log", help="Log an activity as completed (marks todos as done and hides them)"
    )
    log_parser.add_argument(
        "activity_id", type=int, help="Activity ID to log as completed"
    )

    args = parser.parse_args()

    # Check database exists
    if not os.path.exists(DB_PATH):
        console.print("✗ Database not found. Please run the migration script first:")
        console.print("  python migrate_to_sqlite.py")
        return

    # Execute command
    command = args.command

    if command == "add":
        from im_bored.db import add_activity_with_tags

        try:
            parsed = parse_activity(" ".join(args.activity))
        except ValueError as e:
            console.print(f"[red]✗ Error:[/red] {e}")
            return

        activity_type = parsed["type"]
        description = parsed["description"]
        tags = parsed["tags"]
        duration = parsed["duration"]
        completable = parsed["completable"]
        recurrence_days = parsed["recurrence_days"]
        recurrence_warning = parsed["recurrence_warning"]
        due_date = parsed["due_date"]

        # Show warning about month approximation if applicable
        if recurrence_warning:
            console.print(f"[yellow]⚠ {recurrence_warning}[/yellow]")

        # Add activity with tags
        try:
            activity_id = add_activity_with_tags(
                activity_type, description, tags, duration, completable,
                recurrence_days, due_date
            )
        except ValueError as e:
            console.print(f"[red]✗ Error:[/red] {e}")
            return

        # Build output message
        msg = f"Added activity: \\[{activity_type}] {description}"
        if tags:
            tag_str = " ".join(f"#{tag}" for tag in tags)
            msg += f" {tag_str}"
        if duration:
            msg += f" ({duration})"
        if completable:
            msg += " [completable]"
        if recurrence_days:
            msg += f" [recurring: {recurrence_days} days]"
        if due_date:
            msg += f" [due: {due_date}]"

        console.print(msg)

    elif command == "remove":
        from im_bored.db import delete_activity, get_activity_by_id

        activity = get_activity_by_id(args.index)
        if not activity:
            console.print(f"✗ Activity ID {args.index} not found")
            return

        delete_activity(args.index)
        console.print(f"✓ Removed activity {args.index}: {activity['description']}")

    elif command == "archive":
        from im_bored.db import archive_activity, get_activity_by_id

        activity = get_activity_by_id(args.index)
        if not activity:
            console.print(f"✗ Activity ID {args.index} not found")
            return

        if activity.get("archived"):
            console.print(f"Activity {args.index} is already archived")
            return

        archive_activity(args.index)
        console.print(f"✓ Archived activity {args.index}: {activity['description']}")

    elif command == "unarchive":
        from im_bored.db import unarchive_activity, get_activity_by_id

        activity = get_activity_by_id(args.index)
        if not activity:
            console.print(f"✗ Activity ID {args.index} not found")
            return

        if not activity.get("archived"):
            console.print(f"Activity {args.index} is not archived")
            return

        unarchive_activity(args.index)
        console.print(f"✓ Unarchived activity {args.index}: {activity['description']}")
    elif command == "activities":
        from im_bored.db import get_tags_for_activity

        console.print("")

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM activities ORDER BY id")
            activities = [dict(row) for row in cursor.fetchall()]

        # Filter out completed one-off completable activities
        activities = [
            a for a in activities
            if not (a.get("completable") and a["completed"] and not a.get("recurrence_days"))
        ]

        # Filter out archived activities unless --show-archived is set
        if not args.show_archived:
            activities = [a for a in activities if not a.get("archived")]

        # Fetch tags for each activity
        for activity in activities:
            activity["tags"] = get_tags_for_activity(activity["id"])

        # Filter by completion status if specified
        if args.completed:
            activities = [a for a in activities if a["completed"] == 1]

        # Filter by types if specified
        if args.type:
            activities = [a for a in activities if a["type"] in args.type]

        # Filter by tags if specified
        if args.tags:
            # Convert tag names to lowercase for case-insensitive comparison
            filter_tag_names = [tag.lower() for tag in args.tags]
            activities = [
                a
                for a in activities
                if any(tag["name"].lower() in filter_tag_names for tag in a["tags"])
            ]

        # Filter by duration if specified
        if args.duration:
            activities = [a for a in activities if a.get("duration") in args.duration]

        grouped_data = {}
        for activity in activities:
            if activity["type"] not in grouped_data:
                grouped_data[activity["type"]] = []
            # Use actual database ID instead of enumeration index
            grouped_data[activity["type"]].append((activity["id"], activity))

        panels = []

        # Add all types in sorted order (including general)
        for act_type in sorted(grouped_data.keys()):
            panels.append(
                create_panel(
                    grouped_data[act_type], act_type, width=40, show_completable=True
                )
            )

        if panels:
            console.print(
                Columns(panels, equal=True, expand=True, column_first=True, padding=1)
            )
        else:
            console.print("No activities found.")
        console.print()

    elif command == "todo":
        from im_bored.db import get_tags_for_activity

        console.print("")

        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Only get incomplete completable activities that are not archived
            cursor.execute(
                "SELECT * FROM activities WHERE completed = 0 AND completable = 1 AND archived = 0 ORDER BY id"
            )
            activities = [dict(row) for row in cursor.fetchall()]

        # Fetch tags for each activity
        for activity in activities:
            activity["tags"] = get_tags_for_activity(activity["id"])

        # Filter by types if specified
        if args.type:
            activities = [a for a in activities if a["type"] in args.type]

        # Filter by tags if specified
        if args.tags:
            # Convert tag names to lowercase for case-insensitive comparison
            filter_tag_names = [tag.lower() for tag in args.tags]
            activities = [
                a
                for a in activities
                if any(tag["name"].lower() in filter_tag_names for tag in a["tags"])
            ]

        # Filter by duration if specified
        if args.duration:
            activities = [a for a in activities if a.get("duration") in args.duration]

        grouped_data = {}
        for activity in activities:
            if activity["type"] not in grouped_data:
                grouped_data[activity["type"]] = []
            # Use actual database ID instead of enumeration index
            grouped_data[activity["type"]].append((activity["id"], activity))

        panels = []

        # Add all types in sorted order (including general)
        for act_type in sorted(grouped_data.keys()):
            panels.append(
                create_panel(
                    grouped_data[act_type], act_type, width=40, show_completable=True
                )
            )

        if panels:
            console.print(
                Columns(panels, equal=True, expand=True, column_first=True, padding=1)
            )
        else:
            console.print("No incomplete to-do items found.")
        console.print()

    elif command == "categories":
        from im_bored.db import get_all_types

        categories = get_all_types()
        if categories:
            console.print("\n[bold cyan]Available Categories:[/bold cyan]")
            for category in categories:
                console.print(f"  \\[{category}]")
            console.print()
        else:
            console.print("No categories found.")

    elif command == "tags":
        from im_bored.db import get_all_tags, create_tag, get_tag_by_name, delete_tag

        tags_command = args.tags_command

        if tags_command == "list" or tags_command is None:
            tags = get_all_tags()
            if tags:
                console.print("\n[bold cyan]Available Tags:[/bold cyan]")
                table = Table(show_header=True, box=None, header_style="cyan")
                table.add_column("ID", justify="right", width=5)
                table.add_column("Name")

                for tag in tags:
                    table.add_row(str(tag["id"]), f"#{tag['name']}")

                console.print(table)
                console.print()
            else:
                console.print("No tags found.")

        elif tags_command == "create":
            tag_id = create_tag(args.name)
            console.print(f"✓ Created tag: #{args.name} (ID: {tag_id})")

        elif tags_command == "delete":
            tag = get_tag_by_name(args.name)
            if tag:
                if delete_tag(tag["id"]):
                    console.print(f"✓ Deleted tag: #{args.name}")
                else:
                    console.print(f"✗ Failed to delete tag: #{args.name}")
            else:
                console.print(f"✗ Tag not found: #{args.name}")

    elif command == "vibes":
        from im_bored.db import (
            get_all_vibes,
            create_vibe,
            get_vibe_by_name,
            delete_vibe,
            update_vibe,
            get_all_tags,
            get_tag_by_name,
        )
        from rich.prompt import Prompt

        vibes_command = args.vibes_command

        if vibes_command == "list" or vibes_command is None:
            vibes = get_all_vibes()
            if vibes:
                console.print("\n[bold cyan]Available Vibes:[/bold cyan]")
                for vibe in vibes:
                    tag_str = ", ".join(f"#{tag['name']}" for tag in vibe["tags"])
                    desc = (
                        f" - {vibe['description']}" if vibe.get("description") else ""
                    )
                    console.print(f"  [bold]{vibe['name']}[/bold]{desc}")
                    console.print(f"    Tags: {tag_str}")
                console.print()
            else:
                console.print("No vibes found.")

        elif vibes_command == "create":
            # Get all tags for selection
            all_tags = get_all_tags()
            if not all_tags:
                console.print(
                    "✗ No tags available. Create some tags first with 'imbored tag create <name>'"
                )
                return

            # Show available tags
            console.print("\n[bold cyan]Available Tags:[/bold cyan]")
            for i, tag in enumerate(all_tags, 1):
                console.print(f"  {i}. #{tag['name']}")

            # Prompt for description
            description = Prompt.ask("\nVibe description (optional)", default="")

            # Prompt for tags
            console.print(
                "\nEnter tag numbers (comma-separated) or tag names (comma-separated with #):"
            )
            tag_input = Prompt.ask("Tags")

            # Parse tag input
            selected_tag_ids = []
            for item in tag_input.split(","):
                item = item.strip()
                if item.startswith("#"):
                    # Tag name
                    tag_name = item[1:]
                    tag = get_tag_by_name(tag_name)
                    if tag:
                        selected_tag_ids.append(tag["id"])
                    else:
                        console.print(
                            f"[yellow]Warning: Tag '{item}' not found, skipping[/yellow]"
                        )
                elif item.isdigit():
                    # Tag number
                    idx = int(item) - 1
                    if 0 <= idx < len(all_tags):
                        selected_tag_ids.append(all_tags[idx]["id"])
                    else:
                        console.print(
                            f"[yellow]Warning: Invalid tag number {item}, skipping[/yellow]"
                        )

            if selected_tag_ids:
                vibe_id = create_vibe(args.name, description, selected_tag_ids)
                tag_names = [
                    tag["name"] for tag in all_tags if tag["id"] in selected_tag_ids
                ]
                tag_str = ", ".join(f"#{name}" for name in tag_names)
                console.print(f"\n✓ Created vibe: {args.name} with tags: {tag_str}")
            else:
                console.print("✗ No valid tags selected. Vibe not created.")

        elif vibes_command == "edit":
            vibe = get_vibe_by_name(args.name)
            if not vibe:
                console.print(f"✗ Vibe not found: {args.name}")
                return

            # Get all tags for selection
            all_tags = get_all_tags()
            current_tag_names = {tag["name"] for tag in vibe["tags"]}

            # Show available tags with current selection marked
            console.print(f"\n[bold cyan]Editing vibe: {args.name}[/bold cyan]")
            console.print("\n[bold]Available Tags:[/bold] (✓ = currently selected)")
            for i, tag in enumerate(all_tags, 1):
                mark = "✓" if tag["name"] in current_tag_names else " "
                console.print(f"  {mark} {i}. #{tag['name']}")

            # Prompt for new tags
            console.print(
                "\nEnter tag numbers (comma-separated) or tag names (comma-separated with #):"
            )
            console.print("[dim]Leave blank to keep current tags[/dim]")
            tag_input = Prompt.ask("New tags", default="")

            if not tag_input.strip():
                console.print("No changes made.")
                return

            # Parse tag input
            selected_tag_ids = []
            for item in tag_input.split(","):
                item = item.strip()
                if item.startswith("#"):
                    # Tag name
                    tag_name = item[1:]
                    tag = get_tag_by_name(tag_name)
                    if tag:
                        selected_tag_ids.append(tag["id"])
                elif item.isdigit():
                    # Tag number
                    idx = int(item) - 1
                    if 0 <= idx < len(all_tags):
                        selected_tag_ids.append(all_tags[idx]["id"])

            if selected_tag_ids:
                update_vibe(
                    vibe["id"],
                    vibe["name"],
                    vibe.get("description", ""),
                    selected_tag_ids,
                )
                tag_names = [
                    tag["name"] for tag in all_tags if tag["id"] in selected_tag_ids
                ]
                tag_str = ", ".join(f"#{name}" for name in tag_names)
                console.print(f"\n✓ Updated vibe: {args.name} with tags: {tag_str}")
            else:
                console.print("✗ No valid tags selected.")

        elif vibes_command == "delete":
            vibe = get_vibe_by_name(args.name)
            if vibe:
                if delete_vibe(vibe["id"]):
                    console.print(f"✓ Deleted vibe: {args.name}")
                else:
                    console.print(f"✗ Failed to delete vibe: {args.name}")
            else:
                console.print(f"✗ Vibe not found: {args.name}")

    elif command == "log":
        from im_bored.db import (
            get_activity_by_id,
            log_decision_event,
            update_activity_completion,
        )
        import uuid

        # Get the activity
        activity = get_activity_by_id(args.activity_id)
        if not activity:
            console.print(f"✗ Activity ID {args.activity_id} not found")
            return

        # Log the decision event
        session_id = str(uuid.uuid4())
        log_decision_event(
            activity_id=activity["id"],
            outcome="COMPLETED",  # Only log completed activities
            vibe_id=None,  # No vibe for manual logs
            filter_tags=None,
            session_id=session_id,
        )

        # Only mark as completed if it's a completable activity
        if activity["completable"]:
            update_activity_completion(activity["id"], True)
            console.print(
                f"[green]✓[/green] Completed and removed from to-do list: [{activity['type']}] {activity['description']}"
            )
        else:
            console.print(
                f"[green]✓[/green] Logged [{activity['type']}] {activity['description']} as completed"
            )

    elif command == "stats":
        from im_bored.db import get_decision_stats, clear_all_decision_events

        # Handle reset flag
        if args.reset:
            from rich.prompt import Confirm

            if Confirm.ask(
                "[yellow]Are you sure you want to clear ALL statistics? This cannot be undone.[/yellow]"
            ):
                count = clear_all_decision_events()
                console.print(f"[green]✓ Cleared {count} decision events[/green]")
            else:
                console.print("Cancelled.")
            return

        stats = get_decision_stats(days=args.days)

        console.print(
            f"\n[bold cyan]Activity Log{" (Last {stats['days']} days)" if args.days is not None else ""}[/bold cyan]\n"
        )

        # Overall metrics - simplified to just show completed count
        if stats["completed_count"] > 0:
            console.print(
                f"[green]✓ {stats['completed_count']} activities completed[/green]\n"
            )

            # Most completed activities
            if stats["most_completed"]:
                console.print("[bold green]Recently Completed:[/bold green]")
                completed_table = Table(
                    show_header=True, box=None, header_style="green"
                )
                completed_table.add_column("Activity", style="bold")
                completed_table.add_column("Type", style="dim")
                completed_table.add_column("Count", justify="right")

                for activity in stats["most_completed"]:
                    completed_table.add_row(
                        activity["description"],
                        f"[{activity['type']}]",
                        str(activity["count"]),
                    )

                console.print(completed_table)
                console.print()
        else:
            console.print(
                "[dim]No activities logged yet. Use 'imbored log <id>' to track completed activities.[/dim]\n"
            )

    elif args.command == "complete":
        from im_bored.db import update_activity_completion, get_activity_by_id

        activity = get_activity_by_id(args.index)
        if not activity:
            console.print(f"✗ Activity ID {args.index} not found")
            return

        update_activity_completion(args.index, True)
        console.print(
            f"✓ Marked activity {args.index} as complete: {activity['description']}"
        )

    elif args.command == "incomplete":
        from im_bored.db import update_activity_completion, get_activity_by_id

        activity = get_activity_by_id(args.index)
        if not activity:
            console.print(f"✗ Activity ID {args.index} not found")
            return

        update_activity_completion(args.index, False)
        console.print(
            f"Marked activity {args.index} as incomplete: {activity['description']}"
        )

    elif command == "random":
        # Random command - pick a random activity with filtering
        from im_bored.db import (
            get_random_uncompleted_activity_filtered,
            get_tag_by_name,
            get_vibe_by_name,
        )

        # Prepare filters
        activity_types = [args.type] if args.type else None
        duration = args.duration if args.duration else None

        # Parse vibe name to vibe ID
        vibe_id = None
        if args.vibe:
            vibe = get_vibe_by_name(args.vibe)
            if vibe:
                vibe_id = vibe["id"]
                console.print(f"[dim cyan]Applying vibe: {args.vibe}[/dim cyan]")
            else:
                console.print(f"[yellow]Warning: Vibe '{args.vibe}' not found[/yellow]")

        # Parse tag names to tag IDs
        tag_ids = None
        if args.tags:
            tag_names = [t.strip() for t in args.tags.split(",")]
            tag_ids = []
            for tag_name in tag_names:
                tag = get_tag_by_name(tag_name)
                if tag:
                    tag_ids.append(tag["id"])
                else:
                    console.print(
                        f"[yellow]Warning: Tag '#{tag_name}' not found, ignoring[/yellow]"
                    )
            if not tag_ids:
                tag_ids = None

        # Get random activity
        choice = get_random_uncompleted_activity_filtered(
            activity_types=activity_types,
            tag_ids=tag_ids,
            duration=duration,
            vibe_id=vibe_id,
        )

        if choice:
            panel = Panel(
                f"\n[cyan]({choice['type']})[/cyan]\n\n[bold]{choice['description']}[/bold]",
                title="How about you...",
                border_style="green",
                subtitle="?",
                subtitle_align="right",
                expand=False,
            )

            console.print()
            console.print(panel)
            console.print()
        else:
            # Build filter message
            filters = []
            if args.type:
                filters.append(f"type '{args.type}'")
            if duration:
                filters.append(f"duration '{duration}'")
            if args.tags:
                filters.append(f"tags '{args.tags}'")

            filter_msg = " with " + ", ".join(filters) if filters else ""
            console.print(
                f"No uncompleted activities found{filter_msg}. Add some with 'imbored add \"[type] activity\"'"
            )

    else:
        # Default imbored command - list all activities (excluding to-do)
        from im_bored.db import get_tags_for_activity

        console.print("")

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM activities ORDER BY id")
            activities = [dict(row) for row in cursor.fetchall()]

        # Filter out completed one-off completable activities
        activities = [
            a for a in activities
            if not (a.get("completable") and a["completed"] and not a.get("recurrence_days"))
        ]

        # Filter out archived activities unless --show-archived is set
        if not args.show_archived:
            activities = [a for a in activities if not a.get("archived")]

        # Fetch tags for each activity
        for activity in activities:
            activity["tags"] = get_tags_for_activity(activity["id"])

        # Filter by types if specified
        if args.type:
            activities = [a for a in activities if a["type"] == args.type]

        # Parse tag names to list for filtering
        filter_tags = None
        if args.tags:
            filter_tags = [t.strip() for t in args.tags.split(",")]

        # Filter by tags if specified
        if filter_tags:
            # Convert tag names to lowercase for case-insensitive comparison
            filter_tag_names = [tag.lower() for tag in filter_tags]
            activities = [
                a
                for a in activities
                if any(tag["name"].lower() in filter_tag_names for tag in a["tags"])
            ]

        # Filter by duration if specified
        if args.duration:
            activities = [a for a in activities if a.get("duration") == args.duration]

        # Parse vibe and apply its tag filter
        if args.vibe:
            from im_bored.db import get_vibe_by_name

            vibe = get_vibe_by_name(args.vibe)
            if vibe:
                console.print(f"[dim cyan]Applying vibe: {args.vibe}[/dim cyan]\n")
                vibe_tag_names = [tag["name"].lower() for tag in vibe["tags"]]
                activities = [
                    a
                    for a in activities
                    if any(tag["name"].lower() in vibe_tag_names for tag in a["tags"])
                ]
            else:
                console.print(f"[yellow]Warning: Vibe '{args.vibe}' not found[/yellow]\n")

        grouped_data = {}
        for activity in activities:
            if activity["type"] not in grouped_data:
                grouped_data[activity["type"]] = []
            # Use actual database ID instead of enumeration index
            grouped_data[activity["type"]].append((activity["id"], activity))

        panels = []

        # Add all types in sorted order (including general)
        for act_type in sorted(grouped_data.keys()):
            panels.append(
                create_panel(
                    grouped_data[act_type], act_type, width=40, show_completable=True
                )
            )

        if panels:
            console.print(
                Columns(panels, equal=True, expand=True, column_first=True, padding=1)
            )
        else:
            console.print("No activities found.")
        console.print()
