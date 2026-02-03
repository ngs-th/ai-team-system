#!/usr/bin/env python3
"""
AI Team Agent Sync
Periodic sync to ensure database matches actual agent states
"""

import sqlite3
import subprocess
import json
from datetime import datetime, timedelta
from pathlib import Path
from audit_log import AuditLogger

DB_PATH = Path(__file__).parent / "team.db"
audit = AuditLogger()

def get_active_sessions():
    """Get all active subagent sessions"""
    try:
        result = subprocess.run(
            ['openclaw', 'sessions_list', '--active-minutes', '60'],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            sessions = []
            for line in result.stdout.split('\n'):
                if 'standby' in line or 'subagent' in line:
                    sessions.append(line)
            return sessions
    except Exception as e:
        print(f"[Warning] Could not get sessions: {e}")
    return []

def check_stale_agents():
    """Find agents that haven't heartbeat in a while"""
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    cursor = conn.cursor()
    
    # Find agents active but no heartbeat in 30 minutes
    cursor.execute('''
        SELECT id, name, current_task_id, last_heartbeat
        FROM agents
        WHERE status = 'active'
        AND last_heartbeat < datetime('now', '-30 minutes')
    ''')
    
    stale = cursor.fetchall()
    conn.close()
    return stale

def reset_stale_agent(agent_id: str, task_id: str = None):
    """Reset stale agent to idle"""
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
    
    # If has task, block it
    if task_id:
        cursor.execute('''
            UPDATE tasks 
            SET status = 'blocked',
                blocked_reason = 'Agent timeout - no heartbeat for 30+ minutes',
                updated_at = datetime('now')
            WHERE id = ?
        ''', (task_id,))
        
        cursor.execute('''
            INSERT INTO task_history (task_id, agent_id, action, notes)
            VALUES (?, ?, 'blocked', 'Auto-blocked due to agent timeout')
        ''', (task_id, agent_id))
    
    conn.commit()
    conn.close()
    
    # Audit log (after closing connection to avoid locks)
    audit.log_stale_detection(agent_id, task_id, '30+ minutes ago')
    audit.log_status_change(agent_id, old_status, 'idle', 'Auto-reset due to timeout')
    if task_id:
        audit.log_task_update(task_id, agent_id, 'in_progress', 'blocked', 'Agent timeout')
    
    print(f"✅ Reset stale agent: {agent_id}")

def sync_agent_states():
    """Main sync function"""
    print("=" * 60)
    print("🔄 AI Team Agent Sync")
    print("=" * 60)
    print(f"Time: {datetime.now()}")
    print()
    
    # Check for stale agents
    stale = check_stale_agents()
    if stale:
        print(f"⚠️  Found {len(stale)} stale agents:")
        for agent in stale:
            agent_id, name, task_id, last_hb = agent
            print(f"  - {name} ({agent_id}): Last heartbeat {last_hb}")
            reset_stale_agent(agent_id, task_id)
    else:
        print("✅ No stale agents found")
    
    # Get active sessions
    sessions = get_active_sessions()
    print(f"\n📊 Active sessions: {len(sessions)}")
    
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
