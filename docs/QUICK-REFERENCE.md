# 🤖 AI Team Quick Reference

**One-page reference for the OpenClaw AI Team System**

---

## 👥 Agent Roster

| Icon | Agent | Name | Role | Model |
|------|-------|------|------|-------|
| 📋 | **PM** | John | Product Manager | Claude Opus |
| 📊 | **Analyst** | Mary | Business Analyst | Claude Sonnet |
| 🏗️ | **Architect** | Winston | System Architect | Claude Opus |
| 💻 | **Dev** | Amelia | Developer | Kimi Code |
| 🎨 | **UX Designer** | Sally | UX/UI Designer | Claude Sonnet |
| 🏃 | **Scrum Master** | Bob | Scrum Master | Claude Sonnet |
| 🧪 | **QA Engineer** | Quinn | QA Engineer | Claude Sonnet |
| 📝 | **Tech Writer** | Tom | Technical Writer | Claude Sonnet |
| 🚀 | **Solo Dev** | Barry | Quick Fix Dev | Kimi Code |

---

## 🔄 Workflow Patterns

### Pattern 1: Full Team (Complex Project, >3 days)
```
User → PM (vision) → Analyst (requirements) → Architect (design)
  → UX Designer (UI) → Dev (implement) → QA (test) → User
  ↑_________________________________________________|
         (Scrum Master coordinates throughout)
```

### Pattern 2: Dev Team (Feature Development, 1-3 days)
```
User → Architect (tech spec) → Dev (code) → QA (review) → User
         ↓______________↑ (Tech Writer docs)
```

### Pattern 3: Quick Fix (Simple Task, <2 hours)
```
User → Solo Dev → User
```

### Pattern 4: Design First (UI/UX Focus, 2-5 days)
```
User → Analyst (requirements) → UX Designer (mockups) 
  → Architect (tech spec) → Dev → QA → User
```

---

## 🚀 Quick Commands

### CLI Tool
```bash
./team_db.py agents list              # ดูสถานะ agents
./team_db.py tasks list               # ดูรายการ tasks
./team_db.py tasks create --help      # สร้าง task ใหม่
./team_db.py dashboard                # เปิด dashboard
```

### Create Task (with working directory)
```bash
./team_db.py task create "Feature name" \
  --project PROJ-001 \
  --working-dir /Users/ngs/Herd/nurse-ai \
  --prerequisites "- [ ] API ready" \
  --acceptance "- [ ] Tests pass" \
  --expected-outcome "Feature works end-to-end"
```

### Spawn Agent (with template)
```bash
./agents/spawn-agent.sh <agent-type> "<task description>"

./agents/spawn-agent.sh pm "Define roadmap Q1"
./agents/spawn-agent.sh dev "Implement auth"
./agents/spawn-agent.sh qa "Test payment flow"
```

---

## 📂 Key Files

| File | Purpose |
|------|---------|
| `docs/AI-TEAM-SYSTEM.md` | Full documentation (53KB) |
| `docs/QUICK-REFERENCE.md` | This file |
| `docs/architecture/` | System analysis & comparisons |
| `agents/*.md` | Individual agent configs |
| `agents/templates/` | Task templates (PRD, Tech Spec, etc.) |
| `team_db.py` | CLI tool |
| `dashboard.php` | Web dashboard |
| `team.db` | SQLite database |

---

**Full details:** See `docs/AI-TEAM-SYSTEM.md`
