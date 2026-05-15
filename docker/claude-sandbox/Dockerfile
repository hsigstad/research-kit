FROM debian:bookworm-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git ca-certificates openssh-client nodejs npm \
    python3 python3-pip python3-venv \
    chromium chromium-driver \
    rsync pandoc \
  && rm -rf /var/lib/apt/lists/*

# TeX Live (curated subset: latexmk, biber, make4ht, common paper packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    texlive-latex-base texlive-latex-recommended texlive-latex-extra \
    texlive-fonts-recommended texlive-fonts-extra \
    texlive-bibtex-extra texlive-extra-utils \
    texlive-science texlive-luatex \
    latexmk biber \
  && rm -rf /var/lib/apt/lists/*

# R
RUN apt-get update && apt-get install -y --no-install-recommends \
    r-base \
  && rm -rf /var/lib/apt/lists/*

# Install Claude Code
RUN npm install -g @anthropic-ai/claude-code

# Match host user
RUN useradd -m -u 1000 henrik
USER henrik

# Python env with common scraping/analysis packages
RUN python3 -m venv /home/henrik/venv
ENV PATH="/home/henrik/venv/bin:$PATH"
RUN pip install --no-cache-dir \
    requests beautifulsoup4 lxml \
    newspaper3k trafilatura \
    pandas pyarrow \
    numpy scipy statsmodels matplotlib \
    PyMuPDF mistune \
    linearmodels pydantic python-dotenv html2text \
    openai anthropic \
    SQLAlchemy pyyaml pypdf pytesseract pytest scons \
    git+https://github.com/DarrenZal/otter-mcp.git

# Install uv at the same path the host uses, so .mcp.json works as-is
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Pre-build the whatsapp-mcp-server uv environment at a container-local path
# so the host's .venv (with absolute symlinks into ~/.local/share/uv/python)
# isn't reused. Source is bind-mounted at runtime; deps are pinned via uv.lock.
RUN git clone --depth 1 https://github.com/lharries/whatsapp-mcp.git /tmp/wamcp \
 && UV_PROJECT_ENVIRONMENT=/home/henrik/.cache/uv-envs/whatsapp \
    /home/henrik/.local/bin/uv sync --project /tmp/wamcp/whatsapp-mcp-server --frozen \
 && rm -rf /tmp/wamcp

# Memory monitor
COPY monitor_memory.sh /usr/local/bin/monitor_memory.sh

WORKDIR /workspace
