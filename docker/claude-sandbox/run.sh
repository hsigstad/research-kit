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

    WHATSAPP_MOUNT=()
    if [ -d "$HOME/whatsapp-mcp" ]; then
        WHATSAPP_MOUNT=(-v "$HOME/whatsapp-mcp":/home/henrik/whatsapp-mcp)
    fi

    exec docker run --rm -it \
        -v "$(pwd)":/workspace \
        -v "$HOME/Dropbox":/home/henrik/Dropbox:ro \
        -v "$HOME/Dropbox/Transfer_Bocconi":/home/henrik/Dropbox/Transfer_Bocconi \
        -v "$HOME/Screenshots":/home/henrik/Screenshots:ro \
        -v "$HOME/.claude":/home/henrik/.claude \
        -v "$HOME/.claude.json":/home/henrik/.claude.json \
        -v "$HOME/.gitconfig":/home/henrik/.gitconfig:ro \
        -v "$HOME/.ssh":/home/henrik/.ssh:ro \
        -v "$HOME/.config/rclone-sandbox/rclone.conf":/home/henrik/.config/rclone/rclone.conf:ro \
        "${WHATSAPP_MOUNT[@]}" \
        -e TERM=xterm-256color \
        -e COLORTERM=truecolor \
        -e DATA_DIR=/workspace/data \
        -e UV_PROJECT_ENVIRONMENT=/home/henrik/.cache/uv-envs/whatsapp \
        -w /workspace \
        --network host \
        --memory=16g \
        --cpus=2 \
        "$IMAGE_NAME" \
        claude "${CLAUDE_ARGS[@]}"
fi

# --- Apptainer/Singularity path ---
SIF="$SCRIPT_DIR/$IMAGE_NAME.sif"

# Use project disk for build temp files (default /tmp is too small for TeX etc.)
export APPTAINER_TMPDIR="${APPTAINER_TMPDIR:-/projects/ec113/henrik/tmp}"
export SINGULARITY_TMPDIR="$APPTAINER_TMPDIR"
mkdir -p "$APPTAINER_TMPDIR"

if [ ! -f "$SIF" ]; then
    echo "Building $IMAGE_NAME.sif (this takes a while the first time)..."
    "$RUNTIME" build --fakeroot "$SIF" "$SCRIPT_DIR/claude-sandbox.def"
fi

exec "$RUNTIME" run \
    --bind "$(pwd)":/workspace \
    --bind "$HOME/Screenshots":/home/henrik/Screenshots:ro \
    --bind "$HOME/.claude":/home/henrik/.claude \
    --bind "$HOME/.claude.json":/home/henrik/.claude.json \
    --bind "$HOME/.gitconfig":/home/henrik/.gitconfig:ro \
    --bind "$HOME/.ssh":/home/henrik/.ssh:ro \
    --bind /projects/ec113/henrik/.config/rclone-sandbox/rclone.conf:/rclone.conf:ro \
    --env "RCLONE_CONFIG=/rclone.conf" \
    --env "TERM=xterm-256color" \
    --env "COLORTERM=truecolor" \
    --env "DATA_DIR=/workspace/data" \
    --pwd /workspace \
    "$SIF" \
    "${CLAUDE_ARGS[@]}"
