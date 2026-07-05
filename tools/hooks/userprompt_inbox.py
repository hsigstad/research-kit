#!/usr/bin/env python3
"""UserPromptSubmit hook: deliver inter-session messages from inbox/messages/.

Concurrent Claude sessions (host and sandbox) leave messages for each
other as <workspace>/inbox/messages/<from>-to-<to>_<timestamp>.md.
This hook runs on every user prompt, and injects any message this
session hasn't seen yet into context — so delivery is automatic and
nobody has to relay or be told to "check the inbox".

Addressing is by environment in the filename: to = host | sandbox | all.
Files that don't match the naming pattern are delivered everywhere.
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


def workspace() -> Path:
    env = os.environ.get("RESEARCH_WORKSPACE")
    if env:
        return Path(env)
    for cand in (Path.home() / "research", Path("/workspace")):
        if (cand / "research-kit").exists():
            return cand
    return Path.home() / "research"


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

    deliver = []
    for p in candidates:
        if p.name in seen:
            continue
        m = NAME_RE.match(p.name)
        to = (m.group("to").lower() if m else "all")
        if to in (here, "all", "any") or not m:
            deliver.append(p)

    if not deliver:
        # prune state to existing files so it can't grow forever
        state_file.write_text(json.dumps(sorted(seen & {p.name for p in candidates})))
        return

    print(f"## Inter-session message(s) in inbox/messages/ (you are: {here})")
    print()
    for p in deliver[:MAX_FILES]:
        body = p.read_text(errors="replace")[:MAX_BYTES]
        print(f"### {p.name}")
        print(body.rstrip())
        print()
        seen.add(p.name)
    if len(deliver) > MAX_FILES:
        print(f"...and {len(deliver) - MAX_FILES} more message file(s) — read them directly.")
    print(
        "Act on what is relevant, then DELETE each consumed message file "
        "(git-ignored plain files; `rm` is fine). If you are the author of a "
        "message shown above, ignore it."
    )
    state_file.write_text(json.dumps(sorted((seen & {p.name for p in candidates}) | seen)))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
