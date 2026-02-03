#!/usr/bin/env python3
"""
Notification Manager for AI Team
Handles Telegram notifications with configurable levels
QA Engineer: Quinn
"""

import os
import sqlite3
import subprocess
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
from enum import Enum

# Set timezone to Bangkok (+7)
os.environ['TZ'] = 'Asia/Bangkok'

TELEGRAM_CHANNEL = "1268858185"


class NotificationLevel(Enum):
    """Notification level enumeration"""
    MINIMAL = "minimal"    # Only block and complete
    NORMAL = "normal"      # Assign, complete, block, start
    VERBOSE = "verbose"    # All events including review


class NotificationEvent(Enum):
    """Notification event types"""
    ASSIGN = "assign"
    COMPLETE = "complete"
    BLOCK = "block"
    UNBLOCK = "unblock"
    START = "start"
    REVIEW = "review"
    BACKLOG = "backlog"
    CREATE = "create"
    PROGRESS = "progress"
    ERROR = "error"
    MILESTONE = "milestone"
    AUTO_STOP = "auto_stop"


import re

class NotificationManager:
    """
    Manages Telegram notifications for task events
    Supports configurable notification levels
    """
    
    @staticmethod
    def strip_html(text: str) -> str:
        """Strip HTML tags from text"""
        if not text:
            return ""
        # Remove HTML tags
        clean = re.sub(r'<[^>]+>', '', text)
        # Replace HTML entities
        clean = clean.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        return clean.strip()
    
    # Event mapping per level
    LEVEL_EVENTS = {
        NotificationLevel.MINIMAL: {
            NotificationEvent.BLOCK,
            NotificationEvent.COMPLETE,
            NotificationEvent.ERROR,
            NotificationEvent.AUTO_STOP,
        },
        NotificationLevel.NORMAL: {
            NotificationEvent.ASSIGN,
            NotificationEvent.COMPLETE,
            NotificationEvent.BLOCK,
            NotificationEvent.START,
            NotificationEvent.UNBLOCK,
            NotificationEvent.ERROR,
            NotificationEvent.MILESTONE,
            NotificationEvent.AUTO_STOP,
        },
        NotificationLevel.VERBOSE: {
            NotificationEvent.ASSIGN,
            NotificationEvent.COMPLETE,
            NotificationEvent.BLOCK,
            NotificationEvent.START,
            NotificationEvent.REVIEW,
            NotificationEvent.UNBLOCK,
            NotificationEvent.BACKLOG,
            NotificationEvent.CREATE,
            NotificationEvent.ERROR,
            NotificationEvent.MILESTONE,
            NotificationEvent.PROGRESS,
            NotificationEvent.AUTO_STOP,
        }
    }
    
    # Emoji mapping for events
    EVENT_EMOJI = {
        NotificationEvent.ASSIGN: "📋",
        NotificationEvent.COMPLETE: "✅",
        NotificationEvent.BLOCK: "🚫",
        NotificationEvent.UNBLOCK: "🔄",
        NotificationEvent.START: "🚀",
        NotificationEvent.REVIEW: "👀",
        NotificationEvent.BACKLOG: "📋",
        NotificationEvent.CREATE: "🆕",
        NotificationEvent.PROGRESS: "📊",
        NotificationEvent.ERROR: "❌",
        NotificationEvent.MILESTONE: "🏁",
        NotificationEvent.AUTO_STOP: "🛑",
    }
    
    def __init__(self, db_path: Path, telegram_channel: str = TELEGRAM_CHANNEL):
        self.db_path = db_path
        self.telegram_channel = telegram_channel
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self._ensure_schema()
        
    def close(self):
        """Close database connection"""
        self.conn.close()
        
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        self.close()
        
    def _ensure_schema(self):
        """Ensure notification tables exist"""
        cursor = self.conn.cursor()
        
        # Notification settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notification_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                level TEXT NOT NULL DEFAULT 'normal' CHECK (level IN ('minimal', 'normal', 'verbose')),
                notify_on_assign BOOLEAN DEFAULT 1,
                notify_on_complete BOOLEAN DEFAULT 1,
                notify_on_block BOOLEAN DEFAULT 1,
                notify_on_start BOOLEAN DEFAULT 1,
                notify_on_review BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(entity_type, entity_id)
            )
        ''')
        
        # Notification log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notification_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT,
                agent_id TEXT,
                event_type TEXT NOT NULL,
                message TEXT NOT NULL,
                level TEXT NOT NULL,
                sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN DEFAULT 0
            )
        ''')
        
        # Add notification_level column to agents if not exists
        cursor.execute("PRAGMA table_info(agents)")
        columns = {row[1] for row in cursor.fetchall()}
        
        if 'notification_level' not in columns:
            cursor.execute('''
                ALTER TABLE agents ADD COLUMN notification_level 
                TEXT DEFAULT 'normal' CHECK (notification_level IN ('minimal', 'normal', 'verbose'))
            ''')
            print("✅ Added notification_level column to agents table")
            
        self.conn.commit()
        
    def get_settings(self, entity_type: str, entity_id: str) -> Dict:
        """Get notification settings for an entity"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT * FROM notification_settings 
            WHERE entity_type = ? AND entity_id = ?
        ''', (entity_type, entity_id))
        
        row = cursor.fetchone()
        if row:
            return dict(row)
        
        # Return default settings
        return {
            'entity_type': entity_type,
            'entity_id': entity_id,
            'level': 'normal',
            'notify_on_assign': 1,
            'notify_on_complete': 1,
            'notify_on_block': 1,
            'notify_on_start': 1,
            'notify_on_review': 0,
        }
        
    def set_settings(self, entity_type: str, entity_id: str, 
                     level: str = None, **kwargs) -> bool:
        """Set notification settings for an entity"""
        cursor = self.conn.cursor()
        
        # Validate level
        if level and level not in ['minimal', 'normal', 'verbose']:
            raise ValueError(f"Invalid level: {level}. Must be minimal, normal, or verbose")
        
        # Build update fields
        fields = []
        values = []
        
        if level:
            fields.append('level = ?')
            values.append(level)
            
        for key, value in kwargs.items():
            if key.startswith('notify_on_'):
                fields.append(f'{key} = ?')
                values.append(1 if value else 0)
                
        if not fields:
            return False
            
        fields.append('updated_at = CURRENT_TIMESTAMP')
        values.extend([entity_type, entity_id])
        
        # Insert or update
        cursor.execute(f'''
            INSERT INTO notification_settings 
            (entity_type, entity_id, level, notify_on_assign, notify_on_complete, 
             notify_on_block, notify_on_start, notify_on_review)
            VALUES (?, ?, COALESCE(?, 'normal'), 
                    COALESCE(?, 1), COALESCE(?, 1), COALESCE(?, 1), COALESCE(?, 1), COALESCE(?, 0))
            ON CONFLICT(entity_type, entity_id) DO UPDATE SET
                {', '.join(fields)}
        ''', (entity_type, entity_id, level,
              kwargs.get('notify_on_assign', 1),
              kwargs.get('notify_on_complete', 1),
              kwargs.get('notify_on_block', 1),
              kwargs.get('notify_on_start', 1),
              kwargs.get('notify_on_review', 0)) + tuple(values))
              
        self.conn.commit()
        return cursor.rowcount > 0
        
    def should_notify(self, event: NotificationEvent, 
                      entity_type: str = 'global', 
                      entity_id: str = 'default') -> bool:
        """Check if notification should be sent based on level"""
        settings = self.get_settings(entity_type, entity_id)
        level = NotificationLevel(settings.get('level', 'normal'))
        
        # Check if event is in the level's allowed events
        allowed_events = self.LEVEL_EVENTS.get(level, set())
        return event in allowed_events
        
    def format_message(self, event: NotificationEvent, 
                       task_id: str, 
                       task_title: str = None,
                       agent_name: str = None,
                       reason: str = None,
                       **kwargs) -> str:
        """Format notification message - Telegram-friendly, no HTML"""
        emoji = self.EVENT_EMOJI.get(event, "📌")
        # Strip any HTML from inputs
        title = self.strip_html(task_title) or f"Task {task_id}"
        agent = self.strip_html(agent_name) or "Unknown"
        reason = self.strip_html(reason) if reason else None
        
        # Clean format for Telegram (no HTML, compact)
        if event == NotificationEvent.ASSIGN:
            return f"{emoji} {task_id} → {agent}\n   {title}"
        elif event == NotificationEvent.COMPLETE:
            return f"{emoji} {task_id} | {agent}\n   {title}"
        elif event == NotificationEvent.BLOCK:
            reason_str = f"\n   🚫 {reason}" if reason else ""
            return f"{emoji} {task_id} BLOCKED{reason_str}\n   {title}"
        elif event == NotificationEvent.UNBLOCK:
            return f"{emoji} {task_id} resumed | {agent}\n   {title}"
        elif event == NotificationEvent.START:
            return f"{emoji} {task_id} started | {agent}\n   {title}"
        elif event == NotificationEvent.REVIEW:
            return f"{emoji} {task_id} → REVIEW\n   {title}"
        elif event == NotificationEvent.BACKLOG:
            reason_str = f"\n   📝 {reason}" if reason else ""
            return f"{emoji} {task_id} → BACKLOG{reason_str}\n   {title}"
        elif event == NotificationEvent.CREATE:
            assignee = kwargs.get('assignee', 'Unassigned')
            return f"{emoji} {task_id} created → {assignee}\n   {title}"
        elif event == NotificationEvent.PROGRESS:
            progress = kwargs.get('progress', 0)
            return f"{emoji} {task_id} {progress}% | {agent}\n   {title}"
        elif event == NotificationEvent.AUTO_STOP:
            fix_loops = kwargs.get('fix_loops', 10)
            return f"{emoji} {task_id} AUTO-STOPPED | {agent}\n   Fix loops: {fix_loops}/10\n   {title}"
        elif event == NotificationEvent.ERROR:
            error_msg = kwargs.get('error', 'Unknown error')
            return f"{emoji} {task_id} ERROR | {agent}\n   {error_msg}"
        elif event == NotificationEvent.MILESTONE:
            milestone = kwargs.get('milestone', 'Milestone reached')
            return f"{emoji} {task_id} | {agent}\n   {milestone}"
        else:
            return f"{emoji} {task_id}: {event.value}\n   {title}"
            
    def send_notification(self, message: str, task_id: str = None, 
                          agent_id: str = None, event_type: str = None,
                          level: str = 'normal') -> bool:
        """Send notification to Telegram and log it"""
        # Strip any HTML from message
        message = self.strip_html(message)
        success = False
        
        try:
            # Send via openclaw
            result = subprocess.run(
                ["openclaw", "message", "send", "--channel", "telegram",
                 "--target", self.telegram_channel, "--message", message],
                capture_output=True,
                text=True,
                timeout=30
            )
            success = result.returncode == 0
            
            if not success:
                print(f"[Notification Error] {result.stderr}")
                
        except Exception as e:
            print(f"[Notification Error] Failed to send Telegram message: {e}")
            
        # Log the notification
        self._log_notification(task_id, agent_id, event_type, message, level, success)
        
        return success
        
    def _log_notification(self, task_id: str, agent_id: str, 
                          event_type: str, message: str, 
                          level: str, success: bool):
        """Log notification to database"""
        cursor = self.conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO notification_log 
                (task_id, agent_id, event_type, message, level, success)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (task_id, agent_id, event_type, message, level, 1 if success else 0))
            
            self.conn.commit()
        except Exception as e:
            print(f"[Notification Log Error] {e}")
            
    def notify(self, event: NotificationEvent,
               task_id: str,
               task_title: str = None,
               agent_id: str = None,
               agent_name: str = None,
               entity_type: str = 'global',
               entity_id: str = 'default',
               **kwargs) -> bool:
        """
        Main notification method - checks level and sends if appropriate
        
        Args:
            event: Type of notification event
            task_id: Task identifier
            task_title: Task title
            agent_id: Agent identifier
            agent_name: Agent display name
            entity_type: 'global', 'agent', or 'project'
            entity_id: Entity identifier for settings lookup
            **kwargs: Additional event-specific data
        """
        # Check if we should notify
        if not self.should_notify(event, entity_type, entity_id):
            return False
            
        # Get settings to determine level
        settings = self.get_settings(entity_type, entity_id)
        level = settings.get('level', 'normal')
        
        # Format message
        message = self.format_message(
            event, task_id, task_title, agent_name, 
            reason=kwargs.get('reason'), **{k: v for k, v in kwargs.items() if k != 'reason'}
        )
        
        # Send notification
        return self.send_notification(
            message, task_id, agent_id, event.value, level
        )
        
    def get_notification_log(self, task_id: str = None, 
                             limit: int = 50) -> List[Dict]:
        """Get notification log entries"""
        cursor = self.conn.cursor()
        
        if task_id:
            cursor.execute('''
                SELECT * FROM notification_log 
                WHERE task_id = ?
                ORDER BY sent_at DESC
                LIMIT ?
            ''', (task_id, limit))
        else:
            cursor.execute('''
                SELECT * FROM notification_log 
                ORDER BY sent_at DESC
                LIMIT ?
            ''', (limit,))
            
        return [dict(row) for row in cursor.fetchall()]
        
    def get_agent_level(self, agent_id: str) -> str:
        """Get notification level for an agent"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT notification_level FROM agents WHERE id = ?
        ''', (agent_id,))
        
        row = cursor.fetchone()
        if row and row[0]:
            return row[0]
        return 'normal'
        
    def set_agent_level(self, agent_id: str, level: str) -> bool:
        """Set notification level for an agent"""
        if level not in ['minimal', 'normal', 'verbose']:
            raise ValueError(f"Invalid level: {level}")
            
        cursor = self.conn.cursor()
        
        cursor.execute('''
            UPDATE agents 
            SET notification_level = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (level, agent_id))
        
        self.conn.commit()
        return cursor.rowcount > 0


class ProgressNotifier:
    """
    Lightweight progress notifier for agents during task execution
    Designed for minimal performance impact - notifications are fire-and-forget
    """
    
    def __init__(self, db_path: Path, task_id: str, agent_id: str, 
                 task_title: str = None, agent_name: str = None):
        self.db_path = db_path
        self.task_id = task_id
        self.agent_id = agent_id
        self.task_title = task_title or task_id
        self.agent_name = agent_name or agent_id
        self._last_progress = 0
        self._last_milestone = None
        
    def _get_manager(self) -> NotificationManager:
        """Get notification manager instance"""
        return NotificationManager(self.db_path)
        
    def report_progress(self, progress: int, message: str = None) -> bool:
        """
        Report task progress (0-100)
        Only sends notification if level allows PROGRESS events
        """
        progress = max(0, min(100, progress))
        
        # Skip if progress hasn't changed significantly (for minimal spam)
        if abs(progress - self._last_progress) < 5 and progress not in [0, 50, 100]:
            return False
            
        self._last_progress = progress
        
        with self._get_manager() as nm:
            return nm.notify(
                event=NotificationEvent.PROGRESS,
                task_id=self.task_id,
                task_title=self.task_title,
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                entity_type='agent',
                entity_id=self.agent_id,
                progress=progress
            )
    
    def report_milestone(self, milestone: str) -> bool:
        """
        Report a milestone achievement
        Sent at NORMAL level and above
        """
        # Skip duplicate milestones
        if milestone == self._last_milestone:
            return False
        self._last_milestone = milestone
        
        with self._get_manager() as nm:
            return nm.notify(
                event=NotificationEvent.MILESTONE,
                task_id=self.task_id,
                task_title=self.task_title,
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                entity_type='agent',
                entity_id=self.agent_id,
                milestone=milestone
            )
    
    def report_error(self, error: str, fatal: bool = False) -> bool:
        """
        Report an error during task execution
        Errors are sent at ALL levels (minimal and above)
        """
        with self._get_manager() as nm:
            success = nm.notify(
                event=NotificationEvent.ERROR,
                task_id=self.task_id,
                task_title=self.task_title,
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                entity_type='agent',
                entity_id=self.agent_id,
                error=error
            )
            
            # If fatal, also trigger block notification
            if fatal:
                nm.notify(
                    event=NotificationEvent.BLOCK,
                    task_id=self.task_id,
                    task_title=self.task_title,
                    agent_id=self.agent_id,
                    agent_name=self.agent_name,
                    reason=f"Fatal error: {error}"
                )
            
            return success
    
    def report_completion(self, summary: str = None) -> bool:
        """
        Report task completion
        Sent at ALL levels
        """
        with self._get_manager() as nm:
            return nm.notify(
                event=NotificationEvent.COMPLETE,
                task_id=self.task_id,
                task_title=self.task_title,
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                entity_type='agent',
                entity_id=self.agent_id
            )
    
    @staticmethod
    def quick_progress(db_path: Path, task_id: str, agent_id: str, 
                       progress: int, task_title: str = None) -> bool:
        """
        Static method for quick progress updates without creating an instance
        Minimal overhead - single notification, no state tracking
        """
        progress = max(0, min(100, progress))
        
        with NotificationManager(db_path) as nm:
            return nm.notify(
                event=NotificationEvent.PROGRESS,
                task_id=task_id,
                task_title=task_title or task_id,
                agent_id=agent_id,
                agent_name=agent_id,
                entity_type='agent',
                entity_id=agent_id,
                progress=progress
            )


# Legacy compatibility function
def send_telegram_notification(message: str) -> bool:
    """Legacy function for simple notifications"""
    # Strip HTML tags
    message = re.sub(r'<[^>]+>', '', message)
    message = message.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
    
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
        print(f"[Notification Error] Failed to send Telegram message: {e}")
        return False
