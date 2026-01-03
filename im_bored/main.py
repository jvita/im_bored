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

    Format: [type] description
    If no type is specified, defaults to 'general'
    """
    type_pattern = r"^\[(.*?)\]\s*"
    match = re.match(type_pattern, activity)

    if match:
        activity_type = match.group(1).strip()
        activity_description = activity[match.end() :].strip()
    else:
        activity_type = "general"
        activity_description = activity.strip()

    return {
        "type": activity_type,
        "description": activity_description,
        "completed": 0,
    }


def create_panel(data, title, width=None):
    table = Table(
        show_header=True,
        show_edge=False,
        pad_edge=False,
        box=None,
        header_style="cyan",
        row_styles=["", "yellow"],
    )
    table.add_column("ID", justify="right", width=3)

    # Only show "Done" column for "todo" activity type
    show_done = title == "todo"
    if show_done:
        table.add_column("Done", justify="center", width=4)

    table.add_column("Description")

    for ei, entry in data:
        if show_done:
            done_mark = "✔" if entry["completed"] else " "
            table.add_row(str(ei), done_mark, entry["description"])
        else:
            table.add_row(str(ei), entry["description"])

    return Panel(
        table,
        title=title,
        border_style="magenta",
        width=width,
    )


def main():
    # Load arguments
    parser = argparse.ArgumentParser(description="im-bored CLI")
    parser.add_argument(
        "--type", type=str, help="Filter activities by type (for default command)"
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
        "index", type=int, help="The index of the activity to complete"
    )

    incomplete_parser = subparser.add_parser(
        "incomplete", help="Mark an activity as incomplete"
    )
    incomplete_parser.add_argument(
        "index", type=int, help="The index of the activity to mark as incomplete"
    )

    remove_parser = subparser.add_parser("remove", help="Remove an activity")
    remove_parser.add_argument(
        "index", type=int, help="The index of the activity to remove"
    )

    subparser.add_parser("activities", help="List all activities (excluding to-do)")

    subparser.add_parser("todo", help="Show the to-do list")

    args = parser.parse_args()

    # Check database exists
    if not os.path.exists(DB_PATH):
        console.print("✗ Database not found. Please run the migration script first:")
        console.print("  python migrate_to_sqlite.py")
        return

    # Execute command
    command = args.command

    if command == "add":
        parsed = parse_activity(" ".join(args.activity))
        activity_type = parsed["type"]
        description = parsed["description"]

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO activities (type, description, completed) VALUES (?, ?, ?)",
                (parsed["type"], parsed["description"], 0),
            )
        console.print(f"Added activity: \\[{activity_type}] {description}")

    elif command == "remove":
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM activities ORDER BY id")
            activities = cursor.fetchall()

            if args.index < 0 or args.index >= len(activities):
                console.print("Invalid index.")
                return

            activity_id = activities[args.index]["id"]
            cursor.execute("DELETE FROM activities WHERE id = ?", (activity_id,))
    elif command == "activities":
        console.print("")

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM activities ORDER BY id")
            activities = [dict(row) for row in cursor.fetchall()]

        grouped_data = {}
        for ei, activity in enumerate(activities):
            if activity["type"] not in grouped_data:
                grouped_data[activity["type"]] = []
            grouped_data[activity["type"]].append((ei, activity))

        panels = []

        # Add general first if it exists
        if "general" in grouped_data:
            panels.append(create_panel(grouped_data["general"], "general", width=40))

        # Add all other types except 'to-do'
        for act_type in sorted(grouped_data.keys()):
            if act_type in ("general", "todo"):
                continue
            panels.append(create_panel(grouped_data[act_type], act_type, width=40))

        if panels:
            console.print(
                Columns(panels, equal=True, expand=True, column_first=True, padding=1)
            )
        else:
            console.print("No activities found.")
        console.print()

    elif command == "todo":
        console.print("")

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM activities ORDER BY id")
            activities = [dict(row) for row in cursor.fetchall()]

        grouped_data = {}
        for ei, activity in enumerate(activities):
            if activity["type"] not in grouped_data:
                grouped_data[activity["type"]] = []
            grouped_data[activity["type"]].append((ei, activity))

        if "todo" in grouped_data:
            panel = create_panel(grouped_data["todo"], "todo")
            console.print(panel)
        else:
            console.print("No todo items found.")
        console.print()

    elif args.command == "complete":
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM activities ORDER BY id")
            activities = cursor.fetchall()

            if args.index < 0 or args.index >= len(activities):
                console.print("Invalid index.")
                return

            activity_id = activities[args.index]["id"]
            cursor.execute(
                "UPDATE activities SET completed = ? WHERE id = ?", (1, activity_id)
            )
        console.print(f"Marked activity {args.index} as complete.")
    elif args.command == "incomplete":
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM activities ORDER BY id")
            activities = cursor.fetchall()

            if args.index < 0 or args.index >= len(activities):
                console.print("Invalid index.")
                return

            activity_id = activities[args.index]["id"]
            cursor.execute(
                "UPDATE activities SET completed = ? WHERE id = ?", (0, activity_id)
            )
        console.print(f"Marked activity {args.index} as incomplete.")
    else:
        # Default imbored command - pick a random activity
        filter_type = args.type

        with get_db_connection() as conn:
            cursor = conn.cursor()
            if args.type:
                cursor.execute(
                    "SELECT * FROM activities WHERE type = ? ORDER BY RANDOM() LIMIT 1",
                    (args.type,),
                )
            else:
                cursor.execute("SELECT * FROM activities ORDER BY RANDOM() LIMIT 1")

            choice = cursor.fetchone()

        if choice:
            choice = dict(choice)
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
            filter_msg = f" of type '{filter_type}'" if filter_type else ""
            console.print(
                f"No activities found{filter_msg}. Add some with 'imbored add \"[type] activity\"'"
            )
