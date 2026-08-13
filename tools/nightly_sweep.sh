#!/usr/bin/env bash
# Nightly workspace convention sweep (cron wrapper).
# All logic lives in nightly_sweep.py; see that file.
#
# Resolve the root from this script's own location, not from $RESEARCH_WORKSPACE
# with a $HOME/research default: cron exports no environment, and on this host
# $HOME/research is an unrelated stub — the old default made the sweep lint zero
# repos and report a clean workspace (2026-07-06). Same failure took out
# inbox_waker.py for a day (2026-08-13). See tools/workspace_root.py.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/nightly_sweep.py" "$@"
