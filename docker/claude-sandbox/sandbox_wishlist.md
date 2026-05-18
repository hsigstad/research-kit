# Sandbox tooling wishlist

The current `claude-sandbox.def` ships a minimal stack
(`requests beautifulsoup4 lxml newspaper3k trafilatura pandas openai
anthropic` on debian-slim with `curl git nodejs npm chromium`). The
Dockerfile sibling is more complete but is not what the running .sif
was built from.

This document collects tools whose absence has actually slowed work,
plus those needed for known workflows (R analysis, paper compilation,
site generation, remote sync). Use as input when next rebuilding the
sandbox image.

## Critical — blocks workflows already in use

### R toolchain
- `r-base`, `r-base-dev`
- CRAN packages: `dplyr`, `readr`, `tidyr`, `lubridate`, `arrow`,
  `fixest`, `data.table`, `purrr`, `ggplot2`, `kableExtra`, `knitr`,
  `stringr`, `forcats`, `broom`
- Why: every analysis script in `projects/ficha`, `projects/audit`,
  `projects/saude`, etc. is R. Without R we can write but not test
  refactors.

### TeX Live (for both paper PDF and site HTML)
Recommended packages (debian names):
- `texlive-base`, `texlive-latex-recommended`, `texlive-latex-extra`
- `texlive-bibtex-extra`, `biber`
- `texlive-fonts-recommended`, `texlive-fonts-extra`
- `texlive-science`, `texlive-publishers` (econ classes)
- `texlive-extra-utils` (provides **make4ht** / tex4ht)
- `ghostscript`, `dvisvgm`
- Alternative: `texlive-full` (~5 GB, bulletproof, no per-package guessing)
- Why: `paper/main.tex` won't compile without it. The site skill's
  paper→HTML step (`projects/*/source/site/build_all.py`) reads
  `build/make4ht/main.html` produced by `make4ht` — currently no
  project site can include its paper.

### Python data stack
- `pyarrow`, `polars`, `duckdb`
- `unidecode` (transitive dep of `diarios.clean.text`; blocks any
  `from diarios import ...` outside trivial cases)
- `matplotlib`, `seaborn`, `statsmodels`, `scikit-learn`
- `pyyaml`, `openpyxl`, `beautifulsoup4`
- `psycopg2-binary`, `sqlalchemy` (project Postgres in `user-config.yaml`)
- `mistune`, `python-frontmatter` (site builder uses `mistune`)
- `python-dotenv` (already-installed in Dockerfile, missing in .def)
- Why: pyarrow alone removes the CSV-instead-of-parquet workaround
  forced in `projects/ficha/source/clean/consulta_cand.py`. The rest
  are baseline data-science tooling assumed by most scripts.

### Remote sync + collaboration
- `ssh`, `scp`, `rsync`
- `rclone` (used by `drive` and `dropbox` skills)
- `gh` (GitHub CLI — referenced throughout Claude Code instructions
  for PR/issue/check workflows)
- Why: handoff currently has to go through git push only; large
  artifacts, coauthor PDFs, and educloud round-trips have no path.

### Database CLIs
- `sqlite3` (e.g. `pipelines/politica/build/insert/politica.db`)
- `postgresql-client` (`psql`)
- `duckdb` CLI
- Why: can't inspect any of the SQLite/Postgres artifacts the
  pipelines produce.

### Document conversion
- `pandoc` (used by `literature`, `outlook`, `handoff`, and the site
  skill for markdown handling)
- `pdftotext` (`poppler-utils`)
- `pdfgrep`

## Useful — recurring friction

- `jq` — JSON inspection (LLM cache files, run.json ledgers,
  citation registries)
- `fd-find` (`fd`) — faster file walks
- `parallel` — bulk batch processing in cleaning pipelines
- `tesseract-ocr` + `pdf2image` + `pytesseract` — `diarios.io.ocr_file`
- `imagemagick` — figure post-processing
- `gcc`, `g++`, `make` — needed if any pip install ever has to build
  a C extension (currently most binary wheels work, but the next
  niche package may not)
- Python: `jupyter`, `ipykernel`, `notebook` — interactive exploration
- Python: `pdfplumber`, `PyMuPDF` (mentioned in Dockerfile but missing
  from .def)
- Python: `linearmodels`, `pydantic`, `html2text` (Dockerfile but
  missing from .def)
- Python: `requests-cache`, `tenacity` — for scraping/API loops

## Editor/UX nice-to-haves
- `bash-completion`
- `tmux`
- `vim` / `nano` (debian-slim usually omits `vim`)

## Suggested approach

The Dockerfile in this directory is already much closer to what we
want than the .def file. Two options:

1. **Sync .def to Dockerfile, then add the gaps** (R, TeX Live,
   ssh/rsync, rclone, gh, sqlite3, psql, pandoc, unidecode, polars,
   duckdb, pyarrow + the others above). Rebuild .sif.
2. **Drop .def entirely** and build .sif from the Dockerfile via
   `singularity build --from-dockerfile`. Eliminates the divergence
   problem long-term.

Either way, this list should serve as the diff base.
