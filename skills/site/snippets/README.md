# /site skill — canonical snippets

This directory holds the **canonical text** of helpers that get copied
into project-local files when the /site skill scaffolds or refreshes a
project site. Projects keep their own copies of the surrounding files
(`source/summary/compute.py`, `source/site/templates/dataset.html`) —
the skill just ensures the bits that should be shared *match the
snippet here*.

## How to use this directory

- **Inside the /site skill:** when scaffolding a new project or
  refreshing an existing one, port the snippets listed below into the
  matching project files (overwrite the project's copy if it has
  drifted).
- **As a developer:** when you add a feature that belongs in the
  shared layer (a new detector, a new chart block), edit the snippet
  here *first*, then propagate to every project that already has the
  data-page system.
- **When drift is found:** the diff between a project's helper and the
  canonical snippet is the authoritative diff. The snippet wins unless
  the project has a documented reason to override.

## What's here

| Snippet | Target file in project | Purpose |
|---|---|---|
| `detect_binary.py` | `source/summary/compute.py` (helper block) | Auto-detect binary columns (bool, int ⊆ {0,1}, string ⊆ {"S","N"} / {"Y","N"} / …) and return `{mean, na_pct, true_label}`. Used to populate the `binary` block of the per-dataset cache JSON. |
| `binary_chart_block.html` | `source/site/templates/dataset.html` (JS block) | Renders the `DATA.binary` block as a single horizontal Chart.js bar chart, one row per binary column with NA% annotated. |
| `example_value.py` | `source/summary/compute.py` (helper block) | Return one sampled non-null value per column, truncated for display. Adds an `example` field to each entry in the `columns` list of the cache JSON; the dataset page surfaces it in a new "Example" column on the column-info table. |

## Why not a pip package?

For now the surface is small (one Python helper, one JS block). A pip-
installable `packages/sitekit/` would be overkill for a single
function, but is the natural next home if and when 2–3 more shared
helpers join (e.g. a streaming-mode version of `detect_binary`, a
shared temporal-column detector, or a shared categorical-top-N
helper). When that threshold is crossed, lift the snippets into the
package and have the skill `import` rather than copy.

## When you change a snippet

1. Edit the file under `snippets/`.
2. Open every project's matching file (currently: ficha, fisc, saude,
   procure, poll-sponsor-bias) and port the change. Templates can be
   diffed visually; Python helpers can be diffed with `diff`.
3. Rebuild the affected project's summary cache and site to confirm
   the change renders.
