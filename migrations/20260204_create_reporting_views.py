#!/usr/bin/env python3
"""
Migration: Create database views for monitoring dashboard and cron reports
Views: v_agent_status, v_task_overview, v_daily_summary, v_weekly_report
"""

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "team.db"

VIEWS = {
    "v_agent_status": """
        CREATE VIEW IF NOT EXISTS v_agent_status AS
        SELECT 
            a.id,
            a.name,
            a.role,
            a.status,
            a.current_task_id,
            t.title as current_task,
            a.last_heartbeat,
            ROUND((strftime('%s', 'now') - strftime('%s', a.last_heartbeat)) / 60.0, 1) as minutes_since_heartbeat,
            CASE 
                WHEN a.last_heartbeat IS NULL THEN 1
                WHEN (strftime('%s', 'now') - strftime('%s', a.last_heartbeat)) > 1800 THEN 1
                ELSE 0
            END as is_silent,
            a.total_tasks_completed,
            a.total_tasks_assigned,
            a.updated_at
        FROM agents a
        LEFT JOIN tasks t ON a.current_task_id = t.id
    """,
    
    "v_task_overview": """
        CREATE VIEW IF NOT EXISTS v_task_overview AS
        SELECT 
            t.id,
            t.title,
            t.description,
            t.project_id,
            p.name as project_name,
            t.assignee_id,
            a.name as assignee,
            a.role as assignee_role,
            t.status,
            t.priority,
            t.progress,
            t.estimated_hours,
            t.actual_hours,
            t.actual_duration_minutes,
            CASE 
                WHEN t.actual_duration_minutes IS NULL THEN NULL
                WHEN t.actual_duration_minutes >= 1440 THEN 
                    (t.actual_duration_minutes / 1440) || 'd ' || 
                    ((t.actual_duration_minutes % 1440) / 60) || 'h ' ||
                    (t.actual_duration_minutes % 60) || 'm'
                WHEN t.actual_duration_minutes >= 60 THEN
                    (t.actual_duration_minutes / 60) || 'h ' ||
                    (t.actual_duration_minutes % 60) || 'm'
                ELSE t.actual_duration_minutes || 'm'
            END as duration_formatted,
            t.due_date,
            t.started_at,
            t.completed_at,
            t.blocked_by,
            CASE 
                WHEN t.due_date < DATE('now') AND t.status NOT IN ('done', 'cancelled') THEN 'overdue'
                WHEN t.due_date = DATE('now') AND t.status NOT IN ('done', 'cancelled') THEN 'due_today'
                WHEN DATE(t.due_date) BETWEEN DATE('now') AND DATE('now', '+2 days') AND t.status NOT IN ('done', 'cancelled') THEN 'due_soon'
                ELSE 'on_track'
            END as due_status,
            t.created_at,
            t.updated_at
        FROM tasks t
        LEFT JOIN agents a ON t.assignee_id = a.id
        LEFT JOIN projects p ON t.project_id = p.id
    """,
    
    "v_daily_summary": """
        CREATE VIEW IF NOT EXISTS v_daily_summary AS
        SELECT 
            DATE('now') as date,
            (SELECT COUNT(*) FROM tasks WHERE status = 'done' AND DATE(completed_at) = DATE('now')) as tasks_completed_today,
            (SELECT COUNT(*) FROM tasks WHERE status = 'in_progress') as tasks_in_progress,
            (SELECT COUNT(*) FROM tasks WHERE status = 'blocked') as tasks_blocked,
            (SELECT COUNT(*) FROM tasks WHERE status = 'todo') as tasks_todo,
            (SELECT COUNT(*) FROM tasks WHERE status = 'review') as tasks_in_review,
            (SELECT COUNT(*) FROM agents WHERE status = 'active') as active_agents,
            (SELECT COUNT(*) FROM agents WHERE status = 'idle') as idle_agents,
            (SELECT COUNT(*) FROM tasks WHERE due_date = DATE('now') AND status NOT IN ('done', 'cancelled')) as due_today,
            (SELECT COUNT(*) FROM tasks WHERE due_date < DATE('now') AND status NOT IN ('done', 'cancelled')) as overdue_count,
            (SELECT ROUND(AVG(progress), 1) FROM tasks WHERE status = 'in_progress') as avg_progress_in_progress,
            (SELECT COUNT(*) FROM task_history WHERE DATE(timestamp) = DATE('now')) as total_actions_today
    """,
    
    "v_weekly_report": """
        CREATE VIEW IF NOT EXISTS v_weekly_report AS
        SELECT 
            DATE('now', 'weekday 0', '-7 days') as week_start,
            (SELECT COUNT(*) FROM tasks WHERE status = 'done' AND completed_at >= DATE('now', 'weekday 0', '-7 days')) as tasks_completed_this_week,
            (SELECT COUNT(*) FROM tasks WHERE DATE(created_at) >= DATE('now', 'weekday 0', '-7 days')) as tasks_created_this_week,
            (SELECT json_object('todo', (SELECT COUNT(*) FROM tasks WHERE status = 'todo'),
                                'in_progress', (SELECT COUNT(*) FROM tasks WHERE status = 'in_progress'),
                                'review', (SELECT COUNT(*) FROM tasks WHERE status = 'review'),
                                'done', (SELECT COUNT(*) FROM tasks WHERE status = 'done'),
                                'blocked', (SELECT COUNT(*) FROM tasks WHERE status = 'blocked'),
                                'cancelled', (SELECT COUNT(*) FROM tasks WHERE status = 'cancelled'))) as tasks_by_status,
            (SELECT ROUND(AVG(
                CAST((strftime('%s', completed_at) - strftime('%s', started_at)) AS REAL) / 3600
            ), 2) FROM tasks 
            WHERE status = 'done' 
            AND started_at IS NOT NULL 
            AND completed_at IS NOT NULL) as avg_completion_time_hours,
            (SELECT COUNT(*) FROM task_history WHERE timestamp >= DATE('now', 'weekday 0', '-7 days')) as total_actions_this_week,
            (SELECT COUNT(DISTINCT agent_id) FROM task_history WHERE timestamp >= DATE('now', 'weekday 0', '-7 days') AND agent_id IS NOT NULL) as active_agent_count
    """
}

def migrate():
    """Create database views for monitoring and reporting"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    created_views = []
    
    for view_name, view_sql in VIEWS.items():
        try:
            # Drop existing view if exists
            cursor.execute(f"DROP VIEW IF EXISTS {view_name}")
            # Create new view
            cursor.execute(view_sql)
            created_views.append(view_name)
            print(f"✅ Created view: {view_name}")
        except sqlite3.Error as e:
            print(f"❌ Error creating view {view_name}: {e}")
            conn.rollback()
            conn.close()
            sys.exit(1)
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Successfully created {len(created_views)} views:")
    for view in created_views:
        print(f"   - {view}")
    
    return True

def rollback():
    """Drop all created views"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    for view_name in VIEWS.keys():
        try:
            cursor.execute(f"DROP VIEW IF EXISTS {view_name}")
            print(f"✅ Dropped view: {view_name}")
        except sqlite3.Error as e:
            print(f"❌ Error dropping view {view_name}: {e}")
    
    conn.commit()
    conn.close()
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        rollback()
    else:
        migrate()
