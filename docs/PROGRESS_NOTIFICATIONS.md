# Agent Progress Notifications

**QA Engineer:** Quinn  
**Task ID:** T-20260202-022  
**Status:** ✅ Implemented

## Overview

This feature adds Telegram progress notifications for agents during task execution. Agents can report progress, milestones, errors, and completions without impacting performance.

## Acceptance Criteria

- ✅ **Send progress updates to Telegram** - Agents can report progress (0-100%)
- ✅ **Configurable notification levels** - Minimal, Normal, Verbose levels
- ✅ **Error and completion alerts** - Errors sent at all levels
- ✅ **Minimal performance impact** - Fire-and-forget notifications

## Notification Levels

| Level | Events Received | Use Case |
|-------|-----------------|----------|
| **minimal** | block, complete, error | Production - only critical events |
| **normal** | + assign, start, milestone, unblock | Standard monitoring |
| **verbose** | + progress, review, create, backlog | Detailed tracking |

## Event Types

| Event | Emoji | Level | Description |
|-------|-------|-------|-------------|
| **ERROR** | ❌ | all | Fatal or non-fatal errors |
| **BLOCK** | 🚫 | all | Task blocked with reason |
| **COMPLETE** | ✅ | all | Task completed |
| **MILESTONE** | 🏁 | normal+ | Milestone achievement |
| **PROGRESS** | 📊 | verbose | Progress percentage updates |

## Usage

### For Agents (Python API)

```python
from agent_progress import AgentProgressReporter

# Create reporter (auto-detects current task)
reporter = AgentProgressReporter(agent_id='dev')

# Report progress
reporter.progress(50, "Halfway done")

# Report milestone
reporter.milestone("Database schema created")

# Report error
reporter.error("API timeout", fatal=False)

# Report completion
reporter.complete()

reporter.close()
```

### Quick Methods (One-off)

```python
from agent_progress import quick_progress, quick_milestone, quick_error

# Quick progress report
quick_progress('dev', 75, 'T-20260202-001')

# Quick milestone
quick_milestone('dev', 'Tests passing', 'T-20260202-001')

# Quick error
quick_error('dev', 'Build failed', fatal=True)
```

### CLI Usage

```bash
# Report progress
python3 agent_progress.py progress dev 50 --task T-20260202-001

# Report milestone
python3 agent_progress.py milestone dev "Database created" --task T-20260202-001

# Report error
python3 agent_progress.py error dev "Build failed" --task T-20260202-001 --fatal

# Report completion
python3 agent_progress.py complete dev --task T-20260202-001
```

## Integration with team_db.py

Progress updates via `team_db.py` automatically trigger notifications:

```bash
# Update progress - sends notification at milestones (0, 25, 50, 75, 100) or significant jumps
python3 team_db.py task progress T-20260202-001 50
```

## Configuration

### Set Agent Notification Level

```python
from notifications import NotificationManager

with NotificationManager() as nm:
    nm.set_agent_level('dev', 'verbose')  # minimal, normal, verbose
```

### Set Per-Entity Settings

```python
from notifications import NotificationManager, NotificationLevel

with NotificationManager() as nm:
    nm.set_settings(
        entity_type='agent',
        entity_id='dev',
        level='verbose'
    )
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Agent During Task                        │
├─────────────────────────────────────────────────────────────┤
│  AgentProgressReporter                                       │
│  ├─ progress(50) → ProgressNotifier.report_progress()       │
│  ├─ milestone("Done") → ProgressNotifier.report_milestone() │
│  └─ error("Oops") → ProgressNotifier.report_error()         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    ProgressNotifier                          │
│  - Tracks last progress (prevents spam)                     │
│  - Checks notification level                                │
│  - Formats message with emoji                               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   NotificationManager                        │
│  ├─ LEVEL_EVENTS mapping                                    │
│  ├─ should_notify() - level check                           │
│  ├─ format_message() - message formatting                   │
│  └─ send_notification() → Telegram                          │
└─────────────────────────────────────────────────────────────┘
```

## Performance Considerations

1. **Connection Management**: Database connections are short-lived
2. **Spam Prevention**: ProgressNotifier tracks last progress, skips <5% changes
3. **Async by Design**: Subprocess calls are non-blocking (fire-and-forget)
4. **Level Filtering**: Checks level before formatting/sending

## Testing

```bash
# Run all notification tests
python3 test_notifications.py

# Expected: 26 tests OK
```

## Files Added/Modified

| File | Action | Description |
|------|--------|-------------|
| `notifications.py` | Modified | Added PROGRESS, ERROR, MILESTONE events; ProgressNotifier class |
| `agent_progress.py` | Added | High-level agent progress reporting API |
| `team_db.py` | Modified | Updated update_progress() to trigger notifications |
| `test_notifications.py` | Modified | Added progress notification tests |
