import argparse
import json
import os
import random
import re

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

JSON_PATH = "data/data.json"
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
        "completed": False,
    }


def create_panel(data, title, width=None):
    table = Table(
        show_header=True,
        show_edge=False,
        pad_edge=False,
        box=None,
        header_style="magenta",
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
        border_style="cyan",
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

    # Load data
    if os.path.exists(JSON_PATH):
        with open(JSON_PATH) as f:
            data = json.load(f)
    else:
        data = []

    # Execute command
    command = args.command

    if command == "add":
        parsed = parse_activity(" ".join(args.activity))
        activity_type = parsed["type"]
        description = parsed["description"]

        data.append(parsed)
        console.print(f"Added activity: \\[{activity_type}] {description}")

    elif command == "remove":
        if args.index < 0 or args.index >= len(data):
            console.print("Invalid index.")
            return
        del data[args.index]
    elif command == "activities":
        console.print("")

        grouped_data = {}
        for ei, entry in enumerate(data):
            if entry["type"] not in grouped_data:
                grouped_data[entry["type"]] = []
            grouped_data[entry["type"]].append((ei, entry))

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

        grouped_data = {}
        for ei, entry in enumerate(data):
            if entry["type"] not in grouped_data:
                grouped_data[entry["type"]] = []
            grouped_data[entry["type"]].append((ei, entry))

        if "todo" in grouped_data:
            panel = create_panel(grouped_data["todo"], "todo")
            console.print(panel)
        else:
            console.print("No todo items found.")
        console.print()

    elif args.command == "complete":
        if args.index < 0 or args.index >= len(data):
            console.print("Invalid index.")
            return
        data[args.index]["completed"] = True
        console.print(f"Marked activity {args.index} as complete.")
    elif args.command == "incomplete":
        if args.index < 0 or args.index >= len(data):
            console.print("Invalid index.")
            return
        data[args.index]["completed"] = False
        console.print(f"Marked activity {args.index} as incomplete.")
    else:
        # Default imbored command - pick a random activity
        filter_type = args.type
        if args.type:
            filtered_data = [entry for entry in data if entry["type"] == args.type]
        else:
            filtered_data = data

        if data:
            choice = random.choice(filtered_data)
            act_type = choice["type"]

            panel = Panel(
                f"\n({choice['type']})\n\n[bold]{choice['description']}[/bold]",
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

    # Save data
    os.makedirs(os.path.dirname(JSON_PATH), exist_ok=True)
    with open(JSON_PATH, "w") as f:
        json.dump(data, f, indent=4)
