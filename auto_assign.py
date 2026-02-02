#!/usr/bin/env python3
"""
AI Team Auto-Assign with Agent Context
Automatically assign idle agents to todo tasks with context awareness
"""

import os
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

os.environ['TZ'] = 'Asia/Bangkok'

DB_PATH = Path(__file__).parent / "team.db"
TELEGRAM_CHANNEL = "1268858185"

# Role matching for task assignment
ROLE_MATCH = {
    'dev': ['dev', 'solo-dev'],
    'frontend': ['dev', 'ux-designer'],
    'backend': ['dev', 'architect'],
    'database': ['architect', 'dev'],
    'api': ['dev', 'architect'],
    'ui': ['ux-designer'],
    'ux': ['ux-designer'],
    'test': ['qa'],
    'qa': ['qa'],
    'doc': ['tech-writer'],
    'document': ['tech-writer'],
    'design': ['ux-designer'],
    'plan': ['pm', 'analyst'],
    'analyze': ['analyst'],
    'review': ['qa'],
}

class AutoAssign:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        
    def close(self):
        self.conn.close()
        
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        self.close()

    def get_agent_context(self, agent_id: str) -> Dict:
        """Get agent's context from database"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT context, learnings, preferences, last_updated
            FROM agent_context WHERE agent_id = ?
        ''', (agent_id,))
        row = cursor.fetchone()
        if row:
            return {
                'context': row[0] or '',
                'learnings': row[1] or '',
                'preferences': row[2] or '',
                'last_updated': row[3]
            }
        return {'context': '', 'learnings': '', 'preferences': '', 'last_updated': None}

    def update_agent_context(self, agent_id: str, field: str, content: str):
        """Update agent's context field"""
        cursor = self.conn.cursor()
        cursor.execute(f'''
            UPDATE agent_context 
            SET {field} = ?, last_updated = CURRENT_TIMESTAMP
            WHERE agent_id = ?
        ''', (content, agent_id))
        self.conn.commit()

    def get_idle_agents(self) -> List[Dict]:
        """Get list of idle agents with their roles and context"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT a.id, a.name, a.role, a.total_tasks_completed,
                   ac.context, ac.learnings
            FROM agents a
            LEFT JOIN agent_context ac ON a.id = ac.agent_id
            WHERE a.status = 'idle'
            AND (a.current_task_id IS NULL OR a.current_task_id = '')
            ORDER BY a.total_tasks_completed ASC
        ''')
        return [dict(row) for row in cursor.fetchall()]

    def get_unassigned_todo_tasks(self) -> List[Dict]:
        """Get todo tasks without assignee, sorted by priority"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT t.id, t.title, t.description, t.priority, t.project_id,
                   t.prerequisites, t.acceptance_criteria, t.expected_outcome
            FROM tasks t
            WHERE t.status = 'todo'
            AND (t.assignee_id IS NULL OR t.assignee_id = '')
            ORDER BY 
                CASE t.priority 
                    WHEN 'critical' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'normal' THEN 3
                    WHEN 'low' THEN 4
                END,
                t.created_at ASC
        ''')
        return [dict(row) for row in cursor.fetchall()]

    def find_best_agent(self, task: Dict, agents: List[Dict]) -> Optional[Dict]:
        """Find best matching agent for a task based on keywords and context"""
        title_lower = task['title'].lower()
        desc_lower = (task.get('description') or '').lower()
        task_text = title_lower + ' ' + desc_lower
        
        best_agent = None
        best_score = -1
        
        for agent in agents:
            score = 0
            agent_role = agent['role'].lower()
            context = (agent.get('context') or '').lower()
            
            # Check role matches
            for keyword, matching_roles in ROLE_MATCH.items():
                if keyword in task_text:
                    if agent['id'] in matching_roles or agent_role in matching_roles:
                        score += 10
            
            # Check context relevance
            for word in task_text.split():
                if len(word) > 3 and word in context:
                    score += 2
            
            # Prefer agents with fewer active tasks
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM tasks 
                WHERE assignee_id = ? AND status = 'in_progress'
            ''', (agent['id'],))
            active_count = cursor.fetchone()[0]
            score -= active_count * 5
            
            if score > best_score:
                best_score = score
                best_agent = agent
        
        return best_agent

    def assign_task(self, task_id: str, agent_id: str) -> bool:
        """Assign task to agent"""
        cursor = self.conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE tasks 
                SET assignee_id = ?, status = 'todo', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (agent_id, task_id))
            
            cursor.execute('''
                UPDATE agents 
                SET total_tasks_assigned = total_tasks_assigned + 1,
                    current_task_id = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (task_id, agent_id))
            
            cursor.execute('''
                INSERT INTO task_history (task_id, agent_id, action, notes)
                VALUES (?, ?, 'assigned', 'Auto-assigned by system with context')
            ''', (task_id, agent_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"[Error] Failed to assign task: {e}")
            return False

    def spawn_subagent(self, task: Dict, agent: Dict) -> bool:
        """Spawn subagent via openclaw with full context"""
        try:
            # Build context-aware task message
            context = agent.get('context', '')
            learnings = agent.get('learnings', '')
            
            task_message = f"""## Task Assignment

**Agent:** {agent['name']} ({agent['role']})
**Task:** {task['id']} - {task['title']}

### Your Context
{context}

### Your Learnings
{learnings}

### Task Details
- **Description:** {task.get('description', 'N/A')}
- **Priority:** {task['priority']}
- **Expected Outcome:** {task.get('expected_outcome', 'N/A')}

### Prerequisites (Check before starting)
{task.get('prerequisites', 'None specified')}

### Acceptance Criteria (Must complete all)
{task.get('acceptance_criteria', 'None specified')}

### Instructions
1. Review prerequisites - ensure all are met
2. Start task: python3 team_db.py task start {task['id']}
3. Work on the task using your expertise
4. Update progress regularly
5. When done: python3 team_db.py task done {task['id']}
6. Document learnings in your context

**Remember:** You are {agent['name']}. Use your expertise and context to complete this task effectively.
"""

            # Update agent status to active
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE agents 
                SET status = 'active', last_heartbeat = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (agent['id'],))
            self.conn.commit()
            
            # Spawn subagent via openclaw API
            import subprocess
            import json
            
            # Build payload for sessions_spawn
            payload = {
                'task': task_message,
                'agent_id': agent['id'],
                'label': f"{agent['id']}-{task['id']}",
                'run_timeout_seconds': 3600,
                'cleanup': 'keep'
            }
            
            # Use openclaw gateway API
            spawn_result = subprocess.run(
                ['curl', '-s', '-X', 'POST',
                 'http://localhost:3000/api/sessions/spawn',
                 '-H', 'Content-Type: application/json',
                 '-d', json.dumps(payload)],
                capture_output=True,
                text=True
            )
            
            if spawn_result.returncode == 0 and 'sessionKey' in spawn_result.stdout:
                print(f"  🚀 Spawned {agent['name']} for {task['id']}")
            else:
                print(f"  ⚠️  Assigned to {agent['name']} - spawn via API failed, manual start needed")
            
            return True
            
        except Exception as e:
            print(f"[Error] Failed to activate: {e}")
            return False

    def send_notification(self, message: str) -> bool:
        """Send notification to Telegram"""
        try:
            result = subprocess.run(
                ["openclaw", "message", "send", "--channel", "telegram",
                 "--target", TELEGRAM_CHANNEL, "--message", message],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0
        except Exception as e:
            print(f"[Notification Error] {e}")
            return False

    def run(self) -> Dict:
        """Main auto-assign logic"""
        print("🤖 AI Team Auto-Assign with Context Starting...")
        print("=" * 60)
        
        idle_agents = self.get_idle_agents()
        todo_tasks = self.get_unassigned_todo_tasks()
        
        print(f"\n📊 Status:")
        print(f"   Idle agents: {len(idle_agents)}")
        print(f"   Unassigned tasks: {len(todo_tasks)}")
        
        if not idle_agents:
            print("\n⚠️ No idle agents available")
            return {'assigned': 0, 'agents': 0, 'tasks': len(todo_tasks)}
        
        if not todo_tasks:
            print("\n✅ No unassigned tasks")
            return {'assigned': 0, 'agents': len(idle_agents), 'tasks': 0}
        
        assigned_count = 0
        assigned_pairs = []
        
        for task in todo_tasks:
            if not idle_agents:
                break
            
            best_agent = self.find_best_agent(task, idle_agents)
            if not best_agent:
                best_agent = idle_agents[0]
            
            print(f"\n📝 Task: {task['id']}")
            print(f"   Title: {task['title']}")
            print(f"   → Agent: {best_agent['name']} (match score: context + role)")
            
            if self.assign_task(task['id'], best_agent['id']):
                if self.spawn_subagent(task, best_agent):
                    assigned_count += 1
                    assigned_pairs.append({
                        'task': task['id'],
                        'agent': best_agent['name']
                    })
                    idle_agents = [a for a in idle_agents if a['id'] != best_agent['id']]
        
        if assigned_count > 0:
            message = f"🤖 *Auto-Assigned {assigned_count} Tasks*\n\n"
            for pair in assigned_pairs:
                message += f"• {pair['task']} → {pair['agent']}\n"
            message += f"\n⏰ {datetime.now().strftime('%H:%M')}"
            self.send_notification(message)
        
        print("\n" + "=" * 60)
        print(f"✅ Auto-assign complete: {assigned_count} tasks")
        
        return {
            'assigned': assigned_count,
            'agents': len(idle_agents) + assigned_count,
            'tasks': len(todo_tasks)
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description='AI Team Auto-Assign with Context')
    parser.add_argument('--run', action='store_true', help='Run auto-assign once')
    parser.add_argument('--status', action='store_true', help='Show status')
    args = parser.parse_args()
    
    with AutoAssign() as assigner:
        if args.status:
            agents = assigner.get_idle_agents()
            tasks = assigner.get_unassigned_todo_tasks()
            print(f"Idle agents: {len(agents)}")
            print(f"Unassigned tasks: {len(tasks)}")
        else:
            result = assigner.run()


if __name__ == '__main__':
    main()
