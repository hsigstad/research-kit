#!/usr/bin/env python3
"""Idle-wake: waker targeting, and the sentinel that keeps a woken turn locked."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

WS = Path("/projects/ec113/henrik/research")
HOOKS = WS / "research-kit/tools/hooks"
WAKER = WS / "research-kit/tools/inbox_waker.py"
MSGS = WS / "inbox/messages"
PRES = WS / "inbox/presence"
STATE = Path.home() / ".claude/state"
SID = "waketest-0001"
env = {**os.environ, "RESEARCH_WORKSPACE": str(WS)}

sys.path.insert(0, str(HOOKS))
import peer_turn

fails = 0


def check(label, cond, extra=""):
    global fails
    fails += not cond
    print(f"  {'ok ' if cond else 'FAIL'} {label} {extra}")


def live_pane():
    """A real pane id running a claude-ish command (we only ever --dry-run at it)."""
    out = subprocess.run(["tmux", "list-panes", "-a", "-F",
                          "#{pane_id}\t#{pane_current_command}"],
                         capture_output=True, text=True)
    for line in out.stdout.splitlines():
        pid, cmd = line.split("\t", 1)
        if cmd.lower() in {"claude", "apptainer"}:
            return pid
    return None


def put_presence(pane, idle_secs, sid=SID, name="WakeTest"):
    PRES.mkdir(parents=True, exist_ok=True)
    (PRES / f"{name}_{sid[:8]}.json").write_text(json.dumps({
        "name": name, "session_id": sid, "env": "host", "cwd": str(WS),
        "tmux_pane": pane, "started": 0,
        "last_seen": int(time.time()) - idle_secs, "focus": "idle"}))


def put_msg():
    MSGS.mkdir(parents=True, exist_ok=True)
    (MSGS / "peer-to-host_waketest_a.md").write_text(
        f"To-Session: {SID}\nFrom-Name: Peer\n\nwake up please\n")


def clean():
    for f in list(MSGS.glob("*waketest*")) + list(PRES.glob("*waketest*")) + list(PRES.glob("WakeTest*")):
        f.unlink(missing_ok=True)
    for pat in (f"inbox_seen_{SID}.json", f"wake_{SID}.json"):
        (STATE / pat).unlink(missing_ok=True)
    peer_turn.clear(SID)


def waker():
    p = subprocess.run([sys.executable, str(WAKER), "--dry-run"],
                       env=env, capture_output=True, text=True)
    return p.stdout + p.stderr


def prompt_hook(text):
    """Run the UserPromptSubmit hook with a given prompt."""
    subprocess.run([sys.executable, str(HOOKS / "userprompt_inbox.py")],
                   env=env, capture_output=True, text=True,
                   input=json.dumps({"session_id": SID,
                                     "hook_event_name": "UserPromptSubmit",
                                     "prompt": text}))


pane = live_pane()
if not pane:
    print("no claude-ish tmux pane available; skipping waker targeting")
else:
    clean()
    print(f"=== waker targeting (dry-run against real pane {pane}) ===")
    put_msg(); put_presence(pane, idle_secs=600)
    out = waker()
    check("wakes an idle session with mail", "would wake WakeTest" in out, f"| {out.strip()[:60]}")

    put_presence(pane, idle_secs=10)
    out = waker()
    check("skips an ACTIVE session (drain owns it)", "WakeTest" not in out)

    put_presence(pane, idle_secs=99999)
    out = waker()
    check("skips a long-dead session", "WakeTest" not in out)

    put_presence("%99999", idle_secs=600)
    out = waker()
    check("skips a pane that no longer exists", "WakeTest" not in out)

    clean(); put_presence(pane, idle_secs=600)
    out = waker()
    check("no mail -> no wake", "WakeTest" not in out)

    print("=== wake budget ===")
    clean()
    # --dry-run deliberately does not consume budget, so call the accounting
    # directly rather than driving it through the CLI.
    sys.path.insert(0, str(WS / "research-kit/tools"))
    import inbox_waker
    consumed = sum(1 for _ in range(9) if inbox_waker.wake_budget_ok(SID))
    check("budget caps wakes at 6/h", consumed == 6, f"(consumed={consumed})")
    out = waker()
    check("--dry-run never consumes budget",
          inbox_waker.wake_budget_ok(SID, commit=False) is False)

print("=== sentinel keeps a woken turn locked ===")
clean()
peer_turn.begin(SID, origin="peer-to-host_x.md", hop=0)
prompt_hook("[peer-wake] check your inbox")
check("peer_turn SURVIVES the waker's typed prompt", peer_turn.read(SID) is not None)
prompt_hook("hey what are you up to")
check("peer_turn CLEARED by a real human prompt", peer_turn.read(SID) is None)

print("=== outward MCP guard ===")
G = HOOKS / "pretool_outward_mcp_guard.py"


def mcp(tool, peer=False):
    if peer:
        peer_turn.begin(SID, origin="peer.md", hop=0)
    else:
        peer_turn.clear(SID)
    p = subprocess.run([sys.executable, str(G)], capture_output=True, text=True,
                       input=json.dumps({"session_id": SID, "tool_name": tool,
                                         "tool_input": {}}))
    peer_turn.clear(SID)
    return p.returncode


check("telegram reply BLOCKED in peer turn",
      mcp("mcp__plugin_telegram_telegram__reply", peer=True) == 2)
check("telegram reply allowed on a human turn",
      mcp("mcp__plugin_telegram_telegram__reply") == 0)
check("calendar create BLOCKED in peer turn",
      mcp("mcp__claude_ai_Google_Calendar__create_event", peer=True) == 2)
check("gmail trash BLOCKED in peer turn",
      mcp("mcp__claude_ai_Gmail__trash_message", peer=True) == 2)
check("read-only MCP allowed in peer turn",
      mcp("mcp__claude_ai_Gmail__search_threads", peer=True) == 0)
check("todoist allowed in peer turn (not outward)",
      mcp("mcp__todoist__add-tasks", peer=True) == 0)

clean()
print(f"\n{'ALL PASS' if not fails else str(fails) + ' FAILURES'}")
sys.exit(1 if fails else 0)
