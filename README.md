# I'm Bored

You know best what you like to do. But sometimes you forget, or could use a little additional inspiration. This is a tool to help you decide what to do when you're bored. Overcome decision fatigue with smart filtering by mood, context, time available, and more.

## Core functionality

### Adding activities
```bash
# Basic add
imbored add "Read a book"

# Categorize (defaults to 'general')
imbored add "[read] Read a book"

# Add tags for filtering later (MUST use quotations because # breaks bash parsing)
imbored add "[read] Read a book #cozy #indoors"

# Add a duration (allowed values are '5min', '15min', '30min', '1h', and '1h+')
imbored add "[read] Read a book --duration 30min"

# Make the activity a completable, one-off to-do item
imbored add "Buy groceries --completable"

# Give a completable item a due date (year-month-day)
imbored add "Buy groceries --due 2026-01-08"

# Make a completable item recurring (e.g., "3days", "2weeks", "1month")
imbored add "Buy groceries --recurring 7days"
```

### Removing activities
```bash
# Basic permanent removal (by ID)
imbored remove 1

# Archive (remove from display, but keep for future reference)
imbored archive 1
```

### Defining "vibes"
A "vibe" is tag-based grouping of multiple activities. For example, the "Rainy Sunday" vibe might include anything with the `#cozy` or `#indoor` tags. Vibes are useful when you want to generate a random activity to match a certain mood.

```bash
# Define a new vibe
imbored vibes create "Rainy Day"
>>> Vibe description (optional) (): A relaxing indoor activity

>>> Enter tag numbers (comma-separated) or tag names (comma-separated with #):
>>> Tags: #cozy, #indoor, #indoors, #calm

# See existing vibes
imbored vibes

# Generate an idea using a specified vibe
imbored --vibe "Rainy Day"
```

### Browsing activities
```bash
# Show everything
imbored

# Show only specific categories/tags/durations
imbored --type read
imbored --tags cozy
imbored --duration 30min

# Show archived
imbored --show-archived
```

### Generating an idea
```bash
# Return a random activity
imbored random

# Return a random activity using category/tag/duration as a filter
imbored random --type read
imbored random --tags exercise
imbored random --duration 30min
```

### Optional Tracking (Stress-Free)
```bash
# Record that you did an activity (uses activity ID)
imbored log 22

# See what you've accomplished
imbored stats
```

## Installation

```bash
uv pip install -e .
```

## Web Interface (Optional)

Access the app from your phone via Tailscale:

```bash
# On your server/computer
sudo tailscale up
uv run imbored-web

# On your phone
# Install Tailscale app
# Connect to server_ip:5000 (get IP from Tailscale dashboard)
```

See [Tailscale setup guide](https://tailscale.com/download) for details.

## MCP Integration

The `im_bored` codebase is designed to be easily wrapped with FastMCP for AI assistant integration. The core business logic has been extracted into a service layer (`im_bored/services.py`) that provides clean, type-hinted functions perfect for MCP tools.

### Architecture

```
im_bored/
├── db.py           # Database layer (SQLite operations)
├── parsing.py      # String parsing utilities
├── services.py     # Service layer - MCP-friendly business logic
└── main.py         # CLI presentation layer
```

### Available Services

The service layer (`im_bored.services`) provides ~25 functions organized into these categories:

- **Activity Management**: `add_activity()`, `list_activities()`, `get_activity_details()`, `remove_activity()`, `archive_activity()`, `unarchive_activity()`
- **Todo Management**: `list_todos()`, `complete_activity()`, `uncomplete_activity()`, `log_activity_completion()`
- **Random Selection**: `get_random_activity()`
- **Tag Management**: `list_tags()`, `create_tag()`, `delete_tag()`, `get_tag_details()`
- **Vibe Management**: `list_vibes()`, `create_vibe()`, `update_vibe()`, `delete_vibe()`, `get_vibe_details()`
- **Categories**: `list_categories()`
- **Analytics**: `get_stats()`, `reset_stats()`
- **System**: `ensure_database()`, `reset_recurring_activities()`

### Design Principles

- **Structured arguments**: Service functions take explicit parameters (not strings) for better type safety
- **Return types**: Void operations return `None`; queries return data; creation returns IDs
- **Error handling**: Raises exceptions (`ValueError`) for invalid input or not found errors
- **No side effects**: No CLI-specific logic (Rich formatting, prompts, etc.)

### Example: FastMCP Wrapper

```python
from fastmcp import FastMCP
from im_bored import services

mcp = FastMCP("im-bored")

@mcp.tool()
def add_activity(
    type: str,
    description: str,
    tags: list[str] | None = None,
    duration: str | None = None,
    completable: bool = False,
    recurrence_days: int | None = None,
    due_date: str | None = None
) -> int:
    """Add a new activity to the database.

    Args:
        type: Activity type (e.g., 'read', 'exercise', 'cook')
        description: Activity description
        tags: Optional list of tag names
        duration: Optional duration ('5min', '15min', '30min', '1h', '1h+')
        completable: Whether this is a completable todo item
        recurrence_days: Optional recurrence period in days
        due_date: Optional due date (ISO format: YYYY-MM-DD)

    Returns:
        Activity ID
    """
    return services.add_activity(type, description, tags, duration, completable, recurrence_days, due_date)

@mcp.tool()
def get_random_activity(
    types: list[str] | None = None,
    tags: list[str] | None = None,
    duration: str | None = None,
    vibe_name: str | None = None
) -> dict:
    """Get a random activity suggestion.

    Args:
        types: Optional list of activity types to filter by
        tags: Optional list of tags to filter by
        duration: Optional duration to filter by
        vibe_name: Optional vibe name to apply

    Returns:
        Activity dict with full details
    """
    filters = {}
    if types:
        filters['types'] = types
    if tags:
        filters['tags'] = tags
    if duration:
        filters['duration'] = duration
    return services.get_random_activity(filters, vibe_name)

@mcp.tool()
def list_todos() -> list[dict]:
    """Get all incomplete todo items."""
    return services.list_todos()

# ... wrap remaining service functions as needed ...
```

### Running an MCP Server

Once you've created your MCP wrapper, you can run it as a server:

```bash
# Install FastMCP if not already installed
uv pip install fastmcp

# Run your MCP server
python your_mcp_wrapper.py
```

Then configure your AI assistant (Claude Desktop, etc.) to connect to the MCP server. See the [FastMCP documentation](https://github.com/jlowin/fastmcp) for details on MCP server configuration.
