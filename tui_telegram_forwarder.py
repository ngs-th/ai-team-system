#!/usr/bin/env python3
"""
TUI to Telegram Forwarder - Enhanced Version
Monitors for agent messages and forwards to Telegram
"""

import os
import sqlite3
import subprocess
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "team.db"
LAST_CHECK_FILE = Path(__file__).parent / ".last_tui_forward"
TELEGRAM_CHAT_ID = "1268858185"

def get_last_check():
    """Get timestamp of last check"""
    if LAST_CHECK_FILE.exists():
        try:
            return datetime.fromtimestamp(float(LAST_CHECK_FILE.read_text()))
        except:
            pass
    return datetime.now() - timedelta(minutes=2)

def save_last_check():
    """Save current timestamp"""
    LAST_CHECK_FILE.write_text(str(datetime.now().timestamp()))

def forward_to_telegram(message, prefix="Agent"):
    """Forward message to Telegram"""
    try:
        result = subprocess.run(
            ['openclaw', 'message', 'send',
             '--channel', 'telegram',
             '-t', TELEGRAM_CHAT_ID,
             '-m', f"[{prefix}] {message}"],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0
    except Exception as e:
        print(f"[Error] Failed to forward: {e}")
        return False

def check_session_transcripts():
    """Check session transcript files for agent messages"""
    import glob
    
    forwarded = 0
    transcript_dir = Path.home() / ".openclaw" / "agents" / "main" / "sessions"
    
    if not transcript_dir.exists():
        return forwarded
    
    # Get last check time
    last_check = get_last_check()
    
    # Look for recent transcript files
    for transcript_file in transcript_dir.glob("*.jsonl"):
        try:
            # Check file modification time
            mtime = datetime.fromtimestamp(transcript_file.stat().st_mtime)
            if mtime < last_check:
                continue
            
            # Read last few lines
            with open(transcript_file, 'r') as f:
                lines = f.readlines()
            
            for line in lines[-10:]:  # Check last 10 lines
                try:
                    data = json.loads(line.strip())
                    # Look for assistant messages (agent responses)
                    if data.get('role') == 'assistant':
                        content = data.get('content', '')
                        # Filter for agent reports
                        if any(keyword in content for keyword in ['Task', 'Completed', 'Progress', 'Agent:', '✅', '🚀']):
                            if len(content) > 50:  # Only substantial messages
                                if forward_to_telegram(content[:800], "Agent:Report"):
                                    forwarded += 1
                except:
                    continue
                    
        except Exception as e:
            print(f"[Warning] Error reading {transcript_file}: {e}")
            continue
    
    return forwarded

def check_agent_reports():
    """Check for agent completion reports in working_memory and forward"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    forwarded = 0
    
    # First check session transcripts for direct agent messages
    forwarded += check_session_transcripts()
    
    # Check working_memory for completion notes
    cursor.execute('''
        SELECT agent_id, current_task_id, working_notes, blockers, next_steps, last_updated
        FROM agent_working_memory
        WHERE last_updated > datetime('now', '-5 minutes')
          AND (working_notes LIKE '%completed%' 
               OR working_notes LIKE '%done%'
               OR working_notes LIKE '%finished%'
               OR blockers != ''
               OR next_steps LIKE '%completed%')
        ORDER BY last_updated DESC
    ''')
    
    for row in cursor.fetchall():
        # Only forward if there's actual content
        if row['working_notes'] and len(row['working_notes']) > 20:
            message = f"Task {row['current_task_id']} Update:\n{row['working_notes'][:500]}"
            if forward_to_telegram(message, f"Agent:{row['agent_id']}"):
                forwarded += 1
                print(f"  ✅ Forwarded working memory from {row['agent_id']}")
    
    # Check task_history for completed tasks
    cursor.execute('''
        SELECT th.task_id, th.agent_id, th.action, th.timestamp, th.notes,
               t.title as task_title
        FROM task_history th
        LEFT JOIN tasks t ON th.task_id = t.id
        WHERE th.timestamp > datetime('now', '-5 minutes')
          AND th.action IN ('completed', 'blocked', 'started')
        ORDER BY th.timestamp DESC
    ''')
    
    for row in cursor.fetchall():
        if row['action'] == 'completed':
            emoji = "✅"
        elif row['action'] == 'blocked':
            emoji = "🚫"
        else:
            emoji = "🚀"
        
        message = f"{emoji} Task {row['task_id']} {row['action']}"
        if row['notes']:
            message += f"\n{row['notes'][:300]}"
        
        if forward_to_telegram(message, f"Agent:{row['agent_id']}"):
            forwarded += 1
            print(f"  ✅ Forwarded {row['action']} from {row['agent_id']}")
    
    # Check audit log for spawn/complete events
    cursor.execute('''
        SELECT event_type, agent_id, task_id, timestamp, details
        FROM audit_log
        WHERE timestamp > datetime('now', '-5 minutes')
          AND event_type IN ('AGENT_SPAWN', 'TASK_COMPLETE', 'AGENT_COMPLETE', 'STATUS_CHANGE')
        ORDER BY timestamp DESC
    ''')
    
    for row in cursor.fetchall():
        if row['event_type'] == 'AGENT_SPAWN':
            message = f"🚀 Started working on task {row['task_id']}"
        elif row['event_type'] in ('TASK_COMPLETE', 'AGENT_COMPLETE'):
            message = f"✅ Finished task {row['task_id']}"
            if row['details']:
                message += f"\n{row['details'][:300]}"
        else:
            continue  # Skip STATUS_CHANGE without details
            
        if forward_to_telegram(message, f"System:{row['agent_id'] or 'AI-Team'}"):
            forwarded += 1
            print(f"  ✅ Forwarded {row['event_type']}")
    
    # NEW: Check for session messages from agents (via sessions_send pattern)
    # This looks for recent agent activity in the database that indicates progress
    cursor.execute('''
        SELECT id, title, status, assignee_id, progress, updated_at, description
        FROM tasks
        WHERE updated_at > datetime('now', '-5 minutes')
          AND status IN ('in_progress', 'review', 'done')
        ORDER BY updated_at DESC
        LIMIT 10
    ''')
    
    for row in cursor.fetchall():
        # Only notify on significant progress or status changes
        if row['status'] == 'done':
            message = f"✅ Task Completed: {row['id']}\n{row['title'][:100]}"
            if row['description']:
                message += f"\n{str(row['description'])[:200]}"
            if forward_to_telegram(message, f"Agent:{row['assignee_id'] or 'AI-Team'}"):
                forwarded += 1
        elif row['progress'] and row['progress'] >= 50:
            message = f"🔄 Task Progress: {row['id']} ({row['progress']}%)\n{row['title'][:100]}"
            if forward_to_telegram(message, f"Agent:{row['assignee_id'] or 'AI-Team'}"):
                forwarded += 1
    
    conn.close()
    save_last_check()
    
    return forwarded

def main():
    print(f"🔁 TUI→Telegram Forwarder (Enhanced) - {datetime.now()}")
    
    forwarded = check_agent_reports()
    
    if forwarded > 0:
        print(f"✅ Forwarded {forwarded} messages to Telegram")
    else:
        print("📭 No new agent messages to forward")

if __name__ == "__main__":
    main()
