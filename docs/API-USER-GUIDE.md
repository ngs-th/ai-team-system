# 🤖 AI Team System - API Documentation & User Guide

**Version:** 3.5.0  
**Last Updated:** 2026-02-03  
**Documentation Owner:** Tom (Technical Writer)

---

## Table of Contents

1. [Quick Start](#1-quick-start)
2. [API Reference](#2-api-reference)
   - Task Management API
   - Agent Management API
   - Orchestrator API
   - Health Monitor API
   - Notification API
3. [User Guide](#3-user-guide)
   - For Project Managers
   - For Developers
   - For Agents
4. [Setup & Configuration](#4-setup--configuration)
5. [Troubleshooting](#5-troubleshooting)

---

## 1. Quick Start

### 1.1 Prerequisites

```bash
# Required
- Python 3.9+
- SQLite 3
- OpenClaw CLI installed
- Telegram bot configured (optional)

# Optional
- PHP (for dashboard)
- Cron (for automation)
```

### 1.2 First Commands

```bash
# Navigate to project
cd /Users/ngs/clawd/projects/ai-team

# Check system health
python3 health_monitor.py --status

# View dashboard
python3 team_db.py dashboard

# List all tasks
python3 team_db.py task list

# List all agents
python3 team_db.py agent list
```

---

## 2. API Reference

### 2.1 Task Management API

#### Create Task

```bash
python3 team_db.py task create "<title>" \
  --project <project_id> \
  --working-dir <absolute_path> \
  --desc "<description>" \
  --assign <agent_id> \
  --priority <critical|high|normal|low> \
  --due <YYYY-MM-DD> \
  --prerequisites "<markdown checklist>" \
  --acceptance "<markdown checklist>" \
  --expected-outcome "<description>"
```

**Example:**
```bash
python3 team_db.py task create "Implement User Auth" \
  --project PROJ-001 \
  --working-dir /Users/ngs/Herd/nurse-ai \
  --desc "Create JWT-based authentication system" \
  --assign dev \
  --priority high \
  --due 2026-02-10 \
  --prerequisites "- [ ] Database schema ready
- [ ] API design approved" \
  --acceptance "- [ ] Login endpoint working
- [ ] Token refresh implemented
- [ ] Tests passing" \
  --expected-outcome "Users can login and receive JWT tokens"
```

**Required Fields:**
| Field | Description |
|-------|-------------|
| `project` | Project ID (mandatory) |
| `working-dir` | Absolute path where agent must work |
| `expected-outcome` | Clear success definition |
| `prerequisites` | Dependencies as markdown checklist |
| `acceptance` | Verification criteria |

---

#### Task Status Transitions

```bash
# Start work
python3 team_db.py task start <task_id>

# Update progress
python3 team_db.py task progress <task_id> <0-100> --notes "What was done"

# Send to review (in_progress → review)
python3 team_db.py task review <task_id>

# Mark complete (goes to review first)
python3 team_db.py task done <task_id>

# Approve from review (review → done)
python3 team_db.py task approve <task_id> --reviewer <agent_id>
```

---

#### Block/Unblock Tasks

```bash
# Block task
python3 team_db.py task block <task_id> "<reason>"

# Unblock and resume
python3 team_db.py task unblock <task_id> --agent <agent_id>

# Move to backlog
python3 team_db.py task backlog <task_id> --reason "<reason>"
```

---

#### List Tasks

```bash
# All tasks
python3 team_db.py task list

# Filter by status
python3 team_db.py task list --status <backlog|todo|in_progress|review|done|blocked>

# Filter by agent
python3 team_db.py task list --agent <agent_id>
```

**Sample Output:**
```
📋 Tasks (15 total):

⬜ T-20260203-001 | Implement User Authentication...
   Status: todo | Assignee: Unassigned

🔄 T-20260203-002 | Create Database Schema...
   Status: in_progress | Assignee: dev
   Progress: 45%
```

---

#### Task Requirements Management

```bash
# View requirements
python3 team_db.py task show-requirements <task_id>

# Update requirements
python3 team_db.py task requirements <task_id> \
  --prerequisites "<new prerequisites>" \
  --acceptance "<new criteria>" \
  --goal "<new expected outcome>"
```

---

### 2.2 Agent Management API

#### List Agents

```bash
# All agents
python3 team_db.py agent list

# Filter by status
python3 team_db.py agent list --status <idle|active|blocked>
```

**Sample Output:**
```
🤖 Agents (9 total):

⚪ John (pm)
   Status: idle
   Tasks: 0 active, 12 completed

🟢 Amelia (dev)
   Status: active
   Tasks: 1 active, 25 completed
   Avg Progress: 67.5%
```

---

#### Update Agent Heartbeat

```bash
python3 team_db.py agent heartbeat <agent_id>
```

---

#### Agent Context Management

```bash
# View context
python3 team_db.py agent context show <agent_id>

# Update context
python3 team_db.py agent context update <agent_id> \
  --field <context|learnings|preferences> \
  --content "<new content>"

# Add learning
python3 team_db.py agent context learn <agent_id> "<learning entry>"
```

---

#### Agent Working Memory

```bash
# Show working memory
python3 team_db.py agent memory show <agent_id>

# Update working memory
python3 team_db.py agent memory update <agent_id> \
  --notes "<current working notes>" \
  --blockers "<current blockers>" \
  --next-steps "<planned next steps>" \
  --task <task_id>
```

---

#### Inter-Agent Communication

```bash
# Send message
python3 team_db.py agent comm send <from_agent> "<message>" \
  --to <to_agent> \
  --task <task_id> \
  --type <comment|mention|request|response>

# Check inbox
python3 team_db.py agent comm inbox <agent_id> [--unread]

# View task messages
python3 team_db.py agent comm task <task_id>
```

---

#### Notification Settings

```bash
# Set notification level
python3 team_db.py notify level <agent_id> <minimal|normal|verbose>

# Show settings
python3 team_db.py notify show [--agent <agent_id>]

# View notification log
python3 team_db.py notify log [--task <task_id>] [--limit 20]
```

**Notification Levels:**
| Level | Events |
|-------|--------|
| `minimal` | Block, Complete only |
| `normal` | Assign, Start, Block, Unblock, Complete |
| `verbose` | All events including Create, Review, Backlog |

---

### 2.3 Orchestrator API

#### Submit a Goal

```bash
python3 orchestrator.py goal <feature|bugfix|documentation|analysis|refactor> \
  "<title>" \
  --desc "<description>" \
  --outcome "<expected outcome>" \
  [--assignee <agent_id>]
```

**Example:**
```bash
python3 orchestrator.py goal feature \
  "Patient Census Dashboard" \
  --desc "Real-time dashboard showing patient count by ward" \
  --outcome "Nurses can view real-time patient counts in dashboard" \
  --assignee architect
```

**Returns:** Mission ID (e.g., `M-20260203-001`)

---

#### Mission Management

```bash
# List missions
python3 orchestrator.py list [--status <planning|executing|reviewing|completed|failed>]

# Show mission details
python3 orchestrator.py show <mission_id>

# Monitor execution
python3 orchestrator.py monitor
```

---

#### Auto-Assign

```bash
# Run auto-assign manually
python3 auto_assign.py --run

# Check status
python3 auto_assign.py --status
```

---

### 2.4 Health Monitor API

#### Run Health Check

```bash
# Run once
python3 health_monitor.py --check

# Show current status
python3 health_monitor.py --status

# Auto-resolve stuck tasks
python3 health_monitor.py --auto-resolve

# Resolve specific task
python3 health_monitor.py --resolve-task <task_id>
```

#### Health Status Output

```
🤖 AI TEAM HEALTH STATUS
============================================================

📊 Summary (as of 2026-02-03 14:30:00)
   ✅ Healthy:  7
   🟡 Stale:    1
   🔴 Offline:  0
   ⚪ Unknown:  1

⏱️ Stuck Tasks (>2h no update): 2

📋 Agent Details:
------------------------------------------------------------
Name                 Health     Status     Last Heartbeat
------------------------------------------------------------
John                 ✅ healthy  idle       5m ago
Amelia               ✅ healthy  active     2m ago
Winston              🟡 stale    idle       45m ago
...
```

---

### 2.5 Dashboard API

```bash
# View dashboard
python3 team_db.py dashboard

# Export dashboard
python3 team_db.py dashboard --export json
python3 team_db.py dashboard --export markdown
```

---

### 2.6 Reports API

```bash
# Generate daily report
python3 team_db.py report --daily
```

---

## 3. User Guide

### 3.1 For Project Managers

#### Daily Workflow

1. **Morning Check** (5 minutes)
   ```bash
   python3 team_db.py dashboard
   python3 health_monitor.py --status
   ```

2. **Review Blocked Tasks**
   ```bash
   python3 team_db.py task list --status blocked
   ```

3. **Check Agent Workload**
   ```bash
   python3 team_db.py agent list
   ```

#### Creating a New Project Goal

```bash
# Step 1: Submit goal to orchestrator
python3 orchestrator.py goal feature "New Feature Name" \
  --desc "Description of what needs to be built" \
  --outcome "Clear definition of success"

# Step 2: Review the breakdown (after a few minutes)
python3 orchestrator.py show M-20260203-XXX

# Step 3: Monitor progress
python3 orchestrator.py monitor
```

#### Managing Blocked Tasks

When a task is blocked:
1. Check the reason: `python3 team_db.py task list --status blocked`
2. Resolve the blocker
3. Unblock: `python3 team_db.py task unblock <task_id>`

---

### 3.2 For Developers

#### Starting a New Task

```bash
# 1. Check prerequisites
python3 team_db.py task show-requirements <task_id>

# 2. Start the task
python3 team_db.py task start <task_id>

# 3. Update progress regularly
python3 team_db.py task progress <task_id> 25 --notes "Completed initial setup"
```

#### Task Lifecycle

```
Created → Assigned → Started → [Progress Updates] → Review → Done
   ↓          ↓         ↓            ↓              ↓
Backlog   Reassign   Blocked    Update %       Approve
```

#### Best Practices

1. **Always update progress** at 25%, 50%, 75%, 100%
2. **Document blockers immediately** when they occur
3. **Update working memory** with notes and next steps
4. **Complete all acceptance criteria** before marking done

---

### 3.3 For Agents (Subagents)

When spawned as a subagent, you receive:

```
## Task Assignment

**Agent:** Your Name (Your Role)
**Task:** T-XXX - Task Title

### Your Context
[Your background/context]

### Task Details
- Description
- Priority
- Expected Outcome

### Prerequisites (Check before starting)
- [ ] Item 1
- [ ] Item 2

### Acceptance Criteria (Must complete all)
- [ ] Criteria 1
- [ ] Criteria 2

### Instructions
1. Review prerequisites
2. Start task: python3 team_db.py task start <task_id>
3. Work on the task
4. Update progress regularly
5. When done: python3 team_db.py task done <task_id>
```

**Your Actions:**
1. Verify prerequisites are met
2. Run: `python3 team_db.py task start <task_id>`
3. Do the work
4. Update progress: `python3 team_db.py task progress <task_id> <percent> --notes "..."`
5. Complete: `python3 team_db.py task done <task_id>`

---

## 4. Setup & Configuration

### 4.1 Initial Setup

```bash
# 1. Clone or navigate to project
cd /Users/ngs/clawd/projects/ai-team

# 2. Verify database exists
ls -la team.db

# 3. Check Python dependencies
python3 -c "import sqlite3; print('SQLite OK')"

# 4. Test CLI
python3 team_db.py --help
```

### 4.2 Configuration Files

| File | Purpose |
|------|---------|
| `team.db` | Main SQLite database |
| `orchestrator_config.json` | Orchestrator settings (optional) |
| `agents/*.md` | Agent configuration files |

### 4.3 Cron Setup

Add to crontab for automation:

```bash
# Edit crontab
crontab -e

# Add these lines
*/5 * * * * cd /Users/ngs/clawd/projects/ai-team && python3 health_monitor.py --daemon
*/5 * * * * cd /Users/ngs/clawd/projects/ai-team && python3 auto_assign.py --run
0 * * * * cd /Users/ngs/clawd/projects/ai-team && python3 memory_maintenance.py
```

### 4.4 Telegram Notifications

Configure in `notifications.py`:

```python
TELEGRAM_CHANNEL = "1268858185"  # Your channel ID
```

Set notification level per agent:

```bash
python3 team_db.py notify level dev normal
python3 team_db.py notify level pm verbose
```

### 4.5 Agent Configuration

Create agent files in `agents/`:

```markdown
# agents/my-agent.md

## Role
Description of agent role

## Model
Claude Sonnet

## Context
Background information...
```

---

## 5. Troubleshooting

### 5.1 Common Issues

#### Issue: Task creation fails with "project_id is required"

**Cause:** Missing required `--project` flag

**Solution:**
```bash
# Wrong
python3 team_db.py task create "Title"

# Correct
python3 team_db.py task create "Title" --project PROJ-001
```

---

#### Issue: Task creation fails with "expected_outcome is REQUIRED"

**Cause:** Missing Task Quality Framework fields

**Solution:**
```bash
python3 team_db.py task create "Title" \
  --project PROJ-001 \
  --expected-outcome "Clear success definition" \
  --prerequisites "- [ ] Item 1" \
  --acceptance "- [ ] Criteria 1"
```

---

#### Issue: Agent shows as offline

**Cause:** Heartbeat not updated > 60 minutes

**Solution:**
```bash
# Update heartbeat manually
python3 team_db.py agent heartbeat <agent_id>

# Or check health monitor
python3 health_monitor.py --status
```

---

#### Issue: Task stuck in progress

**Cause:** Agent stopped reporting progress

**Solution:**
```bash
# Option 1: Manually block and reassign
python3 team_db.py task block <task_id> "Stuck, needs reassign"
python3 team_db.py task assign <task_id> <new_agent>

# Option 2: Auto-resolve
python3 health_monitor.py --auto-resolve
```

---

#### Issue: Telegram notifications not sending

**Cause:** Network issue or channel ID incorrect

**Solution:**
```bash
# Test manually
openclaw message send --channel telegram --target <channel_id> --message "Test"

# Check channel ID in notifications.py
```

---

### 5.2 Database Issues

#### Issue: Database locked

**Solution:**
```bash
# Check for running processes
lsof team.db

# Wait or kill process if safe
kill <pid>
```

#### Issue: Missing tables/columns

**Solution:**
```bash
# Health monitor will auto-create required columns
python3 health_monitor.py --check

# Or manually check schema
sqlite3 team.db ".schema"
```

---

### 5.3 Agent Issues

#### Issue: Agent won't spawn

**Cause:** Auto-assign cannot spawn subagents directly

**Solution:**
```bash
# Use orchestrator for complex missions
python3 orchestrator.py goal feature "Title" --outcome "Expected result"

# Or manually spawn via OpenClaw
openclaw sessions spawn --label "dev-T-001" --task "Task message"
```

---

#### Issue: Fix loop exceeded

**Cause:** Task failed > 10 times

**Solution:**
```bash
# View task details
python3 team_db.py task list --status blocked

# Manual intervention required
# Review task, provide guidance, unblock
python3 team_db.py task unblock <task_id>
```

---

### 5.4 Mission/Orchestrator Issues

#### Issue: Mission stuck in planning

**Cause:** Orchestrator agent not responding

**Solution:**
```bash
# Check mission status
python3 orchestrator.py show <mission_id>

# View the orchestration plan
# Execute manually or reassign
```

---

### 5.5 Quick Diagnostics

```bash
# Full system check
python3 health_monitor.py --check

# Check database integrity
sqlite3 team.db "PRAGMA integrity_check;"

# View all blocked tasks
python3 team_db.py task list --status blocked

# View all offline agents
python3 team_db.py agent list --status blocked

# Check recent notifications
python3 team_db.py notify log --limit 10
```

---

### 5.6 Emergency Procedures

#### Reset Agent to Idle

```bash
# If agent is stuck but task is complete
python3 team_db.py agent heartbeat <agent_id>

# Force status update via database
sqlite3 team.db "UPDATE agents SET status='idle', current_task_id=NULL WHERE id='<agent_id>';"
```

#### Cancel Mission

```bash
# Update mission status
sqlite3 team.db "UPDATE orchestrator_missions SET status='failed' WHERE id='<mission_id>';"

# Cancel related tasks
sqlite3 team.db "UPDATE tasks SET status='cancelled' WHERE id LIKE 'T-<date>%' AND assignee_id IS NULL;"
```

---

## Appendix A: Database Views Reference

| View | Purpose |
|------|---------|
| `v_agent_workload` | Agent task counts and progress |
| `v_agent_status` | Agent health and current task |
| `v_project_status` | Project completion statistics |
| `v_dashboard_stats` | Overall system statistics |
| `v_daily_summary` | Today's activity summary |
| `v_task_summary` | Task details with assignee names |

---

## Appendix B: Task Status Flow

```
                    ┌─────────────┐
                    │   BACKLOG   │
                    └──────┬──────┘
                           │ unbacklog
                           ▼
┌─────────┐    assign   ┌─────────┐    start    ┌─────────────┐
│ CREATED │ ──────────▶ │   TODO  │ ──────────▶ │ IN_PROGRESS │
└─────────┘             └─────────┘             └──────┬──────┘
                                                       │
          ┌──────────┬──────────┬──────────┐          │
          ▼          ▼          ▼          ▼          │
      ┌──────┐   ┌──────┐   ┌──────┐   ┌──────┐      │
      │ 25%  │   │ 50%  │   │ 75%  │   │ 100% │      │ block
      └──────┘   └──────┘   └──────┘   └──┬───┘      │
                                           │          ▼
                                           ▼     ┌──────────┐
                                       ┌────────┐ │ BLOCKED  │
                                       │ REVIEW │ └───┬──────┘
                                       └───┬────┘     │ unblock
                                           │          │
                                    approve │          │
                                           ▼          │
                                       ┌────────┐     │
                                       │  DONE  │◀────┘
                                       └────────┘
```

---

## Appendix C: Notification Events

| Event | Emoji | Minimal | Normal | Verbose |
|-------|-------|---------|--------|---------|
| Create | 🆕 | ❌ | ❌ | ✅ |
| Assign | 📋 | ❌ | ✅ | ✅ |
| Start | 🚀 | ❌ | ✅ | ✅ |
| Complete | ✅ | ✅ | ✅ | ✅ |
| Block | 🚫 | ✅ | ✅ | ✅ |
| Unblock | 🔄 | ❌ | ✅ | ✅ |
| Review | 👀 | ❌ | ❌ | ✅ |
| Backlog | 📋 | ❌ | ❌ | ✅ |

---

*End of Documentation*

**Need Help?** Check the memory files in `memory/YYYY-MM-DD.md` for recent system updates and known issues.
