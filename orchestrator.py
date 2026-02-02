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

os.environ['TZ'] = 'Asia/Bangkok'

DB_PATH = Path(__file__).parent / "team.db"
TELEGRAM_CHANNEL = "1268858185"

class AITeamOrchestrator:
    """Main orchestrator for autonomous AI Team operations"""
    
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self.running_missions = []
        
    def close(self):
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
        
        print("\n" + "=" * 70)

    def handle_failure(self, task_id: str, failure_reason: str):
        """Handle failed task - reassign or escalate"""
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
        
        # Check retry count
        fix_loops = task.get('fix_loop_count', 0)
        
        if fix_loops >= 10:
            # Block task
            print(f"   Fix loops exceeded (10). Blocking task.")
            cursor.execute('''
                UPDATE tasks SET status = 'blocked', blocked_reason = ?
                WHERE id = ?
            ''', (f"Auto-blocked: {failure_reason}", task_id))
            
            # Notify
            self._notify(f"🚫 Task {task_id} auto-blocked after 10 retries")
        else:
            # Increment and reassign
            new_count = fix_loops + 1
            print(f"   Retry {new_count}/10")
            
            cursor.execute('''
                UPDATE tasks SET fix_loop_count = ? WHERE id = ?
            ''', (new_count, task_id))
        
        self.conn.commit()

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
            
        else:
            parser.print_help()


if __name__ == '__main__':
    main()
