# 🤖 AI Team System

**Version:** 4.1.1  
**Created:** 2026-02-01  
**Updated:** 2026-02-04  
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

- **15 Agents** พร้อมบทบาทชัดเจน (4 Dev, 4 Reviewer)
- **Task Workflow** แบบมี Review จริง (in_progress → review → reviewing → done)
- **Memory System** 3 layers (Context + Working Memory + Communications)
- **Auto-assign + Auto-spawn** ทำงานอัตโนมัติ
- **Auto-review** สั่ง Reviewer ตรวจโค้ดจริง (ไม่ auto-approve)
- **Status Reporting** Agents รายงานสถานะกลับทุก 30 นาที
- **Agent Sync** Auto-detect stale agents ทุก 5 นาที (รีเซ็ตกลับ todo)
- **Retry Queue** Failed operations retry อัตโนมัติ
- **Audit Logging** บันทึกทุก event สำหรับ debugging
- **Telegram Notifications** ทุกเหตุการณ์สำคัญ
- **Timezone:** Asia/Bangkok (UTC+7)

---

## 2. Architecture

### 2.1 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     AI Team System v4.1                          │
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
│  │                  Agent Runtime Adapter                   │    │
│  │   (openclaw | claude_code via AI_TEAM_AGENT_RUNTIME)    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                             │                                    │
│                             ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   Sub-Agents (Isolated)                  │    │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐         │    │
│  │  │ PM   │ │Dev   │ │UX    │ │QA    │ │...   │  x15    │    │
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
3. Spawn Manager → Runtime Adapter (spawn agent)
4. Agent Starts → agent_reporter.py start → Database (status=in_progress)
5. Agent Works → Every 30 min: agent_reporter.py heartbeat
6. Agent Done → agent_reporter.py complete → Database (status=review)
7. Review Manager → Spawn reviewer → status=reviewing
8. Reviewer Approve/Reject → done หรือ todo (priority=high)
9. Log Bridge (cron) → Parse logs → update progress/complete
10. Agent Sync (cron) → Reset stale agents
11. Retry Queue (cron) → Retry failed operations
12. Audit Log → Log every event for debugging
```

---

## 3. Agent Roster

> รายชื่อด้านล่างคือ **agents ในระบบจริง** (team.db + active runtime)

| # | Agent ID | ชื่อ | บทบาท | Model |
|---|---------|------|-------|-------|
| 1 | **pm** | John | Product Manager | claude-opus-4-5 |
| 2 | **analyst** | Mary | Business Analyst | claude-sonnet-4-5 |
| 3 | **architect** | Winston | System Architect | claude-opus-4-5 |
| 4 | **dev** | Amelia | Developer | kimi-for-coding |
| 5 | **dev-2** | Dev-2 | Developer | kimi-coding/k2p5 |
| 6 | **dev-3** | Dev-3 | Developer | kimi-coding/k2p5 |
| 7 | **dev-4** | Dev-4 | Developer | kimi-coding/k2p5 |
| 8 | **ux-designer** | Sally | UX/UI Designer | claude-sonnet-4-5 |
| 9 | **scrum-master** | Bob | Scrum Master | claude-sonnet-4-5 |
| 10 | **qa** | Quinn | QA Engineer (Reviewer) | claude-sonnet-4-5 |
| 11 | **qa-2** | QA-2 | QA Engineer (Reviewer) | kimi-coding/k2p5 |
| 12 | **qa-3** | QA-3 | QA Engineer (Reviewer) | kimi-coding/k2p5 |
| 13 | **qa-4** | QA-4 | QA Engineer (Reviewer) | kimi-coding/k2p5 |
| 14 | **tech-writer** | Tom | Technical Writer | claude-sonnet-4-5 |
| 15 | **solo-dev** | Barry | Solo Developer | kimi-for-coding |

**Session Keys:** ดูใน `STANDBY_AGENTS.md`

---

## 4. Task Workflow

### 4.1 Status Flow

```
backlog → todo → in_progress → review → reviewing → done

blocked = สถานะจริงใน DB และแสดงเป็น attribute (แถบแดง) บนการ์ด
```

**Dashboard Columns:** Backlog / Todo / Doing / Waiting for Review / Reviewing / Done  
`Waiting for Review` = สถานะ `review` ที่ยังไม่มี reviewer ทำงาน

**Workflow ละเอียด:**

| สถานะ | ความหมาย | การเปลี่ยนสถานะ |
|--------|----------|----------------|
| **backlog** | รอข้อมูล/ทรัพยากร | `task backlog <id> --reason "..."` |
| **todo** | พร้อมเริ่ม รอ assign | Auto-assign ทุก 10 นาที |
| **in_progress** | กำลังทำ | Agent ต้องสั่ง `task start` หรือ `agent_reporter.py start` |
| **blocked** | ติดปัญหา | `task block <id> "reason"` |
| **review** | รอเริ่มตรวจ | `task done <id>` (auto → review) |
| **reviewing** | กำลังตรวจงานจริง | `review_manager.py` เริ่ม reviewer |
| **done** | เสร็จสมบูรณ์ | `task approve <id> --reviewer <qa>` |

**หมายเหตุ:** คอลัมน์ `Waiting for Review` ในแดชบอร์ดคือสถานะ `review` ที่ยังไม่มี reviewer ทำงานอยู่  
(`Reviewing` = สถานะจริงใน DB)

**กติกาแสดง blocked ใน Dashboard (ล่าสุด):**
- การ์ดจะติดธง blocked เฉพาะเมื่อ `status=blocked`
- งานที่ `rejected` (เช่น prerequisites ไม่ครบ) จะกลับ `todo` และเก็บเหตุผลใน `review_feedback` ไม่ใช้ `blocked_reason`
- การ์ด blocked จะถูกเรียงไว้บนสุดของคอลัมน์ปัจจุบัน และไม่อยู่คอลัมน์ Done

**Reject Flow:** เมื่อรีวิวไม่ผ่าน → กลับ `todo` + `priority=high` + เก็บ `review_feedback` เพื่อให้ผู้แก้เห็นเหตุผลทันที

### 4.2 Task Completion Flow

1. **Spawn Manager** detects todo task with assignee → Spawns subagent
2. **Agent** เริ่มงาน → `agent_reporter.py start`
   - ตรวจ **Prerequisites checklist** ถ้าไม่ครบ → **rejected → todo (priority=high)**
3. **Agent** ทำงาน → `agent_reporter.py heartbeat` ทุก 30 นาที
4. **Agent** เสร็จ → `agent_reporter.py complete` → Status=review  
   - **ต้องเป็น in_progress เท่านั้น** (ห้าม complete จาก todo)
   - ถ้า **Prerequisites checklist** ยังไม่ครบ → **rejected → todo (priority=high)** (ห้ามเข้า review)
5. **Review Manager** สั่ง reviewer ตรวจจริง → Status=reviewing
   - ตรวจ **Prerequisites checklist** ซ้ำก่อนเริ่มรีวิว ถ้าไม่ครบ → ย้ายกลับ `todo`
6. **Reviewer** ต้องเช็ค **Acceptance Criteria checklist** ครบทุกข้อ
7. **Approve** → Status=done  
   **Reject** → Status=todo + priority=high + review feedback

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

**บังคับใช้ Checklist จริง:**
- **Prerequisites** ต้องเป็น checklist และต้องถูกติ๊กครบก่อนเริ่มงาน  
- **Acceptance Criteria** ต้องเป็น checklist และต้องถูกติ๊กครบก่อนอนุมัติ

เช็คทีละข้อ:
```bash
python3 team_db.py task check <task_id> --field prerequisites --index <n> --done
python3 team_db.py task check <task_id> --field acceptance --index <n> --done
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
    project_id TEXT,
    assignee_id TEXT,
    status TEXT DEFAULT 'todo' CHECK (status IN ('backlog', 'todo', 'in_progress', 'review', 'reviewing', 'done', 'blocked', 'cancelled')),
    blocked_reason TEXT,
    priority TEXT DEFAULT 'normal',
    progress INTEGER DEFAULT 0,
    review_feedback TEXT,
    review_feedback_at DATETIME,
    actual_duration_minutes INTEGER,
    fix_loop_count INTEGER DEFAULT 0,
    prerequisites TEXT,                 -- MANDATORY via app validation
    acceptance_criteria TEXT,           -- MANDATORY via app validation
    expected_outcome TEXT,              -- MANDATORY via app validation
    working_dir TEXT,                   -- MANDATORY via app validation
    runtime TEXT,                       -- openclaw | claude_code (last spawn)
    runtime_at DATETIME,
    created_at DATETIME,
    started_at DATETIME,
    completed_at DATETIME,
    updated_at DATETIME,
    backlog_at DATETIME,
    todo_at DATETIME,
    in_progress_at DATETIME,
    review_at DATETIME,
    reviewing_at DATETIME,
    done_at DATETIME,
    blocked_at DATETIME
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
    id INTEGER PRIMARY KEY,
    agent_id TEXT NOT NULL,          -- indexed (non-unique)
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

**หมายเหตุสำคัญ:** `agent_reporter.py start` จะตรวจ **Prerequisites checklist**  
ถ้าไม่ครบ ระบบจะ reject งานกลับ `todo` (priority=`high`) และคืน agent เป็น `idle`

### 7.2 Usage

```bash
# Start working on task
python3 agent_reporter.py start \
  --agent pm \
  --task T-20260202-001

# (Required) mark prerequisites checklist before start
python3 team_db.py task check T-20260202-001 --field prerequisites --index 1 --done

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
1. ตรวจสัญญาณ runtime (session ถ้าเป็น OpenClaw, heartbeat ถ้า runtime อื่น)
2. รีเซ็ต agent ที่ไม่ active → `idle`
3. ถ้ามีงานค้างใน `in_progress` → ย้ายกลับ `todo` (ไม่ block)
4. ถ้ามีงานค้างใน `reviewing` และ reviewer หาย → ย้ายกลับ `review` (Waiting for Review)
5. Logs to audit_log

---

## 8. Cron Jobs

| Job | Schedule | Purpose | Status |
|-----|----------|---------|--------|
| **AI Team Spawn** | ทุก 5 นาที | Spawn subagents for todo tasks | ✅ Active |
| **AI Team Agent Sync** | ทุก 5 นาที | Detect and reset stale agents | ✅ Active |
| **AI Team Log Bridge** | ทุก 2 นาที | Parse logs → update progress/complete | ✅ Active |
| **AI Team Auto-Assign** | ทุก 10 นาที | Assign idle agents to todo | ✅ Active |
| **AI Team Auto-Review** | ทุก 5 นาที | Spawn reviewer + manage review queue | ✅ Active |
| **AI Team Retry Queue** | ทุก 10 นาที | Retry failed operations | ✅ Active |

**Auto-Review Behavior:**
- ไม่ auto-approve
- เลือก reviewer จาก pool (`qa`, `qa-2`, `qa-3`, `qa-4` หรือกำหนดด้วย `AI_TEAM_REVIEWERS`)
- ตรวจ `prerequisites` ก่อนรีวิว: ถ้ายังมี `[ ]` จะไม่เริ่มรีวิว และย้ายกลับ `todo`
- เปลี่ยน `review` → `reviewing` และสั่ง reviewer ตรวจจริง
- ถ้า reviewer ไม่มี active session จะถูก reset อัตโนมัติ และงานจะกลับ `review` (Waiting for Review) เพื่อไม่ให้ค้างใน Reviewing

### 8.1 Spawn Manager Flow

```
Spawn Manager (cron every 5 min)
    ↓
Get todo tasks with assignee
    ↓
Check for each task:
  - Has working_dir?
  - working_dir exists?
  - Agent not busy (DB/session)
  - Not spawned recently (>10 min)?
    ↓
Spawn subagent via Runtime Adapter
  - Log to audit_log
    ↓
Update database:
  - agent.status = active
  - agent.current_task_id = task
  - task.status คงเป็น `todo` จนกว่า agent จะสั่ง `task start` / `agent_reporter.py start`
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
| `agent_runtime.py` | Runtime adapter สำหรับ spawn agent (`openclaw`/`claude_code`) |
| `spawn_manager_fixed.py` | Spawn subagents และผูก agent/task โดยไม่บังคับ in_progress |
| `agent_reporter.py` | Agents report status back to system |
| `agent_sync.py` | Detect and reset stale agents |
| `log_bridge.py` | Parse agent logs → update DB progress/complete |
| `review_manager.py` | Auto-queue reviewers + manage review status |
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

### 12.1 Runtime Configuration

```bash
# Default
export AI_TEAM_AGENT_RUNTIME=openclaw

# Switch to Claude Code runtime
export AI_TEAM_AGENT_RUNTIME=claude_code

# Optional: custom command (default: "claude code")
export AI_TEAM_CLAUDE_CMD="claude code"

# Advanced: full template with placeholders {agent_id} {message} {timeout}
export AI_TEAM_CLAUDE_CMD_TEMPLATE='claude code --agent {agent_id} --message "{message}" --timeout {timeout}'
```

**หมายเหตุ:** ถ้า runtime ไม่รองรับ session API, ระบบจะใช้ `last_heartbeat` เป็นสัญญาณ liveness แทน
| `docs/architecture/ERD.md` | ERD (logical data model) ของ `team.db` |

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

# Check prerequisites/acceptance (1-by-1)
python3 team_db.py task check <task_id> --field prerequisites --index <n> --done
python3 team_db.py task check <task_id> --field acceptance --index <n> --done

# Block/Unblock
python3 team_db.py task block <task_id> "Reason"
python3 team_db.py task unblock <task_id> --agent <agent_id>

# List tasks
python3 team_db.py task list --status in_progress
python3 team_db.py task list --status reviewing
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

### v4.1.3 (2026-02-05) - Runtime Adapter (OpenClaw / Claude Code)

**Changes:**
- ✅ เพิ่ม `agent_runtime.py` เป็น runtime adapter กลาง
- ✅ Spawn path ทั้งหมด (`spawn_manager_fixed.py`, `auto_assign.py`, `review_manager.py`) เรียกผ่าน adapter เดียว
- ✅ รองรับ `AI_TEAM_AGENT_RUNTIME=claude_code` โดยไม่ต้องแก้ orchestrator หลัก
- ✅ ปรับ `agent_sync.py` ให้ fallback ไปใช้ heartbeat เมื่อ runtime ไม่มี session API
- ✅ ลดอาการงานค้าง `reviewing` ด้วยการคืนงานกลับ `review` เมื่อ reviewer stale

### v4.1.2 (2026-02-05) - Reject/Blocked Semantics Fix

**Changes:**
- ✅ แก้ flow ให้ prerequisite validation fail = `rejected -> todo` (ไม่ติด blocked)
- ✅ เคลียร์ `blocked_reason/blocked_at` อัตโนมัติเมื่อ task เข้า `in_progress/review/reviewing/done`
- ✅ Dashboard ตีความ blocked จาก `status=blocked` เท่านั้น (ไม่ปนกับ review rejection)
- ✅ Agent prompt ปรับให้ unmet prerequisites ใช้ `task reject --reason ...` แทน `task block`

### v4.1.1 (2026-02-04) - Doc Sync + Workflow Gate Alignment

**Changes:**
- ✅ อัปเดตเอกสารให้ตรงโค้ดจริง (spawn, review gate, checklist gate)
- ✅ อัปเดต Agent model roster ให้ตรง `team.db`
- ✅ แก้ schema doc ให้ตรง DB จริง (app-level validation สำหรับ required fields)
- ✅ ระบุชัดว่า `blocked` เป็นสถานะจริงใน DB และแสดงผลเป็นแถบแดงบนการ์ด
- ✅ ปรับ prerequisite gate ให้ **reject กลับ todo** (ไม่ใช้ blocked สำหรับ validation error)

### v4.1.0 (2026-02-04) - Review + Workflow Hardening

**New Features:**
- ✅ **Reviewer Pool** (qa, qa-2, qa-3, qa-4) ตรวจโค้ดจริง
- ✅ **Reviewing Status** (`review` → `reviewing` → `done`)
- ✅ **Review Feedback** เก็บเหตุผลลง `review_feedback`
- ✅ **Checklist Enforcement**
  - Prerequisites ต้องติ๊กครบก่อน start
  - Acceptance Criteria ต้องติ๊กครบก่อน approve
- ✅ **Status Timestamps** (`todo_at`, `review_at`, `reviewing_at`, `done_at`, ฯลฯ)
- ✅ **Log Bridge** อ่าน log แล้วอัปเดต progress/complete
- ✅ **Dev Scaling** เพิ่ม dev-2/3/4

**Behavior Changes:**
- Reject → กลับ `todo` + `priority=high`
- Agent Sync รีเซ็ตกลับ `todo` (ไม่ block)

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

**Last Updated:** 2026-02-04 11:56 PM  
**Maintainer:** Orchestrator Agent  
**Version:** 4.1.1  
**Next Review:** 2026-03-04
