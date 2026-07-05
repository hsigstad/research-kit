FROM debian:bookworm-slim

# System packages, TeX Live, R toolchain, and root-level CLIs.
# Shared with the Apptainer build via lib/install-system.sh — edit that file,
# not this line, so the laptop (Docker) and educloud (Apptainer) images stay
# in lockstep. Same applies to lib/install-r.sh and lib/install-python.sh below.
COPY lib/ /tmp/lib/
RUN bash /tmp/lib/install-system.sh

# R packages (as root, so they land in the system library visible to henrik).
RUN bash /tmp/lib/install-r.sh

# ── Match host user ─────────────────────────────────────────────────
RUN useradd -m -u 1000 henrik
USER henrik

# ── Python virtualenv ───────────────────────────────────────────────
# Installed to the henrik home as the henrik user. The trailing package is a
# Docker-only extra (MCP server) the educloud image omits.
ENV PATH="/home/henrik/venv/bin:$PATH"
RUN bash /tmp/lib/install-python.sh /home/henrik/venv \
    git+https://github.com/DarrenZal/otter-mcp.git

# ── uv (for MCP server envs) ────────────────────────────────────────
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Pre-build the whatsapp-mcp-server uv environment
RUN git clone --depth 1 https://github.com/lharries/whatsapp-mcp.git /tmp/wamcp \
 && UV_PROJECT_ENVIRONMENT=/home/henrik/.cache/uv-envs/whatsapp \
    /home/henrik/.local/bin/uv sync --project /tmp/wamcp/whatsapp-mcp-server --frozen \
 && rm -rf /tmp/wamcp

# ── Memory monitor ──────────────────────────────────────────────────
COPY monitor_memory.sh /usr/local/bin/monitor_memory.sh

WORKDIR /workspace
