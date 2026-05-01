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
  if you copied bind into an empirical project).
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
  (e.g. a docs-only "diários" page).
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

### 6. Deploy to project GitHub Pages

If the project has a `build.sh` with a `deploy_site` function, run:
```bash
cd $PROJECT_ROOT && bash build.sh site
```
This pushes to the project's own `gh-pages` branch (e.g. `hsigstad/deterrence` gh-pages).

If `build.sh` doesn't have a deploy step yet, create one following the pattern in
`/home/henrik/research/projects/bind/build.sh` or `fisc/build.sh` (clone
gh-pages branch to tmpdir, rsync build/site/, commit, push).

### 7. Optionally publish to personal website

**Ask the user** whether they also want the site published on `https://hsigstad.github.io/{slug}/`.
Do NOT publish automatically — only if the user confirms.

If yes:
```bash
rsync -a --delete "$PROJECT_ROOT/build/site/" ~/hsigstad.github.io/{slug}/
cd ~/hsigstad.github.io && git add {slug}/ && git commit -m "Update {slug} site" && git push
```

### 8. Verify

Check that `build/site/index.html` exists and list the generated files.

## Important rules

- **Never modify templates in other projects** -- each project gets its own copy.
- **The design system (CSS, nav bar, JS) must be identical** across all projects for visual consistency.
- **All sites include `robots.txt` with `Disallow: /`** and `<meta name="robots" content="noindex, nofollow">` -- these are private research sites.
- **Paper/talk pages are optional** -- if `build/make4ht/` doesn't exist, the build skips them gracefully and shows a placeholder card on the index.
- **Don't add data portal features** (dataset cards, Chart.js) unless the user explicitly asks. The default is the docs-only pattern.
