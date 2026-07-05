#!/usr/bin/env bash
# Shared Python virtualenv + package install for the claude-sandbox image.
#
# Usage: install-python.sh <venv-dir> [extra-pip-package ...]
#
# The venv dir differs by engine (Docker installs to /home/henrik/venv as the
# henrik user; Apptainer installs to /opt/venv as root), and the Docker build
# passes extra packages the educloud image intentionally omits (e.g. otter-mcp).
# The common package list below is the single source of truth for both.
set -euo pipefail

VENV_DIR="${1:?usage: install-python.sh <venv-dir> [extra-pip-package ...]}"
shift
EXTRA_PKGS=("$@")

python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --no-cache-dir \
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
    tabulate tqdm

if [ ${#EXTRA_PKGS[@]} -gt 0 ]; then
    "$VENV_DIR/bin/pip" install --no-cache-dir "${EXTRA_PKGS[@]}"
fi
