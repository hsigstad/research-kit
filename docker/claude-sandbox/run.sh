#!/usr/bin/env bash
# Run Claude Code in a sandboxed container with full internet
# but filesystem-jailed to the current working directory.
#
# Auto-detects Docker or Apptainer (for HPC/RHEL servers).
#
# Usage:
#   ./run.sh                    # interactive session
#   ./run.sh "collect news"     # non-interactive task

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
IMAGE_NAME="claude-sandbox"

# --- Detect container runtime ---
if command -v docker &>/dev/null; then
    RUNTIME=docker
elif command -v apptainer &>/dev/null; then
    RUNTIME=apptainer
elif command -v singularity &>/dev/null; then
    RUNTIME=singularity
else
    echo "Error: No container runtime found (need docker, apptainer, or singularity)" >&2
    exit 1
fi

# --- Claude args ---
CLAUDE_ARGS=(--dangerously-skip-permissions)

if [ $# -gt 0 ]; then
    CLAUDE_ARGS+=(-p "$*")
fi

# --- Docker path ---
if [ "$RUNTIME" = "docker" ]; then
    if ! docker image inspect "$IMAGE_NAME" &>/dev/null; then
        echo "Building $IMAGE_NAME Docker image..."
        docker build -t "$IMAGE_NAME" "$SCRIPT_DIR"
    fi

    exec docker run --rm -it \
        -v "$(pwd)":/workspace \
        -v "$HOME/Dropbox":/home/henrik/Dropbox:ro \
        -v "$HOME/.claude":/home/henrik/.claude \
        -v "$HOME/.claude.json":/home/henrik/.claude.json \
        -e TERM=xterm-256color \
        -e COLORTERM=truecolor \
        -e DATA_DIR=/workspace/data \
        -w /workspace \
        --memory=16g \
        --cpus=2 \
        "$IMAGE_NAME" \
        claude "${CLAUDE_ARGS[@]}"
fi

# --- Apptainer/Singularity path ---
SIF="$SCRIPT_DIR/$IMAGE_NAME.sif"

if [ ! -f "$SIF" ]; then
    echo "Building $IMAGE_NAME.sif (this takes a few minutes the first time)..."
    "$RUNTIME" build --fakeroot "$SIF" "$SCRIPT_DIR/claude-sandbox.def"
fi

exec "$RUNTIME" run \
    --bind "$(pwd)":/workspace \
    --bind "$HOME/.claude":/home/henrik/.claude \
    --bind "$HOME/.claude.json":/home/henrik/.claude.json \
    --env "TERM=xterm-256color" \
    --env "COLORTERM=truecolor" \
    --env "DATA_DIR=/workspace/data" \
    --pwd /workspace \
    "$SIF" \
    "${CLAUDE_ARGS[@]}"
