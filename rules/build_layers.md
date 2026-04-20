# Build Layer Convention

How generated data and code are organised under `build/` and `source/`.
Applies to every project and pipeline repo that processes data through
more than one transformation step.

The goal: each paper-cited number, figure, and table traces through a
predictable chain of directories, so "where does this come from?" is
answered mechanically rather than by grepping.

**Claude should assume this layout in any project and use it when
scaffolding new code**, unless the project's `CLAUDE.md` explicitly
overrides a specific piece. Other subfolders of `source/` are fine
(the table below lists commonly-added ones); the rule is only that the
canonical directories below keep their role when present.

---

## Canonical directories

| `source/*`             | Output destination            | Role                                                               | Presence |
|------------------------|-------------------------------|--------------------------------------------------------------------|----------|
| `source/clean/`        | `build/clean/*.parquet`       | Normalize raw data into typed per-entity parquets                   | Always, if the project has a data pipeline |
| `source/intermediate/` | `build/intermediate/*.parquet`| Cache expensive shared precomputations (see trigger below)          | Optional — add only when needed |
| `source/assemble/`     | `build/assemble/*.parquet`    | Analysis-ready wide tables keyed by a unit of observation           | Always, once any assembling happens |
| `source/analysis/`     | `build/analysis/*.{parquet,csv,json}` | Derived statistics, regressions, linked records              | As needed |
| `source/figure/`       | `paper/figures/*.{pdf,png}` (or `build/figure/*`) | Figure-generating scripts                          | If the paper has figures |
| `source/table/`        | `paper/tables/*.tex`          | Table-generating scripts                                            | If the paper has computed tables |
| `source/paper/`        | `paper/numbers.{tex,json}`    | Paper numeric macros (see `rules/paper_macros.md`)                  | If the paper cites structural numbers |

Claude may freely add any other subfolder the project needs
(illustrative examples in the wild: `source/scrape/`, `source/llm/`,
`source/site/`, `source/diagnostic/`, `source/feedback/`). The
canonical set above is a *floor*, not a ceiling — the only rule is
that the canonical folders keep their specified role when present.
Project-specific folders carry no layer implication.

---

## Layers

Three tiers under `build/` (plus an optional fourth). Scripts in
`source/` mirror the same names so a file and its output share a base
name.

### 1. `build/clean/` — normalized data

**Role.** One table per entity, parsed once from raw sources into
typed parquet. No merges across entities, no derived columns beyond
what's needed to make the table internally consistent (type coercion,
deduplication, key normalisation).

**Grain.** One row per natural entity: `licitacao`, `contract`,
`empenho`, `bid`, `firm`, `court_case`, `tce_consulta`, etc.

**Who writes it.** Only `source/clean/` may read raw data (from
`$DATA_DIR` or equivalent). Shared parsers live in
`source/clean/parse.py`.

**Who reads it.** `source/intermediate/` and `source/assemble/`
scripts, plus ad-hoc exploratory analysis (notebooks, one-off probes).
Production code paths — figure scripts, paper citation scripts,
analysis outputs — should read from `build/assemble/` instead.

### 2. `build/intermediate/` — expensive shared precomputations (optional)

**Role.** Cache the output of computations that are (a) shared across
two or more assemble scripts and (b) too slow to re-run each time.
Examples: text embeddings over millions of rows, graph statistics,
wide cross-joins, full-text similarity matrices.

**When to add this layer.** When a computation is expensive enough
(minutes or longer) that you don't want to re-run it every time you
edit the downstream script that consumes it. Sharing across multiple
consumers is a bonus reason, not a requirement — splitting a slow
single-consumer computation into its own cached target is also
legitimate, because it lets you iterate on the assemble script
without redoing the expensive step.

**When NOT to add it.**

- Cheap computation (seconds) — just recompute.
- Wide context-joining that's really shaping a unit of observation —
  that's assemble-layer work, not intermediate.

**Grain.** Whatever the shared computation naturally produces — not
required to be a unit of observation.

**Who writes it.** `source/intermediate/` scripts reading from
`build/clean/`.

**Who reads it.** `source/assemble/` scripts.

Skip this layer entirely on small projects. Adding a 4th layer
preemptively tends to create a catch-all directory scripts get dumped
into without discipline.

### 3. `build/assemble/` — analysis-ready, unit-of-observation-keyed

**Role.** Wide tables that merge context across clean tables (and
optionally intermediate outputs) and pre-compute derived columns used
by multiple downstream consumers. Analysis, figure, table, and paper
scripts read from here.

**Grain.** One row per unit of observation — `muni_year`,
`tce_processo`, `firm_year`, `contract`, `irregularity`. The filename
names the grain: `source/assemble/muni_year.py` produces
`build/assemble/muni_year.parquet`.

**What goes in.** Everything a downstream reader would otherwise
recompute from scratch:

- Joined context columns (e.g. `tce_processo` carries `municipio`,
  `classe_group`, `has_rv`).
- Derived flags (`has_sustained`, `has_penalty`, `is_appeal`).
- Derived aggregates at the grain (`n_sustained_irregularities`,
  `dominant_mechanism`).
- Precomputed date arithmetic (`dias_autuacao_decisao`).

**What doesn't go in.** Analysis outputs — distributions, statistical
results, regressions, JSONs summarising the panel. Those belong in
`build/analysis/`.

**Naming.** One file per grain, named by the grain itself. Grains use
snake_case compound nouns that read as "one row per ___":
`muni_year` → "one row per municipality-year". `tce_processo` → "one
row per TCE-SP processo". No prefixes (`tbl_`, `assemble_`) — the
directory already provides the context.

**Chaining within the layer.** An assemble table may read another
assemble table — e.g. `processo.parquet` may read `irregularity.parquet`
to compute `dominant_mechanism`. This is preferred over adding a
`build/intermediate/` layer for the same purpose.

### 4. `build/analysis/`, `build/figure/`, `build/table/`, paper outputs — derived artefacts

**Role.** Final artefacts: JSONs of computed statistics, CSVs of
linked records, PDF/PNG figures, LaTeX tables, paper number macros.

**Who reads it.** Only the paper source and the site generator read
these. They are the terminal layer of the pipeline.

**Who these scripts read.** Figure, analysis, table, and paper scripts
should read *only* from `build/assemble/` (or other `build/analysis/`
outputs for chained analysis). If a script needs a column that's not
in the assemble layer, add the column to the assemble script — don't
reach past it back into `build/clean/`.

---

## Why this layering

**Mechanical provenance.** Any paper-cited number's dependency chain
has the same shape: raw → `clean/<entity>.parquet` →
(`intermediate/<name>.parquet` →) `assemble/<grain>.parquet` →
`analysis/<result>.json` → paper. The validation ledger walks this
graph; the site tooltip post-processor follows the same shape.
Non-uniform layouts break both.

**Short downstream scripts.** When `assemble/` carries derived flags,
the citation scripts in `source/paper/numbers/` collapse to 3-5
lines — small enough to show in a tooltip. See
`rules/paper_macros.md`.

**Cheap re-derivation.** A downstream consumer that needs a new
summary statistic can write a one-file script against the assemble
layer without re-running the clean layer. The clean layer only
rebuilds when raw data changes.

**Coauthor-legible.** A coauthor tracing "where does this 30.8% come
from" sees a handful of named directories, not a tangle of scripts
reading raw CSVs at different points. The filename tells them which
entity, the directory tells them which stage.

---

## Script-to-output naming

Every script's primary output shares the script's base name.

- `source/clean/licitacao.py` → `build/clean/licitacao.parquet`
- `source/intermediate/edges.py` → `build/intermediate/edges.parquet`
- `source/assemble/muni_year.py` → `build/assemble/muni_year.parquet`
- `source/analysis/overruns.py` → `build/analysis/overruns.parquet`
- `source/figure/overruns.py` → `paper/figures/overruns.pdf`
- `source/table/summary_stats.py` → `paper/tables/summary_stats.tex`

Secondary outputs (diagnostic CSVs, auxiliary tables) use the base
name as a prefix: `overruns_unmatched.csv`, `overruns_diagnostics.csv`.

One script per primary output. Multi-output scripts are allowed only
when the outputs genuinely share computation — not as an organizing
convenience.

---

## Permissions summary

| Source directory               | May read from                                            |
|--------------------------------|----------------------------------------------------------|
| `source/clean/`                | `$DATA_DIR` (raw); own prior clean outputs if chained    |
| `source/intermediate/`         | `build/clean/`                                            |
| `source/assemble/`             | `build/clean/`, `build/intermediate/`, `build/assemble/` |
| `source/analysis/`             | `build/assemble/`, `build/analysis/`                     |
| `source/figure/`, `source/table/` | `build/assemble/`, `build/analysis/`                  |
| `source/paper/`                | `build/assemble/`, `build/analysis/`                     |
| Notebooks / exploration        | Any layer (read-only)                                    |

If an analysis/figure/table script currently reads from `build/clean/`,
it's legacy — the next time it's touched, promote its clean-layer
reads into the relevant `assemble/` script.

---

## Relationship to other conventions

- **Validation ledger** (`meta/validation_ledger.md`): the
  `depends_on` column follows the layered chain. A ledger row for an
  analysis script lists its assemble-layer inputs, not the clean
  tables those assemble scripts merged.
- **Paper macros** (`rules/paper_macros.md`): citation scripts in
  `source/paper/numbers/` must read from `build/assemble/` only.
  That's what keeps them short enough to tooltip.
- **IAT** (`rules/inline_audit_trail.md`): assemble scripts are prime
  candidates for `ASSUMES:` comments on every merge (`how=` choice
  + expected cardinality) and `REASONING:` comments on derived
  columns that encode non-obvious definitions.
- **Project docs contract** (`rules/project_docs_contract.md`): the
  top-level directory layout for a repo; this rule specifies the
  substructure of `source/` and `build/`.
- **SCons builds** (`rules/scons_builds.md`): the dependency graph
  across these layers is materialised as an `SConstruct` at the repo
  root. Every arrow between layers should correspond to an SCons
  `source=` entry.
