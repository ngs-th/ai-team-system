#!/usr/bin/env python3
"""
AI Team Agent Sync
Periodic sync to ensure database matches actual agent states
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from audit_log import AuditLogger
from agent_runtime import get_openclaw_session_last_seen, runtime_supports_sessions

DB_PATH = Path(__file__).parent / "team.db"
audit = AuditLogger()

SESSION_ACTIVE_MINUTES = 20


def parse_sqlite_dt(value: str):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None

def check_stale_agents():
    """Find agents that are active but have no recent session activity."""
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT a.id, a.name, a.current_task_id, a.last_heartbeat, a.status, t.status as task_status
        FROM agents a
        LEFT JOIN tasks t ON t.id = a.current_task_id
    ''')
    agents = cursor.fetchall()
    conn.close()

    stale = []
    now = datetime.now()
    for agent_id, name, task_id, last_hb, status, task_status in agents:
        hb_dt = parse_sqlite_dt(last_hb)
        heartbeat_active = (
            hb_dt is not None and
            now - hb_dt <= timedelta(minutes=SESSION_ACTIVE_MINUTES)
        )

        last_seen = get_openclaw_session_last_seen(agent_id) if runtime_supports_sessions() else None
        session_active = (
            last_seen is not None and
            now - last_seen <= timedelta(minutes=SESSION_ACTIVE_MINUTES)
        ) if runtime_supports_sessions() else False

        # OpenClaw mode: require active session OR recent heartbeat.
        # Other runtimes: rely on heartbeat only.
        runtime_active = (session_active or heartbeat_active) if runtime_supports_sessions() else heartbeat_active
        if status == 'active' and not runtime_active:
            stale.append((agent_id, name, task_id, last_hb, last_seen))
    return stale

def reset_stale_agent(agent_id: str, task_id: str = None, reason: str = "No active session"):
    """Reset stale agent to idle and return task to appropriate queue."""
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    cursor = conn.cursor()
    
    # Get old status for audit
    cursor.execute('SELECT status FROM agents WHERE id = ?', (agent_id,))
    row = cursor.fetchone()
    old_status = row[0] if row else 'unknown'
    
    # Reset agent
    cursor.execute('''
        UPDATE agents 
        SET status = 'idle',
            current_task_id = NULL
        WHERE id = ?
    ''', (agent_id,))
    
    task_transition = None

    # If has task, move back to queue based on current stage
    if task_id:
        cursor.execute('SELECT status FROM tasks WHERE id = ?', (task_id,))
        row = cursor.fetchone()
        task_status = row[0] if row else None
        if task_status == 'in_progress':
            cursor.execute('''
                UPDATE tasks 
                SET status = 'todo',
                    started_at = NULL,
                    blocked_reason = NULL,
                    blocked_at = NULL,
                    todo_at = datetime('now', 'localtime'),
                    updated_at = datetime('now', 'localtime')
                WHERE id = ?
            ''', (task_id,))
            
            cursor.execute('''
                INSERT INTO task_history (task_id, agent_id, action, old_status, new_status, notes)
                VALUES (?, ?, 'updated', 'in_progress', 'todo', ?)
            ''', (task_id, agent_id, f"Auto-reset: {reason}"))
            task_transition = ('in_progress', 'todo')
        elif task_status == 'reviewing':
            cursor.execute('''
                UPDATE tasks
                SET status = 'review',
                    blocked_reason = NULL,
                    blocked_at = NULL,
                    updated_at = datetime('now', 'localtime')
                WHERE id = ?
            ''', (task_id,))

            cursor.execute('''
                INSERT INTO task_history (task_id, agent_id, action, old_status, new_status, notes)
                VALUES (?, ?, 'updated', 'reviewing', 'review', ?)
            ''', (task_id, agent_id, f"Auto-reset reviewer: {reason}"))
            task_transition = ('reviewing', 'review')
    
    conn.commit()
    conn.close()
    
    # Audit log (after closing connection to avoid locks)
    audit.log_stale_detection(agent_id, task_id, reason)
    audit.log_status_change(agent_id, old_status, 'idle', 'Auto-reset due to timeout')
    if task_id and task_transition:
        audit.log_task_update(task_id, agent_id, task_transition[0], task_transition[1], reason)
    
    print(f"✅ Reset stale agent: {agent_id}")

def sync_agent_states():
    """Main sync function"""
    print("=" * 60)
    print("🔄 AI Team Agent Sync")
    print("=" * 60)
    print(f"Time: {datetime.now()}")
    print()
    
    # Check for stale agents (no active sessions)
    stale = check_stale_agents()
    if stale:
        print(f"⚠️  Found {len(stale)} stale agents:")
        for agent in stale:
            agent_id, name, task_id, last_hb, last_seen = agent
            print(f"  - {name} ({agent_id}): Last session {last_seen} | Last heartbeat {last_hb}")
            reset_stale_agent(agent_id, task_id, reason="No active agent session")
    else:
        print("✅ No stale agents found")

    # Move orphaned in_progress tasks back to todo when no active session
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.id, t.assignee_id, t.updated_at, a.status
        FROM tasks t
        JOIN agents a ON t.assignee_id = a.id
        WHERE t.status = 'in_progress'
    ''')
    orphaned = []
    now = datetime.now()
    for task_id, agent_id, updated_at, agent_status in cursor.fetchall():
        hb_row = cursor.execute('SELECT last_heartbeat FROM agents WHERE id = ?', (agent_id,)).fetchone()
        hb_dt = parse_sqlite_dt(hb_row[0]) if hb_row else None
        heartbeat_active = (
            hb_dt is not None and
            now - hb_dt <= timedelta(minutes=SESSION_ACTIVE_MINUTES)
        )
        last_seen = get_openclaw_session_last_seen(agent_id) if runtime_supports_sessions() else None
        session_active = (
            last_seen is not None and
            now - last_seen <= timedelta(minutes=SESSION_ACTIVE_MINUTES)
        ) if runtime_supports_sessions() else False
        runtime_active = (session_active or heartbeat_active) if runtime_supports_sessions() else heartbeat_active
        last_update = parse_sqlite_dt(updated_at)
        stale_update = (last_update is None) or (now - last_update > timedelta(minutes=SESSION_ACTIVE_MINUTES))
        if (not runtime_active) and stale_update:
            orphaned.append((task_id, agent_id))

    for task_id, agent_id in orphaned:
        cursor.execute('''
            UPDATE tasks 
            SET status = 'todo',
                started_at = NULL,
                blocked_reason = NULL,
                blocked_at = NULL,
                todo_at = datetime('now', 'localtime'),
                updated_at = datetime('now', 'localtime')
            WHERE id = ?
        ''', (task_id,))
        cursor.execute('''
            INSERT INTO task_history (task_id, agent_id, action, old_status, new_status, notes)
            VALUES (?, ?, 'updated', 'in_progress', 'todo', 'Auto-reset: no active agent session')
        ''', (task_id, agent_id))

    conn.commit()
    conn.close()

    # Summarize active sessions
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    cursor = conn.cursor()
    cursor.execute('SELECT id, status, last_heartbeat FROM agents')
    agents = cursor.fetchall()
    conn.close()
    now = datetime.now()
    active_count = 0
    for agent_id, status, last_hb in agents:
        if runtime_supports_sessions():
            last_seen = get_openclaw_session_last_seen(agent_id)
            if last_seen and now - last_seen <= timedelta(minutes=SESSION_ACTIVE_MINUTES):
                active_count += 1
        else:
            # Runtime without session API: use DB heartbeat as liveness proxy.
            hb_dt = parse_sqlite_dt(last_hb)
            if hb_dt and now - hb_dt <= timedelta(minutes=SESSION_ACTIVE_MINUTES):
                active_count += 1
    metric = "sessions" if runtime_supports_sessions() else "heartbeats"
    print(f"\n📊 Active agent {metric} (last {SESSION_ACTIVE_MINUTES}m): {active_count}")
    
    print("\n" + "=" * 60)
    print("✅ Sync complete")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='AI Team Agent Sync')
    parser.add_argument('--run', action='store_true', help='Run sync')
    args = parser.parse_args()
    
    if args.run:
        sync_agent_states()
    else:
        sync_agent_states()

if __name__ == '__main__':
    main()
