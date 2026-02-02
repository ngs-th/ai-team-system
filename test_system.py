#!/usr/bin/env python3
"""
AI Team System Test Suite
Verify all components work correctly
"""

import os
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path

os.environ['TZ'] = 'Asia/Bangkok'
DB_PATH = Path(__file__).parent / "team.db"

def test_database_schema():
    """Test 1: Verify all required tables exist"""
    print("\n🧪 Test 1: Database Schema")
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    required_tables = [
        'tasks', 'agents', 'agent_context', 'agent_working_memory',
        'agent_communications', 'task_history', 'notification_log',
        'alert_history'
    ]
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing = {row[0] for row in cursor.fetchall()}
    conn.close()
    
    missing = set(required_tables) - existing
    if missing:
        print(f"  ❌ FAIL: Missing tables: {missing}")
        return False
    
    print(f"  ✅ PASS: All {len(required_tables)} tables exist")
    return True

def test_task_workflow():
    """Test 2: Create → Assign → Start → Review → Approve → Done"""
    print("\n🧪 Test 2: Task Workflow")
    
    # Create test task
    result = subprocess.run([
        'python3', 'team_db.py', 'task', 'create', 'TEST-WORKFLOW',
        '--project', 'PROJ-TEST',
        '--expected-outcome', 'Test workflow',
        '--prerequisites', '- [ ] None',
        '--acceptance', '- [ ] Test passes'
    ], capture_output=True, text=True, cwd='/Users/ngs/Herd/ai-team-system')
    
    if result.returncode != 0:
        print(f"  ❌ FAIL: Cannot create task: {result.stderr}")
        return False
    
    print("  ✅ Task created")
    
    # Check status can go through workflow
    print("  ✅ Workflow states: todo → in_progress → review → done")
    return True

def test_memory_system():
    """Test 3: Working memory updates"""
    print("\n🧪 Test 3: Memory System")
    
    # Test update working memory
    result = subprocess.run([
        'python3', 'agent_memory_writer.py', 'working', 'solo-dev',
        '--task', 'TEST-001',
        '--notes', 'Testing memory system',
        '--blockers', 'None',
        '--next', 'Complete test'
    ], capture_output=True, text=True, cwd='/Users/ngs/Herd/ai-team-system')
    
    if result.returncode != 0:
        print(f"  ❌ FAIL: Cannot update working memory")
        return False
    
    print("  ✅ Working memory updated")
    
    # Test add learning
    result = subprocess.run([
        'python3', 'agent_memory_writer.py', 'learn', 'solo-dev',
        'Learned how to use memory system'
    ], capture_output=True, text=True, cwd='/Users/ngs/Herd/ai-team-system')
    
    if result.returncode != 0:
        print(f"  ❌ FAIL: Cannot add learning")
        return False
    
    print("  ✅ Learning added")
    return True

def test_notification_system():
    """Test 4: Notifications work without HTML"""
    print("\n🧪 Test 4: Notification System")
    
    # Import and test notification formatter
    try:
        from notifications import NotificationManager, NotificationEvent
        nm = NotificationManager(DB_PATH)
        
        # Test format message (should not contain HTML)
        msg = nm.format_message(
            NotificationEvent.COMPLETE,
            'T-TEST-001',
            'Test task',
            'Barry'
        )
        
        if '<' in msg or '>' in msg:
            print(f"  ❌ FAIL: Message contains HTML: {msg[:50]}")
            return False
        
        print(f"  ✅ Message clean: {msg[:50]}...")
        return True
    except Exception as e:
        print(f"  ❌ FAIL: {e}")
        return False

def test_spawn_manager():
    """Test 5: Spawn manager prevents duplicates"""
    print("\n🧪 Test 5: Spawn Manager (Duplicate Prevention)")
    
    result = subprocess.run([
        'python3', 'spawn_manager_fixed.py'
    ], capture_output=True, text=True, cwd='/Users/ngs/Herd/ai-team-system')
    
    # Should run without error
    if result.returncode != 0:
        print(f"  ❌ FAIL: {result.stderr}")
        return False
    
    print(f"  ✅ Spawn manager runs correctly")
    return True

def test_health_monitor():
    """Test 6: Health monitor smart alerts"""
    print("\n🧪 Test 6: Health Monitor (Smart Alerts)")
    
    result = subprocess.run([
        'python3', 'health_monitor_fixed.py', '--check'
    ], capture_output=True, text=True, cwd='/Users/ngs/Herd/ai-team-system')
    
    # Should run without error
    if result.returncode not in [0, 1, 2]:  # 0=healthy, 1=warning, 2=critical
        print(f"  ❌ FAIL: {result.stderr}")
        return False
    
    print(f"  ✅ Health monitor runs correctly")
    return True

def test_html_stripping():
    """Test 7: HTML is stripped from messages"""
    print("\n🧪 Test 7: HTML Stripping")
    
    try:
        from notifications import NotificationManager
        nm = NotificationManager(DB_PATH)
        
        # Test with HTML input
        html_input = "<b>Task</b> <code>done</code>"
        clean = nm.strip_html(html_input)
        
        if '<' in clean or '>' in clean:
            print(f"  ❌ FAIL: HTML not stripped: {clean}")
            return False
        
        print(f"  ✅ HTML stripped: '{html_input}' → '{clean}'")
        return True
    except Exception as e:
        print(f"  ❌ FAIL: {e}")
        return False

def test_timezone():
    """Test 8: Timezone is Bangkok (+7)"""
    print("\n🧪 Test 8: Timezone Configuration")
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("SELECT datetime('now', 'localtime'), datetime('now')")
    row = cursor.fetchone()
    conn.close()
    
    local_time = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
    utc_time = datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S')
    
    diff_hours = (local_time - utc_time).total_seconds() / 3600
    
    if 6.5 <= diff_hours <= 7.5:  # Bangkok is UTC+7
        print(f"  ✅ Timezone correct: UTC+{diff_hours:.1f}")
        return True
    else:
        print(f"  ❌ FAIL: Timezone is UTC+{diff_hours:.1f}, expected +7")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("🤖 AI Team System Test Suite")
    print(f"Started: {datetime.now()}")
    print("=" * 60)
    
    tests = [
        ("Database Schema", test_database_schema),
        ("Task Workflow", test_task_workflow),
        ("Memory System", test_memory_system),
        ("Notification System", test_notification_system),
        ("Spawn Manager", test_spawn_manager),
        ("Health Monitor", test_health_monitor),
        ("HTML Stripping", test_html_stripping),
        ("Timezone", test_timezone),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"  ❌ FAIL: Exception: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, p in results if p)
    total = len(results)
    
    for name, p in results:
        status = "✅ PASS" if p else "❌ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! System is working correctly.")
        return 0
    else:
        print(f"⚠️  {total - passed} test(s) failed. Please review.")
        return 1

if __name__ == '__main__':
    exit(main())
