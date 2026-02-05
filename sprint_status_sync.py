#!/usr/bin/env python3
"""
Sync task status -> sprint-status.yaml (nurse-ai).
"""
import re
import sqlite3
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "team.db"
DEFAULT_SPRINT_STATUS = Path("/Users/ngs/Herd/nurse-ai/_bmad-output/implementation-artifacts/sprint-status.yaml")

STATUS_MAP = {
    "backlog": "backlog",
    "todo": "ready",
    "in_progress": "in-progress",
    "review": "review",
    "reviewing": "review",
    "done": "done",
}


def _extract_story_id(title: str, description: str) -> Optional[str]:
    title = title or ""
    description = description or ""

    m = re.match(r"^([0-9A-Za-z][0-9A-Za-z\-\.]+):", title)
    if m:
        return m.group(1)

    m = re.search(r"Story file:\s*(.+/stories/([^/]+)\.md)", description)
    if m:
        return m.group(2)

    m = re.search(r"\bStory ID\b\s*[:\-]\s*([0-9A-Za-z][0-9A-Za-z\-\.]+)", description, re.I)
    if m:
        return m.group(1)

    return None


def update_story_status(task_id: str, status: Optional[str] = None, sprint_status_path: Path = DEFAULT_SPRINT_STATUS) -> bool:
    """Update sprint-status.yaml for a task's story id. Returns True if updated."""
    if not sprint_status_path.exists():
        return False

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT title, description, status FROM tasks WHERE id = ?", (task_id,))
    row = cur.fetchone()
    con.close()
    if not row:
        return False

    title, description, db_status = row[0], row[1], row[2]
    story_id = _extract_story_id(title, description)
    if not story_id:
        return False

    status_key = status or db_status
    new_status = STATUS_MAP.get((status_key or "").lower())
    if not new_status:
        return False

    text = sprint_status_path.read_text(encoding="utf-8")
    pattern = re.compile(rf"^(\s*{re.escape(story_id)}\s*:\s*)([^\s#]+)(.*)$", re.M)
    m = pattern.search(text)
    if not m:
        return False

    updated = pattern.sub(lambda mm: f"{mm.group(1)}{new_status}{mm.group(3)}", text, count=1)
    if updated == text:
        return False

    sprint_status_path.write_text(updated, encoding="utf-8")
    return True


def normalize_ready_status(sprint_status_path: Path = DEFAULT_SPRINT_STATUS) -> int:
    """Convert ready-for-dev -> ready in sprint-status.yaml. Returns count of changes."""
    if not sprint_status_path.exists():
        return 0
    text = sprint_status_path.read_text(encoding="utf-8")
    updated, count = re.subn(r"\bready-for-dev\b", "ready", text)
    if count:
        sprint_status_path.write_text(updated, encoding="utf-8")
    return count


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: sprint_status_sync.py <task_id>")
        raise SystemExit(1)
    tid = sys.argv[1]
    changed = update_story_status(tid)
    print("updated" if changed else "no-change")
