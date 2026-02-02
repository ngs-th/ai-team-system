# 🤖 AI Team Dashboard

AI Team monitoring dashboard - Pure PHP + SQLite3 implementation.

## Location

All files in one place:

```
~/clawd/projects/ai-team/
├── dashboard.php      # Web dashboard
├── team_db.py         # CLI tool
├── team.db            # SQLite database (git-lfs tracked)
├── docs/
│   └── AI-TEAM.md     # Full documentation
└── README.md          # This file
```

## Files

| File | Description |
|------|-------------|
| `dashboard.php` | Main dashboard (pure PHP, single file) |
| `team_db.py` | CLI tool for database management |
| `team.db` | SQLite database (tracked with git-lfs) |
| `docs/AI-TEAM.md` | Full system documentation |

## Quick Start

### Run Dashboard

```bash
cd ~/clawd/projects/ai-team
php -S localhost:8080 dashboard.php
```

Then open: http://localhost:8080

### CLI Tool

```bash
cd ~/clawd/projects/ai-team
python3 team_db.py --help
```

## Dashboard Features

- **Auto-refresh:** Every 30 seconds
- **Stats:** Total agents, tasks, projects
- **Agents:** Status, workload, progress
- **Projects:** Progress bars, task counts
- **Tasks:** Full task list with priorities
- **Activity:** Recent task history

## Database

Location: Same directory (`team.db`)

Tables:
- `agents` - Team members
- `projects` - Project definitions
- `tasks` - Task records
- `task_history` - Activity log

Views:
- `v_dashboard_stats` - Pre-calculated stats
- `v_project_status` - Project progress
- `v_task_summary` - Task summaries
- `v_agent_workload` - Agent workload info

## Git LFS

Database is tracked with git-lfs:

```bash
# Install git-lfs (one time)
brew install git-lfs
git lfs install

# Pull LFS files
git lfs pull
```

## No Dependencies

- Pure PHP (built-in SQLite3 extension)
- No frameworks
- No composer packages
- No external libraries
