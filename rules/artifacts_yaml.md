# `artifacts.yaml` — script ↔ doc reverse index

`docs/reference/artifacts.yaml` is the **reverse-index ledger** for a
project's scripted outputs. For each artifact in `build/table/` or
`build/figure/`, it records the script that produces it and the docs
that cite it. It is the machine-readable companion to the prose
`docs/reference/key-findings.md` and `docs/reference/stylized-facts.md`.

## What problem it solves

You can already go from a finding to its source: open `key-findings.md`,
read the Sources footer, follow the link to `build/table/X.csv`. The
**reverse** direction has no support today — given a script, which
findings depend on it? — and that's exactly the question you need to
answer after a parser fix, data refresh, or sample-definition change.
Without an index, you walk back the dependency graph from memory, and
miss things.

`artifacts.yaml` makes the reverse walk mechanical:

- After a re-run that changes `build/table/X.csv`, look up `X.csv` in
  the yaml → get the list of citing docs → re-verify each entry.
- The `/findings --refresh` skill consumes this file to decide which
  finding entries need a stale-number check.
- The `/next` skill writes a new entry whenever it adds a new
  artifact-citing line to any doc.

This is the **coarse** complement to the inline `@claim` registry: that
operates at the number-token level (one specific value); this operates
at the artifact level (a whole table or figure).

## Schema

```yaml
# Header (optional but recommended)
# ---------------------------------
# version: 1
# updated: 2026-05-11  # ISO date of last hand-edit; not authoritative
# notes: free-text — special conventions, missing-artifact policy, etc.

artifacts:
  - path: build/table/<name>.csv          # required; canonical file path
    script: source/table/<name>.py        # required; producing script
    description: <one short line>         # required; what the artifact shows
    cited_in:                             # required; list of doc paths
      - docs/reference/key-findings.md
      - docs/briefs/<topic>.md
      - paper/main.tex
    tags: [<tag>, <tag>]                  # optional; for filtering
```

### Field semantics

- **`path`** — the canonical artifact path, relative to the project
  root. For multi-format outputs (CSV + Markdown + LaTeX triples), use
  the `.csv` as canonical; sibling `.md` / `.tex` are implicit.
- **`script`** — the producing script, relative to the project root.
  Use the actual `__main__` script that writes the output; not a
  helper imported by it.
- **`description`** — one line, plain prose. Goal: someone reading this
  line knows whether the artifact is relevant to their question without
  opening the CSV.
- **`cited_in`** — list of doc paths. Paths are relative to the project
  root. May include `#anchor` fragments for section-level pointers
  (`docs/reference/key-findings.md#three-exequente-lanes-operate-...`).
  An empty list is valid and means "produced but not yet cited" — still
  worth tracking, because it surfaces unused work.
- **`tags`** — optional; free-form short labels for filtering. Common
  uses: identification design (`d1`, `d2`, ...), hypothesis (`h14`,
  `h6`), substantive cluster (`pgfn`, `tjsp`, `phoenix`).

### What NOT to include

- **Hand-authored content** — files in `paper/figures/` or
  `paper/tables/` that were written by hand (TikZ standalone .tex,
  illustrator diagrams, equation snippets) are out of scope. The yaml
  is for scripted outputs only.
- **Intermediate build artifacts** that no doc cites — parquets in
  `build/clean/`, `build/assemble/`, etc. The yaml indexes things
  *because* a doc points at them; if no doc does, it doesn't belong.
- **`last_updated` per entry** — not useful enough to maintain. If you
  need recency, derive from `git log -- <path>`.
- **Confidence tags** — those are finding-level attributes. The same
  artifact may back a 🟢 claim in one doc and a 🟡 caveat in another.
  Confidence belongs in `key-findings.md`, not here.

## Conventions

### One artifact, one entry

If a script writes four outputs, write four entries — all sharing the
same `script` field. This keeps the reverse-lookup simple: given a path,
exactly one entry resolves.

### Multi-format triples are one entry

fisc-style outputs that emit `.csv` + `.md` + `.tex` from one logical
table belong in **one** entry keyed on the `.csv`. The sibling formats
are auto-generated alternates and don't need separate index lines.

### Sort by path

Entries are sorted alphabetically by `path`. Makes git diffs readable
and merge conflicts narrower.

### Tag the identification design or hypothesis

When an artifact is part of a D-series identification design or a
specific hypothesis test, tag it (`d1`, `h14`, etc.). Lets a future
audit pull all artifacts backing a single design.

## How `/next` maintains the file

`/next` step 5 (propagate to docs) is the canonical write-point:

1. After the run produces `build/table/X.csv`, /next checks whether an
   entry for `X.csv` already exists in `artifacts.yaml`.
2. If yes: it may add new doc paths to `cited_in` if the propagation
   step added a new citation.
3. If no: it creates a fresh entry with the script, description (from
   the script's IAT `INTENT` line), and the docs that step 5 cited it
   in. Tags inferred from the script name or asked from the user.

The yaml should never lag the docs by more than one /next iteration.

## How `/findings --refresh` uses the file

After a pipeline re-run or parser fix:

1. Walk `artifacts.yaml`.
2. For each artifact whose `path` was modified by the re-run (compare
   git status / mtime against last refresh), enumerate `cited_in`.
3. Open each citing doc and re-verify the cited number(s) against the
   new artifact. Flag any drift in a refresh report.
4. Hand control back to the researcher for review.

This is what makes the doc-propagation step robust to surprise
re-runs — the index does the bookkeeping you would otherwise do from
memory.

## Auditing the file

`/findings --audit` should flag:

- Entries whose `path` no longer exists on disk → stale (script was
  renamed or deleted).
- Entries whose `cited_in` doc no longer mentions the artifact → stale
  citation (doc was rewritten without updating yaml).
- Docs that cite a `build/{table,figure}/X` not present in `cited_in`
  for the matching artifact → missing entry.

## Example (excerpt from a fisc-style project)

```yaml
version: 1
notes: |
  Reverse-index for scripted outputs under build/table and build/figure.
  Maintained by /next; audited by /findings --audit. Hand-authored
  artifacts (paper/figures/scheme_timeline.{tex,pdf}, etc.) are out of
  scope.

artifacts:
  - path: build/table/h4_pgfn_cohort_break.csv
    script: source/table/h4_pgfn_filtering_break.py
    description: |
      PGFN inscrição-level cohort break test at Portaria 33/2018 —
      annual share_ajuizado pre vs post, by inscrição year.
    cited_in:
      - docs/reference/key-findings.md
      - docs/outline-companion.md
      - docs/briefs/cross-jurisdictional-reform.md
      - paper/companion.tex
    tags: [d2, h4, pgfn, filtering]

  - path: build/figure/d1_focal_event_study.pdf
    script: source/figure/d1_focal_event_study.py
    description: |
      D1 phoenix focal event study — log(employment) at the focal CNPJ
      around the exfis filing event, Sun–Abraham heterogeneity-robust.
    cited_in:
      - docs/reference/key-findings.md
      - docs/briefs/phoenix-state-of-evidence.md
      - docs/outline-phoenix.md
    tags: [d1, h1, phoenix]

  - path: build/table/h6_vara_fe_correlations.csv
    script: source/table/h6_vara_fixed_effects.py
    description: |
      Cross-outcome correlations of vara fixed effects (TJSP).
      Foundational evidence for the "vara productivity is non-collinear"
      claim in the H14 paper.
    cited_in:
      - docs/reference/key-findings.md
      - docs/briefs/vara-productivity.md
      - docs/outline.md
    tags: [h6, vara, tjsp]
```

## Bootstrapping the file in an existing project

For a project that already has many findings citing many artifacts:

1. Grep `docs/` for references to `build/table/` and `build/figure/`.
2. Group by artifact path.
3. Look up each artifact's producing script via the
   `source/X.py → build/X.*` naming convention.
4. Take the description from the script's IAT `INTENT` line.
5. Tag by inspection.

Don't try to be exhaustive on the first pass. Cover the load-bearing
artifacts (those cited from `key-findings.md` and the active outlines);
the long tail can fill in as `/next` runs add to the file naturally.
