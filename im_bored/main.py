import argparse
import os
import re
from pathlib import Path

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from im_bored.db import (
    DB_PATH,
    initialize_database,
    set_db_path,
    DEFAULT_DB_PATH,
)
from im_bored import services
from im_bored.parsing import parse_activity, format_recurrence_days

console = Console()


def ensure_database_exists():
    """Ensure database exists, prompting user for location if needed."""
    if not os.path.exists(DB_PATH):
        from rich.prompt import Prompt, Confirm

        console.print("\n[yellow]Database not found.[/yellow]")
        console.print(f"Default location: [cyan]{DEFAULT_DB_PATH}[/cyan]\n")

        use_default = Confirm.ask(
            "Would you like to create the database in the default location?",
            default=True
        )

        if use_default:
            db_path = DEFAULT_DB_PATH
        else:
            custom_path = Prompt.ask(
                "Enter the full path where you'd like to create the database",
                default=str(DEFAULT_DB_PATH)
            )
            db_path = Path(custom_path)

        console.print(f"\n[cyan]Creating database at:[/cyan] {db_path}")

        try:
            initialize_database(db_path)
            # Save the chosen path to config
            set_db_path(db_path)
            console.print("[green]✓ Database created successfully![/green]\n")
        except Exception as e:
            console.print(f"[red]✗ Error creating database:[/red] {e}")
            raise


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

        # Add recurrence frequency if present
        if entry.get("recurrence_days"):
            recurrence_str = format_recurrence_days(entry["recurrence_days"])
            desc = f"{desc} [dim]({recurrence_str})[/dim]"

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
    # Ensure database exists, create if needed
    ensure_database_exists()

    # Reset expired recurring activities before doing anything else
    from im_bored.db import reset_expired_recurring_activities

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

    archive_parser = subparser.add_parser(
        "archive", help="Archive an activity (hides from default view, keeps history)"
    )
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

    # Default command flags
    parser.add_argument(
        "--show-archived",
        action="store_true",
        help="Show archived activities (for default command)",
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
    random_parser.add_argument("--type", type=str, help="Filter activities by type")
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

    # Log command - manually log an activity as completed
    log_parser = subparser.add_parser(
        "log", help="Log an activity as completed (marks todos as done and hides them)"
    )
    log_parser.add_argument(
        "activity_id", type=int, help="Activity ID to log as completed"
    )

    args = parser.parse_args()

    # Execute command
    command = args.command

    if command == "add":
        try:
            # Parse the activity string
            parsed = parse_activity(" ".join(args.activity))

            # Show warning about month approximation if applicable
            if parsed.get("recurrence_warning"):
                console.print(f"[yellow]⚠ {parsed['recurrence_warning']}[/yellow]")

            # Add activity via services layer
            activity_id = services.add_activity(
                type=parsed["type"],
                description=parsed["description"],
                tags=parsed["tags"],
                duration=parsed["duration"],
                completable=parsed["completable"],
                recurrence_days=parsed["recurrence_days"],
                due_date=parsed["due_date"],
            )

            # Build output message
            msg = f"Added activity {activity_id}: \\[{parsed['type']}] {parsed['description']}"
            if parsed["tags"]:
                tag_str = " ".join(f"#{tag}" for tag in parsed["tags"])
                msg += f" {tag_str}"
            if parsed["duration"]:
                msg += f" ({parsed['duration']})"
            if parsed["completable"]:
                msg += " [completable]"
            if parsed["recurrence_days"]:
                msg += f" [recurring: {parsed['recurrence_days']} days]"
            if parsed["due_date"]:
                msg += f" [due: {parsed['due_date']}]"

            console.print(msg)
        except ValueError as e:
            console.print(f"[red]✗ Error:[/red] {e}")

    elif command == "remove":
        try:
            activity = services.get_activity_details(args.index)
            services.remove_activity(args.index)
            console.print(f"✓ Removed activity {args.index}: {activity['description']}")
        except ValueError as e:
            console.print(f"[red]✗ Error:[/red] {e}")

    elif command == "archive":
        try:
            activity = services.get_activity_details(args.index)
            services.archive_activity(args.index)
            console.print(f"✓ Archived activity {args.index}: {activity['description']}")
        except ValueError as e:
            console.print(f"[red]✗ Error:[/red] {e}")

    elif command == "unarchive":
        try:
            activity = services.get_activity_details(args.index)
            services.unarchive_activity(args.index)
            console.print(f"✓ Unarchived activity {args.index}: {activity['description']}")
        except ValueError as e:
            console.print(f"[red]✗ Error:[/red] {e}")

    elif command == "activities":
        console.print("")

        # Get activities from services layer with individual parameters
        # For multiple types, we'll filter after getting all activities
        activities = services.list_activities(
            type=args.type[0] if args.type and len(args.type) == 1 else None,
            tags=args.tags if args.tags else None,
            duration=args.duration[0] if args.duration and len(args.duration) == 1 else None,
            completable_only=False,
            completed_only=args.completed if hasattr(args, 'completed') else False,
            show_archived=args.show_archived
        )

        # Filter out completed one-off completable activities
        activities = [
            a
            for a in activities
            if not (
                a.get("completable") and a["completed"] and not a.get("recurrence_days")
            )
        ]

        # Additional filtering for multiple types or durations
        if args.type and len(args.type) > 1:
            activities = [a for a in activities if a["type"] in args.type]

        if args.duration and len(args.duration) > 1:
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
        console.print("")

        # Get todos from services layer with individual parameters
        activities = services.list_todos(
            type=args.type[0] if args.type and len(args.type) == 1 else None,
            tags=args.tags if args.tags else None,
            duration=args.duration[0] if args.duration and len(args.duration) == 1 else None
        )

        # Additional filtering for multiple types or durations
        if args.type and len(args.type) > 1:
            activities = [a for a in activities if a["type"] in args.type]

        if args.duration and len(args.duration) > 1:
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
        categories = services.list_categories()
        if categories:
            console.print("\n[bold cyan]Available Categories:[/bold cyan]")
            for category in categories:
                console.print(f"  \\[{category}]")
            console.print()
        else:
            console.print("No categories found.")

    elif command == "tags":
        tags_command = args.tags_command

        if tags_command == "list" or tags_command is None:
            tags = services.list_tags()
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
            tag_id = services.create_tag(args.name)
            console.print(f"✓ Created tag: #{args.name} (ID: {tag_id})")

        elif tags_command == "delete":
            try:
                services.delete_tag(args.name)
                console.print(f"✓ Deleted tag: #{args.name}")
            except ValueError as e:
                console.print(f"[red]✗ Error:[/red] {e}")

    elif command == "log":
        try:
            activity = services.get_activity_details(args.activity_id)
            services.log_activity_completion(args.activity_id)

            # Show appropriate message based on activity type
            if activity["completable"]:
                console.print(
                    f"[green]✓[/green] Completed and removed from to-do list: [{activity['type']}] {activity['description']}"
                )
            else:
                console.print(
                    f"[green]✓[/green] Logged [{activity['type']}] {activity['description']} as completed"
                )
        except ValueError as e:
            console.print(f"[red]✗ Error:[/red] {e}")

    elif command == "stats":
        # Handle reset flag
        if args.reset:
            from rich.prompt import Confirm

            if Confirm.ask(
                "[yellow]Are you sure you want to clear ALL statistics? This cannot be undone.[/yellow]"
            ):
                count = services.reset_stats()
                console.print(f"[green]✓ Cleared {count} decision events[/green]")
            else:
                console.print("Cancelled.")
            return

        stats = services.get_stats(days=args.days)

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
        try:
            activity = services.get_activity_details(args.index)
            services.complete_activity(args.index)
            console.print(
                f"✓ Marked activity {args.index} as complete: {activity['description']}"
            )
        except ValueError as e:
            console.print(f"[red]✗ Error:[/red] {e}")

    elif args.command == "incomplete":
        try:
            activity = services.get_activity_details(args.index)
            services.uncomplete_activity(args.index)
            console.print(
                f"Marked activity {args.index} as incomplete: {activity['description']}"
            )
        except ValueError as e:
            console.print(f"[red]✗ Error:[/red] {e}")

    elif command == "random":
        # Get random activity with individual parameters
        try:
            choice = services.get_random_activity(
                types=[args.type] if args.type else None,
                tags=[t.strip() for t in args.tags.split(",")] if args.tags else None,
                duration=args.duration if args.duration else None,
            )
        except ValueError as e:
            # Build filter message
            filter_parts = []
            if args.type:
                filter_parts.append(f"type '{args.type}'")
            if args.duration:
                filter_parts.append(f"duration '{args.duration}'")
            if args.tags:
                filter_parts.append(f"tags '{args.tags}'")

            filter_msg = " with " + ", ".join(filter_parts) if filter_parts else ""
            console.print(
                f"No uncompleted activities found{filter_msg}. Add some with 'imbored add \"[type] activity\"'"
            )
            return

        # Display the choice
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
        # Default imbored command - list all activities (excluding to-do)
        console.print("")

        # Get activities from services layer with individual parameters
        activities = services.list_activities(
            type=args.type if args.type else None,
            tags=[t.strip() for t in args.tags.split(",")] if args.tags else None,
            duration=args.duration if args.duration else None,
            completable_only=False,
            completed_only=False,
            show_archived=args.show_archived
        )

        # Filter out completed one-off completable activities
        activities = [
            a
            for a in activities
            if not (
                a.get("completable") and a["completed"] and not a.get("recurrence_days")
            )
        ]

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
