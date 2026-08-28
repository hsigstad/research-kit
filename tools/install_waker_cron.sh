#!/usr/bin/env bash
# Ensure the inbox-waker cron block exists. Idempotent; a no-op when it is already there.
#
# INTENT: give the waker block a guardian. saga-brain and valborg-brain each re-add
# themselves on every run of their brain-up.sh; inbox-waker had no such script, so any
# event that replaced the crontab (a brain-up rewrite, or — 2026-08-28 — landing on an
# Educloud login node carrying a stale node-local table) silently dropped it and idle
# peers stopped getting their mail. The outage is invisible from inside a session:
# waker.log is silent on no-op runs and nothing else notices.
#
# REASONING: write only when the block is genuinely absent, so this stays safe to call
# from a watchdog that fires every 15 minutes. Read failures abort rather than rewrite —
# a transient `crontab -l` error must never be read as "the table is empty" (that bug
# wiped every block we do not manage, 2026-08).
#
# ASSUMES: run on the HOST (the sandbox has no crontab and no tmux). The block goes at
# the TOP of the table, above the saga/valborg `PATH=` assignments, so the waker runs
# under cron's default PATH=/usr/bin:/bin and its `#!/usr/bin/env python3` shebang
# resolves to /usr/bin/python3 rather than whatever the interactive PATH prefers.
#
# Usage:  install_waker_cron.sh [--check]
#         --check  report status and exit 1 if missing; never writes.
set -euo pipefail

SENTINEL="inbox-waker"
TOOLS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WAKER="$TOOLS/inbox_waker.py"
WAKER_LOG="$HOME/.claude/state/waker.log"
CHECK_ONLY=0
[ "${1:-}" = "--check" ] && CHECK_ONLY=1

[ -x "$WAKER" ] || { echo "install_waker_cron: $WAKER missing or not executable" >&2; exit 1; }

# Guarded read: only an explicit "no crontab for" counts as a genuinely empty table.
err="$(mktemp)"
set +e
cur="$(crontab -l 2>"$err")"; rc=$?
set -e
if [ "$rc" -ne 0 ] && ! grep -qi "no crontab for" "$err"; then
  echo "install_waker_cron: could not read crontab (rc=$rc: $(head -1 "$err")) — refusing to rewrite" >&2
  rm -f "$err"; exit 1
fi
rm -f "$err"

if printf '%s\n' "$cur" | grep -q "$SENTINEL"; then
  echo "install_waker_cron: block present — no change"
  exit 0
fi

if [ "$CHECK_ONLY" -eq 1 ]; then
  echo "install_waker_cron: MISSING — inbox-waker block is not in the crontab" >&2
  exit 1
fi

tmp="$(mktemp)"
cat > "$tmp" <<CRON
# >>> inbox-waker >>>
# Wake an idle Claude session that has inbox mail (tmux send-keys into its pane).
# Host-only: tmux lives here, not in the sandboxes. Self-limiting — skips sessions
# seen in the last 2min (stop_inbox drains those), dead panes, and >6 wakes/hour.
# Kept ABOVE the saga/valborg PATH= lines on purpose: runs under cron's default
# PATH=/usr/bin:/bin. Re-added by research-kit/tools/install_waker_cron.sh.
* * * * *    $WAKER >> $WAKER_LOG 2>&1  # $SENTINEL
# <<< inbox-waker <<<
CRON
# Strip nothing: the block is absent by the check above, so the rest of the table
# (saga-brain, valborg-brain, anything hand-added) is carried through verbatim.
printf '%s\n' "$cur" >> "$tmp"
crontab "$tmp"
rm -f "$tmp"
echo "install_waker_cron: block INSTALLED (was missing)"
