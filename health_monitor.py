#!/usr/bin/env python3
"""
AI Team Agent Health Monitor
Monitors agent health, detects stale/offline agents, and sends alerts
"""

import os
import sqlite3
import subprocess
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Set timezone to Bangkok (+7)
os.environ['TZ'] = 'Asia/Bangkok'

DB_PATH = Path(__file__).parent / "team.db"
TELEGRAM_CHANNEL = "1268858185"

# Health thresholds (in minutes)
STALE_THRESHOLD = 30       # > 30 min = stale
OFFLINE_THRESHOLD = 60     # > 60 min = offline
TASK_STUCK_THRESHOLD = 120 # > 2 hours in progress with no update = stuck
ALERT_COOLDOWN = 30        # Don't send same alert within 30 minutes

class HealthMonitor:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self.alerts_sent = []
        
    def close(self):
        self.conn.close()
        
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        self.close()

    def _send_telegram_alert(self, message: str, alert_type: str = "general") -> bool:
        """Send alert to Telegram with cooldown to prevent spam"""
        # Check if we recently sent this type of alert
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT last_alert_sent, health_status 
            FROM agents 
            WHERE last_alert_type = ? 
            AND last_alert_sent > datetime('now', '-30 minutes')
            LIMIT 1
        ''', (alert_type,))
        
        if cursor.fetchone():
            # Alert recently sent, skip
            return False
        
        try:
            result = subprocess.run(
                ["openclaw", "message", "send", "--channel", "telegram", 
                 "--target", TELEGRAM_CHANNEL, "--message", message],
                capture_output=True,
                text=True,
                timeout=30
            )
            success = result.returncode == 0
            if success:
                self.alerts_sent.append(alert_type)
            return success
        except Exception as e:
            print(f"[Alert Error] Failed to send Telegram message: {e}")
            return False

    def ensure_schema(self):
        """Ensure database has required health monitoring columns"""
        cursor = self.conn.cursor()
        
        # Check if health_status column exists
        cursor.execute("PRAGMA table_info(agents)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'health_status' not in columns:
            cursor.execute('''
                ALTER TABLE agents ADD COLUMN health_status TEXT DEFAULT 'unknown'
                CHECK (health_status IN ('healthy', 'stale', 'offline', 'unknown'))
            ''')
            print("✅ Added health_status column to agents table")
            
        if 'last_alert_sent' not in columns:
            cursor.execute('''
                ALTER TABLE agents ADD COLUMN last_alert_sent DATETIME
            ''')
            print("✅ Added last_alert_sent column to agents table")
            
        if 'last_alert_type' not in columns:
            cursor.execute('''
                ALTER TABLE agents ADD COLUMN last_alert_type TEXT
            ''')
            print("✅ Added last_alert_type column to agents table")
            
        self.conn.commit()

    def check_agent_heartbeats(self) -> List[Dict]:
        """Check all agents for stale/offline status based on heartbeat"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT 
                a.id,
                a.name,
                a.role,
                a.status as agent_status,
                a.last_heartbeat,
                a.health_status,
                a.last_alert_sent,
                a.last_alert_type,
                ROUND((strftime('%s', 'now') - strftime('%s', a.last_heartbeat)) / 60.0, 1) as minutes_since_heartbeat,
                t.id as current_task_id,
                t.title as current_task_title,
                t.status as task_status
            FROM agents a
            LEFT JOIN tasks t ON a.current_task_id = t.id
            ORDER BY a.last_heartbeat DESC
        ''')
        
        agents = [dict(row) for row in cursor.fetchall()]
        issues = []
        
        for agent in agents:
            minutes_since = agent['minutes_since_heartbeat'] or 9999
            old_health = agent['health_status'] or 'unknown'
            new_health = old_health
            
            # Determine health status
            if agent['last_heartbeat'] is None:
                new_health = 'unknown'
            elif minutes_since > OFFLINE_THRESHOLD:
                new_health = 'offline'
            elif minutes_since > STALE_THRESHOLD:
                new_health = 'stale'
            else:
                new_health = 'healthy'
            
            # Update health status in DB
            if new_health != old_health:
                cursor.execute('''
                    UPDATE agents 
                    SET health_status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (new_health, agent['id']))
                self.conn.commit()
                
                # Log the health change
                print(f"🔄 Agent {agent['name']} health changed: {old_health} → {new_health}")
            
            agent['new_health'] = new_health
            agent['old_health'] = old_health
            
            # Check if we should alert
            should_alert = False
            alert_reason = ""
            
            if new_health == 'offline' and old_health != 'offline':
                should_alert = True
                alert_reason = f"Agent {agent['name']} is OFFLINE (no heartbeat for {int(minutes_since)} minutes)"
            elif new_health == 'stale' and old_health == 'healthy':
                should_alert = True
                alert_reason = f"Agent {agent['name']} is STALE (no heartbeat for {int(minutes_since)} minutes)"
            
            if should_alert:
                # Check cooldown
                if agent['last_alert_sent']:
                    last_alert = datetime.fromisoformat(agent['last_alert_sent'].replace('Z', '+00:00'))
                    if datetime.now() - last_alert < timedelta(minutes=ALERT_COOLDOWN):
                        should_alert = False
                
                if should_alert:
                    issues.append({
                        'type': 'agent_health',
                        'agent_id': agent['id'],
                        'agent_name': agent['name'],
                        'severity': 'critical' if new_health == 'offline' else 'warning',
                        'message': alert_reason,
                        'minutes_since_heartbeat': minutes_since
                    })
                    
                    # Update last alert timestamp
                    cursor.execute('''
                        UPDATE agents 
                        SET last_alert_sent = CURRENT_TIMESTAMP,
                            last_alert_type = ?
                        WHERE id = ?
                    ''', (f"health_{new_health}", agent['id']))
                    self.conn.commit()
        
        return issues

    def check_stuck_tasks(self) -> List[Dict]:
        """Check for tasks stuck in progress without updates for > 2 hours"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT 
                t.id,
                t.title,
                t.status,
                t.progress,
                t.started_at,
                t.updated_at,
                a.id as agent_id,
                a.name as agent_name,
                ROUND((strftime('%s', 'now') - strftime('%s', t.updated_at)) / 60.0, 1) as minutes_since_update,
                ROUND((strftime('%s', 'now') - strftime('%s', t.started_at)) / 60.0, 1) as minutes_since_start
            FROM tasks t
            JOIN agents a ON t.assignee_id = a.id
            WHERE t.status = 'in_progress'
            AND t.updated_at < datetime('now', '-2 hours')
            ORDER BY t.updated_at ASC
        ''')
        
        stuck_tasks = [dict(row) for row in cursor.fetchall()]
        issues = []
        
        for task in stuck_tasks:
            minutes_since_update = task['minutes_since_update'] or 0
            
            issue = {
                'type': 'stuck_task',
                'task_id': task['id'],
                'task_title': task['title'],
                'agent_id': task['agent_id'],
                'agent_name': task['agent_name'],
                'severity': 'warning',
                'message': f"Task {task['id']} stuck for {int(minutes_since_update)} minutes (assigned to {task['agent_name']})",
                'minutes_since_update': minutes_since_update,
                'progress': task['progress']
            }
            issues.append(issue)
        
        return issues

    def check_subagent_sessions(self) -> List[Dict]:
        """Check for long-running subagent sessions that might be stuck"""
        cursor = self.conn.cursor()
        
        # Check if there's a subagent_sessions table or similar
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%subagent%'")
        tables = [row[0] for row in cursor.fetchall()]
        
        if not tables:
            # No subagent tracking table, check task history for long-running actions
            cursor.execute('''
                SELECT 
                    th.id,
                    th.task_id,
                    th.agent_id,
                    th.action,
                    th.timestamp,
                    t.title as task_title,
                    a.name as agent_name,
                    ROUND((strftime('%s', 'now') - strftime('%s', th.timestamp)) / 60.0, 1) as minutes_since_action
                FROM task_history th
                JOIN tasks t ON th.task_id = t.id
                JOIN agents a ON th.agent_id = a.id
                WHERE th.action IN ('started', 'assigned')
                AND th.timestamp < datetime('now', '-3 hours')
                AND t.status = 'in_progress'
                ORDER BY th.timestamp ASC
            ''')
            
            old_actions = [dict(row) for row in cursor.fetchall()]
            issues = []
            
            for action in old_actions:
                minutes_since = action['minutes_since_action'] or 0
                if minutes_since > 180:  # > 3 hours
                    issues.append({
                        'type': 'long_running_session',
                        'task_id': action['task_id'],
                        'agent_id': action['agent_id'],
                        'agent_name': action['agent_name'],
                        'severity': 'warning',
                        'message': f"Long-running session: {action['agent_name']} working on {action['task_id']} for {int(minutes_since)} minutes",
                        'minutes_since_action': minutes_since
                    })
            
            return issues
        
        return []

    def run_health_check(self) -> Dict:
        """Run complete health check and return results"""
        print("🔍 Running AI Team Health Check...")
        print("=" * 50)
        
        # Ensure schema is up to date
        self.ensure_schema()
        
        all_issues = []
        
        # Check 1: Agent heartbeats
        print("\n📡 Checking agent heartbeats...")
        heartbeat_issues = self.check_agent_heartbeats()
        all_issues.extend(heartbeat_issues)
        
        if heartbeat_issues:
            for issue in heartbeat_issues:
                emoji = "🔴" if issue['severity'] == 'critical' else "🟡"
                print(f"  {emoji} {issue['message']}")
        else:
            print("  ✅ All agents reporting healthy heartbeats")
        
        # Check 2: Stuck tasks
        print("\n⏱️ Checking for stuck tasks...")
        stuck_tasks = self.check_stuck_tasks()
        all_issues.extend(stuck_tasks)
        
        if stuck_tasks:
            for issue in stuck_tasks:
                print(f"  🟡 {issue['message']} (Progress: {issue['progress']}%)")
        else:
            print("  ✅ No stuck tasks found")
        
        # Check 3: Long-running subagent sessions
        print("\n👤 Checking subagent sessions...")
        session_issues = self.check_subagent_sessions()
        all_issues.extend(session_issues)
        
        if session_issues:
            for issue in session_issues:
                print(f"  🟡 {issue['message']}")
        else:
            print("  ✅ No long-running sessions detected")
        
        # Send alerts for critical issues
        print("\n📤 Sending alerts...")
        critical_issues = [i for i in all_issues if i['severity'] == 'critical']
        warning_issues = [i for i in all_issues if i['severity'] == 'warning']
        
        alerts_sent = 0
        
        # Group issues by type for consolidated alerts
        if critical_issues:
            message = "🔴 *CRITICAL: AI Team Health Issues*\n\n"
            for issue in critical_issues:
                message += f"• {issue['message']}\n"
            message += f"\nChecked at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            if self._send_telegram_alert(message, "critical_health"):
                print("  ✅ Critical alert sent")
                alerts_sent += 1
        
        if warning_issues:
            # Send warnings in batches to avoid spam
            message = "🟡 *WARNING: AI Team Health Issues*\n\n"
            for issue in warning_issues[:5]:  # Limit to 5 warnings per alert
                message += f"• {issue['message']}\n"
            if len(warning_issues) > 5:
                message += f"\n...and {len(warning_issues) - 5} more warnings"
            message += f"\nChecked at: {datetime.now().strftime('%Y-%m-%d %H:%S')}"
            
            if self._send_telegram_alert(message, "warning_health"):
                print("  ✅ Warning alert sent")
                alerts_sent += 1
        
        if not critical_issues and not warning_issues:
            print("  ✅ No alerts needed - all systems healthy")
        
        print("\n" + "=" * 50)
        print(f"Health check complete: {len(critical_issues)} critical, {len(warning_issues)} warnings, {alerts_sent} alerts sent")
        
        # Auto-response for stuck tasks (> 3 hours)
        auto_resolved = self._auto_response(stuck_tasks)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'critical_count': len(critical_issues),
            'warning_count': len(warning_issues),
            'alerts_sent': alerts_sent,
            'auto_resolved': auto_resolved,
            'issues': all_issues
        }

    def _auto_response(self, stuck_tasks: List[Dict]) -> int:
        """
        Auto-response for stuck tasks based on Alert Response Workflow
        - Task stuck > 3 hours: Auto-block and release agent
        - Returns count of auto-resolved tasks
        """
        resolved = 0
        cursor = self.conn.cursor()
        
        for task in stuck_tasks:
            minutes = task.get('minutes_since_update', 0)
            
            # Only auto-respond if stuck > 3 hours (180 minutes)
            if minutes >= 180:
                task_id = task['task_id']
                agent_id = task['agent_id']
                agent_name = task['agent_name']
                
                print(f"  🔄 Auto-resolving stuck task {task_id} (>3h)")
                
                # 1. Block the task
                cursor.execute('''
                    UPDATE tasks 
                    SET status = 'blocked', 
                        blocked_reason = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (f"Auto-blocked: Stuck for {int(minutes)} minutes", task_id))
                
                # 2. Release the agent (set to idle, clear current_task)
                cursor.execute('''
                    UPDATE agents 
                    SET status = 'idle',
                        current_task_id = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (agent_id,))
                
                # 3. Log the action
                cursor.execute('''
                    INSERT INTO task_history (task_id, agent_id, action, notes)
                    VALUES (?, ?, 'blocked', ?)
                ''', (task_id, agent_id, f"Auto-blocked by health monitor after {int(minutes)} minutes"))
                
                self.conn.commit()
                
                # 4. Send notification
                message = f"🚫 *Auto-Blocked:* Task {task_id} blocked after {int(minutes)} minutes\nAgent {agent_name} released and available for new tasks"
                self._send_telegram_alert(message, f"auto_block_{task_id}")
                
                resolved += 1
                print(f"  ✅ Task {task_id} auto-blocked, {agent_name} released")
        
        return resolved

    def get_health_status(self) -> Dict:
        """Get current health status summary"""
        cursor = self.conn.cursor()
        
        # Ensure schema exists
        self.ensure_schema()
        
        # Get agent health summary
        cursor.execute('''
            SELECT 
                health_status,
                COUNT(*) as count
            FROM agents
            GROUP BY health_status
        ''')
        health_summary = {row[0] or 'unknown': row[1] for row in cursor.fetchall()}
        
        # Get detailed agent status
        cursor.execute('''
            SELECT 
                a.id,
                a.name,
                a.role,
                a.health_status,
                a.status as agent_status,
                a.last_heartbeat,
                ROUND((strftime('%s', 'now') - strftime('%s', a.last_heartbeat)) / 60.0, 1) as minutes_since_heartbeat,
                t.id as current_task_id,
                t.title as current_task_title
            FROM agents a
            LEFT JOIN tasks t ON a.current_task_id = t.id
            ORDER BY a.name
        ''')
        agents = [dict(row) for row in cursor.fetchall()]
        
        # Get stuck tasks count
        cursor.execute('''
            SELECT COUNT(*) 
            FROM tasks 
            WHERE status = 'in_progress' 
            AND updated_at < datetime('now', '-2 hours')
        ''')
        stuck_count = cursor.fetchone()[0]
        
        # Get recent alerts
        cursor.execute('''
            SELECT 
                name,
                last_alert_sent,
                last_alert_type
            FROM agents
            WHERE last_alert_sent > datetime('now', '-24 hours')
            ORDER BY last_alert_sent DESC
        ''')
        recent_alerts = [dict(row) for row in cursor.fetchall()]
        
        return {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'healthy': health_summary.get('healthy', 0),
                'stale': health_summary.get('stale', 0),
                'offline': health_summary.get('offline', 0),
                'unknown': health_summary.get('unknown', 0)
            },
            'stuck_tasks': stuck_count,
            'agents': agents,
            'recent_alerts': recent_alerts
        }

    def print_health_status(self):
        """Print formatted health status to console"""
        status = self.get_health_status()
        
        print("\n" + "=" * 60)
        print("🤖 AI TEAM HEALTH STATUS")
        print("=" * 60)
        print(f"\n📊 Summary (as of {datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
        print(f"   ✅ Healthy:  {status['summary']['healthy']}")
        print(f"   🟡 Stale:    {status['summary']['stale']}")
        print(f"   🔴 Offline:  {status['summary']['offline']}")
        print(f"   ⚪ Unknown:  {status['summary']['unknown']}")
        print(f"\n⏱️ Stuck Tasks (>2h no update): {status['stuck_tasks']}")
        
        print("\n📋 Agent Details:")
        print("-" * 60)
        print(f"{'Name':<20} {'Health':<10} {'Status':<10} {'Last Heartbeat':<20}")
        print("-" * 60)
        
        for agent in status['agents']:
            health_emoji = {
                'healthy': '✅',
                'stale': '🟡',
                'offline': '🔴',
                'unknown': '⚪'
            }.get(agent['health_status'], '⚪')
            
            minutes = agent['minutes_since_heartbeat']
            if minutes is None:
                last_seen = "Never"
            elif minutes < 1:
                last_seen = "Just now"
            elif minutes < 60:
                last_seen = f"{int(minutes)}m ago"
            else:
                hours = minutes / 60
                last_seen = f"{hours:.1f}h ago"
            
            print(f"{agent['name']:<20} {health_emoji} {agent['health_status']:<8} {agent['agent_status']:<10} {last_seen:<20}")
        
        if status['recent_alerts']:
            print("\n🚨 Recent Alerts (24h):")
            print("-" * 60)
            for alert in status['recent_alerts'][:5]:
                print(f"   {alert['last_alert_sent']}: {alert['name']} - {alert['last_alert_type']}")
        
        print("=" * 60)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='AI Team Health Monitor')
    parser.add_argument('--check', action='store_true', help='Run health check once')
    parser.add_argument('--status', action='store_true', help='Show current health status')
    parser.add_argument('--daemon', action='store_true', help='Run as daemon (for cron)')
    parser.add_argument('--auto-resolve', action='store_true', help='Auto-resolve stuck tasks (>3h)')
    parser.add_argument('--resolve-task', type=str, help='Manually resolve specific stuck task ID')
    
    args = parser.parse_args()
    
    with HealthMonitor() as monitor:
        if args.check or args.daemon:
            result = monitor.run_health_check()
            # Exit with error code if critical issues found (for cron monitoring)
            if result['critical_count'] > 0:
                exit(1)
        elif args.status:
            monitor.print_health_status()
        elif args.auto_resolve:
            # Force auto-resolve all stuck tasks > 3 hours
            print("🔄 Running auto-resolve for stuck tasks...")
            stuck = monitor.check_stuck_tasks()
            resolved = monitor._auto_response(stuck)
            print(f"✅ Auto-resolved {resolved} tasks")
        elif args.resolve_task:
            # Resolve specific task
            task_id = args.resolve_task
            print(f"🔄 Resolving task {task_id}...")
            cursor = monitor.conn.cursor()
            cursor.execute('''
                UPDATE tasks 
                SET status = 'blocked', 
                    blocked_reason = 'Manually resolved by health monitor',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND status = 'in_progress'
            ''', (task_id,))
            monitor.conn.commit()
            print(f"✅ Task {task_id} blocked, agent released")
        else:
            # Default: show status
            monitor.print_health_status()


if __name__ == '__main__':
    main()
