#!/usr/bin/env python3
"""
Agent Progress Notifications Integration
Easy-to-use module for agents to report progress during task execution
QA Engineer: Quinn
"""

import os
import sys
import sqlite3
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from notifications import ProgressNotifier, NotificationManager, NotificationEvent

# Set timezone
os.environ['TZ'] = 'Asia/Bangkok'

DB_PATH = Path(__file__).parent / "team.db"
TELEGRAM_CHANNEL = "1268858185"


class AgentProgressReporter:
    """
    High-level interface for agents to report progress
    Auto-detects task context from database
    """
    
    def __init__(self, agent_id: str, task_id: str = None, db_path: Path = DB_PATH):
        self.agent_id = agent_id
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        
        # Auto-detect task if not provided
        self.task_id = task_id or self._detect_current_task()
        self.task_title = None
        self.agent_name = None
        self._notifier = None
        
        self._load_context()
        
    def _detect_current_task(self) -> Optional[str]:
        """Auto-detect current task from agent assignment"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT current_task_id FROM agents WHERE id = ?
        ''', (self.agent_id,))
        row = cursor.fetchone()
        return row[0] if row else None
    
    def _load_context(self):
        """Load task and agent details"""
        cursor = self.conn.cursor()
        
        # Load task title
        if self.task_id:
            cursor.execute('''
                SELECT title FROM tasks WHERE id = ?
            ''', (self.task_id,))
            row = cursor.fetchone()
            self.task_title = row[0] if row else self.task_id
        
        # Load agent name
        cursor.execute('''
            SELECT name FROM agents WHERE id = ?
        ''', (self.agent_id,))
        row = cursor.fetchone()
        self.agent_name = row[0] if row else self.agent_id
        
        # Initialize notifier
        if self.task_id:
            self._notifier = ProgressNotifier(
                db_path=self.db_path,
                task_id=self.task_id,
                agent_id=self.agent_id,
                task_title=self.task_title,
                agent_name=self.agent_name
            )
    
    def progress(self, percent: int, message: str = None) -> bool:
        """Report progress percentage (0-100)"""
        if not self._notifier:
            print("[Progress] No active task detected")
            return False
        return self._notifier.report_progress(percent, message)
    
    def milestone(self, description: str) -> bool:
        """Report a milestone achievement"""
        if not self._notifier:
            print("[Progress] No active task detected")
            return False
        return self._notifier.report_milestone(description)
    
    def error(self, message: str, fatal: bool = False) -> bool:
        """Report an error"""
        if not self._notifier:
            print("[Progress] No active task detected")
            return False
        return self._notifier.report_error(message, fatal)
    
    def complete(self, summary: str = None) -> bool:
        """Report task completion"""
        if not self._notifier:
            print("[Progress] No active task detected")
            return False
        return self._notifier.report_completion(summary)
    
    def close(self):
        """Close database connection"""
        self.conn.close()


def quick_progress(agent_id: str, progress: int, task_id: str = None, 
                   message: str = None, db_path: Path = DB_PATH) -> bool:
    """
    Quick one-off progress report without creating a reporter instance
    Usage: quick_progress('dev', 50, 'T-20260101-001')
    """
    reporter = AgentProgressReporter(agent_id, task_id, db_path)
    try:
        result = reporter.progress(progress, message)
        return result
    finally:
        reporter.close()


def quick_milestone(agent_id: str, milestone: str, task_id: str = None,
                    db_path: Path = DB_PATH) -> bool:
    """
    Quick one-off milestone report
    Usage: quick_milestone('dev', 'Database schema created')
    """
    reporter = AgentProgressReporter(agent_id, task_id, db_path)
    try:
        result = reporter.milestone(milestone)
        return result
    finally:
        reporter.close()


def quick_error(agent_id: str, error: str, task_id: str = None,
                fatal: bool = False, db_path: Path = DB_PATH) -> bool:
    """
    Quick one-off error report
    Usage: quick_error('dev', 'API timeout', fatal=True)
    """
    reporter = AgentProgressReporter(agent_id, task_id, db_path)
    try:
        result = reporter.error(error, fatal)
        return result
    finally:
        reporter.close()


def main():
    """CLI for testing progress notifications"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Agent Progress Reporter')
    subparsers = parser.add_subparsers(dest='command')
    
    # Progress command
    prog = subparsers.add_parser('progress', help='Report progress')
    prog.add_argument('agent_id', help='Agent ID')
    prog.add_argument('percent', type=int, help='Progress percentage (0-100)')
    prog.add_argument('--task', help='Task ID (auto-detected if not specified)')
    prog.add_argument('--message', help='Optional message')
    
    # Milestone command
    mile = subparsers.add_parser('milestone', help='Report milestone')
    mile.add_argument('agent_id', help='Agent ID')
    mile.add_argument('description', help='Milestone description')
    mile.add_argument('--task', help='Task ID')
    
    # Error command
    err = subparsers.add_parser('error', help='Report error')
    err.add_argument('agent_id', help='Agent ID')
    err.add_argument('message', help='Error message')
    err.add_argument('--task', help='Task ID')
    err.add_argument('--fatal', action='store_true', help='Fatal error (blocks task)')
    
    # Complete command
    comp = subparsers.add_parser('complete', help='Report completion')
    comp.add_argument('agent_id', help='Agent ID')
    comp.add_argument('--task', help='Task ID')
    comp.add_argument('--summary', help='Completion summary')
    
    args = parser.parse_args()
    
    if args.command == 'progress':
        success = quick_progress(args.agent_id, args.percent, args.task, args.message)
        print(f"{'✅' if success else '❌'} Progress notification {'sent' if success else 'failed'}")
        
    elif args.command == 'milestone':
        success = quick_milestone(args.agent_id, args.description, args.task)
        print(f"{'✅' if success else '❌'} Milestone notification {'sent' if success else 'failed'}")
        
    elif args.command == 'error':
        success = quick_error(args.agent_id, args.message, args.task, args.fatal)
        print(f"{'✅' if success else '❌'} Error notification {'sent' if success else 'failed'}")
        
    elif args.command == 'complete':
        reporter = AgentProgressReporter(args.agent_id, args.task)
        try:
            success = reporter.complete(args.summary)
            print(f"{'✅' if success else '❌'} Completion notification {'sent' if success else 'failed'}")
        finally:
            reporter.close()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
