#!/usr/bin/env python3
"""Exercise stop_inbox drain: trigger, hop ceiling, budget, dedup, re-entrancy."""
import json
import os
import subprocess
import sys
from pathlib import Path

WS = Path("/projects/ec113/henrik/research")
H = WS / "research-kit/tools/hooks/stop_inbox.py"
MSGS = WS / "inbox/messages"
SID = "draintest-0001"
STATE = Path.home() / ".claude/state"
env = {**os.environ, "RESEARCH_WORKSPACE": str(WS)}

sys.path.insert(0, str(WS / "research-kit/tools/hooks"))
import peer_turn


def reset():
    for f in MSGS.glob("*draintest*"):
        f.unlink()
    (STATE / f"inbox_seen_{SID}.json").unlink(missing_ok=True)
    (STATE / f"drain_{SID}.json").unlink(missing_ok=True)
    peer_turn.clear(SID)


def put(name, hop=None, body="please rebuild the extract"):
    lines = [f"To-Session: {SID}", "From-Name: Peer"]
    if hop is not None:
        lines.append(f"Hop: {hop}")
    lines += ["", body, ""]
    (MSGS / name).write_text("\n".join(lines))


def stop(active=False):
    p = subprocess.run([sys.executable, str(H)], env=env, text=True, capture_output=True,
                       input=json.dumps({"session_id": SID, "hook_event_name": "Stop",
                                         "stop_hook_active": active}))
    return p.returncode, p.stderr


fails = 0


def check(label, cond, extra=""):
    global fails
    fails += not cond
    print(f"  {'ok ' if cond else 'FAIL'} {label} {extra}")


reset()
print("=== no messages -> turn ends normally ===")
rc, _ = stop()
check("rc=0 when inbox empty", rc == 0, f"(rc={rc})")

print("=== message addressed here -> blocks the stop ===")
put("peer-to-host_draintest_a.md")
rc, err = stop()
check("rc=2 blocks", rc == 2, f"(rc={rc})")
check("surfaces the body", "rebuild the extract" in err)
check("flags no-human-watching", "no human is watching" in err.lower())
check("states the lockout", "irreversible" in err.lower())
check("peer_turn flag set", peer_turn.read(SID) is not None)

print("=== dedup: same message does not re-block ===")
rc, _ = stop()
check("rc=0 second time", rc == 0, f"(rc={rc})")

print("=== stop_hook_active -> never re-enters ===")
put("peer-to-host_draintest_b.md")
rc, _ = stop(active=True)
check("rc=0 when already in stop hook", rc == 0, f"(rc={rc})")

print("=== hop ceiling: hop>=3 is held for a human ===")
reset()
put("peer-to-host_draintest_c.md", hop=3)
rc, err = stop()
check("rc=0, not drained", rc == 0, f"(rc={rc})")
reset()
put("peer-to-host_draintest_d.md", hop=2)
rc, err = stop()
check("hop=2 still drains", rc == 2, f"(rc={rc})")

print("=== not addressed to me -> ignored ===")
reset()
(MSGS / "peer-to-host_draintest_e.md").write_text(
    "To-Session: someone-else\nFrom-Name: Peer\n\nnot yours\n")
rc, _ = stop()
check("rc=0", rc == 0, f"(rc={rc})")

print("=== budget: 12 drains/hour, 13th defers ===")
reset()
real, deferred = 0, 0
for i in range(14):
    put(f"peer-to-host_draintest_n{i}.md")
    rc, err = stop()
    if rc == 2 and "budget" in err.lower():
        deferred += 1
    elif rc == 2:
        real += 1
check("exactly 12 real drains", real == 12, f"(real={real})")
check("the rest defer on budget", deferred == 2, f"(deferred={deferred})")
# Budget-defer blocks once to announce it; the stop_hook_active retry then ends
# the turn, so a stuck session is not possible.
check("retry after defer ends the turn", stop(active=True)[0] == 0)

reset()
print(f"\n{'ALL PASS' if not fails else str(fails) + ' FAILURES'}")
sys.exit(1 if fails else 0)
