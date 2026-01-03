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

### ✅ Completable To-Dos
Mark activities as completable one-off tasks that disappear when logged:
```bash
# Add a completable to-do
imbored add "[chores] Call dentist --completable"

# Log it when done - it disappears from your to-do list
imbored log 15

# Repeatable activities stay available even after logging
imbored add "[exercise] Go for a run"
imbored log 22  # Logged, but still available for next time
```

### 📊 Optional Tracking (Stress-Free)
Log what you've completed *only if you want to*. No prompts, no pressure:
```bash
# Did something? Log it!
imbored log 22

# See what you've accomplished
imbored stats
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
# Repeatable activity (default)
imbored add "[exercise] Go for a run"

# One-off completable to-do
imbored add "[chores] Schedule dentist --completable"

# With context tags
imbored add "[exercise] Morning yoga #indoor #calm #solo"

# With duration
imbored add "[reading] Read current book --duration 1h"

# Everything together
imbored add "[chores] Buy groceries #quick --duration 30min --completable"
```

### Managing Your Activity List
```bash
# View all activities (grouped by type)
imbored activities

# View just incomplete to-dos
imbored todo

# Mark a completable activity as done (use 'complete' or 'log')
imbored complete 15
imbored log 15  # Same effect for completable activities

# Mark as incomplete again (brings it back)
imbored incomplete 15

# Remove an activity permanently
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
- **Type**: Primary category (e.g., `exercise`, `chores`, `reading`, `hobbies`)
- **Description**: What to do
- **Tags** (optional): Context attributes like `#indoor`, `#solo`, `#quick`
- **Duration** (optional): `5min`, `15min`, `30min`, `1h`, `1h+`
- **Completable** (optional): Whether it's a one-off task that should disappear when done

**Activity Behavior:**
- **Completable** (`--completable` flag) - One-off tasks that hide when logged/completed
- **Repeatable** (default) - Activities that remain available even after logging

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

# Add --completable flag for one-off to-dos
imbored add "[chores] Call dentist --completable"
imbored add "[work] Submit expense report --completable"

# With tags (automatically creates new tags)
imbored add "[exercise] Run in park #outdoor #active"

# With duration
imbored add "[reading] Read fiction --duration 1h"

# Everything together
imbored add "[chores] Grocery shopping #quick --duration 30min --completable"
```

#### Viewing Activities
```bash
# See all activities grouped by type
imbored activities

# See only incomplete completable to-dos (with checkboxes)
imbored todo

# Each activity shows its ID, description, tags, and duration
```

#### Completing & Updating Activities
```bash
# Mark completable activity as done (hides it from to-do list)
imbored complete <id>
imbored log <id>  # Same effect for completable activities

# Mark as incomplete (brings it back to to-do list)
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

**Common tags:** `indoor`, `outdoor`, `solo`, `social`, `quick`, `focus`, `cozy`, `active`, `creative`, `learning`, `fun`

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
imbored stats
imbored stats --days 7     # Last 7 days

# Reset statistics
imbored stats --reset
```

**Logging Behavior:**
- **Completable activities**: Logging marks them complete and hides them from to-do list
- **Repeatable activities**: Logging tracks completion but keeps the activity available

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

### Daily To-Dos
```bash
# Add some completable to-dos
imbored add "[chores] Email tax documents #quick --completable"
imbored add "[chores] Schedule dentist appointment #quick --completable"
imbored add "[shopping] Research hiking boots --completable"

# View to-do list (shows only incomplete completable items)
imbored todo

# Complete one (it disappears from the list)
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
# Add social activities (repeatable, not completable)
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
- **Chores**: errands, admin tasks, maintenance (often with `--completable`)
- **Creative**: writing, art, music

### Completable vs Repeatable
- **Use `--completable` for**: One-time tasks, errands, specific to-dos, things that shouldn't reappear after completion
- **Don't use `--completable` for**: Regular activities you do repeatedly like exercise, hobbies, social activities

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
