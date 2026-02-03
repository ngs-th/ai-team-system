# 🤖 AI Team System

**Version:** 4.0.0  
**Created:** 2026-02-01  
**Updated:** 2026-02-03  
**Status:** Active  
**Based on:** Sengdao2 BMAD Agent Pattern + Multi-Agent Standby System

---

## 📋 Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Agent Roster](#3-agent-roster)
4. [Task Workflow](#4-task-workflow)
5. [Database System](#5-database-system-teamdb)
6. [Memory System](#6-memory-system)
7. [Agent Status Reporting](#7-agent-status-reporting)
8. [Cron Jobs](#8-cron-jobs)
9. [Audit Logging](#9-audit-logging)
10. [Retry Queue](#10-retry-queue)
11. [Inter-Agent Communication](#11-inter-agent-communication)
12. [Key Files](#12-key-files)
13. [CLI Commands](#13-cli-commands)
14. [Recent Changes](#14-recent-changes)

---

## 1. Overview

เอกสารนี้เป็น **Single Source of Truth** สำหรับระบบ AI Team:

- **11 Agents** พร้อมบทบาทชัดเจน
- **Task Workflow** แบบมี Review (in_progress → review → done)
- **Memory System** 3 layers (Context + Working Memory + Communications)
- **Auto-assign + Auto-spawn** ทำงานอัตโนมัติ
- **Status Reporting** Agents รายงานสถานะกลับทุก 30 นาที
- **Agent Sync** Auto-detect stale agents ทุก 5 นาที
- **Retry Queue** Failed operations retry อัตโนมัติ
- **Audit Logging** บันทึกทุก event สำหรับ debugging
- **Telegram Notifications** ทุกเหตุการณ์สำคัญ
- **Timezone:** Asia/Bangkok (UTC+7)

---

## 2. Architecture

### 2.1 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     AI Team System v4.0                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    Cron Jobs                             │    │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │    │
│  │  │Spawn Manager│ │Health Monitor│ │Agent Sync   │        │    │
│  │  │(ทุก 5 นาที)  │ │(ทุก 5 นาที)  │ │(ทุก 5 นาที) │        │    │
│  │  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘        │    │
│  │  ┌─────────────┐ ┌─────────────┐                        │    │
│  │  │Retry Queue  │ │Comm Bridge  │                        │    │
│  │  │(ทุก 10 นาที)│ │(ทุก 5 นาที)  │                        │    │
│  │  └─────────────┘ └─────────────┘                        │    │
│  └─────────────────────────────────────────────────────────┘    │
│                             │                                    │
│                             ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    OpenClaw Gateway                      │    │
│  │              (sessions_spawn, sessions_send)             │    │
│  └─────────────────────────────────────────────────────────┘    │
│                             │                                    │
│                             ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   Sub-Agents (Isolated)                  │    │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐         │    │
│  │  │ PM   │ │Dev   │ │UX    │ │QA    │ │...   │  x11    │    │
│  │  │ John │ │Amelia│ │Sally │ │Quinn │ │      │         │    │
│  │  └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘         │    │
│  │     │        │        │        │        │              │    │
│  │     └────────┴────────┴────────┴────────┘              │    │
│  │                    │                                    │    │
│  │                    ▼                                    │    │
│  │  ┌──────────────────────────────────────────────────┐  │    │
│  │  │  Status Reporting (heartbeat every 30 min)       │  │    │
│  │  │  - agent_reporter.py start/heartbeat/complete    │  │    │
│  │  └──────────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                             │                                    │
│                             ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    SQLite Database                       │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │    │
│  │  │ tasks    │ │ agents   │ │audit_log │ │retry_queue│   │    │
│  │  ├──────────┤ ├──────────┤ ├──────────┤ ├──────────┤   │    │
│  │  │task_hist │ │context   │ │agent_work│ │agent_comm│   │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow

```
1. Create Task → Database (status=todo)
2. Auto-Assign → Database (assignee_id=agent, status=todo)
3. Spawn Manager → OpenClaw API (sessions_spawn)
4. Agent Starts → agent_reporter.py start → Database (status=active)
5. Agent Works → Every 30 min: agent_reporter.py heartbeat
6. Agent Done → agent_reporter.py complete → Database (status=review)
7. Agent Sync (cron) → Check heartbeats → Reset stale agents
8. Retry Queue (cron) → Retry failed operations
9. Audit Log → Log every event for debugging
```

---

## 3. Agent Roster

| # | Agent | ชื่อ | บทบาท | Model | Status |
|---|-------|------|-------|-------|--------|
| 1 | **Orchestrator** | Master | ประสานงานหลัก | kimi-for-coding | Standby |
| 2 | **PM** | John | Product Manager | Claude Opus | Standby |
| 3 | **Analyst** | Mary | Business Analyst | Claude Sonnet | Standby |
| 4 | **Architect** | Winston | System Architect | Claude Opus | Standby |
| 5 | **Dev** | Amelia | Developer | Kimi Code | Standby |
| 6 | **UX Designer** | Sally | UX/UI Designer | Claude Sonnet | Standby |
| 7 | **Scrum Master** | Bob | Scrum Master | Claude Sonnet | Standby |
| 8 | **QA Engineer** | Quinn | QA | Claude Sonnet | Standby |
| 9 | **Tech Writer** | Tom | Technical Writer | Claude Sonnet | Standby |
| 10 | **Solo Dev** | Barry | Quick Flow Dev | Kimi Code | Standby |
| 11 | **Planning** | (N/A) | Planning Agent | Claude Sonnet | Standby |

**Session Keys:** ดูใน `STANDBY_AGENTS.md`

---

## 4. Task Workflow

### 4.1 Status Flow

```
todo → in_progress → review → done
  ↓        ↓           ↓
backlog  blocked    (QA verify)
```

**Workflow ละเอียด:**

| สถานะ | ความหมาย | การเปลี่ยนสถานะ |
|--------|----------|----------------|
| **backlog** | รอข้อมูล/ทรัพยากร | `task backlog <id> --reason "..."` |
| **todo** | พร้อมเริ่ม รอ assign | Auto-assign ทุก 10 นาที |
| **in_progress** | กำลังทำ | Spawn auto → status=in_progress |
| **blocked** | ติดปัญหา | `task block <id> "reason"` |
| **review** | รอ QA ตรวจสอบ | `task done <id>` (auto → review) |
| **done** | เสร็จสมบูรณ์ | `task approve <id> --reviewer qa` |

### 4.2 Task Completion Flow

1. **Spawn Manager** detects todo task with assignee → Spawns subagent
2. **Agent** starts work → `agent_reporter.py start` → Database updated
3. **Agent** works → `agent_reporter.py heartbeat` every 30 min
4. **Agent** completes → `agent_reporter.py complete` → Status=review
5. **QA** reviews → `task approve` → Status=done

### 4.3 Required Fields (MANDATORY)

```bash
python3 team_db.py task create "Title" \
  --project PROJ-001 \
  --working-dir /Users/ngs/Herd/nurse-ai \
  --expected-outcome "What success looks like" \
  --prerequisites "- [ ] Item 1
- [ ] Item 2" \
  --acceptance "- [ ] Criteria 1
- [ ] Criteria 2"
```

---

## 5. Database System (team.db)

### 5.1 Core Tables

```sql
-- Tasks
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    project_id TEXT NOT NULL,
    assignee_id TEXT,
    status TEXT DEFAULT 'todo' CHECK (status IN ('backlog', 'todo', 'in_progress', 'review', 'done', 'blocked', 'cancelled')),
    blocked_reason TEXT,
    priority TEXT DEFAULT 'normal',
    progress INTEGER DEFAULT 0,
    actual_duration_minutes INTEGER,
    fix_loop_count INTEGER DEFAULT 0,
    prerequisites TEXT NOT NULL,        -- MANDATORY
    acceptance_criteria TEXT NOT NULL,  -- MANDATORY
    expected_outcome TEXT NOT NULL,     -- MANDATORY
    working_dir TEXT NOT NULL,          -- MANDATORY: Where agent must work
    created_at DATETIME,
    started_at DATETIME,
    completed_at DATETIME,
    updated_at DATETIME
);

-- Agents
CREATE TABLE agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    model TEXT,
    status TEXT DEFAULT 'idle',
    current_task_id TEXT,
    last_heartbeat DATETIME,
    total_tasks_completed INTEGER DEFAULT 0,
    total_tasks_assigned INTEGER DEFAULT 0,
    notification_level TEXT DEFAULT 'normal',
    health_status TEXT DEFAULT 'unknown'
);
```

### 5.2 Memory Tables

```sql
-- Long-term Memory (CLAUDE.md equivalent)
CREATE TABLE agent_context (
    agent_id TEXT PRIMARY KEY,
    context TEXT DEFAULT '',      -- Role & responsibilities
    learnings TEXT DEFAULT '',    -- Accumulated knowledge
    preferences TEXT DEFAULT '',  -- Personal settings
    last_updated DATETIME
);

-- Short-term Memory (WORKING.md equivalent)
CREATE TABLE agent_working_memory (
    agent_id TEXT PRIMARY KEY,
    current_task_id TEXT,
    working_notes TEXT DEFAULT '',
    blockers TEXT DEFAULT '',
    next_steps TEXT DEFAULT '',
    last_updated DATETIME
);

-- Inter-Agent Communication
CREATE TABLE agent_communications (
    id INTEGER PRIMARY KEY,
    from_agent_id TEXT NOT NULL,
    to_agent_id TEXT,
    task_id TEXT,
    message TEXT NOT NULL,
    message_type TEXT CHECK (message_type IN ('comment', 'mention', 'request', 'response')),
    is_read BOOLEAN DEFAULT FALSE,
    created_at DATETIME
);

-- Audit Log (NEW in v4.0)
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    event_type TEXT NOT NULL,
    agent_id TEXT,
    task_id TEXT,
    details TEXT,
    before_state TEXT,
    after_state TEXT,
    ip_address TEXT,
    session_key TEXT
);

-- Retry Queue (NEW in v4.0)
CREATE TABLE retry_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation TEXT NOT NULL,
    payload TEXT NOT NULL,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    next_retry_at DATETIME,
    last_error TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending'
);
```

---

## 6. Memory System

### 6.1 Architecture

| Layer | Table | Purpose | Update Frequency |
|-------|-------|---------|------------------|
| **Context** | agent_context | บทบาท, ความรู้สะสม | Manual + Auto |
| **Working** | agent_working_memory | งานปัจจุบัน, ปัญหา, แผน | ทุก 30 นาที |
| **Comm** | agent_communications | ข้อความระหว่าง agents | Real-time |

### 6.2 Commands

```bash
# View memory
python3 team_db.py agent memory show <agent_id>
python3 team_db.py agent context show <agent_id>

# Update working memory
python3 agent_memory_writer.py working <agent_id> \
  --task <task_id> \
  --notes "Current progress" \
  --blockers "None" \
  --next "Will implement X"

# Add learning
python3 agent_memory_writer.py learn <agent_id> "What I learned"
```

---

## 7. Agent Status Reporting

### 7.1 Overview

Agents MUST report their status back to the main system using `agent_reporter.py`:

| Command | When to Use | Effect |
|---------|-------------|--------|
| `start` | When agent begins work | status=active, task=in_progress |
| `heartbeat` | Every 30 minutes while working | Updates last_heartbeat |
| `progress` | When progress changes | Updates task progress |
| `complete` | When agent finishes task | status=idle, task=review |
| `status` | General status update | Updates agent status |

### 7.2 Usage

```bash
# Start working on task
python3 agent_reporter.py start \
  --agent pm \
  --task T-20260202-001

# Send heartbeat (every 30 minutes MANDATORY)
python3 agent_reporter.py heartbeat --agent pm

# Update progress
python3 agent_reporter.py progress \
  --agent pm \
  --task T-20260202-001 \
  --progress 50 \
  --message "Halfway done"

# Complete task
python3 agent_reporter.py complete \
  --agent pm \
  --task T-20260202-001 \
  --message "PRD completed and saved"
```

### 7.3 Stale Agent Detection

**Agent Sync** (cron every 5 minutes) automatically:
1. Finds agents with no heartbeat > 30 minutes
2. Resets them to `idle` status
3. Blocks their current task with reason "Agent timeout"
4. Logs to audit_log

---

## 8. Cron Jobs

| Job | Schedule | Purpose | Status |
|-----|----------|---------|--------|
| **AI Team Spawn Agents** | ทุก 5 นาที | Spawn subagents for todo tasks | ✅ Active |
| **AI Team Health Monitor** | ทุก 5 นาที | Check agent health, long-running sessions | ✅ Active |
| **AI Team Agent Sync** | ทุก 5 นาที | Detect and reset stale agents | ✅ Active |
| **AI Team Retry Queue** | ทุก 10 นาที | Retry failed operations | ✅ Active |
| **AI Team Comm Bridge** | ทุก 5 นาที | Forward agent messages to Telegram | ✅ Active |

### 8.1 Spawn Manager Flow

```
Spawn Manager (cron every 5 min)
    ↓
Get todo tasks with assignee
    ↓
Check for each task:
  - Has working_dir?
  - working_dir exists?
  - Not already spawned?
  - Not spawned recently (>10 min)?
    ↓
Spawn subagent via OpenClaw API
  - Retry up to 3 times
  - Exponential backoff
  - Log to audit_log
    ↓
Update database:
  - agent.status = active
  - agent.current_task_id = task
  - task.status = in_progress
```

---

## 9. Audit Logging

### 9.1 Overview

All significant events are logged to `audit_log` table and `logs/audit.log` file:

| Event Type | Description |
|------------|-------------|
| `AGENT_SPAWN` | When subagent is spawned |
| `STATUS_CHANGE` | When agent status changes |
| `TASK_UPDATE` | When task status changes |
| `HEARTBEAT` | Agent heartbeat received |
| `STALE_DETECTED` | Stale agent detected |
| `RETRY_ATTEMPT` | Retry queue operation |

### 9.2 Usage

```bash
# View recent events
python3 audit_log.py --recent 20

# View agent activity
python3 audit_log.py --agent pm --recent 10

# View via database
sqlite3 team.db "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 10;"
```

---

## 10. Retry Queue

### 10.1 Overview

Failed operations are queued for retry with exponential backoff:
- First retry: 5 minutes
- Second retry: 10 minutes
- Third retry: 20 minutes
- Max retries: 3

### 10.2 Operations Supported

| Operation | Description |
|-----------|-------------|
| `spawn` | Failed subagent spawn |
| `report` | Failed status report |

### 10.3 Usage

```bash
# View stats
python3 retry_queue.py --stats

# Process queue manually
python3 retry_queue.py --process

# View via database
sqlite3 team.db "SELECT * FROM retry_queue WHERE status='pending';"
```

---

## 11. Inter-Agent Communication

### 11.1 Database Messages

```bash
# Send message
python3 team_db.py agent comm send <from_agent> "Message" \
  --to <to_agent> --task <task_id>

# List messages
python3 team_db.py agent comm list <agent_id>

# Mark as read
python3 team_db.py agent comm read <message_id>
```

### 11.2 Telegram Bridge

**Realtime Mode:** Forward agent communications to Telegram every 5 minutes
**Digest Mode:** Summary every 30 minutes

---

## 12. Key Files

| File | Purpose |
|------|---------|
| `team_db.py` | Main CLI tool for tasks, agents, notifications |
| `spawn_manager_fixed.py` | Spawn subagents with retry logic |
| `agent_reporter.py` | Agents report status back to system |
| `agent_sync.py` | Detect and reset stale agents |
| `retry_queue.py` | Retry failed operations |
| `audit_log.py` | Centralized audit logging |
| `dashboard.php` | Web Kanban board (read-only) |
| `auto_assign.py` | Auto-assign idle agents to todo tasks |
| `health_monitor.py` | Health checks and alerts |
| `memory_maintenance.py` | Update learnings, reset stale agents |
| `notifications.py` | NotificationManager with HTML stripping |
| `agent_memory_writer.py` | Agents update working memory |
| `multi_agent_standby.py` | Spawn all agents in standby mode |
| `agent_comm_hub.py` | Facilitate agent communication |
| `STANDBY_AGENTS.md` | Active agent session keys |
| `docs/IMPLEMENTATION.md` | Implementation details |

---

## 13. CLI Commands

### Task Management
```bash
# Create task (MANDATORY fields)
python3 team_db.py task create "Title" \
  --project PROJ-001 \
  --working-dir /Users/ngs/Herd/nurse-ai \
  --expected-outcome "What success looks like" \
  --prerequisites "- [ ] Item 1
- [ ] Item 2" \
  --acceptance "- [ ] Criteria 1
- [ ] Criteria 2"

# Start working
python3 team_db.py task start <task_id>

# Update progress
python3 team_db.py task progress <task_id> <percent>

# Complete (sends to review)
python3 team_db.py task done <task_id>

# Approve (moves to done)
python3 team_db.py task approve <task_id> --reviewer qa

# Block/Unblock
python3 team_db.py task block <task_id> "Reason"
python3 team_db.py task unblock <task_id> --agent <agent_id>

# List tasks
python3 team_db.py task list --status in_progress
python3 team_db.py task list --agent dev
```

### Agent Management
```bash
# List agents
python3 team_db.py agent list
python3 team_db.py agent list --status idle

# Update heartbeat
python3 team_db.py agent heartbeat <agent_id>

# View memory
python3 team_db.py agent memory show <agent_id>
python3 team_db.py agent context show <agent_id>

# Communication
python3 team_db.py agent comm send <from> "Message" --to <to> --task <task_id>
```

### Agent Reporter (for subagents)
```bash
# Start working
python3 agent_reporter.py start --agent <id> --task <task_id>

# Heartbeat (every 30 minutes MANDATORY)
python3 agent_reporter.py heartbeat --agent <id>

# Update progress
python3 agent_reporter.py progress --agent <id> --task <task_id> --progress 50

# Complete task
python3 agent_reporter.py complete --agent <id> --task <task_id> --message "Done"
```

### Audit & Retry
```bash
# View audit log
python3 audit_log.py --recent 20
python3 audit_log.py --agent <id> --recent 10

# View retry queue
python3 retry_queue.py --stats
python3 retry_queue.py --process
```

### Multi-Agent Operations
```bash
# Spawn all agents in standby mode
python3 multi_agent_standby.py --spawn-all

# List active agents
python3 agent_comm_hub.py --status

# Broadcast to all agents
python3 agent_comm_hub.py --broadcast "Message"

# Send to specific agent
python3 agent_comm_hub.py --send "agent_id:Message"
```

---

## 14. Recent Changes

### v4.0.0 (2026-02-03) - Major Update

**New Features:**
- ✅ **Multi-Agent Standby System** - Spawn 9 agents simultaneously
- ✅ **Agent Reporter** - Mandatory status reporting every 30 minutes
- ✅ **Agent Sync** - Auto-detect and reset stale agents (cron every 5 min)
- ✅ **Retry Queue** - Exponential backoff for failed operations
- ✅ **Audit Logging** - All events logged to DB + file
- ✅ **Working Directory Validation** - Enforced for all tasks

**Architecture Improvements:**
- ✅ **Real Spawn** - spawn_manager now spawns actual subagents via OpenClaw API
- ✅ **Retry Logic** - 3 attempts with exponential backoff (5min, 10min, 20min)
- ✅ **Status Sync** - Database reflects real agent states via heartbeats
- ✅ **Stale Detection** - Agents without heartbeat >30min auto-reset

**Documentation:**
- ✅ Updated `AI-TEAM-SYSTEM.md` (this file)
- ✅ Created `docs/IMPLEMENTATION.md` with architecture diagram
- ✅ Updated all 9 agent configs with reporter instructions
- ✅ Created `STANDBY_AGENTS.md` with session keys

**New Scripts:**
- `spawn_manager_fixed.py` - Real spawn with retry
- `agent_reporter.py` - Status reporting
- `agent_sync.py` - Stale agent detection
- `retry_queue.py` - Failed operation retry
- `audit_log.py` - Centralized logging
- `multi_agent_standby.py` - Spawn all agents
- `agent_comm_hub.py` - Agent communication hub

### Previous Versions

**v3.6.0 (2026-02-03):**
- Task workflow with review stage
- Memory system 3 layers
- Notification system with HTML stripping
- Auto-assign + auto-spawn

**v3.5.0 (2026-02-02):**
- Task Quality Framework (required fields)
- Orchestrator system
- Auto-fix workflow

---

**Last Updated:** 2026-02-03 09:15 AM  
**Maintainer:** Orchestrator Agent  
**Version:** 4.0.0  
**Next Review:** 2026-03-03
