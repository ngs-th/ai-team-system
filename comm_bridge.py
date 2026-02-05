#!/usr/bin/env python3
"""
Agent Communication Bridge
Forwards agent messages to Telegram (real-time + digest modes)
"""

import os
import sqlite3
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict
import time

os.environ['TZ'] = 'Asia/Bangkok'
try:
    time.tzset()
except AttributeError:
    pass
DB_PATH = Path(__file__).parent / "team.db"
TELEGRAM_CHANNEL = "1268858185"

class CommunicationBridge:
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

    def get_unread_messages(self, since_minutes: int = 30) -> List[Dict]:
        """Get unread messages from last N minutes"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT ac.*, 
                   a_from.name as from_name,
                   a_to.name as to_name,
                   t.title as task_title
            FROM agent_communications ac
            JOIN agents a_from ON ac.from_agent_id = a_from.id
            LEFT JOIN agents a_to ON ac.to_agent_id = a_to.id
            LEFT JOIN tasks t ON ac.task_id = t.id
            WHERE ac.is_read = FALSE
            AND ac.created_at > datetime('now', '-{} minutes')
            ORDER BY ac.created_at ASC
        '''.format(since_minutes))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_all_recent_messages(self, since_minutes: int = 30) -> List[Dict]:
        """Get all messages from last N minutes (for digest)"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT ac.*, 
                   a_from.name as from_name,
                   a_to.name as to_name,
                   t.title as task_title
            FROM agent_communications ac
            JOIN agents a_from ON ac.from_agent_id = a_from.id
            LEFT JOIN agents a_to ON ac.to_agent_id = a_to.id
            LEFT JOIN tasks t ON ac.task_id = t.id
            WHERE ac.created_at > datetime('now', '-{} minutes')
            ORDER BY ac.created_at ASC
        '''.format(since_minutes))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def send_to_telegram(self, message: str) -> bool:
        """Send message to Telegram"""
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
            print(f"[Bridge Error] {e}")
            return False
    
    def format_message_realtime(self, msg: Dict) -> str:
        """Format single message for real-time notification"""
        from_agent = msg['from_name']
        to_agent = msg['to_name'] or "everyone"
        task = msg['task_title'] or msg['task_id'] or "general"
        message = msg['message']
        
        # Strip HTML
        import re
        message = re.sub(r'<[^>]+>', '', message)
        
        emoji = {
            'comment': '💬',
            'mention': '📢',
            'request': '🙏',
            'response': '✍️'
        }.get(msg['message_type'], '💬')
        
        return f"""{emoji} **Agent Chat**

**{from_agent}** → {to_agent}
Task: {task}

{message}"""
    
    def format_digest(self, messages: List[Dict]) -> str:
        """Format digest of multiple messages"""
        if not messages:
            return ""
        
        lines = ["📬 **Agent Communications Digest**", ""]
        
        for msg in messages:
            from_agent = msg['from_name']
            to_agent = msg['to_name'] or "all"
            task = msg['task_title'] or msg['task_id'] or "general"
            message = msg['message']
            
            # Strip HTML and truncate
            import re
            message = re.sub(r'<[^>]+>', '', message)
            if len(message) > 100:
                message = message[:97] + "..."
            
            emoji = {
                'comment': '💬',
                'mention': '📢',
                'request': '🙏',
                'response': '✍️'
            }.get(msg['message_type'], '💬')
            
            lines.append(f"{emoji} **{from_agent}** → {to_agent}")
            lines.append(f"   Task: {task}")
            lines.append(f"   {message}")
            lines.append("")
        
        return "\n".join(lines)
    
    def mark_as_read(self, message_ids: List[int]):
        """Mark messages as read"""
        cursor = self.conn.cursor()
        for msg_id in message_ids:
            cursor.execute('''
                UPDATE agent_communications 
                SET is_read = TRUE 
                WHERE id = ?
            ''', (msg_id,))
        self.conn.commit()
    
    def run_realtime(self) -> int:
        """Send real-time notifications for unread messages"""
        messages = self.get_unread_messages(since_minutes=5)
        sent_count = 0
        
        for msg in messages:
            formatted = self.format_message_realtime(msg)
            if self.send_to_telegram(formatted):
                sent_count += 1
                self.mark_as_read([msg['id']])
        
        return sent_count
    
    def run_digest(self) -> int:
        """Send digest of recent messages"""
        messages = self.get_all_recent_messages(since_minutes=30)
        
        if not messages:
            return 0
        
        digest = self.format_digest(messages)
        if self.send_to_telegram(digest):
            # Mark all as read
            self.mark_as_read([m['id'] for m in messages])
            return len(messages)
        
        return 0


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Agent Communication Bridge')
    parser.add_argument('--realtime', action='store_true', help='Send real-time notifications')
    parser.add_argument('--digest', action='store_true', help='Send digest (30 min summary)')
    args = parser.parse_args()
    
    with CommunicationBridge() as bridge:
        if args.realtime:
            count = bridge.run_realtime()
            if count > 0:
                print(f"✅ Sent {count} real-time notifications")
        elif args.digest:
            count = bridge.run_digest()
            if count > 0:
                print(f"✅ Sent digest with {count} messages")
            else:
                print("✅ No messages to digest")
        else:
            parser.print_help()


if __name__ == '__main__':
    main()
