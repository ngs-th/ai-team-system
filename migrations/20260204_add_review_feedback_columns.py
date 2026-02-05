#!/usr/bin/env python3
"""
Add review feedback columns to tasks and backfill from task_history.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "team.db"


def migrate():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(tasks)")
    existing = {row[1] for row in cursor.fetchall()}

    if "review_feedback" not in existing:
        cursor.execute("ALTER TABLE tasks ADD COLUMN review_feedback TEXT")
    if "review_feedback_at" not in existing:
        cursor.execute("ALTER TABLE tasks ADD COLUMN review_feedback_at DATETIME")

    # Backfill from latest rejection note if exists
    cursor.execute("SELECT id FROM tasks")
    task_ids = [row[0] for row in cursor.fetchall()]
    for task_id in task_ids:
        cursor.execute("""
            SELECT notes, timestamp
            FROM task_history
            WHERE task_id = ? AND action = 'rejected'
            ORDER BY timestamp DESC
            LIMIT 1
        """, (task_id,))
        row = cursor.fetchone()
        if not row:
            continue
        notes, ts = row
        cursor.execute("""
            UPDATE tasks
            SET review_feedback = COALESCE(review_feedback, ?),
                review_feedback_at = COALESCE(review_feedback_at, ?)
            WHERE id = ?
        """, (notes, ts, task_id))

    conn.commit()
    conn.close()


if __name__ == "__main__":
    migrate()
