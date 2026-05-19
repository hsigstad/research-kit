FROM debian:bookworm-slim

# ── 1a. Core + ca-certificates first (needed for all curl calls) ────
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git ca-certificates wget gnupg2 openssh-client \
    python3 python3-pip python3-venv \
    nodejs npm \
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

# ── 1b. R toolchain ─────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    r-base r-base-dev \
  && rm -rf /var/lib/apt/lists/*

# ── 1c. TeX Live (full — bulletproof, no per-package guessing) ───────
RUN apt-get update && apt-get install -y \
    texlive-full \
  && rm -rf /var/lib/apt/lists/*

# ── 1d. Tools, DB CLIs, doc conversion, editors ─────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    pandoc \
    poppler-utils \
    pdfgrep \
    sqlite3 \
    postgresql-client \
    openssh-client \
    rsync \
    rclone \
    jq \
    fd-find \
    parallel \
    imagemagick \
    tesseract-ocr \
    gcc g++ make \
    unzip \
    bash-completion \
    tmux \
    vim-tiny \
    nano \
  && rm -rf /var/lib/apt/lists/*

# ── 2. GitHub CLI ────────────────────────────────────────────────────
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
 && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
      > /etc/apt/sources.list.d/github-cli.list \
 && apt-get update && apt-get install -y gh \
 && rm -rf /var/lib/apt/lists/*

# ── 3. DuckDB CLI ───────────────────────────────────────────────────
RUN ARCH=$(dpkg --print-architecture) \
 && curl -fsSL "https://github.com/duckdb/duckdb/releases/latest/download/duckdb_cli-linux-${ARCH}.zip" \
      -o /tmp/duckdb.zip \
 && unzip /tmp/duckdb.zip -d /usr/local/bin \
 && rm /tmp/duckdb.zip

# ── 4. Claude Code ──────────────────────────────────────────────────
RUN npm install -g @anthropic-ai/claude-code

# ── 5. Match host user ──────────────────────────────────────────────
RUN useradd -m -u 1000 henrik
USER henrik

# ── 6. Python virtualenv ────────────────────────────────────────────
RUN python3 -m venv /home/henrik/venv
ENV PATH="/home/henrik/venv/bin:$PATH"

RUN pip install --no-cache-dir \
    pandas pyarrow polars duckdb \
    numpy scipy \
    matplotlib seaborn \
    statsmodels scikit-learn \
    unidecode \
    pyyaml openpyxl \
    psycopg2-binary sqlalchemy \
    mistune python-frontmatter \
    python-dotenv \
    requests beautifulsoup4 lxml \
    newspaper3k trafilatura \
    openai anthropic \
    pypdf pdfplumber PyMuPDF \
    pdf2image pytesseract \
    linearmodels pydantic \
    html2text \
    requests-cache tenacity \
    pytest scons \
    jupyter ipykernel notebook \
    git+https://github.com/DarrenZal/otter-mcp.git

# ── 7. R packages (CRAN) ────────────────────────────────────────────
RUN Rscript -e ' \
    install.packages(c( \
        "dplyr", "readr", "tidyr", "lubridate", "arrow", \
        "fixest", "data.table", "purrr", "ggplot2", \
        "kableExtra", "knitr", "stringr", "forcats", "broom" \
    ), repos = "https://cloud.r-project.org", Ncpus = 4) \
'

# ── 8. uv (for MCP server envs) ─────────────────────────────────────
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Pre-build the whatsapp-mcp-server uv environment
RUN git clone --depth 1 https://github.com/lharries/whatsapp-mcp.git /tmp/wamcp \
 && UV_PROJECT_ENVIRONMENT=/home/henrik/.cache/uv-envs/whatsapp \
    /home/henrik/.local/bin/uv sync --project /tmp/wamcp/whatsapp-mcp-server --frozen \
 && rm -rf /tmp/wamcp

# ── 9. Memory monitor ───────────────────────────────────────────────
COPY monitor_memory.sh /usr/local/bin/monitor_memory.sh

WORKDIR /workspace
