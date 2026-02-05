#!/usr/bin/env python3
"""
AI Team Orchestrator
Autonomous multi-agent orchestration system
Receives high-level goals, breaks down tasks, manages agents
"""

import os
import sqlite3
import subprocess
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Import notification system
from notifications import NotificationManager, NotificationEvent
import time

os.environ['TZ'] = 'Asia/Bangkok'
try:
    time.tzset()
except AttributeError:
    pass

DB_PATH = Path(__file__).parent / "team.db"
TELEGRAM_CHANNEL = "1268858185"

class AITeamOrchestrator:
    """Main orchestrator for autonomous AI Team operations"""
    
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self.running_missions = []
        self.notifier = NotificationManager(db_path, TELEGRAM_CHANNEL)
        
    def close(self):
        self.notifier.close()
        self.conn.close()
        
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        self.close()

    def receive_goal(self, goal_type: str, title: str, description: str, 
                     expected_outcome: str, assignee: str = None) -> str:
        """
        Receive a high-level goal from user
        Types: 'feature', 'bugfix', 'documentation', 'analysis', 'refactor'
        """
        print(f"\n🎯 ORCHESTRATOR: Received {goal_type} goal")
        print(f"   Title: {title}")
        print(f"   Expected: {expected_outcome}")
        
        # Create mission record
        mission_id = f"M-{datetime.now().strftime('%Y%m%d')}-{self._get_next_mission_number():03d}"
        
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO orchestrator_missions 
            (id, goal_type, title, description, expected_outcome, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'planning', datetime('now'))
        ''', (mission_id, goal_type, title, description, expected_outcome))
        
        self.conn.commit()
        
        # Auto-assign to orchestrator or specified assignee
        orchestrator = assignee or 'architect'  # Default to architect for planning
        
        print(f"   Mission ID: {mission_id}")
        print(f"   Assigned to: {orchestrator} for breakdown")
        
        # Spawn orchestrator agent to break down the mission
        self._spawn_orchestrator_agent(mission_id, orchestrator)
        
        return mission_id

    def _spawn_orchestrator_agent(self, mission_id: str, orchestrator_id: str):
        """Spawn orchestrator subagent to break down mission"""
        cursor = self.conn.cursor()
        
        # Get orchestrator context
        cursor.execute('''
            SELECT context, learnings FROM agent_context WHERE agent_id = ?
        ''', (orchestrator_id,))
        row = cursor.fetchone()
        context = row[0] if row else ''
        learnings = row[1] if row else ''
        
        # Get mission details
        cursor.execute('''
            SELECT * FROM orchestrator_missions WHERE id = ?
        ''', (mission_id,))
        mission = dict(cursor.fetchone())
        
        # Build orchestration message
        orchestration_message = f"""# 🎯 ORCHESTRATOR MISSION

**Mission ID:** {mission_id}
**Type:** {mission['goal_type']}
**Status:** PLANNING PHASE

## Your Role as Orchestrator
{context}

## Mission
**Title:** {mission['title']}
**Description:** {mission['description']}
**Expected Outcome:** {mission['expected_outcome']}

## Your Task
1. Analyze this {mission['goal_type']} goal
2. Break down into sub-tasks (3-10 tasks)
3. Identify dependencies between tasks
4. Assign tasks to appropriate agents based on:
   - Agent expertise (check agent_context)
   - Workload (check active tasks)
   - Task complexity
5. Create all tasks in database
6. Set task dependencies
7. Start the first independent tasks

## Task Creation Template
For each sub-task, create with:
- Title: Clear action-oriented title
- Expected Outcome: Specific deliverable
- Prerequisites: What must be done first
- Acceptance Criteria: How to verify complete
- Assignee: Best matching agent

## Available Agents
Check agent_context table for:
- dev (Amelia) - Full-stack development
- architect (Winston) - System design
- qa (Quinn) - Testing
- tech-writer (Tom) - Documentation
- ux-designer (Sally) - UI/UX
- analyst (Mary) - Requirements
- pm (John) - Planning

## Commands to Use
```bash
# Create task
python3 team_db.py task create "Task Title" \
  --project PROJ-001 \
  --expected-outcome "What success looks like" \
  --prerequisites "- [ ] Dependency done" \
  --acceptance "- [ ] Criteria met"

# Assign to agent
python3 team_db.py task assign <task_id> <agent_id>

# Start task
python3 team_db.py task start <task_id>

# Check agent availability
python3 team_db.py agent list
```

## Success Criteria
- [ ] All sub-tasks created with clear outcomes
- [ ] Dependencies mapped correctly
- [ ] Tasks assigned to appropriate agents
- [ ] First batch of independent tasks started
- [ ] Mission status updated to 'executing'

**Begin breakdown now. Work autonomously.**
"""

        # Note: In real implementation, this would spawn via sessions_spawn
        # For now, we save the orchestration message for manual execution
        cursor.execute('''
            UPDATE orchestrator_missions 
            SET orchestration_plan = ?, status = 'ready'
            WHERE id = ?
        ''', (orchestration_message, mission_id))
        
        self.conn.commit()
        
        print(f"\n📋 ORCHESTRATION PLAN CREATED")
        print(f"   View: python3 orchestrator.py show-mission {mission_id}")
        print(f"   Execute: python3 orchestrator.py execute-mission {mission_id}")

    def show_mission(self, mission_id: str):
        """Display mission details and orchestration plan"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM orchestrator_missions WHERE id = ?
        ''', (mission_id,))
        mission = cursor.fetchone()
        
        if not mission:
            print(f"❌ Mission {mission_id} not found")
            return
        
        mission = dict(mission)
        print(f"\n🎯 MISSION: {mission_id}")
        print(f"   Type: {mission['goal_type']}")
        print(f"   Title: {mission['title']}")
        print(f"   Status: {mission['status']}")
        print(f"   Created: {mission['created_at']}")
        
        if mission['orchestration_plan']:
            print(f"\n📋 ORCHESTRATION PLAN:")
            print("=" * 60)
            print(mission['orchestration_plan'])
            print("=" * 60)

    def list_missions(self, status: str = None):
        """List all missions"""
        cursor = self.conn.cursor()
        
        if status:
            cursor.execute('''
                SELECT id, goal_type, title, status, created_at 
                FROM orchestrator_missions WHERE status = ?
                ORDER BY created_at DESC
            ''', (status,))
        else:
            cursor.execute('''
                SELECT id, goal_type, title, status, created_at 
                FROM orchestrator_missions 
                ORDER BY created_at DESC
            ''')
        
        missions = [dict(row) for row in cursor.fetchall()]
        
        print(f"\n🎯 ORCHESTRATOR MISSIONS ({len(missions)} total)")
        print("-" * 70)
        print(f"{'ID':<15} {'Type':<12} {'Status':<12} {'Title':<30}")
        print("-" * 70)
        
        for m in missions:
            print(f"{m['id']:<15} {m['goal_type']:<12} {m['status']:<12} {m['title'][:28]:<30}")

    def monitor_execution(self):
        """Monitor all active missions and agent progress"""
        cursor = self.conn.cursor()
        
        print("\n🔍 ORCHESTRATOR MONITOR")
        print("=" * 70)
        
        # Get active missions
        cursor.execute('''
            SELECT * FROM orchestrator_missions 
            WHERE status IN ('planning', 'executing', 'reviewing')
        ''')
        missions = [dict(row) for row in cursor.fetchall()]
        
        print(f"\n📊 Active Missions: {len(missions)}")
        for m in missions:
            print(f"\n   {m['id']}: {m['title']}")
            print(f"   Status: {m['status']}")
            
            # Count related tasks
            # (Would need mission_tasks table for full tracking)
        
        # Get active agents
        cursor.execute('''
            SELECT a.name, a.status, a.current_task_id, t.title
            FROM agents a
            LEFT JOIN tasks t ON a.current_task_id = t.id
            WHERE a.status = 'active'
        ''')
        agents = cursor.fetchall()
        
        print(f"\n👥 Active Agents: {len(agents)}")
        for a in agents:
            print(f"   {a[0]}: {a[3] or 'No task'}")
        
        # Get stuck tasks
        cursor.execute('''
            SELECT COUNT(*) FROM tasks 
            WHERE status = 'in_progress' 
            AND updated_at < datetime('now', '-2 hours')
        ''')
        stuck = cursor.fetchone()[0]
        
        if stuck > 0:
            print(f"\n⚠️  Stuck Tasks: {stuck}")
        
        # Get tasks with high fix loop counts (approaching limit)
        cursor.execute('''
            SELECT t.id, t.title, t.fix_loop_count, a.name as assignee_name
            FROM tasks t
            LEFT JOIN agents a ON t.assignee_id = a.id
            WHERE t.fix_loop_count > 0
            ORDER BY t.fix_loop_count DESC
            LIMIT 5
        ''')
        fix_loop_tasks = [dict(row) for row in cursor.fetchall()]
        
        if fix_loop_tasks:
            print(f"\n🔄 Fix Loop Status:")
            for t in fix_loop_tasks:
                warning = ""
                if t['fix_loop_count'] >= 10:
                    warning = " 🛑 AUTO-STOPPED"
                elif t['fix_loop_count'] >= 7:
                    warning = " ⚠️ NEAR LIMIT"
                print(f"   {t['id']}: {t['fix_loop_count']}/10{warning} - {t['assignee_name'] or 'Unassigned'}")
        
        print("\n" + "=" * 70)

    def handle_failure(self, task_id: str, failure_reason: str):
        """Handle failed task - reassign or escalate with auto-stop at 10 fix loops"""
        print(f"\n🚨 HANDLING FAILURE: {task_id}")
        print(f"   Reason: {failure_reason}")
        
        cursor = self.conn.cursor()
        
        # Get task details
        cursor.execute('''
            SELECT t.*, a.name as assignee_name 
            FROM tasks t 
            JOIN agents a ON t.assignee_id = a.id
            WHERE t.id = ?
        ''', (task_id,))
        task = dict(cursor.fetchone())
        
        if not task:
            print(f"   ❌ Task {task_id} not found")
            return
        
        # Check retry count
        fix_loops = task.get('fix_loop_count', 0)
        
        if fix_loops >= 9:  # This will be the 10th loop (9+1)
            # Auto-stop: Block task after 10 fix loops
            new_count = fix_loops + 1
            blocked_reason = f"""🛑 AUTO-STOPPED after {new_count} fix loops

Original failure: {failure_reason}

This task has exceeded the maximum allowed fix loops (10) to prevent infinite loops and excessive token consumption.

TO RESUME:
1. Investigate the root cause manually
2. Use: python3 orchestrator.py resume-task {task_id} --agent <agent_id>
   or: python3 team_db.py task unblock {task_id}
3. This will reset the fix loop counter and allow the agent to continue
"""
            print(f"   🛑 Fix loops exceeded ({new_count}/10). Auto-stopping task.")
            
            cursor.execute('''
                UPDATE tasks 
                SET status = 'blocked', 
                    blocked_reason = ?,
                    fix_loop_count = ?,
                    updated_at = datetime('now', 'localtime')
                WHERE id = ?
            ''', (blocked_reason, new_count, task_id))
            
            # Update agent status
            cursor.execute('''
                UPDATE agents 
                SET status = 'blocked', current_task_id = NULL,
                    updated_at = datetime('now', 'localtime')
                WHERE id = (SELECT assignee_id FROM tasks WHERE id = ?)
            ''', (task_id,))
            
            # Log to task history
            cursor.execute('''
                INSERT INTO task_history (task_id, action, old_status, new_status, notes)
                VALUES (?, 'auto-stopped', 'in_progress', 'blocked', ?)
            ''', (task_id, f"Auto-stopped after {new_count} fix loops: {failure_reason}"))
            
            self.conn.commit()
            
            # Send notification using NotificationManager
            self.notifier.notify(
                event=NotificationEvent.AUTO_STOP,
                task_id=task_id,
                task_title=task.get('title', 'Unknown'),
                agent_id=task.get('assignee_id'),
                agent_name=task.get('assignee_name', 'Unknown'),
                entity_type='agent',
                entity_id=task.get('assignee_id', 'unknown'),
                fix_loops=new_count
            )
            
            # Also send detailed message via legacy notification
            self._notify(
                f"🚫 TASK AUTO-STOPPED: {task_id}\n"
                f"Task exceeded 10 fix loops and was automatically stopped.\n"
                f"Assignee: {task.get('assignee_name', 'Unknown')}\n"
                f"To resume: python3 orchestrator.py resume-task {task_id} --agent <agent_id>"
            )
            
        else:
            # Increment and continue
            new_count = fix_loops + 1
            print(f"   🔄 Retry {new_count}/10")
            
            cursor.execute('''
                UPDATE tasks 
                SET fix_loop_count = ?, updated_at = datetime('now', 'localtime')
                WHERE id = ?
            ''', (new_count, task_id))
            
            # Log the retry
            cursor.execute('''
                INSERT INTO task_history (task_id, action, notes)
                VALUES (?, 'fix-loop', ?)
            ''', (task_id, f"Fix loop {new_count}/10: {failure_reason}"))
            
            self.conn.commit()
    
    def resume_task(self, task_id: str, agent_id: str = None, reason: str = "") -> bool:
        """
        Resume an auto-stopped task after manual intervention.
        Resets fix_loop_count and changes status back to in_progress.
        """
        cursor = self.conn.cursor()
        
        # Get task details
        cursor.execute('''
            SELECT t.*, a.name as assignee_name 
            FROM tasks t 
            LEFT JOIN agents a ON t.assignee_id = a.id
            WHERE t.id = ?
        ''', (task_id,))
        row = cursor.fetchone()
        
        if not row:
            print(f"❌ Task {task_id} not found")
            return False
        
        task = dict(row)
        
        if task['status'] != 'blocked':
            print(f"⚠️  Task {task_id} is not blocked (status: {task['status']})")
            return False
        
        # Check if it was auto-stopped (has high fix_loop_count)
        if task.get('fix_loop_count', 0) < 10:
            print(f"⚠️  Task {task_id} was not auto-stopped (fix loops: {task.get('fix_loop_count', 0)})")
            print(f"   Use: python3 team_db.py task unblock {task_id}")
            return False
        
        # Determine agent to assign
        resume_agent = agent_id or task.get('assignee_id')
        if not resume_agent:
            print(f"❌ No agent specified and task has no current assignee")
            print(f"   Use: python3 orchestrator.py resume-task {task_id} --agent <agent_id>")
            return False
        
        # Reset fix loops and unblock
        cursor.execute('''
            UPDATE tasks 
            SET status = 'in_progress',
                fix_loop_count = 0,
                blocked_reason = NULL,
                started_at = datetime('now', 'localtime'),
                updated_at = datetime('now', 'localtime'),
                assignee_id = ?
            WHERE id = ?
        ''', (resume_agent, task_id))
        
        # Update agent status
        cursor.execute('''
            UPDATE agents 
            SET status = 'active', current_task_id = ?,
                updated_at = datetime('now', 'localtime')
            WHERE id = ?
        ''', (task_id, resume_agent))
        
        # Log the resume
        resume_note = f"Resumed after auto-stop. {reason}".strip()
        cursor.execute('''
            INSERT INTO task_history (task_id, action, old_status, new_status, agent_id, notes)
            VALUES (?, 'resumed', 'blocked', 'in_progress', ?, ?)
        ''', (task_id, resume_agent, resume_note))
        
        self.conn.commit()
        
        print(f"✅ Task {task_id} resumed")
        print(f"   Agent: {resume_agent}")
        print(f"   Fix loops reset to: 0")
        print(f"   Status: in_progress")
        
        # Notify
        self._notify(
            f"✅ TASK RESUMED: {task_id}\n"
            f"Task has been manually resumed after auto-stop.\n"
            f"Assigned to: {resume_agent}\n"
            f"Fix loop counter reset to 0."
        )
        
        return True

    def _notify(self, message: str):
        """Send notification to Telegram"""
        try:
            subprocess.run(
                ["openclaw", "message", "send", "--channel", "telegram",
                 "--target", TELEGRAM_CHANNEL, "--message", message],
                capture_output=True, text=True, timeout=30
            )
        except Exception as e:
            print(f"[Notification Error] {e}")

    def check_fix_loop_status(self, task_id: str = None):
        """Check fix loop status for a task or all tasks approaching limit"""
        cursor = self.conn.cursor()
        
        if task_id:
            # Check specific task
            cursor.execute('''
                SELECT t.id, t.title, t.status, t.fix_loop_count, t.blocked_reason,
                       a.name as assignee_name
                FROM tasks t
                LEFT JOIN agents a ON t.assignee_id = a.id
                WHERE t.id = ?
            ''', (task_id,))
            row = cursor.fetchone()
            
            if not row:
                print(f"❌ Task {task_id} not found")
                return
            
            task = dict(row)
            print(f"\n🔍 Fix Loop Status: {task_id}")
            print(f"   Title: {task['title']}")
            print(f"   Status: {task['status']}")
            print(f"   Assignee: {task['assignee_name'] or 'Unassigned'}")
            print(f"   Fix Loops: {task['fix_loop_count']}/10")
            
            remaining = 10 - task['fix_loop_count']
            if task['fix_loop_count'] >= 10:
                print(f"   ⚠️  Task AUTO-STOPPED - Manual intervention required")
                print(f"   To resume: python3 orchestrator.py resume-task {task_id} --agent <agent_id>")
            elif remaining <= 3:
                print(f"   ⚠️  WARNING: Only {remaining} fix loops remaining!")
            else:
                print(f"   ✅ {remaining} fix loops remaining")
                
            if task['blocked_reason']:
                print(f"\n   Blocked Reason:")
                for line in task['blocked_reason'].split('\n')[:5]:
                    print(f"   {line}")
        else:
            # List all tasks with fix loops > 0
            cursor.execute('''
                SELECT t.id, t.title, t.status, t.fix_loop_count, a.name as assignee_name
                FROM tasks t
                LEFT JOIN agents a ON t.assignee_id = a.id
                WHERE t.fix_loop_count > 0
                ORDER BY t.fix_loop_count DESC
            ''')
            tasks = [dict(row) for row in cursor.fetchall()]
            
            print(f"\n🔄 Tasks with Fix Loops ({len(tasks)} total):")
            print("-" * 70)
            
            for t in tasks:
                status_emoji = {
                    'blocked': '🚫', 'in_progress': '🔄', 'todo': '⬜',
                    'review': '👀', 'done': '✅'
                }.get(t['status'], '⬜')
                
                warning = ""
                if t['fix_loop_count'] >= 10:
                    warning = " 🛑 AUTO-STOPPED"
                elif t['fix_loop_count'] >= 7:
                    warning = " ⚠️ "
                
                print(f"{status_emoji} {t['id']} | Loops: {t['fix_loop_count']}/10{warning}")
                print(f"   {t['title'][:50]}...")
                print(f"   Status: {t['status']} | Assignee: {t['assignee_name'] or 'Unassigned'}")
                print()

    def _get_next_mission_number(self) -> int:
        """Get next mission sequence number"""
        cursor = self.conn.cursor()
        today = datetime.now().strftime('%Y%m%d')
        cursor.execute('''
            SELECT COUNT(*) FROM orchestrator_missions 
            WHERE id LIKE ?
        ''', (f'M-{today}-%',))
        return cursor.fetchone()[0] + 1


def main():
    import argparse
    parser = argparse.ArgumentParser(description='AI Team Orchestrator')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Receive goal
    goal = subparsers.add_parser('goal', help='Receive new goal')
    goal.add_argument('type', choices=['feature', 'bugfix', 'documentation', 'analysis', 'refactor'])
    goal.add_argument('title', help='Goal title')
    goal.add_argument('--desc', default='', help='Description')
    goal.add_argument('--outcome', required=True, help='Expected outcome')
    goal.add_argument('--assignee', help='Orchestrator agent (default: architect)')
    
    # List missions
    list_cmd = subparsers.add_parser('list', help='List missions')
    list_cmd.add_argument('--status', choices=['planning', 'executing', 'reviewing', 'completed', 'failed'])
    
    # Show mission
    show = subparsers.add_parser('show', help='Show mission details')
    show.add_argument('mission_id', help='Mission ID')
    
    # Monitor
    monitor = subparsers.add_parser('monitor', help='Monitor execution')
    
    # Resume auto-stopped task
    resume = subparsers.add_parser('resume-task', help='Resume an auto-stopped task after manual intervention')
    resume.add_argument('task_id', help='Task ID to resume')
    resume.add_argument('--agent', help='Agent ID to assign (optional, defaults to previous assignee)')
    resume.add_argument('--reason', default='', help='Reason for resuming')
    
    # Handle failure (for testing or manual trigger)
    fail = subparsers.add_parser('handle-failure', help='Handle task failure (increment fix loop)')
    fail.add_argument('task_id', help='Task ID')
    fail.add_argument('reason', help='Failure reason')
    
    # Fix loop status check
    fix_status = subparsers.add_parser('fix-status', help='Check fix loop status')
    fix_status.add_argument('--task', help='Specific task ID (optional, shows all if omitted)')
    
    args = parser.parse_args()
    
    with AITeamOrchestrator() as orch:
        if args.command == 'goal':
            mission_id = orch.receive_goal(
                args.type, args.title, args.desc, 
                args.outcome, args.assignee
            )
            print(f"\n✅ Mission created: {mission_id}")
            
        elif args.command == 'list':
            orch.list_missions(args.status)
            
        elif args.command == 'show':
            orch.show_mission(args.mission_id)
            
        elif args.command == 'monitor':
            orch.monitor_execution()
            
        elif args.command == 'resume-task':
            orch.resume_task(args.task_id, args.agent, args.reason)
            
        elif args.command == 'handle-failure':
            orch.handle_failure(args.task_id, args.reason)
            
        elif args.command == 'fix-status':
            orch.check_fix_loop_status(args.task)
            
        else:
            parser.print_help()


if __name__ == '__main__':
    main()
