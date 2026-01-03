# I'm Bored

A CLI tool to help you decide what to do when you're bored. Overcome decision fatigue with smart filtering by mood, context, time available, and more.

## Key Features

### 🎯 Smart Activity Filtering
Filter activities by multiple dimensions simultaneously:
- **Duration** - "I only have 15 minutes"
- **Tags** - "Indoor, solo activities only"
- **Type** - "Something active, not reading"
- **Vibes** - Pre-saved mood filters

### 🌈 Vibes (Mood Filters)
Create named filter presets for your common moods:
```bash
# Create a "Rainy Sunday" vibe with indoor + cozy tags
imbored vibe create "Rainy Sunday"

# Later, just use it
imbored --vibe "Rainy Sunday"
```

### 🏷️ Flexible Tagging
Multi-dimensional categorization beyond simple types:
```bash
# Activities can have multiple attributes
imbored add "[exercise] Yoga #indoor #calm #solo --duration 30min"
```

### 📊 Optional Tracking (Stress-Free)
Log what you've completed *only if you want to*. No prompts, no pressure:
```bash
# Did something? Log it!
imbored log 22

# See what you've accomplished
imbored stats
```

### ✅ Auto-Completing Todos
Todo items automatically hide when you log them as complete:
```bash
imbored add "[todo] Call dentist"
imbored log 15  # Marks complete and removes from list
```

## Installation

```bash
uv pip install -e .
```

## Quick Examples

### Basic Usage
```bash
# Get a random activity
imbored

# I only have 15 minutes
imbored --duration 15min

# Something indoors
imbored --tags indoor

# Indoor exercise
imbored --type exercise --tags indoor
```

### Using Vibes
```bash
# Create a "Quick Win" vibe for short, easy tasks
imbored vibe create "Quick Win"
# Select tags: #quick, #solo

# Use it anytime you want quick wins
imbored --vibe "Quick Win"
```

### Adding Activities
```bash
# Simple activity
imbored add "[exercise] Go for a run"

# With context tags
imbored add "[exercise] Morning yoga #indoor #calm #solo"

# With duration
imbored add "[reading] Read current book --duration 1h"

# Full featured
imbored add "[hobby] Work on chess puzzles #indoor #focus #solo --duration 30min"
```

### Managing Your Activity List
```bash
# View all activities with their IDs
imbored activities

# View just todos
imbored todo

# Mark a todo complete (hides it)
imbored complete 15

# Remove an activity you don't want anymore
imbored remove 22
```

### Optional Tracking
```bash
# Log activities you complete
imbored log 22

# See your activity log
imbored stats

# See last week
imbored stats --days 7

# Start fresh
imbored stats --reset
```

## Core Concepts

### Activities
Each activity has:
- **Type**: Primary category (e.g., `exercise`, `chess`, `reading`, `todo`)
- **Description**: What to do
- **Tags** (optional): Context attributes like `#indoor`, `#solo`, `#quick`
- **Duration** (optional): `5min`, `15min`, `30min`, `1h`, `1h+`

**Types:**
- `todo` - One-off tasks (disappear when completed)
- Everything else - Repeatable activities

### Tags
Multi-dimensional attributes that describe *how* or *where* you do an activity:
- **Location**: `#indoor`, `#outdoor`
- **Social**: `#solo`, `#social`
- **Energy**: `#active`, `#calm`, `#cozy`
- **Time**: `#quick` (for short activities)
- **Context**: `#focus`, `#creative`, `#learning`

Activities can have multiple tags. When filtering, activities must match *all* selected tags.

### Vibes
Pre-configured filter combinations for common moods or contexts:

**Example Vibes:**
- "Rainy Sunday" → `#indoor` + `#cozy`
- "Quick Win" → `#quick` + `#solo`
- "Social Saturday" → `#social` + `#outdoor`
- "Deep Focus" → `#focus` + `#solo` + `#learning`

## Detailed Usage

### Activity Management

#### Adding Activities
```bash
# Basic syntax: [type] description
imbored add "[type] description"

# With tags (automatically creates new tags)
imbored add "[exercise] Run in park #outdoor #active"

# With duration
imbored add "[reading] Read fiction --duration 1h"

# Everything together
imbored add "[hobby] Paint watercolors #indoor #creative #calm --duration 2h"
```

#### Viewing Activities
```bash
# See all activities grouped by type
imbored activities

# See only todos
imbored todo

# Each activity shows its ID, description, tags, and duration
```

#### Updating Activities
```bash
# Mark as complete (hides todos)
imbored complete <id>

# Mark as incomplete (shows todos again)
imbored incomplete <id>

# Remove permanently
imbored remove <id>
```

### Tag Management

```bash
# List all tags
imbored tag list

# Create a tag
imbored tag create energetic

# Delete a tag (removes from all activities)
imbored tag delete energetic
```

**Default tags:** `indoor`, `outdoor`, `solo`, `social`, `quick`, `focus`, `cozy`, `active`, `creative`, `learning`, `maintenance`, `fun`

### Vibe Management

```bash
# Create a vibe
imbored vibe create "Productive Morning"
# Then select tags: 1,2,5 or #quick,#focus,#solo

# List all vibes
imbored vibe list

# Edit a vibe's tags
imbored vibe edit "Productive Morning"

# Delete a vibe
imbored vibe delete "Productive Morning"
```

### Filtering Activities

```bash
# Single filter
imbored --type exercise
imbored --duration 30min
imbored --tags indoor
imbored --vibe "Rainy Sunday"

# Combine filters (AND logic - must match all)
imbored --type exercise --duration 30min --tags outdoor,solo

# Vibe + duration
imbored --vibe "Quick Win" --duration 15min
```

**Filtering Logic:**
- Tags use AND logic: `--tags indoor,solo` means activities must have *both* tags
- All filters combine with AND: must match type *and* duration *and* tags

### Activity Tracking

Tracking is completely optional. Use it only if it helps you feel accomplished.

```bash
# Log a completed activity
imbored log <id>

# See your activity log
imbored stats              # Last 30 days
imbored stats --days 7     # Last 7 days

# Reset statistics
imbored stats --reset      # Clears all logged activities
```

**For Todos:** Logging a todo marks it complete and hides it from your list.

**For Regular Activities:** Logging tracks completion but keeps the activity available for future use.

## Real-World Examples

### Morning Routine
```bash
# Create a morning vibe
imbored vibe create "Morning Routine"
# Select: #quick, #solo

# Use it every morning
imbored --vibe "Morning Routine" --duration 15min
```

### Rainy Day
```bash
# Create rainy day vibe
imbored vibe create "Rainy Day"
# Select: #indoor, #cozy, #calm

# Find something cozy for a rainy afternoon
imbored --vibe "Rainy Day" --duration 1h
```

### Lunch Break
```bash
# Quick 15-minute activities
imbored --duration 15min --tags quick

# Or save as a vibe
imbored vibe create "Lunch Break"
# Select: #quick, #solo
imbored --vibe "Lunch Break"
```

### Weekend Projects
```bash
# Add a project activity
imbored add "[hobby] Work on chess opening repertoire #indoor #focus #learning --duration 2h"

# Filter for long, focused activities
imbored --duration 1h+ --tags focus,learning
```

### Daily Todos
```bash
# Add some todos
imbored add "[todo] Email tax documents #quick"
imbored add "[todo] Schedule dentist appointment #quick"
imbored add "[todo] Research hiking boots"

# View todo list
imbored todo

# Complete one (it disappears)
imbored log 42
```

### Exercise Decision
```bash
# Outdoor exercise that's quick
imbored --type exercise --tags outdoor --duration 30min

# Any active activity
imbored --tags active
```

### Social Activities
```bash
# Add social activities
imbored add "[general] Call a friend #social #indoor --duration 30min"
imbored add "[games] Play board games #social #indoor --duration 2h"

# Filter for social activities
imbored --tags social
```

### End of Week Tracking
```bash
# See what you accomplished this week
imbored stats --days 7

# Feel good about it!
```

## Advanced Tips

### Tag Strategy
- **Be consistent**: Use the same tags across similar activities
- **Start simple**: Don't over-tag. Add tags as you find you need them
- **Location tags**: `#indoor` / `#outdoor` are super useful for filtering
- **Energy tags**: `#active` / `#calm` / `#cozy` help match your mood
- **Time tags**: Use `#quick` for activities under 15 minutes

### Vibe Ideas
- "Morning Energy" → `#active`, `#solo`, `#quick`
- "Evening Calm" → `#indoor`, `#calm`, `#cozy`
- "Weekend Adventure" → `#outdoor`, `#active`, `#social`
- "Learning Time" → `#focus`, `#learning`, `#solo`
- "Productive Hour" → `#focus`, `#solo`, `#indoor`

### Activity Categories
Group activities into types that make sense for you:
- **Hobbies**: chess, guitar, painting, crafts
- **Exercise**: running, yoga, weightlifting
- **Learning**: reading, courses, practice
- **Social**: calls, games, hangouts
- **Maintenance**: todos, chores, errands
- **Creative**: writing, art, music

### Avoid Analysis Paralysis
The tool is designed to *reduce* decision fatigue, not create it:
- Don't overthink tags - you can always add more later
- Start with a few vibes for your most common moods
- Use `imbored` with no filters when truly indifferent
- Tracking is optional - don't stress about it

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

## Philosophy

This tool is designed to **reduce anxiety**, not create it:
- No forced prompts after suggestions
- Tracking is completely optional
- No guilt-inducing metrics
- Just helpful filtering to overcome decision paralysis

Use it however helps you. Ignore the features that don't.
