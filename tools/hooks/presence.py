#!/usr/bin/env python3
"""Presence registry: which Claude sessions are live, and what they're doing.

Each session heartbeats <workspace>/inbox/presence/<name>_<sid8>.json. The
roster is injected into every prompt by userprompt_inbox.py, so a session can
see who else is working and pick whom to consult without being told.

Runs as a hook for SessionStart / Stop / SessionEnd (upsert, upsert, remove).
UserPromptSubmit does NOT register it separately — userprompt_inbox.py imports
touch() and calls it inline, so the roster it renders always includes this
session's own fresh heartbeat regardless of hook ordering.

Presence is a courtesy signal, not a lock: a crashed session leaves a stale
file, which ages out of the roster after STALE_SECS and is reaped after
REAP_SECS. Nothing depends on it for correctness. Prints nothing on any path
(a UserPromptSubmit hook's stdout is injected into context) and fails open.
"""
import json
import os
import re
import sys
import time
from pathlib import Path

STALE_SECS = 600      # older than this → not shown in the roster
REAP_SECS = 86400     # older than this → file deleted
FOCUS_MAX = 120       # one-line focus, truncated


def workspace() -> Path:
    env = os.environ.get("RESEARCH_WORKSPACE")
    if env:
        return Path(env)
    for cand in (Path.home() / "research", Path("/workspace")):
        if (cand / "research-kit").exists():
            return cand
    return Path.home() / "research"


def own_name(session_id):
    """This session's /rename name from ~/.claude/sessions/, or None.

    Mirrors userprompt_inbox.own_name; duplicated rather than shared because
    these run as standalone scripts under run_hook.sh, not as a package.
    """
    best = None
    try:
        files = list((Path.home() / ".claude" / "sessions").glob("*.json"))
    except Exception:
        return None
    for f in files:
        try:
            s = json.loads(f.read_text())
        except Exception:
            continue
        if s.get("sessionId") == session_id and s.get("name"):
            if best is None or s.get("updatedAt", 0) > best[0]:
                best = (s.get("updatedAt", 0), s["name"])
    return best[1] if best else None


def _slug(text, fallback="session"):
    s = re.sub(r"[^A-Za-z0-9._-]+", "-", (text or "").strip()).strip("-")
    return s[:40] or fallback


def presence_dir() -> Path:
    return workspace() / "inbox" / "presence"


def _path_for(session_id, name):
    return presence_dir() / f"{_slug(name, 'unnamed')}_{_slug(session_id)[:8]}.json"


def _reap(pdir, now):
    """Delete records nothing will ever refresh (crashed/killed sessions)."""
    for p in pdir.glob("*.json"):
        try:
            if now - json.loads(p.read_text()).get("last_seen", 0) > REAP_SECS:
                p.unlink()
        except Exception:
            continue


def touch(session_id, *, focus=None, event=None):
    """Upsert this session's heartbeat. Never raises."""
    try:
        now = int(time.time())
        name = own_name(session_id)
        pdir = presence_dir()
        pdir.mkdir(parents=True, exist_ok=True)
        path = _path_for(session_id, name)

        prev = {}
        try:
            prev = json.loads(path.read_text())
        except Exception:
            pass
        # A session named after launch keeps its old file under the old slug;
        # drop it so the roster doesn't show the same session twice.
        for stale in pdir.glob(f"*_{_slug(session_id)[:8]}.json"):
            if stale != path:
                try:
                    if not prev:
                        prev = json.loads(stale.read_text())
                    stale.unlink()
                except Exception:
                    pass

        rec = {
            "name": name or prev.get("name"),
            "session_id": session_id,
            "env": "sandbox" if Path("/workspace").exists() else "host",
            "cwd": str(Path.cwd()),
            # The tmux pane is how inbox_waker.py reaches an idle session: the
            # pane's stdin IS the containerized claude's stdin, so send-keys
            # crosses the container boundary that breaks socket messaging.
            "tmux_pane": os.environ.get("TMUX_PANE") or prev.get("tmux_pane"),
            "started": prev.get("started", now),
            "last_seen": now,
            # Keep the last known focus when the event carries none (Stop,
            # SessionStart) so the roster doesn't blank out between prompts.
            "focus": (focus or prev.get("focus") or "")[:FOCUS_MAX],
            "event": event or prev.get("event"),
        }
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(rec))
        tmp.replace(path)  # atomic: concurrent readers never see a partial file
        _reap(pdir, now)
    except Exception:
        pass


def remove(session_id):
    try:
        for p in presence_dir().glob(f"*_{_slug(session_id)[:8]}.json"):
            p.unlink()
    except Exception:
        pass


def roster(session_id, *, stale=STALE_SECS):
    """Live peers as display lines, excluding this session. [] on any error."""
    out = []
    try:
        now = time.time()
        for p in sorted(presence_dir().glob("*.json")):
            try:
                r = json.loads(p.read_text())
            except Exception:
                continue
            if r.get("session_id") == session_id:
                continue
            age = now - r.get("last_seen", 0)
            if age > stale:
                continue
            name = r.get("name") or f"(unnamed {str(r.get('session_id'))[:8]})"
            mins = int(age // 60)
            when = "active now" if mins < 1 else f"{mins}m idle"
            line = f"- **{name}** ({r.get('env', '?')}, {when})"
            try:
                line += f" — cwd `{Path(r['cwd']).name}`"
            except Exception:
                pass
            if r.get("focus"):
                line += f"; {r['focus']}"
            out.append(line)
    except Exception:
        return []
    return out


def main():
    data = json.load(sys.stdin)
    sid = data.get("session_id", "unknown")
    event = data.get("hook_event_name") or ""
    if event == "SessionEnd":
        remove(sid)
    else:
        prompt = data.get("prompt") if event == "UserPromptSubmit" else None
        focus = " ".join(prompt.split())[:FOCUS_MAX] if prompt else None
        touch(sid, focus=focus, event=event)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
