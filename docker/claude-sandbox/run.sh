#!/usr/bin/env bash
# Run Claude Code in a sandboxed container with full internet
# but filesystem-jailed to the current working directory.
#
# Auto-detects Docker or Apptainer (for HPC/RHEL servers).
#
# Usage:
#   ./run.sh                    # interactive, auto-named <launchdir>-<pid>, Remote Control on
#   ./run.sh govspend           # interactive, named "govspend", Remote Control on
#   ./run.sh -p "collect news"  # non-interactive task, NO Remote Control seat

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
IMAGE_NAME="claude-sandbox"

# gmail-dl MCP server lives OUTSIDE any single project tree (me/personal/gmail-mcp),
# so a session launched from elsewhere (e.g. Valborg's cron, cwd=household/) doesn't
# get it via the cwd auto-mount and its user-scope registration dangles. Bind it into
# EVERY sandbox at its real path so the registration resolves regardless of launch dir.
# Guarded by existence so it's a no-op where the dir isn't present (e.g. the laptop).
# NOTE: this mounts a raw read-only Gmail token (token.json) into every sandbox
# session — a deliberate breadth choice, not an opt-in gate.
GMAIL_MCP_DIR=/projects/ec113/henrik/personal/me/personal/gmail-mcp

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

# --- Arguments ---------------------------------------------------------------
# BREAKING CHANGE 2026-08-12: a bare positional used to be the print-mode TASK; it is
# now the session NAME, and the task moved behind -p. Rationale: naming a session is the
# common interactive case (concurrent sandboxes are otherwise indistinguishable to
# ListAgents/SendMessage), while print mode is a handful of cron lines. Every known
# caller — Valborg's five cron jobs and the template in household/brain-up.sh — was
# migrated in the same commit. As a backstop against an unmigrated caller silently
# opening an interactive session named "act as Valborg and run daily-job.md", a
# positional containing whitespace is a hard error rather than a name.
CS_TASK=""
while [ $# -gt 0 ]; do
    case "$1" in
        -p|--print)
            [ $# -ge 2 ] || { echo "run.sh: -p needs a task string" >&2; exit 2; }
            CS_TASK="$2"; shift 2 ;;
        -n|--name)
            [ $# -ge 2 ] || { echo "run.sh: -n needs a name" >&2; exit 2; }
            CS_NAME="$2"; shift 2 ;;
        -h|--help)
            sed -n '2,10p' "$0"; exit 0 ;;
        -*)
            echo "run.sh: unknown option '$1' (interactive: run.sh [name]; task: run.sh -p \"…\")" >&2
            exit 2 ;;
        *[[:space:]]*)
            echo "run.sh: '$1' looks like a task, not a session name." >&2
            echo "        Print mode now needs -p:  run.sh -p \"$1\"" >&2
            exit 2 ;;
        *)
            CS_NAME="$1"; shift ;;
    esac
done

# Interactive iff no task was given. Print mode must never hold a Remote Control seat,
# so this single flag gates every RC decision below.
INTERACTIVE=true
[ -n "$CS_TASK" ] && INTERACTIVE=false

# Resolved once at the bottom: display name, and the RC connection name (empty = no RC).
SESSION_NAME=""
RC_NAME=""

# --- Optional: Claude Code channels (e.g. the Telegram household bot) ---
# CS_CHANNELS=telegram cs   →  launch with the Telegram plugin channel so a
# bot session (Valborg) runs prompt-free inside the sandbox. Run it from the
# household repo (~/me/household) so /workspace jails her to the household brain
# and nothing else. Accepts the convenience alias `telegram`
# or a full channel spec. The token (~/.claude/channels/telegram/.env) and
# plugin cache live on the mounted, real ~/.claude, so they persist across runs.
if [ -n "${CS_CHANNELS:-}" ]; then
    case "$CS_CHANNELS" in
        telegram) CHANNELS_SPEC="plugin:telegram@claude-plugins-official"
                  # This is the household bot (Valborg). Name the session "Valborg" (in the
                  # prompt box / /resume picker / terminal title) and name its Remote Control
                  # connection the same, so it can be driven/watched from the Claude app.
                  # The RC half is dropped automatically in print mode by the resolver below.
                  SESSION_NAME=Valborg; RC_NAME=Valborg
                  # Bound over /workspace/.claude/settings.local.json below — the only place the
                  # Telegram plugin is enabled. See the CS_TELEGRAM_ENABLE_SRC block.
                  CS_TELEGRAM_ENABLE_SRC="${CS_TELEGRAM_ENABLE_SRC:-$HOME/.claude/channels/telegram/enable-plugin.json}" ;;
        *)        CHANNELS_SPEC="$CS_CHANNELS" ;;
    esac
    CLAUDE_ARGS+=(--channels "$CHANNELS_SPEC")
    # The plugin's MCP server is a bun process, and claude spawns it as a NON-login
    # subprocess — so the host ~/.bun/bin that .bashrc puts on PATH never reaches it
    # inside the container (verified on educloud: it can't find bun and the bot goes
    # silent). Inject bun onto the container PATH for every process. (Apptainer path
    # only; the Docker image bakes bun in and ignores these.)
    if [ -d "$HOME/.bun/bin" ]; then
        export APPTAINERENV_PREPEND_PATH="$HOME/.bun/bin${APPTAINERENV_PREPEND_PATH:+:$APPTAINERENV_PREPEND_PATH}"
        export SINGULARITYENV_PREPEND_PATH="$APPTAINERENV_PREPEND_PATH"
    fi
fi

# --- Optional: pin the Remote Control / display name (e.g. Saga, the work brain) ---
# CS_REMOTE_CONTROL=Saga  →  force both names to "Saga" (no plugin channel — Saga has no
# Telegram poller; she's reached only via Remote Control). Since RC is now the default for
# every interactive session, this env var no longer *enables* anything; it only pins the
# name, and is kept because work/brain-up.sh sets it. No-op when unset.
if [ -n "${CS_REMOTE_CONTROL:-}" ]; then
    SESSION_NAME="$CS_REMOTE_CONTROL"; RC_NAME="$CS_REMOTE_CONTROL"
fi

# --- Optional: extra read-write bind mounts (space-separated host:container specs) ---
# CS_BIND="/host/a:/workspace/a /host/b:/workspace/b" → appended as --bind (apptainer) / -v (docker).
# Used by the `saga` launcher to bind the sibling research/ + teach/ workbenches (and the Saga⇄Valborg
# mailbox) INTO a work-rooted jail, so the raw-data lake and personal/ stay out by absence. No-op when
# unset, so `cs` and the Valborg launcher are unaffected.
EXTRA_BIND_APPT=()
EXTRA_BIND_DOCK=()
if [ -n "${CS_BIND:-}" ]; then
    for spec in $CS_BIND; do
        EXTRA_BIND_APPT+=(--bind "$spec")
        EXTRA_BIND_DOCK+=(-v "$spec")
    done
fi

# --- Telegram plugin: enable it HERE and nowhere else ---
# The plugin's MCP server starts long-polling getUpdates the moment it loads, and it SIGTERMs
# whoever holds ~/.claude/channels/telegram/bot.pid — Telegram allows exactly one consumer per
# token. So any OTHER Claude session that merely *loads* the plugin steals the bot from Valborg,
# and if that session wasn't started with --channels it swallows the messages silently (they
# arrive as notifications a non-channel CLI ignores). Enablement is therefore OFF at user scope
# and OFF in the household repo's own .claude/settings.local.json; this bind overlays that file
# with an enabling copy that exists only inside the container, so the ONLY way to load the plugin
# is through this launcher. ($HOME is the real host home in here — apptainer auto-mounts it — so
# there is no user-scope file the container has and the host doesn't.)
if [ -n "${CS_TELEGRAM_ENABLE_SRC:-}" ] && [ -f "$CS_TELEGRAM_ENABLE_SRC" ] \
   && [ -f "$(pwd)/.claude/settings.local.json" ]; then
    EXTRA_BIND_APPT+=(--bind "$CS_TELEGRAM_ENABLE_SRC":/workspace/.claude/settings.local.json)
    EXTRA_BIND_DOCK+=(-v "$CS_TELEGRAM_ENABLE_SRC":/workspace/.claude/settings.local.json)
fi

if [ "$INTERACTIVE" = false ]; then
    CLAUDE_ARGS+=(-p "$CS_TASK")
elif [ -n "${CS_SEED:-}" ]; then
    # Interactive initial prompt (a BARE positional, NOT -p): claude starts by processing this
    # seed and then STAYS interactive. Used by the Saga daemon to seed her always-on Remote
    # Control session. Only when no -p task is given (a task means print mode above).
    CLAUDE_ARGS+=("$CS_SEED")
fi

# --- Session name + Remote Control -------------------------------------------
# Every launch has cwd=/workspace inside the container, so Claude would auto-derive the
# SAME display name for all of them, leaving concurrent sessions ambiguous to address via
# ListAgents/SendMessage. So always name the session: an explicit name (positional, -n, or
# CS_NAME) wins; otherwise fall back to the host launch dir + PID, unique per session.
SESSION_NAME="${SESSION_NAME:-${CS_NAME:-$(basename "$(pwd)")-$$}}"
CLAUDE_ARGS+=(--name "$SESSION_NAME")

# Remote Control on by default for INTERACTIVE sessions, so any sandbox can be driven or
# watched from the Claude app without deciding at launch. Print mode never gets a seat:
# a cron job that exits would leave a dangling connection, and headless runs are exactly
# what the Valborg/Saga comments meant by "must never hold a Remote Control seat".
# CS_NO_RC=1 opts a one-off out.
if [ "$INTERACTIVE" = true ] && [ -z "${CS_NO_RC:-}" ]; then
    CLAUDE_ARGS+=(--remote-control "${RC_NAME:-$SESSION_NAME}")
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

    GMAIL_MOUNT=()
    if [ -e "$GMAIL_MCP_DIR" ]; then
        GMAIL_MOUNT=(-v "$GMAIL_MCP_DIR":"$GMAIL_MCP_DIR")
    fi

    # R_ENVIRON_USER/R_LIBS_USER: keep the container's R self-contained (see
    # the note above the Apptainer exec below).
    exec docker run --rm -it \
        -v "$(pwd)":/workspace \
        "${EXTRA_BIND_DOCK[@]}" \
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
        "${GMAIL_MOUNT[@]}" \
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
GMAIL_BIND=()
if [ -e "$GMAIL_MCP_DIR" ]; then
    GMAIL_BIND=(--bind "$GMAIL_MCP_DIR":"$GMAIL_MCP_DIR")
fi

exec "$RUNTIME" run \
    --bind "$(pwd)":/workspace \
    "${EXTRA_BIND_APPT[@]}" \
    "${GMAIL_BIND[@]}" \
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
