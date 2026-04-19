---
name: data
description: "Search the data catalog, variable dictionary, and data linkages for datasets, variables, or data sources. Use when the user asks about available data, what variables exist, or how datasets connect across projects."
user_invocable: true
---

# Data Catalog Lookup

Search across the workspace's data documentation to find datasets, variables, and cross-project data linkages.

## Finding the workspace root

The workspace root contains `CLAUDE.md` and subdirectories `projects/`, `pipelines/`, `data_catalog/`, `research/`. If the current working directory is inside a project or pipeline, search upward to find the root. For example, if you're in `projects/deterrence/`, the root is two levels up.

Use `git rev-parse --show-toplevel` or search upward for `CLAUDE.md` with `research/rules/workspace.md` alongside it. Store the resolved root as `$ROOT` for the paths below.

## Where to look

Search these files in order of relevance:

1. **`$ROOT/data_catalog/DATA_CATALOG.md`** (symlink to sibling repo) — master registry of all raw datasets with provenance, structure, and restrictions
2. **`$ROOT/data_catalog/codebooks/`** (symlink) — detailed codebooks per dataset
3. **`$ROOT/research/meta/variable_dictionary.md`** — shared variable definitions used across projects
4. **`$ROOT/research/meta/data_linkages.md`** — how datasets link across projects (join keys, shared identifiers)
5. **Project-level `docs/data.md`** files — in `$ROOT/projects/*/docs/data.md`
6. **Pipeline `docs/data.md`** and `docs/summary.md` — in `$ROOT/pipelines/*/docs/`

## How to search

Based on the user's query:

- **"What data do we have on X?"** — Search DATA_CATALOG.md and codebooks for topic matches. Report: dataset name, provider, coverage, key variables, which projects use it.
- **"What is variable X?"** — Search variable_dictionary.md first, then project data.md files. Report: definition, construction, which datasets contain it, which projects use it.
- **"How do datasets X and Y connect?"** — Search data_linkages.md. Report: join keys, shared identifiers, known issues with linkage.
- **"Which projects use dataset X?"** — Search all project `docs/data.md` files. Report: project name, how they use it, any sample restrictions.
- **"What does pipeline X produce?"** — Read the pipeline's `docs/summary.md` and `docs/data.md`. Report: outputs, coverage, key variables.

## Output format

```
## <Dataset or Variable Name>

**Source:** <provider, access method>
**Coverage:** <time period, geographic scope>
**Key variables:** <list>
**Used by:** <project1, project2, ...>
**Linked via:** <join keys to other datasets>
**Notes:** <restrictions, quality issues, gotchas>
```

If multiple results match, list them all with brief descriptions so the user can drill down.

## Gotchas

- The `data_catalog/` directory contains **symlinks** to a sibling repository. If the symlinks don't resolve, tell the user they need to clone the `data_catalog` repo as a sibling.
- Raw data is in `data/` which is in `.claudeignore` — never try to read raw data files directly. Only use metadata from the catalog.
- Pipeline outputs in `build/` are typically gitignored and may not exist on disk. Describe what they produce based on docs, don't try to read the files.
- Some projects have data that contains PII (party names, case details). Flag this if relevant to the query.
