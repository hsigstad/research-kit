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

# ── 1b. R toolchain (from CRAN apt repo for latest R ≥ 4.4) ─────────
# Debian bookworm ships R 4.2.2; newer CRAN packages (Matrix ≥ 1.6, quantreg)
# require R ≥ 4.4. Use CRAN's official Debian repo to get a current R.
# Key fingerprint 95C0FAF38DB3CCAD0C080A7BDC78B2DDEABC47B7 (Johannes Ranke);
# fetched from Ubuntu keyserver since CRAN no longer publishes a stable .asc URL.
RUN mkdir -p /etc/apt/keyrings \
 && curl -fsSL "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0xB8F25A8A73EACF41" \
      -o /etc/apt/keyrings/cran_debian_key.asc \
 && echo "deb [signed-by=/etc/apt/keyrings/cran_debian_key.asc] https://cloud.r-project.org/bin/linux/debian bookworm-cran40/" \
      > /etc/apt/sources.list.d/r-cran.list \
 && apt-get update && apt-get install -y --no-install-recommends \
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
    gcc g++ make cmake \
    libxml2-dev libssl-dev libcurl4-openssl-dev \
    libfontconfig1-dev libfreetype6-dev \
    libharfbuzz-dev libfribidi-dev \
    libpng-dev libtiff5-dev libjpeg-dev \
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

# ── 4b. R packages (CRAN) ───────────────────────────────────────────
# Must run as root (before the USER henrik switch below) so packages land
# in the system library /usr/local/lib/R/site-library, visible to henrik.
# Fails loudly: if any package is missing afterwards the build aborts,
# so a stale image can never silently ship without its R libraries.
# rdd was archived on CRAN (orphaned; last release 0.57), so it is not in the
# current contrib index — install it separately from the CRAN archive by URL.
# Its deps (AER, sandwich, lmtest, Formula) come from the main list below.
RUN Rscript -e ' \
    pkgs <- c( \
        "dplyr", "readr", "tidyr", "lubridate", "arrow", \
        "fixest", "lfe", "data.table", "dtplyr", "purrr", "ggplot2", \
        "kableExtra", "knitr", "stringr", "forcats", "broom", \
        "modelsummary", "did", "sandwich", "lmtest", \
        "haven", "marginaleffects", "tidyverse", \
        "Hmisc", "quantreg", "stargazer", \
        "tinytable", "rdrobust", "rddensity", \
        "estimatr", "jsonlite", "boot", \
        "ggpubr", "gridExtra", "scales", "readxl", \
        "janitor", "AER", "MatchIt", "clubSandwich" \
    ); \
    install.packages(pkgs, repos = "https://cloud.r-project.org", Ncpus = 4); \
    install.packages("https://cran.r-project.org/src/contrib/Archive/rdd/rdd_0.57.tar.gz", repos = NULL, type = "source"); \
    all_pkgs <- c(pkgs, "rdd"); \
    missing <- all_pkgs[!all_pkgs %in% rownames(installed.packages())]; \
    if (length(missing)) { cat("FAILED to install:", missing, "\n"); quit(status = 1) } \
'

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
    linearmodels pydantic pyreadr \
    html2text \
    requests-cache tenacity \
    pytest scons \
    jupyter ipykernel notebook \
    playwright \
    google-cloud-bigquery google-cloud-storage \
    tabulate tqdm \
    git+https://github.com/DarrenZal/otter-mcp.git

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
