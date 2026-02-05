#!/usr/bin/env python3
"""
Agent runtime adapter.
Supports multiple execution backends (OpenClaw, Claude Code) behind one API.
"""

import json
import os
import shlex
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

OPENCLAW_STATE_DIR = Path.home() / ".openclaw"
RUNTIME_OVERRIDE_PATH = Path(__file__).with_name("runtime.override")


def get_runtime() -> str:
    """Current agent runtime backend."""
    override = None
    try:
        if RUNTIME_OVERRIDE_PATH.exists():
            override = RUNTIME_OVERRIDE_PATH.read_text(encoding="utf-8").strip().lower()
    except Exception:
        override = None

    runtime = (override or os.getenv("AI_TEAM_AGENT_RUNTIME", "openclaw")).strip().lower()
    if runtime not in {"openclaw", "claude_code"}:
        return "openclaw"
    return runtime


def runtime_supports_sessions() -> bool:
    """Whether runtime has queryable session metadata."""
    return get_runtime() == "openclaw"


def get_active_sessions(active_minutes: int = 60) -> Dict[str, datetime]:
    """
    Return active sessions keyed by agent_id.
    Only OpenClaw currently supports this query.
    """
    if get_runtime() != "openclaw":
        return {}

    try:
        result = subprocess.run(
            ["openclaw", "sessions", "--active", str(active_minutes), "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return {}
        data = json.loads(result.stdout or "{}")
        active = {}
        for session in data.get("sessions", []):
            session_key = session.get("key", "")
            parts = session_key.split(":")
            if len(parts) >= 2 and parts[0] == "agent":
                active[parts[1]] = datetime.now()
        return active
    except Exception:
        return {}


def get_openclaw_session_last_seen(agent_id: str) -> Optional[datetime]:
    """Get latest OpenClaw session timestamp for an agent."""
    path = OPENCLAW_STATE_DIR / "agents" / agent_id / "sessions" / "sessions.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except Exception:
        return None
    sessions = data.get("sessions", [])
    latest_ms = 0
    for sess in sessions:
        updated = sess.get("updatedAt") or sess.get("updated_at") or 0
        try:
            updated = int(updated)
        except Exception:
            updated = 0
        if updated > latest_ms:
            latest_ms = updated
    if latest_ms <= 0:
        return None
    return datetime.fromtimestamp(latest_ms / 1000)


def _build_spawn_request(message: str, label: str, working_dir: str, task_id: str, agent_id: str) -> str:
    return f"""[AI-TEAM TASK]
LABEL: {label}
WORKING_DIR: {working_dir}
TASK_ID: {task_id}
AGENT_ID: {agent_id}

{message}
"""


def _resolve_claude_command(agent_id: str, message: str, timeout: int) -> list:
    """
    Resolve Claude Code command.
    - Preferred: AI_TEAM_CLAUDE_CMD_TEMPLATE with placeholders:
      {agent_id} {message} {timeout}
    - Fallback: AI_TEAM_CLAUDE_CMD + standardized flags.
    """
    template = os.getenv("AI_TEAM_CLAUDE_CMD_TEMPLATE", "").strip()
    if template:
        rendered = template.format(agent_id=agent_id, message=message, timeout=timeout)
        return shlex.split(rendered)

    base = os.getenv("AI_TEAM_CLAUDE_CMD", "").strip()
    if not base:
        preferred = "/Users/ngs/.local/bin/claude"
        base = preferred if Path(preferred).exists() else "claude"
    base_cmd = shlex.split(base)
    return base_cmd + ["-p", message]


def _build_spawn_command(runtime: str, agent_id: str, message: str, timeout: int) -> list:
    if runtime == "openclaw":
        return ["openclaw", "agent", "--agent", agent_id, "--message", message, "--timeout", str(timeout)]
    if runtime == "claude_code":
        return _resolve_claude_command(agent_id, message, timeout)
    raise ValueError(f"Unsupported AI_TEAM_AGENT_RUNTIME: {runtime}")


def spawn_agent(
    *,
    agent_id: str,
    task_id: str,
    working_dir: str,
    message: str,
    log_path: Path,
    timeout_seconds: int = 3600,
    label: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Spawn one agent run via selected runtime.
    Returns (ok, reason_or_logpath).
    """
    runtime = get_runtime()
    label = label or f"{agent_id}-{task_id}"
    spawn_request = _build_spawn_request(message, label, working_dir, task_id, agent_id)
    command = _build_spawn_command(runtime, agent_id, spawn_request, timeout_seconds)

    log_path.parent.mkdir(exist_ok=True)
    dry_run = os.getenv("AI_TEAM_RUNTIME_DRY_RUN", "0").strip() == "1"
    env = os.environ.copy()
    env["AI_TEAM_MESSAGE"] = spawn_request
    env["AI_TEAM_AGENT_ID"] = agent_id
    env["AI_TEAM_TASK_ID"] = task_id
    env["AI_TEAM_WORKING_DIR"] = working_dir
    if dry_run:
        log_path.write_text(
            f"[DRY RUN] runtime={runtime}\ncommand={command}\n\n{spawn_request}",
            encoding="utf-8",
        )
        return True, str(log_path)

    try:
        with open(log_path, "w") as logf:
            proc = subprocess.Popen(
                command,
                stdout=logf,
                stderr=logf,
                text=True,
                start_new_session=True,
                env=env,
            )
        time.sleep(1)
        if proc.poll() is not None and proc.returncode != 0:
            return False, f"{runtime} exited {proc.returncode}; see {log_path}"
        return True, str(log_path)
    except Exception as exc:
        return False, str(exc)
