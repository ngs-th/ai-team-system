# 🤖 AI Team System

AI Team monitoring and task management system with multi-agent orchestration.

## 📁 Project Structure

```
~/clawd/projects/ai-team/
├── 📄 Core Files
│   ├── team_db.py          # CLI tool (Python + SQLite)
│   ├── dashboard.php       # Web dashboard (PHP)
│   ├── team.db             # SQLite database (git-lfs tracked)
│   ├── health_monitor.py   # Health monitoring system
│   ├── auto_assign.py      # Auto task assignment
│   └── update-heartbeat.sh # Cron helper
│
├── 📁 agents/              # Agent configurations
│   ├── *.md                # 12 Agent configs (pm, dev, qa, etc.)
│   ├── spawn-agent.sh      # Agent spawner script
│   └── templates/          # Task templates
│       ├── template-prd.md
│       ├── template-tech-spec.md
│       ├── template-qa-testplan.md
│       ├── template-feature-dev.md
│       └── template-bug-fix.md
│
├── 📁 docs/                # Documentation
│   ├── AI-TEAM-SYSTEM.md       # Full system docs (53KB)
│   ├── AI-TEAM-SHARED-SYSTEM.md # Shared context
│   ├── QUICK-REFERENCE.md       # One-page reference
│   ├── SPAWN-MECHANISM.md       # Spawn modes explained
│   ├── ARCHIVED-AGENTS-TEAM.md  # Legacy reference
│   └── architecture/            # System analysis
│       ├── mission-control-comparison.md
│       └── system-analysis.md
│
└── 📁 cron/
    └── AI-TEAM-HANDLER.md  # Cron job handlers
```

## 🚀 Quick Start

### 1. View Dashboard

```bash
cd ~/clawd/projects/ai-team
php -S localhost:8080 dashboard.php
# Open: http://localhost:8080
```

### 2. CLI Tool

```bash
# List all commands
./team_db.py --help

# List agents
./team_db.py agents list

# List tasks
./team_db.py tasks list

# Create task with template
./team_db.py task create "Implement auth" --project PROJ-001 --template feature-dev
```

### 3. Spawn Agent

```bash
# Mode A: Database Queue (default) - Agent picks up via heartbeat
./agents/spawn-agent.sh pm "Define roadmap Q1"

# Mode B: Immediate Spawn - Start working immediately
./agents/spawn-agent.sh pm "Urgent bug fix" --spawn

# With template
./agents/spawn-agent.sh dev "Build API" --template tech-spec
```

## 📊 Features

- **Multi-Agent System:** 12 specialized agents (PM, Dev, QA, UX, etc.)
- **Task Management:** Create, assign, track tasks with SQLite
- **Templates:** PRD, Tech Spec, QA Test Plan, Feature Dev, Bug Fix
- **Dashboard:** Real-time PHP dashboard with auto-refresh
- **Health Monitoring:** Cron-based monitoring with Telegram alerts
- **Two Spawn Modes:** Database Queue (default) or Immediate Spawn

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [docs/AI-TEAM-SYSTEM.md](docs/AI-TEAM-SYSTEM.md) | Complete system documentation |
| [docs/QUICK-REFERENCE.md](docs/QUICK-REFERENCE.md) | One-page quick reference |
| [docs/SPAWN-MECHANISM.md](docs/SPAWN-MECHANISM.md) | Spawn modes explained |
| [docs/architecture/](docs/architecture/) | System analysis & comparisons |

## 🗄️ Database

Location: `team.db` (SQLite)

**Tables:**
- `agents` - Team members & status
- `projects` - Project definitions
- `tasks` - Task records with requirements
- `task_history` - Activity log
- `task_dependencies` - Dependency graph

**Views:**
- `v_dashboard_stats` - Pre-calculated stats
- `v_project_status` - Project progress
- `v_agent_status` - Agent health status
- `v_task_summary` - Task summaries

## 🔄 Spawn Modes

| Mode | Command | When to Use |
|------|---------|-------------|
| **A - DB Queue** | `./spawn-agent.sh pm "Task"` | Normal tasks, background work |
| **B - Immediate** | `./spawn-agent.sh pm "Task" --spawn` | Urgent bugs, user waiting |

See [docs/SPAWN-MECHANISM.md](docs/SPAWN-MECHANISM.md) for details.

## 📝 Templates

Available task templates:

```bash
# List templates
./team_db.py task template list

# Create task from template
./team_db.py task template create prd "My Feature" --project PROJ-001
```

| Template | Purpose |
|----------|---------|
| `prd` | Product Requirements Document |
| `tech-spec` | Technical Specification |
| `qa-testplan` | QA Test Plan |
| `feature-dev` | Feature Development |
| `bug-fix` | Bug Fix |

## 🔔 Monitoring

Cron jobs configured for:
- **Every 5 min:** Agent heartbeat check
- **Every 30 min:** Deadline check
- **Hourly:** Hourly report
- **08:00 daily:** Morning report
- **18:00 daily:** Evening summary

All alerts sent to Telegram.

## 🔧 Requirements

- PHP 8.0+ (with SQLite3 extension)
- Python 3.8+
- SQLite3
- Git LFS (for `team.db`)

```bash
# Install git-lfs
brew install git-lfs
git lfs install
git lfs pull
```

## 📦 No Dependencies

- Pure PHP (built-in SQLite3)
- No frameworks
- No composer packages
- Single-file dashboard

---

**Version:** 3.4.4  
**Last Updated:** 2026-02-02
