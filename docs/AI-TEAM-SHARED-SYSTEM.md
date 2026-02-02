# 🤖 AI Team - Shared Task & Progress System

**Version:** 1.0.0  
**Created:** 2026-02-01  
**Status:** Draft

---

## 🎯 ภาพรวมระบบ

AI Team 9 Agents จะแชร์ข้อมูลผ่าน **Shared Memory + Status Board** แบบเดียวกับ Kanban Board

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SHARED TASK BOARD                                 │
├─────────────────────────────────────────────────────────────────────┤
│  📋 TODO        │  🔄 IN PROGRESS   │  ✅ DONE        │  🚧 BLOCKED │
├─────────────────┼───────────────────┼─────────────────┼─────────────┤
│ • Task A        │ • Task B (Dev)    │ • Task C        │ • Task D    │
│   [PM]          │   70%             │   [QA]          │   Waiting   │
│                 │   Due: 20:00      │                 │   API       │
├─────────────────┴───────────────────┴─────────────────┴─────────────┤
│  📊 PROJECT STATUS: 3 Active | 5 Done | 1 Blocked | Progress: 65%   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌─────────────────────────────┐
              │     AGENT SHARED MEMORY      │
              │  ~/clawd/memory/team/        │
              │  - context.md                │
              │  - active-tasks.json         │
              │  - agent-status.json         │
              └─────────────────────────────┘
```

---

## 📁 โครงสร้าง Shared Memory

```
~/clawd/memory/
├── team/                          # SHARED - ทุก Agent อ่าน/เขียนได้
│   ├── TASK-BOARD.md             # Kanban board หลัก
│   ├── PROJECT-STATUS.md         # สถานะโปรเจครวม
│   ├── active-tasks.json         # Tasks ที่กำลังทำ
│   ├── agent-status.json         # สถานะแต่ละ Agent
│   └── shared-context.md         # Context ร่วม
│
├── agents/                        # PRIVATE - เฉพาะ Agent นั้น
│   ├── pm/
│   ├── dev/
│   └── ...
│
└── YYYY-MM-DD.md                 # Daily logs
```

---

## 📋 1. Task Board (Kanban Style)

**ไฟล์:** `~/clawd/memory/team/TASK-BOARD.md`

### รูปแบบ:
```markdown
# AI Team Task Board
**Last Updated:** 2026-02-01 20:15  
**Updated By:** Orchestrator

---

## 📋 TODO
| ID | Task | Assignee | Priority | Due |
|----|------|----------|----------|-----|
| T-001 | เขียน PRD ฟีเจอร์ X | PM John | HIGH | 2026-02-02 |
| T-002 | วิเคราะห์ requirements | Analyst Mary | MEDIUM | 2026-02-03 |

## 🔄 IN PROGRESS
| ID | Task | Assignee | Progress | Started | ETA |
|----|------|----------|----------|---------|-----|
| T-003 | ออกแบบ database | Architect Winston | 60% | 20:00 | 22:00 |
| T-004 | Implement API | Dev Amelia | 30% | 19:30 | 21:00 |

## ✅ DONE (Today)
| ID | Task | Assignee | Completed | Result |
|----|------|----------|-----------|--------|
| T-005 | Fix bug #123 | Solo Dev Barry | 19:45 | ✅ PASS |

## 🚧 BLOCKED
| ID | Task | Assignee | Blocked By | Need Help From |
|----|------|----------|------------|----------------|
| T-006 | Test payment | QA Quinn | API not ready | Dev Amelia |

---

## 📊 Quick Stats
- Total: 6 tasks
- Done: 1 (17%)
- In Progress: 2 (33%)
- Todo: 2 (33%)
- Blocked: 1 (17%)
```

---

## 📊 2. Project Status Dashboard

**ไฟล์:** `~/clawd/memory/team/PROJECT-STATUS.md`

```markdown
# Project Status Dashboard

## 🎯 Current Sprint
**Sprint:** #1 - Foundation  
**Start:** 2026-02-01  
**End:** 2026-02-07  
**Progress:** 65%

---

## 📈 Overall Progress
```
Requirements    [████████░░] 80%  ✅ Analyst Mary
Design          [██████░░░░] 60%  🔄 Architect Winston
Development     [████░░░░░░] 40%  🔄 Dev Amelia
Testing         [░░░░░░░░░░] 0%   ⏳ QA Quinn
Documentation   [░░░░░░░░░░] 0%   ⏳ Tech Writer Tom
```

## 👥 Agent Status
| Agent | Current Task | Status | Since | ETA |
|-------|--------------|--------|-------|-----|
| PM John | Planning | 🟢 Active | 19:00 | 20:30 |
| Analyst Mary | Requirements | 🟡 Review | 19:15 | 20:00 |
| Architect Winston | Database Design | 🟢 Active | 20:00 | 22:00 |
| Dev Amelia | API Dev | 🟢 Active | 19:30 | 21:00 |
| QA Quinn | Waiting | 🔴 Idle | - | - |
| Tech Writer Tom | Waiting | 🔴 Idle | - | - |

## 🚨 Issues & Blockers
1. **API not ready** - QA waiting for Dev (ETA: 21:00)
2. **Requirements unclear** - Analyst needs clarification from PM

## 📅 Upcoming Milestones
- [ ] 2026-02-02: Requirements complete
- [ ] 2026-02-03: Design approved
- [ ] 2026-02-05: MVP ready for testing
```

---

## 🔧 3. Active Tasks (JSON Format)

**ไฟล์:** `~/clawd/memory/team/active-tasks.json`

```json
{
  "version": "1.0",
  "last_updated": "2026-02-01T20:15:00+07:00",
  "sprint": {
    "id": "sprint-001",
    "name": "Foundation",
    "start": "2026-02-01",
    "end": "2026-02-07"
  },
  "tasks": [
    {
      "id": "T-003",
      "title": "Design database schema",
      "assignee": "architect",
      "agent_name": "Winston",
      "status": "in_progress",
      "progress": 60,
      "priority": "high",
      "started_at": "2026-02-01T20:00:00+07:00",
      "eta": "2026-02-01T22:00:00+07:00",
      "blockers": [],
      "notes": "Working on ERD diagram"
    },
    {
      "id": "T-004",
      "title": "Implement API endpoints",
      "assignee": "dev",
      "agent_name": "Amelia",
      "status": "in_progress",
      "progress": 30,
      "priority": "high",
      "started_at": "2026-02-01T19:30:00+07:00",
      "eta": "2026-02-01T21:00:00+07:00",
      "blockers": [],
      "dependencies": ["T-003"],
      "notes": "Authentication done, working on CRUD"
    }
  ],
  "metrics": {
    "total": 6,
    "done": 1,
    "in_progress": 2,
    "todo": 2,
    "blocked": 1,
    "completion_rate": 17
  }
}
```

---

## 👤 4. Agent Status (JSON Format)

**ไฟล์:** `~/clawd/memory/team/agent-status.json`

```json
{
  "last_updated": "2026-02-01T20:15:00+07:00",
  "agents": [
    {
      "id": "pm",
      "name": "John",
      "status": "active",
      "current_task": "T-001",
      "task_title": "Write PRD",
      "since": "2026-02-01T19:00:00+07:00",
      "eta": "2026-02-01T20:30:00+07:00",
      "last_heartbeat": "2026-02-01T20:10:00+07:00",
      "health": "good"
    },
    {
      "id": "dev",
      "name": "Amelia",
      "status": "active",
      "current_task": "T-004",
      "task_title": "Implement API",
      "since": "2026-02-01T19:30:00+07:00",
      "eta": "2026-02-01T21:00:00+07:00",
      "last_heartbeat": "2026-02-01T20:14:00+07:00",
      "health": "good"
    },
    {
      "id": "qa",
      "name": "Quinn",
      "status": "idle",
      "current_task": null,
      "blocked_by": "T-004",
      "notes": "Waiting for API to be ready"
    }
  ]
}
```

---

## 🔄 Workflow การอัปเดต

### 1. ตอนเริ่มงาน (Agent ทำ)
```markdown
1. อ่าน active-tasks.json หางานของตัวเอง
2. อัปเดต agent-status.json → status: "active"
3. อัปเดต TASK-BOARD.md → ย้ายไป IN PROGRESS
4. บันทึกเวลาเริ่ม (started_at)
```

### 2. ตอนรายงาน progress (ทุก 10 นาที)
```markdown
1. อัปเดต progress % ใน active-tasks.json
2. อัปเดต last_heartbeat ใน agent-status.json
3. ถ้ามี blocker → ย้ายไป BLOCKED + ระบุเหตุผล
```

### 3. ตอนเสร็จงาน
```markdown
1. อัปเดต active-tasks.json → status: "done"
2. ย้ายงานใน TASK-BOARD.md ไป DONE
3. อัปเดต agent-status.json → status: "idle" หรือ next task
4. สรุปผลลัพธ์ใน PROJECT-STATUS.md
```

### 4. ตอนมีปัญหา
```markdown
1. ย้ายงานไป BLOCKED
2. ระบุ blocked_by และ need_help_from
3. แจ้ง Orchestrator ทันที
4. Scrum Master ประสานงานแก้ไข
```

---

## 🛠️ Tools สำหรับดู Status

### ดู Task Board:
```bash
# ดูแบบสรุป
cat ~/clawd/memory/team/TASK-BOARD.md

# ดูแบบ JSON (สำหรับ automation)
cat ~/clawd/memory/team/active-tasks.json | jq '.tasks[] | select(.status == "in_progress")'
```

### ดู Agent Status:
```bash
# ใครทำอะไรอยู่
cat ~/clawd/memory/team/agent-status.json | jq '.agents[] | {name, status, task: .current_task}'

# ใครว่าง
cat ~/clawd/memory/team/agent-status.json | jq '.agents[] | select(.status == "idle")'
```

### ดู Project Status:
```bash
cat ~/clawd/memory/team/PROJECT-STATUS.md
```

---

## 📱 การแจ้งเตือน

### Cron Jobs (แจ้งเตือนอัตโนมัติ)
```yaml
# ทุก 30 นาที: สรุปสถานะ
- name: "AI Team Status Update"
  schedule: "*/30 * * * *"
  action: "สรุปสถานะ AI Team ส่ง Telegram"

# ทุกชั่วโมง: เช็ค Agent ที่เงียบ
- name: "Check Silent Agents"
  schedule: "0 * * * *"
  action: "เช็ค last_heartbeat แจ้งเตือนถ้าเงียบ > 30 นาที"

# ตอนเที่ยงคืน: สรุปวัน
- name: "Daily Summary"
  schedule: "0 0 * * *"
  action: "สรุปงานวันนี้ที่เสร็จ/ค้าง"
```

---

## 🎯 สรุป

| ไฟล์ | ใช้สำหรับ | ใครอัปเดต |
|-----|----------|----------|
| `TASK-BOARD.md` | Kanban board | ทุก Agent |
| `PROJECT-STATUS.md` | สถานะโปรเจครวม | Scrum Master / Orchestrator |
| `active-tasks.json` | Tasks ที่ทำ | แต่ละ Agent |
| `agent-status.json` | สถานะ Agent | แต่ละ Agent |
| `shared-context.md` | Context ร่วม | ทุก Agent |

**การทำงาน:**
1. Agent อ่านจาก `active-tasks.json` หางานตัวเอง
2. Agent อัปเดต progress ทุก 10 นาที
3. Orchestrator อ่านสถานะรวมจาก `agent-status.json`
4. Scrum Master อัปเดต `PROJECT-STATUS.md`
5. User ดูสถานะได้จาก `TASK-BOARD.md` หรือ Telegram

**พร้อมให้สร้างไฟล์จริงไหมครับ?** 🎯
