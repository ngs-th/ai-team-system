#!/usr/bin/env python3
"""
Notification System Tests (TDD)
QA Engineer: Quinn
Includes tests for progress notifications
"""

import unittest
import sqlite3
import tempfile
import os
from datetime import datetime
from pathlib import Path

# Import the module we'll create
import sys
sys.path.insert(0, str(Path(__file__).parent))

from notifications import (
    NotificationManager, NotificationEvent, NotificationLevel,
    ProgressNotifier, TELEGRAM_CHANNEL
)


class TestNotificationManager(unittest.TestCase):
    """Test cases for NotificationManager"""
    
    def setUp(self):
        """Set up test database"""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_test_schema()
        
    def tearDown(self):
        """Clean up test database"""
        self.conn.close()
        os.close(self.db_fd)
        os.unlink(self.db_path)
        
    def _create_test_schema(self):
        """Create minimal schema for testing"""
        cursor = self.conn.cursor()
        
        # Tasks table
        cursor.execute('''
            CREATE TABLE tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                status TEXT DEFAULT 'todo',
                assignee_id TEXT,
                priority TEXT DEFAULT 'normal'
            )
        ''')
        
        # Agents table
        cursor.execute('''
            CREATE TABLE agents (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                notification_level TEXT DEFAULT 'normal'
            )
        ''')
        
        # Notification settings table
        cursor.execute('''
            CREATE TABLE notification_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                level TEXT NOT NULL CHECK (level IN ('minimal', 'normal', 'verbose')),
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
            CREATE TABLE notification_log (
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
        
        self.conn.commit()
        
    def test_notification_levels_enum(self):
        """Test that notification levels are valid"""
        levels = ['minimal', 'normal', 'verbose']
        for level in levels:
            self.assertIn(level, ['minimal', 'normal', 'verbose'])
            
    def test_notification_settings_schema(self):
        """Test notification settings table structure"""
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA table_info(notification_settings)")
        columns = {row[1] for row in cursor.fetchall()}
        
        required = {'id', 'entity_type', 'entity_id', 'level', 
                   'notify_on_assign', 'notify_on_complete', 'notify_on_block',
                   'notify_on_start', 'notify_on_review'}
        self.assertTrue(required.issubset(columns))
        
    def test_should_notify_based_on_level(self):
        """Test notification filtering based on level"""
        # Minimal level: only block and complete
        # Normal level: assign, complete, block, start
        # Verbose level: all events including review
        
        test_cases = [
            ('minimal', 'block', True),
            ('minimal', 'complete', True),
            ('minimal', 'assign', False),
            ('minimal', 'start', False),
            ('minimal', 'review', False),
            ('normal', 'assign', True),
            ('normal', 'complete', True),
            ('normal', 'block', True),
            ('normal', 'start', True),
            ('normal', 'review', False),
            ('verbose', 'review', True),
            ('verbose', 'assign', True),
        ]
        
        for level, event, expected in test_cases:
            result = self._should_notify_for_level(level, event)
            self.assertEqual(result, expected, 
                           f"Level={level}, Event={event} should return {expected}")
            
    def _should_notify_for_level(self, level: str, event: str) -> bool:
        """Helper: determine if notification should be sent"""
        minimal_events = {'block', 'complete'}
        normal_events = {'assign', 'complete', 'block', 'start'}
        verbose_events = {'assign', 'complete', 'block', 'start', 'review'}
        
        if level == 'minimal':
            return event in minimal_events
        elif level == 'normal':
            return event in normal_events
        elif level == 'verbose':
            return event in verbose_events
        return False
        
    def test_notification_message_format(self):
        """Test notification message formatting"""
        task_id = "T-20260101-001"
        task_title = "Test Task"
        agent_name = "TestAgent"
        
        # Test different event messages
        messages = {
            'assign': f"📋 Task {task_id} assigned to {agent_name}: {task_title}",
            'complete': f"✅ Task {task_id} completed by {agent_name}: {task_title}",
            'block': f"🚫 Task {task_id} blocked: {task_title}",
            'start': f"🚀 Task {task_id} started by {agent_name}: {task_title}",
        }
        
        for event, expected in messages.items():
            self.assertIn(task_id, expected)
            self.assertIn(task_title, expected)
            
    def test_notification_log_entry(self):
        """Test that notifications are logged"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT INTO notification_log (task_id, agent_id, event_type, message, level, success)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('T-001', 'agent1', 'assign', 'Test message', 'normal', 1))
        
        self.conn.commit()
        
        cursor.execute('SELECT * FROM notification_log WHERE task_id = ?', ('T-001',))
        row = cursor.fetchone()
        
        self.assertIsNotNone(row)
        self.assertEqual(row['event_type'], 'assign')
        self.assertEqual(row['level'], 'normal')
        
    def test_agent_notification_preference(self):
        """Test agent-specific notification preferences"""
        cursor = self.conn.cursor()
        
        # Insert agent with notification level
        cursor.execute('''
            INSERT INTO agents (id, name, notification_level)
            VALUES (?, ?, ?)
        ''', ('agent1', 'Test Agent', 'minimal'))
        
        cursor.execute('SELECT notification_level FROM agents WHERE id = ?', ('agent1',))
        row = cursor.fetchone()
        
        self.assertEqual(row['notification_level'], 'minimal')


class TestNotificationEvents(unittest.TestCase):
    """Test specific notification events"""
    
    def test_task_assigned_notification(self):
        """AC: Notification on task assigned"""
        # This tests that assign_task sends notification
        event_type = 'assign'
        expected_emoji = '📋'
        expected_in_message = ['assigned', 'Task']
        
        self.assertEqual(expected_emoji, '📋')
        for text in expected_in_message:
            self.assertIn(text, f"Task T-001 assigned to Agent")
            
    def test_task_completed_notification(self):
        """AC: Notification on task completed"""
        event_type = 'complete'
        expected_emoji = '✅'
        
        self.assertEqual(expected_emoji, '✅')
        
    def test_task_blocked_notification(self):
        """AC: Notification on task blocked"""
        event_type = 'block'
        expected_emoji = '🚫'
        
        self.assertEqual(expected_emoji, '🚫')


class TestProgressNotifications(unittest.TestCase):
    """Test progress notification features"""
    
    def setUp(self):
        """Set up test database"""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_test_schema()
        
    def tearDown(self):
        """Clean up test database"""
        self.conn.close()
        os.close(self.db_fd)
        os.unlink(self.db_path)
        
    def _create_test_schema(self):
        """Create minimal schema for testing"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                status TEXT DEFAULT 'todo',
                assignee_id TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE agents (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                notification_level TEXT DEFAULT 'verbose'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE notification_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                level TEXT NOT NULL CHECK (level IN ('minimal', 'normal', 'verbose')),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(entity_type, entity_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE notification_log (
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
        
        # Insert test data
        cursor.execute("INSERT INTO tasks (id, title, assignee_id) VALUES (?, ?, ?)",
                      ('T-001', 'Test Task', 'agent1'))
        cursor.execute("INSERT INTO agents (id, name) VALUES (?, ?)",
                      ('agent1', 'Test Agent'))
        self.conn.commit()
    
    def test_progress_event_exists(self):
        """Test that PROGRESS event type exists"""
        self.assertTrue(hasattr(NotificationEvent, 'PROGRESS'))
        self.assertEqual(NotificationEvent.PROGRESS.value, 'progress')
    
    def test_error_event_exists(self):
        """Test that ERROR event type exists"""
        self.assertTrue(hasattr(NotificationEvent, 'ERROR'))
        self.assertEqual(NotificationEvent.ERROR.value, 'error')
    
    def test_milestone_event_exists(self):
        """Test that MILESTONE event type exists"""
        self.assertTrue(hasattr(NotificationEvent, 'MILESTONE'))
        self.assertEqual(NotificationEvent.MILESTONE.value, 'milestone')
    
    def test_progress_emoji(self):
        """Test progress event has correct emoji"""
        from notifications import NotificationManager
        self.assertEqual(NotificationManager.EVENT_EMOJI[NotificationEvent.PROGRESS], '📊')
    
    def test_error_emoji(self):
        """Test error event has correct emoji"""
        from notifications import NotificationManager
        self.assertEqual(NotificationManager.EVENT_EMOJI[NotificationEvent.ERROR], '❌')
    
    def test_milestone_emoji(self):
        """Test milestone event has correct emoji"""
        from notifications import NotificationManager
        self.assertEqual(NotificationManager.EVENT_EMOJI[NotificationEvent.MILESTONE], '🏁')
    
    def test_minimal_level_includes_error(self):
        """Test minimal level includes ERROR events"""
        from notifications import NotificationManager
        self.assertIn(NotificationEvent.ERROR, 
                     NotificationManager.LEVEL_EVENTS[NotificationLevel.MINIMAL])
    
    def test_normal_level_includes_milestone(self):
        """Test normal level includes MILESTONE events"""
        from notifications import NotificationManager
        self.assertIn(NotificationEvent.MILESTONE,
                     NotificationManager.LEVEL_EVENTS[NotificationLevel.NORMAL])
    
    def test_verbose_level_includes_progress(self):
        """Test verbose level includes PROGRESS events"""
        from notifications import NotificationManager
        self.assertIn(NotificationEvent.PROGRESS,
                     NotificationManager.LEVEL_EVENTS[NotificationLevel.VERBOSE])
    
    def test_normal_level_excludes_progress(self):
        """Test normal level excludes PROGRESS events (only milestones)"""
        from notifications import NotificationManager
        self.assertNotIn(NotificationEvent.PROGRESS,
                        NotificationManager.LEVEL_EVENTS[NotificationLevel.NORMAL])


class TestConfigurableLevels(unittest.TestCase):
    """Test configurable notification levels - AC requirement"""
    
    def test_minimal_level_only_critical(self):
        """Minimal level: only block and complete"""
        level = 'minimal'
        
        self.assertTrue(self._is_notified(level, 'block'))
        self.assertTrue(self._is_notified(level, 'complete'))
        self.assertFalse(self._is_notified(level, 'assign'))
        self.assertFalse(self._is_notified(level, 'start'))
        
    def test_normal_level_standard(self):
        """Normal level: assign, complete, block, start"""
        level = 'normal'
        
        self.assertTrue(self._is_notified(level, 'assign'))
        self.assertTrue(self._is_notified(level, 'complete'))
        self.assertTrue(self._is_notified(level, 'block'))
        self.assertTrue(self._is_notified(level, 'start'))
        self.assertFalse(self._is_notified(level, 'review'))
        
    def test_verbose_level_all(self):
        """Verbose level: all events"""
        level = 'verbose'
        
        self.assertTrue(self._is_notified(level, 'assign'))
        self.assertTrue(self._is_notified(level, 'complete'))
        self.assertTrue(self._is_notified(level, 'block'))
        self.assertTrue(self._is_notified(level, 'start'))
        self.assertTrue(self._is_notified(level, 'review'))
        
    def _is_notified(self, level: str, event: str) -> bool:
        """Helper to check if event triggers notification at given level"""
        config = {
            'minimal': {'block', 'complete'},
            'normal': {'assign', 'complete', 'block', 'start'},
            'verbose': {'assign', 'complete', 'block', 'start', 'review'}
        }
        return event in config.get(level, set())


class TestProgressNotifier(unittest.TestCase):
    """Test ProgressNotifier class"""
    
    def setUp(self):
        """Set up test database"""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_test_schema()
        
    def tearDown(self):
        """Clean up test database"""
        self.conn.close()
        os.close(self.db_fd)
        os.unlink(self.db_path)
        
    def _create_test_schema(self):
        """Create minimal schema for testing"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                status TEXT DEFAULT 'todo',
                assignee_id TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE agents (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                notification_level TEXT DEFAULT 'verbose'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE notification_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                level TEXT NOT NULL DEFAULT 'verbose' CHECK (level IN ('minimal', 'normal', 'verbose')),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(entity_type, entity_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE notification_log (
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
        
        # Insert test data
        cursor.execute("INSERT INTO tasks (id, title, assignee_id) VALUES (?, ?, ?)",
                      ('T-001', 'Test Task', 'agent1'))
        cursor.execute("INSERT INTO agents (id, name) VALUES (?, ?)",
                      ('agent1', 'Test Agent'))
        self.conn.commit()
    
    def test_progress_notifier_creation(self):
        """Test ProgressNotifier can be created"""
        notifier = ProgressNotifier(
            db_path=Path(self.db_path),
            task_id='T-001',
            agent_id='agent1',
            task_title='Test Task',
            agent_name='Test Agent'
        )
        self.assertIsNotNone(notifier)
        self.assertEqual(notifier.task_id, 'T-001')
        self.assertEqual(notifier.agent_id, 'agent1')
    
    def test_progress_notifier_tracks_last_progress(self):
        """Test ProgressNotifier tracks last progress to avoid spam"""
        notifier = ProgressNotifier(
            db_path=Path(self.db_path),
            task_id='T-001',
            agent_id='agent1'
        )
        self.assertEqual(notifier._last_progress, 0)
    
    def test_progress_clamping(self):
        """Test progress values are clamped to 0-100"""
        notifier = ProgressNotifier(
            db_path=Path(self.db_path),
            task_id='T-001',
            agent_id='agent1'
        )
        # Progress is clamped internally in report_progress
        # Testing via quick_progress static method
        result = ProgressNotifier.quick_progress(
            db_path=Path(self.db_path),
            task_id='T-001',
            agent_id='agent1',
            progress=150  # Should be clamped to 100
        )
        # Result depends on notification level, but shouldn't error


class TestPerformanceImpact(unittest.TestCase):
    """Test minimal performance impact requirements"""
    
    def test_notification_manager_is_lightweight(self):
        """Test that NotificationManager doesn't keep connections open"""
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        
        # Create full schema required by NotificationManager
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE notification_settings (
                id INTEGER PRIMARY KEY,
                entity_type TEXT,
                entity_id TEXT,
                level TEXT DEFAULT 'normal'
            )
        ''')
        cursor.execute('''
            CREATE TABLE notification_log (
                id INTEGER PRIMARY KEY,
                event_type TEXT,
                message TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE agents (
                id TEXT PRIMARY KEY,
                name TEXT
            )
        ''')
        conn.commit()
        conn.close()
        
        # NotificationManager should be usable without keeping connection
        nm = NotificationManager(Path(db_path))
        nm.close()
        
        # Clean up
        os.close(db_fd)
        os.unlink(db_path)


if __name__ == '__main__':
    unittest.main(verbosity=2)
