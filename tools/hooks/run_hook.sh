#!/usr/bin/env bash
# Resolve the research workspace root, then run a hook script under it.
#
# Why this exists: hooks in ~/.claude/settings.json used to hardcode
# `python3 "$CLAUDE_PROJECT_DIR/research-kit/tools/..."`. When Claude is
# launched from a subdirectory (e.g. pipelines/bdata, which is its own git
# repo), CLAUDE_PROJECT_DIR points at that subdir, research-kit/ doesn't exist
# there, and every hook errors out ("No such file or directory").
#
# Scoping model (so the research hooks fire in the RIGHT places, including from
# a work-rooted brain like Saga whose jail binds research at /workspace/research):
#   1. If the hook payload names an edited file, resolve the workspace from THAT
#      file — the nearest ancestor containing research-kit/. A file outside any
#      such tree (teach/, the work brain repo, /tmp, …) is SKIPPED. This is what
#      makes the edit hooks fire on research edits only.
#   2. git_guard is workspace-independent (it blocks `git add -A` in any shared
#      repo) — it runs wherever research-kit is reachable, regardless of root.
#   3. Other no-file hooks (SessionStart / UserPromptSubmit / Stop) run only in a
#      session actually rooted in a research workspace — a work-/household-rooted
#      brain skips them.
# Fails open (exit 0) whenever no root or script is found, so a bad launch dir or
# a non-research edit never blocks the session.
#
# Usage (in settings.json hook command):
#   bash /abs/path/to/research-kit/tools/hooks/run_hook.sh <path-relative-to-root>
set -u

rel="${1:-}"
[ -z "$rel" ] && exit 0

# nearest ancestor of $1 that contains research-kit/ (the workspace root)
find_root() {
  local d="$1"
  while [ -n "$d" ] && [ "$d" != "/" ]; do
    if [ -d "$d/research-kit" ]; then printf '%s\n' "$d"; return 0; fi
    d="$(dirname "$d")"
  done
  return 1
}

# Capture the hook payload (JSON on stdin) so we can both peek at it and forward it.
payload="$(cat)"

# run the requested hook under root=$1, forwarding the captured payload; propagate
# its exit code (exit 2 = block reaches Claude). Fail open if the script is missing.
run() {
  local root="$1"
  [ -f "$root/$rel" ] || exit 0
  printf '%s' "$payload" | env RESEARCH_WORKSPACE="$root" python3 "$root/$rel"
  exit $?
}

# 1) Edited file present → scope to that file's workspace (teach/work/tmp → skip).
file_path="$(printf '%s' "$payload" | python3 -c 'import json,sys
try: print((json.load(sys.stdin).get("tool_input") or {}).get("file_path","") or "")
except Exception: print("")' 2>/dev/null)"
if [ -n "$file_path" ]; then
  root="$(find_root "$(dirname "$file_path")")" || exit 0   # not under a research workspace → skip
  run "$root"
fi

# 2) git_guard: workspace-independent — run wherever research-kit is reachable.
case "$rel" in
  *pretool_git_guard*)
    root="$(find_root "${CLAUDE_PROJECT_DIR:-}")" || root="$(find_root "$PWD")" || root=""
    if [ -z "$root" ]; then
      for c in /workspace/research "$HOME/research" /projects/ec113/henrik/research; do
        [ -d "$c/research-kit" ] && { root="$c"; break; }
      done
    fi
    [ -n "$root" ] && run "$root"
    exit 0
    ;;
esac

# 3) Session/prompt hooks (no file): only in a session rooted in a research
#    workspace. Work-/household-rooted brains (Saga, Valborg) skip them.
root="$(find_root "${CLAUDE_PROJECT_DIR:-}")" || root="$(find_root "$PWD")" || exit 0
run "$root"
