# 🤖 AI Team System

ระบบบริหารงานแบบ Kanban + spawn agent อัตโนมัติ + workflow รีวิวโค้ดจริง โดยเก็บ state ทั้งหมดไว้ใน SQLite (`team.db`) และมีแดชบอร์ดอ่านอย่างเดียว (`dashboard.php`) เพื่อให้ “สิ่งที่เห็น” ตรงกับ “สิ่งที่เกิดขึ้นจริง”

Timezone มาตรฐานของระบบ: `Asia/Bangkok (UTC+7)`

## สิ่งที่ระบบนี้ทำให้ได้ (Expected Outcome)

- แดชบอร์ดสะท้อนความจริงของงานและ session agent
- งานถูกไล่สถานะตาม workflow: `backlog → todo → in_progress → review → reviewing → done`
- `blocked` และ `info_needed` เป็น “สถานะจริง” ใน DB และแสดงเป็น attribute (แถบแดงบนการ์ด)
- prerequisites/acceptance criteria เป็น checklist และใช้เป็น gate ของการ “ปิดงาน” แบบตรวจได้
- รองรับ runtime หลายแบบผ่าน adapter (`agent_runtime.py`) โดย default คือ `openclaw`

## 📁 โครงสร้างโปรเจกต์ (Project Structure)

โฟลเดอร์หลัก:
- `team_db.py`: CLI หลัก (Python + SQLite)
- `dashboard.php`: Kanban dashboard (PHP, read-only)
- `team.db`: SQLite database (source of truth สำหรับ state)
- `auto_assign.py`: auto-assign + spawn งานจาก `todo`
- `spawn_manager_fixed.py`: spawn งานที่ assigned แล้ว + auto-start เพื่อย้ายการ์ดไป Doing
- `review_manager.py`: spawn reviewer และจัดการสถานะ review/reviewing
- `agent_reporter.py`: ช่องทางมาตรฐานที่ agent ใช้รายงานกลับ DB

เอกสาร:
- `docs/AI-TEAM-SYSTEM.md`: Single Source of Truth (สำคัญที่สุด)
- `docs/TASK-SOP.md`: SOP การสร้าง task ใหม่ (สำหรับ agent/คน)
- `docs/architecture/`: เอกสารสถาปัตยกรรม/เปรียบเทียบระบบ

## 🚀 Quick Start

### 1) เปิดแดชบอร์ด

```bash
cd /Users/ngs/Herd/ai-team-system

# ถ้าใช้ Herd (แนะนำ): เปิด URL ตรง
# http://ai-team-system.test/dashboard.php

# หรือรัน php built-in server
php -S localhost:8080 dashboard.php
```

### 2) ใช้ CLI

```bash
# List commands
python3 team_db.py --help

# List agents
python3 team_db.py agent list

# List tasks
python3 team_db.py task list

# Create task (ต้องระบุ working-dir + project + expected/prereq/AC)
python3 team_db.py task create "Implement auth" \
  --project PROJ-001 \
  --working-dir /Users/ngs/Herd/nurse-ai \
  --expected-outcome "User can login/logout and session persists" \
  --prerequisites "- [ ] HUMAN: ได้รับ API key ของจริง @human\n- [ ] ยืนยัน working_dir = /Users/ngs/Herd/nurse-ai" \
  --acceptance "- [ ] AC1: Login works\n- [ ] AC2: Logout works"

# ถ้าต้อง “รอข้อมูลจากคน” ให้ใช้ info_needed (ไม่ให้ระบบวนหยิบไปทำ)
python3 team_db.py task info-needed T-20260202-001 "ต้องมี API key ของจริงจากผู้ใช้"

# คนเป็นผู้ติ๊ก HUMAN-only prerequisites
python3 team_db.py task check T-20260202-001 --field prerequisites --index 1 --done --actor human
```

### 3) ให้ระบบ spawn agent ทำงาน

```bash
# Auto-assign + spawn (รันครั้งเดียว)
python3 auto_assign.py --run

# Spawn งานที่ถูก assign แล้ว (รันครั้งเดียว)
python3 spawn_manager_fixed.py

# Review manager (รันครั้งเดียว)
python3 review_manager.py --verbose
```

## 📊 Features

- **Kanban Board:** Backlog / Todo / Doing / Waiting for Review / Reviewing / Done
- **Review Workflow จริง:** reviewer ต้องอ่านโค้ดและติ๊ก AC ก่อน approve
- **HUMAN-only prerequisites:** กัน agent “ติ๊กผ่านเอง” เรื่อง key/secret ของจริง
- **Dashboard truth:** จุดเขียวกระพริบ = agent `active` และทำ task นี้จริง
- **Bangkok time:** ทุก timestamp ใช้ `localtime` (+7)

## 📚 Documentation

- `docs/AI-TEAM-SYSTEM.md`: Single Source of Truth
- `docs/TASK-SOP.md`: SOP การสร้าง task ใหม่
- `docs/QUICK-REFERENCE-CARD.md`: คำสั่งหลักแบบสั้น
- `docs/architecture/`: เอกสารเปรียบเทียบ/สถาปัตยกรรม

## 🗄️ Database

Location: `team.db` (SQLite)

ERD: `docs/architecture/ERD.md`

## 📝 Templates

Available task templates:

```bash
# List templates
python3 team_db.py task template list

# Create task from template
python3 team_db.py task template create prd "My Feature" --project PROJ-001
```

| Template | Purpose |
|----------|---------|
| `prd` | Product Requirements Document |
| `tech-spec` | Technical Specification |
| `qa-testplan` | QA Test Plan |
| `feature-dev` | Feature Development |
| `bug-fix` | Bug Fix |

## 🛑 Auto-Stop Safety (Fix Loop Protection)

To prevent infinite loops and excessive token consumption, tasks are automatically stopped after **10 fix loops**.

### How It Works

1. Each time a task fails and needs fixing, the `fix_loop_count` increments
2. At loop 10, the task is **automatically blocked** with a clear status message
3. The agent is released and notified
4. Manual intervention is required to resume

### Commands

```bash
# Check fix loop status for all tasks
python3 orchestrator.py fix-status

# Check specific task
python3 orchestrator.py fix-status --task T-20260202-001

# Resume auto-stopped task (resets counter to 0)
python3 orchestrator.py resume-task T-20260202-001 --agent dev

# Manual failure trigger (for testing)
python3 orchestrator.py handle-failure T-20260202-001 "Build failed"
```

### Alternative Resume via team_db

```bash
# This also resets fix_loop_count to 0
python3 team_db.py task unblock T-20260202-001
```

## 🔔 Monitoring

Cron jobs configured for:
- **Every 5 min:** Agent heartbeat check
- **Every 30 min:** Deadline check
- **Hourly:** Hourly report
- **08:00 daily:** Morning report
- **18:00 daily:** Evening summary

All alerts sent to Telegram.

## 🔧 Requirements

- PHP 8+ (พร้อม SQLite3 extension) หรือ Herd
- Python 3.8+
- `openclaw` CLI (ถ้าจะให้ runtime ทำงานจริง)

---

**Last Updated:** 2026-02-05
