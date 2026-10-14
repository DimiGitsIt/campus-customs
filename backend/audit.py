"""Append-only audit trail for agent/tool/delegation activity.

Writes JSON objects to output/audit_trail.json as a JSON array. A simple
lock-file (atomic create/delete) around the read-modify-write keeps
concurrent writers from corrupting the file; writes land via an atomic
rename so a crash mid-write can't truncate prior entries.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
AUDIT_PATH = ROOT / "output" / "audit_trail.json"
LOCK_PATH = ROOT / "output" / "audit_trail.json.lock"

_SECRET_MARKERS = ("api_key", "apikey", "password", "secret", "token", "portkey")
_MAX_LEN = 400


def _redact_and_truncate(value: Any) -> Any:
    if value is None:
        return None
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    lowered = text.lower()
    for marker in _SECRET_MARKERS:
        if marker in lowered:
            return "[redacted]"
    if len(text) > _MAX_LEN:
        return text[:_MAX_LEN] + "...[truncated]"
    return text


def _acquire_lock(timeout: float = 5.0) -> None:
    start = time.time()
    while True:
        try:
            fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            return
        except FileExistsError:
            if time.time() - start > timeout:
                # Stale lock protection: break it rather than hang forever.
                try:
                    LOCK_PATH.unlink()
                except FileNotFoundError:
                    pass
                continue
            time.sleep(0.05)


def _release_lock() -> None:
    try:
        LOCK_PATH.unlink()
    except FileNotFoundError:
        pass


def append_audit_entry(
    ticket_id: int | None,
    agent_name: str,
    step_type: str,
    tool_name: str | None = None,
    args_summary: Any = None,
    result_summary: Any = None,
    usage: Any = None,
    stop_reason: str | None = None,
) -> None:
    """Append one audit entry. step_type in {'model_call','tool_call','delegation','final_result'}."""
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ticket_id": ticket_id,
        "agent": agent_name,
        "step_type": step_type,
        "tool_name": tool_name,
        "args_summary": _redact_and_truncate(args_summary),
        "result_summary": _redact_and_truncate(result_summary),
        "usage": _usage_to_dict(usage),
        "stop_reason": stop_reason,
    }

    _acquire_lock()
    try:
        if AUDIT_PATH.exists() and AUDIT_PATH.stat().st_size > 0:
            try:
                data = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
                if not isinstance(data, list):
                    data = []
            except json.JSONDecodeError:
                data = []
        else:
            data = []

        data.append(entry)

        tmp_path = AUDIT_PATH.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(tmp_path, AUDIT_PATH)
    finally:
        _release_lock()


def _usage_to_dict(usage: Any) -> dict | None:
    if usage is None:
        return None
    if isinstance(usage, dict):
        return usage
    for attr in ("requests", "request_tokens", "response_tokens", "total_tokens"):
        if hasattr(usage, attr):
            return {a: getattr(usage, a, None) for a in ("requests", "request_tokens", "response_tokens", "total_tokens")}
    return {"repr": str(usage)[:_MAX_LEN]}
