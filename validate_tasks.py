#!/usr/bin/env python3
"""
AI Team Task Validator
Validate all tasks have required fields
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "team.db"

def validate_tasks():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("🔍 Validating Tasks...")
    print("=" * 70)
    
    # Check all non-done tasks
    cursor.execute('''
        SELECT id, title, status, expected_outcome, prerequisites, acceptance_criteria
        FROM tasks
        WHERE status NOT IN ('done', 'cancelled')
        ORDER BY status, id
    ''')
    
    tasks = [dict(row) for row in cursor.fetchall()]
    incomplete = []
    
    for task in tasks:
        missing = []
        if not task.get('expected_outcome'):
            missing.append('expected_outcome')
        if not task.get('prerequisites'):
            missing.append('prerequisites')
        if not task.get('acceptance_criteria'):
            missing.append('acceptance_criteria')
        
        if missing:
            incomplete.append({
                'id': task['id'],
                'title': task['title'][:40],
                'status': task['status'],
                'missing': missing
            })
    
    if incomplete:
        print(f"\n⚠️  {len(incomplete)} tasks MISSING required fields:\n")
        for t in incomplete:
            print(f"  {t['id']} [{t['status']}] {t['title']}")
            print(f"    Missing: {', '.join(t['missing'])}")
        print("\n" + "=" * 70)
        print("\n❌ VALIDATION FAILED")
        print("\nFix with:")
        print("  python3 team_db.py task requirements <task_id> \\")
        print("    --expected-outcome '...' \\")
        print("    --prerequisites '- [ ] ...' \\")
        print("    --acceptance '- [ ] ...'")
        return False
    else:
        print(f"\n✅ All {len(tasks)} tasks have required fields!")
        print("=" * 70)
        return True

if __name__ == '__main__':
    import sys
    success = validate_tasks()
    sys.exit(0 if success else 1)
