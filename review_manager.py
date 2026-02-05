#!/usr/bin/env python3
"""
AI Team Review Manager
Auto-approve or auto-reject tasks in review based on evidence.
"""

import argparse
import os
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from agent_runtime import spawn_agent, get_runtime

DB_PATH = Path(__file__).parent / "team.db"
LOG_DIR = Path(__file__).parent / "logs"
REVIEW_MINUTES = int(os.getenv("AI_TEAM_REVIEW_MINUTES", "10"))
REJECT_GRACE_MINUTES = int(os.getenv("AI_TEAM_REVIEW_REJECT_GRACE_MINUTES", "60"))
REVIEWER_STALE_MINUTES = int(os.getenv("AI_TEAM_REVIEWER_STALE_MINUTES", "20"))
DEFAULT_REVIEWER = "qa"


def parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def has_log_completion(task_id: str) -> bool:
    if not LOG_DIR.exists():
        return False
    patterns = [
        f"spawn_{task_id}_*.log",
        f"auto_assign_{task_id}_*.log",
    ]
    for pattern in patterns:
        for path in LOG_DIR.glob(pattern):
            try:
                text = path.read_text(errors="ignore")
            except Exception:
                continue
            if "Task Completed" in text or "✅ Task" in text or "Status: Done" in text:
                return True
    return False


def has_recent_file_changes(working_dir: str, since: Optional[datetime]) -> bool:
    if not working_dir or not os.path.isdir(working_dir):
        return False
    if since is None:
        return False

    skip_dirs = {".git", "node_modules", "vendor", "storage", "logs", "tmp", "cache"}
    since_ts = since.timestamp()

    for root, dirs, files in os.walk(working_dir):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for name in files:
            try:
                path = os.path.join(root, name)
                if os.path.getmtime(path) > since_ts:
                    return True
            except Exception:
                continue
    return False


def has_recent_working_memory(agent_id: str, task_id: str) -> bool:
    if not agent_id or not task_id:
        return False
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 1
        FROM agent_working_memory
        WHERE agent_id = ?
          AND current_task_id = ?
          AND last_updated > datetime('now', '-2 hours')
        LIMIT 1
    ''', (agent_id, task_id))
    ok = cursor.fetchone() is not None
    conn.close()
    return ok


def checklist_unchecked(text: Optional[str]) -> list:
    items = []
    for line in (text or "").splitlines():
        m = re.match(r'^\s*[-*]\s+\[(x| )\]\s+(.*)$', line, re.IGNORECASE)
        if not m:
            continue
        checked = m.group(1).lower() == 'x'
        label = m.group(2).strip()
        if not checked:
            items.append(label)
    return items


def _is_human_only_prereq(label: str) -> bool:
    if not label:
        return False
    s = label.lower()
    return ("@human" in s) or ("human-only" in s) or ("🔒" in label) or s.startswith("human:")


def reviewer_status(reviewer_id: str):
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute('SELECT status, current_task_id, last_heartbeat FROM agents WHERE id = ?', (reviewer_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None, None, None
    return row[0], row[1], parse_dt(row[2])


def release_reviewer(reviewer_id: str):
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE agents
        SET status = 'idle',
            current_task_id = NULL,
            updated_at = datetime('now', 'localtime')
        WHERE id = ?
    ''', (reviewer_id,))
    conn.commit()
    conn.close()


def get_reviewer_ids() -> list:
    env = os.getenv("AI_TEAM_REVIEWERS", "").strip()
    if env:
        return [r.strip() for r in env.split(",") if r.strip()]

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id FROM agents
        WHERE lower(id) LIKE 'qa%' OR lower(role) LIKE '%qa%' OR lower(role) LIKE '%review%'
        ORDER BY id
    ''')
    rows = [r[0] for r in cursor.fetchall()]
    conn.close()
    return rows or [DEFAULT_REVIEWER]

def order_reviewers_for_assignment(reviewer_ids: list) -> list:
    """
    Prefer reviewers that have been idle longest (older heartbeat first),
    so load is spread across qa/qa-2/qa-3/qa-4 instead of always first id.
    """
    if not reviewer_ids:
        return []
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    placeholders = ",".join(["?"] * len(reviewer_ids))
    cursor.execute(
        f"SELECT id, COALESCE(last_heartbeat, '1970-01-01 00:00:00') FROM agents WHERE id IN ({placeholders})",
        reviewer_ids,
    )
    hb = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return sorted(reviewer_ids, key=lambda rid: (hb.get(rid, "1970-01-01 00:00:00"), rid))


def assign_reviewer(reviewer_id: str, task_id: str) -> None:
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE agents
        SET status = 'active',
            current_task_id = ?,
            last_heartbeat = datetime('now', 'localtime'),
            updated_at = datetime('now', 'localtime')
        WHERE id = ?
    ''', (task_id, reviewer_id))
    conn.commit()
    conn.close()


def build_review_message(task: sqlite3.Row, reviewer_id: str) -> str:
    working_dir = task['working_dir'] or '/Users/ngs/clawd'
    base_dir = str(Path(__file__).parent)
    return f"""## Review Task (Code Review Required)

**Reviewer:** {reviewer_id}
**Task:** {task['id']} - {task['title']}

### 📁 WORKING DIRECTORY (REQUIRED)
**You MUST work in:** `{working_dir}`
```bash
cd {working_dir}
```

### What to Review
- **Description:** {task['description'] or 'N/A'}
- **Expected Outcome:** {task['expected_outcome'] or 'N/A'}
- **Acceptance Criteria:** {task['acceptance_criteria'] or 'N/A'}
- **Prerequisites:** {task['prerequisites'] or 'N/A'}

### Required Review Steps
1. Inspect changes (preferred):
   - If git repo: `git status -sb` then `git diff` (or `git diff --stat`)
   - If no git: identify changed files by timestamps
2. Read the changed files and assess:
   - correctness vs acceptance criteria
   - edge cases / regressions
   - code quality & maintainability
3. Run tests **only if clearly specified** in README/task or obvious test command exists.
4. **Mark Acceptance Criteria checklist items 1-by-1 (required for approval)**:
```bash
python3 {base_dir}/team_db.py task check {task['id']} --field acceptance --index <n> --done
```

### Deliverable: Review Report
Provide a concise report with:
- Summary (PASS/FAIL)
- Files reviewed
- Tests run (or "not run" + reason)
- Issues found (if any)

### Decision (required)
Approve:
```bash
python3 {base_dir}/team_db.py task approve {task['id']} --reviewer {reviewer_id}
```

Reject (must include reason):
```bash
python3 {base_dir}/team_db.py task reject {task['id']} --reviewer {reviewer_id} --reason \"<what to fix>\"
```
"""


def spawn_review_agent(task: sqlite3.Row, reviewer_id: str) -> bool:
    import time

    message = build_review_message(task, reviewer_id)
    log_dir = LOG_DIR
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / f"review_{task['id']}_{reviewer_id}_{int(time.time())}.log"

    ok, _ = spawn_agent(
        agent_id=reviewer_id,
        task_id=task["id"],
        working_dir=task["working_dir"] or str(Path(__file__).parent),
        message=message,
        log_path=log_path,
        timeout_seconds=3600,
        label=f"{reviewer_id}-{task['id']}",
    )
    if ok:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE tasks
            SET runtime = ?,
                runtime_at = datetime('now', 'localtime'),
                updated_at = datetime('now', 'localtime')
            WHERE id = ?
        ''', (get_runtime(), task["id"]))
        conn.commit()
        conn.close()
    return ok

def reconcile_completed_tasks(verbose: bool = False) -> None:
    """Move tasks with completion evidence into review."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id FROM tasks
        WHERE status IN ('in_progress')
          AND (
                completed_at IS NOT NULL
             OR progress >= 100
          )
        """
    )
    candidate_ids = [row[0] for row in cursor.fetchall()]
    cursor.execute(
        """
        UPDATE tasks
        SET status = 'review',
            progress = CASE WHEN progress IS NULL OR progress < 100 THEN 100 ELSE progress END,
            blocked_reason = NULL,
            blocked_at = NULL,
            review_at = datetime('now', 'localtime'),
            updated_at = datetime('now', 'localtime')
        WHERE status IN ('in_progress')
          AND (
                completed_at IS NOT NULL
             OR progress >= 100
          )
        """
    )
    moved = cursor.rowcount
    conn.commit()
    conn.close()
    if candidate_ids:
        try:
            from sprint_status_sync import update_story_status
            for tid in candidate_ids:
                update_story_status(tid, 'review')
        except Exception:
            pass
    if verbose and moved:
        print(f"Reconciled {moved} completed tasks -> review")


def auto_reject(task_id: str, reason: str):
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE tasks
        SET status = 'todo',
            started_at = NULL,
            blocked_reason = NULL,
            blocked_at = NULL,
            fix_loop_count = COALESCE(fix_loop_count, 0) + 1,
            review_feedback = ?,
            review_feedback_at = datetime('now', 'localtime'),
            todo_at = datetime('now', 'localtime'),
            updated_at = datetime('now', 'localtime')
        WHERE id = ?
    ''', (reason, task_id))

    cursor.execute('''
        INSERT INTO task_history (task_id, action, old_status, new_status, notes)
        VALUES (?, 'updated', 'review', 'todo', ?)
    ''', (task_id, reason))
    conn.commit()
    conn.close()
    try:
        from sprint_status_sync import update_story_status
        update_story_status(task_id, 'todo')
    except Exception:
        pass


def soft_return_to_todo(task_id: str, reason: str):
    """
    Return task to TODO without increasing fix loop.
    Used for transient/system issues (e.g. stale working memory) to avoid false auto-stop.
    """
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return
    old_status = row[0] or "review"

    cursor.execute('''
        UPDATE tasks
        SET status = 'todo',
            started_at = NULL,
            blocked_reason = NULL,
            blocked_at = NULL,
            review_feedback = ?,
            review_feedback_at = datetime('now', 'localtime'),
            todo_at = datetime('now', 'localtime'),
            updated_at = datetime('now', 'localtime')
        WHERE id = ?
    ''', (reason, task_id))

    cursor.execute('''
        UPDATE agents
        SET status = 'idle',
            current_task_id = NULL,
            updated_at = datetime('now', 'localtime')
        WHERE current_task_id = ?
    ''', (task_id,))

    cursor.execute('''
        INSERT INTO task_history (task_id, action, old_status, new_status, agent_id, notes)
        VALUES (?, 'backlogged', ?, 'todo', 'auto-review', ?)
    ''', (task_id, old_status, reason))

    conn.commit()
    conn.close()
    try:
        from sprint_status_sync import update_story_status
        update_story_status(task_id, 'todo')
    except Exception:
        pass


def mark_info_needed(task_id: str, reason: str):
    """Mark task as waiting for human input (does not count as a fix loop)."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return
    old_status = row[0] or "review"

    cursor.execute('''
        UPDATE tasks
        SET status = 'info_needed',
            blocked_reason = ?,
            blocked_at = datetime('now', 'localtime'),
            review_feedback = ?,
            review_feedback_at = datetime('now', 'localtime'),
            updated_at = datetime('now', 'localtime')
        WHERE id = ?
    ''', (reason, reason, task_id))

    cursor.execute('''
        UPDATE agents
        SET status = 'idle',
            current_task_id = NULL,
            updated_at = datetime('now', 'localtime')
        WHERE current_task_id = ?
    ''', (task_id,))

    cursor.execute('''
        INSERT INTO task_history (task_id, action, old_status, new_status, agent_id, notes)
        VALUES (?, 'updated', ?, 'info_needed', 'auto-review', ?)
    ''', (task_id, old_status, reason))

    conn.commit()
    conn.close()


def mark_reviewing(task_id: str, note: str = "Auto-review started"):
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE tasks
        SET status = 'reviewing',
            blocked_reason = NULL,
            blocked_at = NULL,
            reviewing_at = datetime('now', 'localtime'),
            updated_at = datetime('now', 'localtime')
        WHERE id = ? AND status = 'review'
    ''', (task_id,))
    if cursor.rowcount > 0:
        cursor.execute('''
            INSERT INTO task_history (task_id, action, old_status, new_status, notes)
            VALUES (?, 'updated', 'review', 'reviewing', ?)
        ''', (task_id, note))
    conn.commit()
    conn.close()
    try:
        from sprint_status_sync import update_story_status
        update_story_status(task_id, 'reviewing')
    except Exception:
        pass

def mark_waiting_review(task_id: str, note: str = "No active reviewer; returned to waiting review"):
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE tasks
        SET status = 'review',
            blocked_reason = NULL,
            blocked_at = NULL,
            updated_at = datetime('now', 'localtime')
        WHERE id = ? AND status = 'reviewing'
    ''', (task_id,))
    if cursor.rowcount > 0:
        cursor.execute('''
            INSERT INTO task_history (task_id, action, old_status, new_status, notes)
            VALUES (?, 'updated', 'reviewing', 'review', ?)
        ''', (task_id, note))
    conn.commit()
    conn.close()
    try:
        from sprint_status_sync import update_story_status
        update_story_status(task_id, 'review')
    except Exception:
        pass


def review_tasks(dry_run: bool = False, verbose: bool = False):
    if not dry_run:
        reconcile_completed_tasks(verbose=verbose)

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, title, description, expected_outcome, acceptance_criteria, prerequisites,
               assignee_id, working_dir, progress, completed_at, started_at, updated_at, status
        FROM tasks
        WHERE status IN ('review', 'reviewing')
    ''')
    tasks = cursor.fetchall()
    conn.close()

    if not tasks:
        if verbose:
            print("No review tasks.")
        return

    reviewers = get_reviewer_ids()
    assignment_order = order_reviewers_for_assignment(reviewers)
    now = datetime.now()
    for task in tasks:
        task_id = task['id']
        progress = task['progress'] or 0
        completed_at = parse_dt(task['completed_at'])
        started_at = parse_dt(task['started_at'])
        updated_at = parse_dt(task['updated_at'])
        working_dir = task['working_dir']
        status = task['status'] or 'review'
        assignee_id = task['assignee_id']
        prerequisites = task['prerequisites']

        # Review gate: prerequisites must be checked before any review starts.
        unmet_prereq = checklist_unchecked(prerequisites)
        if unmet_prereq:
            human_unmet = [p for p in unmet_prereq if _is_human_only_prereq(p)]
            if human_unmet:
                reason = "Info needed (HUMAN-only prerequisites unchecked) -> " + "; ".join(human_unmet)
            else:
                reason = "Review gate failed: prerequisites unchecked -> " + "; ".join(unmet_prereq)
            if verbose:
                print(f"REQUEUE {task_id} ({reason})")
            if not dry_run:
                if human_unmet:
                    mark_info_needed(task_id, reason)
                else:
                    soft_return_to_todo(task_id, reason)
            continue

        evidence = []
        if progress >= 100:
            evidence.append("progress=100")
        if completed_at:
            evidence.append("completed_at")
        if has_log_completion(task_id):
            evidence.append("log")
        if has_recent_file_changes(working_dir, started_at or updated_at):
            evidence.append("files")

        if status == 'review':
            if evidence:
                reviewer_id = None
                reviewer_state = None
                reviewer_task = None

                # Prefer reviewer already assigned to this task
                for rid in reviewers:
                    reviewer_state, reviewer_task, _ = reviewer_status(rid)
                    if reviewer_task == task_id:
                        reviewer_id = rid
                        break

                # Otherwise, pick first idle reviewer
                if not reviewer_id:
                    for rid in assignment_order:
                        reviewer_state, reviewer_task, _ = reviewer_status(rid)
                        if reviewer_state == 'idle' and not reviewer_task:
                            reviewer_id = rid
                            break

                if not dry_run and reviewer_id:
                    if verbose:
                        print(f"REVIEWING {task_id} ({', '.join(evidence)}) -> spawn {reviewer_id}")
                    mark_reviewing(task_id)
                    if reviewer_state == 'idle':
                        assign_reviewer(reviewer_id, task_id)
                        if not spawn_review_agent(task, reviewer_id):
                            release_reviewer(reviewer_id)
                            mark_waiting_review(task_id, "Reviewer spawn failed; returned to waiting review")
                            if verbose:
                                print(f"WAIT {task_id} (spawn failed for {reviewer_id})")
                            continue
                else:
                    if verbose:
                        print(f"WAIT {task_id} (reviewer unavailable)")
            else:
                # No evidence yet: wait until grace period before auto-reject
                base_time = completed_at or updated_at
                if base_time and (now - base_time) >= timedelta(minutes=REJECT_GRACE_MINUTES):
                    reason = "Auto-review failed: no evidence of completion"
                    if verbose:
                        print(f"REJECT {task_id} ({reason})")
                    if not dry_run:
                        auto_reject(task_id, reason)
            continue

        # status == reviewing: ensure a reviewer is actually assigned
        assigned_reviewer = None
        assigned_heartbeat = None
        for rid in reviewers:
            state, current, heartbeat = reviewer_status(rid)
            if current == task_id:
                assigned_reviewer = rid
                assigned_heartbeat = heartbeat
                break

        if assigned_reviewer and assigned_heartbeat:
            age = now - assigned_heartbeat
            if age < timedelta(minutes=-5) or age >= timedelta(minutes=REVIEWER_STALE_MINUTES):
                if verbose:
                    mins = int(age.total_seconds() // 60)
                    if mins < 0:
                        print(f"REVIEWING {task_id} (clock-skew reviewer {assigned_reviewer}, {mins}m) -> release")
                    else:
                        print(f"REVIEWING {task_id} (stale reviewer {assigned_reviewer}, {mins}m) -> release")
                if not dry_run:
                    release_reviewer(assigned_reviewer)
                assigned_reviewer = None

        if not assigned_reviewer:
            # assign an idle reviewer to continue
            for rid in assignment_order:
                state, current, _ = reviewer_status(rid)
                if state == 'idle' and not current:
                    assigned_reviewer = rid
                    if not dry_run:
                        assign_reviewer(rid, task_id)
                        spawn_review_agent(task, rid)
                    if verbose:
                        print(f"REVIEWING {task_id} (reassigned -> {rid})")
                    break
        if not assigned_reviewer:
            if not dry_run:
                mark_waiting_review(task_id)
            if verbose:
                print(f"WAIT {task_id} (no active reviewer)")
            continue

        if verbose:
            print(f"REVIEWING {task_id} (active reviewer: {assigned_reviewer})")


def main():
    parser = argparse.ArgumentParser(description="AI Team Review Manager")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    review_tasks(dry_run=args.dry_run, verbose=args.verbose)


if __name__ == "__main__":
    main()
