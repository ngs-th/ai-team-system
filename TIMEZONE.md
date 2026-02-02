# Timezone Configuration for AI Team Database

## Problem
SQLite's `CURRENT_TIMESTAMP` returns UTC time, but we need Asia/Bangkok (+7) time.

## Solution Used
Replace `CURRENT_TIMESTAMP` with `datetime('now', 'localtime')` in all SQL statements.

## Why Not Other Methods?

### ❌ PRAGMA timezone
- SQLite's `PRAGMA timezone` is READ-ONLY
- Cannot change timezone behavior for `CURRENT_TIMESTAMP`
- Only shows the current timezone setting

### ❌ Triggers
- `BEFORE INSERT` triggers cannot UPDATE the same row being inserted
- Complex and error-prone

### ❌ Schema DEFAULT
- SQLite doesn't allow `DEFAULT datetime('now', 'localtime')` in table definitions
- Only `CURRENT_TIMESTAMP` is allowed as default

## Current Implementation
All timestamp columns use `datetime('now', 'localtime')`:
- `created_at`
- `updated_at`
- `started_at`
- `completed_at`
- `last_heartbeat`

## Verified Working
```bash
cd /Users/ngs/clawd/projects/ai-team
python3 team_db.py task start T-XXXXXX-XXX
# Returns Bangkok time (UTC+7)
```
