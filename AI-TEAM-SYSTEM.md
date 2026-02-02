# 🤖 AI Team System Documentation

System for managing AI agents and tasks using SQLite database.

## Overview

The AI Team System coordinates multiple AI agents working on projects. It tracks:
- Agent status and heartbeats
- Task assignments and progress
- Project status and deadlines
- Historical actions via task history
- **Task requirements: prerequisites, acceptance criteria, and goals**

## Task Structure (New Fields)

Tasks now include three new fields for better project management:

### 1. Goal (TEXT)
Clear description of expected outcome.

**Example:**
```
Implement user login with JWT tokens, supporting email/password and OAuth
```

### 2. Prerequisites (TEXT - Markdown Checklist)
Items needed before starting work.

**Example:**
```markdown
- [ ] API token received
- [ ] Database schema approved
- [ ] Design mockups ready
```

### 3. Acceptance Criteria (TEXT - Markdown Checklist)
Conditions for task completion (Definition of Done).

**Example:**
```markdown
- [ ] Feature works on staging
- [ ] Unit tests pass (>80% coverage)
- [ ] Code reviewed by senior dev
- [ ] Documentation updated
```

### Benefits
- **No more "oops, forgot we need API key"** - Prerequisites checked before starting
- **Clear definition of done** - Everyone knows when a task is truly complete
- **Better task handoffs** - New agents can pick up tasks with full context

## Quick Start

### Show Current Status
```bash
# Check all agents
~/clawd/projects/ai-team/update-heartbeat.sh status

# Check system overview
sqlite3 ~/clawd/projects/ai-team/team.db "SELECT * FROM v_dashboard_stats;"
```

### Create a Task with Requirements
```bash
# Create a basic task
python3 ~/clawd/projects/ai-team/team_db.py task create "Fix login bug" \
  --project EPIC-001 --assign dev --priority high

# Create a task with all new fields
python3 ~/clawd/projects/ai-team/team_db.py task create "Implement OAuth" \
  --project EPIC-001 \
  --assign dev \
  --priority critical \
  --goal "Enable users to login with Google and GitHub OAuth" \
  --prerequisites $'- [ ] OAuth app credentials\n- [ ] SSL certificate\n- [ ] Privacy policy page' \
  --acceptance $'- [ ] Login works with Google\n- [ ] Login works with GitHub\n- [ ] Error handling tested\n- [ ] Docs updated'

# Update requirements on existing task
python3 ~/clawd/projects/ai-team/team_db.py task requirements T-20260202-001 \
  --goal "Updated goal description" \
  --acceptance $'- [ ] Criterion 1\n- [ ] Criterion 2'

# Show task requirements
python3 ~/clawd/projects/ai-team/team_db.py task show-requirements T-20260202-001
```

### Start Working on a Task
```bash
# When an agent starts a task, update heartbeat
~/clawd/projects/ai-team/update-heartbeat.sh start-task <agent_id> <task_id>

# Example:
~/clawd/projects/ai-team/update-heartbeat.sh start-task dev T-20260202-001
```

### During Long Tasks (10+ minutes)
```bash
# Start periodic heartbeat updates every 10 minutes
~/clawd/projects/ai-team/update-heartbeat.sh periodic-start <agent_id>

# Stop when done
~/clawd/projects/ai-team/update-heartbeat.sh periodic-stop <agent_id>
```

### Complete a Task
```bash
# Mark task as complete and update agent
~/clawd/projects/ai-team/update-heartbeat.sh complete <agent_id> <task_id>
```

### Move Task to Backlog
```bash
# When task needs external resources/requirements
python3 ~/clawd/projects/ai-team/team_db.py task backlog <task_id> --reason "Missing LINE API token"

# Or via database directly
sqlite3 ~/clawd/projects/ai-team/team.db "UPDATE tasks SET status='backlog', blocked_reason='Waiting for API token' WHERE id='TASK-001';"
```

## Directory Structure

```
~/clawd/projects/ai-team/
├── team.db                      # Main SQLite database
├── update-heartbeat.sh          # Heartbeat management script
└── AI-TEAM-SYSTEM.md           # This documentation

~/clawd/monitoring/scripts/
└── ai-team-monitor.sh          # Monitoring and reporting script
```

## Database Schema

### Tables

| Table | Purpose |
|-------|---------|
| `agents` | AI agent profiles and status |
| `tasks` | Task definitions and progress |
| `projects` | Project containers |
| `task_history` | Audit log of all task changes |
| `task_dependencies` | Task dependency relationships |

### Views

| View | Purpose |
|------|---------|
| `v_agent_status` | Agent heartbeat status with silence detection |
| `v_agent_workload` | Task counts per agent |
| `v_task_summary` | Task overview with urgency |
| `v_task_overview` | Comprehensive task view with due dates |
| `v_project_status` | Project progress summary |
| `v_dashboard_stats` | System-wide statistics |
| `v_daily_summary` | Daily aggregated metrics |
| `v_weekly_report` | Weekly aggregated metrics |

## Monitoring

### Check Heartbeats (Silent Agents >30 min)
```bash
~/clawd/monitoring/scripts/ai-team-monitor.sh heartbeat
```

### Check Deadlines
```bash
~/clawd/monitoring/scripts/ai-team-monitor.sh deadlines
```

### Check Blocked Tasks
```bash
~/clawd/monitoring/scripts/ai-team-monitor.sh blocked
```

### Generate Reports
```bash
# Hourly report
~/clawd/monitoring/scripts/ai-team-monitor.sh hourly

# Daily report
~/clawd/monitoring/scripts/ai-team-monitor.sh daily

# All checks
~/clawd/monitoring/scripts/ai-team-monitor.sh all
```

### Telegram Output (Plain Text)
```bash
~/clawd/monitoring/scripts/ai-team-monitor.sh telegram-hourly
~/clawd/monitoring/scripts/ai-team-monitor.sh telegram-daily
```

## Agent Workflow

```
1. AGENT STARTS TASK
   └─→ update-heartbeat.sh start-task <agent> <task>
       └─→ Sets status='active', updates heartbeat

2. DURING TASK (long running)
   ├─→ update-heartbeat.sh periodic-start <agent>  (every 10 min)
   └─→ OR: update-heartbeat.sh update <agent>      (manual)

3. TASK COMPLETE
   └─→ update-heartbeat.sh complete <agent> <task>
       └─→ Sets status='done', progress=100, heartbeat

4. AGENT IDLE
   └─→ Automatically set when no tasks in progress
```

## Useful Queries

### Find Silent Agents (>30 min)
```sql
SELECT id, name, minutes_since_heartbeat 
FROM v_agent_status 
WHERE is_silent = 1;
```

### Overdue Tasks
```sql
SELECT id, title, assignee, days_until_due 
FROM v_task_overview 
WHERE is_overdue = 1;
```

### Tasks Due Today
```sql
SELECT id, title, assignee 
FROM v_task_overview 
WHERE due_status = 'due_today';
```

### Agent Workload
```sql
SELECT * FROM v_agent_workload;
```

### Project Progress
```sql
SELECT * FROM v_project_status;
```

## Cron Setup

### Hourly Monitoring (add to crontab)
```bash
0 * * * * /Users/ngs/clawd/monitoring/scripts/ai-team-monitor.sh hourly >> /Users/ngs/clawd/monitoring/logs/hourly.log 2>&1
```

### Daily Report at 6 PM
```bash
0 18 * * * /Users/ngs/clawd/monitoring/scripts/ai-team-monitor.sh daily >> /Users/ngs/clawd/monitoring/logs/daily.log 2>&1
```

## Well-Defined Task Examples

### Good Task Example
```
Title: Implement Line webhook handler
Goal: Create webhook endpoint to receive and process Line bot messages

Prerequisites:
- [x] Line channel secret received
- [x] Line channel access token received
- [ ] Webhook URL configured in Line Console
- [ ] SSL certificate installed

Acceptance Criteria:
- [ ] Webhook receives message events from Line
- [ ] Message content parsed correctly
- [ ] Reply message sent within 3 seconds
- [ ] Error handling for invalid signatures
- [ ] Unit tests >80% coverage
- [ ] Webhook URL documented
```

### Poor Task Example (Avoid This)
```
Title: Fix Line bot
Description: It's not working
```

### Task Creation Checklist
Before creating a task, ensure:
- [ ] Goal is specific and measurable
- [ ] All prerequisites identified
- [ ] Acceptance criteria cover happy path AND edge cases
- [ ] Task fits in 1-3 days of work (break down if larger)
- [ ] Dependencies on other tasks noted

## Troubleshooting

### Check Database Connection
```bash
~/clawd/monitoring/scripts/ai-team-monitor.sh db-check
```

### Manual Heartbeat Update
```bash
sqlite3 ~/clawd/projects/ai-team/team.db \
  "UPDATE agents SET last_heartbeat = datetime('now') WHERE id = 'dev';"
```

### View Recent Task History
```sql
SELECT * FROM task_history 
ORDER BY timestamp DESC 
LIMIT 20;
```

## Task Status Values

| Status | Meaning | When to Use |
|--------|---------|-------------|
| `backlog` | Waiting for requirements/resources | Task is defined but cannot start due to missing dependencies, API tokens, or unclear requirements |
| `todo` | Ready to work, not started | Task has clear requirements and all dependencies are available |
| `in_progress` | Currently working | Agent is actively working on the task |
| `review` | Pending review | Task completed, waiting for review/approval |
| `done` | Completed | Task finished and approved |
| `blocked` | Blocked by issue during work | Task was in progress but hit an unexpected blocker (agent offline, fix loop exceeded) |
| `cancelled` | Cancelled | Task no longer needed |

### Backlog vs Todo

**Use `backlog` when:**
- Missing external dependencies (API tokens, third-party approvals)
- Waiting for requirements clarification from stakeholders
- Resources not yet available (hardware, accounts, access)
- Task is defined but prerequisites are not met

**Use `todo` when:**
- All requirements are clear and documented
- All dependencies are available
- Agent can start immediately when assigned

### Blocked vs Backlog Workflow

```
New Task
    ↓
[Requirements clear?] ──No──→ backlog
    │ Yes
    ↓
  todo
    ↓
Assign to Agent
    ↓
in_progress
    ↓
[Issue encountered?] ──Yes──→ blocked
    │ No
    ↓
  review → done
```

**From blocked:**
- If issue resolved → `unblock` → back to `in_progress`
- If requires external resources → `backlog` (waiting for requirements)

**From backlog:**
- When requirements met → `todo` (ready to assign)

## Agent Status Values

| Status | Meaning |
|--------|---------|
| `idle` | Available for tasks |
| `active` | Working on task |
| `blocked` | Unable to proceed |
| `offline` | Not responding |
