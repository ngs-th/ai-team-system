# 🤖 AI Team System

**Version:** 3.4.4  
**Created:** 2026-02-01  
**Updated:** 2026-02-02  
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
13. [Version History](#13-version-history)

---

## 1. Overview

เอกสารนี้เป็น **Single Source of Truth** สำหรับระบบ AI Team ของ OpenClaw ประกอบด้วย:

- **10 Agents** ที่มีบทบาทและความรับผิดชอบชัดเจน
- **4 Workflow Patterns** สำหรับสถานการณ์ต่าง ๆ
- **Centralized Database (team.db)** สำหรับจัดการ tasks, agents, projects
- **Quality Gates** เพื่อรับรองคุณภาพงาน
- **Timeout & Fallback Systems** สำหรับ handle failure scenarios
- **Cron Monitoring System** สำหรับติดตามสถานะอัตโนมัติและแจ้งเตือน

---

## 2. Agent Roster

| # | Agent | ชื่อ | บทบาท | Model | ไฟล์ config |
|---|-------|------|-------|-------|-------------|
| 1 | **Orchestrator** | Master | ประสานงานหลัก | kimi-for-coding | - |
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

## 3. Decision Matrix

### 3.1 Choosing the Right Pattern

| Criteria | Full Team | Dev Team | Quick Fix | Design First |
|----------|-----------|----------|-----------|--------------|
| **Duration** | >3 days | 1-3 days | <2 hours | 2-5 days |
| **Agents Needed** | >3 agents | 2-3 agents | 1 agent | 3-4 agents |
| **Complexity** | High | Medium | Low | Medium-High |
| **Scope** | New architecture, major feature | Feature development | Bug fixes, minor tweaks | New user-facing feature |
| **Primary Focus** | End-to-end delivery | Implementation | Rapid resolution | UX/UI experience |
| **Documentation** | Full docs required | Basic docs | Minimal/none | Design specs required |
| **QA Required** | Full regression | Feature testing | Smoke test | UX validation |

### 3.2 Quick Decision Tree

```
Is it a UI/UX primary concern?
├── YES → Design First Pattern
└── NO → Estimate time needed
    ├── <2 hours → Quick Fix (Solo Dev)
    ├── 1-3 days → Dev Team Pattern
    └── >3 days → Full Team Pattern
```

### 3.3 Pattern Selection Examples

| Scenario | Recommended Pattern | Rationale |
|----------|---------------------|-----------|
| Database schema redesign | Full Team | High complexity, affects multiple systems |
| Add new API endpoint | Dev Team | Medium complexity, focused scope |
| Fix typo in error message | Quick Fix | <5 min task, single file change |
| Redesign checkout flow | Design First | UX is primary concern |
| New microservice implementation | Full Team | New architecture, >3 days work |
| Update dashboard filters | Dev Team | Feature enhancement, 1-2 days |

---

## 4. Workflow Patterns

### 4.1 Pattern 1: Full Team (Complex Projects)

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│   👤    │────▶│   🎛️    │────▶│   📋    │────▶│   📊    │
│  User   │     │Orchestrator│   │   PM    │     │ Analyst │
└─────────┘     └─────────┘     └────┬────┘     └────┬────┘
     ▲                               │               │
     │                               ▼               ▼
     │                          ┌─────────┐     ┌─────────┐
     │                          │   🏗️    │◀────│   🎨    │
     │                          │Architect│     │  UX     │
     │                          └────┬────┘     └─────────┘
     │                               │
     │                               ▼
     │                          ┌─────────┐     ┌─────────┐
     │                          │   💻    │────▶│   🧪    │
     │                          │   Dev   │     │   QA    │
     │                          └────┬────┘     └────┬────┘
     │                               │               │
     │                               ▼               ▼
     │                          ┌─────────┐     ┌─────────┐
     │                          │   📝    │────▶│  Done   │
     │                          │ Writer  │     │         │
     │                          └─────────┘     └────┬────┘
     │                                               │
     └───────────────────────────────────────────────┘
```

**ใช้เมื่อ:** โปรเจคใหญ่ ต้องการทีมครบ  
**ระยะเวลา:** หลายวัน-หลายสัปดาห์  
**Scrum Master:** ประสานงานตลอด

---

### 4.2 Pattern 2: Dev Team (Feature Development)

```
👤 ──▶ 🎛️ ──▶ 🏗️ ──▶ 💻 ──▶ 🧪 ──▶ ✅ ──▶ 👤
User    Orchestrator   Architect   Dev   QA   Done   User
                              │
                              ▼
                            📝 (Tech Writer - optional)
```

**ใช้เมื่อ:** พัฒนาฟีเจอร์ใหม่  
**ระยะเวลา:** 1-3 วัน

---

### 4.3 Pattern 3: Quick Fix (Emergency)

```
👤 ──▶ 🎛️ ──▶ 🚀 ──▶ ✅ ──▶ 👤
User    Orchestrator  Solo Dev  Done   User
```

**ใช้เมื่อ:** แก้บั๊กด่วน งานเล็ก  
**ระยะเวลา:** < 2 ชั่วโมง

---

### 4.4 Pattern 4: Design First (UI/UX Focus)

```
👤 ──▶ 🎛️ ──▶ 📊 ──▶ 🎨 ──▶ 🏗️ ──▶ 💻 ──▶ 🧪 ──▶ 👤
     Orchestrator  Analyst   UX     Architect  Dev   QA
```

**ใช้เมื่อ:** ออกแบบ UI/UX เป็นหลัก  
**ระยะเวลา:** 2-5 วัน

---

### 4.5 How to Use

#### วิธีที่ 1: สั่งผ่าน Orchestrator

| คำสั่ง | Agent ที่ถูกส่ง | งาน |
|--------|----------------|-----|
| "ส่ง PM ไป..." | PM (John) | วางแผนโปรดักต์ |
| "ให้ Analyst..." | Analyst (Mary) | วิเคราะห์ความต้องการ |
| "Architect..." | Architect (Winston) | ออกแบบระบบ |
| "Dev ทำ..." | Dev (Amelia) | พัฒนา |
| "QA ทดสอบ..." | QA (Quinn) | ทดสอบ |
| "แก้ด่วน" | Solo Dev (Barry) | แก้ไขด่วน |

#### วิธีที่ 2: Spawn Agent โดยตรง

```bash
./agents/spawn-agent.sh <agent-type> "<task>"

# ตัวอย่าง:
./agents/spawn-agent.sh pm "วางแผน roadmap Q1"
./agents/spawn-agent.sh analyst "วิเคราะห์ requirements"
./agents/spawn-agent.sh architect "ออกแบบ database"
./agents/spawn-agent.sh dev "Implement login"
./agents/spawn-agent.sh ux-designer "ออกแบบ dashboard"
./agents/spawn-agent.sh qa "ทดสอบ payment"
./agents/spawn-agent.sh tech-writer "เขียน API docs"
./agents/spawn-agent.sh solo-dev "Quick fix bug"
```

---

## 5. Database System (team.db)

### 5.1 Overview

**team.db** เป็น **Single Source of Truth** สำหรับข้อมูลทั้งหมดของ AI Team:

| สิ่งที่เก็บ | ไฟล์/ระบบ | ลักษณะ |
|------------|----------|--------|
| Tasks, Agents, Projects, History | **team.db** | Structured, queryable, persistent |
| Daily logs, detailed outputs | `memory/*.md` | Unstructured, narrative |
| Agent configs | `agents/*.md` | Static configuration |
| Shared context | `team-context.md` | Current session context |

**Location:** `~/clawd/memory/team/team.db`  
**CLI Tool:** `~/clawd/projects/ai-team/team_db.py`  
**Dashboard:** `~/clawd/projects/ai-team/dashboard.php`

---

### 5.2 Database Schema

#### Core Tables

```sql
-- Agents: ข้อมูลสมาชิกทีม AI
CREATE TABLE agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    model TEXT,
    status TEXT DEFAULT 'idle' 
        CHECK (status IN ('idle', 'active', 'blocked', 'offline')),
    current_task_id TEXT,
    last_heartbeat DATETIME,
    total_tasks_completed INTEGER DEFAULT 0,
    total_tasks_assigned INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (current_task_id) REFERENCES tasks(id) ON DELETE SET NULL
);

-- Projects: โครงการ/Project
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'planning' 
        CHECK (status IN ('planning', 'active', 'paused', 'completed', 'cancelled')),
    start_date DATE,
    end_date DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tasks: งานย่อย
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    project_id TEXT NOT NULL,  -- ⚠️ MANDATORY: Every task must have a project
    assignee_id TEXT,
    status TEXT DEFAULT 'todo' 
        CHECK (status IN ('todo', 'in_progress', 'review', 'done', 'blocked', 'cancelled')),
    blocked_reason TEXT,  -- เหตุผลที่ถูก block (fix-loop-exceeded, info-required, etc.)
    priority TEXT DEFAULT 'normal' 
        CHECK (priority IN ('critical', 'high', 'normal', 'low')),
    progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    estimated_hours REAL,
    actual_duration_minutes INTEGER,  -- ระยะเวลาที่ใช้จริง (นาที) คำนวณจาก started_at -> completed_at
    fix_loop_count INTEGER DEFAULT 0,  -- จำนวนรอบแก้ไข (สำหรับ auto-fix tracking)
    actual_hours REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    started_at DATETIME,
    completed_at DATETIME,
    due_date DATETIME,
    blocked_by TEXT,
    notes TEXT,
    updated_at DATETIME,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL,
    FOREIGN KEY (assignee_id) REFERENCES agents(id) ON DELETE SET NULL
);

-- Task Dependencies: ความสัมพันธ์ระหว่างงาน
CREATE TABLE task_dependencies (
    task_id TEXT NOT NULL,
    depends_on_task_id TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (task_id, depends_on_task_id),
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (depends_on_task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

-- Task History: Audit log
CREATE TABLE task_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    agent_id TEXT,
    action TEXT NOT NULL 
        CHECK (action IN ('created', 'assigned', 'started', 'updated', 
                         'completed', 'blocked', 'unblocked', 'cancelled')),
    old_status TEXT,
    new_status TEXT,
    old_progress INTEGER,
    new_progress INTEGER,
    notes TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE SET NULL
);
```

#### Views (for Dashboard)

| View | Description |
|------|-------------|
| `v_agent_workload` | ภาระงานแต่ละ agent (active tasks, progress, completed count) |
| `v_project_status` | สถานะโครงการ (progress %, task counts by status) |
| `v_task_summary` | สรุปงานพร้อม urgency flag (overdue/due today/on track) |
| `v_dashboard_stats` | ตัวเลขรวมทั้งหมด (counts for dashboard cards) |

---

### 5.3 Data Flow & State Machine

#### Task Lifecycle

```
Created (via Orchestrator/PM)
    │
    ▼
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  todo   │───▶│in_prog  │───▶│ review  │───▶│  done   │
│         │    │         │    │         │    │         │
└────┬────┘    └────┬────┘    └────┬────┘    └─────────┘
     │              │              │
     │              ▼              │
     │         ┌─────────┐         │
     └────────▶│ blocked │◀────────┘
               │         │
               └────┬────┘
                    │
                    ▼
               ┌─────────┐
               │cancelled│
               └─────────┘
```

**Status Transitions:**

| From | To | Triggered By | Who Can Do |
|------|-----|--------------|------------|
| todo | in_progress | Agent starts work | Assigned Agent |
| in_progress | review | Implementation complete | Dev |
| review | done | QA approves | QA |
| review | in_progress | QA finds issues | QA |
| any | blocked | Blocker identified | Any Agent |
| blocked | in_progress | Blocker resolved | Orchestrator/PM |
| any | cancelled | Scope changed | PM |

---

### 5.4 Agent-Database Contract

แต่ละ Agent มี **หน้าที่** ในการอัพเดต database ดังนี้:

#### Orchestrator (Master)

| Action | DB Operation | When |
|--------|-------------|------|
| Create project | `INSERT INTO projects` | New project starts |
| Create task | `INSERT INTO tasks` | Spawn task for agent (MUST include project_id) |
| Assign task | `UPDATE tasks SET assignee_id` | Assign to agent |
| Monitor | `SELECT * FROM v_dashboard_stats` | Periodic check |
| Escalate | `UPDATE tasks SET status = 'blocked'` | Issue detected |

#### PM (John)

| Action | DB Operation | When |
|--------|-------------|------|
| Update project | `UPDATE projects SET status` | Project phase change |
| Set priority | `UPDATE tasks SET priority` | Prioritize tasks |
| Set deadline | `UPDATE tasks SET due_date` | Set timeline |
| Report | Generate from views | Daily standup |

#### Dev (Amelia)

| Action | DB Operation | When |
|--------|-------------|------|
| Start task | `UPDATE tasks SET status = 'in_progress'` | Begin work |
| Update progress | `UPDATE tasks SET progress` | Every checkpoint |
| Complete | `UPDATE tasks SET status = 'review'` | Code ready |
| Log hours | `UPDATE tasks SET actual_hours` | Task done |

#### QA (Quinn)

| Action | DB Operation | When |
|--------|-------------|------|
| Approve | `UPDATE tasks SET status = 'done'` | Tests pass |
| Reject | `UPDATE tasks SET status = 'in_progress'` | Issues found |
| Block | `UPDATE tasks SET status = 'blocked'` | Critical bug |

#### All Agents

| Action | DB Operation | When |
|--------|-------------|------|
| Heartbeat | `UPDATE agents SET last_heartbeat` | Every 10 min |
| Update status | `UPDATE agents SET status` | State change |

#### Orchestrator (Block Handling)

| Action | DB Operation | When |
|--------|-------------|------|
| Block task | `UPDATE tasks SET status = 'blocked', blocked_reason = ?` | Fix loop > 10, info needed |
| Release agent | `UPDATE agents SET status = 'idle', current_task_id = NULL` | After task blocked |
| Reassign | `UPDATE tasks SET assignee_id = ?` | Assign new task to idle agent |

---

### 5.4a Validation Rules (MANDATORY)

#### Rule 1: Every Task Must Have Project
```
❌ INVALID: INSERT INTO tasks (title) VALUES ('Task name')
✅ VALID:   INSERT INTO tasks (title, project_id) VALUES ('Task name', 'PROJ-001')

Error if project_id is NULL: "ERROR: Every task must have a project"
```

**Check before creating task:**
```python
if not project_id:
    raise ValueError("project_id is required - every task must belong to a project")
```

#### Rule 2: Task ID Format (MANDATORY)

**Format:** `T-YYYYMMDD-NNN`

| Component | Description | Example |
|-----------|-------------|---------|
| `T` | Task prefix | T |
| `YYYYMMDD` | Date (4-digit year, 2-digit month, 2-digit day) | 20260202 |
| `NNN` | Sequence number (3 digits, leading zeros) | 001, 012, 123 |

**Valid Examples:**
- ✅ `T-20260202-001` (Jan 1st task)
- ✅ `T-20260202-012` (12th task of the day)
- ✅ `T-20260202-123` (123rd task of the day)

**Invalid Examples:**
- ❌ `T-20260202-1` (missing leading zeros)
- ❌ `T-20260202-01` (only 2 digits)
- ❌ `T-20260202-24` (missing leading zero)
- ❌ `Task-001` (wrong prefix)
- ❌ `20260202-001` (missing T prefix)

**Enforcement:**
```python
# In team_db.py - auto-generated with :03d format
task_id = f"T-{datetime.now().strftime('%Y%m%d')}-{self._get_next_task_number():03d}"
# Result: T-20260202-001 (always 3 digits)
```

---

### 5.5 CLI Usage

```bash
cd ~/clawd/projects/ai-team

# Task Management
python3 team_db.py task create "Implement login" --assign amelia --priority high --due 2026-02-05
python3 team_db.py task list --status in_progress
python3 team_db.py task assign T-20260202-001 amelia
python3 team_db.py task start T-20260202-001
python3 team_db.py task progress T-20260202-001 50 --notes "API done, UI in progress"
python3 team_db.py task done T-20260202-001
python3 team_db.py task block T-20260202-001 "Waiting for API key"

# Agent Management
python3 team_db.py agent list
python3 team_db.py agent heartbeat amelia

# Dashboard Stats
python3 team_db.py dashboard

# Reports
python3 team_db.py report --daily
```

---

### 5.6 Data vs Memory Boundaries

| Use Case | Store In | Example |
|----------|----------|---------|
| Task status, assignments | **team.db** | "Task T-001 assigned to Dev" |
| Progress percentage | **team.db** | "Progress: 75%" |
| Agent workload stats | **team.db** | "Dev has 3 active tasks" |
| Detailed implementation notes | `memory/*.md` | "Used React hook pattern because..." |
| Code snippets, logs | `memory/*.md` | Error logs, code examples |
| Decision rationale | `memory/*.md` | "Chose PostgreSQL over MySQL because..." |
| Current session context | `team-context.md` | "Working on feature X, waiting for Y" |

**Rule of Thumb:**
- **team.db** = ข้อมูลที่ต้อง query, aggregate, report ได้
- **memory/*.md** = รายละเอียดเชิงลึกที่อ่านเป็นบทความ

---

## 5.7 Autonomous Fix Protocol (NEW)

**Rule:** Orchestrator **MUST** autonomously fix ALL issues until none remain. **DO NOT ASK** user for permission to fix.

### Auto-Fix Loop (แก้ไขวนไปจนกว่าจะไม่มีปัญหา)

```
Agent: "✅ Task complete. Delivered: [files]"
    │
    ▼
┌─────────────────────────────┐
│  Orchestrator (Auto-check)  │
│                             │
│  1. ตรวจสอบผลงาน            │
│  2. พบปัญหา?                │
│     ├── YES → แก้ไขทันที    │
│     │        ↓              │
│     │      (วนกลับไป 1)     │
│     │                       │
│     └── NO  → อัพเดต done   │
└─────────────────────────────┘
```

### Fix Until Clean

**หลักการ:** แก้ไขซ้ำไปเรื่อยๆ จนกว่าจะไม่พบปัญหา

| รอบ | พบปัญหา | การกระทำ |
|-----|---------|----------|
| 1 | Path ผิด, ชื่อไฟล์ผิด | ย้าย + Rename |
| 2 | ขาด import, syntax error | เพิ่ม import, fix syntax |
| 3 | Test fail | แก้ code ตาม test |
| 4 | Lint error | จัด format |
| 5 | (ไม่มีปัญหา) | ✅ Done |

**คำสั่งตัวเอง:** "Fix it again. And again. Until clean."

### ⚠️ MANDATORY: Test Before Marking Complete

**Agents MUST test before reporting "complete":**

```
Before: "✅ Task complete"
        ↓
   1. Syntax check (php -l, etc.)
   2. Database query check (if applicable)
   3. Basic functionality test
   4. Check for obvious errors
        ↓
After: Confirm working → "✅ Task complete"
```

**Testing Checklist:**
- [ ] **Syntax Validation**: `php -l file.php`, `python -m py_compile file.py`
- [ ] **Database Check**: ตรวจสอบ columns ที่ใช้มีจริง
- [ ] **Query Test**: รัน SQL query ที่เขียน
- [ ] **File Existence**: ตรวจสอบไฟล์ที่อ้างอิงมีจริง
- [ ] **Basic Run**: ถ้าเป็น web → เปิดดู; ถ้าเป็น script → รันทดสอบ

**Example Error (ที่ต้องจับได้):**
```
❌ Bad:  Query uses a.avatar_url (column doesn't exist)
✅ Good: Test query first → Find error → Fix → Then report complete
```

**If test fails:**
1. Fix the issue (don't report complete yet)
2. Test again
3. Only report complete when tests pass

### Auto-Fix Categories (แก้ได้ทันที)

| หมวด | ตัวอย่าง | แก้ไข |
|------|---------|--------|
| **Path/File** | อยู่ผิดที่, ชื่อผิด | ย้าย, rename |
| **Code** | Syntax error, missing import | Fix, add import |
| **Config** | ขาด config, env | เพิ่มตาม template |
| **Test** | Test fail, no coverage | แก้ code, เพิ่ม test |
| **Lint** | Format ผิด, style | Auto-fix lint |
| **Doc** | ขาด README, type | Generate, add |

### When to STOP and ASK (หยุดเมื่อ)

หยุดแก้อัตโนมัติ และถามผู้ใช้เมื่อ:
- **ไม่รู้ว่าต้องแก้ยังไง** (ไม่เข้าใจ error)
- **แก้แล้วพัง** (fix นึงทำให้เกิดปัญหาใหม่)
- **วนลูป > 10 รอบ** (hard limit) → เปลี่ยน status เป็น **blocked**
- **ต้องตัดสินใจเรื่อง design/architecture**
- **ต้องการข้อมูลเพิ่มเติม** จาก user → เปลี่ยน status เป็น **blocked**

### Safety Limit: 10 Fix Rounds

```
รอบที่ 1-5:  แก้ไขตามปกติ
รอบที่ 6-9:  แจ้งเตือน Telegram "⚠️ Fix loop warning: X rounds"
รอบที่ 10:   STOP → แจ้ง Telegram → เปลี่ยน status เป็น blocked
```

### Blocked Status Usage

**⚠️ IMPORTANT: Block the TASK, not the AGENT**

```
When task needs to be blocked:
    │
    ├──> Task.status = 'blocked'
    ├──> Task.blocked_reason = '[reason]'
    ├──> Agent.status = 'idle'          <-- Agent ว่างแล้ว
    ├──> Agent.current_task_id = NULL   <-- ไม่มีงานติดตัว
    └──> Agent รับงานใหม่ได้ทันที
```

**ผลลัพธ์:** Agent ว่าง → รับงานใหม่ได้ → ไม่ waste resource

| สถานการณ์ | Task | Agent | blocked_reason |
|-----------|------|-------|----------------|
| วนลูปแก้ไข > 10 รอบ | blocked | idle | fix-loop-exceeded |
| ต้องการข้อมูลเพิ่ม | blocked | idle | info-required |
| ไม่เข้าใจ requirements | blocked | idle | unclear-requirements |
| ต้องตัดสินใจ design | blocked | idle | needs-design-decision |

### Agent Reassignment After Block

```
Task T-001 (blocked) ──> Agent A หลุด (idle)
                              │
                              ▼
                    รับ Task T-002 ใหม่ทันที
```

**อย่าทำแบบนี้:**
```
❌ ผิด: Agent.status = 'blocked'  (Agent ติดๆ ไม่ทำงาน)
```

**ทำแบบนี้:**
```
✅ ถูก: Task.status = 'blocked'   (งานติด, คนไม่ติด)
       Agent.status = 'idle'     (คนว่าง ไปทำงานอื่น)
```

### Telegram Notifications (MANDATORY)

**ส่งข้อความไป Telegram เมื่อมีการเปลี่ยนแปลงใดๆ:**

#### Task Created (สร้างงานใหม่)
| เหตุการณ์ | ข้อความ |
|-----------|----------|
| Task ถูกสร้าง | 🆕 Task #XXX: [ชื่อ] ถูกสร้างแล้ว (Assignee: [Agent]) |

#### EVERY Status Change (ทุกการเปลี่ยน status)
| จาก | เป็น | ข้อความ |
|------|------|----------|
| todo | in_progress | 🚀 Task #XXX เริ่มทำแล้ว (Agent) |
| in_progress | review | 👀 Task #XXX ส่งรีวิว |
| review | done | ✅ Task #XXX เสร็จสมบูรณ์ |
| any | blocked | 🚫 Task #XXX ถูก block (เหตุผล) |
| blocked | in_progress | 🔄 Task #XXX กลับมาทำต่อ |

#### Other Events
- ⚠️ Fix loop ครบ 5, 8, 10 รอบ
- 📊 สรุปรายวัน

**Rule:** ทุกการสร้าง task และทุกการเปลี่ยน status ต้องแจ้ง Telegram ทันที ไม่มีข้อยกเว้น

### Example

**Before (Ask):**
```
Agent: "เสร็จแล้ว แต่ไฟล์อยู่ผิดที่"
User: "ย้ายไปให้ถูกสิ"
Agent: "ย้ายแล้ว"
```

**After (Auto-fix):**
```
Agent: "เสร็จแล้ว แต่ไฟล์อยู่ผิดที่"
Orchestrator: "[Auto-fix] ย้ายไฟล์ไป [correct-path] แล้ว"
```

---

## 6. Quality Gates

### 6.1 Gate Definitions

| Gate | From | To | Pass Criteria | Validator |
|------|------|-----|---------------|-----------|
| **G1: Requirements** | User | PM | Problem statement clear, success criteria defined | Orchestrator |
| **G2: Analysis** | PM | Analyst | PRD approved, user stories written | PM |
| **G3: Design** | Analyst | Architect/UX | Requirements validated, edge cases documented | Analyst |
| **G4: Architecture** | Architect | Dev | Tech spec approved, API contracts defined | Architect + PM |
| **G5: UX Ready** | UX | Dev | Mockups approved, accessibility checked | UX + PM |
| **G6: Implementation** | Dev | QA | Code complete, unit tests pass | Dev |
| **G7: Testing** | QA | Release | All tests pass, no critical bugs | QA |
| **G8: Documentation** | Writer | Release | Docs complete, examples working | Tech Writer |

### 6.2 Gate Checklist Templates

#### G4: Architecture Gate
- [ ] Tech spec document written
- [ ] Database schema defined
- [ ] API contracts documented
- [ ] Security considerations addressed
- [ ] Performance requirements specified
- [ ] Reviewed and approved by PM

#### G6: Implementation Gate
- [ ] Feature implemented per spec
- [ ] Unit tests written (>80% coverage)
- [ ] Code linting passes
- [ ] Self-tested by developer
- [ ] PR created

#### G7: Testing Gate
- [ ] Functional tests pass
- [ ] Edge cases tested
- [ ] Regression suite pass
- [ ] Bug reports documented

### 6.3 Gate Failure Handling

| Failure Type | Action | Responsible |
|--------------|--------|-------------|
| Missing documentation | Return to previous agent | Orchestrator |
| Code quality issues | Return to Dev | QA |
| Scope creep | PM review required | Orchestrator |

---

## 7. Timeout & Fallback

### 7.1 Timeout Specifications

| Agent | Task Type | Soft Timeout | Hard Timeout | Action on Timeout |
|-------|-----------|--------------|--------------|-------------------|
| **PM** | Planning | 30 min | 45 min | Escalate to Architect |
| **PM** | PRD writing | 2 hours | 3 hours | Review scope |
| **Analyst** | Requirements | 1 hour | 1.5 hours | Escalate to PM |
| **Architect** | System design | 2 hours | 3 hours | Review with PM |
| **Dev** | Implementation | 4 hours | 6 hours | Split task |
| **Dev** | Debugging | 1 hour | 2 hours | Escalate to Architect |
| **UX** | Design | 2 hours | 3 hours | Review scope |
| **QA** | Testing | 2 hours | 3 hours | Reduce scope |
| **Solo Dev** | Any task | 1 hour | 1 hour | Auto-escalate |

### 7.2 Fallback Procedures

#### Agent Silent (>15 min)
```
1. T+15 min: Send heartbeat ping
2. T+20 min: Check memory for last checkpoint
3. T+25 min: Attempt graceful termination
4. T+30 min: Force kill, spawn replacement
```

#### Quality Gate Failure
```
1. Document specific failures
2. Return to previous agent with feedback
3. Allow 1 retry
4. If still failing → Escalate to PM + Architect
```

#### Technical Blocker
```
1. Dev flags blocker in checkpoint
2. Orchestrator spawns Architect
3. Architect reviews within 30 min
4. If unresolved in 1 hour → Escalate to PM
```

---

## 8. Resource Guidelines

### 8.1 Token Budget by Agent

| Agent/Task | Context | Working Budget | Max Output |
|------------|---------|----------------|------------|
| PM - Planning | 200K | 100K | 8K |
| PM - PRD Writing | 200K | 120K | 16K |
| Architect - Design | 200K | 140K | 16K |
| Dev - Implementation | 200K | 100K | 16K |
| Dev - Debugging | 200K | 80K | 4K |
| QA - Testing | 200K | 100K | 8K |
| Tech Writer | 200K | 100K | 16K |
| Solo Dev | 200K | 60K | 8K |

### 8.2 Model Recommendations

| Task Category | Primary | Fallback |
|---------------|---------|----------|
| Strategic Planning | Claude Opus | Claude Sonnet |
| System Architecture | Claude Opus | Claude Sonnet |
| Code Implementation | Kimi Code | Claude Sonnet |
| UX/UI Design | Claude Sonnet | Claude Opus |
| Testing/QA | Claude Sonnet | Claude Haiku |
| Documentation | Claude Sonnet | Claude Haiku |
| Quick Tasks | Claude Haiku | Claude Sonnet |

---

## 9. Communication Protocol

### 9.1 Language Policy
- **สื่อสารกับผู้ใช้:** ภาษาไทย
- **ข้อมูลใน code blocks:** ภาษาอังกฤษ (tables, data)

### 9.2 Status Format
```
[Agent Name]: [Status] - [Message]

Example:
PM John: Starting - วิเคราะห์ requirements
Dev Amelia: Progress - ทำส่วน authentication เสร็จแล้ว
QA Quinn: Done - ผ่านการทดสอบทั้งหมด
```

### 9.3 Decision Summary

| Command | Action |
|---------|--------|
| "ทำงานนี้" (ไม่ระบุ Agent) | Orchestrator เลือก Agent ที่เหมาะสม |
| "ส่ง [Agent] ไป..." | ส่งงานให้ Agent นั้นโดยเฉพาะ |
| "แก้ด่วน" / "quick fix" | ใช้ Solo Dev (Barry) |
| "งานใหญ่" / "โปรเจคใหม่" | ประสานทีมเต็มรูปแบบ |

---

## 10. Tools Reference

| Tool | Primary Users | Purpose |
|------|---------------|---------|
| `sessions_spawn` | Orchestrator | Spawn agents |
| `memory_search` | All Agents | Recall past work |
| `memory_get` | All Agents | Read specific memories |
| `write` | All Agents | Save outputs |
| `read` | All Agents | Load files |
| `exec` | Dev, QA | Run commands |
| `browser` | QA, UX, Dev | Web testing |
| `web_search` | Planning | Research |
| `cron` | Orchestrator | Scheduled tasks |
| `message` | Orchestrator | Notifications |

---

## 12. Dashboard (Kanban)

### 12.1 Kanban Board View

Dashboard แสดงผลแบบ **Kanban Board** แทนตาราง:

```
┌─────────────┬─────────────┬─────────────┬─────────────┬─────────────┐
│    TODO     │ IN PROGRESS │   REVIEW    │    DONE     │   BLOCKED   │
├─────────────┼─────────────┼─────────────┼─────────────┼─────────────┤
│ 📝 Task A   │ 🔄 Task B   │ 👀 Task C   │ ✅ Task D   │ 🚧 Task E   │
│ 🔴 Critical │ 🟠 High     │ 🟡 Normal   │             │ ⚠️ Loop >10 │
│ 📅 Due: 2d  │ ⏱️ 2h 30m   │             │             │ ❓ Info needed│
├─────────────┼─────────────┼─────────────┼─────────────┼─────────────┤
│ 📝 Task F   │ 🔄 Task G   │             │             │             │
│ 🟡 Normal   │ 🟠 High     │             │             │             │
│ 📅 Due: 5d  │ ⏱️ 45m      │             │             │             │
└─────────────┴─────────────┴─────────────┴─────────────┴─────────────┘
```

### 12.2 Task Card Information

แต่ละ Card แสดง:
- **ไอคอน + ชื่องาน**
- **สี Priority**: 🔴 Critical, 🟠 High, 🟡 Normal, 🟢 Low
- **Assignee Avatar**
- **Duration**: ⏱️ ระยะเวลาที่ใช้ (คำนวณจาก started_at → now/completed_at)
- **Due Date**: 📅 กำหนดส่ง
- **Blocked Reason**: ⚠️ แสดงเหตุผลถ้า status = blocked

### 12.3 Duration Tracking

| Field | Description |
|-------|-------------|
| `started_at` | เวลาเริ่มงาน (auto-set when status → in_progress) |
| `completed_at` | เวลาเสร็จ (auto-set when status → done) |
| `actual_duration_minutes` | ระยะเวลาที่ใช้จริง (auto-calculated) |

**คำนวณอัตโนมัติ:**
```
ถ้า status = done:
  duration = completed_at - started_at
ถ้า status = in_progress:
  duration = now - started_at (real-time)
```

### 12.4 Drag & Drop

- ลาก Task ไปยัง Column อื่นเพื่อเปลี่ยน status
- Auto-update database ทันที
- บันทึก history การย้าย

### 12.5 Blocked Column

แสดงเฉพาะ Task ที่ status = blocked พร้อม:
- 🔴 Red border highlight
- Blocked reason badge
- "Unblock" button (สำหรับ Orchestrator)

---

## 13. Version History

| Version | Date | Changes |
|---------|------|---------|
| **3.4.4** | 2026-02-02 | Added Task Created notification: Telegram alert when new task is created with assignee |
| **3.4.3** | 2026-02-02 | Mandatory Telegram notifications for EVERY task status change (todo→in_progress, in_progress→review, review→done, etc.) |
| **3.4.2** | 2026-02-02 | Clarified Blocked Status: Block the TASK (not the AGENT) so agent can be reassigned to other work immediately |
| **3.4.1** | 2026-02-02 | Added MANDATORY testing requirement: Agents must test (syntax, database, basic functionality) before marking tasks complete |
| **3.4.0** | 2026-02-02 | Added Kanban Dashboard, Duration Tracking, Telegram Notifications, Fix Loop Limit (10), Blocked Status with reason |
| **3.3.0** | 2026-02-02 | Enhanced Autonomous Fix Protocol: Fix ALL issues iteratively until clean (Fix Until Clean principle) |
| **3.2.0** | 2026-02-02 | Added Autonomous Fix Protocol: Orchestrator auto-fixes issues after agent reports without asking permission |
| **3.1.0** | 2026-02-02 | Added Cron Monitoring System section (active jobs, monitoring rules, alerts, reports) |
| **3.0.0** | 2026-02-02 | **Major:** Renamed to AI-TEAM-SYSTEM.md, added comprehensive Database System section (schema, data flow, agent-db contracts) |
| 2.0.0 | 2026-02-02 | Added Decision Matrix, Timeouts, Quality Gates, Fallback Plans, Resource Guidelines |
| 1.0.0 | 2026-02-01 | Initial draft based on Sengdao2 BMAD Pattern |

---

## 🔗 Related Files

### Code (Projects)
| File | Purpose |
|------|---------|
| `~/clawd/projects/ai-team/dashboard.php` | Web dashboard (PHP) |
| `~/clawd/projects/ai-team/team_db.py` | CLI management tool |
| `~/clawd/projects/ai-team/README.md` | Project documentation |

### Data (Memory)
| File | Purpose |
|------|---------|
| `~/clawd/memory/team/team.db` | Central database |
| `~/clawd/memory/team/messages.db` | Alert/message history |
| `~/clawd/memory/team/TASK-BOARD.md` | Kanban board view |
| `~/clawd/memory/team/PROJECT-STATUS.md` | Project status view |

---

## 12. Agent Memory System (Context & Learning)

ระบบความจำของ Agents แบบ persistent - เก็บ context และ learnings ใน database

### 12.1 Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Agent Memory System                 │
├─────────────────────────────────────────────────────┤
│  agent_context table                                │
│  ├── agent_id      : รหัส agent                     │
│  ├── context       : บทบาทและความเชี่ยวชาญ        │
│  ├── learnings     : สิ่งที่เรียนรู้จากงาน         │
│  ├── preferences   : การตั้งค่าส่วนตัว              │
│  └── last_updated  : เวลาอัพเดตล่าสุด               │
└─────────────────────────────────────────────────────┘
```

### 12.2 How It Works

#### Memory Flow
```
1. Auto-Assign หา Agent ที่ว่าง
        ↓
2. อ่าน Context ของ Agent จาก database
        ↓
3. ส่ง Context + Task Details ให้ Subagent
        ↓
4. Subagent ใช้ Context เป็น "ความจำ" เริ่มต้น
        ↓
5. เมื่อทำงานเสร็จ → อัพเดต Learnings
```

#### Memory Maintenance (ทุกชั่วโมง)
```
memory_maintenance.py รัน:
├── Reset stale agents (>1h ไม่มี heartbeat)
├── Update learnings จาก completed tasks
└── Archive old history (>30 วัน)
```

### 12.3 CLI Commands

```bash
# ดู context ของ agent
python3 team_db.py agent context show <agent_id>

# อัพเดต context
python3 team_db.py agent context update <agent_id> \
  --field context --content "# Role\nExpert in..."

# เพิ่ม learning
python3 team_db.py agent context learn <agent_id> \
  "Learned: Always use transactions"
```

### 12.4 Context Example

**Agent: Amelia (Developer)**
```markdown
# Developer Amelia

## Role
Full-stack developer สำหรับ Nurse AI Project

## Expertise
- Laravel/PHP
- Livewire components
- Tailwind CSS
- SQLite/MySQL

## Recent Learnings
- Completed: User authentication system
- Completed: Database migration tools
- Learned: Always validate inputs before DB operations
```

### 12.5 Benefits

| Feature | Benefit |
|---------|---------|
| **Persistent Context** | Agent จำบทบาทตัวเองได้ |
| **Learning Accumulation** | เก็บบทเรียนจากงานก่อน ๆ |
| **Auto-Cleanup** | ล้างข้อมูลเก่าอัตโนมัติ |
| **Stale Detection** | รีเซ็ต agents ที่ค้าง |

---

## 13. Cron Monitoring System

ระบบ Cron สำหรับติดตามสถานะ AI Team อัตโนมัติ แจ้งเตือนผ่าน Telegram

### Agent Configs
| File | Purpose |
|------|---------|
| `~/clawd/agents/*.md` | Individual agent configurations |

---

## 11. Cron Monitoring System

ระบบ Cron สำหรับติดตามสถานะ AI Team อัตโนมัติ แจ้งเตือนผ่าน Telegram

### 13.1 Active Cron Jobs

| Job Name | Schedule | Purpose |
|----------|----------|---------|
| **ai-team-heartbeat** | ทุก 5 นาที | ตรวจสอบ Agent เงียบ/ค้าง |
| **ai-team-auto-assign** | ทุก 10 นาที | Auto-assign งานให้ agents |
| **ai-team-memory-maint** | ทุกชั่วโมง | อัพเดต learnings + reset stale |
| **ai-team-deadlines** | ทุก 30 นาที | ตรวจสอบ deadline |
| **ai-team-hourly-report** | ทุกชั่วโมง | สรุปสถานะรายชั่วโมง |
| **ai-team-daily-morning** | 08:00 ทุกวัน | รายงานเช้า |
| **ai-team-daily-evening** | 18:00 ทุกวัน | สรุปผลงานเย็น |

### 11.2 Monitoring Rules

#### Rule 1: Agent Heartbeat Check (ทุก 5 นาที)
```python
# ตรวจสอบ Agent ที่เงียบ > 30 นาที
silent_threshold = 30 minutes
alert_condition: last_heartbeat > 30 min ago AND status = 'active'

# ตรวจสอบ Agent ที่ทำงานนานเกินไปโดยไม่มี progress
stuck_threshold = 60 minutes
alert_condition: started_at > 60 min ago AND progress unchanged
```

**Actions:**
- แจ้งเตือน Telegram: "🚨 Agent [name] silent for [X] minutes"
- Auto-ping agent
- Escalate to Orchestrator หากไม่ตอบสนอง

#### Rule 2: Deadline Check (ทุก 30 นาที)
```python
# งานที่ครบกำหนดวันนี้
check: due_date = TODAY() AND status NOT IN ('done', 'cancelled')
severity: info

# งานที่เลยกำหนด
check: due_date < TODAY() AND status NOT IN ('done', 'cancelled')
severity: warning (< 1 day), critical (> 1 day)

# งานที่ติดนานเกินไป
check: status = 'blocked' AND updated_at > 2 hours ago
severity: warning
```

**Actions:**
- แจ้งเตือน Telegram: "⏰ Task [ID] due today/overdue"
- Auto-tag PM สำหรับ overdue tasks
- สร้าง escalation สำหรับ blocked > 4 ชั่วโมง

#### Rule 3: Project Health Check (รวมใน daily report)
```python
# โปรเจคที่เสี่ยง
check: progress < 50% AND days_remaining < 3
severity: warning

# โปรเจคที่มีงานติดมาก
check: blocked_tasks > total_tasks * 0.3
severity: warning

# โปรเจคเลยกำหนด
check: end_date < TODAY()
severity: critical
```

### 11.3 Report Types

#### Hourly Report (ทุกชั่วโมง)
```
📊 HOURLY STATUS UPDATE (14:00)

✅ Completed last hour: 2
🔄 In progress: 3
🚧 Blocked: 1

Active agents will continue working.
```

#### Daily Morning Report (08:00)
```
📅 DAILY REPORT - 2026-02-02

📊 TASK SUMMARY
━━━━━━━━━━━━━━━━━━━━
🆕 Created today: 5
✅ Completed today: 0
🔄 In progress: 3
⬜ Todo: 8
🚧 Blocked: 1

👥 ACTIVE AGENTS
━━━━━━━━━━━━━━━━━━━━
🟢 Dev Amelia: 12 tasks completed
🟡 QA Quinn: 8 tasks completed
⚪ PM John: idle

⚠️ ATTENTION: 2 overdue tasks need review
```

#### Daily Evening Summary (18:00)
```
🌆 EVENING SUMMARY - 2026-02-02

📈 TODAY'S ACHIEVEMENTS
✅ Tasks completed: 8
⏱️ Total work hours: 32
🎯 Completion rate: 85%

📝 PENDING FOR TOMORROW
• 3 tasks in progress
• 2 tasks due tomorrow
• 1 blocked task needs attention

Good work today! 💪
```

### 11.4 Alert Templates

#### Agent Silent Alert
```
🚨 AGENT SILENT ALERT

Agent: Dev Amelia (Developer)
Status: Has not reported progress for 35 minutes

Current Task: T-20260202-003
Task: Implement login API
Progress: 45%

Last Heartbeat: 14:25:00
Expected Update: Every 10 minutes

Actions: [Ping Agent] [Check Status] [Reassign Task]
```

#### Task Overdue Alert
```
⏰ TASK OVERDUE

Task: T-20260202-001
Title: Setup database schema
Assignee: Architect Winston

Due Date: 2026-02-01
Days Overdue: 1
Current Status: in_progress
Progress: 80%

Actions: [Extend Deadline] [Reassign] [Mark Complete]
```

#### Task Blocked Alert
```
🚧 TASK BLOCKED

Task: T-20260202-002
Title: Integrate payment gateway
Assignee: Dev Amelia
Blocked For: 3 hours

Blocker: Waiting for API key from vendor
Notes: Vendor contacted, awaiting response

Actions: [View Details] [Unblock] [Escalate]
```

### 11.5 Implementation Files

| File | Purpose |
|------|---------|
| `~/clawd/docs/CRON-MONITORING-SYSTEM.md` | Full design documentation |
| `~/clawd/monitoring/monitor.py` | Main monitoring engine |
| `~/clawd/monitoring/reports.py` | Report generator |
| `~/clawd/monitoring/rules/agent_rules.py` | Agent monitoring rules |
| `~/clawd/monitoring/rules/task_rules.py` | Task monitoring rules |
| `~/clawd/monitoring/rules/project_rules.py` | Project monitoring rules |

### 11.6 Database Tables (Monitoring)

```sql
-- Monitoring state tracking
CREATE TABLE monitoring_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    check_type TEXT NOT NULL,        -- 'agent_heartbeat', 'task_deadline'
    last_check DATETIME NOT NULL,
    next_check DATETIME,
    findings TEXT,                   -- JSON of findings
    alert_sent BOOLEAN DEFAULT FALSE,
    alert_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Alert history
CREATE TABLE alert_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id TEXT NOT NULL UNIQUE,
    alert_type TEXT NOT NULL,        -- 'agent_silent', 'task_overdue'
    severity TEXT,                   -- 'info', 'warning', 'critical'
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    related_task_id TEXT,
    related_agent_id TEXT,
    status TEXT DEFAULT 'active',    -- 'active', 'acknowledged', 'resolved'
    acknowledged_by TEXT,
    acknowledged_at DATETIME,
    resolved_at DATETIME,
    notification_sent BOOLEAN DEFAULT FALSE,
    notification_channel TEXT DEFAULT 'telegram',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 11.7 Alert Severity Levels

| Level | Condition | Response Time | Action |
|-------|-----------|---------------|--------|
| **Critical** | Task overdue > 1 day, Project overdue | Immediate | Telegram + Escalate |
| **Warning** | Agent silent > 30 min, Task blocked > 2h | 5 minutes | Telegram alert |
| **Info** | Task due today, Hourly summary | N/A | Telegram notification |

---

## 12. Alert Response Workflow

เมื่อได้รับการแจ้งเตือนจาก Health Monitor ต้องทำตามขั้นตอนนี้:

### 12.1 ประเภท Alerts และการตอบสนอง

| Alert Type | เงื่อนไข | การตอบสนองอัตโนมัติ | การแจ้งผู้ใช้ |
|------------|----------|---------------------|--------------|
| **Agent Stuck** | Task in_progress > 2h ไม่มี progress | 1. ตรวจสอบ subagent session ยังทำงานอยู่หรือไม่<br>2. ถ้าค้าง → unblock task, reset agent เป็น idle<br>3. รี(assign) ให้ agent อื่นหรือให้ agent เดิมเริ่มใหม่ | แจ้งเมื่อต้อง reassign |
| **Agent Offline** | Heartbeat หาย > 60 min | 1. ตั้ง agent status = offline<br>2. ย้ายงานที่กำลังทำ → ให้ agent อื่น<br>3. Log ว่า agent offline | แจ้งทันที |
| **Task Stuck** | In progress > 2h ไม่มี progress update | 1. ตรวจสอบว่าเป็น subagent หรือไม่<br>2. ถ้า subagent ค้าง → kill session<br>3. Block task + ปล่อย agent<br>4. รอผู้ใช้ตัดสินใจ (continue/abort/reassign) | แจ้งทันที พร้อมตัวเลือก |
| **Fix Loop Exceeded** | Fix attempts > 10 | 1. Block task<br>2. ปล่อย agent เป็น idle<br>3. แจ้งผู้ใช้พร้อมเหตุผล | แจ้งทันที |

### 12.2 Response Commands

```bash
# ตรวจสอบสถานะล่าสุด
python3 team_db.py health status

# ตรวจสอบเฉพาะ task ที่ค้าง
python3 team_db.py task list --status in_progress --stuck

# Unblock และ reassign
python3 team_db.py task unblock <task_id>
python3 team_db.py task reassign <task_id> <new_agent>

# Kill subagent session (ถ้าค้าง)
openclaw sessions list --active
openclaw sessions kill <session_id>

# รีเซ็ต agent
python3 team_db.py agent reset <agent_id>
```

### 12.3 Decision Tree

```
ได้รับ Alert "Task Stuck"
         │
         ▼
┌─────────────────────┐
│ Subagent ยังทำงาน? │
└─────────────────────┘
    │           │
   Yes          No
    │           │
    ▼           ▼
┌─────────┐  ┌──────────────────┐
│ รอต่อ?  │  │ Agent ยัง active?│
│ > 30 min│  └──────────────────┘
└─────────┘       │          │
    │            Yes         No
   Yes            │          │
    │             ▼          ▼
    ▼      ┌──────────┐  ┌─────────┐
┌────────┐ │ Auto-kill │  │ Unblock │
│ Kill   │ │ session   │  │ task    │
│session │ └──────────┘  └─────────┘
└────────┘      │              │
    │           ▼              ▼
    │    ┌─────────────────────────┐
    └───>│ Block task + Release    │
         │ agent → Notify user     │
         └─────────────────────────┘
```

### 12.4 User Response Options

เมื่อผู้ใช้ได้รับแจ้งเตือน สามารถตอบ:

| คำสั่ง | ผลลัพธ์ |
|--------|---------|
| "continue" / "ทำต่อ" | Unblock task, agent เริ่มทำใหม่ |
| "reassign to [agent]" / "ให้ [ชื่อ] ทำ" | Reassign ให้ agent ใหม่ |
| "abort" / "ยกเลิก" | Cancel task, agent ว่าง |
| "check" / "ตรวจสอบ" | รายงานสถานะปัจจุบัน |

---

**Last Updated:** 2026-02-02  
**Maintainer:** Orchestrator Agent  
**Next Review:** 2026-03-02
