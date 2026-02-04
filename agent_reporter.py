#!/usr/bin/env python3
"""
AI Team Agent Reporter
Allow subagents to report their status back to the main system
"""

import sqlite3
import json
import argparse
import re
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "team.db"

def report_status(agent_id: str, status: str, message: str = ""):
    """Report agent status to database"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Update agent status
    cursor.execute('''
        UPDATE agents 
        SET status = ?,
            last_heartbeat = datetime('now')
        WHERE id = ?
    ''', (status, agent_id))
    
    # Log the report
    cursor.execute('''
        INSERT INTO task_history (agent_id, action, notes)
        VALUES (?, 'status_update', ?)
    ''', (agent_id, f"Status: {status} - {message}"))
    
    conn.commit()
    conn.close()
    print(f"✅ Reported status: {status}")

def report_progress(task_id: str, progress: int, notes: str = ""):
    """Report task progress"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE tasks 
        SET progress = ?,
            notes = CASE 
                WHEN notes IS NULL OR notes = '' THEN ?
                ELSE notes || '\n' || ?
            END,
            updated_at = datetime('now', 'localtime')
        WHERE id = ?
    ''', (progress, notes, notes, task_id))
    
    # Log progress
    cursor.execute('''
        INSERT INTO task_history (task_id, action, notes)
        VALUES (?, 'updated', ?)
    ''', (task_id, f"Progress: {progress}% - {notes}"))
    
    conn.commit()
    conn.close()
    print(f"✅ Reported progress: {progress}%")

def report_start(agent_id: str, task_id: str):
    """Report that agent has started working"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Check prerequisites checklist
    cursor.execute('SELECT prerequisites FROM tasks WHERE id = ?', (task_id,))
    row = cursor.fetchone()
    prerequisites = (row[0] or '') if row else ''
    if prerequisites.strip():
        items = []
        for idx, line in enumerate(prerequisites.splitlines()):
            m = re.match(r'^\s*[-*]\s+\[(x| )\]\s+(.*)$', line, re.IGNORECASE)
            if not m:
                continue
            items.append((m.group(1).lower() == 'x', m.group(2).strip()))
        if not items:
            reason = "Prerequisites must be a checklist (- [ ] item)."
            cursor.execute('''
                UPDATE tasks
                SET status = 'blocked',
                    blocked_reason = ?,
                    blocked_at = datetime('now', 'localtime'),
                    updated_at = datetime('now', 'localtime')
                WHERE id = ?
            ''', (reason, task_id))
            cursor.execute('''
                INSERT INTO task_history (task_id, agent_id, action, notes)
                VALUES (?, ?, 'blocked', ?)
            ''', (task_id, agent_id, reason))
            # release agent
            cursor.execute('''
                UPDATE agents
                SET status = 'idle', current_task_id = NULL,
                    updated_at = datetime('now', 'localtime')
                WHERE id = ?
            ''', (agent_id,))
            conn.commit()
            conn.close()
            print(f"⚠️ Task {task_id} blocked: {reason}")
            return
        unchecked = [text for checked, text in items if not checked]
        if unchecked:
            reason = "Prerequisites not checked: " + "; ".join(unchecked)
            cursor.execute('''
                UPDATE tasks
                SET status = 'blocked',
                    blocked_reason = ?,
                    blocked_at = datetime('now', 'localtime'),
                    updated_at = datetime('now', 'localtime')
                WHERE id = ?
            ''', (reason, task_id))
            cursor.execute('''
                INSERT INTO task_history (task_id, agent_id, action, notes)
                VALUES (?, ?, 'blocked', ?)
            ''', (task_id, agent_id, reason))
            cursor.execute('''
                UPDATE agents
                SET status = 'idle', current_task_id = NULL,
                    updated_at = datetime('now', 'localtime')
                WHERE id = ?
            ''', (agent_id,))
            conn.commit()
            conn.close()
            print(f"⚠️ Task {task_id} blocked: {reason}")
            return
    
    # Update agent
    cursor.execute('''
        UPDATE agents 
        SET status = 'active',
            current_task_id = ?,
            last_heartbeat = datetime('now', 'localtime')
        WHERE id = ?
    ''', (task_id, agent_id))
    
    # Update task
    cursor.execute('''
        UPDATE tasks 
        SET status = 'in_progress',
            started_at = datetime('now', 'localtime'),
            in_progress_at = datetime('now', 'localtime'),
            updated_at = datetime('now', 'localtime')
        WHERE id = ?
    ''', (task_id,))
    
    # Log
    cursor.execute('''
        INSERT INTO task_history (task_id, agent_id, action, notes)
        VALUES (?, ?, 'started', 'Agent started working on task')
    ''', (task_id, agent_id))

    # Auto-bootstrap working memory to prevent immediate review-gate failure.
    cursor.execute('''
        UPDATE agent_working_memory
        SET current_task_id = ?,
            working_notes = CASE
                WHEN working_notes IS NULL OR trim(working_notes) = '' THEN 'Auto-init: task started'
                ELSE working_notes
            END,
            blockers = COALESCE(blockers, ''),
            next_steps = CASE
                WHEN next_steps IS NULL OR trim(next_steps) = '' THEN 'Begin work and post first progress update'
                ELSE next_steps
            END,
            last_updated = datetime('now', 'localtime')
        WHERE agent_id = ?
    ''', (task_id, agent_id))
    if cursor.rowcount == 0:
        cursor.execute('''
            INSERT INTO agent_working_memory
            (agent_id, current_task_id, working_notes, blockers, next_steps, last_updated)
            VALUES (?, ?, 'Auto-init: task started', '', 'Begin work and post first progress update', datetime('now', 'localtime'))
        ''', (agent_id, task_id))
    
    conn.commit()
    conn.close()
    print(f"✅ Reported start: {agent_id} working on {task_id}")

def report_complete(agent_id: str, task_id: str, summary: str = ""):
    """Report task completion"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Prerequisites must be checked before completion/review.
    cursor.execute('SELECT prerequisites FROM tasks WHERE id = ?', (task_id,))
    row = cursor.fetchone()
    prerequisites = (row[0] or '') if row else ''
    if prerequisites.strip():
        items = []
        for line in prerequisites.splitlines():
            m = re.match(r'^\s*[-*]\s+\[(x| )\]\s+(.*)$', line, re.IGNORECASE)
            if not m:
                continue
            items.append((m.group(1).lower() == 'x', m.group(2).strip()))
        if not items:
            reason = "Prerequisites must be a checklist (- [ ] item)."
            cursor.execute('''
                UPDATE tasks
                SET status = 'blocked',
                    blocked_reason = ?,
                    blocked_at = datetime('now', 'localtime'),
                    updated_at = datetime('now', 'localtime')
                WHERE id = ?
            ''', (reason, task_id))
            cursor.execute('''
                UPDATE agents
                SET status = 'idle', current_task_id = NULL, updated_at = datetime('now', 'localtime')
                WHERE id = ?
            ''', (agent_id,))
            cursor.execute('''
                INSERT INTO task_history (task_id, agent_id, action, notes)
                VALUES (?, ?, 'blocked', ?)
            ''', (task_id, agent_id, reason))
            conn.commit()
            conn.close()
            print(f"⚠️ Task {task_id} blocked: {reason}")
            return
        unchecked = [text for checked, text in items if not checked]
        if unchecked:
            reason = "Cannot complete task: prerequisites not checked -> " + "; ".join(unchecked)
            cursor.execute('''
                UPDATE tasks
                SET status = 'blocked',
                    blocked_reason = ?,
                    blocked_at = datetime('now', 'localtime'),
                    updated_at = datetime('now', 'localtime')
                WHERE id = ?
            ''', (reason, task_id))
            cursor.execute('''
                UPDATE agents
                SET status = 'idle', current_task_id = NULL, updated_at = datetime('now', 'localtime')
                WHERE id = ?
            ''', (agent_id,))
            cursor.execute('''
                INSERT INTO task_history (task_id, agent_id, action, notes)
                VALUES (?, ?, 'blocked', ?)
            ''', (task_id, agent_id, reason))
            conn.commit()
            conn.close()
            print(f"⚠️ Task {task_id} blocked: {reason}")
            return
    
    # Update agent
    cursor.execute('''
        UPDATE agents 
        SET status = 'idle',
            current_task_id = NULL,
            total_tasks_completed = total_tasks_completed + 1,
            last_heartbeat = datetime('now')
        WHERE id = ?
    ''', (agent_id,))
    
    # Update task
    cursor.execute('''
        UPDATE tasks 
        SET status = 'review',
            progress = 100,
            completed_at = datetime('now', 'localtime'),
            review_at = datetime('now', 'localtime'),
            updated_at = datetime('now', 'localtime')
        WHERE id = ?
    ''', (task_id,))
    
    # Log
    cursor.execute('''
        INSERT INTO task_history (task_id, agent_id, action, notes)
        VALUES (?, ?, 'completed', ?)
    ''', (task_id, agent_id, summary or 'Task completed'))
    
    conn.commit()
    conn.close()
    print(f"✅ Reported completion: {task_id}")

def heartbeat(agent_id: str):
    """Send heartbeat to show agent is still alive"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE agents 
        SET last_heartbeat = datetime('now')
        WHERE id = ?
    ''', (agent_id,))
    
    conn.commit()
    conn.close()
    print(f"💓 Heartbeat: {agent_id}")

def main():
    parser = argparse.ArgumentParser(description='AI Team Agent Reporter')
    parser.add_argument('action', choices=['start', 'progress', 'complete', 'status', 'heartbeat'])
    parser.add_argument('--agent', required=True, help='Agent ID')
    parser.add_argument('--task', help='Task ID')
    parser.add_argument('--progress', type=int, help='Progress percentage (0-100)')
    parser.add_argument('--message', default='', help='Message or notes')
    parser.add_argument('--status', help='Status (idle, active, etc.)')
    
    args = parser.parse_args()
    
    if args.action == 'start':
        if not args.task:
            print("❌ --task required for start")
            return
        report_start(args.agent, args.task)
    
    elif args.action == 'progress':
        if not args.task or args.progress is None:
            print("❌ --task and --progress required")
            return
        report_progress(args.task, args.progress, args.message)
    
    elif args.action == 'complete':
        if not args.task:
            print("❌ --task required for complete")
            return
        report_complete(args.agent, args.task, args.message)
    
    elif args.action == 'status':
        if not args.status:
            print("❌ --status required")
            return
        report_status(args.agent, args.status, args.message)
    
    elif args.action == 'heartbeat':
        heartbeat(args.agent)

if __name__ == '__main__':
    main()
