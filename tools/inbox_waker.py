#!/usr/bin/env python3
"""Wake an idle Claude session that has inbox mail waiting.

The gap this closes: stop_inbox.py hands messages to a session that is still
awake, but a session sitting at its prompt runs nothing, so no hook can fire and
a message waits for a human. This is the only part of the design that needs a
push from outside the session.

Mechanism: tmux. Each `cs` is its own container — which is what breaks socket-
based native messaging — but the pane's stdin IS the containerized claude's
stdin, so `tmux send-keys` reaches inside. presence.py records $TMUX_PANE, which
gives us the session -> pane map.

The waker carries NO message content. It types a sentinel prompt; the ordinary
UserPromptSubmit hook then delivers the mail with the addressing, dedup and
truncation logic already used everywhere else.

Runs on the HOST (tmux lives there), from cron, like the Saga watchdog:
    * * * * * /projects/.../research-kit/tools/inbox_waker.py >> ~/.claude/state/waker.log 2>&1

Cron exports no environment, so the workspace is resolved by tools/workspace_root.py
(self-locating) — never from RESEARCH_WORKSPACE, which only hooks receive. Health is
reported in ~/.claude/state/waker.heartbeat as JSON: see heartbeat(). Two signals here
are known liars, both learned from the 2026-08-13 outage — waker.log is silent on
no-op runs, and a bare heartbeat timestamp says only that cron fired. The tell for
"has this EVER woken anyone" is whether any ~/.claude/state/wake_*.json exists.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "hooks"))
import peer_turn
import userprompt_inbox as inbox

SENTINEL = "[peer-wake] check your inbox"
ACTIVE_SECS = 120      # seen more recently than this → awake; stop_inbox has it
STALE_SECS = 3600      # not seen in an hour → probably dead, don't type at it
MAX_WAKES_PER_WINDOW = 6
WINDOW_SECS = 3600
OK_PANE_CMDS = {"claude", "apptainer", "singularity", "node", "bun"}


def state_dir() -> Path:
    d = Path.home() / ".claude" / "state"
    d.mkdir(parents=True, exist_ok=True)
    return d


def panes():
    """{pane_id: current_command} for every pane on this host, or {}."""
    try:
        out = subprocess.run(
            ["tmux", "list-panes", "-a", "-F", "#{pane_id}\t#{pane_current_command}"],
            capture_output=True, text=True, timeout=10)
        if out.returncode != 0:
            return {}
        return dict(
            line.split("\t", 1) for line in out.stdout.splitlines() if "\t" in line)
    except Exception:
        return {}


def heartbeat(ws, inbox_ok, n_panes):
    """Report whether a wake COULD land, not merely that cron fired.

    Contract agreed with Saga's meta/health_check.py (2026-08-13):
        {"ts": <int epoch>, "workspace": "<resolved root>", "inbox_ok": <bool>}
    `panes` is extra — tmux being unreachable is the other way a wake cannot land,
    and only this process can see it (the sandbox has no tmux).

    A bare timestamp was the false-green that hid a day-long outage: it was written
    before workspace resolution, so it ticked happily while the waker was resolving
    a root with no inbox/ and waking nobody. Never fatal.
    """
    try:
        (state_dir() / "waker.heartbeat").write_text(json.dumps({
            "ts": int(time.time()),
            "workspace": str(ws),
            "inbox_ok": bool(inbox_ok),
            "panes": int(n_panes),
        }))
    except Exception:
        pass


def complain(msg, *, every=3600):
    """Log a misconfiguration at most once per `every` seconds. Cron runs this
    every minute, so an unthrottled complaint would bury waker.log."""
    stamp = state_dir() / "waker_complaint.json"
    now = int(time.time())
    try:
        rec = json.loads(stamp.read_text())
    except Exception:
        rec = {}
    if rec.get("msg") == msg and now - rec.get("at", 0) < every:
        return
    print(f"inbox_waker: {msg}", file=sys.stderr)
    try:
        stamp.write_text(json.dumps({"msg": msg, "at": now}))
    except Exception:
        pass


def wake_budget_ok(sid, *, commit=True):
    """Rate-limit wakes per target. Every wake costs a paid turn."""
    p = state_dir() / f"wake_{re.sub(r'[^A-Za-z0-9-]', '', sid)[:40]}.json"
    now = int(time.time())
    try:
        rec = json.loads(p.read_text())
    except Exception:
        rec = {}
    if now - rec.get("window_start", 0) > WINDOW_SECS:
        rec = {"window_start": now, "count": 0}
    if rec.get("count", 0) >= MAX_WAKES_PER_WINDOW:
        return False
    if commit:
        rec["count"] = rec.get("count", 0) + 1
        try:
            p.write_text(json.dumps(rec))
        except Exception:
            pass
    return True


def unread_for(sid, name, env, msg_dir):
    """Messages addressed to this session that it has not been shown."""
    session = re.sub(r"[^A-Za-z0-9-]", "", sid)[:40]
    try:
        seen = set(json.loads((state_dir() / f"inbox_seen_{session}.json").read_text()))
    except Exception:
        seen = set()
    out = []
    for p in sorted(msg_dir.glob("*.md")):
        if p.name in seen:
            continue
        try:
            head = p.read_text(errors="replace")[:1500]
        except Exception:
            continue
        if inbox.addressed_to_me(p.name, head, session, env, name):
            out.append(p)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would be woken; type nothing")
    args = ap.parse_args()

    # Resolve everything a wake DEPENDS on before reporting health, so the heartbeat can
    # answer "could a wake land?" rather than only "did cron fire?".
    ws = inbox.workspace()
    msg_dir = ws / "inbox" / "messages"
    pdir = ws / "inbox" / "presence"
    inbox_ok = msg_dir.is_dir() and pdir.is_dir()
    live_panes = panes()
    heartbeat(ws, inbox_ok, len(live_panes))

    if not inbox_ok:
        # Resolving a workspace with no inbox/ means the waker is running but can
        # never wake anyone. It did exactly that for a day, silently, because
        # this returned 0 like an ordinary no-op. Say so — hourly, not 1440x/day.
        complain(f"no inbox at {ws} — resolved the wrong workspace root; "
                 f"RESEARCH_WORKSPACE={os.environ.get('RESEARCH_WORKSPACE') or '(unset)'}")
        return 0

    # Retire messages nobody will read. Piggy-backs on this cron entry rather than
    # taking its own — the crontab is a known-fragile surface (brain-up.sh ate the
    # waker block once). inbox_reaper self-throttles to hourly, so calling it every
    # minute is a stat() on a stamp file. Never let it break waking.
    try:
        subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "inbox_reaper.py")],
                       capture_output=False, timeout=60)
    except Exception as e:
        print(f"inbox_reaper failed (waking continues): {e}", file=sys.stderr)

    if not live_panes:
        return 0  # no tmux here; nothing to wake

    now = time.time()
    woke = 0
    for rec_path in sorted(pdir.glob("*.json")):
        try:
            rec = json.loads(rec_path.read_text())
        except Exception:
            continue
        sid = rec.get("session_id")
        pane = rec.get("tmux_pane")
        age = now - rec.get("last_seen", 0)
        if not sid or not pane:
            continue
        if age < ACTIVE_SECS:
            continue          # awake — stop_inbox.py will drain it
        if age > STALE_SECS:
            continue          # long gone; typing at it would hit whatever took the pane
        if live_panes.get(pane, "").lower() not in OK_PANE_CMDS:
            continue          # pane is gone or now a shell — never type into it

        pending = unread_for(sid, rec.get("name"), rec.get("env", "host"), msg_dir)
        if not pending:
            continue
        if not wake_budget_ok(sid, commit=not args.dry_run):
            print(f"skip {rec.get('name') or sid}: wake budget "
                  f"{MAX_WAKES_PER_WINDOW}/h exhausted ({len(pending)} waiting)")
            continue

        who = rec.get("name") or sid[:8]
        if args.dry_run:
            print(f"would wake {who} at {pane} ({len(pending)} msg, idle {int(age)}s)")
            continue

        # Set the flag BEFORE typing. A typed prompt is indistinguishable from a
        # human one, so without this the woken turn would clear the lock and run
        # unattended with full irreversible rights.
        peer_turn.begin(sid, origin=pending[0].name, hop=0, thread=pending[0].name)
        try:
            subprocess.run(["tmux", "send-keys", "-t", pane, "-l", SENTINEL],
                           check=True, timeout=10)
            subprocess.run(["tmux", "send-keys", "-t", pane, "Enter"],
                           check=True, timeout=10)
        except Exception as e:
            peer_turn.clear(sid)
            print(f"wake FAILED {who} at {pane}: {e}")
            continue
        woke += 1
        print(f"woke {who} at {pane} ({len(pending)} msg, idle {int(age)}s)")

    return 0 if woke or True else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"inbox_waker: {e}", file=sys.stderr)
        sys.exit(0)
