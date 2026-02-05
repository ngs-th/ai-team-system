#!/usr/bin/env python3
"""
AI Team Memory Maintenance
Automatically maintain agent contexts and clean up stale data
"""

import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict
import time

os.environ['TZ'] = 'Asia/Bangkok'
try:
    time.tzset()
except AttributeError:
    pass

DB_PATH = Path(__file__).parent / "team.db"

class MemoryMaintenance:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self.actions = []
        
    def close(self):
        self.conn.close()
        
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        self.close()

    def reset_stale_agents(self) -> int:
        """Reset agents that are active but haven't sent heartbeat > 1 hour"""
        cursor = self.conn.cursor()
        
        # Find stale agents
        cursor.execute('''
            SELECT a.id, a.name, a.current_task_id, t.title as task_title
            FROM agents a
            LEFT JOIN tasks t ON a.current_task_id = t.id
            WHERE a.status = 'active'
            AND (a.last_heartbeat IS NULL OR a.last_heartbeat < datetime('now', '-1 hour'))
        ''')
        
        stale_agents = [dict(row) for row in cursor.fetchall()]
        reset_count = 0
        
        for agent in stale_agents:
            print(f"  🔄 Resetting {agent['name']} (stale)")
            
            # Reset agent to idle
            cursor.execute('''
                UPDATE agents 
                SET status = 'idle', current_task_id = NULL, last_heartbeat = datetime('now')
                WHERE id = ?
            ''', (agent['id'],))
            
            # Move task back to todo if exists
            if agent['current_task_id']:
                cursor.execute('''
                    UPDATE tasks 
                    SET status = 'todo', assignee_id = NULL, updated_at = datetime('now')
                    WHERE id = ?
                ''', (agent['current_task_id'],))
                
                cursor.execute('''
                    INSERT INTO task_history (task_id, agent_id, action, notes)
                    VALUES (?, ?, 'updated', 'Reset: agent stale, task returned to todo')
                ''', (agent['current_task_id'], agent['id']))
            
            reset_count += 1
            self.actions.append(f"Reset {agent['name']}: stale agent")
        
        self.conn.commit()
        return reset_count

    def update_agent_learnings(self) -> int:
        """Update agent contexts with learnings from recent completed tasks"""
        cursor = self.conn.cursor()
        
        # Get agents with recent completed tasks
        cursor.execute('''
            SELECT DISTINCT a.id, a.name
            FROM agents a
            JOIN tasks t ON a.id = t.assignee_id
            WHERE t.status = 'done'
            AND t.completed_at > datetime('now', '-7 days')
        ''')
        
        agents = [dict(row) for row in cursor.fetchall()]
        update_count = 0
        
        for agent in agents:
            # Get recent completed tasks
            cursor.execute('''
                SELECT title, expected_outcome, notes
                FROM tasks
                WHERE assignee_id = ? AND status = 'done'
                AND completed_at > datetime('now', '-7 days')
                ORDER BY completed_at DESC
                LIMIT 5
            ''', (agent['id'],))
            
            tasks = cursor.fetchall()
            if not tasks:
                continue
            
            # Generate learning summary
            learnings = []
            for task in tasks:
                title = task[0]
                learnings.append(f"- Completed: {title}")
            
            new_learning = "\n".join(learnings)
            
            # Get existing learnings
            cursor.execute('''
                SELECT learnings FROM agent_context WHERE agent_id = ?
            ''', (agent['id'],))
            row = cursor.fetchone()
            existing = row[0] if row else ""
            
            # Merge learnings (keep recent 20 items)
            combined = f"{new_learning}\n{existing}" if existing else new_learning
            lines = combined.split('\n')
            # Keep only non-empty lines
            lines = [l for l in lines if l.strip()]
            # Keep last 20
            lines = lines[:20]
            updated = '\n'.join(lines)
            
            # Update agent context
            cursor.execute('''
                UPDATE agent_context 
                SET learnings = ?, last_updated = datetime('now')
                WHERE agent_id = ?
            ''', (updated, agent['id']))
            
            update_count += 1
            self.actions.append(f"Updated learnings for {agent['name']}")
        
        self.conn.commit()
        return update_count

    def archive_old_history(self) -> int:
        """Archive task history older than 30 days"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            DELETE FROM task_history
            WHERE timestamp < datetime('now', '-30 days')
        ''')
        
        deleted = cursor.rowcount
        self.conn.commit()
        
        if deleted > 0:
            self.actions.append(f"Archived {deleted} old history records")
        
        return deleted

    def run(self) -> Dict:
        """Run full maintenance"""
        print("🧠 AI Team Memory Maintenance Starting...")
        print("=" * 50)
        
        # 1. Reset stale agents
        print("\n1️⃣ Checking for stale agents...")
        stale_reset = self.reset_stale_agents()
        print(f"   Reset {stale_reset} stale agents")
        
        # 2. Update learnings
        print("\n2️⃣ Updating agent learnings...")
        learnings_updated = self.update_agent_learnings()
        print(f"   Updated {learnings_updated} agents")
        
        # 3. Archive old history
        print("\n3️⃣ Archiving old history...")
        archived = self.archive_old_history()
        print(f"   Archived {archived} records")
        
        print("\n" + "=" * 50)
        
        if self.actions:
            print("✅ Maintenance complete:")
            for action in self.actions:
                print(f"   • {action}")
        else:
            print("✅ No maintenance needed")
        
        return {
            'stale_reset': stale_reset,
            'learnings_updated': learnings_updated,
            'archived': archived,
            'actions': self.actions
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description='AI Team Memory Maintenance')
    parser.add_argument('--run', action='store_true', help='Run maintenance')
    args = parser.parse_args()
    
    with MemoryMaintenance() as mm:
        result = mm.run()


if __name__ == '__main__':
    main()
