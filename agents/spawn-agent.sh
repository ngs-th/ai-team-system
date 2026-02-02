#!/usr/bin/env bash
#
# OpenClaw Team Agent Spawner
# Usage: ./spawn-agent.sh <agent-type> <task-description>
#

set -e

AGENT_TYPE=$1
TASK_DESC=$2
WORKSPACE="${HOME}/clawd"

if [ -z "$AGENT_TYPE" ] || [ -z "$TASK_DESC" ]; then
    echo "Usage: ./spawn-agent.sh <agent-type> <task-description>"
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
    echo "Examples:"
    echo "  ./spawn-agent.sh pm 'Define product roadmap Q1'"
    echo "  ./spawn-agent.sh dev 'Implement user authentication'"
    echo "  ./spawn-agent.sh qa 'Test payment flow'"
    exit 1
fi

# Validate agent type
case $AGENT_TYPE in
    pm|analyst|architect|dev|ux-designer|scrum-master|qa|tech-writer|solo-dev)
        ;;
    *)
        echo "Error: Invalid agent type: $AGENT_TYPE"
        echo "Use: pm, analyst, architect, dev, ux-designer, scrum-master, qa, tech-writer, or solo-dev"
        exit 1
        ;;
esac

echo "🚀 Spawning ${AGENT_TYPE} agent..."
echo "   Task: ${TASK_DESC}"
echo ""

# Build agent-specific configuration
case $AGENT_TYPE in
    pm)
        AGENT_FILE="${WORKSPACE}/agents/pm.md"
        MODEL="anthropic/claude-opus-4-5"
        LABEL="pm-$(date +%s)"
        ;;
    analyst)
        AGENT_FILE="${WORKSPACE}/agents/analyst.md"
        MODEL="anthropic/claude-sonnet-4-5"
        LABEL="analyst-$(date +%s)"
        ;;
    architect)
        AGENT_FILE="${WORKSPACE}/agents/architect.md"
        MODEL="anthropic/claude-opus-4-5"
        LABEL="architect-$(date +%s)"
        ;;
    dev)
        AGENT_FILE="${WORKSPACE}/agents/dev.md"
        MODEL="kimi-code/kimi-for-coding"
        LABEL="dev-$(date +%s)"
        ;;
    ux-designer)
        AGENT_FILE="${WORKSPACE}/agents/ux-designer.md"
        MODEL="anthropic/claude-sonnet-4-5"
        LABEL="ux-$(date +%s)"
        ;;
    scrum-master)
        AGENT_FILE="${WORKSPACE}/agents/scrum-master.md"
        MODEL="anthropic/claude-sonnet-4-5"
        LABEL="sm-$(date +%s)"
        ;;
    qa)
        AGENT_FILE="${WORKSPACE}/agents/qa-engineer.md"
        MODEL="anthropic/claude-sonnet-4-5"
        LABEL="qa-$(date +%s)"
        ;;
    tech-writer)
        AGENT_FILE="${WORKSPACE}/agents/tech-writer.md"
        MODEL="anthropic/claude-sonnet-4-5"
        LABEL="writer-$(date +%s)"
        ;;
    solo-dev)
        AGENT_FILE="${WORKSPACE}/agents/solo-dev.md"
        MODEL="kimi-code/kimi-for-coding"
        LABEL="solo-$(date +%s)"
        ;;
esac

echo "📋 Agent Config: ${AGENT_FILE}"
echo "🤖 Model: ${MODEL}"
echo "🏷️  Label: ${LABEL}"
echo ""

# Create the task with agent context
TASK="
## Agent Task

**Role:** ${AGENT_TYPE} Agent
**Task:** ${TASK_DESC}

### Context
Read your agent configuration at: ${AGENT_FILE}
Follow the patterns defined there.

### Deliverables
1. Complete the assigned task
2. Save progress to memory/agents/${AGENT_TYPE}/
3. Report back to main session with:
   - Status (done/blocked)
   - Output location
   - Any issues encountered

### Checkpoint
Report progress every 10 minutes.
Save work immediately after completing sub-tasks.

### Task Details
${TASK_DESC}
"

echo "📤 Sending task to agent..."
echo ""

# Use openclaw sessions spawn (if available)
# Fallback: echo instructions
if command -v openclaw &> /dev/null; then
    openclaw sessions spawn \
        --agent-id "${AGENT_TYPE}" \
        --model "${MODEL}" \
        --label "${LABEL}" \
        --task "${TASK}"
else
    echo "⚠️  openclaw CLI not found. Manual instructions:"
    echo ""
    echo "1. Open new terminal/session"
    echo "2. Set agent context from: ${AGENT_FILE}"
    echo "3. Execute task: ${TASK_DESC}"
    echo "4. Report back to main session"
fi

echo ""
echo "✅ Agent spawn request complete"
echo "📊 Monitor with: sessions_list"
