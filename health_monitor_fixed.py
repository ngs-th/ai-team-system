#!/usr/bin/env python3
"""
AI Team Health Monitor - FIXED VERSION
Smart alerts: only alert once per issue until resolved
"""

import os
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path

os.environ['TZ'] = 'Asia/Bangkok'
DB_PATH = Path(__file__).parent / "team.db"

class SmartHealthMonitor:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self._ensure_alert_table()
        
    def _ensure_alert_table(self):
        """Track which alerts have been sent"""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alert_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_alert DATETIME DEFAULT CURRENT_TIMESTAMP,
                resolved BOOLEAN DEFAULT FALSE,
                UNIQUE(alert_type, entity_id)
            )
        ''')
        self.conn.commit()
        
    def check_long_running_sessions(self) -> List[Dict]:
        """Find sessions running longer than 3 hours"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 
                a.name as agent_name,
                a.id as agent_id,
                t.id as task_id,
                t.title as task_title,
                t.started_at,
                ROUND((strftime('%s', 'now') - strftime('%s', t.started_at)) / 60.0) as minutes
            FROM tasks t
            JOIN agents a ON t.assignee_id = a.id
            WHERE t.status = 'in_progress'
            AND t.started_at < datetime('now', '-3 hours')
            ORDER BY t.started_at ASC
        ''')
        return [dict(row) for row in cursor.fetchall()]
    
    def should_alert(self, alert_type: str, entity_id: str) -> bool:
        """Check if we should send alert (not already sent for this issue)"""
        cursor = self.conn.cursor()
        
        # Check if alert exists and is unresolved
        cursor.execute('''
            SELECT id, last_alert FROM alert_history
            WHERE alert_type = ? AND entity_id = ? AND resolved = FALSE
        ''', (alert_type, entity_id))
        
        row = cursor.fetchone()
        if row:
            # Alert already sent - update last_seen but don't alert again
            cursor.execute('''
                UPDATE alert_history SET last_alert = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (row[0],))
            self.conn.commit()
            return False  # Don't alert again
        
        # New issue - record it
        cursor.execute('''
            INSERT INTO alert_history (alert_type, entity_id)
            VALUES (?, ?)
        ''', (alert_type, entity_id))
        self.conn.commit()
        return True  # Should alert
    
    def mark_resolved(self, alert_type: str, entity_id: str):
        """Mark alert as resolved"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE alert_history 
            SET resolved = TRUE, last_alert = CURRENT_TIMESTAMP
            WHERE alert_type = ? AND entity_id = ?
        ''', (alert_type, entity_id))
        self.conn.commit()
    
    def cleanup_old_alerts(self, hours: int = 24):
        """Remove resolved alerts older than N hours"""
        cursor = self.conn.cursor()
        cursor.execute(f'''
            DELETE FROM alert_history
            WHERE resolved = TRUE
            AND last_alert < datetime('now', '-{hours} hours')
        ''')
        self.conn.commit()
    
    def run(self) -> Dict:
        """Run health check with smart alerting"""
        print(f"🔍 AI Team Health Check (Smart) - {datetime.now()}")
        
        # Check long-running sessions
        long_running = self.check_long_running_sessions()
        
        alerts_to_send = []
        warnings = 0
        
        for session in long_running:
            entity_id = f"{session['agent_id']}-{session['task_id']}"
            
            if self.should_alert('long_running', entity_id):
                alerts_to_send.append({
                    'agent': session['agent_name'],
                    'task': session['task_id'],
                    'title': session['task_title'],
                    'minutes': session['minutes']
                })
                warnings += 1
        
        # Cleanup old resolved alerts
        self.cleanup_old_alerts()
        
        result = {
            'critical': 0,
            'warnings': warnings,
            'long_running': long_running,
            'alerts_to_send': alerts_to_send
        }
        
        print(f"  Critical: {result['critical']}")
        print(f"  Warnings: {result['warnings']}")
        print(f"  New alerts: {len(alerts_to_send)}")
        
        return result
    
    def format_alert(self, alerts: List[Dict]) -> str:
        """Format alert message for Telegram"""
        if not alerts:
            return ""
        
        lines = ["🟡 AI Team Health Alert", ""]
        
        for alert in alerts:
            hours = alert['minutes'] // 60
            mins = alert['minutes'] % 60
            duration = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
            
            lines.append(f"• {alert['agent']}: {alert['task']}")
            lines.append(f"  ({duration}) - {alert['title'][:40]}...")
        
        lines.append("")
        lines.append(f"Checked: {datetime.now().strftime('%H:%M')}")
        
        return "\n".join(lines)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--smart-alert', action='store_true')
    args = parser.parse_args()
    
    monitor = SmartHealthMonitor()
    result = monitor.run()
    
    if args.smart_alert and result['alerts_to_send']:
        alert_msg = monitor.format_alert(result['alerts_to_send'])
        print(alert_msg)
    
    # Exit code: 0 = healthy, 1 = warnings, 2 = critical
    if result['critical'] > 0:
        exit(2)
    elif result['warnings'] > 0:
        exit(1)
    else:
        exit(0)

if __name__ == '__main__':
    main()
