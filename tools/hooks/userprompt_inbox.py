#!/usr/bin/env python3
"""UserPromptSubmit hook: deliver inter-session messages from inbox/messages/.

Concurrent Claude sessions (host and sandbox) leave messages for each
other as <workspace>/inbox/messages/<from>-to-<to>_<timestamp>.md.
This hook runs on every user prompt, and injects any message this
session hasn't seen yet into context — so delivery is automatic and
nobody has to relay or be told to "check the inbox".

Addressing (most specific wins):
  - By session name: a `To-Name: <name>` line delivers only to the session a
    user named with /rename (matched against this session's own name, looked
    up in ~/.claude/sessions/). Lets a user say "message the 'CGU pipeline'
    session".
  - By session id: a `To-Session: <id-or-prefix>` line delivers only to the
    session whose id matches (prefix match, since ids are truncated).
  - By environment (filename): to = host | sandbox | all — any session of that
    env. Files that don't match the naming pattern are delivered everywhere.

A non-matching session skips a targeted message AND does not mark it seen, so
the intended session still receives it. The RECEIVING session deletes a file
once acted on. Delivered filenames are tracked per session in ~/.claude/state/
so a message is injected at most once per session. Fails open on any error.
"""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import presence
except Exception:  # presence is optional — the inbox works without it
    presence = None
try:
    import peer_turn
except Exception:
    peer_turn = None

MAX_FILES = 3
MAX_BYTES = 12000   # per message; over this, deliver the head + a pointer to the file
WAKE_SENTINEL = "[peer-wake]"   # inbox_waker.py types this; not a human prompt
NAME_RE = re.compile(r"^(?P<frm>[^_]+)-to-(?P<to>[A-Za-z]+)_.*\.md$")
TO_SESSION_RE = re.compile(r"^\s*(?:to-session|target-session|session)\s*:\s*(\S+)",
                           re.IGNORECASE | re.MULTILINE)
TO_NAME_RE = re.compile(r"^\s*to-name\s*:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
FROM_SESSION_RE = re.compile(r"^\s*from-session\s*:\s*(\S+)", re.IGNORECASE | re.MULTILINE)
FROM_NAME_RE = re.compile(r"^\s*from-name\s*:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workspace_root import workspace  # noqa: E402  (one resolver; see its docstring)


def own_name(session_id):
    """This session's /rename name from ~/.claude/sessions/, or None."""
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


def head_match(rx, text):
    m = rx.search(text)
    return m.group(1).strip() if m else None


def addressed_to_me(filename, head, session, here, myname):
    """Does this message target this session? Most specific addressing wins.

    Shared with stop_inbox.py so the drain can never disagree with delivery
    about who a message is for.
    """
    to_name = head_match(TO_NAME_RE, head)
    to_session = head_match(TO_SESSION_RE, head)
    if to_name is not None:
        return bool(myname and myname.strip().lower() == to_name.lower())
    if to_session is not None:
        return (session == to_session or session.startswith(to_session)
                or to_session.lower() in (here, "all", "any"))
    m = NAME_RE.match(filename)
    if not m:
        return True
    return m.group("to").lower() in (here, "all", "any")


def main() -> None:
    data = json.load(sys.stdin)
    raw_sid = data.get("session_id", "unknown")
    session = re.sub(r"[^A-Za-z0-9-]", "", raw_sid)[:40]
    here = "sandbox" if Path("/workspace").exists() else "host"
    myname = own_name(raw_sid)

    # A human is typing, so whatever peer turn was in flight is over — release
    # the irreversible-action lock this session was holding.
    #
    # Except when the "human" is inbox_waker.py: it wakes an idle session by
    # typing into its tmux pane, which is indistinguishable from a real prompt.
    # Clearing here would let a woken turn escape the lockout entirely — the
    # guard defeated by the wake mechanism. The waker sets the flag before
    # typing and marks the prompt, so a woken turn stays locked down.
    if peer_turn is not None and not (data.get("prompt") or "").lstrip().startswith(WAKE_SENTINEL):
        peer_turn.clear(raw_sid)

    # Heartbeat + roster. Done here rather than as a separate UserPromptSubmit
    # hook so the refresh always precedes the render — two hooks would race and
    # this session could read a roster written before its own heartbeat landed.
    if presence is not None:
        prompt = data.get("prompt")
        focus = " ".join(prompt.split())[:presence.FOCUS_MAX] if prompt else None
        presence.touch(raw_sid, focus=focus, event="UserPromptSubmit")
        peers = presence.roster(raw_sid)
        if peers:
            print("## Live sessions (presence registry)")
            print("Other Claude sessions active in the last 10 minutes. Consult one when it "
                  "owns the area you're working in — `research-kit/tools/send_message.py "
                  '--to-name "<name>"`. Stale entries can linger if a session crashed, so a '
                  "name here is a hint, not a guarantee anyone is listening.")
            for line in peers:
                print(line)
            print()

    msg_dir = workspace() / "inbox" / "messages"
    if not msg_dir.is_dir():
        return
    candidates = sorted(p for p in msg_dir.glob("*.md") if p.is_file())
    if not candidates:
        return

    state_dir = Path.home() / ".claude" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / f"inbox_seen_{session}.json"
    try:
        seen = set(json.loads(state_file.read_text()))
    except Exception:
        seen = set()

    existing = {p.name for p in candidates}
    deliver = []
    for p in candidates:
        if p.name in seen:
            continue
        full = p.read_text(errors="replace")
        # Truncate LOUDLY. Silently cutting at the cap once cost us a design
        # doc: the sender saw "delivered", the reader got a fragment with no
        # sign anything was missing, and the file was deleted on consume.
        if len(full) > MAX_BYTES:
            body = (full[:MAX_BYTES].rstrip()
                    + f"\n\n**[TRUNCATED — {len(full) - MAX_BYTES} of {len(full)} bytes not shown. "
                      f"Read the full message with `Read {p}` before acting on it, "
                      f"and do NOT delete it until you have.]**")
        else:
            body = full
        head = full[:1500]
        # A non-matching session skips the message AND leaves it unseen, so the
        # intended session still receives it.
        if not addressed_to_me(p.name, head, session, here, myname):
            continue
        deliver.append((p, body))

    if not deliver:
        state_file.write_text(json.dumps(sorted(seen & existing)))
        return

    who = f'the **{here}** session' + (f' ("{myname}")' if myname else f", id `{session}`")
    print(f"## Inter-session message(s) in inbox/messages/")
    print(f"You are {who}. "
          f"Host and sandbox share the SAME /workspace filesystem and git repo — "
          f"files another session changed are already on disk for you. Do NOT ask for "
          f"(or perform) a `git pull`, re-clone, or rerun of code that already ran; "
          f"just read the files.")
    print()
    for p, body in deliver[:MAX_FILES]:
        print(f"### {p.name}")
        print(body.rstrip())
        fname = head_match(FROM_NAME_RE, body[:1500])
        fsid = head_match(FROM_SESSION_RE, body[:1500])
        if fname:
            print(f"\n_↩ to reply, run `research-kit/tools/send_message.py "
                  f'--to-name "{fname}"`._')
        elif fsid:
            print(f"\n_↩ to reply, run `research-kit/tools/send_message.py "
                  f"--to-session {fsid}`._")
        print()
        seen.add(p.name)
    if len(deliver) > MAX_FILES:
        print(f"...and {len(deliver) - MAX_FILES} more message file(s) — read them directly.")
    print(
        "Act ONLY on messages relevant to your current work. If a message is clearly "
        "for a different task or session, do not act on it and do NOT delete it — leave "
        "it for the intended session. Delete (with `rm`) only the messages you actually "
        "consumed; they are git-ignored plain files. If you are the author, ignore it. "
        "Send messages with `research-kit/tools/send_message.py` (address by `--to-name`, "
        "`--to-session`, or `--to host|sandbox`); it stamps your id/name so replies route back."
    )
    state_file.write_text(json.dumps(sorted(seen & existing)))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
