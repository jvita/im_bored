# I'm Bored

You know best what you like to do. But sometimes you forget, or could use a little additional inspiration. This is a tool to help you decide what to do when you're bored. Overcome decision fatigue with smart filtering by mood, context, time available, and more.

## Core functionality

### Adding activities
```bash
# Basic add
imbored add "Read a book"

# Categorize (defaults to 'general')
imbored add "[read] Read a book"

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

### Browsing activities
```bash
# Show everything
imbored

# Show only specific categories
imbored --type read

# Show archived
imbored --show-archived
```

### Generating an idea
```bash
# Return a random activity
imbored random

# Return a random activity using category as a filter
imbored random --type read
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
    completable: bool = False,
    recurrence_days: int | None = None,
    due_date: str | None = None
) -> int:
    """Add a new activity to the database.

    Args:
        type: Activity type (e.g., 'read', 'exercise', 'cook')
        description: Activity description
        completable: Whether this is a completable todo item
        recurrence_days: Optional recurrence period in days
        due_date: Optional due date (ISO format: YYYY-MM-DD)

    Returns:
        Activity ID
    """
    return services.add_activity(type, description, completable, recurrence_days, due_date)

@mcp.tool()
def get_random_activity(
    types: list[str] | None = None,
) -> dict:
    """Get a random activity suggestion.

    Args:
        types: Optional list of activity types to filter by

    Returns:
        Activity dict with full details
    """
    return services.get_random_activity(types=types)

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
