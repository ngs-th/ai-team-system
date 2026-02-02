#!/usr/bin/env python3
"""
AI Team Database Manager
Manage tasks, agents, and projects for the AI Team
"""

import os
import sqlite3
import json
import argparse
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict

# Import health monitor and notifications
from health_monitor import HealthMonitor
from notifications import NotificationManager, NotificationEvent, send_telegram_notification

# Set timezone to Bangkok (+7)
os.environ['TZ'] = 'Asia/Bangkok'

DB_PATH = Path(__file__).parent / "team.db"
TELEGRAM_CHANNEL = "1268858185"

class AITeamDB:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self.notifier = NotificationManager(db_path, TELEGRAM_CHANNEL)
        
    def close(self):
        self.notifier.close()
        self.conn.close()
        
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        self.close()

    # ========== Tasks ==========
    
    def create_task(self, title: str, description: str = "", 
                    assignee_id: str = None, project_id: str = None,
                    priority: str = "normal", estimated_hours: float = None,
                    due_date: str = None, prerequisites: str = None,
                    acceptance_criteria: str = None, expected_outcome: str = None) -> str:
        """Create a new task"""
        # MANDATORY: Every task must have a project
        if not project_id:
            raise ValueError("project_id is required - every task must belong to a project")
        
        # MANDATORY: Task quality framework fields
        if not expected_outcome:
            raise ValueError("expected_outcome is REQUIRED - define what success looks like")
        if not prerequisites:
            raise ValueError("prerequisites is REQUIRED - list what must be ready first")
        if not acceptance_criteria:
            raise ValueError("acceptance_criteria is REQUIRED - define how to verify completion")
        
        task_id = f"T-{datetime.now().strftime('%Y%m%d')}-{self._get_next_task_number():03d}"
        
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO tasks (id, title, description, assignee_id, project_id,
                             priority, estimated_hours, due_date, status,
                             prerequisites, acceptance_criteria, expected_outcome)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'todo', ?, ?, ?)
        ''', (task_id, title, description, assignee_id, project_id,
              priority, estimated_hours, due_date, prerequisites, 
              acceptance_criteria, expected_outcome))
        
        # Log the creation
        cursor.execute('''
            INSERT INTO task_history (task_id, action, notes)
            VALUES (?, 'created', ?)
        ''', (task_id, f"Task created with priority {priority}"))
        
        self.conn.commit()
        
        # Send Telegram notification using NotificationManager
        self.notifier.notify(
            event=NotificationEvent.CREATE,
            task_id=task_id,
            task_title=title,
            agent_id=assignee_id,
            assignee=assignee_id if assignee_id else "Unassigned"
        )
        
        return task_id
    
    def assign_task(self, task_id: str, agent_id: str) -> bool:
        """Assign task to an agent"""
        cursor = self.conn.cursor()
        
        # Get task info before updating
        cursor.execute('SELECT title, assignee_id FROM tasks WHERE id = ?', (task_id,))
        row = cursor.fetchone()
        if not row:
            return False
        
        task_title = row[0]
        
        # Update task - reset started_at when reassigning so fresh start time on next start
        cursor.execute('''
            UPDATE tasks SET assignee_id = ?, status = 'todo', started_at = NULL, updated_at = datetime('now', 'localtime')
            WHERE id = ?
        ''', (agent_id, task_id))
        
        # Update agent stats
        cursor.execute('''
            UPDATE agents SET total_tasks_assigned = total_tasks_assigned + 1,
                            current_task_id = ?, status = 'active',
                            updated_at = datetime('now', 'localtime')
            WHERE id = ?
        ''', (task_id, agent_id))
        
        # Log history
        cursor.execute('''
            INSERT INTO task_history (task_id, agent_id, action, notes)
            VALUES (?, ?, 'assigned', ?)
        ''', (task_id, agent_id, f"Assigned to {agent_id}"))
        
        self.conn.commit()
        
        # Send Telegram notification (AC: Notification on task assigned)
        self.notifier.notify(
            event=NotificationEvent.ASSIGN,
            task_id=task_id,
            task_title=task_title,
            agent_id=agent_id,
            agent_name=agent_id,
            entity_type='agent',
            entity_id=agent_id
        )
        
        return cursor.rowcount > 0
    
    def start_task(self, task_id: str, agent_id: str = None) -> bool:
        """Start working on a task"""
        cursor = self.conn.cursor()
        
        # Get task info before updating
        cursor.execute('SELECT title, assignee_id FROM tasks WHERE id = ?', (task_id,))
        row = cursor.fetchone()
        if not row:
            return False
        
        task_title = row[0]
        assignee = agent_id or row[1] or "Unknown"
        
        cursor.execute('''
            UPDATE tasks 
            SET status = 'in_progress', started_at = datetime('now', 'localtime'),
                updated_at = datetime('now', 'localtime')
            WHERE id = ?
        ''', (task_id,))
        
        cursor.execute('''
            INSERT INTO task_history (task_id, action, old_status, new_status)
            SELECT id, 'started', 'todo', 'in_progress'
            FROM tasks WHERE id = ?
        ''', (task_id,))
        
        self.conn.commit()
        
        # Send Telegram notification using NotificationManager
        self.notifier.notify(
            event=NotificationEvent.START,
            task_id=task_id,
            task_title=task_title,
            agent_id=assignee,
            agent_name=assignee
        )
        
        return cursor.rowcount > 0
    
    def send_to_review(self, task_id: str) -> bool:
        """Send task to review (in_progress -> review)"""
        cursor = self.conn.cursor()
        
        # Get task info before updating
        cursor.execute('SELECT title, status FROM tasks WHERE id = ?', (task_id,))
        row = cursor.fetchone()
        if not row:
            return False
        
        old_status = row[1]
        if old_status != 'in_progress':
            print(f"⚠️ Task {task_id} must be in_progress to send to review")
            return False
        
        cursor.execute('''
            UPDATE tasks 
            SET status = 'review', updated_at = datetime('now', 'localtime')
            WHERE id = ?
        ''', (task_id,))
        
        cursor.execute('''
            INSERT INTO task_history (task_id, action, old_status, new_status)
            VALUES (?, 'updated', 'in_progress', 'review')
        ''', (task_id,))
        
        self.conn.commit()
        
        # Send Telegram notification using NotificationManager
        self.notifier.notify(
            event=NotificationEvent.REVIEW,
            task_id=task_id,
            task_title=row[0]
        )
        
        return cursor.rowcount > 0
    
    def update_progress(self, task_id: str, progress: int, notes: str = "") -> bool:
        """Update task progress (0-100) - sends notification at milestone intervals"""
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT progress, title, assignee_id FROM tasks WHERE id = ?', (task_id,))
        row = cursor.fetchone()
        if not row:
            return False
        
        old_progress = row[0] if row[0] else 0
        task_title = row[1]
        assignee_id = row[2]
        
        cursor.execute('''
            UPDATE tasks 
            SET progress = ?, updated_at = datetime('now', 'localtime'),
                notes = CASE WHEN ? != '' THEN ? ELSE notes END
            WHERE id = ?
        ''', (progress, notes, notes, task_id))
        
        cursor.execute('''
            INSERT INTO task_history (task_id, action, old_progress, new_progress, notes)
            VALUES (?, 'updated', ?, ?, ?)
        ''', (task_id, old_progress, progress, notes))
        
        self.conn.commit()
        
        # Send progress notification at milestone intervals (0, 25, 50, 75, 100)
        # or if this is a significant jump (>20%)
        is_milestone = progress in [0, 25, 50, 75, 100]
        is_significant = abs(progress - old_progress) >= 20
        
        if is_milestone or is_significant:
            from notifications import NotificationEvent
            self.notifier.notify(
                event=NotificationEvent.PROGRESS,
                task_id=task_id,
                task_title=task_title,
                agent_id=assignee_id,
                agent_name=assignee_id,
                entity_type='agent',
                entity_id=assignee_id,
                progress=progress
            )
        
        return cursor.rowcount > 0
    
    def complete_task(self, task_id: str) -> bool:
        """Mark task as completed - sends to REVIEW for another agent to verify"""
        cursor = self.conn.cursor()
        
        # Get task info before updating
        cursor.execute('SELECT title, started_at, assignee_id FROM tasks WHERE id = ?', (task_id,))
        row = cursor.fetchone()
        if not row:
            return False
        
        task_title = row[0]
        assignee = row[2]
        
        # Calculate actual duration if started_at exists
        if row[1]:
            cursor.execute('''
                UPDATE tasks 
                SET status = 'review', progress = 95, 
                    actual_duration_minutes = ROUND((strftime('%s', 'now') - strftime('%s', started_at)) / 60),
                    updated_at = datetime('now', 'localtime')
                WHERE id = ?
            ''', (task_id,))
        else:
            cursor.execute('''
                UPDATE tasks 
                SET status = 'review', progress = 95,
                    updated_at = datetime('now', 'localtime')
                WHERE id = ?
            ''', (task_id,))
        
        # Release agent (they're done, waiting for review)
        cursor.execute('''
            UPDATE agents 
            SET current_task_id = NULL, status = 'idle',
                updated_at = datetime('now', 'localtime')
            WHERE id = ?
        ''', (assignee,))
        
        # Update agent stats
        cursor.execute('''
            INSERT INTO task_history (task_id, action, old_status, new_status)
            VALUES (?, 'completed', 'in_progress', 'review')
        ''', (task_id,))
        
        self.conn.commit()
        
        # Send Telegram notification - task ready for review
        self.notifier.notify(
            event=NotificationEvent.REVIEW,
            task_id=task_id,
            task_title=task_title,
            agent_id=assignee,
            agent_name=assignee
        )
        
        return cursor.rowcount > 0
    
    def approve_review(self, task_id: str, reviewer_id: str = None) -> bool:
        """Approve reviewed task - moves from review to done"""
        cursor = self.conn.cursor()
        
        # Get task info
        cursor.execute('SELECT title, status, assignee_id, started_at FROM tasks WHERE id = ?', (task_id,))
        row = cursor.fetchone()
        if not row:
            return False
        
        if row[1] != 'review':
            print(f"⚠️ Task {task_id} must be in review status to approve")
            return False
        
        task_title = row[0]
        original_assignee = row[2]
        started_at = row[3]
        
        # Check if memory was updated (working memory must have recent entry)
        cursor.execute('''
            SELECT working_notes, last_updated 
            FROM agent_working_memory 
            WHERE agent_id = ? AND current_task_id = ?
            AND last_updated > datetime('now', '-2 hours')
        ''', (original_assignee, task_id))
        memory_row = cursor.fetchone()
        
        if not memory_row:
            print(f"⚠️ Cannot approve {task_id}: Agent {original_assignee} did not update working memory!")
            print(f"   Requirement: Must update working memory every 30 minutes")
            return False
        
        # Check if learnings were added
        cursor.execute('''
            SELECT 1 FROM agent_context 
            WHERE agent_id = ? 
            AND learnings LIKE '%' || datetime('now', '%Y-%m') || '%'
        ''', (original_assignee,))
        if not cursor.fetchone():
            print(f"⚠️ Warning: Agent {original_assignee} may not have added learning for this task")
            # Don't block approval, just warn
        
        # Calculate actual duration if not already set and started_at exists
        duration_calc = ""
        duration_params = []
        if started_at:
            duration_calc = """
                , actual_duration_minutes = COALESCE(
                    actual_duration_minutes, 
                    ROUND((strftime('%s', 'now') - strftime('%s', started_at)) / 60)
                )
            """
        
        # Move to done
        cursor.execute(f'''
            UPDATE tasks 
            SET status = 'done', progress = 100, completed_at = datetime('now', 'localtime'),
                updated_at = datetime('now', 'localtime')
                {duration_calc}
            WHERE id = ?
        ''', (task_id,))
        
        # Update original agent's completed count
        if original_assignee:
            cursor.execute('''
                UPDATE agents 
                SET total_tasks_completed = total_tasks_completed + 1,
                    updated_at = datetime('now', 'localtime')
                WHERE id = ?
            ''', (original_assignee,))
        
        cursor.execute('''
            INSERT INTO task_history (task_id, action, old_status, new_status, agent_id, notes)
            VALUES (?, 'approved', 'review', 'done', ?, ?)
        ''', (task_id, reviewer_id, f"Approved by {reviewer_id or 'unknown'}"))
        
        self.conn.commit()
        
        # Send completion notification
        self.notifier.notify(
            event=NotificationEvent.COMPLETE,
            task_id=task_id,
            task_title=task_title,
            agent_id=original_assignee,
            agent_name=original_assignee
        )
        
        return cursor.rowcount > 0
    
    def block_task(self, task_id: str, reason: str) -> bool:
        """Block a task with reason"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            UPDATE tasks 
            SET status = 'blocked', blocked_reason = ?, updated_at = datetime('now', 'localtime')
            WHERE id = ?
        ''', (reason, task_id))
        
        cursor.execute('''
            UPDATE agents 
            SET status = 'blocked', updated_at = datetime('now', 'localtime')
            WHERE id = (SELECT assignee_id FROM tasks WHERE id = ?)
        ''', (task_id,))
        
        cursor.execute('''
            INSERT INTO task_history (task_id, action, notes)
            VALUES (?, 'blocked', ?)
        ''', (task_id, reason))
        
        self.conn.commit()
        
        # Send Telegram notification using NotificationManager (AC: Notification on task blocked)
        # Get task title
        cursor.execute('SELECT title FROM tasks WHERE id = ?', (task_id,))
        title_row = cursor.fetchone()
        task_title = title_row[0] if title_row else None
        
        # Get assignee
        cursor.execute('SELECT assignee_id FROM tasks WHERE id = ?', (task_id,))
        assignee_row = cursor.fetchone()
        assignee = assignee_row[0] if assignee_row else None
        
        self.notifier.notify(
            event=NotificationEvent.BLOCK,
            task_id=task_id,
            task_title=task_title,
            agent_id=assignee,
            agent_name=assignee,
            reason=reason
        )
        
        return cursor.rowcount > 0
    
    def unblock_task(self, task_id: str, agent_id: str = None) -> bool:
        """Unblock a task and resume (blocked -> in_progress)"""
        cursor = self.conn.cursor()
        
        # Get task info before updating
        cursor.execute('SELECT title, assignee_id, status FROM tasks WHERE id = ?', (task_id,))
        row = cursor.fetchone()
        if not row:
            return False
        
        if row[2] != 'blocked':
            print(f"⚠️ Task {task_id} is not blocked")
            return False
        
        assignee = agent_id or row[1] or "Unknown"
        
        cursor.execute('''
            UPDATE tasks 
            SET status = 'in_progress', started_at = datetime('now', 'localtime'), 
                blocked_reason = NULL, fix_loop_count = 0, updated_at = datetime('now', 'localtime')
            WHERE id = ?
        ''', (task_id,))
        
        cursor.execute('''
            UPDATE agents 
            SET status = 'active', updated_at = datetime('now', 'localtime')
            WHERE id = (SELECT assignee_id FROM tasks WHERE id = ?)
        ''', (task_id,))
        
        cursor.execute('''
            INSERT INTO task_history (task_id, action, old_status, new_status, notes)
            VALUES (?, 'unblocked', 'blocked', 'in_progress', 'Fix loop counter reset to 0')
        ''', (task_id,))
        
        self.conn.commit()
        
        # Send Telegram notification using NotificationManager
        self.notifier.notify(
            event=NotificationEvent.UNBLOCK,
            task_id=task_id,
            task_title=row[0],
            agent_id=assignee,
            agent_name=assignee
        )
        
        return cursor.rowcount > 0
    
    def backlog_task(self, task_id: str, reason: str = "Waiting for requirements/resources") -> bool:
        """Move task to backlog (waiting for requirements/resources)"""
        cursor = self.conn.cursor()
        
        # Get task info before updating
        cursor.execute('SELECT title, status FROM tasks WHERE id = ?', (task_id,))
        row = cursor.fetchone()
        if not row:
            return False
        
        old_status = row[1]
        
        cursor.execute('''
            UPDATE tasks 
            SET status = 'backlog', blocked_reason = ?, started_at = NULL, updated_at = datetime('now', 'localtime')
            WHERE id = ?
        ''', (reason, task_id))
        
        cursor.execute('''
            INSERT INTO task_history (task_id, action, old_status, new_status, notes)
            VALUES (?, 'backlogged', ?, 'backlog', ?)
        ''', (task_id, old_status, reason))
        
        self.conn.commit()
        
        # Send Telegram notification using NotificationManager
        self.notifier.notify(
            event=NotificationEvent.BACKLOG,
            task_id=task_id,
            task_title=row[0],
            reason=reason
        )
        
        return cursor.rowcount > 0
    
    def get_tasks(self, status: str = None, assignee: str = None) -> List[Dict]:
        """Get tasks with optional filters"""
        cursor = self.conn.cursor()
        
        query = 'SELECT * FROM v_task_summary WHERE 1=1'
        params = []
        
        if status:
            query += ' AND status = ?'
            params.append(status)
        if assignee:
            query += ' AND assignee_id = ?'
            params.append(assignee)
            
        query += ' ORDER BY due_date, priority'
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    # ========== Agents ==========
    
    def get_agents(self, status: str = None) -> List[Dict]:
        """Get all agents with their workload"""
        cursor = self.conn.cursor()
        
        query = 'SELECT * FROM v_agent_workload WHERE 1=1'
        params = []
        
        if status:
            query += ' AND status = ?'
            params.append(status)
            
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def update_agent_heartbeat(self, agent_id: str) -> bool:
        """Update agent heartbeat timestamp"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE agents 
            SET last_heartbeat = datetime('now', 'localtime'), updated_at = datetime('now', 'localtime')
            WHERE id = ?
        ''', (agent_id,))
        self.conn.commit()
        return cursor.rowcount > 0
    
    # ========== Dashboard ==========
    
    def get_dashboard_stats(self) -> Dict:
        """Get dashboard statistics"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM v_dashboard_stats')
        row = cursor.fetchone()
        if row:
            return {
                'total_agents': row[0],
                'active_agents': row[1],
                'idle_agents': row[2],
                'blocked_agents': row[3],
                'total_projects': row[4],
                'active_projects': row[5],
                'total_tasks': row[6],
                'todo_tasks': row[7],
                'in_progress_tasks': row[8],
                'completed_tasks': row[9],
                'blocked_tasks': row[10],
                'avg_progress': row[11],
                'due_today': row[12],
                'overdue_tasks': row[13]
            }
        return {}
    
    def get_project_status(self) -> List[Dict]:
        """Get all projects with status"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM v_project_status ORDER BY progress_pct DESC')
        return [dict(row) for row in cursor.fetchall()]
    
    # ========== Reports ==========
    
    def generate_daily_report(self) -> str:
        """Generate daily report"""
        stats = self.get_dashboard_stats()
        tasks_done_today = self._get_tasks_completed_today()
        
        report = f"""
# AI Team Daily Report - {datetime.now().strftime('%Y-%m-%d')}

## 📊 Summary
- Total Tasks: {stats.get('total_tasks', 0)}
- Completed Today: {len(tasks_done_today)}
- In Progress: {stats.get('in_progress_tasks', 0)}
- Blocked: {stats.get('blocked_tasks', 0)}
- Active Agents: {stats.get('active_agents', 0)}

## ✅ Tasks Completed Today
"""
        for task in tasks_done_today:
            report += f"- {task['id']}: {task['title']} (by {task['assignee']})\n"
        
        report += "\n## 🔄 In Progress\n"
        in_progress = self.get_tasks(status='in_progress')
        for task in in_progress[:5]:
            report += f"- {task['id']}: {task['title']} ({task['progress']}%) - {task['assignee_name']}\n"
        
        report += "\n## 🚧 Blocked\n"
        blocked = self.get_tasks(status='blocked')
        for task in blocked:
            report += f"- {task['id']}: {task['title']} - {task['assignee_name']}\n"
        
        return report
    
    # ========== Helper Methods ==========
    
    @staticmethod
    def format_duration(minutes: int) -> str:
        """Format duration in human-readable format (e.g., '2h 30m', '45m', '1d 2h')"""
        if minutes is None or minutes < 0:
            return "-"
        
        days = minutes // 1440
        hours = (minutes % 1440) // 60
        mins = minutes % 60
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if mins > 0 or (days == 0 and hours == 0):
            parts.append(f"{mins}m")
        
        return " ".join(parts) if parts else "0m"
    
    def get_task_duration(self, task_id: str) -> dict:
        """Get task duration info"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT started_at, completed_at, actual_duration_minutes
            FROM tasks WHERE id = ?
        ''', (task_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        return {
            'started_at': row[0],
            'completed_at': row[1],
            'actual_duration_minutes': row[2],
            'duration_formatted': self.format_duration(row[2])
        }
    
    def _get_next_task_number(self) -> int:
        """Get next task number for today"""
        cursor = self.conn.cursor()
        today = datetime.now().strftime('%Y%m%d')
        cursor.execute("""
            SELECT COALESCE(MAX(CAST(SUBSTR(id, 12) AS INTEGER)), 0) FROM tasks 
            WHERE id LIKE ?
        """, (f'T-{today}-%',))
        return cursor.fetchone()[0] + 1
    
    def _get_tasks_completed_today(self) -> List[Dict]:
        """Get tasks completed today"""
        cursor = self.conn.cursor()
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('''
            SELECT t.id, t.title, a.name as assignee,
                   t.actual_duration_minutes
            FROM tasks t
            JOIN agents a ON t.assignee_id = a.id
            WHERE DATE(t.completed_at) = ?
        ''', (today,))
        return [dict(row) for row in cursor.fetchall()]
    
    def recalculate_durations(self) -> int:
        """Recalculate actual_duration_minutes for all completed tasks that don't have it set"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE tasks 
            SET actual_duration_minutes = ROUND((strftime('%s', completed_at) - strftime('%s', started_at)) / 60)
            WHERE status = 'done' 
              AND completed_at IS NOT NULL 
              AND started_at IS NOT NULL
              AND actual_duration_minutes IS NULL
        ''')
        self.conn.commit()
        return cursor.rowcount

    def get_duration_stats(self) -> dict:
        """Get task duration statistics"""
        cursor = self.conn.cursor()
        
        # Overall stats for completed tasks
        cursor.execute('''
            SELECT 
                COUNT(*) as total_completed,
                ROUND(AVG(actual_duration_minutes), 1) as avg_duration_minutes,
                MIN(actual_duration_minutes) as min_duration,
                MAX(actual_duration_minutes) as max_duration,
                ROUND(AVG(CASE 
                    WHEN actual_duration_minutes > 0 THEN actual_duration_minutes 
                END), 1) as avg_nonzero_duration
            FROM tasks 
            WHERE status = 'done' 
              AND actual_duration_minutes IS NOT NULL
              AND actual_duration_minutes > 0
        ''')
        overall = cursor.fetchone()
        
        # Stats by agent
        cursor.execute('''
            SELECT 
                a.name as agent_name,
                COUNT(*) as tasks_completed,
                ROUND(AVG(t.actual_duration_minutes), 1) as avg_duration_minutes,
                ROUND(AVG(t.actual_duration_minutes) / 60, 1) as avg_duration_hours
            FROM tasks t
            JOIN agents a ON t.assignee_id = a.id
            WHERE t.status = 'done' 
              AND t.actual_duration_minutes IS NOT NULL
              AND t.actual_duration_minutes > 0
            GROUP BY t.assignee_id
            ORDER BY tasks_completed DESC
        ''')
        by_agent = [dict(row) for row in cursor.fetchall()]
        
        # Recent completed tasks with duration
        cursor.execute('''
            SELECT 
                t.id,
                t.title,
                a.name as assignee_name,
                t.actual_duration_minutes,
                t.completed_at
            FROM tasks t
            LEFT JOIN agents a ON t.assignee_id = a.id
            WHERE t.status = 'done' 
              AND t.actual_duration_minutes IS NOT NULL
            ORDER BY t.completed_at DESC
            LIMIT 10
        ''')
        recent = [dict(row) for row in cursor.fetchall()]
        
        return {
            'overall': {
                'total_completed': overall[0] or 0,
                'avg_duration_minutes': overall[1] or 0,
                'min_duration_minutes': overall[2] or 0,
                'max_duration_minutes': overall[3] or 0,
                'avg_formatted': self.format_duration(int(overall[1] or 0)),
                'min_formatted': self.format_duration(int(overall[2] or 0)),
                'max_formatted': self.format_duration(int(overall[3] or 0))
            },
            'by_agent': by_agent,
            'recent': recent
        }

    def update_task_requirements(self, task_id: str, 
                                  prerequisites: str = None,
                                  acceptance_criteria: str = None, 
                                  expected_outcome: str = None) -> bool:
        """Update task prerequisites, acceptance criteria, and expected outcome"""
        cursor = self.conn.cursor()
        
        # Build dynamic update query based on provided fields
        updates = []
        params = []
        
        if prerequisites is not None:
            updates.append("prerequisites = ?")
            params.append(prerequisites)
        if acceptance_criteria is not None:
            updates.append("acceptance_criteria = ?")
            params.append(acceptance_criteria)
        if expected_outcome is not None:
            updates.append("expected_outcome = ?")
            params.append(expected_outcome)
        
        if not updates:
            return False
        
        params.append(task_id)
        query = f'''
            UPDATE tasks 
            SET {', '.join(updates)}, updated_at = datetime('now', 'localtime')
            WHERE id = ?
        '''
        
        cursor.execute(query, params)
        
        # Log the update
        cursor.execute('''
            INSERT INTO task_history (task_id, action, notes)
            VALUES (?, 'updated', 'Task requirements updated')
        ''', (task_id,))
        
        self.conn.commit()
        return cursor.rowcount > 0

    def get_task_requirements(self, task_id: str) -> dict:
        """Get task prerequisites, acceptance criteria, and expected outcome"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT prerequisites, acceptance_criteria, expected_outcome
            FROM tasks WHERE id = ?
        ''', (task_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        return {
            'prerequisites': row[0],
            'acceptance_criteria': row[1],
            'expected_outcome': row[2]
        }

    def get_agent_context(self, agent_id: str) -> dict:
        """Get agent context from database"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT context, learnings, preferences, last_updated
            FROM agent_context WHERE agent_id = ?
        ''', (agent_id,))
        row = cursor.fetchone()
        if row:
            return {
                'context': row[0],
                'learnings': row[1],
                'preferences': row[2],
                'last_updated': row[3]
            }
        return None

    def update_agent_context(self, agent_id: str, field: str, content: str) -> bool:
        """Update agent context field"""
        cursor = self.conn.cursor()
        try:
            cursor.execute(f'''
                UPDATE agent_context 
                SET {field} = ?, last_updated = datetime('now', 'localtime')
                WHERE agent_id = ?
            ''', (content, agent_id))
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"[Error] Failed to update context: {e}")
            return False

    # ========== Agent Working Memory ==========

    def get_working_memory(self, agent_id: str) -> dict:
        """Get agent's working memory (like WORKING.md)"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT current_task_id, working_notes, blockers, next_steps, last_updated
            FROM agent_working_memory WHERE agent_id = ?
        ''', (agent_id,))
        row = cursor.fetchone()
        if row:
            return {
                'current_task_id': row[0],
                'working_notes': row[1],
                'blockers': row[2],
                'next_steps': row[3],
                'last_updated': row[4]
            }
        return None

    def update_working_memory(self, agent_id: str, **fields) -> bool:
        """Update agent's working memory"""
        cursor = self.conn.cursor()
        valid_fields = ['current_task_id', 'working_notes', 'blockers', 'next_steps']
        
        updates = []
        params = []
        for field, value in fields.items():
            if field in valid_fields:
                updates.append(f"{field} = ?")
                params.append(value)
        
        if not updates:
            return False
        
        params.append(agent_id)
        query = f'''
            UPDATE agent_working_memory 
            SET {', '.join(updates)}, last_updated = datetime('now', 'localtime')
            WHERE agent_id = ?
        '''
        
        try:
            cursor.execute(query, params)
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"[Error] Failed to update working memory: {e}")
            return False

    # ========== Inter-Agent Communication ==========

    def send_message(self, from_agent: str, message: str, to_agent: str = None,
                     task_id: str = None, msg_type: str = 'comment') -> int:
        """Send message between agents"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO agent_communications 
                (from_agent_id, to_agent_id, task_id, message, message_type)
                VALUES (?, ?, ?, ?, ?)
            ''', (from_agent, to_agent, task_id, message, msg_type))
            self.conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"[Error] Failed to send message: {e}")
            return None

    def get_messages(self, agent_id: str = None, task_id: str = None,
                     unread_only: bool = False, limit: int = 50) -> list:
        """Get messages for agent or task"""
        cursor = self.conn.cursor()
        
        query = '''
            SELECT c.*, 
                   from_a.name as from_name,
                   to_a.name as to_name
            FROM agent_communications c
            JOIN agents from_a ON c.from_agent_id = from_a.id
            LEFT JOIN agents to_a ON c.to_agent_id = to_a.id
            WHERE 1=1
        '''
        params = []
        
        if agent_id:
            query += ' AND (c.to_agent_id = ? OR c.from_agent_id = ?)'
            params.extend([agent_id, agent_id])
        if task_id:
            query += ' AND c.task_id = ?'
            params.append(task_id)
        if unread_only:
            query += ' AND c.is_read = FALSE'
        
        query += ' ORDER BY c.created_at DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def mark_read(self, message_id: int) -> bool:
        """Mark message as read"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                UPDATE agent_communications 
                SET is_read = TRUE WHERE id = ?
            ''', (message_id,))
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"[Error] Failed to mark read: {e}")
            return False


def load_template(template_name: str) -> str:
    """Load a template file from agents/templates/"""
    template_path = Path(__file__).parent / "agents" / "templates" / f"template-{template_name}.md"
    if template_path.exists():
        return template_path.read_text()
    return None

def list_templates() -> List[str]:
    """List available templates"""
    templates_dir = Path(__file__).parent / "agents" / "templates"
    if not templates_dir.exists():
        return []
    templates = []
    for f in templates_dir.glob("template-*.md"):
        # Extract template name from filename (template-{name}.md)
        name = f.stem.replace("template-", "")
        templates.append(name)
    return sorted(templates)

def main():
    parser = argparse.ArgumentParser(description='AI Team Database Manager')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Task commands
    task_parser = subparsers.add_parser('task', help='Task management')
    task_sub = task_parser.add_subparsers(dest='task_action')
    
    create = task_sub.add_parser('create', help='Create new task')
    create.add_argument('title', help='Task title')
    create.add_argument('--desc', default='', help='Task description')
    create.add_argument('--assign', help='Assign to agent')
    create.add_argument('--project', required=True, help='Project ID (required)')
    create.add_argument('--priority', choices=['critical', 'high', 'normal', 'low'], 
                       default='normal', help='Task priority')
    create.add_argument('--due', help='Due date (YYYY-MM-DD)')
    create.add_argument('--prerequisites', help='Prerequisites as markdown checklist (e.g., "- [ ] API token\n- [ ] Design ready")')
    create.add_argument('--acceptance', help='Acceptance criteria as markdown checklist')
    create.add_argument('--expected-outcome', help='Clear description of expected outcome')
    create.add_argument('--template', help='Use template (prd, tech-spec, qa-testplan, feature-dev, bug-fix)')
    
    # Template commands
    template_parser = task_sub.add_parser('template', help='List or use task templates')
    template_sub = template_parser.add_subparsers(dest='template_action')
    
    template_list = template_sub.add_parser('list', help='List available templates')
    
    template_create = template_sub.add_parser('create', help='Create task from template')
    template_create.add_argument('template_name', help='Template name (prd, tech-spec, qa-testplan, feature-dev, bug-fix)')
    template_create.add_argument('title', help='Task title')
    template_create.add_argument('--project', required=True, help='Project ID')
    template_create.add_argument('--assign', help='Assign to agent')
    template_create.add_argument('--priority', choices=['critical', 'high', 'normal', 'low'], 
                                default='normal', help='Task priority')
    
    assign = task_sub.add_parser('assign', help='Assign task')
    assign.add_argument('task_id', help='Task ID')
    assign.add_argument('agent_id', help='Agent ID')
    
    start = task_sub.add_parser('start', help='Start task')
    start.add_argument('task_id', help='Task ID')
    
    progress = task_sub.add_parser('progress', help='Update progress')
    progress.add_argument('task_id', help='Task ID')
    progress.add_argument('percent', type=int, help='Progress percentage')
    progress.add_argument('--notes', default='', help='Progress notes')
    
    done = task_sub.add_parser('done', help='Complete task')
    done.add_argument('task_id', help='Task ID')
    
    review = task_sub.add_parser('review', help='Send task to review')
    review.add_argument('task_id', help='Task ID')
    
    block = task_sub.add_parser('block', help='Block task')
    block.add_argument('task_id', help='Task ID')
    block.add_argument('reason', help='Block reason')
    
    backlog = task_sub.add_parser('backlog', help='Move task to backlog (waiting for requirements)')
    backlog.add_argument('task_id', help='Task ID')
    backlog.add_argument('--reason', default='Waiting for requirements/resources', help='Reason for backlog')
    
    unblock = task_sub.add_parser('unblock', help='Unblock and resume task')
    unblock.add_argument('task_id', help='Task ID')
    unblock.add_argument('--agent', help='Agent ID resuming the task')
    
    approve = task_sub.add_parser('approve', help='Approve reviewed task (review -> done)')
    approve.add_argument('task_id', help='Task ID')
    approve.add_argument('--reviewer', help='Reviewer agent ID')
    
    requirements = task_sub.add_parser('requirements', help='Update task requirements (prerequisites, acceptance criteria, goal)')
    requirements.add_argument('task_id', help='Task ID')
    requirements.add_argument('--prerequisites', help='Prerequisites as markdown checklist')
    requirements.add_argument('--acceptance', help='Acceptance criteria as markdown checklist')
    requirements.add_argument('--goal', help='Clear description of expected outcome')
    
    show_reqs = task_sub.add_parser('show-requirements', help='Show task requirements')
    show_reqs.add_argument('task_id', help='Task ID')
    
    duration_cmd = task_sub.add_parser('duration', help='Show task duration and timing info')
    duration_cmd.add_argument('task_id', help='Task ID')
    duration_cmd.add_argument('--recalc', action='store_true', help='Recalculate duration for completed tasks')
    
    list_tasks = task_sub.add_parser('list', help='List tasks')
    list_tasks.add_argument('--status', choices=['backlog', 'todo', 'in_progress', 'review', 'done', 'blocked', 'cancelled'],
                           help='Filter by status')
    list_tasks.add_argument('--agent', help='Filter by agent')
    
    # Agent commands
    agent_parser = subparsers.add_parser('agent', help='Agent management')
    agent_sub = agent_parser.add_subparsers(dest='agent_action')
    
    list_agents = agent_sub.add_parser('list', help='List agents')
    list_agents.add_argument('--status', choices=['idle', 'active', 'blocked'],
                            help='Filter by status')
    
    heartbeat = agent_sub.add_parser('heartbeat', help='Update agent heartbeat')
    heartbeat.add_argument('agent_id', help='Agent ID')
    
    # Agent context commands
    context = agent_sub.add_parser('context', help='Manage agent context')
    context_sub = context.add_subparsers(dest='context_action')
    
    ctx_show = context_sub.add_parser('show', help='Show agent context')
    ctx_show.add_argument('agent_id', help='Agent ID')
    
    ctx_update = context_sub.add_parser('update', help='Update agent context')
    ctx_update.add_argument('agent_id', help='Agent ID')
    ctx_update.add_argument('--field', choices=['context', 'learnings', 'preferences'], 
                           default='context', help='Field to update')
    ctx_update.add_argument('--content', required=True, help='New content')
    
    ctx_learn = context_sub.add_parser('learn', help='Add learning to agent')
    ctx_learn.add_argument('agent_id', help='Agent ID')
    ctx_learn.add_argument('learning', help='Learning to add')
    
    # Agent working memory commands
    memory = agent_sub.add_parser('memory', help='Manage agent working memory (WORKING.md)')
    memory_sub = memory.add_subparsers(dest='memory_action')
    
    mem_show = memory_sub.add_parser('show', help='Show working memory')
    mem_show.add_argument('agent_id', help='Agent ID')
    
    mem_update = memory_sub.add_parser('update', help='Update working memory')
    mem_update.add_argument('agent_id', help='Agent ID')
    mem_update.add_argument('--notes', help='Working notes')
    mem_update.add_argument('--blockers', help='Current blockers')
    mem_update.add_argument('--next-steps', help='Next steps planned')
    mem_update.add_argument('--task', help='Current task ID')
    
    # Agent communication commands
    comm = agent_sub.add_parser('comm', help='Inter-agent communication')
    comm_sub = comm.add_subparsers(dest='comm_action')
    
    comm_send = comm_sub.add_parser('send', help='Send message')
    comm_send.add_argument('from_agent', help='From agent ID')
    comm_send.add_argument('message', help='Message content')
    comm_send.add_argument('--to', help='To agent ID (optional - broadcast if not set)')
    comm_send.add_argument('--task', help='Related task ID')
    comm_send.add_argument('--type', choices=['comment', 'mention', 'request', 'response'],
                          default='comment', help='Message type')
    
    comm_inbox = comm_sub.add_parser('inbox', help='Check inbox')
    comm_inbox.add_argument('agent_id', help='Agent ID')
    comm_inbox.add_argument('--unread', action='store_true', help='Show only unread')
    
    comm_task = comm_sub.add_parser('task', help='Show task messages')
    comm_task.add_argument('task_id', help='Task ID')
    
    # Dashboard commands
    dash_parser = subparsers.add_parser('dashboard', help='Dashboard')
    dash_parser.add_argument('--export', choices=['json', 'markdown'],
                            help='Export format')
    
    # Report commands
    report_parser = subparsers.add_parser('report', help='Generate reports')
    report_parser.add_argument('--daily', action='store_true', help='Daily report')
    report_parser.add_argument('--duration', action='store_true', help='Show task duration statistics')
    
    # Health commands
    health_parser = subparsers.add_parser('health', help='Health monitoring')
    health_sub = health_parser.add_subparsers(dest='health_action')
    
    health_check = health_sub.add_parser('check', help='Run health check once')
    health_status = health_sub.add_parser('status', help='Show current health status')
    
    # Notification commands
    notify_parser = subparsers.add_parser('notify', help='Notification settings')
    notify_sub = notify_parser.add_subparsers(dest='notify_action')
    
    notify_level = notify_sub.add_parser('level', help='Set notification level for agent')
    notify_level.add_argument('agent_id', help='Agent ID')
    notify_level.add_argument('level', choices=['minimal', 'normal', 'verbose'],
                              help='Notification level (minimal=block+complete, normal=assign+start+block+complete, verbose=all)')
    
    notify_show = notify_sub.add_parser('show', help='Show notification settings')
    notify_show.add_argument('--agent', help='Show settings for specific agent')
    
    notify_log = notify_sub.add_parser('log', help='Show notification log')
    notify_log.add_argument('--task', help='Filter by task ID')
    notify_log.add_argument('--limit', type=int, default=20, help='Number of entries to show')
    
    args = parser.parse_args()
    
    with AITeamDB() as db:
        if args.command == 'task':
            if args.task_action == 'create':
                # Load template if specified
                description = args.desc
                prerequisites = args.prerequisites
                acceptance = args.acceptance
                goal = args.expected_outcome
                
                if args.template:
                    template_content = load_template(args.template)
                    if template_content:
                        description = f"## Template: {args.template}\n\n{template_content}\n\n---\n\n## Task: {args.title}\n\n{args.desc}"
                        print(f"📄 Using template: {args.template}")
                    else:
                        available = list_templates()
                        print(f"⚠️  Template '{args.template}' not found")
                        print(f"   Available: {', '.join(available)}")
                
                task_id = db.create_task(
                    title=args.title,
                    description=description,
                    assignee_id=args.assign,
                    project_id=args.project,
                    priority=args.priority,
                    due_date=args.due,
                    prerequisites=prerequisites,
                    acceptance_criteria=acceptance,
                    expected_outcome=goal
                )
                print(f"✅ Task created: {task_id}")
                if prerequisites:
                    print(f"   Prerequisites: {len(prerequisites.split(chr(10)))} items")
                if acceptance:
                    print(f"   Acceptance Criteria: {len(acceptance.split(chr(10)))} items")
                if goal:
                    print(f"   Goal: {goal[:50]}{'...' if len(goal) > 50 else ''}")
            
            elif args.task_action == 'template':
                if args.template_action == 'list':
                    templates = list_templates()
                    print(f"\n📄 Available Templates ({len(templates)}):\n")
                    for t in templates:
                        template_file = Path(__file__).parent / "agents" / "templates" / f"template-{t}.md"
                        # Get first line as description
                        desc = ""
                        if template_file.exists():
                            first_line = template_file.read_text().split('\n')[0]
                            desc = first_line.replace('#', '').strip() if first_line.startswith('#') else ""
                        print(f"  • {t:<12} {desc}")
                    print(f"\nUsage: ./team_db.py task create --template <name> ...")
                    print(f"   or: ./team_db.py task template create <name> <title> ...")
                    
                elif args.template_action == 'create':
                    template_content = load_template(args.template_name)
                    if not template_content:
                        print(f"❌ Template '{args.template_name}' not found")
                        available = list_templates()
                        if available:
                            print(f"Available: {', '.join(available)}")
                        sys.exit(1)
                    
                    description = f"## Template: {args.template_name}\n\n{template_content}\n\n---\n\n## Task: {args.title}"
                    
                    task_id = db.create_task(
                        title=args.title,
                        description=description,
                        assignee_id=args.assign,
                        project_id=args.project,
                        priority=args.priority
                    )
                    print(f"✅ Task created from template: {task_id}")
                    print(f"   Template: {args.template_name}")
                
            elif args.task_action == 'assign':
                if db.assign_task(args.task_id, args.agent_id):
                    print(f"✅ Task {args.task_id} assigned to {args.agent_id}")
                    
            elif args.task_action == 'start':
                if db.start_task(args.task_id):
                    print(f"✅ Task {args.task_id} started")
            
            elif args.task_action == 'review':
                if db.send_to_review(args.task_id):
                    print(f"✅ Task {args.task_id} sent to review")
                    
            elif args.task_action == 'progress':
                if db.update_progress(args.task_id, args.percent, args.notes):
                    print(f"✅ Task {args.task_id} progress: {args.percent}%")
                    
            elif args.task_action == 'done':
                if db.complete_task(args.task_id):
                    print(f"✅ Task {args.task_id} completed - sent to review")
                    
            elif args.task_action == 'approve':
                if db.approve_review(args.task_id, args.reviewer):
                    print(f"✅ Task {args.task_id} approved and marked as done")
                    
            elif args.task_action == 'block':
                if db.block_task(args.task_id, args.reason):
                    print(f"⚠️ Task {args.task_id} blocked: {args.reason}")
            
            elif args.task_action == 'backlog':
                if db.backlog_task(args.task_id, args.reason):
                    print(f"📋 Task {args.task_id} moved to backlog: {args.reason}")
            
            elif args.task_action == 'unblock':
                if db.unblock_task(args.task_id, args.agent):
                    print(f"✅ Task {args.task_id} unblocked and resumed")
            
            elif args.task_action == 'requirements':
                if db.update_task_requirements(
                    args.task_id,
                    prerequisites=args.prerequisites,
                    acceptance_criteria=args.acceptance,
                    expected_outcome=args.goal
                ):
                    print(f"✅ Task {args.task_id} requirements updated")
                    if args.prerequisites:
                        print(f"   Prerequisites: {len(args.prerequisites.split(chr(10)))} items")
                    if args.acceptance:
                        print(f"   Acceptance Criteria: {len(args.acceptance.split(chr(10)))} items")
                    if args.goal:
                        print(f"   Goal: {args.goal[:50]}{'...' if len(args.goal) > 50 else ''}")
            
            elif args.task_action == 'show-requirements':
                reqs = db.get_task_requirements(args.task_id)
                if reqs:
                    print(f"\n📋 Task {args.task_id} Requirements:\n")
                    if reqs['goal']:
                        print(f"🎯 Goal:\n{reqs['goal']}\n")
                    if reqs['prerequisites']:
                        print(f"✅ Prerequisites:\n{reqs['prerequisites']}\n")
                    if reqs['acceptance_criteria']:
                        print(f"📌 Acceptance Criteria:\n{reqs['acceptance_criteria']}\n")
                    if not any([reqs['goal'], reqs['prerequisites'], reqs['acceptance_criteria']]):
                        print("   No requirements defined yet.")
                else:
                    print(f"⚠️ Task {args.task_id} not found")
            
            elif args.task_action == 'duration':
                # Get full task details
                cursor = db.conn.cursor()
                cursor.execute('''
                    SELECT id, title, status, started_at, completed_at, 
                           actual_duration_minutes, created_at, assignee_id
                    FROM tasks WHERE id = ?
                ''', (args.task_id,))
                row = cursor.fetchone()
                
                if not row:
                    print(f"⚠️ Task {args.task_id} not found")
                else:
                    task_id, title, status, started_at, completed_at, duration_mins, created_at, assignee_id = row
                    
                    # Recalculate if requested
                    if args.recalc and status == 'done' and started_at and completed_at:
                        recalc_count = db.recalculate_durations()
                        print(f"🔄 Recalculated {recalc_count} task durations")
                        # Re-fetch
                        cursor.execute('''
                            SELECT actual_duration_minutes FROM tasks WHERE id = ?
                        ''', (args.task_id,))
                        duration_mins = cursor.fetchone()[0]
                    
                    print(f"\n⏱️  Task Duration: {task_id}")
                    print(f"   Title: {title}")
                    print(f"   Status: {status}")
                    print()
                    
                    if created_at:
                        print(f"   📅 Created:     {created_at}")
                    if started_at:
                        print(f"   🚀 Started:     {started_at}")
                    else:
                        print(f"   🚀 Started:     (not started yet)")
                    if completed_at:
                        print(f"   ✅ Completed:   {completed_at}")
                    
                    print()
                    if duration_mins:
                        formatted = db.format_duration(duration_mins)
                        print(f"   ⏱️  Duration: {formatted} ({duration_mins} minutes)")
                    elif status == 'done':
                        print(f"   ⏱️  Duration: Not recorded")
                    elif started_at:
                        # Calculate elapsed time for in-progress tasks
                        cursor.execute('''
                            SELECT ROUND((strftime('%s', 'now') - strftime('%s', started_at)) / 60)
                            FROM tasks WHERE id = ?
                        ''', (args.task_id,))
                        elapsed = cursor.fetchone()[0]
                        print(f"   ⏱️  Elapsed: {db.format_duration(elapsed)} (in progress)")
                    else:
                        print(f"   ⏱️  Duration: N/A (task not started)")
                    
                    # Show agent
                    if assignee_id:
                        print(f"   👤 Agent: {assignee_id}")
                    print()
                    
            elif args.task_action == 'list':
                tasks = db.get_tasks(status=args.status, assignee=args.agent)
                print(f"\n📋 Tasks ({len(tasks)} total):\n")
                for t in tasks:
                    status_emoji = {
                        'backlog': '📋', 'todo': '⬜', 'in_progress': '🔄',
                        'review': '👀', 'done': '✅', 'blocked': '🚧', 'cancelled': '🚫'
                    }.get(t['status'], '⬜')
                    print(f"{status_emoji} {t['id']} | {t['title'][:40]}...")
                    print(f"   Status: {t['status']} | Assignee: {t['assignee_name'] or 'Unassigned'}")
                    if t.get('progress') and t['progress'] > 0:
                        print(f"   Progress: {t['progress']}%")
                    print()
                    
        elif args.command == 'agent':
            if args.agent_action == 'list':
                agents = db.get_agents(status=args.status)
                print(f"\n🤖 Agents ({len(agents)} total):\n")
                for a in agents:
                    status_emoji = {
                        'idle': '⚪', 'active': '🟢',
                        'blocked': '🔴', 'offline': '⚫'
                    }.get(a['status'], '⚪')
                    print(f"{status_emoji} {a['name']} ({a['role']})")
                    print(f"   Status: {a['status']}")
                    print(f"   Tasks: {a['active_tasks']} active, {a['total_tasks_completed']} completed")
                    if a['avg_progress']:
                        print(f"   Avg Progress: {a['avg_progress']:.1f}%")
                    print()
                    
            elif args.agent_action == 'heartbeat':
                if db.update_agent_heartbeat(args.agent_id):
                    print(f"💓 Heartbeat updated for {args.agent_id}")
                    
            elif args.agent_action == 'context':
                if args.context_action == 'show':
                    ctx = db.get_agent_context(args.agent_id)
                    if ctx:
                        print(f"\n📝 Agent Context: {args.agent_id}\n")
                        print(f"📋 Context:\n{ctx.get('context', 'Not set')}\n")
                        print(f"🧠 Learnings:\n{ctx.get('learnings', 'None')}\n")
                        print(f"⚙️  Preferences:\n{ctx.get('preferences', 'None')}\n")
                        print(f"🕐 Last Updated: {ctx.get('last_updated', 'Never')}")
                    else:
                        print(f"⚠️ No context found for {args.agent_id}")
                        
                elif args.context_action == 'update':
                    if db.update_agent_context(args.agent_id, args.field, args.content):
                        print(f"✅ Updated {args.field} for {args.agent_id}")
                        
                elif args.context_action == 'learn':
                    ctx = db.get_agent_context(args.agent_id)
                    if ctx:
                        new_learning = f"- {args.learning}"
                        existing = ctx.get('learnings', '')
                        updated = f"{existing}\n{new_learning}" if existing else new_learning
                        if db.update_agent_context(args.agent_id, 'learnings', updated):
                            print(f"✅ Added learning to {args.agent_id}")
                    else:
                        print(f"⚠️ Agent {args.agent_id} not found")
                        
            elif args.agent_action == 'memory':
                if args.memory_action == 'show':
                    mem = db.get_working_memory(args.agent_id)
                    if mem:
                        print(f"\n📝 Working Memory: {args.agent_id}\n")
                        print(f"📌 Current Task: {mem.get('current_task_id') or 'None'}\n")
                        print(f"📝 Notes:\n{mem.get('working_notes', 'Empty')}\n")
                        print(f"🚧 Blockers:\n{mem.get('blockers', 'None')}\n")
                        print(f"📋 Next Steps:\n{mem.get('next_steps', 'None')}\n")
                        print(f"🕐 Last Updated: {mem.get('last_updated', 'Never')}")
                    else:
                        print(f"⚠️ No working memory for {args.agent_id}")
                        
                elif args.memory_action == 'update':
                    kwargs = {}
                    if args.notes:
                        kwargs['working_notes'] = args.notes
                    if args.blockers:
                        kwargs['blockers'] = args.blockers
                    if args.next_steps:
                        kwargs['next_steps'] = args.next_steps
                    if args.task:
                        kwargs['current_task_id'] = args.task
                    
                    if kwargs and db.update_working_memory(args.agent_id, **kwargs):
                        print(f"✅ Updated working memory for {args.agent_id}")
                    else:
                        print(f"⚠️ Nothing to update")
                        
            elif args.agent_action == 'comm':
                if args.comm_action == 'send':
                    msg_id = db.send_message(
                        args.from_agent, args.message,
                        args.to, args.task, args.type
                    )
                    if msg_id:
                        to_str = f"to {args.to}" if args.to else "(broadcast)"
                        print(f"✅ Message sent {to_str}: ID {msg_id}")
                    else:
                        print(f"❌ Failed to send message")
                        
                elif args.comm_action == 'inbox':
                    messages = db.get_messages(
                        args.agent_id, unread_only=args.unread
                    )
                    print(f"\n📬 Inbox for {args.agent_id} ({len(messages)} messages)\n")
                    for m in messages:
                        read_status = "🔴" if not m['is_read'] else "✅"
                        to_str = f"→ {m['to_name']}" if m['to_name'] else "(broadcast)"
                        print(f"{read_status} [{m['message_type']}] {m['from_name']} {to_str}")
                        print(f"   {m['message'][:60]}{'...' if len(m['message']) > 60 else ''}")
                        print(f"   🕐 {m['created_at']}\n")
                        
                elif args.comm_action == 'task':
                    messages = db.get_messages(task_id=args.task_id)
                    print(f"\n💬 Task Messages for {args.task_id} ({len(messages)} messages)\n")
                    for m in messages:
                        print(f"[{m['from_name']}] {m['message'][:80]}")
        
        elif args.command == 'dashboard':
            stats = db.get_dashboard_stats()
            print("\n📊 Dashboard Stats:\n")
            print(f"Total Tasks: {stats.get('total_tasks', stats.get(6, 0))}")
            print(f"  - Todo: {stats.get('todo_tasks', stats.get(7, 0))}")
            print(f"  - In Progress: {stats.get('in_progress_tasks', stats.get(8, 0))}")
            print(f"  - Done: {stats.get('completed_tasks', stats.get(9, 0))}")
            print(f"  - Blocked: {stats.get('blocked_tasks', stats.get(10, 0))}")
            print(f"\nAgents:")
            print(f"  - Total: {stats.get('total_agents', stats.get(0, 0))}")
            print(f"  - Active: {stats.get('active_agents', stats.get(1, 0))}")
            print(f"  - Idle: {stats.get('idle_agents', stats.get(2, 0))}")
            print(f"  - Blocked: {stats.get('blocked_agents', stats.get(3, 0))}")
            print(f"\nDue:")
            print(f"  - Due Today: {stats.get('due_today', stats.get(12, 0))}")
            print(f"  - Overdue: {stats.get('overdue_tasks', stats.get(13, 0))}")
            
        elif args.command == 'report':
            if args.daily:
                report = db.generate_daily_report()
                print(report)
            elif args.duration:
                stats = db.get_duration_stats()
                print("\n⏱️  Task Duration Statistics\n")
                
                overall = stats['overall']
                print("📊 Overall Statistics:")
                print(f"   Total Completed Tasks: {overall['total_completed']}")
                if overall['total_completed'] > 0:
                    print(f"   Average Duration: {overall['avg_formatted']}")
                    print(f"   Fastest Task: {overall['min_formatted']}")
                    print(f"   Slowest Task: {overall['max_formatted']}")
                print()
                
                if stats['by_agent']:
                    print("👤 By Agent:")
                    for agent in stats['by_agent']:
                        agent_avg = db.format_duration(int(agent['avg_duration_minutes'] or 0))
                        print(f"   {agent['agent_name']}: {agent['tasks_completed']} tasks, avg {agent_avg}")
                    print()
                
                if stats['recent']:
                    print("🕐 Recently Completed:")
                    for task in stats['recent'][:5]:
                        duration = db.format_duration(task['actual_duration_minutes'] or 0)
                        print(f"   {task['id']}: {duration} - {task['title'][:40]}...")
                    print()
            else:
                # Default: show usage
                print("📊 Reports")
                print("\nCommands:")
                print("  report --daily     - Generate daily report")
                print("  report --duration  - Show task duration statistics")
                
        elif args.command == 'health':
            # Health commands use their own context manager
            db.close()
            with HealthMonitor() as monitor:
                if args.health_action == 'check':
                    result = monitor.run_health_check()
                    # Exit with error code if critical issues found
                    if result['critical_count'] > 0:
                        sys.exit(1)
                elif args.health_action == 'status':
                    monitor.print_health_status()
                else:
                    # Default: show status
                    monitor.print_health_status()
            return  # Already closed db
            
        elif args.command == 'notify':
            from notifications import NotificationManager
            
            if args.notify_action == 'level':
                level_details = {
                    'minimal': 'Only block and complete events',
                    'normal': 'Assign, start, block, and complete events',
                    'verbose': 'All events including review and backlog'
                }
                if db.notifier.set_agent_level(args.agent_id, args.level):
                    print(f"✅ Set notification level for {args.agent_id} to '{args.level}'")
                    print(f"   Level details: {level_details.get(args.level, '')}")
                else:
                    print(f"⚠️ Agent {args.agent_id} not found")
                    
            elif args.notify_action == 'show':
                if args.agent:
                    level = db.notifier.get_agent_level(args.agent)
                    settings = db.notifier.get_settings('agent', args.agent)
                    event_details = {
                        'minimal': 'block, complete',
                        'normal': 'assign, start, block, complete, unblock',
                        'verbose': 'all events (assign, start, block, complete, unblock, review, backlog, create)'
                    }
                    print(f"\n📬 Notification Settings for {args.agent}:")
                    print(f"   Level: {level}")
                    print(f"   Events: {event_details.get(level, 'unknown')}")
                else:
                    # Show all agents' notification levels
                    cursor = db.conn.cursor()
                    cursor.execute('SELECT id, name, notification_level FROM agents ORDER BY id')
                    print("\n📬 Notification Levels:")
                    for row in cursor.fetchall():
                        print(f"   {row[0]}: {row[2]}")
                        
            elif args.notify_action == 'log':
                logs = db.notifier.get_notification_log(args.task, args.limit)
                print(f"\n📋 Notification Log ({len(logs)} entries):")
                for log in logs[:args.limit]:
                    status = "✅" if log['success'] else "❌"
                    print(f"   {status} [{log['sent_at']}] {log['event_type'].upper()}: {log['message'][:60]}...")
                    
            else:
                # Default: show notification help
                print("📬 Notification Management")
                print("\nCommands:")
                print("  notify level <agent_id> <minimal|normal|verbose>  - Set notification level")
                print("  notify show [--agent <agent_id>]                   - Show notification settings")
                print("  notify log [--task <task_id>] [--limit <n>]        - Show notification log")
                print("\nLevels:")
                print("  minimal - Only block and complete events")
                print("  normal  - Assign, start, block, complete, unblock events")
                print("  verbose - All events including review, backlog, create")
                    
        else:
            parser.print_help()


if __name__ == '__main__':
    main()
