#!/usr/bin/env python3
"""Retire inbox messages nobody is ever going to read, and tell the sender.

The gap this closes: inbox_waker.py stops trying to wake a target after
STALE_SECS (1h) and presence.py reaps the target's record after REAP_SECS (24h),
but the MESSAGE FILE is never expired. Nothing anywhere reports the failure, so
a sender sees silence that is indistinguishable from "received and ignored".

Found 2026-08-31: 28 of 29 files in inbox/messages/ were addressed to session
ids that no longer existed, the oldest 32 days old, and one had been sent that
morning to a session already 17h idle -- past STALE, so it was undeliverable the
moment it was written. Its sender went on believing it had landed. Closes that
incident per rules/incident_to_check.md.

What it does NOT do: decide whether a session is "dead". It cannot -- ~/.claude
keeps 167 resumable sandbox transcripts, so any session might come back, and a
To-Name message is addressed to a name a future /rename could reuse. So the test
here is not "is the recipient alive" but the purely operational "has this file
sat undelivered past the grace period". Generous grace, reversible outcome:
files MOVE to inbox/dead/, they are never deleted.

Bounces go only to senders currently in presence, and never to a bounce (see
X-Bounce) -- otherwise a dead sender's bounce becomes the next orphan.

Usage:
    inbox_reaper.py --dry-run          # report, touch nothing (do this first)
    inbox_reaper.py                    # reap, honouring the once-an-hour stamp
    inbox_reaper.py --force            # ignore the stamp
    inbox_reaper.py --grace-days 14    # override the default 7
"""
import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "hooks"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import userprompt_inbox as inbox  # noqa: E402  (addressing logic; never duplicate it)

GRACE_DAYS = 7          # undelivered this long → retire. Deliberately generous.
BOUNCE_MAX_IDLE = 86400  # only tell a sender seen within a day; else just log
RUN_EVERY = 3600        # self-throttle, so the every-minute waker can call this
X_BOUNCE = "X-Bounce: 1"


def state_dir() -> Path:
    d = Path.home() / ".claude" / "state"
    d.mkdir(parents=True, exist_ok=True)
    return d


def delivered_filenames() -> set:
    """Every message filename any session has been shown, from the seen-lists.

    One pass over ~/.claude/state/inbox_seen_*.json (118 of them today), unioned
    into a set, so classification below is a membership test rather than a
    per-message rescan.
    """
    out = set()
    for p in state_dir().glob("inbox_seen_*.json"):
        try:
            out.update(json.loads(p.read_text()))
        except Exception:
            continue
    return out


def presence_by(ws: Path):
    """(by_session_id, by_lowercased_name) for records that still exist."""
    by_sid, by_name = {}, {}
    for p in (ws / "inbox" / "presence").glob("*.json"):
        try:
            r = json.loads(p.read_text())
        except Exception:
            continue
        if r.get("session_id"):
            by_sid[r["session_id"]] = r
        if r.get("name"):
            by_name[r["name"].strip().lower()] = r
    return by_sid, by_name


def header(head: str, regex) -> str | None:
    m = regex.search(head)
    return m.group(1).strip() if m else None


def bounce(ws, msg_name, reason, sender, orig_subject) -> Path | None:
    """Write a bounce addressed back to the sender. Never bounces a bounce."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    env = "host" if sender.get("env") == "host" else "sandbox"
    path = ws / "inbox" / "messages" / f"reaper-to-{env}_{stamp}_{msg_name[:20]}.md"
    lines = [
        "From-Session: inbox_reaper",
        "From-Name: inbox-reaper",
        f"To-Session: {sender['session_id']}",
        X_BOUNCE,
        "",
        f"# UNDELIVERED: your message `{msg_name}` was never read",
        "",
        f"Subject was: {orig_subject or '(none)'}",
        "",
        f"{reason} It has been moved to `inbox/dead/{msg_name}` (not deleted) "
        f"after {GRACE_DAYS} days.",
        "",
        "Treat anything you asked for in it as NOT done. If it still matters, "
        "either make the change durable yourself (edit the file / rule directly) "
        "or re-send to a session you can see in the presence roster.",
        "",
        "-- inbox_reaper.py",
    ]
    path.write_text("\n".join(lines))
    return path


def classify(head, fname, delivered, by_sid, by_name):
    """(status, detail) for one message. Pure — no side effects."""
    if X_BOUNCE.split(":")[0].lower() in head.lower():
        return "bounce", "a bounce; retiring quietly"
    if fname in delivered:
        return "consumed", "was delivered; recipient never rm'd it"
    to_session = header(head, inbox.TO_SESSION_RE)
    to_name = header(head, inbox.TO_NAME_RE)
    if to_name:
        alive = by_name.get(to_name.lower())
        return "undelivered", (
            f"addressed To-Name '{to_name}', which "
            + ("has a presence record but never read it"
               if alive else "matches no session in the presence registry"))
    if to_session:
        alive = any(s == to_session or s.startswith(to_session) for s in by_sid)
        return "undelivered", (
            f"addressed To-Session {to_session[:8]}, which "
            + ("is still in presence but never read it"
               if alive else "no longer exists"))
    return "undelivered", "broadcast; no session ever read it"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="report only; move nothing")
    ap.add_argument("--force", action="store_true", help="ignore the once-an-hour stamp")
    ap.add_argument("--grace-days", type=float, default=GRACE_DAYS)
    args = ap.parse_args()

    stamp = state_dir() / "reaper.last"
    now = time.time()
    if not args.force and not args.dry_run:
        try:
            if now - float(stamp.read_text().strip()) < RUN_EVERY:
                return 0
        except Exception:
            pass

    ws = inbox.workspace()
    msg_dir = ws / "inbox" / "messages"
    if not msg_dir.is_dir():
        print(f"inbox_reaper: no inbox at {ws}", file=sys.stderr)
        return 0
    dead_dir = ws / "inbox" / "dead"

    delivered = delivered_filenames()
    by_sid, by_name = presence_by(ws)
    cutoff = args.grace_days * 86400

    reaped = bounced = 0
    for p in sorted(msg_dir.glob("*.md")):
        try:
            age = now - p.stat().st_mtime
        except Exception:
            continue
        if age < cutoff:
            continue
        try:
            head = p.read_text(errors="replace")
        except Exception:
            continue

        status, detail = classify(head, p.name, delivered, by_sid, by_name)
        days = age / 86400
        print(f"{'would reap' if args.dry_run else 'reap'} {p.name} "
              f"({days:.1f}d, {status}: {detail})")
        if args.dry_run:
            reaped += 1
            continue

        dead_dir.mkdir(parents=True, exist_ok=True)
        try:
            p.replace(dead_dir / p.name)
        except Exception as e:
            print(f"  move FAILED: {e}", file=sys.stderr)
            continue
        reaped += 1

        try:
            (dead_dir / "REAPED.jsonl").open("a").write(json.dumps({
                "file": p.name, "reaped_at": int(now),
                "age_days": round(days, 1), "status": status, "detail": detail,
            }) + "\n")
        except Exception:
            pass

        # Tell the sender, but only one that is around to read it.
        if status != "undelivered":
            continue
        frm = header(head, inbox.FROM_SESSION_RE)
        sender = by_sid.get(frm) if frm else None
        if not sender or now - sender.get("last_seen", 0) > BOUNCE_MAX_IDLE:
            continue
        subj = next((ln.lstrip("# ").strip() for ln in head.splitlines()
                     if ln.startswith("# ")), None)
        try:
            if bounce(ws, p.name, detail.capitalize() + ".", sender, subj):
                bounced += 1
                print(f"  bounced to {sender.get('name') or frm[:8]}")
        except Exception as e:
            print(f"  bounce FAILED: {e}", file=sys.stderr)

    if not args.dry_run:
        try:
            stamp.write_text(str(int(now)))
        except Exception:
            pass
    if reaped:
        print(f"inbox_reaper: {reaped} retired, {bounced} bounced")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"inbox_reaper: {e}", file=sys.stderr)
        sys.exit(0)
