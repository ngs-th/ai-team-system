#!/bin/bash
#
# 💓 AI Team Heartbeat Updater
# Updates agent heartbeat timestamps in the database
# Usage: update-heartbeat.sh [agent_id] [--background]
#

set -e

# Configuration
DB_PATH="${HOME}/clawd/projects/ai-team/team.db"

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }

# Check if sqlite3 is available
if ! command -v sqlite3 &> /dev/null; then
    log_error "sqlite3 is required but not installed."
    exit 1
fi

# Check if database exists
if [[ ! -f "$DB_PATH" ]]; then
    log_error "Database not found: $DB_PATH"
    exit 1
fi

# ====================
# Heartbeat Functions
# ====================

# Update heartbeat for a specific agent
update_heartbeat() {
    local agent_id="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    if [[ -z "$agent_id" ]]; then
        log_error "Agent ID required"
        return 1
    fi
    
    # Update the heartbeat
    sqlite3 "$DB_PATH" << EOF
UPDATE agents 
SET last_heartbeat = '$timestamp', 
    updated_at = '$timestamp'
WHERE id = '$agent_id';
EOF
    
    if [[ $? -eq 0 ]]; then
        log_success "Heartbeat updated for $agent_id at $timestamp"
        return 0
    else
        log_error "Failed to update heartbeat for $agent_id"
        return 1
    fi
}

# Update heartbeat and set agent status to active
update_heartbeat_on_task_start() {
    local agent_id="$1"
    local task_id="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    if [[ -z "$agent_id" ]]; then
        log_error "Agent ID required"
        return 1
    fi
    
    if [[ -z "$task_id" ]]; then
        log_warn "No task_id provided, updating heartbeat only"
    fi
    
    sqlite3 "$DB_PATH" << EOF
UPDATE agents 
SET last_heartbeat = '$timestamp',
    status = 'active',
    current_task_id = COALESCE('$task_id', current_task_id),
    updated_at = '$timestamp'
WHERE id = '$agent_id';
EOF
    
    if [[ $? -eq 0 ]]; then
        log_success "Agent $agent_id started task $task_id, heartbeat updated"
        return 0
    else
        log_error "Failed to update agent $agent_id"
        return 1
    fi
}

# Start periodic heartbeat updates (every 10 minutes)
start_periodic_heartbeat() {
    local agent_id="$1"
    local interval_minutes="${2:-10}"
    local pid_file="/tmp/heartbeat-${agent_id}.pid"
    
    if [[ -z "$agent_id" ]]; then
        log_error "Agent ID required for periodic heartbeat"
        exit 1
    fi
    
    # Check if already running
    if [[ -f "$pid_file" ]]; then
        local old_pid=$(cat "$pid_file" 2>/dev/null || echo "")
        if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
            log_warn "Periodic heartbeat already running for $agent_id (PID: $old_pid)"
            return 1
        fi
    fi
    
    log_info "Starting periodic heartbeat for $agent_id (every ${interval_minutes} min)"
    
    # Run in background
    (
        while true; do
            local ts=$(date '+%Y-%m-%d %H:%M:%S')
            sqlite3 "$DB_PATH" "UPDATE agents SET last_heartbeat = '$ts', updated_at = '$ts' WHERE id = '$agent_id';" 2>/dev/null
            sleep $((interval_minutes * 60))
        done
    ) &
    
    local bg_pid=$!
    echo $bg_pid > "$pid_file"
    log_success "Periodic heartbeat started (PID: $bg_pid)"
}

# Stop periodic heartbeat
stop_periodic_heartbeat() {
    local agent_id="$1"
    local pid_file="/tmp/heartbeat-${agent_id}.pid"
    
    if [[ -f "$pid_file" ]]; then
        local pid=$(cat "$pid_file" 2>/dev/null || echo "")
        if [[ -n "$pid" ]]; then
            kill "$pid" 2>/dev/null || true
            rm -f "$pid_file"
            log_success "Stopped periodic heartbeat for $agent_id"
        fi
    else
        log_warn "No periodic heartbeat found for $agent_id"
    fi
}

# Update heartbeat on task completion
update_heartbeat_on_task_complete() {
    local agent_id="$1"
    local task_id="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    if [[ -z "$agent_id" ]]; then
        log_error "Agent ID required"
        return 1
    fi
    
    # Update agent heartbeat and set to idle if no other tasks
    sqlite3 "$DB_PATH" << EOF
UPDATE agents 
SET last_heartbeat = '$timestamp',
    status = CASE 
        WHEN (SELECT COUNT(*) FROM tasks WHERE assignee_id = '$agent_id' AND status IN ('todo', 'in_progress')) = 0 
        THEN 'idle' 
        ELSE 'active' 
    END,
    current_task_id = CASE 
        WHEN current_task_id = '$task_id' 
        THEN NULL 
        ELSE current_task_id 
    END,
    total_tasks_completed = total_tasks_completed + 1,
    updated_at = '$timestamp'
WHERE id = '$agent_id';

UPDATE tasks 
SET status = 'done',
    completed_at = '$timestamp',
    progress = 100,
    updated_at = '$timestamp'
WHERE id = '$task_id';

INSERT INTO task_history (task_id, agent_id, action, new_status, new_progress, notes)
VALUES ('$task_id', '$agent_id', 'completed', 'done', 100, 'Task completed via heartbeat system');
EOF
    
    if [[ $? -eq 0 ]]; then
        log_success "Task $task_id completed by $agent_id"
        return 0
    else
        log_error "Failed to complete task $task_id"
        return 1
    fi
}

# Get agent status
get_agent_status() {
    local agent_id="$1"
    
    if [[ -z "$agent_id" ]]; then
        # Show all agents
        sqlite3 "$DB_PATH" << EOF
.headers on
.mode column
SELECT id, name, status, current_task_id, 
       strftime('%H:%M', last_heartbeat) as last_seen,
       ROUND((strftime('%s', 'now') - strftime('%s', last_heartbeat)) / 60.0, 0) || 'm ago' as ago
FROM agents
ORDER BY last_heartbeat DESC;
EOF
    else
        # Show specific agent
        sqlite3 "$DB_PATH" << EOF
SELECT * FROM v_agent_status WHERE id = '$agent_id';
EOF
    fi
}

# ====================
# Main
# ====================
main() {
    local command="${1:-help}"
    local agent_id="$2"
    local task_id="$3"
    
    case "$command" in
        update|ping)
            update_heartbeat "$agent_id"
            ;;
        start-task)
            update_heartbeat_on_task_start "$agent_id" "$task_id"
            ;;
        complete|done)
            update_heartbeat_on_task_complete "$agent_id" "$task_id"
            ;;
        periodic-start)
            start_periodic_heartbeat "$agent_id"
            ;;
        periodic-stop)
            stop_periodic_heartbeat "$agent_id"
            ;;
        status)
            get_agent_status "$agent_id"
            ;;
        *)
            cat << EOF
💓 AI Team Heartbeat Updater

Usage: $0 <command> [agent_id] [task_id]

Commands:
  update <agent_id>              Update heartbeat for agent
  start-task <agent_id> [task]   Agent starts working on task
  complete <agent_id> <task>     Mark task as complete
  periodic-start <agent_id>      Start 10-min heartbeat updates (background)
  periodic-stop <agent_id>       Stop background heartbeat
  status [agent_id]              Show agent status (all if no ID)

Examples:
  # Update heartbeat for agent 'dev'
  $0 update dev

  # Agent 'architect' starts task T-123
  $0 start-task architect T-123

  # Start periodic heartbeat (every 10 min)
  $0 periodic-start dev

  # Complete task
  $0 complete dev T-123

  # Check all agent statuses
  $0 status

Database:
  $DB_PATH

EOF
            ;;
    esac
}

main "$@"
