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

    Format: [type] description #tag1 #tag2 --duration 15min --completable
    If no type is specified, defaults to 'general'
    Hashtags are extracted as tags
    --duration flag specifies duration
    --completable flag marks this as a one-off to-do activity
    """
    from im_bored.db import parse_tags_from_description

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
    }


def create_panel(data, title, width=None, show_completable=False):
    table = Table(
        show_header=True,
        show_edge=False,
        pad_edge=False,
        box=None,
        header_style="cyan",
        row_styles=["", "yellow"],
    )
    table.add_column("ID", justify="right", width=3)

    # Only show "Done" column when showing completable activities
    if show_completable:
        table.add_column("Done", justify="center", width=4)

    table.add_column("Description")

    for ei, entry in data:
        # Build description with tags and duration
        desc = entry["description"]

        # Add checkbox indicator for completable activities (when not showing the Done column)
        if not show_completable and entry.get("completable"):
            checkbox = "☐" if not entry["completed"] else "☑"
            desc = f"{checkbox} {desc}"

        # Add tags if present
        if entry.get("tags"):
            tag_str = " ".join(f"[dim]#{tag['name']}[/dim]" for tag in entry["tags"])
            desc = f"{desc} {tag_str}"

        # Add duration if present
        if entry.get("duration"):
            desc = f"{desc} [dim cyan]({entry['duration']})[/dim cyan]"

        if show_completable:
            done_mark = "✔" if entry["completed"] else " "
            table.add_row(str(ei), done_mark, desc)
        else:
            table.add_row(str(ei), desc)

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

    subparser.add_parser("activities", help="List all activities (excluding to-do)")

    subparser.add_parser("todo", help="Show the to-do list")

    # Tag management commands
    tag_parser = subparser.add_parser("tag", help="Manage tags")
    tag_subparser = tag_parser.add_subparsers(dest="tag_command")

    tag_subparser.add_parser("list", help="List all tags")

    tag_create_parser = tag_subparser.add_parser("create", help="Create a new tag")
    tag_create_parser.add_argument("name", type=str, help="Tag name")

    tag_delete_parser = tag_subparser.add_parser("delete", help="Delete a tag")
    tag_delete_parser.add_argument("name", type=str, help="Tag name")

    # Vibe management commands
    vibe_parser = subparser.add_parser("vibe", help="Manage vibes")
    vibe_subparser = vibe_parser.add_subparsers(dest="vibe_command")

    vibe_subparser.add_parser("list", help="List all vibes")

    vibe_create_parser = vibe_subparser.add_parser("create", help="Create a new vibe")
    vibe_create_parser.add_argument("name", type=str, help="Vibe name")

    vibe_edit_parser = vibe_subparser.add_parser("edit", help="Edit a vibe's tags")
    vibe_edit_parser.add_argument("name", type=str, help="Vibe name")

    vibe_delete_parser = vibe_subparser.add_parser("delete", help="Delete a vibe")
    vibe_delete_parser.add_argument("name", type=str, help="Vibe name")

    # Add --vibe flag to default command
    parser.add_argument(
        "--vibe", type=str, help="Filter activities by vibe (for default command)"
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

        parsed = parse_activity(" ".join(args.activity))
        activity_type = parsed["type"]
        description = parsed["description"]
        tags = parsed["tags"]
        duration = parsed["duration"]
        completable = parsed["completable"]

        # Add activity with tags
        activity_id = add_activity_with_tags(activity_type, description, tags, duration, completable)

        # Build output message
        msg = f"Added activity: \\[{activity_type}] {description}"
        if tags:
            tag_str = " ".join(f"#{tag}" for tag in tags)
            msg += f" {tag_str}"
        if duration:
            msg += f" ({duration})"
        if completable:
            msg += " [completable]"

        console.print(msg)

    elif command == "remove":
        from im_bored.db import delete_activity, get_activity_by_id

        activity = get_activity_by_id(args.index)
        if not activity:
            console.print(f"✗ Activity ID {args.index} not found")
            return

        delete_activity(args.index)
        console.print(f"✓ Removed activity {args.index}: {activity['description']}")
    elif command == "activities":
        from im_bored.db import get_tags_for_activity

        console.print("")

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM activities ORDER BY id")
            activities = [dict(row) for row in cursor.fetchall()]

        # Fetch tags for each activity
        for activity in activities:
            activity["tags"] = get_tags_for_activity(activity["id"])

        grouped_data = {}
        for activity in activities:
            if activity["type"] not in grouped_data:
                grouped_data[activity["type"]] = []
            # Use actual database ID instead of enumeration index
            grouped_data[activity["type"]].append((activity["id"], activity))

        panels = []

        # Add all types in sorted order (including general)
        for act_type in sorted(grouped_data.keys()):
            panels.append(create_panel(grouped_data[act_type], act_type, width=40))

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
            # Only get incomplete completable activities
            cursor.execute("SELECT * FROM activities WHERE completed = 0 AND completable = 1 ORDER BY id")
            activities = [dict(row) for row in cursor.fetchall()]

        # Fetch tags for each activity
        for activity in activities:
            activity["tags"] = get_tags_for_activity(activity["id"])

        grouped_data = {}
        for activity in activities:
            if activity["type"] not in grouped_data:
                grouped_data[activity["type"]] = []
            # Use actual database ID instead of enumeration index
            grouped_data[activity["type"]].append((activity["id"], activity))

        panels = []

        # Add all types in sorted order (including general)
        for act_type in sorted(grouped_data.keys()):
            panels.append(create_panel(grouped_data[act_type], act_type, width=40, show_completable=True))

        if panels:
            console.print(
                Columns(panels, equal=True, expand=True, column_first=True, padding=1)
            )
        else:
            console.print("No incomplete to-do items found.")
        console.print()

    elif command == "tag":
        from im_bored.db import get_all_tags, create_tag, get_tag_by_name, delete_tag

        tag_command = args.tag_command

        if tag_command == "list":
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

        elif tag_command == "create":
            tag_id = create_tag(args.name)
            console.print(f"✓ Created tag: #{args.name} (ID: {tag_id})")

        elif tag_command == "delete":
            tag = get_tag_by_name(args.name)
            if tag:
                if delete_tag(tag["id"]):
                    console.print(f"✓ Deleted tag: #{args.name}")
                else:
                    console.print(f"✗ Failed to delete tag: #{args.name}")
            else:
                console.print(f"✗ Tag not found: #{args.name}")

    elif command == "vibe":
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

        vibe_command = args.vibe_command

        if vibe_command == "list":
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

        elif vibe_command == "create":
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

        elif vibe_command == "edit":
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

        elif vibe_command == "delete":
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
    else:
        # Default imbored command - pick a random activity with filtering
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
