#!/usr/bin/env bash
# Resolve the research workspace root, then run a hook script under it.
#
# Why this exists: hooks in ~/.claude/settings.json used to hardcode
# `python3 "$CLAUDE_PROJECT_DIR/research-kit/tools/..."`. When Claude is
# launched from a subdirectory (e.g. pipelines/bdata, which is its own git
# repo), CLAUDE_PROJECT_DIR points at that subdir, research-kit/ doesn't exist
# there, and every hook errors out ("No such file or directory").
#
# This wrapper walks up from CLAUDE_PROJECT_DIR (falling back to PWD) until it
# finds a directory containing research-kit/, exports RESEARCH_WORKSPACE to
# that root, and runs the requested script. Fails open (exit 0) if no root is
# found, so a bad launch dir never blocks the session.
#
# Usage (in settings.json hook command):
#   bash /abs/path/to/research-kit/tools/hooks/run_hook.sh <path-relative-to-root>
# e.g.
#   bash .../run_hook.sh research-kit/tools/hooks/userprompt_inbox.py
set -u

rel="${1:-}"
[ -z "$rel" ] && exit 0

find_root() {
  local d="$1"
  while [ -n "$d" ] && [ "$d" != "/" ]; do
    if [ -d "$d/research-kit" ]; then printf '%s\n' "$d"; return 0; fi
    d="$(dirname "$d")"
  done
  return 1
}

root="$(find_root "${CLAUDE_PROJECT_DIR:-}")" \
  || root="$(find_root "$PWD")" \
  || for c in "$HOME/research" /workspace /projects/ec113/henrik/research; do
       [ -d "$c/research-kit" ] && { root="$c"; break; }
     done

[ -z "${root:-}" ] && exit 0          # fail open — never block on a bad launch dir
[ -f "$root/$rel" ] || exit 0         # fail open — script missing

exec env RESEARCH_WORKSPACE="$root" python3 "$root/$rel"
