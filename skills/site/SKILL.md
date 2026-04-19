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
- **Doc pages** -- each `docs/*.md` file rendered as HTML with collapsible sections (open by default), image lightbox, anchor linking, Hypothes.is annotation layer
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

Use the reference implementation from `/home/henrik/research/projects/deterrence/source/site/` as the canonical template:

- **`build_all.py`**: Copy the structure from `deterrence/source/site/build_all.py`, updating:
  - `PROJECT_TITLE` variable and nav brand text
  - `PAPER_TITLE` for paper/talk page headers
  - `DOC_REGISTRY` based on which docs exist
  - Paper/talk `.tex` filenames if different from `paper.tex`/`talk_short.tex`

- **Templates**: Copy from `deterrence/source/site/templates/`, updating:
  - `<title>` tags to use the project title
  - Paper/talk page `<h1>` to use the paper title
  - No other changes needed -- the design system is shared

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
`/home/henrik/research/projects/deterrence/build.sh` (clone gh-pages branch to
tmpdir, rsync build/site/, commit, push).

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
