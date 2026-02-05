#!/usr/bin/env python3
"""
AI Team Log Bridge
Parse agent output logs and update task progress/completion in team.db.
"""

import argparse
import json
import re
import sqlite3
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import agent_reporter

DB_PATH = Path(__file__).parent / "team.db"
LOG_DIR = Path(__file__).parent / "logs"
STATE_PATH = LOG_DIR / "log_bridge_state.json"

PROGRESS_RE = re.compile(r"progress\s*[:=]?\s*(\d{1,3})\s*%", re.IGNORECASE)
TASK_ID_RE = re.compile(r"(T-\d{8}-[A-Za-z0-9]+)")
COMPLETE_RE = re.compile(r"\btask\s+completed\b", re.IGNORECASE)
STATUS_COMPLETE_RE = re.compile(r"\bstatus\s*[:=]\s*completed\b", re.IGNORECASE)


def load_state() -> Dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text())
        except Exception:
            pass
    return {"file_offsets": {}, "task_progress": {}}


def save_state(state: Dict) -> None:
    tmp = STATE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2))
    tmp.replace(STATE_PATH)


def iter_log_files() -> Iterable[Path]:
    if not LOG_DIR.exists():
        return []
    patterns = ["spawn_T-*.log", "auto_assign_T-*.log"]
    files: List[Path] = []
    for pattern in patterns:
        files.extend(sorted(LOG_DIR.glob(pattern)))
    return files


def task_id_from_filename(path: Path) -> Optional[str]:
    m = TASK_ID_RE.search(path.name)
    return m.group(1) if m else None


def read_new_lines(path: Path, offset: int) -> Tuple[int, List[str]]:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        if offset > 0:
            f.seek(offset)
        data = f.read()
        new_offset = f.tell()
    lines = data.splitlines()
    return new_offset, lines


def get_task_info(task_id: str) -> Optional[Tuple[str, str, int]]:
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute(
        "SELECT assignee_id, status, COALESCE(progress, 0) FROM tasks WHERE id = ?",
        (task_id,),
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return row[0], row[1], int(row[2] or 0)


def detect_progress(line: str) -> Optional[int]:
    m = PROGRESS_RE.search(line)
    if not m:
        return None
    try:
        pct = int(m.group(1))
        return max(0, min(100, pct))
    except ValueError:
        return None


def detect_complete(line: str) -> bool:
    if "✅" in line and "Task" in line:
        return True
    if COMPLETE_RE.search(line):
        return True
    if STATUS_COMPLETE_RE.search(line):
        return True
    return False


def extract_task_id(line: str, default_task_id: Optional[str]) -> Optional[str]:
    m = TASK_ID_RE.search(line)
    if m:
        return m.group(1)
    return default_task_id


def handle_progress(task_id: str, pct: int, message: str, state: Dict, verbose: bool) -> None:
    info = get_task_info(task_id)
    if not info:
        return
    assignee_id, status, current = info
    if status in ("review", "done", "cancelled"):
        return
    last_seen = int(state["task_progress"].get(task_id, current))
    if pct <= max(current, last_seen):
        return
    if verbose:
        print(f"Progress: {task_id} -> {pct}%")
    agent_reporter.report_progress(task_id, pct, message)
    state["task_progress"][task_id] = pct


def handle_complete(task_id: str, message: str, verbose: bool) -> None:
    info = get_task_info(task_id)
    if not info:
        return
    assignee_id, status, _ = info
    if status in ("review", "done", "cancelled"):
        return
    if not assignee_id:
        return
    if verbose:
        print(f"Complete: {task_id} (agent {assignee_id})")
    agent_reporter.report_complete(assignee_id, task_id, message)


def process_logs(dry_run: bool = False, verbose: bool = False) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    state = load_state()
    file_offsets = state.get("file_offsets", {})

    for path in iter_log_files():
        task_id = task_id_from_filename(path)
        if not task_id:
            continue

        prev_offset = int(file_offsets.get(str(path), 0))
        if path.stat().st_size < prev_offset:
            prev_offset = 0

        new_offset, lines = read_new_lines(path, prev_offset)
        if not lines:
            file_offsets[str(path)] = new_offset
            continue

        for line in lines:
            line = line.strip()
            if not line:
                continue

            line_task_id = extract_task_id(line, task_id)
            if not line_task_id:
                continue

            pct = detect_progress(line)
            if pct is not None:
                if not dry_run:
                    handle_progress(line_task_id, pct, line, state, verbose)
                continue

            if detect_complete(line):
                if not dry_run:
                    handle_complete(line_task_id, line, verbose)

        file_offsets[str(path)] = new_offset

    state["file_offsets"] = file_offsets
    if not dry_run:
        save_state(state)


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Team Log Bridge")
    parser.add_argument("--dry-run", action="store_true", help="Parse logs but do not update DB")
    parser.add_argument("--verbose", action="store_true", help="Print detected events")
    args = parser.parse_args()

    process_logs(dry_run=args.dry_run, verbose=args.verbose)


if __name__ == "__main__":
    main()
