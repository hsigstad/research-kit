#!/usr/bin/env python3
"""PreToolUse hook (Bash): gate the small set of operations you cannot undo.

Applies to EVERY turn, not just peer-initiated ones — the risk is the same
whoever started it, and a rule with one set of semantics beats a second-class
turn type. This is the same posture as pretool_git_guard.py, which blocks
`git add -A` for everybody.

Deliberately NOT a general mutation gate. Writing files, editing, running code
and committing locally all proceed unattended: they are in git, rebuildable, or
visible. What is gated is the short list that ends with something gone or sent:

  - rewriting published history (force-push, filter-branch, remote deletes)
  - sending outward (Telegram/WhatsApp/mail, rclone to a remote)
  - destroying data (rm -rf on the lake, rclone purge/delete, shred, dd)
  - editing live automation (crontab)

Override, for a human turn: re-run with ALLOW_IRREVERSIBLE=1 prefixed. Being
blocked once and having to restate it IS the confirmation step — the point is
that it cannot happen as a side effect of a longer plan.

During a peer turn (stop_inbox.py drained a message and nobody is watching) the
override is refused outright. Peers can make this session work; they cannot make
it publish, send, or delete.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import peer_turn
except Exception:
    peer_turn = None

# (name, regex, why) — matched against the whole command string.
RULES = [
    ("force-push",
     r"\bgit\b(?=[^\n;|&]*\bpush\b)[^\n;|&]*(--force(?!-with-lease)|(?<![\w-])-f(?![\w-])|--mirror)",
     "rewrites published history"),
    ("remote-branch-delete",
     r"\bgit\b(?=[^\n;|&]*\bpush\b)[^\n;|&]*(--delete(?![\w-])|(?<![\w-])-d(?![\w-])\s)",
     "deletes a remote branch"),
    ("history-rewrite",
     r"\bgit\s+(filter-branch|filter-repo)\b|\bgit\s+reflog\s+expire\b|\bgit\s+gc\b[^\n;|&]*--prune=now",
     "destroys recoverable history"),
    ("rclone-destructive",
     r"\brclone\s+(purge|delete|deletefile|rmdir|rmdirs)\b|\brclone\s+sync\b",
     "deletes on the remote (sync mirrors deletions too)"),
    ("outward-send",
     r"\bnotify-telegram\.sh\b|\bwhatsapp[-_]?(send|mcp)\b|\bmail\s+-s\b|\bsendmail\b|\bmsmtp\b",
     "sends a message to a real person"),
    # The method can precede or follow the URL, so anchor on curl and look ahead
    # for the host; -d/--data implies POST even with no explicit -X.
    ("github-write-api",
     r"\bcurl\b(?=[^\n;|&]*api\.github\.com)[^\n;|&]*(?:-X\s*|--request\s*)(?:POST|PATCH|PUT|DELETE)\b"
     r"|\bcurl\b(?=[^\n;|&]*api\.github\.com)[^\n;|&]*(?:--data\b|-d\s)",
     "writes to GitHub (issues, PRs, releases)"),
    ("crontab-edit",
     r"\bcrontab\s+(-r\b|-\s*$|[^\s-][^\n;|&]*)",
     "replaces live scheduled automation"),
    ("disk-destroy",
     r"\b(mkfs|shred)\b|\bdd\s+[^\n;|&]*\bof=/dev/",
     "destroys a device or file irrecoverably"),
]

# rm -rf is judged by target, not by the flag: scratch dirs are fine, the data
# lake and home are not. Anything absolute outside a scratch path is gated.
RM_RF = re.compile(r"\brm\s+(-[A-Za-z]*[rR][A-Za-z]*f|-[A-Za-z]*f[A-Za-z]*[rR])[A-Za-z]*\s+(?P<rest>[^\n;|&]+)")
SCRATCH_OK = re.compile(r"^(/tmp/|/var/tmp/|\./|[^/~])")
PROTECTED = re.compile(r"^(~|\$HOME|/projects/ec113/henrik/data|\$DATA_DIR|/fp/homes01|/projects/ec113/henrik/research/(?!.*scratch))")


def rm_targets(command):
    """Absolute-ish rm -rf targets that are not obviously scratch."""
    bad = []
    for m in RM_RF.finditer(command):
        for tok in m.group("rest").split():
            if tok.startswith("-"):
                continue
            if PROTECTED.match(tok) or (tok.startswith("/") and not SCRATCH_OK.match(tok)):
                bad.append(tok)
    return bad


def violations(command):
    hits = [(n, why) for n, rx, why in RULES if re.search(rx, command, re.IGNORECASE)]
    tgts = rm_targets(command)
    if tgts:
        hits.append(("recursive-delete", f"removes {' '.join(tgts[:3])} irrecoverably"))
    return hits


def main():
    data = json.load(sys.stdin)
    cmd = (data.get("tool_input") or {}).get("command", "") or ""
    if not cmd:
        return 0
    hits = violations(cmd)
    if not hits:
        return 0

    sid = data.get("session_id")
    peer = peer_turn.read(sid) if (peer_turn and sid) else None
    listed = "; ".join(f"{n} ({why})" for n, why in hits)

    if peer:
        print(
            f"Blocked (peer turn): {listed}.\n"
            f"This turn was started by a peer session's message "
            f"({peer.get('origin')}), not by a human, so irreversible and outward "
            f"actions are refused and ALLOW_IRREVERSIBLE does not apply here.\n"
            f"Do the reversible part, then say plainly in your reply what you did "
            f"NOT do and why, so a human can run this step.",
            file=sys.stderr,
        )
        return 2

    if re.search(r"\bALLOW_IRREVERSIBLE=1\b", cmd):
        return 0

    print(
        f"Blocked: {listed}.\n"
        f"This is one of the few operations with nothing to undo it. If the user "
        f"asked for exactly this, re-run it prefixed with ALLOW_IRREVERSIBLE=1 — "
        f"otherwise stop and confirm with them first. Do not add the prefix to "
        f"work around an unexpected block.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
