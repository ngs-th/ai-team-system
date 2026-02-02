#!/usr/bin/env python3
"""
AI Team Spawn Manager - Spawns subagents for assigned tasks
Called by cron job every 5 minutes
"""

import os
import sqlite3
import json
from datetime import datetime
from pathlib import Path

os.environ['TZ'] = 'Asia/Bangkok'

DB_PATH = Path(__file__).parent / "team.db"

def get_assigned_tasks_without_sessions():
    """Get tasks that are assigned but no subagent running"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get all assigned todo tasks
    cursor.execute('''
        SELECT t.id, t.title, t.description, t.assignee_id, t.priority,
               t.prerequisites, t.acceptance_criteria, t.expected_outcome,
               a.name as agent_name, a.role as agent_role
        FROM tasks t
        JOIN agents a ON t.assignee_id = a.id
        WHERE t.status = 'todo' 
        AND t.assignee_id IS NOT NULL
        AND t.assignee_id != ''
    ''')
    
    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tasks

def get_agent_context(agent_id):
    """Get agent context from database"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute('''
        SELECT context, learnings FROM agent_context WHERE agent_id = ?
    ''', (agent_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {'context': row[0] or '', 'learnings': row[1] or ''}
    return {'context': '', 'learnings': ''}

def build_task_message(task, agent_context):
    """Build task message for subagent"""
    return f"""## Task Assignment

**Agent:** {task['agent_name']} ({task['agent_role']})
**Task:** {task['id']} - {task['title']}

### Your Context
{agent_context['context']}

### Your Learnings
{agent_context['learnings']}

### Task Details
- **Description:** {task.get('description') or 'N/A'}
- **Priority:** {task['priority']}
- **Expected Outcome:** {task.get('expected_outcome') or 'N/A'}

### Prerequisites (Check before starting)
{task.get('prerequisites') or 'None specified'}

### Acceptance Criteria (Must complete all)
{task.get('acceptance_criteria') or 'None specified'}

### Instructions
1. Review prerequisites - ensure all are met
2. Start task: python3 team_db.py task start {task['id']}
3. **UPDATE WORKING MEMORY** ทุก 30 นาที:
   ```bash
   python3 agent_memory_writer.py working {task['assignee_id']} --task {task['id']} --notes "What I'm doing now"
   ```
4. ถ้าติดปัญหา: Update blockers
   ```bash
   python3 agent_memory_writer.py working {task['assignee_id']} --blockers "Stuck on X"
   ```
5. Update progress: python3 team_db.py task progress {task['id']} <pct>
6. When done: python3 team_db.py task done {task['id']}
7. **ADD LEARNING** ก่อนจบ:
   ```bash
   python3 agent_memory_writer.py learn {task['assignee_id']} "What I learned from this task"
   ```

**⚠️ CRITICAL RULES - FOLLOW EXACTLY:**
1. You are {task['agent_name']} - work autonomously but ASK FOR HELP if stuck after 3 attempts
2. **MUST update working memory every 30 minutes**
3. **🔴 FORBIDDEN: HTML tags** - Never use <b>, <code>, <i>, <anything>
4. **✅ USE THIS to send all messages:**
   ```bash
   python3 message_filter.py "Your message here"
   ```
   This will auto-strip HTML and send to Telegram.
5. **Markdown OK:** Use **bold**, `code`, _italic_ (NOT HTML)
6. Progress bar: [████░░░░░░] 40% (simple text, no HTML)
"""

def main():
    print(f"🤖 AI Team Spawn Manager - {datetime.now()}")
    print("=" * 60)
    
    tasks = get_assigned_tasks_without_sessions()
    
    if not tasks:
        print("✅ No tasks need spawning")
        return 0
    
    print(f"📋 Found {len(tasks)} tasks to spawn\n")
    
    for task in tasks:
        print(f"📝 {task['id']}: {task['title']}")
        print(f"   → {task['agent_name']} ({task['agent_role']})")
        
        # Get agent context
        agent_ctx = get_agent_context(task['assignee_id'])
        
        # Build task message
        task_message = build_task_message(task, agent_ctx)
        
        # Output spawn command (will be executed by parent agent)
        spawn_cmd = {
            'action': 'spawn',
            'task': task_message,
            'agent_id': task['assignee_id'],
            'label': f"{task['assignee_id']}-{task['id']}",
            'run_timeout_seconds': 3600
        }
        
        print(f"   📤 Spawn command prepared")
        print(f"   💡 Use: sessions_spawn with agent_id={task['assignee_id']}")
        print()
    
    return len(tasks)

if __name__ == '__main__':
    count = main()
    exit(0 if count == 0 else 1)
