#!/usr/bin/env python3
"""
Agent Memory Writer - For subagents to update their working memory
Subagents call this to save progress, blockers, and next steps
"""

import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

os.environ['TZ'] = 'Asia/Bangkok'
DB_PATH = Path(__file__).parent / "team.db"

def update_working_memory(agent_id: str, task_id: str = None, 
                          working_notes: str = None, 
                          blockers: str = None, 
                          next_steps: str = None):
    """Update agent's working memory during task execution"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Build update fields
    updates = []
    params = []
    
    if task_id is not None:
        updates.append("current_task_id = ?")
        params.append(task_id)
    if working_notes is not None:
        updates.append("working_notes = ?")
        params.append(working_notes)
    if blockers is not None:
        updates.append("blockers = ?")
        params.append(blockers)
    if next_steps is not None:
        updates.append("next_steps = ?")
        params.append(next_steps)
    
    if not updates:
        print("❌ No fields to update")
        return False
    
    updates.append("last_updated = datetime('now', 'localtime')")
    params.append(agent_id)
    
    cursor.execute(f'''
        UPDATE agent_working_memory 
        SET {', '.join(updates)}
        WHERE agent_id = ?
    ''', params)
    
    # If no row exists, insert one
    if cursor.rowcount == 0:
        cursor.execute('''
            INSERT INTO agent_working_memory (agent_id, current_task_id, working_notes, blockers, next_steps)
            VALUES (?, ?, ?, ?, ?)
        ''', (agent_id, task_id, working_notes or '', blockers or '', next_steps or ''))
    
    conn.commit()
    conn.close()
    print(f"✅ Working memory updated for {agent_id}")
    return True

def add_learning(agent_id: str, learning: str):
    """Add a learning to agent's context"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Get existing learnings
    cursor.execute('SELECT learnings FROM agent_context WHERE agent_id = ?', (agent_id,))
    row = cursor.fetchone()
    existing = row[0] if row else ""
    
    # Prepend new learning with timestamp
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    new_entry = f"[{timestamp}] {learning}"
    
    if existing:
        updated = f"{new_entry}\n{existing}"
    else:
        updated = new_entry
    
    # Keep only last 50 entries
    lines = [l for l in updated.split('\n') if l.strip()][:50]
    updated = '\n'.join(lines)
    
    cursor.execute('''
        UPDATE agent_context 
        SET learnings = ?, last_updated = datetime('now', 'localtime')
        WHERE agent_id = ?
    ''', (updated, agent_id))
    
    conn.commit()
    conn.close()
    print(f"✅ Learning added for {agent_id}")
    return True

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Agent Memory Writer')
    subparsers = parser.add_subparsers(dest='command')
    
    # Update working memory
    wm_parser = subparsers.add_parser('working', help='Update working memory')
    wm_parser.add_argument('agent_id', help='Agent ID (e.g., dev, qa)')
    wm_parser.add_argument('--task', help='Current task ID')
    wm_parser.add_argument('--notes', help='Working notes')
    wm_parser.add_argument('--blockers', help='Current blockers')
    wm_parser.add_argument('--next', help='Next steps')
    
    # Add learning
    learn_parser = subparsers.add_parser('learn', help='Add learning')
    learn_parser.add_argument('agent_id', help='Agent ID')
    learn_parser.add_argument('learning', help='Learning text')
    
    args = parser.parse_args()
    
    if args.command == 'working':
        update_working_memory(
            args.agent_id, 
            args.task, 
            args.notes, 
            args.blockers, 
            args.next
        )
    elif args.command == 'learn':
        add_learning(args.agent_id, args.learning)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
