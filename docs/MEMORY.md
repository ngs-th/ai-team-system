# AI Team Memory System

## Architecture

ระบบ Memory ใช้ SQLite ทั้งหมด 3 ตาราง:

### 1. agent_context (Long-term Memory)
- `context` - บทบาทและความรับผิดชอบของ agent
- `learnings` - บทเรียนจากงานที่ผ่านมา (สะสม)
- `preferences` - การตั้งค่าส่วนตัว

**การใช้งาน:**
- อ่านทุกครั้งที่ spawn subagent
- อัพเดตอัตโนมัติโดย memory_maintenance.py (ทุกชั่วโมง)

### 2. agent_working_memory (Short-term Memory)
- `current_task_id` - งานที่กำลังทำ
- `working_notes` - บันทึกระหว่างทำงาน
- `blockers` - ปัญหาที่ติดอยู่
- `next_steps` - ขั้นตอนถัดไป

**การใช้งาน:**
```bash
# Update ทุก 30 นาที
python3 agent_memory_writer.py working <agent_id> --task <task_id> --notes "..."

# Update blockers
python3 agent_memory_writer.py working <agent_id> --blockers "Stuck on X"

# Update next steps
python3 agent_memory_writer.py working <agent_id> --next "Will do Y"
```

### 3. agent_communications (Inter-Agent Communication)
- `message` - ข้อความ
- `message_type` - comment/mention/request/response
- `is_read` - สถานะอ่าน

**การใช้งาน:**
```bash
python3 team_db.py agent comm send <from> "message" --to <to> --task <task_id>
python3 team_db.py agent comm list <agent_id>
python3 team_db.py agent comm read <message_id>
```

## Commands

### View Working Memory
```bash
python3 team_db.py agent memory show <agent_id>
```

### Add Learning
```bash
python3 agent_memory_writer.py learn <agent_id> "What I learned"
```

### View All Learnings
```bash
python3 team_db.py agent context <agent_id>
```

---

## Documentation

### API Documentation & User Guide
- **Location:** `docs/API-USER-GUIDE.md`
- **Contents:**
  - Complete API reference for all CLI commands
  - Task, Agent, Orchestrator, Health Monitor APIs
  - User guides for PMs, Developers, and Agents
  - Setup and configuration instructions
  - Comprehensive troubleshooting section

### Quick Reference Card
- **Location:** `docs/QUICK-REFERENCE-CARD.md`
- **Contents:**
  - One-page cheat sheet
  - Most common commands
  - Status reference (emojis)
  - Task lifecycle flow
  - Emergency commands

---

## Maintenance

Cron job `memory_maintenance.py` ทำอัตโนมัติ:
1. Reset stale agents (>1h ไม่มี heartbeat)
2. Update learnings จากงานที่เสร็จ (7 วันล่าสุด)
3. Archive history เกิน 30 วัน
