#!/usr/bin/env python3
"""
Expand task_history.action CHECK constraint to include newer actions.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "team.db"

ALLOWED_ACTIONS = (
    "created", "assigned", "started", "updated", "completed",
    "blocked", "unblocked", "cancelled",
    "approved", "rejected", "backlogged", "auto_stopped"
)


def migrate():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys=off;")
    cursor.execute("BEGIN;")

    cursor.execute("ALTER TABLE task_history RENAME TO task_history_old;")

    cursor.execute(f"""
        CREATE TABLE task_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            agent_id TEXT,
            action TEXT NOT NULL CHECK (action IN {ALLOWED_ACTIONS}),
            old_status TEXT,
            new_status TEXT,
            old_progress INTEGER,
            new_progress INTEGER,
            notes TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
            FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE SET NULL
        )
    """)

    cursor.execute("""
        INSERT INTO task_history (id, task_id, agent_id, action, old_status, new_status,
                                  old_progress, new_progress, notes, timestamp)
        SELECT id, task_id, agent_id, action, old_status, new_status,
               old_progress, new_progress, notes, timestamp
        FROM task_history_old
    """)

    cursor.execute("DROP TABLE task_history_old;")
    cursor.execute("COMMIT;")
    cursor.execute("PRAGMA foreign_keys=on;")
    conn.close()


if __name__ == "__main__":
    migrate()
