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
```

### Removing activities
```bash
# Basic remove (by ID)
imbored remove 1
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
imbored activities

# Show only specific categories/tags/durations
imbored activities --type read
imbored activities --tags cozy
imbored activities --duration 30min
```

### Generating an idea
```bash
# Return a random activity
imbored

# Return a random activity using category/tag/duration as a filter
imbored --type read
imbored --tags exercise
imbored --duration 30min
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
