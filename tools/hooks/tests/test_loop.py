#!/usr/bin/env python3
"""A<->B ping-pong must terminate: hop increments across replies and hits the ceiling."""
import json
import os
import subprocess
import sys
from pathlib import Path

WS = Path("/projects/ec113/henrik/research")
HOOKS = WS / "research-kit/tools/hooks"
SEND = WS / "research-kit/tools/send_message.py"
MSGS = WS / "inbox/messages"
A, B = "looptest-aaaa", "looptest-bbbb"
STATE = Path.home() / ".claude/state"

sys.path.insert(0, str(HOOKS))
import peer_turn


def clean():
    for f in MSGS.glob("*looptest*"):
        f.unlink()
    for sid in (A, B):
        (STATE / f"inbox_seen_{sid}.json").unlink(missing_ok=True)
        (STATE / f"drain_{sid}.json").unlink(missing_ok=True)
        peer_turn.clear(sid)


def drain(sid):
    p = subprocess.run([sys.executable, str(HOOKS / "stop_inbox.py")],
                       env={**os.environ, "RESEARCH_WORKSPACE": str(WS)},
                       text=True, capture_output=True,
                       input=json.dumps({"session_id": sid, "hook_event_name": "Stop"}))
    return p.returncode, p.stderr


def reply(from_sid, to_sid):
    """Simulate the drained session replying via send_message.py."""
    return subprocess.run(
        [sys.executable, str(SEND), "--to-session", to_sid, "--body", "and back to you"],
        env={**os.environ, "RESEARCH_WORKSPACE": str(WS),
             "CLAUDE_CODE_SESSION_ID": from_sid},
        text=True, capture_output=True)


clean()
# A opens the exchange (hop 0, no peer turn active for the sender).
(MSGS / "peer-to-host_looptest_seed.md").write_text(
    f"To-Session: {B}\nFrom-Name: A\n\nkick it off\n")

hops, turns = [], 0
cur, other = B, A
for turns in range(1, 12):
    rc, err = drain(cur)
    if rc != 2:
        print(f"  exchange stopped after {turns - 1} drains (rc={rc})")
        break
    hop_line = [l for l in err.splitlines() if l.startswith("### ")]
    hops.append(hop_line[0] if hop_line else "?")
    r = reply(cur, other)
    if r.returncode != 0:
        print("  send failed:", r.stderr[:200])
        break
    cur, other = other, cur

print("drain sequence:")
for h in hops:
    print("   ", h)

sent = sorted(p.name for p in MSGS.glob("*looptest*"))
print(f"messages on disk: {len(sent)}")
stamped = []
for p in MSGS.glob("*looptest*"):
    t = p.read_text()
    h = [l for l in t.splitlines() if l.lower().startswith("hop:")]
    stamped.append(h[0] if h else "Hop: (none)")
print("hop headers:", sorted(stamped))

ok = len(hops) <= 4 and any("hop 2" in h for h in hops)
print(f"\n{'PASS — exchange terminated at the hop ceiling' if ok else 'FAIL — did not terminate as expected'}")
clean()
sys.exit(0 if ok else 1)
