---
name: site
description: "Generate the static HTML site for a research project. Creates source/site/build_all.py and templates if they don't exist, then builds the site. Use when the user wants to create or rebuild a project site."
disable-model-invocation: true
---

# Project Site Generator

Create and build a static HTML site for a research project.

## Status of the canonical implementation

The rendering machinery lives in the **`sitekit`** package under
`research-kit/sitekit/`. Each project's `source/site/build_all.py` is a
thin shim that hands a `SiteConfig` to `sitekit.build_site()`.

**Migrated to sitekit:** `audit`, `campaign-finance`, `deterrence`,
`electoral-justice`, `fisc`, `judgeGPT`, `poll-sponsor-bias`, `promotor`,
`serasa`, `vague`, `lawsuit`, `scheme`, `segredo`, `connect` (minimal +
empirical), and `bind` (theoretical). For migrated projects, verification is
content-parity of each rendered doc body against the pre-migration output plus
intended convergence of the chrome onto the shared design system — NOT
byte-equivalence (that only held for `serasa`, whose templates *were* the
extraction source; other projects had drifted chrome the migration deliberately
normalizes). The standard acceptance check the recent migrations used: page-set
diff (0 lost), body-text parity (~1.0; sub-1.0 is pure CSS-var normalization),
and "new broken-link set ⊆ baseline broken-link set" (the migration introduces
no broken links; pre-existing stale source refs stay pre-existing).

**Not yet migrated — each is a DEDICATED effort blocked on a specific host or
build, NOT a batch slot** (verified by attempted migrations 2026-08-31, which
correctly refused to force a lossy/unverifiable rewrite of coauthor-facing
sites):
- `procure` — coauthor-facing + validation-gated; ~2,500 loc of bespoke
  subsystems to port as hooks: a paper page with validation-ledger UI +
  number-attribution tooltips + feedback-worker (the blocker — 850 loc of
  bespoke UI that can't be built/verified without a **TeX host**), a dataset
  portal (`build/summary/*.json`, different schema than the empirical archetype),
  a 1,111-loc `build_cases.py` cases renderer, validation + election-RD pages,
  and a chip-filtered AN index. ~40% maps to stock. Needs a **TeX-capable host**.
  Deploys **plaintext-public** → run a PII/sensitive compliance audit before any
  redeploy (sitekit build newly copies `build/figure` + `build/analysis` PNGs
  and stops shipping `main.pdf`).
- `ficha` — empirical, 476 pages (231 script pages dominate), **coauthor-facing**.
  Needs a **TeX host**: its bespoke paper page (inline-footnote reconstruction,
  `\newcommand` macro substitution, side-rail TOC, figure-path rewrite) has no
  cached `build/make4ht/paper.html` in-sandbox, so it can't be diffed — don't
  port it blind. Also renders everything FLAT at site root with a bespoke
  autolink layer (`an_file_map`, `link_h_refs`, `autolink_build_artifacts`,
  `rewrite_build_artifact_paths`), so flat→nested is a full link-layer
  reimplementation (verify by new-broken⊆baseline), not a config migration.
  4 bespoke builders to port as hooks (`copy_build_artifacts` copies
  PDF+PNG+tables to `figure/`+`table/`, `autolink_build_artifacts`, ~300-line
  `build_key_artifacts_page`, note asset-folder copies) — the artifact copy needs
  a **pre-docs hook** (`copy_site_figures` is pre-docs but `config.hooks` are
  post-docs); add `SiteConfig.pre_docs_hooks` *with* ficha as its first consumer
  (don't land it unexercised). Verifiable-in-sandbox parts: docs, 82 analyses,
  hypotheses, findings, subdirs, 231 script pages, 2 dataset pages, key_artifacts.
  Fold in a check of the possibly-stale `docs/reference/analysis-index.yaml`.
- `saude` — empirical; ~30% maps to stock (top-level docs + stock cached
  paper). LIVE bespoke subsystems needing hooks: a news timeline
  (`references/news/stories.csv` → `news.html`) and an 18-source references
  index (`references/` → `references.html`); notebooklm is dead (droppable).
  Dataset portal reads an empty summary cache in-sandbox → needs a **data host**
  to regenerate the cache and verify dataset pages.
`rol` is **intentionally NOT migrated** (decision 2026-08-31, Henrik): it's not
a docs site but a bespoke claim-graph knowledge base (14 typed node types,
strand cross-cut indexes, an interactive graph explorer + generated
`site-data.js`, a linear book). Its deploy is already on the shared
`site_deploy.sh`, and a graph archetype would be single-consumer code in shared
sitekit, so rol stays on its own `build_all.py`. Do not force it onto `minimal`
(catastrophic content loss) and do not re-open this without a second graph
consumer to justify the archetype.

For unmigrated projects the old archetype-reference workflow is still
authoritative: copy `build_all.py` + `templates/` from the matching
canonical reference and customize. For new projects, prefer the sitekit
path (see "Using sitekit" below).

The **empirical** archetype (fisc, poll-sponsor-bias, connect's docs-heavy
variant) and the **theoretical** archetype (`bind` — cases discovery +
per-case pages via a project `cases.html`, grouped cases index,
`extra_tex_pages` for holdings-style companion LaTeX, plus a citations hook)
are both real and exercised, as are the AN-page / cite-ref / anecdote /
findings / hypotheses / script-page passes. Still a stub: any **graph**
archetype (`rol`). sitekit also gained `SiteConfig.exclude_stems` (keep
specific subdir notes off a PUBLIC site) during this work.

## Arguments

- `/site` -- create site scaffold + build for the current project
- `/site [project-slug]` -- target a specific project

## What the site contains

- **Index page** -- landing page with paper/talk hero cards and docs grouped by category
- **Doc pages** -- each `docs/*.md` file rendered as HTML with a table of contents linking to h2/h3 sections, image lightbox, anchor linking, Hypothes.is annotation layer
- **Paper page** -- LaTeX paper converted to HTML via make4ht, with inline footnote tooltips, MathJax, Hypothes.is annotation layer
- **Talk page** -- beamer slides converted to HTML via make4ht

## Step-by-step

### 1. Locate project

Find workspace root by searching upward for `CLAUDE.md` next to `projects/` and `pipelines/`.
Resolve the target: `$ROOT/projects/{slug}/` **or `$ROOT/pipelines/{slug}/`** — a slug can
name either. If `/site foo` is given, check both trees; pipelines are as valid a target as
projects.

Read the target's `CLAUDE.md` to get the title and short description.

**Pipeline repos differ from project repos** in three ways — mind them throughout:

1. **Deploy plumbing.** Pipeline `build.sh` sources the shared
   `research-kit/tools/site_deploy.sh` (providing `sk_encrypt_site` /
   `sk_deploy_site`) and sets `SITE_TITLE` + a `SITE_GATED` toggle, rather than
   inlining the staticrypt/rsync logic. Public data-reconstruction pipelines set
   `SITE_GATED=0` (plaintext, e.g. `lovhistorie`); pipelines documenting access
   to sensitive/geoblocked raw data set `SITE_GATED=1` (default — gated, e.g.
   `govspend`). Model a new pipeline `build.sh` on `pipelines/lovhistorie/build.sh`
   (public) or `pipelines/govspend/build.sh` (gated), NOT on `serasa/build.sh`.
2. **`source/` may not be a package.** Pipelines often run scrape/clean scripts
   directly, so `source/__init__.py` can be absent; `python3 -m source.site.build_all`
   needs it. Create empty `source/__init__.py` and `source/site/__init__.py` if missing.
3. **Usual archetype is `minimal` (docs-only) or `empirical` (data portal)** — a
   pipeline rarely has a `paper/`, so set `paper_title=""` and a
   `paper_placeholder_msg` that says "this is a pipeline". `lovhistorie` is the
   canonical minimal pipeline; `govspend` the canonical empirical pipeline (source
   cards over raw + clean tables — see "Empirical data portal for a pipeline" below).

### 2. Check if site already exists

If `source/site/build_all.py` already exists:
- Ask the user if they want to rebuild only (run the existing script) or regenerate the scaffold.
- If rebuild only: skip to step 5.

### 3. Create site scaffold

Create the following files using the canonical templates below.

#### Directory structure

```
source/site/
  build_all.py          # main generator script
  templates/
    index.html          # landing page
    doc.html            # docs page (markdown rendered)
    paper.html          # paper page (make4ht content)
    talk.html           # talk/slides page (make4ht content)
```

#### Customization points

When creating the scaffold, customize these project-specific values:

1. **`PROJECT_TITLE`** -- short title for the nav brand (e.g., "Causal Judge", "Corruption Networks"). Read from project's `CLAUDE.md` first line heading or `docs/summary.md`.
2. **`PAPER_TITLE`** -- full paper title for paper/talk page headers. Read from `paper/main.tex` or `paper/paper.tex` (`\title{...}`), or fall back to `docs/summary.md` heading.
3. **`DOC_REGISTRY`** -- list of (path, title, description, category) tuples. Scan `docs/` for existing `.md` files and register them using the standard mapping:

| File | Title | Category |
|------|-------|----------|
| summary.md | Research Summary | Reference |
| institutions.md | Institutional Background | Reference |
| data.md | Data Sources | Reference |
| methods.md | Methods | Reference |
| literature.md | Literature | Reference |
| thinking.md | Open Questions & Ideas | Working notes |
| decisions.md | Key Decisions | Working notes |
| outline.md | Paper Outline | Working notes |
| hypotheses.md | Hypotheses | Working notes |
| desiderata.md | Desiderata | Working notes |
| todo.md | Active Tasks | Tasks |
| done.md | Completed Tasks | Tasks |
| meetings.md | Meeting Notes | Communication |
| feedback.md | External Feedback | Communication |

Only include files that actually exist in the project's `docs/` directory.
If there are `.md` files not in this table, add them with a sensible title and the "Reference" category.

### 4. Write the files

#### Using sitekit (preferred path for new projects and serasa-style minimal projects)

Two files in `source/site/`:

```python
# source/site/build_all.py — thin shim
import sys
from pathlib import Path
_SITEKIT = (
    Path(__file__).resolve().parent.parent.parent.parent.parent
    / "research-kit" / "sitekit"
)
if str(_SITEKIT) not in sys.path:
    sys.path.insert(0, str(_SITEKIT))

from sitekit import build_site
from source.site.site import config

if __name__ == "__main__":
    raise SystemExit(build_site(config))
```

```python
# source/site/site.py — config + project-local hooks
from pathlib import Path
from sitekit import SiteConfig

config = SiteConfig(
    project_root=Path(__file__).parent.parent.parent,
    project_title="…",
    paper_title="…",
    archetype="minimal",        # or "empirical" / "theoretical" / "mixed"
    paper_tex="paper.tex",
    talk_tex="talk.tex",
    doc_registry=[
        ("docs/summary.md", "Research Summary", "...", "Reference"),
        # ...
    ],
)
```

The sitekit package bundles default `templates/`. A project can override any
one by placing a same-named file under its `source/site/templates/`: project
files take precedence over package files.

When the project needs an extra section that doesn't generalize (e.g.
serasa's specs-for-Ramon dropdown, BCB results gallery), write it as a hook
callable in `site.py` and add it to `config.hooks`. The hook receives a
`BuildContext` and may return `{"extra_cards": "<html>"}` to inject content
above the index's standard doc-group grid.

On `educloud` the system venv is read-only, so the `sys.path` shim in
`build_all.py` replaces `pip install -e`. On a writable env you can
substitute `pip install -e ../../research-kit/sitekit` and drop the shim.

#### Empirical data portal (`archetype="empirical"`) — extra wiring

The data portal (source-card landing grid → per-source pages → per-table pages
with columns / example rows / histograms) needs more than the `site.py` shim.
Gotchas, learned building `govspend` (canonical empirical **pipeline**):

- **sitekit does NOT bundle `dataset.html`, `source.html`, or `index.html`.** The
  empirical archetype raises `TemplateNotFoundError: dataset.html` unless the
  project supplies them under `source/site/templates/`. Copy all three from
  `projects/fisc/source/site/templates/` (the canonical empirical set), then edit
  only `index.html`'s `<title>` and `summary-box` for the new project. The
  bundled `index.html` has NO `<!-- INJECT_SOURCE_CARDS -->` marker, so **without
  a copied `index.html` the landing page silently omits the source cards** even
  though the source/dataset pages build fine — always verify the index actually
  links `sources/*.html` after building.
- **Two-stage build.** `source/summary/{config,compute,build_all}.py` computes a
  per-dataset JSON cache (`source/summary/cache/*.json`, committed to git so the
  site rebuilds without raw data); the site reads that cache. `build.sh` needs a
  `summary` mode (`python3 -m source.summary.build_all [--force|--only <id>]`)
  separate from `site`. Model `config.py`/`compute.py` on
  `projects/fisc/source/summary/`.
- **`config.py` contract:** `SOURCES` (list of `SourceConfig(id, name,
  description, categories)`) + `DATASETS` (list of `DatasetConfig`, each with a
  `category` in exactly one source's `categories`) + a `CACHE_DIR`. Source group
  pages only build if **every** source has non-empty `categories`.
- **Big / heterogeneous data (pipeline-scale):** fisc's `compute.py` does a single
  `read_parquet` — fine for projects, not for a pipeline with 500M-row
  partitioned dirs or JSONL raw. `govspend`'s `compute.py` is the reference for:
  exact `row_count` from Parquet **footer metadata** (no data read) + a
  **stratified** sample of parts spread across the partition list (NOT the first N
  — a `{uf}-{year}` layout sampled first-N yields an all-Amazonas histogram);
  **skip 0-row parts** (BigQuery exports leave padding files that zero out stats);
  a JSONL reader; and **CPF masking** (`[CPF]` for CPF-shaped values + a
  `mask_columns` list for person-name columns) — do this even on a gated site.
  Firm CNPJs/names stay visible; individual CPFs never surface. Note CEIS/CNEP-style
  **public naming registries** are the exception — leave party names visible, mask
  only CPFs. Record a `stats_scope` note (which/how many parts scanned).
- **Full-text corpora (gazettes, court text, etc.) OOM a naive read.** A `text`
  column of multi-KB documents times the scanned rows is gigabytes — a whole-part
  `read_parquet` gets the process **silently OOM-killed** (looks like an empty exit
  when piped through `grep`; symptom: only the first 1–2 caches written, no error).
  `diario-municipal`'s `compute.py` is the reference: read a **row-bounded first
  batch** via `pq.ParquetFile(f).iter_batches(batch_size=…)` (a ~20k-row budget
  spread across the stratified scan parts) instead of loading whole parts, and
  **truncate sample-row cells** (~240 chars) so a dataset page doesn't embed
  megabytes of raw act text. When a build "completes" with a near-empty cache and
  no error, suspect OOM on a `text` column — run the build in the foreground
  (unpiped) to see the real output.
- **Raw vs clean pages:** show a raw table page only where the clean layer drops
  fields the raw carries (or the raw has no clean equivalent); otherwise the clean
  table is the faithful view. Channels whose raw is ZIP/nested dumps (not cleanly
  tabular) are represented by their clean tables with a feeder note in
  `source_notes`.
- **Turn off `build_descriptives` / `build_tables`** in `SiteConfig` for a
  pipeline with no paper-style `build/figure` + `build/table`; the data portal is
  the content. A stray aggregate `build/figure/*.png` still gets copied into
  `build/site/figures/` (unencrypted on a gated site) — confirm it carries no PII
  or drop it.
- **Coverage checkerboard (high-value landing hero).** Both `govspend` and
  `diario-municipal` ship a `source/summary/coverage.py` (writes a committed
  `coverage.json`: a UF × data-type × **year** cube) + `source/figure/
  coverage_matrix.py` (small-multiples — each cell a mini year-histogram on a
  fixed shared x-axis, bar height ∝ √count normalized within column, tri-state
  green/amber/blank color), embedded on the index via an `<img>` the copied
  `index.html` template references. Copy both. Compute the cube cheaply/exactly:
  UF and year from `{uf}-{year}` partition **filenames** + footers where possible,
  else read just the uf + year/date columns; derive UF from `ibge7` (first two
  digits = IBGE state code) when there's no uf column. Pick the amber="partial"
  semantics per pipeline: govspend uses it for platform-limited/incomplete columns
  (BLL, aditivos), diario for recall-limited **derived extractions** vs complete
  **corpus text**. Name capability columns honestly ("Bids · incl. losers", not
  "full rolls") and verify surprising ones against the data before shipping.

#### Using the legacy fork-and-customize pattern (for archetype-rich projects until they migrate)

Pick the canonical reference that matches the project's archetype, then copy
its `build_all.py` and `templates/` as a starting point. Both archetypes share
the same design system (palette, typography, nav, summary-box, Reading Guide,
All Documentation) — they differ only in what middle sections appear on the
landing page and what auxiliary templates exist.

| Archetype   | Canonical reference                                  | What's distinctive                                                                |
|-------------|------------------------------------------------------|------------------------------------------------------------------------------------|
| Theoretical | `/home/henrik/research/projects/bind/source/site/`   | Cases section + per-case pages; *Results at a Glance* propositions table; briefs   |
| Empirical   | `/home/henrik/research/projects/fisc/source/site/`   | Data Sources grid + per-source / per-dataset pages; Descriptives + Tables pages    |

How to tell which archetype:

- **Theoretical** if the project's `paper/` is a formal model (propositions,
  theorems, proofs), the docs include `propositions.md` / `holdings.md` /
  case extractions, and there's no `data_catalog/`-backed parquet dataset list.
- **Empirical** if the project has descriptive figures/tables backed by data
  pipelines, `source/figure/` and `source/table/` scripts, and a `summary/`
  cache of dataset metadata.
- **Mixed** projects exist (e.g. an empirical paper with a small theory
  appendix). Pick the archetype that matches the *primary* output and add
  the secondary archetype's sections on top of it.

Then customize what you copied:

- **`build_all.py`**: update `PROJECT_TITLE`, `PAPER_TITLE`, `DOC_REGISTRY`,
  and the `.tex` filenames if they differ. Drop archetype-specific scaffolding
  the new project doesn't need (e.g. `AREA_MAP` / `TOPIC_MAP` / `cases.html`
  if you copied bind into an empirical project). Also make sure it: wipes
  `SITE_DIR` at the start of each build (so renamed/removed sources don't
  linger as stale files); does **not** copy `paper.pdf` / `talk.pdf` into the
  site (staticrypt encrypts only HTML — a shipped PDF would be readable by
  direct URL; the make4ht HTML render is the paper page); and contains **no
  deployment logic** of its own (no `DEPLOY_DIR`, no rsync to
  `~/hsigstad.github.io` — deployment is `build.sh`'s job, see step 6).
- **Cite-ref machinery**: if the project has (or will have) a
  `docs/literature.md` or `docs/literature/index.md`, the build must turn
  `[cite:<bibkey>]` tokens into hyperlinks per `research/rules/citations.md`.
  The canonical implementation lives in
  `/home/henrik/research/projects/connect/source/site/build_all.py` —
  copy these helpers verbatim:
    - `_load_cite_map()` + `CITE_MAP` (papers with their own
      `docs/literature/<key>.md` page)
    - `_load_bib_authoryear()` + `BIB_AUTHORYEAR` (author-year labels
      parsed from `paper/*.bib`)
    - `_load_index_cite_map()` + `INDEX_CITE_MAP` (papers that appear
      only as `[cite:<key>]`-tagged bullets on the literature index)
    - `_link_cite_refs(html, current_stem)` — resolution order:
      page → index anchor → literal token
    - `_inject_index_cite_anchors(html)` — adds `id="cite-<key>"` to
      `<li>` elements on the literature/index page
  Then wire `_link_cite_refs` into the render pipeline (alongside the
  existing `_link_an_refs` / `_link_h_refs` / `_link_anec_refs` passes)
  and run `_inject_index_cite_anchors` only when rendering
  `docs/literature/index.md`. The CSS rule
  `.md-body li:target { background: #fff8c4; scroll-margin-top: 4rem; }`
  in `templates/doc.html` highlights the bullet you jumped to.
- **Templates**: update `<title>` tags and any paper/talk `<h1>` to use the
  new project's title. Keep all CSS in `:root` and surface colors as-is —
  they are part of the contract below.

The canonical projects are the single source of truth for the *templates*;
do not inline them in this skill. If you find a fully built site that diverges
from the cream palette / nav style / summary-box+Reading Guide skeleton, that's
drift — bring it back in line with the design-system invariants below.

### Design system invariants

Every site must preserve these — they are what makes the projects look like
one cohesive workspace. If you copy from any project that lacks them, fix it
to match.

**Color tokens** (in every template's `:root`):

```css
:root {
  --bg: #faf9f6;       /* warm cream background */
  --card: #fffefa;     /* slightly lighter cream for cards/dropdowns/page-headers */
  --fg: #374151;       /* soft near-black text */
  --muted: #6b7280;    /* secondary text */
  --border: #e5e2db;   /* warm cream border */
  --accent: #2563eb;   /* blue links / left-borders / primary actions */
  --accent2: #198754;  /* secondary green accent (rarely used) */
}
```

**Surface colors** that pair with the cream palette (use these instead of
cool-gray `#f8f9fa` / `#f0f4f8` / `#eef1f5` / `#fafbfc`):

- Code-inline background: `#f0ede6`
- Code-block / blockquote / table-header background: `#f5f3ee`
- Even-row striping: `var(--bg)` (`#faf9f6`)
- Hover surfaces (table rows, dropdown items): `#f5f3ee` (light) or `#f0ede6` (slightly stronger)

**Body text** uses Georgia/Times serif at `1.06rem` / line-height `1.78` on
`.md-body` / paper / brief / case pages; UI chrome (nav, headings, page-header,
table headers) stays on the system sans-serif.

**Sticky top nav** is `background: #212529` with white brand on the left and
muted (`#adb5bd`) link text that brightens on hover. Active link is full white.

**Landing page (`index.html`) structure** — every project's landing page
follows this top-to-bottom shape:

1. `<div class="summary-box">` — one paragraph executive summary, with a
   blue 4px left border. Lives just inside `<main>`.
2. `<h2>Reading Guide</h2>` followed by `<div class="guide-grid">` — a 2-column
   grid of `guide-card` links, each with a small uppercase priority label
   above the title (`priority-start` red, `priority-main` blue, `priority-ref`
   gray) and a one-line description below. The first 1–2 cards are the
   "start here" entry points (paper, talk, lead brief).
3. **Archetype-specific sections** — see below. Reuse `summary-box` /
   table / card vocabulary; never invent a new card style per project.
4. `<h2>All Documentation</h2>` followed by `<div class="doc-groups">` —
   doc cards grouped by category, each group with a colored 3px top border.

Page width is `max-width: 900px` for the index, `42rem` for doc/brief/case
pages. The body font is `.88rem` on the index, `1.06rem` (Georgia serif) on
content pages.

### Archetype-specific sections

The middle of the landing page (step 3 above) and the set of auxiliary
templates differ by archetype. Match these to whatever copy of `build_all.py`
you started from.

**Theoretical projects** (e.g. bind) typically include:

- *Results at a Glance* — one or two `<table class="results-table">` blocks
  listing propositions/corollaries with a one-line "what it says" column and
  a `<span class="badge badge-proved">` / `badge-draft` status pill. Source:
  bind `index.html` lines 142–173.
- *Decisions Needed* — `<ol class="decision-list">` with each `<li>` styled
  as an amber-bordered card auto-numbered `D1, D2, …` via CSS counters.
- *Cases* (or analogous content section): a separate `cases/index.html`
  page grouped by area/topic, plus per-case pages built from
  `cases/extractions/*.md`. Add a "Cases" dropdown to the nav.
- Auxiliary templates: `cases.html` (grouped grid), and a paper template
  that handles multiple `.tex` documents (paper + holdings, etc.).

**Empirical projects** (e.g. fisc) typically include:

- *Data Sources* — `<div class="data-grid">` of `data-card` links, one per
  source group, with a `data-meta` row-count badge (`'533K'`, `'9.8M'`).
  Each card links to `sources/{id}.html`.
- *Descriptives* / *Tables* doc pages — auto-generated from `build/figure/`
  PDFs (converted to PNG) and `build/table/*.md` files; the build script
  appends them to `DOC_REGISTRY` under a "Descriptives" category.
- Auxiliary templates: `dataset.html` (Chart.js histograms + column-info
  table + sample-rows table), `source.html` (group overview with category
  rollups), and optional per-source narrative templates under
  `templates/sources/{id}.html` for groups that have no parquet backing
  (e.g. a docs-only "diários" page). The `dataset.html` template
  includes a **Binary columns** card above the categorical block: one
  horizontal bar per column showing the share of "true" (1 / "S" / "Y"),
  with NA% annotated per row. Binary columns are auto-detected by
  `source/summary/compute.py::detect_binary` from bool dtype, integer
  ⊆ {0,1,NA}, and string ⊆ {"S","N"} / {"Y","N"} / etc. — no manual
  registration. Detected binaries are excluded from the per-column
  value-count chart to avoid double-display.

  **Canonical source of the binary helper:** snippets live in
  [`snippets/`](snippets/) next to this skill —
  [`snippets/detect_binary.py`](snippets/detect_binary.py) for the
  Python detection logic and
  [`snippets/binary_chart_block.html`](snippets/binary_chart_block.html)
  for the JS chart block. When scaffolding a new project (or
  refreshing one whose `compute.py` / `dataset.html` predate the
  binary feature), paste from these files rather than copying from a
  random project. When updating the helper, edit the snippet first
  and propagate to projects.

  **Example-value helper:** the column-info table on each dataset page
  has an "Example" column showing one sampled non-null value per
  column. Canonical helper:
  [`snippets/example_value.py`](snippets/example_value.py). Adds an
  `example` field to each entry in the `columns` list of the cache
  JSON; the template renders it as the rightmost cell in the
  column-info table.

  **Source-script pages:** every `.py` / `.R` / `.sh` / `.sql` under
  `source/` is rendered to its own HTML page at
  `build/site/source/<subpath>.html` with per-line anchors (`#L42`).
  The dataset page's "Source:" line links to it (project-owned scripts
  only — upstream `pipelines/*` references stay plain text). Canonical
  helper: [`snippets/source_pages.py`](snippets/source_pages.py)
  (functions for `find_source_scripts`, `script_out_name`,
  `build_source_pages`, plus the per-line gutter CSS for `doc.html`).

  **Pseudocode block:** assembled datasets get an optional
  `DatasetConfig.pseudocode` field — a short, hand-written summary of
  how the dataset is built, with input-dataset references in `[brackets]`
  that the template rewrites to hyperlinks. Renders as a `<pre>` block
  near the top of the dataset page. Canonical helper:
  [`snippets/pseudocode_block.md`](snippets/pseudocode_block.md). Lets
  the long description / notes paragraphs come down — the construction
  logic lives in one place where every input is clickable.

  **Grain-verification helper:** when a `DatasetConfig.key_columns`
  field is declared (e.g. `key_columns=["cpf", "npu"]`), the dataset
  page renders a tri-state badge in the page header — green ✓
  "Unique on (...)" when the key holds, yellow "!" "Unique but null
  keys on (...)" when there are no duplicates but some rows have null
  values in a key column (typical for left-joined panels), red ✗
  "Grain broken on (...)" when duplicate rows exist. Canonical pair:
  [`snippets/verify_grain.py`](snippets/verify_grain.py) (Python
  helper that emits a `grain_check` block in the cache JSON) and
  [`snippets/grain_check_badge.html`](snippets/grain_check_badge.html)
  (the page-header JS block). The point is end-to-end data-quality
  observable on the page itself: if a future change to the assemble
  script silently breaks grain, the badge flips on the next cache
  rebuild — no separate ledger entry to maintain.
- Talk page (`talk.html`) — empirical projects usually have a beamer talk
  alongside the paper; theoretical ones often don't.

**Mixed**: layer the secondary archetype's sections on top of the primary.
E.g. an empirical paper with theory: start from fisc, add a *Results at a
Glance* table for the theoretical results above the *Data Sources* section.

### 5. Build the site

Run:
```bash
cd $PROJECT_ROOT && python3 -m source.site.build_all
```

Report what was generated (number of doc pages, whether paper/talk were built).

### 6. Deploy: staticrypt-encrypted, to the project's gh-pages branch

This is the canonical deployment for **every** project: the site is
staticrypt-encrypted and pushed to the project's own `gh-pages` branch. One
self-contained command, a readable repo-name URL
(`https://hsigstad.github.io/{repo}/`), and a password gate so the private
research content isn't readable by anyone who stumbles on the URL. There is no
separate plaintext push or `~/hsigstad.github.io/{slug}/` personal-website
step — that legacy approach is retired.

The reference implementation is **`/home/henrik/research/projects/serasa/build.sh`**
(self-contained, project style). Port it (adjusting `PROJECT_TITLE` and the
paper/talk `.tex` names) to any project that doesn't have it yet — including
projects still on the old plaintext `gh-pages` push or the legacy
`~/hsigstad.github.io/{slug}/` rsync.

**Pipeline repos take the shared-helper route instead** (see step 1): their
`build.sh` sources `research-kit/tools/site_deploy.sh` and calls its
`sk_encrypt_site` / `sk_deploy_site` — no inlined staticrypt/rsync. Set
`SITE_GATED=0` for a public pipeline (`pipelines/lovhistorie/build.sh`) or leave
it gated (default 1) for a sensitive one (`pipelines/govspend/build.sh`). Same
gh-pages / repo-name-URL / password-gate outcome as below.

The self-contained `build.sh` wires three functions into a `deploy` mode:

- **`build_site`** — make4ht for paper/talk, then `python3 -m source.site.build_all` → `build/site/` (plaintext).
- **`encrypt_site`** — staticrypt over `build/site/` → `build/site-encrypted/`:
  ```bash
  STATICRYPT_PASSWORD="$pw" npx --yes staticrypt build/site \
      --recursive --directory build/site-encrypted \
      --config build/.staticrypt.json \
      --short --template-title "<PROJECT_TITLE>" \
      --template-instructions "Enter the shared password to access the site." \
      --remember 30
  ```
  staticrypt keeps the input dir's basename, so flatten `build/site-encrypted/site/`
  up one level afterward. `--config build/.staticrypt.json` keeps the salt
  artifact out of the repo root.
- **`deploy_site`** — clone the `gh-pages` branch to a tmpdir (orphan-init it if
  absent), `rsync -a --delete` from **`build/site-encrypted/`** (not `build/site/`),
  write `robots.txt` with `Disallow: /`, commit, push.

`deploy` mode chains them: `build_site; encrypt_site; deploy_site`. Run with:
```bash
cd $PROJECT_ROOT && bash build.sh deploy
```
Requirements: `npx` (for staticrypt) and git push access to the project repo.
`site_deploy.sh` clones/pushes gh-pages over **SSH** (`git@github.com:…`)
regardless of the repo's `origin` URL, so the deploy works even when `origin` is
HTTPS. But **committing the source** to an HTTPS-origin repo fails here (no
credential helper: `could not read Username for 'https://github.com'`) — push via
token instead: `git push "https://x-access-token:${GH_TOKEN}@github.com/<owner>/<repo>.git" HEAD:main`
(leaves `origin` untouched). SSH-origin repos push normally.

**The site password.** Each project gets its own, stored in a gitignored
`.site-password` at the project root (also read from `$STATICRYPT_PASSWORD`).
Pick a memorable phrase tied to the project's *topic*, in three-word
hyphen-slug form (`aaa-bbb-ccc`) — for Brazil law/economics projects, a
Portuguese legal term or a phrase from the subject matter. Example: serasa uses
`dano-moral-presumido` (the "presumed moral damage" doctrine central to its
cases). When setting up a new site, propose a password in this style, write it
to `.site-password`, and tell the user what it is — it is not secret *from* the
user, they need it to view the site. Add both `.site-password` and
`.staticrypt.json` to the project `.gitignore`.

### 7. Verify

Check that `build/site/index.html` exists and list the generated files. After a
deploy, confirm `https://hsigstad.github.io/{repo}/` serves the staticrypt
password gate (look for `class="staticrypt-html"` / "Enter the shared password")
— on a sub-page too, not just the index.

## Important rules

- **Never modify templates in other projects** -- each project gets its own copy.
- **The design system (CSS, nav bar, JS) must be identical** across all projects for visual consistency.
- **All sites include `robots.txt` with `Disallow: /`** and `<meta name="robots" content="noindex, nofollow">` -- these are private research sites.
- **The deployed site is staticrypt-encrypted and pushed to the project's `gh-pages` branch** -- see step 6. `bash build.sh deploy` is the one canonical deploy path; there is no plaintext or personal-website publish step.
- **Never ship sensitive non-HTML assets into `build/site/`** -- staticrypt encrypts only HTML, so PDFs/CSVs/images would be readable by direct URL. The only non-HTML file in a deployed site should be `robots.txt`.
- **Paper/talk pages are optional** -- if `build/make4ht/` doesn't exist, the build skips them gracefully and shows a placeholder card on the index.
- **Don't add data portal features** (dataset cards, Chart.js) unless the user explicitly asks. The default is the docs-only pattern.
