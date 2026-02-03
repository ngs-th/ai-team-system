#!/usr/bin/env python3
"""
AI Team Retry Queue
Queue failed operations for retry with exponential backoff
"""

import sqlite3
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "team.db"

class RetryQueue:
    """Manage retry queue for failed operations"""
    
    def __init__(self):
        self.db_path = DB_PATH
        self.init_table()
    
    def init_table(self):
        """Create retry queue table if not exists"""
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS retry_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation TEXT NOT NULL,
                payload TEXT NOT NULL,
                retry_count INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 3,
                next_retry_at DATETIME,
                last_error TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending'
            )
        ''')
        conn.commit()
        conn.close()
    
    def add(self, operation: str, payload: dict, max_retries: int = 3):
        """Add operation to retry queue"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        next_retry_at = datetime.now() + timedelta(minutes=5)  # First retry in 5 min
        
        cursor.execute('''
            INSERT INTO retry_queue (operation, payload, max_retries, next_retry_at)
            VALUES (?, ?, ?, ?)
        ''', (operation, json.dumps(payload), max_retries, next_retry_at))
        
        conn.commit()
        queue_id = cursor.lastrowid
        conn.close()
        
        print(f"✅ Added to retry queue: {operation} (ID: {queue_id})")
        return queue_id
    
    def get_pending(self):
        """Get all pending items ready for retry"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, operation, payload, retry_count, max_retries
            FROM retry_queue
            WHERE status = 'pending'
            AND next_retry_at <= datetime('now')
            ORDER BY created_at ASC
        ''')
        
        items = cursor.fetchall()
        conn.close()
        return items
    
    def mark_success(self, queue_id: int):
        """Mark item as successfully processed"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE retry_queue 
            SET status = 'completed'
            WHERE id = ?
        ''', (queue_id,))
        
        conn.commit()
        conn.close()
        print(f"✅ Retry succeeded: {queue_id}")
    
    def mark_failed(self, queue_id: int, error: str):
        """Mark item as failed, schedule next retry"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Exponential backoff: 5min, 10min, 20min
        cursor.execute('''
            UPDATE retry_queue 
            SET retry_count = retry_count + 1,
                last_error = ?,
                next_retry_at = datetime('now', '+' || (5 * (retry_count + 1)) || ' minutes'),
                status = CASE 
                    WHEN retry_count + 1 >= max_retries THEN 'failed'
                    ELSE 'pending'
                END
            WHERE id = ?
        ''', (error, queue_id))
        
        conn.commit()
        conn.close()
        print(f"⚠️  Retry failed: {queue_id} - {error}")
    
    def process_queue(self):
        """Process all pending items"""
        items = self.get_pending()
        
        if not items:
            print("✅ No pending retry items")
            return 0
        
        print(f"🔄 Processing {len(items)} retry items...")
        
        processed = 0
        for item in items:
            queue_id, operation, payload_json, retry_count, max_retries = item
            payload = json.loads(payload_json)
            
            print(f"  Processing {operation} (retry {retry_count + 1}/{max_retries})")
            
            try:
                if operation == 'spawn':
                    success = self.retry_spawn(payload)
                elif operation == 'report':
                    success = self.retry_report(payload)
                else:
                    print(f"    ❌ Unknown operation: {operation}")
                    continue
                
                if success:
                    self.mark_success(queue_id)
                    processed += 1
                else:
                    self.mark_failed(queue_id, "Operation returned false")
                    
            except Exception as e:
                self.mark_failed(queue_id, str(e))
        
        return processed
    
    def retry_spawn(self, payload: dict) -> bool:
        """Retry spawn operation"""
        import subprocess
        import json as json_lib
        
        try:
            result = subprocess.run(
                ['curl', '-s', '-X', 'POST',
                 'http://localhost:3000/api/sessions/spawn',
                 '-H', 'Content-Type: application/json',
                 '-d', json_lib.dumps(payload)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                response = json_lib.loads(result.stdout)
                return 'childSessionKey' in response
            return False
        except Exception as e:
            print(f"    Spawn retry failed: {e}")
            return False
    
    def retry_report(self, payload: dict) -> bool:
        """Retry report operation"""
        try:
            # Import here to avoid circular dependency
            from agent_reporter import report_status, report_progress, report_complete
            
            action = payload.get('action')
            if action == 'status':
                report_status(payload['agent'], payload['status'], payload.get('message', ''))
            elif action == 'progress':
                report_progress(payload['task'], payload['progress'], payload.get('message', ''))
            elif action == 'complete':
                report_complete(payload['agent'], payload['task'], payload.get('message', ''))
            
            return True
        except Exception as e:
            print(f"    Report retry failed: {e}")
            return False
    
    def get_stats(self):
        """Get queue statistics"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT status, COUNT(*) 
            FROM retry_queue 
            GROUP BY status
        ''')
        
        stats = dict(cursor.fetchall())
        conn.close()
        return stats

def main():
    import argparse
    parser = argparse.ArgumentParser(description='AI Team Retry Queue')
    parser.add_argument('--process', action='store_true', help='Process retry queue')
    parser.add_argument('--stats', action='store_true', help='Show queue stats')
    
    args = parser.parse_args()
    
    queue = RetryQueue()
    
    if args.stats:
        stats = queue.get_stats()
        print("Retry Queue Stats:")
        for status, count in stats.items():
            print(f"  {status}: {count}")
    else:
        queue.process_queue()

if __name__ == '__main__':
    main()
