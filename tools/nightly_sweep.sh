#!/usr/bin/env bash
# Nightly workspace convention sweep (cron wrapper).
# All logic lives in nightly_sweep.py; see that file.
set -u
WS="${RESEARCH_WORKSPACE:-$HOME/research}"
exec python3 "$WS/research-kit/tools/nightly_sweep.py"
