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

    return {"type": activity_type, "description": activity_description}


def main():
    # Load arguments
    parser = argparse.ArgumentParser(description="im-bored CLI")
    parser.add_argument(
        "--type", type=str, help="Filter activities by type (for default command)"
    )

    subparser = parser.add_subparsers(dest="command")

    add_parser = subparser.add_parser("add", help="Add a new activity")
    add_parser.add_argument("activity", type=str, help="The activity to add")

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
        data = {"general": []}

    # Migrate old data structure if needed
    if "activities" in data:
        data["general"] = data.pop("activities")

    # Execute command
    command = args.command

    if command == "add":
        parsed = parse_activity(args.activity)
        activity_type = parsed["type"]
        description = parsed["description"]

        if activity_type not in data:
            data[activity_type] = []
        data[activity_type].append(description)
        console.print(f"Added activity to '{activity_type}': {description}")

    elif command == "remove":
        # Flatten all activities with their types for indexing
        all_activities = []
        for act_type in data.keys():
            for activity in data[act_type]:
                all_activities.append((act_type, activity))

        if 0 <= args.index < len(all_activities):
            act_type, activity = all_activities[args.index]
            data[act_type].remove(activity)
            console.print(f"Removed: [{act_type}] {activity}")

            if len(data[act_type]) == 0:
                del data[act_type]
        else:
            console.print(f"Error: Index {args.index} out of range")

    elif command == "list":
        filter_type = args.type
        console.print("")
        index = 0

        for act_type in data.keys():
            table = Table(title=act_type, title_justify="left")
            table.add_column("Index", justify="right")
            table.add_column("Activity", justify="left")

            if data[act_type]:
                for activity in data[act_type]:
                    table.add_row(str(index), activity)
                    index += 1

            console.print(table)
            console.print()

    else:
        # Default imbored command - pick a random activity
        filter_type = args.type
        all_activities = []

        for act_type in data.keys():
            all_activities.extend(data[act_type])

        if all_activities:
            console.print(f"[{act_type}]", random.choice(all_activities))
        else:
            filter_msg = f" of type '{filter_type}'" if filter_type else ""
            console.print(
                f"No activities found{filter_msg}. Add some with 'imbored add \"[type] activity\"'"
            )

    # Save data
    os.makedirs(os.path.dirname(JSON_PATH), exist_ok=True)
    with open(JSON_PATH, "w") as f:
        json.dump(data, f, indent=4)
