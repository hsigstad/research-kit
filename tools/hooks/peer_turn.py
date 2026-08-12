#!/usr/bin/env python3
"""Peer-turn state: is this session currently acting on a peer's message?

Set by stop_inbox.py when it drains peer messages at turn end; cleared on the
next genuine human prompt, or by TTL. Read by pretool_irreversible_guard.py,
which refuses the manual override during a peer turn, and by send_message.py,
which stamps hop/thread headers so A<->B exchanges terminate.

TTL matters: clearing only on the next human UserPromptSubmit would latch an
always-on session (Saga can go days without one) into peer-turn mode forever.
"""
import json
import os
import re
import time
from pathlib import Path

TTL_SECS = 1800  # 30min — a peer turn that outlives this was abandoned


def _dir() -> Path:
    d = Path.home() / ".claude" / "state"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _path(session_id) -> Path:
    return _dir() / f"peer_turn_{re.sub(r'[^A-Za-z0-9-]', '', str(session_id))[:40]}.json"


def begin(session_id, *, origin, hop=0, thread=None):
    """Mark this session as acting on a peer message. Never raises."""
    try:
        _path(session_id).write_text(json.dumps({
            "origin": origin,          # filename of the draining message
            "hop": int(hop),
            "thread": thread or origin,
            "started": int(time.time()),
        }))
    except Exception:
        pass


def read(session_id):
    """Active peer-turn record, or None (expired records are cleared)."""
    try:
        p = _path(session_id)
        rec = json.loads(p.read_text())
        if time.time() - rec.get("started", 0) > TTL_SECS:
            p.unlink(missing_ok=True)
            return None
        return rec
    except Exception:
        return None


def clear(session_id):
    try:
        _path(session_id).unlink(missing_ok=True)
    except Exception:
        pass


def current():
    """Peer-turn record for the session this process belongs to, or None.

    Hooks receive session_id on stdin, but plain tools (send_message.py) do not,
    so fall back to the env var the CLI exports.
    """
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID")
    return read(sid) if sid else None
