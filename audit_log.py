#!/usr/bin/env python3
"""
AI Team Audit Log
Log all significant system events for debugging and compliance
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "team.db"
AUDIT_LOG_FILE = Path(__file__).parent / "logs" / "audit.log"

class AuditLogger:
    """Centralized audit logging for AI Team System"""
    
    def __init__(self):
        self.db_path = DB_PATH
        self.log_file = AUDIT_LOG_FILE
        self.log_file.parent.mkdir(exist_ok=True)
        self.init_table()
    
    def init_table(self):
        """Create audit log table if not exists"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                event_type TEXT NOT NULL,
                agent_id TEXT,
                task_id TEXT,
                details TEXT,
                before_state TEXT,
                after_state TEXT,
                ip_address TEXT,
                session_key TEXT
            )
        ''')
        conn.commit()
        conn.close()
    
    def log(self, event_type: str, agent_id: str = None, task_id: str = None,
            details: str = "", before_state: dict = None, after_state: dict = None,
            session_key: str = None):
        """Log an audit event"""
        
        # Log to database with timeout
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO audit_log 
            (event_type, agent_id, task_id, details, before_state, after_state, session_key)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            event_type,
            agent_id,
            task_id,
            details,
            json.dumps(before_state) if before_state else None,
            json.dumps(after_state) if after_state else None,
            session_key
        ))
        
        conn.commit()
        conn.close()
        
        # Also log to file
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] {event_type}"
        if agent_id:
            log_entry += f" | Agent: {agent_id}"
        if task_id:
            log_entry += f" | Task: {task_id}"
        if details:
            log_entry += f" | {details}"
        
        with open(self.log_file, 'a') as f:
            f.write(log_entry + '\n')
    
    def log_spawn(self, agent_id: str, task_id: str, success: bool, session_key: str = None, error: str = None):
        """Log agent spawn event"""
        self.log(
            event_type='AGENT_SPAWN',
            agent_id=agent_id,
            task_id=task_id,
            details=f"Success: {success}" + (f" | Error: {error}" if error else ""),
            after_state={'status': 'active', 'success': success},
            session_key=session_key
        )
    
    def log_status_change(self, agent_id: str, old_status: str, new_status: str, reason: str = ""):
        """Log agent status change"""
        self.log(
            event_type='STATUS_CHANGE',
            agent_id=agent_id,
            details=f"{old_status} → {new_status}" + (f" | {reason}" if reason else ""),
            before_state={'status': old_status},
            after_state={'status': new_status}
        )
    
    def log_task_update(self, task_id: str, agent_id: str, old_status: str, new_status: str, details: str = ""):
        """Log task status update"""
        self.log(
            event_type='TASK_UPDATE',
            agent_id=agent_id,
            task_id=task_id,
            details=f"{old_status} → {new_status}" + (f" | {details}" if details else ""),
            before_state={'status': old_status},
            after_state={'status': new_status}
        )
    
    def log_heartbeat(self, agent_id: str, task_id: str = None):
        """Log agent heartbeat"""
        self.log(
            event_type='HEARTBEAT',
            agent_id=agent_id,
            task_id=task_id
        )
    
    def log_stale_detection(self, agent_id: str, task_id: str, last_heartbeat: str):
        """Log stale agent detection"""
        self.log(
            event_type='STALE_DETECTED',
            agent_id=agent_id,
            task_id=task_id,
            details=f"Last heartbeat: {last_heartbeat}"
        )
    
    def log_retry(self, operation: str, queue_id: int, retry_count: int, success: bool):
        """Log retry operation"""
        self.log(
            event_type='RETRY_ATTEMPT',
            details=f"Operation: {operation}, Queue ID: {queue_id}, Attempt: {retry_count}, Success: {success}"
        )
    
    def get_recent_events(self, limit: int = 50):
        """Get recent audit events"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT timestamp, event_type, agent_id, task_id, details
            FROM audit_log
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        events = cursor.fetchall()
        conn.close()
        return events
    
    def get_agent_activity(self, agent_id: str, limit: int = 20):
        """Get activity for specific agent"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT timestamp, event_type, task_id, details
            FROM audit_log
            WHERE agent_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (agent_id, limit))
        
        events = cursor.fetchall()
        conn.close()
        return events

def main():
    import argparse
    parser = argparse.ArgumentParser(description='AI Team Audit Log')
    parser.add_argument('--recent', type=int, help='Show recent events')
    parser.add_argument('--agent', help='Show activity for specific agent')
    
    args = parser.parse_args()
    
    logger = AuditLogger()
    
    if args.agent:
        events = logger.get_agent_activity(args.agent, args.recent or 20)
        print(f"Activity for {args.agent}:")
        for event in events:
            print(f"  {event[0]} | {event[1]} | Task: {event[2]} | {event[3]}")
    elif args.recent:
        events = logger.get_recent_events(args.recent)
        print("Recent events:")
        for event in events:
            print(f"  {event[0]} | {event[1]} | Agent: {event[2]} | Task: {event[3]}")
    else:
        print("Usage:")
        print("  audit_log.py --recent 20")
        print("  audit_log.py --agent pm --recent 10")

if __name__ == '__main__':
    main()
