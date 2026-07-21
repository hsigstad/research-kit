#!/usr/bin/env python3
"""UserPromptSubmit hook: deliver inter-session messages from inbox/messages/.

Concurrent Claude sessions (host and sandbox) leave messages for each
other as <workspace>/inbox/messages/<from>-to-<to>_<timestamp>.md.
This hook runs on every user prompt, and injects any message this
session hasn't seen yet into context — so delivery is automatic and
nobody has to relay or be told to "check the inbox".

Addressing has two layers:
  - By environment in the filename: to = host | sandbox | all. Files that
    don't match the naming pattern are delivered everywhere.
  - By session (optional): a `To-Session: <id-or-prefix>` line in the first
    ~20 lines of the message restricts delivery to the one session whose id
    matches (prefix match, since ids are truncated). This overrides the
    env addressing and is how a sender reaches ONE specific session rather
    than every session of a type.

The RECEIVING session deletes a message file once acted on. Delivered
filenames are tracked per session in ~/.claude/state/ so a message is
injected at most once per session. Fails open on any error.
"""
import json
import os
import re
import sys
from pathlib import Path

MAX_FILES = 3
MAX_BYTES = 4000
NAME_RE = re.compile(r"^(?P<frm>[^_]+)-to-(?P<to>[A-Za-z]+)_.*\.md$")
# `To-Session:` / `Session:` / `Target-Session:` header, scanned in the head of the file.
TO_SESSION_RE = re.compile(r"^\s*(?:to-session|target-session|session)\s*:\s*(\S+)",
                           re.IGNORECASE | re.MULTILINE)


def workspace() -> Path:
    env = os.environ.get("RESEARCH_WORKSPACE")
    if env:
        return Path(env)
    for cand in (Path.home() / "research", Path("/workspace")):
        if (cand / "research-kit").exists():
            return cand
    return Path.home() / "research"


def targeted_session(head: str):
    """Return the To-Session target declared in the message head, or None."""
    m = TO_SESSION_RE.search(head)
    return m.group(1).strip() if m else None


def main() -> None:
    data = json.load(sys.stdin)
    session = re.sub(r"[^A-Za-z0-9-]", "", data.get("session_id", "unknown"))[:40]
    here = "sandbox" if Path("/workspace").exists() else "host"

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
        body = p.read_text(errors="replace")[:MAX_BYTES]
        target = targeted_session(body[:1500])
        if target is not None:
            # Session-targeted: deliver only to the matching session (or the
            # broadcast tokens). A non-matching session skips it AND does not
            # mark it seen, so the intended session still receives it.
            if not (session == target or session.startswith(target)
                    or target.lower() in (here, "all", "any")):
                continue
        else:
            m = NAME_RE.match(p.name)
            to = (m.group("to").lower() if m else "all")
            if not (to in (here, "all", "any") or not m):
                continue
        deliver.append((p, body))

    if not deliver:
        state_file.write_text(json.dumps(sorted(seen & existing)))
        return

    print(f"## Inter-session message(s) in inbox/messages/")
    print(f"You are the **{here}** session, id `{session}`. "
          f"Host and sandbox share the SAME /workspace filesystem and git repo — "
          f"files another session changed are already on disk for you. Do NOT ask for "
          f"(or perform) a `git pull`, re-clone, or rerun of code that already ran; "
          f"just read the files. To reach one specific session, a sender can add a "
          f"`To-Session: <id>` line (ids appear in commit trailers).")
    print()
    for p, body in deliver[:MAX_FILES]:
        print(f"### {p.name}")
        print(body.rstrip())
        print()
        seen.add(p.name)
    if len(deliver) > MAX_FILES:
        print(f"...and {len(deliver) - MAX_FILES} more message file(s) — read them directly.")
    print(
        "Act ONLY on messages relevant to your current work. If a message is clearly "
        "for a different task or session, do not act on it and do NOT delete it — leave "
        "it for the intended session. Delete (with `rm`) only the messages you actually "
        "consumed; they are git-ignored plain files. If you are the author, ignore it."
    )
    state_file.write_text(json.dumps(sorted(seen & existing)))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
