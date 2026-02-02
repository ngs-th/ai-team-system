# 🤖 AI Team System

**Version:** 3.6.0  
**Created:** 2026-02-01  
**Updated:** 2026-02-03  
**Status:** Active  
**Based on:** Sengdao2 BMAD Agent Pattern

---

## 📋 Table of Contents

1. [Overview](#1-overview)
2. [Agent Roster](#2-agent-roster)
3. [Task Workflow](#3-task-workflow)
4. [Database System](#4-database-system-teamdb)
5. [Memory System](#5-memory-system)
6. [Notification System](#6-notification-system)
7. [Cron Jobs](#7-cron-jobs)
8. [Inter-Agent Communication](#8-inter-agent-communication)
9. [Key Files](#9-key-files)
10. [CLI Commands](#10-cli-commands)
11. [Recent Changes](#11-recent-changes)

---

## 1. Overview

เอกสารนี้เป็น **Single Source of Truth** สำหรับระบบ AI Team:

- **11 Agents** พร้อมบทบาทชัดเจน
- **Task Workflow** แบบมี Review (in_progress → review → done)
- **Memory System** 3 layers (Context + Working Memory + Communications)
- **Auto-assign + Auto-spawn** ทำงานอัตโนมัติ
- **Telegram Notifications** ทุกเหตุการณ์สำคัญ
- **Timezone:** Asia/Bangkok (UTC+7)

---

## 2. Agent Roster

| # | Agent | ชื่อ | บทบาท | Model |
|---|-------|------|-------|-------|
| 1 | **Orchestrator** | Master | ประสานงานหลัก | kimi-for-coding |
| 2 | **PM** | John | Product Manager | Claude Opus |
| 3 | **Analyst** | Mary | Business Analyst | Claude Sonnet |
| 4 | **Architect** | Winston | System Architect | Claude Opus |
| 5 | **Dev** | Amelia | Developer | Kimi Code |
| 6 | **UX Designer** | Sally | UX/UI Designer | Claude Sonnet |
| 7 | **Scrum Master** | Bob | Scrum Master | Claude Sonnet |
| 8 | **QA Engineer** | Quinn | QA | Claude Sonnet |
| 9 | **Tech Writer** | Tom | Technical Writer | Claude Sonnet |
| 10 | **Solo Dev** | Barry | Quick Flow Dev | Kimi Code |

---

## 3. Task Workflow

### 3.1 Status Flow

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
| **in_progress** | กำลังทำ | `task start <id>` |
| **blocked** | ติดปัญหา | `task block <id> "reason"` |
| **review** | รอ QA ตรวจสอบ | `task done <id>` (auto → review) |
| **done** | เสร็จสมบูรณ์ | `task approve <id> --reviewer qa` |

### 3.2 Task Completion Flow

1. **Agent ทำงานเสร็จ** → `task done <id>`
2. **ระบบส่งไป review** (ไม่ใช่ done เลย)
3. **QA ตรวจสอบ** → `task approve <id> --reviewer qa`
4. **งานเสร็จสมบูรณ์**

---

## 4. Database System (team.db)

### 4.1 Core Tables

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

### 4.2 Memory Tables

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
```

### 4.3 Timezone Configuration

**⚠️ Important:** SQLite `CURRENT_TIMESTAMP` returns UTC. We use `datetime('now', 'localtime')` for Bangkok time (UTC+7).

```sql
-- Use this for Bangkok time
UPDATE tasks SET updated_at = datetime('now', 'localtime');

-- NOT this (returns UTC)
UPDATE tasks SET updated_at = CURRENT_TIMESTAMP;  -- ❌ UTC
```

---

## 5. Memory System

### 5.1 Architecture

| Layer | Table | Purpose | Update Frequency |
|-------|-------|---------|------------------|
| **Context** | agent_context | บทบาท, ความรู้สะสม | Manual + Auto (จาก task history) |
| **Working** | agent_working_memory | งานปัจจุบัน, ปัญหา, แผน | ทุก 30 นาทีขณะทำงาน |
| **Comm** | agent_communications | ข้อความระหว่าง agents | Real-time |

### 5.2 MANDATORY Requirements (บังคับ)

**⚠️ Agents MUST update memory ตามนี้:**

| ความถี่ | การกระทำ | คำสั่ง |
|---------|----------|--------|
| **ทุก 30 นาที** | อัพเดต working memory | `python3 agent_memory_writer.py working <agent_id> --task <id> --notes "..." --blockers "..." --next "..."` |
| **ก่อนจบงาน** | Add learning | `python3 agent_memory_writer.py learn <agent_id> "สิ่งที่เรียนรู้"` |
| **เมื่อติดปัญหา** | อัพเดต blockers | `--blockers "ติดที่ X ต้องการความช่วยเหลือ"` |

**❌ ผลกระทบถ้าไม่ทำ:**
- QA จะ **ไม่ approve** งานที่ไม่อัพเดต memory
- Task จะค้างอยู่ที่ `review` ตลอดไป

### 5.3 Commands

```bash
# Update working memory (MANDATORY every 30 min)
python3 agent_memory_writer.py working <agent_id> \
  --task <task_id> \
  --notes "Current progress" \
  --blockers "None" \
  --next "Will implement X"

# Add learning (MANDATORY before task done)
python3 agent_memory_writer.py learn <agent_id> "What I learned"

# View memory
python3 team_db.py agent memory show <agent_id>
python3 team_db.py agent context <agent_id>
```

### 5.4 Auto-Maintenance

Cron job `memory_maintenance.py` ทำอัตโนมัติทุกชั่วโมง:
1. Reset stale agents (>1h ไม่มี heartbeat)
2. Update learnings จากงานที่เสร็จ (7 วันล่าสุด)
3. Archive history เกิน 30 วัน

---

## 6. Notification System

### 6.1 Configuration

```bash
# Set notification level
python3 team_db.py notify level <agent_id> <minimal|normal|verbose>

# Levels:
# - minimal: block, complete only
# - normal: assign, complete, block, start, unblock (default)
# - verbose: all events
```

### 6.2 Notification Format

**✅ DO:** Plain text, Markdown-style
```
📋 T-001 → Barry
   Implement feature X

✅ T-001 | Barry
   Feature X completed

🚫 T-001 BLOCKED
   🚫 Need API key
   Feature X implementation
```

**❌ DON'T:** HTML tags
```
<b>Task Completed</b>          ❌
<code>██████████</code>       ❌
<b>Task:</b> T-001             ❌
```

### 6.3 Events

| Event | Emoji | Trigger |
|-------|-------|---------|
| ASSIGN | 📋 | Task assigned to agent |
| START | 🚀 | Agent starts working |
| PROGRESS | 📊 | Progress milestone (0, 25, 50, 75, 100) |
| REVIEW | 👀 | Task sent to review |
| COMPLETE | ✅ | Task approved & done |
| BLOCK | 🚫 | Task blocked |
| UNBLOCK | 🔄 | Task resumed |

---

## 7. Cron Jobs

| Job | Schedule | Purpose |
|-----|----------|---------|
| **AI Team Health Monitor** | ทุก 5 นาที | ตรวจสอบ long-running sessions, ส่ง alerts |
| **AI Team Auto-Assign** | ทุก 10 นาที | แจกงานให้ idle agents |
| **AI Team Spawn Agents** | ทุก 5 นาที | Spawn subagents สำหรับ assigned tasks |
| **AI Team Memory Maintenance** | ทุกชั่วโมง | Update learnings, reset stale agents |

### 7.1 Auto-Assign + Spawn Flow

```
Auto-Assign (ทุก 10 นาที)
    ↓
หา todo tasks ที่ยังไม่มี assignee
    ↓
Match กับ idle agents (context + role)
    ↓
Update database (assignee_id, status=todo)
    ↓
Spawn Manager (ทุก 5 นาที)
    ↓
หา tasks ที่ assign แล้วแต่ยังไม่ spawn
    ↓
Spawn subagents via sessions_spawn
    ↓
Agents ทำงาน + update progress
```

---

## 8. Inter-Agent Communication

### 8.1 Database Messages

```bash
# Send message
python3 team_db.py agent comm send <from_agent> "Message" \
  --to <to_agent> --task <task_id>

# List messages
python3 team_db.py agent comm list <agent_id>

# Mark as read
python3 team_db.py agent comm read <message_id>
```

### 8.2 Telegram Bridge (Planned)

**Real-time:** Forward agent communications to Telegram immediately
**Digest:** Summary every 30 minutes

---

## 9. Key Files

| File | Purpose |
|------|---------|
| `team_db.py` | Main CLI tool for tasks, agents, notifications |
| `dashboard.php` | Web Kanban board (read-only) |
| `auto_assign.py` | Auto-assign idle agents to todo tasks |
| `spawn_manager.py` | Prepare spawn commands for subagents |
| `health_monitor.py` | Health checks and alerts |
| `memory_maintenance.py` | Update learnings, reset stale agents |
| `notifications.py` | NotificationManager with HTML stripping |
| `agent_memory_writer.py` | Agents update working memory |
| `triggers.sql` | Database triggers for data integrity |
| `TIMEZONE.md` | Timezone configuration notes |

---

## 10. CLI Commands

### Task Management
```bash
# Create task (MANDATORY fields)
python3 team_db.py task create "Title" \
  --project PROJ-001 \
  --expected-outcome "What success looks like" \
  --prerequisites "- [ ] Item 1\n- [ ] Item 2" \
  --acceptance "- [ ] Criteria 1\n- [ ] Criteria 2"

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
python3 team_db.py agent context <agent_id>

# Communication
python3 team_db.py agent comm send <from> "Message" --to <to> --task <task_id>
```

### Notifications
```bash
# Set level
python3 team_db.py notify level <agent_id> <minimal|normal|verbose>

# View settings
python3 team_db.py notify show
python3 team_db.py notify show --agent <agent_id>

# View log
python3 team_db.py notify log --limit 20
python3 team_db.py notify log --task <task_id>
```

### Memory
```bash
# Update working memory (agents use this)
python3 agent_memory_writer.py working <agent_id> \
  --task <task_id> \
  --notes "Current progress" \
  --blockers "None" \
  --next "Will do X"

# Add learning
python3 agent_memory_writer.py learn <agent_id> "Learning text"
```

---

## 11. Recent Changes

### v3.6.0 (2026-02-03)

**Workflow Changes:**
- ✅ **Task completion** now sends to `review` first (not `done`)
- ✅ **Task approve** command moves from `review` → `done`
- ✅ **Reset start time** when reassigning tasks (triggers + code)

**Notification System:**
- ✅ HTML stripping from all messages
- ✅ Telegram-friendly format (no HTML tags)
- ✅ Markdown-style formatting (**bold**, `code`)
- ✅ Configurable levels per agent

**Memory System:**
- ✅ `agent_memory_writer.py` for agents to update working memory
- ✅ Auto-update learnings from completed tasks
- ✅ Instructions in spawn messages (update every 30 min)

**Timezone:**
- ✅ Use `datetime('now', 'localtime')` instead of `CURRENT_TIMESTAMP`
- ✅ All timestamps in Asia/Bangkok (UTC+7)

**Dashboard:**
- ✅ Fix PHP float→int deprecation warnings
- ✅ Fix markdown checklist rendering (literal `\n`)
- ✅ Fix description/expected outcome display

**Database:**
- ✅ Triggers for auto-reset started_at on reassign
- ✅ Triggers for auto-calculate duration on complete

### Known Issues (In Progress)

**HTML Notifications:**
- ⚠️ **Issue:** Some agents still sending HTML tags (`<b>`, `<code>`) to Telegram
- ✅ **Mitigation:** 
  - `notifications.py` - Auto-strip HTML from all messages
  - `message_filter.py` - Force strip helper for agents
  - `message_guard.sh` - Bash wrapper with HTML removal
  - Updated spawn instructions with strict "NO HTML" rules
- **Format:** Use `**bold**` and `code` (Markdown) NOT `<b>` or `<code>` (HTML)

---

**Last Updated:** 2026-02-03 05:30  
**Maintainer:** Orchestrator Agent  
**Next Review:** 2026-03-03
