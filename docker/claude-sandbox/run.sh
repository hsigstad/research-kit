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

# --- Optional: Claude Code channels (e.g. the Telegram household bot) ---
# CS_CHANNELS=telegram cs   →  launch with the Telegram plugin channel so a
# bot session (Valborg) runs prompt-free inside the sandbox. Run it from the
# household repo (~/me/household) so /workspace jails her to the household brain
# and nothing else. Accepts the convenience alias `telegram`
# or a full channel spec. The token (~/.claude/channels/telegram/.env) and
# plugin cache live on the mounted, real ~/.claude, so they persist across runs.
if [ -n "${CS_CHANNELS:-}" ]; then
    case "$CS_CHANNELS" in
        telegram) CHANNELS_SPEC="plugin:telegram@claude-plugins-official" ;;
        *)        CHANNELS_SPEC="$CS_CHANNELS" ;;
    esac
    CLAUDE_ARGS+=(--channels "$CHANNELS_SPEC")
fi

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

    # R_ENVIRON_USER/R_LIBS_USER: keep the container's R self-contained (see
    # the note above the Apptainer exec below).
    exec docker run --rm -it \
        -v "$(pwd)":/workspace \
        -e R_ENVIRON_USER=/dev/null \
        -e R_LIBS_USER=/tmp/r-sandbox-libs \
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
    # Plain `apptainer build --fakeroot <sif> <def>` SEGFAULTS on this host:
    # EduCloud/Fox has no /etc/subuid mapping, so apptainer runs mksquashfs under
    # the libfakeroot shim, which corrupts it (SIGSEGV) even for a trivial image.
    # Workaround — build a --sandbox (fakeroot %post is fine, no mksquashfs), then
    # pack it to a SIF ourselves with a direct mksquashfs -no-xattrs (no fakeroot)
    # plus SIF assembly. The nfs4_acl/rootlesscontainers xattrs that -no-xattrs
    # drops are meaningless inside a .sif. Build from SCRIPT_DIR so the .def's
    # %files (lib/) resolve regardless of the caller's cwd. On a host that has
    # subuid set up, the plain one-line build works and this can be simplified.
    SBX="$APPTAINER_TMPDIR/$IMAGE_NAME.sbx.$$"
    SQFS="$APPTAINER_TMPDIR/$IMAGE_NAME.sqfs.$$"
    MKSQUASHFS="${MKSQUASHFS:-/usr/libexec/apptainer/bin/mksquashfs}"
    command -v "$MKSQUASHFS" >/dev/null 2>&1 || MKSQUASHFS=mksquashfs
    trap 'rm -rf "$SBX" "$SQFS" "$SIF"' EXIT
    rm -rf "$SBX" "$SQFS"
    ( cd "$SCRIPT_DIR" && "$RUNTIME" build --sandbox "$SBX" claude-sandbox.def )
    "$MKSQUASHFS" "$SBX" "$SQFS" -noappend -no-xattrs
    "$RUNTIME" sif new "$SIF"
    # datatype 4=Partition, parttype 2=PrimSys (bootable rootfs), partfs 1=Squashfs, partarch 2=amd64
    "$RUNTIME" sif add "$SIF" "$SQFS" --datatype 4 --parttype 2 --partfs 1 --partarch 2
    rm -rf "$SBX" "$SQFS"
    trap - EXIT
    echo "Built $SIF"
fi

# Decouple the container's R from the host home R library. Apptainer auto-mounts
# $HOME, so ~/.Renviron (which pins R_LIBS_USER to ~/R_libs) and those packages
# leak in — but ~/R_libs is built against the host's R (4.6.0) while the image
# ships R 4.5.3, so arrow/ggplot2 fail with "undefined symbol R_MakeMissingBinding".
# Skip the host .Renviron (it only sets R_LIBS_USER) and point R at a throwaway
# user lib; arrow/fixest/ggplot2 resolve from the image's system library
# (/usr/local/lib/R/site-library, populated by lib/install-r.sh). No rebuild needed.
exec "$RUNTIME" run \
    --bind "$(pwd)":/workspace \
    --env "R_ENVIRON_USER=/dev/null" \
    --env "R_LIBS_USER=/tmp/r-sandbox-libs" \
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
