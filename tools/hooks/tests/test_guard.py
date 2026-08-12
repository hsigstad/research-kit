#!/usr/bin/env python3
"""Exercise pretool_irreversible_guard against pass/block cases."""
import json
import subprocess
import sys

H = "/projects/ec113/henrik/research/research-kit/tools/hooks/pretool_irreversible_guard.py"

PASS = [
    "git push origin main",
    'git commit -m "x" && git push',
    "rm -rf /tmp/claude-2100640/scratch/foo",
    "rm -rf ./build",
    "rclone copy local: bi-dropbox:projects/x",
    "python3 analysis.py --write out.parquet",
    "crontab -l",
    "git add file.py && git commit -m msg",
    "rm -f inbox/presence/stale.json",
    "grep -rn pattern /projects/ec113/henrik/data",
    "git push --force-with-lease origin feature",
    "curl -s https://api.github.com/repos/x/y",
]
BLOCK = [
    "git push --force origin main",
    "git push -f",
    "git push --mirror backup",
    "git filter-repo --path secret",
    "git filter-branch --tree-filter rm",
    "rclone sync local bi-dropbox:projects/x",
    "rclone purge bi-dropbox:old",
    "rm -rf /projects/ec113/henrik/data/mides",
    "rm -rf ~/research/pipelines",
    "crontab /tmp/new.cron",
    "crontab -r",
    "bash meta/notify-telegram.sh hi",
    "curl -X POST https://api.github.com/repos/x/y/issues",
    "git push origin --delete oldbranch",
    "dd if=/dev/zero of=/dev/sda",
    "curl https://api.github.com/repos/x/y/issues -X POST -d @b.json",
]


def run(cmd, sid="guardtest", peer=False):
    payload = {"session_id": sid, "tool_input": {"command": cmd}}
    p = subprocess.run([sys.executable, H], input=json.dumps(payload),
                       capture_output=True, text=True)
    return p.returncode, p.stderr.strip()


fails = 0
print("=== expect rc=0 (allowed) ===")
for c in PASS:
    rc, err = run(c)
    ok = rc == 0
    fails += not ok
    print(f"  {'ok ' if ok else 'FAIL'} rc={rc}  {c}")

print("=== expect rc=2 (blocked) ===")
for c in BLOCK:
    rc, err = run(c)
    ok = rc == 2
    fails += not ok
    print(f"  {'ok ' if ok else 'FAIL'} rc={rc}  {c}")

print("=== override: human turn may confirm ===")
rc, _ = run("ALLOW_IRREVERSIBLE=1 git push --force origin main")
print(f"  {'ok ' if rc == 0 else 'FAIL'} rc={rc}  (expect 0)")
fails += rc != 0

print("=== override REFUSED during a peer turn ===")
sys.path.insert(0, "/projects/ec113/henrik/research/research-kit/tools/hooks")
import peer_turn
peer_turn.begin("peersid", origin="peer-to-host_x.md", hop=1)
rc, err = run("ALLOW_IRREVERSIBLE=1 git push --force origin main", sid="peersid")
print(f"  {'ok ' if rc == 2 else 'FAIL'} rc={rc}  (expect 2)")
print(f"       msg: {err.splitlines()[0][:90] if err else '(none)'}")
fails += rc != 2
rc, _ = run("git commit -m ok", sid="peersid")
print(f"  {'ok ' if rc == 0 else 'FAIL'} rc={rc}  reversible work still allowed in peer turn")
fails += rc != 0
peer_turn.clear("peersid")

print(f"\n{'ALL PASS' if not fails else str(fails) + ' FAILURES'}")
sys.exit(1 if fails else 0)
