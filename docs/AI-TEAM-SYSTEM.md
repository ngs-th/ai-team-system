# 🤖 AI Team System

**Version:** 3.5.0  
**Created:** 2026-02-01  
**Updated:** 2026-02-03  
**Status:** Active  
**Based on:** Sengdao2 BMAD Agent Pattern

---

## 📋 Table of Contents

1. [Overview](#1-overview)
2. [Agent Roster](#2-agent-roster)
3. [Decision Matrix](#3-decision-matrix)
4. [Workflow Patterns](#4-workflow-patterns)
5. [Database System (team.db)](#5-database-system-teamdb)
6. [Quality Gates](#6-quality-gates)
7. [Timeout & Fallback](#7-timeout--fallback)
8. [Resource Guidelines](#8-resource-guidelines)
9. [Communication Protocol](#9-communication-protocol)
10. [Tools Reference](#10-tools-reference)
11. [Cron Monitoring System](#11-cron-monitoring-system)
12. [Dashboard (Kanban)](#12-dashboard-kanban)
13. [Alert Response Workflow](#13-alert-response-workflow)
14. [Version History](#14-version-history)

---

## 1. Overview

เอกสารนี้เป็น **Single Source of Truth** สำหรับระบบ AI Team ของ OpenClaw ประกอบด้วย:

- **11 Agents** ที่มีบทบาทและความรับผิดชอบชัดเจน (รวม Orchestrator)
- **4 Workflow Patterns** สำหรับสถานการณ์ต่าง ๆ
- **Centralized Database (team.db)** สำหรับจัดการ tasks, agents, projects
- **Quality Gates** เพื่อรับรองคุณภาพงาน
- **Timeout & Fallback Systems** สำหรับ handle failure scenarios
- **Cron Monitoring System** สำหรับติดตามสถานะอัตโนมัติและแจ้งเตือน
- **Alert Response Workflow** สำหรับจัดการเมื่อเกิดปัญหา

---

## 2. Agent Roster

| # | Agent | ชื่อ | บทบาท | Model | ไฟล์ config |
|---|-------|------|-------|-------|-------------|
| 1 | **Orchestrator** | Master | ประสานงานหลัก | kimi-for-coding | `agents/orchestrator.md` |
| 2 | **PM** | John | Product Manager | Claude Opus | `agents/pm.md` |
| 3 | **Analyst** | Mary | Business Analyst | Claude Sonnet | `agents/analyst.md` |
| 4 | **Architect** | Winston | System Architect | Claude Opus | `agents/architect.md` |
| 5 | **Dev** | Amelia | Developer | Kimi Code | `agents/dev.md` |
| 6 | **UX Designer** | Sally | UX/UI Designer | Claude Sonnet | `agents/ux-designer.md` |
| 7 | **Scrum Master** | Bob | Scrum Master | Claude Sonnet | `agents/scrum-master.md` |
| 8 | **QA Engineer** | Quinn | QA | Claude Sonnet | `agents/qa-engineer.md` |
| 9 | **Tech Writer** | Tom | Technical Writer | Claude Sonnet | `agents/tech-writer.md` |
| 10 | **Solo Dev** | Barry | Quick Flow Dev | Kimi Code | `agents/solo-dev.md` |

---

## 3. Database Schema

### 3.1 Core Tables

```sql
-- Tasks: งานย่อย
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    project_id TEXT NOT NULL,  -- MANDATORY
    assignee_id TEXT,
    status TEXT DEFAULT 'todo' 
        CHECK (status IN ('backlog', 'todo', 'in_progress', 'review', 'done', 'blocked', 'cancelled')),
    blocked_reason TEXT,
    priority TEXT DEFAULT 'normal',
    progress INTEGER DEFAULT 0,
    estimated_hours REAL,
    actual_hours REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    started_at DATETIME,
    completed_at DATETIME,
    due_date DATETIME,
    updated_at DATETIME,
    blocked_by TEXT,
    notes TEXT,
    actual_duration_minutes INTEGER,
    fix_loop_count INTEGER DEFAULT 0,
    -- NEW: Required fields for task quality
    prerequisites TEXT,          -- MANDATORY
    acceptance_criteria TEXT,    -- MANDATORY
    expected_outcome TEXT        -- MANDATORY
);

-- Agents: ข้อมูลสมาชิกทีม AI
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
    health_status TEXT DEFAULT 'unknown',
    last_alert_sent DATETIME,
    last_alert_type TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Agent Context: ความจำและบริบทของแต่ละ agent (เหมือน CLAUDE.md)
CREATE TABLE agent_context (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL UNIQUE,
    context TEXT NOT NULL DEFAULT '',
    learnings TEXT DEFAULT '',
    preferences TEXT DEFAULT '',
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Agent Working Memory: WORKING.md ของแต่ละ agent
CREATE TABLE agent_working_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    current_task_id TEXT,
    working_notes TEXT DEFAULT '',
    blockers TEXT DEFAULT '',
    next_steps TEXT DEFAULT '',
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Inter-Agent Communication: @mentions, threads
CREATE TABLE agent_communications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_agent_id TEXT NOT NULL,
    to_agent_id TEXT,
    task_id TEXT,
    message TEXT NOT NULL,
    message_type TEXT DEFAULT 'comment' 
        CHECK (message_type IN ('comment', 'mention', 'request', 'response')),
    is_read BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Orchestrator Missions: High-level goals
CREATE TABLE orchestrator_missions (
    id TEXT PRIMARY KEY,
    goal_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    expected_outcome TEXT,
    status TEXT DEFAULT 'planning' 
        CHECK (status IN ('planning', 'ready', 'executing', 'reviewing', 'completed', 'failed')),
    orchestration_plan TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    started_at DATETIME,
    completed_at DATETIME,
    orchestrator_agent TEXT DEFAULT 'architect'
);
```

---

## 4. Cron Jobs (Automated Monitoring)

| Job | Schedule | Purpose |
|-----|----------|---------|
| **AI Team Health Monitor** | ทุก 5 นาที | ตรวจสอบ Agent เงียบ/ค้าง |
| **AI Team Auto-Assign** | ทุก 10 นาที | Auto-assign งานให้ agents |
| **AI Team Memory Maintenance** | ทุกชั่วโมง | อัพเดต learnings + reset stale |
| **Obsidian Vault Maintenance** | ทุก 4 ชั่วโมง | ดูแล vault |
| **Bills Dashboard** | 00:10 ทุกวัน | อัพเดตรายการจ่าย |
| **Missing Data Reminder** | 09:00 ทุกวัน | แจ้งเตือนรายการค้าง |

---

## 5. Alert Response Workflow (Section 13)

### 5.1 Alert Types และ Response

| Alert Type | เงื่อนไข | การตอบสนองอัตโนมัติ |
|------------|----------|---------------------|
| **Agent Stuck** | Task in_progress > 2h ไม่มี progress | 1. ตรวจสอบ subagent session<br>2. ถ้าค้าง → unblock task, reset agent เป็น idle<br>3. รี(assign) ให้ agent อื่นหรือให้ agent เดิมเริ่มใหม่ |
| **Agent Offline** | Heartbeat หาย > 60 min | 1. ตั้ง agent status = offline<br>2. ย้ายงานที่กำลังทำ → ให้ agent อื่น<br>3. Log ว่า agent offline |
| **Task Stuck** | In progress > 2h ไม่มี progress update | 1. ตรวจสอบว่าเป็น subagent หรือไม่<br>2. ถ้า subagent ค้าง → kill session<br>3. Block task + ปล่อย agent<br>4. รอผู้ใช้ตัดสินใจ |
| **Fix Loop Exceeded** | Fix attempts > 10 | 1. Block task<br>2. ปล่อย agent เป็น idle<br>3. แจ้งผู้ใช้พร้อมเหตุผล |
| **Long-running Session** | Session > 3 ชั่วโมง | 1. Kill session<br>2. Block task<br>3. Reset agent to idle<br>4. แจ้ง Telegram |

### 5.2 Auto-Fix Script

```python
# health_monitor.py --auto-fix
# 1. Check for long-running sessions
# 2. Block tasks > 3 hours
# 3. Reset agents to idle
# 4. Send notification
```

---

## 6. Validation & Quality Gates

### 6.1 Task Creation Validation (MANDATORY)

```python
# All tasks MUST have:
- project_id          # ทุก task ต้องมี project
- expected_outcome    # ผลลัพธ์ที่คาดหวัง
- prerequisites       # สิ่งที่ต้องเตรียมก่อน
- acceptance_criteria # วิธีตรวจสอบความสำเร็จ

# ถ้าขาดจะ raise ValueError
```

### 6.2 Task Validator

```bash
# ตรวจสอบทุก task ก่อนเริ่มงาน
python3 validate_tasks.py

# ผลลัพธ์:
# ✅ All tasks valid  หรือ
# ❌ X tasks missing required fields
```

---

## 7. Key Files

| File | Purpose |
|------|---------|
| `team_db.py` | CLI management tool |
| `dashboard.php` | Web dashboard |
| `health_monitor.py` | Health monitoring |
| `auto_assign.py` | Auto-assign with context |
| `memory_maintenance.py` | Memory maintenance |
| `orchestrator.py` | Mission orchestration |
| `validate_tasks.py` | Task validation |

---

## 8. Recent Changes (v3.5.0)

### 8.1 Added (2026-02-03)
- ✅ Task Quality Framework - Required fields validation
- ✅ Agent Working Memory - WORKING.md per agent
- ✅ Inter-Agent Communication - @mentions, threads
- ✅ Orchestrator System - Autonomous mission management
- ✅ Auto-Fix Workflow - Handle long-running sessions
- ✅ Task Validator - Pre-execution validation

### 8.2 Fixed
- ✅ Dashboard checklist rendering
- ✅ Expected outcome display in modal
- ✅ Auto-assign action name (assigned vs auto_assigned)

---

## 9. Usage Examples

### Create Task (with required fields)
```bash
python3 team_db.py task create "Implement Feature X" \
  --project PROJ-001 \
  --expected-outcome "Users can do X with Y result" \
  --prerequisites "- [ ] API ready\n- [ ] Design approved" \
  --acceptance "- [ ] Feature works\n- [ ] Tests pass"
```

### Submit Goal to Orchestrator
```bash
python3 orchestrator.py goal feature \
  "Nurse Schedule System" \
  --outcome "Complete scheduling system" \
  --desc "Calendar view, filters, mobile support"
```

### Validate All Tasks
```bash
python3 validate_tasks.py
```

### Check Agent Working Memory
```bash
python3 team_db.py agent memory show <agent_id>
```

### Send Message Between Agents
```bash
python3 team_db.py agent comm send <from_agent> "Message" \
  --to <to_agent> --task <task_id>
```

---

**Last Updated:** 2026-02-03  
**Maintainer:** Orchestrator Agent  
**Next Review:** 2026-03-03
