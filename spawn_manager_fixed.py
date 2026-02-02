#!/usr/bin/env python3
"""
AI Team Spawn Manager - FIXED VERSION
Prevents duplicate spawns and handles sessions properly
"""

import os
import sqlite3
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

os.environ['TZ'] = 'Asia/Bangkok'
DB_PATH = Path(__file__).parent / "team.db"

def get_active_sessions() -> Dict[str, datetime]:
    """Get currently active subagent sessions from OpenClaw"""
    try:
        result = subprocess.run(
            ['openclaw', 'sessions_list', '--active-minutes', '60'],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            # Parse output for active sessions with task labels
            active = {}
            for line in result.stdout.split('\n'):
                if 'label' in line and 'T-20260202' in line:
                    # Extract task ID from label
                    parts = line.split()
                    for part in parts:
                        if 'T-20260202' in part:
                            task_id = part.strip('",:')
                            active[task_id] = datetime.now()
            return active
    except Exception as e:
        print(f"[Warning] Could not get active sessions: {e}")
    return {}

def get_tasks_to_spawn() -> List[Dict]:
    """Get tasks that need spawning (assigned, todo, not being worked on)"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get assigned todo tasks
    cursor.execute('''
        SELECT t.id, t.title, t.description, t.assignee_id, t.priority,
               t.prerequisites, t.acceptance_criteria, t.expected_outcome,
               a.name as agent_name, a.role as agent_role
        FROM tasks t
        JOIN agents a ON t.assignee_id = a.id
        WHERE t.status = 'todo' 
        AND t.assignee_id IS NOT NULL
        AND t.assignee_id != ''
        AND t.updated_at < datetime('now', '-2 minutes')  -- Wait 2 min after assign
    ''')
    
    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tasks

def was_recently_spawned(task_id: str, minutes: int = 10) -> bool:
    """Check if task was spawned recently"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 1 FROM task_history 
        WHERE task_id = ? 
        AND action = 'spawned'
        AND timestamp > datetime('now', '-? minutes')
        LIMIT 1
    ''', (task_id, minutes))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def get_agent_context(agent_id: str) -> Dict:
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

def build_task_message(task: Dict, agent_context: Dict) -> str:
    """Build task message with STRICT no-HTML rules"""
    return f"""## 🚨 CRITICAL: NO HTML ALLOWED 🚨

**You are {task['agent_name']} ({task['agent_role']})**
**Task:** {task['id']} - {task['title']}

### ⚠️ FORBIDDEN (NEVER USE):
- ❌ `\u003cb\u003e`, `\u003c/b\u003e` - Use `**bold**` instead
- ❌ `\u003ccode\u003e`, `\u003c/code\u003e` - Use backticks instead  
- ❌ `\u003ci\u003e`, `\u003c/i\u003e` - Use `_italic_` instead
- ❌ ANY HTML tags

### Your Context
{agent_context['context']}

### Your Learnings
{agent_context['learnings']}

### Task Details
- **Description:** {task.get('description') or 'N/A'}
- **Priority:** {task['priority']}
- **Expected Outcome:** {task.get('expected_outcome') or 'N/A'}

### 📝 MANDATORY MEMORY UPDATES (ทุก 30 นาที)

**ต้องอัพเดต working memory ทุก 30 นาที:**
```bash
python3 agent_memory_writer.py working {task['assignee_id']} \
  --task {task['id']} \
  --notes "สิ่งที่กำลังทำตอนนี้" \
  --blockers "ติดปัญหาอะไร (ถ้ามี)" \
  --next "จะทำอะไรต่อไป"
```

**ก่อนจบงาน ต้อง add learning:**
```bash
python3 agent_memory_writer.py learn {task['assignee_id']} \
  "สิ่งที่เรียนรู้จากงานนี้"
```

### 📋 Instructions
1. Start: `python3 team_db.py task start {task['id']}`
2. **อัพเดต working memory ทุก 30 นาที** (บังคับ)
3. Update progress: `python3 team_db.py task progress {task['id']} \u003cpct\u003e`
4. **Add learning ก่อนจบ** (บังคับ)
5. Done: `python3 team_db.py task done {task['id']}`

**⚠️ ถ้าไม่อัพเดต memory งานจะไม่ผ่าน review!**
"""

def log_spawn(task_id: str, agent_id: str):
    """Log that task was spawned"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO task_history (task_id, agent_id, action, notes)
        VALUES (?, ?, 'spawned', 'Subagent spawned via spawn_manager')
    ''', (task_id, agent_id))
    conn.commit()
    conn.close()

def main():
    print(f"🤖 AI Team Spawn Manager (FIXED) - {datetime.now()}")
    print("=" * 60)
    
    # Get active sessions to avoid duplicates
    active_sessions = get_active_sessions()
    print(f"Active sessions: {len(active_sessions)}")
    
    # Get tasks to spawn
    tasks = get_tasks_to_spawn()
    print(f"Assigned todo tasks: {len(tasks)}")
    
    spawned = []
    skipped = []
    
    for task in tasks:
        task_id = task['id']
        
        # Check 1: Already has active session?
        if task_id in active_sessions:
            print(f"⏭️  {task_id}: Already has active session, skipping")
            skipped.append((task_id, "active session exists"))
            continue
        
        # Check 2: Spawned recently?
        if was_recently_spawned(task_id):
            print(f"⏭️  {task_id}: Spawned recently, skipping")
            skipped.append((task_id, "spawned recently"))
            continue
        
        # Spawn
        print(f"🚀 {task_id}: Spawning {task['agent_name']}")
        
        agent_ctx = get_agent_context(task['assignee_id'])
        task_message = build_task_message(task, agent_ctx)
        
        log_spawn(task_id, task['assignee_id'])
        spawned.append({
            'task_id': task_id,
            'agent': task['agent_name'],
            'message': task_message
        })
    
    print("\n" + "=" * 60)
    print(f"✅ Spawned: {len(spawned)}")
    print(f"⏭️  Skipped: {len(skipped)}")
    
    if spawned:
        print("\nSpawned tasks:")
        for s in spawned:
            print(f"  - {s['task_id']}: {s['agent']}")
    
    return len(spawned)

if __name__ == '__main__':
    count = main()
    exit(0 if count > 0 else 0)  # Always exit 0 to prevent cron errors
