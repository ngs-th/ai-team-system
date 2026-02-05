#!/usr/bin/env python3
"""
Add per-status timestamp columns for tasks.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "team.db"

COLUMNS = [
    ("backlog_at", "DATETIME"),
    ("todo_at", "DATETIME"),
    ("in_progress_at", "DATETIME"),
    ("review_at", "DATETIME"),
    ("reviewing_at", "DATETIME"),
    ("done_at", "DATETIME"),
    ("blocked_at", "DATETIME"),
]


def migrate():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(tasks)")
    existing = {row[1] for row in cursor.fetchall()}

    for name, col_type in COLUMNS:
        if name in existing:
            continue
        cursor.execute(f"ALTER TABLE tasks ADD COLUMN {name} {col_type}")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    migrate()
