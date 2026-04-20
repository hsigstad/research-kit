---
name: validate-section
description: "Run AI validation on one subsection of the paper: identify its backing scripts, run the applicable AI checks, and record results in the validation ledger. Use when the user asks to validate a section or asks what AI has verified for a section."
user_invocable: true
---

# Validate a paper subsection

Run a focused AI validation pass on one subsection of the paper,
following the ledger conventions in
`research-kit/meta/validation_ledger.md` and the methodology in
`research-kit/meta/ai_research_workflow.md` stage 8.

Invoke with a section identifier:

- Section slug as it appears in the paper HTML anchor
  (e.g. `enforcement-outcomes`).
- Or a section number (e.g. `7.4`).
- Or a heading phrase that matches a subsection title.

## Procedure

### 1. Locate the section

- Resolve the identifier to an anchor slug by grepping
  `build/make4ht/main.html` for matching `id='…'` on `<h3>` / `<h4>` tags.
  If the make4ht build is missing, parse `paper/main.tex` for
  `\subsection{…}` and derive the slug via the same rule the site
  uses (lowercase, non-alphanumerics → hyphens).
- Confirm the match with the user before proceeding if ambiguous.

### 2. Identify backing scripts

Trace what the section depends on in the build graph:

- Grep the section's LaTeX body for `\input{}`, `\ref{tab:…}`,
  `\ref{fig:…}`, and `\includegraphics{…}` — the referenced tables,
  figures, and included files point into `paper/tables/` and
  `paper/figures/`.
- For each table/figure, grep `source/figure/` and `source/analysis/`
  for the script that produces it.
- Follow `depends_on` chains in `paper/validation.md` back to upstream
  clean-layer scripts. A section's "backing_scripts" should include
  every script in the transitive dependency closure of the numbers it
  cites.
- If `paper/validation_sections.yaml` already has an entry for this
  section with `backing_scripts`, start from that list and only add
  newly-discovered deps.

### 3. Choose which checks to run

From the check-kind vocabulary in
`research-kit/meta/validation_ledger.md`. Default mapping:

| Script type                               | Checks to run                                        |
|-------------------------------------------|------------------------------------------------------|
| Clean-layer (raw → parquet)               | `line_by_line_trace`, `property_assertions`          |
| Merge / join / linking                    | `line_by_line_trace`, `property_assertions`          |
| Estimation / statistics                   | `line_by_line_trace`, `output_sanity`                |
| Table/figure generator referenced in §    | `line_by_line_trace`, `text_table_consistency`       |
| Section-level consistency (prose ↔ tables) | `text_table_consistency` on the section HTML         |

Required-method floors are enforced in the ledger spec. If the floor
isn't met after your pass, the row stays `pending` — say so explicitly
in the report.

### 4. Run the checks

For each `(script, check_kind)` pair:

- **`line_by_line_trace`** — read the script end to end. Narrate the
  logic in a few lines. Flag: sign flips, off-by-one indexing, silent
  row drops around filters and joins, boolean mask ambiguity, type
  coercions that mask missing values, hidden mutation of module-level
  state.
- **`property_assertions`** — generate invariants and check them against
  the actual output. Include: row count bounds, key uniqueness on the
  documented grain, domain of categorical columns, monotone/bounded
  numeric columns, cross-table foreign-key integrity.
- **`output_sanity`** — load the script's output and check that signs,
  magnitudes, and sample sizes match ex-ante priors stated in
  `docs/decisions.md` or the paper's prose.
- **`text_table_consistency`** — for every numeric claim in the section
  (percentages, N, R$, coefficient estimates, days, counts), locate the
  source in the backing script's output and confirm the text matches to
  within expected rounding. Report each number with a status.
- **`reproduction_run`** — re-run the script from a clean state and
  diff the output against the committed artifact. Optional for routine
  validation; use when a previous check flags concerns.

Don't rubber-stamp. An `ai-verified` check that didn't actually run is
worse than `pending`.

### 5. Record results

**`paper/validation.md`** — for each script touched:

1. Compute the current short git hash: `git log -n 1 --format=%h <path>`.
2. If the row's `hash` cell differs, update it.
3. Append to `ai_checks`: `<check_kind> YYYY-MM-DD[; brief note]`.
   - If a check surfaced code issues that got fixed, note the severity
     (HIGH / MEDIUM / LOW) and a one-phrase description.
   - If a check is incomplete (e.g. pipeline rerun deferred), say so.
4. Update `status` if the required-method floor is now met and
   `human_check` is empty → `ai-verified`.
5. Never set `human-verified` yourself. That's the human reviewer's
   action.

**`paper/validation_sections.yaml`** — if the project uses section-level
state:

- If the section has no entry, add one with `level: unreviewed`,
  `reviewer: null`, `date: null`, and the discovered `backing_scripts`.
- If the entry exists, update `backing_scripts` with any new deps found
  in step 2. Do not change `level`, `reviewer`, or `date` — those are
  set by the human via the site form.

### 6. Report

At the end, tell the user:

- Which section was validated (slug + title + number).
- Which backing scripts were in scope.
- Which checks ran on each script, and what they found.
- Ledger updates made (which rows, which columns).
- What still blocks `human-verified` — required-method floors not met,
  hash mismatches not reconciled, claims that couldn't be traced.

Keep the report under ~40 lines. The authoritative record is the
ledger diff, not the chat.

## Scope guards

- **One section at a time.** If the user asks for "all of section 7",
  confirm — that's five subsections of work and the ledger churn is
  easy to get wrong in bulk.
- **Don't modify the script being validated** unless the check explicitly
  surfaced a bug and the user has OK'd the fix. Reading ≠ refactoring.
- **Numbers in the prose that don't trace to a backing script** are a
  finding, not a ledger problem. Flag them; don't invent a script to
  back them.
- **If the paper HTML is stale**, say so. Don't validate against a
  version the user hasn't seen. `bash build.sh site` or equivalent
  first.
