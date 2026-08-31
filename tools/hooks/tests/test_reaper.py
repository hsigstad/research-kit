#!/usr/bin/env python3
"""Reaper: grace period, delivered-vs-never-read, bounce targeting, no bounce loops."""
import json
import os
import sys
import time
from pathlib import Path

WS = Path("/projects/ec113/henrik/research")
sys.path.insert(0, str(WS / "research-kit/tools"))
sys.path.insert(0, str(WS / "research-kit/tools/hooks"))
import inbox_reaper as R

fails = 0


def check(label, cond, extra=""):
    global fails
    fails += not cond
    print(f"  {'ok ' if cond else 'FAIL'} {label} {extra}")


def head(**kw):
    return "\n".join(f"{k.replace('_', '-')}: {v}" for k, v in kw.items())


print("classify")
NOW = time.time()
by_sid = {"aaaa1111-live": {"session_id": "aaaa1111-live", "name": "Live",
                            "env": "host", "last_seen": NOW}}
by_name = {"live": by_sid["aaaa1111-live"]}

s, d = R.classify(head(From_Session="x", To_Session="aaaa1111-live"),
                  "m1.md", {"m1.md"}, by_sid, by_name)
check("delivered file -> consumed", s == "consumed", f"({s})")

s, d = R.classify(head(From_Session="x", To_Session="dead0000-gone"),
                  "m2.md", set(), by_sid, by_name)
check("unknown To-Session -> undelivered", s == "undelivered", f"({s})")
check("  ...and says so", "no longer exists" in d, f"({d})")

s, d = R.classify(head(From_Session="x", To_Session="aaaa1111-live"),
                  "m3.md", set(), by_sid, by_name)
check("live but unread -> undelivered", s == "undelivered", f"({s})")
check("  ...distinguishes live-but-unread", "still in presence" in d, f"({d})")

s, d = R.classify(head(From_Session="x", To_Name="Nobody"),
                  "m4.md", set(), by_sid, by_name)
check("unknown To-Name -> undelivered", s == "undelivered", f"({s})")

# The loop guard: a bounce that goes stale must retire quietly, never bounce back.
s, d = R.classify(head(From_Session="inbox_reaper", To_Session="aaaa1111-live") +
                  "\n" + R.X_BOUNCE, "m5.md", set(), by_sid, by_name)
check("a bounce is never re-bounced", s == "bounce", f"({s})")

print("\ngrace period (integration, isolated workspace)")
import shutil
import subprocess
import tempfile

tmp = Path(tempfile.mkdtemp())
(tmp / "inbox/messages").mkdir(parents=True)
(tmp / "inbox/presence").mkdir(parents=True)
old = tmp / "inbox/messages/sandbox-to-host_old.md"
new = tmp / "inbox/messages/sandbox-to-host_new.md"
old.write_text(head(From_Session="gone", To_Session="alsogone") + "\n\n# old\n")
new.write_text(head(From_Session="gone", To_Session="alsogone") + "\n\n# new\n")
os.utime(old, (NOW - 30 * 86400, NOW - 30 * 86400))

env = {**os.environ, "RESEARCH_WORKSPACE": str(tmp)}
out = subprocess.run([sys.executable, str(WS / "research-kit/tools/inbox_reaper.py"),
                      "--force"], capture_output=True, text=True, env=env).stdout
check("old message retired", not old.exists(), out.strip()[:60])
check("fresh message untouched", new.exists())
check("retired file moved, not deleted", (tmp / "inbox/dead/sandbox-to-host_old.md").exists())
check("audit line written", (tmp / "inbox/dead/REAPED.jsonl").exists())
try:
    rec = json.loads((tmp / "inbox/dead/REAPED.jsonl").read_text().splitlines()[0])
    check("audit line has status", rec.get("status") == "undelivered", str(rec))
except Exception as e:
    check("audit line parses", False, str(e))
check("no bounce to a dead sender",
      not list((tmp / "inbox/messages").glob("reaper-to-*.md")))

print("\nbounce goes to a LIVE sender only")
tmp2 = Path(tempfile.mkdtemp())
(tmp2 / "inbox/messages").mkdir(parents=True)
(tmp2 / "inbox/presence").mkdir(parents=True)
(tmp2 / "inbox/presence/live.json").write_text(json.dumps(
    {"session_id": "sender-live", "name": "Sender", "env": "host", "last_seen": int(NOW)}))
m = tmp2 / "inbox/messages/sandbox-to-host_x.md"
m.write_text(head(From_Session="sender-live", To_Session="nobody") + "\n\n# please do X\n")
os.utime(m, (NOW - 30 * 86400, NOW - 30 * 86400))
subprocess.run([sys.executable, str(WS / "research-kit/tools/inbox_reaper.py"), "--force"],
               capture_output=True, text=True,
               env={**os.environ, "RESEARCH_WORKSPACE": str(tmp2)})
bounces = list((tmp2 / "inbox/messages").glob("reaper-to-*.md"))
check("live sender is told", len(bounces) == 1, f"({len(bounces)})")
if bounces:
    b = bounces[0].read_text()
    check("bounce is addressed to the sender", "To-Session: sender-live" in b)
    check("bounce carries the loop guard", R.X_BOUNCE in b)
    check("bounce names the original", "sandbox-to-host_x.md" in b)
    check("bounce says it is not done", "NOT done" in b)

shutil.rmtree(tmp, ignore_errors=True)
shutil.rmtree(tmp2, ignore_errors=True)
print("\nFAILED" if fails else "\nall passed")
sys.exit(1 if fails else 0)
