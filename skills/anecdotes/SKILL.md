---
name: anecdotes
description: Collect anecdotal news evidence about a project's topic from Brazilian news outlets (or broader for non-Brazil projects) using the newsbr package. Discovers articles, fetches full text, appends to references/news/stories.csv, and writes a search audit log.
---

# /anecdotes — Collect news evidence for a project

When invoked, gather news/anecdotal evidence relevant to the current project's
research topic and store it under `references/news/` using the canonical
newsbr layout.

## What you do

1. **Read project context** to figure out what to search for:
   - `<project>/CLAUDE.md` (current focus, key terms)
   - `<project>/docs/summary.md` (research question)
   - `<project>/paper/main.tex` introduction, if present
   - `<project>/README.md`

2. **Decide if the project is Brazil-focused.** Most projects in this
   workspace are. If non-Brazil, expand outlet selection accordingly (see
   "Non-Brazil mode" below).

3. **Propose 3–8 search queries** covering different angles of the topic.
   Show them to the user before running. Briefly explain why each query.
   Wait for confirmation unless the user said "go ahead" up front.

4. **Run newsbr collect** for each approved query, against the relevant
   outlets:

   ```bash
   python3 -m newsbr collect \
     --project <project_root> \
     --query "<query>" \
     --outlets migalhas,folha,estadao,globo \
     --max-pages 1 \
     --context "/anecdotes for <project>"
   ```

   Always pass `--context` so the audit log captures who/why.

5. **Report back** what was added: number of new articles per outlet,
   total added, and the path to `search_log.md`. If you saw notable
   articles, mention 2–3 by title.

6. **Update `docs/notes/anecdotes.md`** (create if missing) with a brief
   one-line entry per session listing the queries run and how many
   articles were collected. This is a human-curated complement to the
   machine-readable search_log.md. Do not duplicate the article list.

## Outlet selection guide

| Outlet | Strength | Notes |
|--------|----------|-------|
| `migalhas` | Legal news, free, native search | Default for legal/judicial topics |
| `folha` | National news, paywalled | Requires Chrome login; native search |
| `estadao` | National news, JS paywall (text in HTML) | Topic + RSS keyword discovery |
| `globo` | National news, paywalled | Sitemap scan, requires Chrome login |
| `conjur` | Legal news, free | **fetch-only** (Cloudflare blocks search). Use `newsbr fetch --file references/news/curated_*.txt` for hand-collected URLs |
| `piaui` | Long-form investigative | Sitemap scan, requires Playwright + Chrome login |

For most legal/judicial projects start with `migalhas,folha,estadao` —
fast and high signal. Add `globo` for political/economic topics.

## Storage layout

newsbr writes everything under `<project>/references/news/`:

```
stories.csv          date,outlet,title,url,theme,summary,paywalled
texts/NNN.txt        full article body, 1-indexed zero-padded
search_log.md        audit trail (newsbr appends to this)
curated_*.txt        hand-curated URL lists for fetch-only outlets
```

Themes are left blank by newsbr — fill them in later by hand or via
project-specific classification.

## Non-Brazil mode

If the project isn't Brazil-focused (rare in this workspace — check
CLAUDE.md), the baseline outlet list still works for any English query
that has Portuguese coverage, but you should also:

1. Tell the user newsbr is Brazil-biased and ask for fallback outlets.
2. Skip Brazilian-only outlets (`migalhas`, `conjur`, `piaui`).
3. Suggest the user use Web Search for non-Brazil sources, then pass
   discovered URLs to `newsbr fetch --file urls.txt`.

## Adding new outlets

Outlet modules live in `packages/newsbr/newsbr/outlets/`. To add one,
create `<name>.py` exposing `NAME`, `DOMAIN`, `STATUS`, `SEARCH`,
`search()`, and `fetch()`. Then add the short name to `OUTLET_NAMES`
in `outlets/__init__.py`.

## Common commands

```bash
# Discover and fetch in one shot
python3 -m newsbr collect --project <root> --query "..."

# Preview without fetching
python3 -m newsbr collect --project <root> --query "..." --dry-run

# Restrict to specific outlets
python3 -m newsbr collect --project <root> --query "..." --outlets migalhas,folha

# Fetch URLs directly (e.g. from a curated list)
python3 -m newsbr fetch --project <root> --file curated.txt
python3 -m newsbr fetch --project <root> --url https://...

# Re-fetch missing texts/NNN.txt files for existing CSV rows
python3 -m newsbr refetch-texts --project <root>

# Show all outlets and their status
python3 -m newsbr outlets
```

## Important rules

- **Never delete or rewrite existing rows** in `stories.csv`. Always append.
- **Always pass `--context`** so the audit trail is interpretable later.
- **Show queries before running.** Don't burn many requests on bad queries.
- **Use `--dry-run` first** when running a new query against a slow outlet
  (globo's sitemap scan can take minutes).
- **The search log is the audit trail.** It's how reviewers will see how
  evidence was gathered. Treat it as part of the paper's methodology.
