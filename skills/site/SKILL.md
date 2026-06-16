---
name: site
description: "Generate the static HTML site for a research project. Creates source/site/build_all.py and templates if they don't exist, then builds the site. Use when the user wants to create or rebuild a project site."
user_invocable: true
---

# Project Site Generator

Create and build a static HTML site for a research project.

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
Resolve the project: `$ROOT/projects/{slug}/`.

Read the project's `CLAUDE.md` to get the project title and short description.

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

The reference implementation is **`/home/henrik/research/projects/serasa/build.sh`**.
Port it (adjusting `PROJECT_TITLE` and the paper/talk `.tex` names) to any
project that doesn't have it yet — including projects still on the old
plaintext `gh-pages` push or the legacy `~/hsigstad.github.io/{slug}/` rsync.
`build.sh` wires three functions into a `deploy` mode:

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
