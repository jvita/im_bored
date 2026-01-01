import argparse
import json
import os
import random
import re

from rich.console import Console
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


def main():
    # Load arguments
    parser = argparse.ArgumentParser(description="im-bored CLI")
    parser.add_argument(
        "--type", type=str, help="Filter activities by type (for default command)"
    )

    subparser = parser.add_subparsers(dest="command")

    add_parser = subparser.add_parser("add", help="Add a new activity")
    add_parser.add_argument("activity", type=str, help="The activity to add")

    complete_parser = subparser.add_parser(
        "complete", help="Mark an activity as complete"
    )
    complete_parser.add_argument(
        "index", type=int, help="The index of the activity to complete"
    )

    remove_parser = subparser.add_parser("remove", help="Remove an activity")
    remove_parser.add_argument(
        "index", type=int, help="The index of the activity to remove"
    )

    list_parser = subparser.add_parser("list", help="List all activities")
    list_parser.add_argument("--type", type=str, help="Filter activities by type")

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
        parsed = parse_activity(args.activity)
        activity_type = parsed["type"]
        description = parsed["description"]

        data.append(parsed)
        console.print(f"Added activity: \\[{activity_type}] {description}")

    elif command == "remove":
        if args.index < 0 or args.index >= len(data):
            console.print("Invalid index.")
            return
        del data[args.index]
    elif command == "list":
        console.print("")

        grouped_data = {}
        for ei, entry in enumerate(data):
            if entry["type"] not in grouped_data:
                grouped_data[entry["type"]] = []
            grouped_data[entry["type"]].append((ei, entry))

        if args.type is not None:
            table = Table(title=args.type, title_justify="left")
            table.add_column("ID", justify="right")
            table.add_column("Done", justify="center")
            table.add_column("Activity", justify="left")

            for ei, activity in grouped_data[args.type]:
                table.add_row(
                    str(ei),
                    "✔" if activity["completed"] else "",
                    activity["description"],
                )

            console.print(table)
            console.print()

        else:
            for act_type in grouped_data.keys():
                table = Table(title=act_type, title_justify="left")
                table.add_column("ID", justify="right")
                table.add_column("Done", justify="center")
                table.add_column("Activity", justify="left")

                if grouped_data[act_type]:
                    for ei, activity in grouped_data[act_type]:
                        table.add_row(
                            str(ei),
                            "✔" if activity["completed"] else "",
                            activity["description"],
                        )

                console.print(table)
                console.print()
    elif args.command == "complete":
        if args.index < 0 or args.index >= len(data):
            console.print("Invalid index.")
            return
        data[args.index]["completed"] = True
        console.print(f"Marked activity {args.index} as complete.")
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

            console.print()
            console.print(f"\\[{act_type}]", choice["description"])
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
