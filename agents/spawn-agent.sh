#!/usr/bin/env bash
#
# OpenClaw AI Team - Agent Spawner
# Usage: ./spawn-agent.sh <agent-type> "<task-description>" [--template <template-name>]
#
# This script:
# 1. Creates a task record in team.db
# 2. Spawns an OpenClaw session with the agent context (optional, see MODES below)
#
# MODES:
#   Mode A (Default): Create task in DB only → Agent picks up from heartbeat
#   Mode B (--spawn): Create task + spawn OpenClaw session immediately
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
WORKSPACE="${PROJECT_DIR}"  # Fixed: points to ai-team/ directory

AGENT_TYPE=$1
TASK_DESC=$2
TEMPLATE=""
SPAWN_MODE="db"  # Default: db only

# Parse optional flags
shift 2
while [[ $# -gt 0 ]]; do
    case $1 in
        --template)
            TEMPLATE="$2"
            shift 2
            ;;
        --spawn)
            SPAWN_MODE="session"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate inputs
if [ -z "$AGENT_TYPE" ] || [ -z "$TASK_DESC" ]; then
    echo "Usage: ./spawn-agent.sh <agent-type> \"<task-description>\" [--template <name>] [--spawn]"
    echo ""
    echo "Available agents:"
    echo "  pm          - Product Manager (John)"
    echo "  analyst     - Business Analyst (Mary)"
    echo "  architect   - System Architect (Winston)"
    echo "  dev         - Developer (Amelia)"
    echo "  ux-designer - UX Designer (Sally)"
    echo "  scrum-master- Scrum Master (Bob)"
    echo "  qa          - QA Engineer (Quinn)"
    echo "  tech-writer - Technical Writer (Tom)"
    echo "  solo-dev    - Solo Developer (Barry)"
    echo ""
    echo "Available templates:"
    echo "  prd        - Product Requirements Document"
    echo "  tech-spec  - Technical Specification"
    echo "  qa-testplan- QA Test Plan"
    echo "  feature-dev- Feature Development"
    echo "  bug-fix    - Bug Fix"
    echo ""
    echo "Modes:"
    echo "  (default)  - Create task in database, agent picks up via heartbeat"
    echo "  --spawn    - Create task + spawn OpenClaw session immediately"
    echo ""
    echo "Examples:"
    echo "  ./spawn-agent.sh pm 'Define roadmap Q1'"
    echo "  ./spawn-agent.sh dev 'Implement auth' --template feature-dev"
    echo "  ./spawn-agent.sh qa 'Test payment' --spawn"
    exit 1
fi

# Validate agent type
case $AGENT_TYPE in
    pm|analyst|architect|dev|ux-designer|scrum-master|qa|tech-writer|solo-dev)
        ;;
    *)
        echo "Error: Invalid agent type: $AGENT_TYPE"
        exit 1
        ;;
esac

echo "🚀 AI Team Agent Spawner"
echo "========================"

# Map agent type to config file and model
case $AGENT_TYPE in
    pm)
        AGENT_FILE="${WORKSPACE}/agents/pm.md"
        AGENT_ID="agent-pm-001"
        MODEL="anthropic/claude-opus-4-5"
        LABEL="pm-$(date +%s)"
        ;;
    analyst)
        AGENT_FILE="${WORKSPACE}/agents/analyst.md"
        AGENT_ID="agent-analyst-001"
        MODEL="anthropic/claude-sonnet-4-5"
        LABEL="analyst-$(date +%s)"
        ;;
    architect)
        AGENT_FILE="${WORKSPACE}/agents/architect.md"
        AGENT_ID="agent-architect-001"
        MODEL="anthropic/claude-opus-4-5"
        LABEL="architect-$(date +%s)"
        ;;
    dev)
        AGENT_FILE="${WORKSPACE}/agents/dev.md"
        AGENT_ID="agent-dev-001"
        MODEL="kimi-code/kimi-for-coding"
        LABEL="dev-$(date +%s)"
        ;;
    ux-designer)
        AGENT_FILE="${WORKSPACE}/agents/ux-designer.md"
        AGENT_ID="agent-ux-001"
        MODEL="anthropic/claude-sonnet-4-5"
        LABEL="ux-$(date +%s)"
        ;;
    scrum-master)
        AGENT_FILE="${WORKSPACE}/agents/scrum-master.md"
        AGENT_ID="agent-sm-001"
        MODEL="anthropic/claude-sonnet-4-5"
        LABEL="sm-$(date +%s)"
        ;;
    qa)
        AGENT_FILE="${WORKSPACE}/agents/qa-engineer.md"
        AGENT_ID="agent-qa-001"
        MODEL="anthropic/claude-sonnet-4-5"
        LABEL="qa-$(date +%s)"
        ;;
    tech-writer)
        AGENT_FILE="${WORKSPACE}/agents/tech-writer.md"
        AGENT_ID="agent-writer-001"
        MODEL="anthropic/claude-sonnet-4-5"
        LABEL="writer-$(date +%s)"
        ;;
    solo-dev)
        AGENT_FILE="${WORKSPACE}/agents/solo-dev.md"
        AGENT_ID="agent-solo-001"
        MODEL="kimi-code/kimi-for-coding"
        LABEL="solo-$(date +%s)"
        ;;
esac

# Build task description with template if specified
if [ -n "$TEMPLATE" ]; then
    TEMPLATE_FILE="${WORKSPACE}/agents/templates/template-${TEMPLATE}.md"
    if [ -f "$TEMPLATE_FILE" ]; then
        echo "📄 Using template: ${TEMPLATE}"
        # Read template and append task description
        TASK_DESCRIPTION="$(cat "$TEMPLATE_FILE")

---

## Task Assignment

**Task:** ${TASK_DESC}
**Assigned to:** ${AGENT_TYPE}
**Created:** $(date '+%Y-%m-%d %H:%M:%S')"
    else
        echo "⚠️  Template not found: ${TEMPLATE_FILE}"
        echo "   Using default description"
        TASK_DESCRIPTION="${TASK_DESC}"
    fi
else
    TASK_DESCRIPTION="${TASK_DESC}"
fi

echo ""
echo "📋 Task Details:"
echo "   Agent: ${AGENT_TYPE}"
echo "   Agent ID: ${AGENT_ID}"
echo "   Model: ${MODEL}"
echo "   Mode: ${SPAWN_MODE}"
echo ""

# Step 1: Create task in database
echo "📝 Step 1: Creating task in database..."

# Use Python to create task (more reliable than raw SQL)
python3 << EOF
import sqlite3
import sys
from datetime import datetime

db_path = "${WORKSPACE}/team.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Generate task ID
today = datetime.now()
task_id = f"T-{today.strftime('%Y%m%d')}-{cursor.execute('SELECT COUNT(*) FROM tasks WHERE id LIKE ?', (f'T-{today.strftime(\"%Y%m%d\")}%',)).fetchone()[0] + 1:03d}"

# Insert task
cursor.execute('''
    INSERT INTO tasks (id, title, description, assignee_id, status, priority, created_at, updated_at)
    VALUES (?, ?, ?, ?, 'todo', 'normal', ?, ?)
''', (
    task_id,
    "${TASK_DESC}",
    """${TASK_DESCRIPTION}""",
    "${AGENT_ID}",
    today.isoformat(),
    today.isoformat()
))

conn.commit()
conn.close()
print(f"✅ Task created: {task_id}")
EOF

# Step 2: Spawn session if requested
if [ "$SPAWN_MODE" = "session" ]; then
    echo ""
    echo "🤖 Step 2: Spawning OpenClaw session..."
    
    # Read agent config
    if [ -f "$AGENT_FILE" ]; then
        AGENT_CONTEXT=$(cat "$AGENT_FILE")
    else
        echo "⚠️  Agent config not found: ${AGENT_FILE}"
        AGENT_CONTEXT="Role: ${AGENT_TYPE}"
    fi
    
    # Build full task prompt
    FULL_TASK="${AGENT_CONTEXT}

---

## Assigned Task

${TASK_DESCRIPTION}

---

## Deliverables
1. Read and follow your agent configuration
2. Complete the assigned task
3. Update task status in team.db as you progress:
   - status: 'in_progress' when starting
   - status: 'review' when ready for review
   - status: 'done' when complete
4. Save any outputs to appropriate location
5. Report back to orchestrator with summary

## Database
- Location: ${WORKSPACE}/team.db
- Your task ID: See stdout above
- Update command: ./team_db.py task update <id> --status <status>
"
    
    echo "   Label: ${LABEL}"
    echo "   Model: ${MODEL}"
    echo ""
    
    # Check if we can use sessions_spawn via API
    # For now, print instructions
    echo "📤 To spawn this agent, run:"
    echo ""
    echo "openclaw sessions spawn \\"
    echo "  --agent-id '${AGENT_TYPE}' \\"
    echo "  --model '${MODEL}' \\"
    echo "  --label '${LABEL}' \\"
    echo "  --task '${FULL_TASK}'"
    echo ""
    echo "⚠️  Note: OpenClaw CLI spawn requires active gateway connection"
else
    echo ""
    echo "⏳ Task created in database. Agent will pick up via heartbeat."
    echo "   To spawn immediately, use: --spawn flag"
fi

echo ""
echo "✅ Done!"
echo "📊 Monitor with: ./team_db.py tasks list"
