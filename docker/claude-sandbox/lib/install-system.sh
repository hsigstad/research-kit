#!/usr/bin/env bash
# Shared system-level install for the claude-sandbox image.
# Sourced identically by the Docker build (COPY + RUN) and the Apptainer
# build (%files + %post). Runs as root. Keep this the SINGLE source of truth
# for apt packages, TeX Live, the R toolchain, and the root-level CLIs —
# editing it once keeps the laptop (Docker) and educloud (Apptainer) images
# in lockstep. See lib/install-r.sh and lib/install-python.sh for the rest.
set -euo pipefail

# ── 1a. Core + ca-certificates first (needed for all curl calls) ────
apt-get update && apt-get install -y --no-install-recommends \
    curl git ca-certificates wget gnupg2 openssh-client \
    python3 python3-pip python3-venv \
    nodejs npm \
    chromium chromium-driver \
    rsync pandoc \
  && rm -rf /var/lib/apt/lists/*

# TeX Live (curated subset: latexmk, biber, make4ht, common paper packages)
apt-get update && apt-get install -y --no-install-recommends \
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
mkdir -p /etc/apt/keyrings
curl -fsSL "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0xB8F25A8A73EACF41" \
    -o /etc/apt/keyrings/cran_debian_key.asc
echo "deb [signed-by=/etc/apt/keyrings/cran_debian_key.asc] https://cloud.r-project.org/bin/linux/debian bookworm-cran40/" \
    > /etc/apt/sources.list.d/r-cran.list
apt-get update && apt-get install -y --no-install-recommends \
    r-base r-base-dev \
  && rm -rf /var/lib/apt/lists/*

# ── 1c. TeX Live (full — bulletproof, no per-package guessing) ───────
apt-get update && apt-get install -y \
    texlive-full \
  && rm -rf /var/lib/apt/lists/*

# ── 1d. Tools, DB CLIs, doc conversion, editors ─────────────────────
apt-get update && apt-get install -y --no-install-recommends \
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
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    -o /usr/share/keyrings/githubcli-archive-keyring.gpg
ARCH=$(dpkg --print-architecture)
echo "deb [arch=${ARCH} signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    > /etc/apt/sources.list.d/github-cli.list
apt-get update && apt-get install -y gh \
  && rm -rf /var/lib/apt/lists/*

# ── 3. DuckDB CLI ───────────────────────────────────────────────────
curl -fsSL "https://github.com/duckdb/duckdb/releases/latest/download/duckdb_cli-linux-${ARCH}.zip" \
    -o /tmp/duckdb.zip
unzip /tmp/duckdb.zip -d /usr/local/bin
rm /tmp/duckdb.zip

# ── 4. Claude Code ──────────────────────────────────────────────────
npm install -g @anthropic-ai/claude-code
