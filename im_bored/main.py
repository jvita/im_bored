import argparse
import json
import os
import random
import re

JSON_PATH = "data/data.json"


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

    add_parser = subparser.add_parser("todo", help="Add a new TO-DO item")
    add_parser.add_argument("activity", type=str, help="The item to add")

    remove_parser = subparser.add_parser("remove", help="Remove an activity")
    remove_parser.add_argument(
        "index", type=int, help="The index of the activity to remove"
    )

    list_parser = subparser.add_parser("list", help="List all activities and todos")
    list_parser.add_argument("--type", type=str, help="Filter activities by type")

    args = parser.parse_args()

    # Load data
    if os.path.exists(JSON_PATH):
        with open(JSON_PATH) as f:
            data = json.load(f)
    else:
        data = {"todo": [], "general": []}

    # Migrate old data structure if needed
    if "activities" in data:
        data["general"] = data.pop("activities")

    # Execute command
    command = args.command

    if command == "add" or command == "todo":
        parsed = parse_activity(args.activity)
        activity_type = "todo" if command == "todo" else parsed["type"]
        description = parsed["description"]

        if activity_type not in data:
            data[activity_type] = []
        data[activity_type].append(description)
        print(f"Added activity to '{activity_type}': {description}")

    elif command == "remove":
        # Flatten all activities with their types for indexing
        all_activities = []
        for act_type in sorted(data.keys()):
            for activity in data[act_type]:
                all_activities.append((act_type, activity))

        if 0 <= args.index < len(all_activities):
            act_type, activity = all_activities[args.index]
            data[act_type].remove(activity)
            print(f"Removed: [{act_type}] {activity}")
        else:
            print(f"Error: Index {args.index} out of range")

    elif command == "list":
        filter_type = args.type
        print("Activities:")
        index = 0

        for act_type in sorted(data.keys()):
            if data[act_type]:
                print(f"\n  [{act_type}]")
                for activity in data[act_type]:
                    print(f"    {index}. {activity}")
                    index += 1

    else:
        # Default imbored command - pick a random activity
        filter_type = args.type
        all_activities = []

        for act_type in data.keys():
            all_activities.extend(data[act_type])

        if all_activities:
            print(f"[{act_type}]", random.choice(all_activities))
        else:
            filter_msg = f" of type '{filter_type}'" if filter_type else ""
            print(
                f"No activities found{filter_msg}. Add some with 'imbored add \"[type] activity\"'"
            )

    # Save data
    os.makedirs(os.path.dirname(JSON_PATH), exist_ok=True)
    with open(JSON_PATH, "w") as f:
        json.dump(data, f, indent=4)
