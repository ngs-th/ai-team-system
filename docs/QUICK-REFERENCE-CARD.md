# 🤖 AI Team - Quick Reference Card

**One-page cheat sheet for common operations**

---

## 🚀 Most Common Commands

### Tasks
```bash
# Create task (with required fields)
python3 team_db.py task create "Title" --project PROJ-001 \
  --expected-outcome "Success criteria" \
  --prerequisites "- [ ] Item" \
  --acceptance "- [ ] Criteria"

# Start, progress, complete
python3 team_db.py task start T-20260203-001
python3 team_db.py task progress T-20260203-001 50 --notes "Half done"
python3 team_db.py task done T-20260203-001

# List and filter
python3 team_db.py task list
python3 team_db.py task list --status blocked
python3 team_db.py task list --agent dev
```

### Agents
```bash
# List all agents
python3 team_db.py agent list

# Update heartbeat
python3 team_db.py agent heartbeat dev

# Working memory
python3 team_db.py agent memory show dev
python3 team_db.py agent memory update dev --notes "Current focus"
```

### Orchestrator
```bash
# Submit goal
python3 orchestrator.py goal feature "Title" \
  --outcome "Expected result" --desc "Details"

# Monitor
python3 orchestrator.py list
python3 orchestrator.py show M-20260203-001
python3 orchestrator.py monitor
```

### Health
```bash
# Check status
python3 health_monitor.py --status
python3 health_monitor.py --check

# Auto-fix stuck tasks
python3 health_monitor.py --auto-resolve
```

---

## 📊 Status Reference

### Task Status
| Status | Emoji | Meaning |
|--------|-------|---------|
| backlog | 📋 | Waiting for requirements |
| todo | ⬜ | Ready to start |
| in_progress | 🔄 | Currently working |
| review | 👀 | Waiting for approval |
| done | ✅ | Completed |
| blocked | 🚧 | Blocked, needs help |

### Agent Status
| Status | Emoji | Meaning |
|--------|-------|---------|
| idle | ⚪ | Available for work |
| active | 🟢 | Working on task |
| blocked | 🔴 | Stuck, needs help |
| offline | ⚫ | No heartbeat > 60min |

### Agent Health
| Health | Emoji | Last Heartbeat |
|--------|-------|----------------|
| healthy | ✅ | < 30 min |
| stale | 🟡 | 30-60 min |
| offline | 🔴 | > 60 min |

---

## 🔗 Task Lifecycle Flow

```
Create → Assign → Start → Progress → Review → Done
   ↓        ↓       ↓         ↓         ↓
Backlog  Block   Block    Update    Approve
```

**Commands at each stage:**
1. **Create**: `task create` → `task assign`
2. **Start**: `task start`
3. **Progress**: `task progress <id> <%>`
4. **Block**: `task block <id> "reason"`
5. **Unblock**: `task unblock <id>`
6. **Complete**: `task done <id>` → `task approve <id>`

---

## 🆘 Emergency Commands

```bash
# Reset agent to idle
sqlite3 team.db "UPDATE agents SET status='idle', current_task_id=NULL WHERE id='dev';"

# Block stuck task
python3 team_db.py task block T-001 "Stuck, reassigning"

# Check system health
python3 health_monitor.py --status

# View recent notifications
python3 team_db.py notify log --limit 5
```

---

## 📝 Task Template

When creating tasks, always include:

```bash
python3 team_db.py task create "Feature Name" \
  --project PROJ-001 \
  --desc "What needs to be done" \
  --assign dev \
  --priority high \
  --due 2026-02-10 \
  --expected-outcome "Clear success definition" \
  --prerequisites "- [ ] API ready
- [ ] Design approved" \
  --acceptance "- [ ] Code implemented
- [ ] Tests passing
- [ ] Documentation updated"
```

---

## 🔧 Cron Jobs

```bash
# Health check every 5 minutes
*/5 * * * * cd /Users/ngs/clawd/projects/ai-team && python3 health_monitor.py --daemon

# Auto-assign every 10 minutes
*/10 * * * * cd /Users/ngs/clawd/projects/ai-team && python3 auto_assign.py --run

# Memory maintenance hourly
0 * * * * cd /Users/ngs/clawd/projects/ai-team && python3 memory_maintenance.py
```

---

## 📁 Important Files

| File | Purpose |
|------|---------|
| `team.db` | Main database |
| `team_db.py` | Main CLI |
| `orchestrator.py` | Mission orchestration |
| `health_monitor.py` | Health checks |
| `auto_assign.py` | Auto-assignment |
| `docs/API-USER-GUIDE.md` | Full documentation |
| `memory/YYYY-MM-DD.md` | Daily logs |

---

**Full Documentation**: `docs/API-USER-GUIDE.md`
