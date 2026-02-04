#!/usr/bin/env python3
"""
AI Team Spawn Manager - FIXED VERSION
Prevents duplicate spawns and handles sessions properly
"""

import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

os.environ['TZ'] = 'Asia/Bangkok'
DB_PATH = Path(__file__).parent / "team.db"

# Import audit logger
from audit_log import AuditLogger
from agent_runtime import get_active_sessions, get_runtime, spawn_agent

audit = AuditLogger()

def update_task_runtime(task_id: str, runtime: str) -> None:
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE tasks
        SET runtime = ?,
            runtime_at = datetime('now', 'localtime'),
            updated_at = datetime('now', 'localtime')
        WHERE id = ?
    ''', (runtime, task_id))
    conn.commit()
    conn.close()

def get_tasks_to_spawn(task_id: Optional[str] = None) -> List[Dict]:
    """Get tasks that need spawning (assigned, todo, not being worked on)"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get assigned todo tasks
    where_clause = '''
        WHERE t.status = 'todo'
          AND t.assignee_id IS NOT NULL
          AND t.assignee_id != ''
          AND (t.updated_at IS NULL OR t.updated_at < datetime('now', 'localtime', '-2 minutes'))  -- Wait 2 min after assign
    '''
    params = []
    if task_id:
        where_clause += " AND t.id = ?"
        params.append(task_id)

    base_sql = f'''
        SELECT t.id, t.title, t.description, t.assignee_id, t.priority,
               t.prerequisites, t.acceptance_criteria, t.expected_outcome, t.working_dir,
               t.review_feedback, t.review_feedback_at,
               a.name as agent_name, a.role as agent_role
        FROM tasks t
        JOIN agents a ON t.assignee_id = a.id
        {where_clause}
        ORDER BY
            CASE t.priority
                WHEN 'critical' THEN 1
                WHEN 'high' THEN 2
                WHEN 'normal' THEN 3
                WHEN 'low' THEN 4
                ELSE 5
            END,
            t.updated_at ASC
    '''
    cursor.execute(base_sql, params)
    
    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tasks

def was_recently_spawned(task_id: str, minutes: int = 10) -> bool:
    """Check if task was spawned recently"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    # Use string formatting for interval since SQLite doesn't support parameterized intervals
    interval = f'-{minutes} minutes'
    cursor.execute('''
        SELECT 1 FROM task_history 
        WHERE task_id = ? 
        AND action = 'assigned'
        AND timestamp > datetime('now', ?)
        LIMIT 1
    ''', (task_id, interval))
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

def get_busy_agents() -> Dict[str, str]:
    """Return agents that should not receive a new task (active or already assigned)."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, status, current_task_id
        FROM agents
        WHERE status = 'active' OR current_task_id IS NOT NULL
    ''')
    rows = cursor.fetchall()
    conn.close()
    busy = {}
    for agent_id, status, task_id in rows:
        reason = "active" if status == "active" else "has current_task_id"
        if task_id:
            reason = f"{reason}:{task_id}"
        busy[agent_id] = reason
    return busy

def build_task_message(task: Dict, agent_context: Dict) -> str:
    """Build task message with STRICT no-HTML rules"""
    working_dir = task.get('working_dir', '/Users/ngs/clawd')
    base_dir = str(Path(__file__).parent)
    return f"""## 🚨 CRITICAL: NO HTML ALLOWED 🚨

**You are {task['agent_name']} ({task['agent_role']})**
**Task:** {task['id']} - {task['title']}

### 📁 WORKING DIRECTORY (REQUIRED)
**You MUST work in:** `{working_dir}`

**Before doing ANYTHING:**
```bash
cd {working_dir}
```

**NEVER create files outside this directory!**
**NEVER assume the workspace - always use the path above!**

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

### ✅ Prerequisites (must check 1-by-1 BEFORE starting)
{task.get('prerequisites') or 'N/A'}

If prerequisites are a checklist, mark each item:
```bash
python3 {base_dir}/team_db.py task check {task['id']} --field prerequisites --index <n> --done
```
If any prerequisite is NOT met, stop work and send back to todo with clear reason:
```bash
python3 {base_dir}/team_db.py task reject {task['id']} --reason "Prerequisite not met: <reason>"
```

### ✅ Acceptance Criteria (review will require all checked)
{task.get('acceptance_criteria') or 'N/A'}

### 📌 Last Review Feedback (if any)
{task.get('review_feedback') or 'N/A'}

**Feedback Time:** {task.get('review_feedback_at') or 'N/A'}

### 📝 MANDATORY MEMORY UPDATES (ทุก 30 นาที)

**ต้องอัพเดต working memory ทุก 30 นาที:**
```bash
python3 {base_dir}/agent_memory_writer.py working {task['assignee_id']} \
  --task {task['id']} \
  --notes "สิ่งที่กำลังทำตอนนี้" \
  --blockers "ติดปัญหาอะไร (ถ้ามี)" \
  --next "จะทำอะไรต่อไป"
```

**ก่อนจบงาน ต้อง add learning:**
```bash
python3 {base_dir}/agent_memory_writer.py learn {task['assignee_id']} \
  "สิ่งที่เรียนรู้จากงานนี้"
```

### 📋 Instructions
1. Start: `python3 {base_dir}/team_db.py task start {task['id']}`
2. **อัพเดต working memory ทุก 30 นาที** (บังคับ)
3. Update progress: `python3 {base_dir}/team_db.py task progress {task['id']} \u003cpct\u003e`
4. **Add learning ก่อนจบ** (บังคับ)
5. Done: `python3 {base_dir}/team_db.py task done {task['id']}`

**⚠️ ถ้าไม่อัพเดต memory งานจะไม่ผ่าน review!**

### 📢 MANDATORY: รายงานผลกลับเข้าระบบ

**ใช้ `agent_reporter.py` เท่านั้น เพื่อให้ฐานข้อมูลอัปเดตจริง:**

```bash
# รายงานความคืบหน้า
python3 {base_dir}/agent_reporter.py progress --agent {task['assignee_id']} \
  --task {task['id']} --progress <pct> --message "สรุปความคืบหน้า"

# รายงานเสร็จงาน
python3 {base_dir}/agent_reporter.py complete --agent {task['assignee_id']} \
  --task {task['id']} --message "สรุปผลลัพธ์"
```
"""

def log_spawn(task_id: str, agent_id: str):
    """Log that task was spawned and update agent status"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Check current task status to avoid clobbering fast-completing agents
    cursor.execute('SELECT status FROM tasks WHERE id = ?', (task_id,))
    row = cursor.fetchone()
    task_status = row[0] if row else None

    # Get old status for audit
    cursor.execute('SELECT status FROM agents WHERE id = ?', (agent_id,))
    row = cursor.fetchone()
    old_status = row[0] if row else 'unknown'
    
    # Log to history
    cursor.execute('''
        INSERT INTO task_history (task_id, agent_id, action, notes)
        VALUES (?, ?, 'assigned', 'Subagent spawned via spawn_manager')
    ''', (task_id, agent_id))
    
    # Update only if task is still todo (prevents overwriting fast completions)
    if task_status == 'todo':
        cursor.execute('''
            UPDATE agents 
            SET status = 'active', 
                current_task_id = ?,
                last_heartbeat = datetime('now', 'localtime')
            WHERE id = ?
        ''', (task_id, agent_id))
    
    conn.commit()
    conn.close()
    
    # Audit log
    audit.log_status_change(agent_id, old_status, 'active', 'Task spawned (waiting for explicit start)')

def spawn_subagent(task: Dict, task_message: str) -> bool:
    """Run agent via configured runtime (detached)."""
    import time
    
    label = f"{task['assignee_id']}-{task['id']}"
    agent_id = task['assignee_id']
    task_id = task['id']
    working_dir = task.get('working_dir', '/Users/ngs/clawd')
    
    try:
        runtime = get_runtime()
        print(f"    📤 Sending task to {runtime} agent (detached): {agent_id} ...")

        log_dir = Path(__file__).parent / "logs"
        log_dir.mkdir(exist_ok=True)
        log_path = log_dir / f"spawn_{task_id}_{int(time.time())}.log"

        ok, details = spawn_agent(
            agent_id=agent_id,
            task_id=task_id,
            working_dir=working_dir,
            message=task_message,
            log_path=log_path,
            timeout_seconds=3600,
            label=label,
        )
        if not ok:
            error_msg = details
            print(f"    ❌ Failed to start agent: {details}")
            audit.log_spawn(agent_id, task_id, False, error=error_msg)
            return False

        print(f"    ✅ Agent run started (log: {details})")
        audit.log_spawn(agent_id, task_id, True, f"pending:{label}")
        return True
        
    except Exception as e:
        error_msg = str(e)
        print(f"    ❌ Spawn request error: {error_msg}")
        audit.log_spawn(agent_id, task_id, False, error=error_msg)
        return False

def main():
    import argparse
    parser = argparse.ArgumentParser(description='AI Team Spawn Manager (FIXED)')
    parser.add_argument('--task', help='Spawn only a specific task ID')
    args = parser.parse_args()

    print(f"🤖 AI Team Spawn Manager (FIXED) - {datetime.now()}")
    print("=" * 60)
    
    runtime = get_runtime()
    # Get active sessions to avoid duplicates (runtime-dependent)
    active_agents = get_active_sessions()
    if runtime == "openclaw":
        print(f"Runtime: {runtime} | Active agent sessions: {len(active_agents)}")
    else:
        print(f"Runtime: {runtime} | Session query not available (using DB busy-state only)")
    busy_agents = get_busy_agents()
    if busy_agents:
        print(f"Busy agents (DB): {len(busy_agents)}")
    
    # Get tasks to spawn
    tasks = get_tasks_to_spawn(args.task)
    print(f"Assigned todo tasks: {len(tasks)}")
    
    spawned = []
    skipped = []
    
    for task in tasks:
        task_id = task['id']
        working_dir = task.get('working_dir')
        
        # Check 1: Has working directory?
        if not working_dir:
            print(f"⏭️  {task_id}: No working_dir specified, skipping")
            skipped.append((task_id, "no working_dir"))
            continue
        
        # Check 2: Working directory exists?
        if not os.path.isdir(working_dir):
            print(f"⏭️  {task_id}: Working dir does not exist: {working_dir}")
            skipped.append((task_id, f"invalid working_dir: {working_dir}"))
            continue
        
        # Check 3: Agent already has an active session?
        if task['assignee_id'] in active_agents:
            print(f"⏭️  {task_id}: Agent already has active session, skipping")
            skipped.append((task_id, "agent active session exists"))
            continue

        # Check 4: Agent already marked busy in DB?
        if task['assignee_id'] in busy_agents:
            reason = busy_agents[task['assignee_id']]
            print(f"⏭️  {task_id}: Agent already busy in DB ({reason}), skipping")
            skipped.append((task_id, f"agent busy: {reason}"))
            continue
        
        # Check 5: Spawned recently?
        if was_recently_spawned(task_id):
            print(f"⏭️  {task_id}: Spawned recently, skipping")
            skipped.append((task_id, "spawned recently"))
            continue
        
        # Spawn
        print(f"🚀 {task_id}: Spawning {task['agent_name']}")
        
        agent_ctx = get_agent_context(task['assignee_id'])
        task_message = build_task_message(task, agent_ctx)
        
        # Actually spawn the subagent
        spawn_success = spawn_subagent(task, task_message)
        
        if spawn_success:
            update_task_runtime(task_id, runtime)
            log_spawn(task_id, task['assignee_id'])
            busy_agents[task['assignee_id']] = f"active:{task_id}"
            spawned.append({
                'task_id': task_id,
                'agent': task['agent_name'],
                'message': task_message
            })
        else:
            print(f"    ⚠️  Spawn failed for {task_id}, not updating database")
            skipped.append((task_id, "spawn failed"))
    
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
