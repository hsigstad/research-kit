---
name: validate-section
description: "Run AI validation on one subsection of the paper: identify its backing scripts, run the applicable AI checks, and record results in the validation ledger. Use when the user asks to validate a section or asks what AI has verified for a section."
disable-model-invocation: true
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

Flags:

- `--full` — ignore the incremental cache (`last_ai_pass_sha`) and
  run every applicable check over the whole section. Use after a
  major prose rewrite, when changing the check vocabulary, or when
  suspicious that a prior pass missed something.
- `--all` — iterate over every entry in `build/paper/section_deps.json`
  and run the skill once per section. Intended for autonomous bulk
  passes. Each section's result is recorded independently; a failure
  on one section does not abort the loop (the failing section is
  reported and the loop continues). Prose-only sections (no macros,
  no figures, no tables) are skipped — recording nothing for them
  keeps the ledger uncluttered.

## File locations

The validation ledger is **project memory** (which scripts have been
verified) and lives in `docs/` alongside `findings.md`,
`hypotheses.md`, and the rest of project state. Paper-build outputs
stay in `paper/` and `build/paper/`.

Discovery order — first hit wins, with backward compatibility for the
historical `paper/` location:

| File | Canonical | Legacy fallback |
|---|---|---|
| Script ledger | `docs/validation.yaml` | `paper/validation.yaml` |
| Narrative companion | `docs/validation.md` | `paper/validation.md` |
| Section state | `paper/validation_sections.yaml` | (paper-build state — stays in `paper/`) |
| Paper macro source | `paper/numbers.json` | (paper-specific) |
| Section deps index | `build/paper/section_deps.json` | (paper-build output) |

For all read operations below, check the canonical path first; fall back
to the legacy path if the canonical doesn't exist. For write operations,
write to whichever location currently has the file — do not silently
migrate. To migrate a project to the canonical location, `git mv
paper/validation.yaml docs/validation.yaml` as a single deliberate step.

If neither location has a `validation.yaml`, the project hasn't opted
in to the validation ledger. Tell the user and exit; do not bootstrap
one mid-pass.

## Procedure

### 1. Locate the section

The canonical source of section slugs is
`build/paper/section_deps.json`. Each top-level key is a slug and the
values are authoritative for that section.

- If the user passed a slug that exists as a key in section_deps.json:
  use it directly.
- If the user passed a section number (e.g. `7.4`) or a heading
  phrase: scan section_deps.json entries for a matching `title` or
  `label`. Unique match → proceed. Multiple matches → pick the
  latest heading (usually the intended one); under `--all` the
  caller handles slug ordering, so you should never hit this case.
- Unknown identifier: fail fast. Do not fuzzy-match outside
  section_deps.json — that was the old "ambiguous, ask the user"
  path, which is not available in autonomous runs.
- If section_deps.json is missing (site build hasn't run), report
  the problem and exit; don't fall through to re-parsing main.tex.

No pre-emptive skip based on artefact-count alone. The absence of
macros, figures, and tables does NOT mean nothing is checkable —
`narrative_claim_check`, `citation_claim_check`, and
`institutional_claim_check` all apply to substantive prose. Let the
check-selection step (§3) decide what runs; if it comes back with an
empty set after scoping, §3 itself will short-circuit with
"no applicable checks". Trivially short sections (one paragraph,
purely connective framing) can still be skipped at §3 — but only
after considering what applies, not before.

### 2. Identify backing scripts

Identify the **direct** producers of the section's cited artefacts.
Only one hop — do not walk the dependency graph transitively.

Preferred: read `build/paper/section_deps.json` — it's a pre-computed
map from section slug to `{macros, figures, backing_scripts,
macros_missing_interpretation}`. If the file exists (scons built it),
use it; the per-invocation walk below is the fallback.

- For each `\MacroName{}` in the section, look up the macro in
  `paper/numbers.json` and read the `source` field. That is the
  direct script for that macro.
- For each `\ref{tab:…}`, `\ref{fig:…}`, `\includegraphics{…}`, or
  `\input{…}`: prefer **`docs/reference/artifacts.yaml`** as the
  script-resolution source (canonical script↔artifact map; schema:
  `research-kit/rules/artifacts_yaml.md`). Fall back to grepping
  `source/figure/` and `source/analysis/` only if `artifacts.yaml`
  is missing or doesn't have the referenced artifact yet.
- The union of those scripts is this section's `backing_scripts`.
- If `paper/validation_sections.yaml` already has an entry with
  `backing_scripts`, start from that list and only add newly-
  discovered deps.

**Interpretation-coverage gate.** Read
`section_deps.json[slug].macros_missing_interpretation`. If non-empty,
this section cannot reach `ai-verified` — the
`interpretation_prose_alignment` check has no interpretation to verify
against. Report the missing macros in the final report and leave the
section at `pending` (or back-fill interpretations in
`source/paper/numbers.py::_defs()` first, then re-run).

**Rely on the ledger for upstream.** Each backing script has its own
entry in the script ledger (`docs/validation.yaml` or legacy `paper/validation.yaml`) with its own `ai_checks` and `status`.
The pre-submission checker propagates `stale` and `pending` upstream
via the `depends_on` column — a section whose direct backing script
is fine but whose grandparent clean-layer script is `stale` cannot
sign off, and that is surfaced by the checker, not by this skill.
Revalidating the same clean-layer script once per dependent section
is churn, not defense in depth.

### 2b. Scope the pass (incremental mode)

Skip this step if `--full` was passed. Otherwise determine whether
anything changed since the last AI pass, and run only what the delta
requires.

1. Read `last_ai_pass_sha` from the section's YAML entry. If absent or
   null, fall through to a full pass (record the section as fresh).
2. **Prose delta.** Compute the diff:
   ```
   git diff <last_ai_pass_sha>..HEAD -- paper/main.tex
   ```
   Parse the hunks and filter to those whose line ranges fall inside
   the section (between its `\subsection{…}` and the next one).
3. **Script drift.** For each backing script, compare its current
   closure hash (e.g. `python3 scripts/closure_hash.py <path>`) to
   the entry's `closure_hash:` in the script ledger. A drifted
   closure catches both leaf edits and helper-module edits; the
   plain git `hash` column is the audit anchor, not the drift
   detector. Collect the drifted scripts.
4. **Macro sensitivity.** For every `\MacroName{}` in the section,
   look up the source script via `paper/numbers.json` (field:
   `source`). A macro is **sensitive** if either the macro itself
   appears inside a hunk, OR its source script is drifted.
5. Scope the pass:
   - No hunks, no drift → skip. Report "no re-check needed; last
     pass at `<sha>`". Do not modify the ledger.
   - Hunks only → `macro_provenance` + `qualifier_alignment` on
     sensitive macros; `text_table_consistency` only on non-macro
     literals inside hunks; `narrative_claim_check` over the full
     section (it's argument-level and cheap relative to running it
     piecewise).
   - Drift only → `qualifier_alignment` on sensitive macros (values
     may have moved under the unchanged prose). `macro_provenance`
     unchanged, since JSON paths didn't move — unless the drifted
     script renamed a field, which the check would catch anyway.
   - Both → union of the above.
6. If the pass is skipped, stop here. Otherwise continue with the
   scoped check set.

### 3. Choose which checks to run

From the check-kind vocabulary in
`research-kit/meta/validation_ledger.md`. Default mapping:

| Target                                    | Checks to run                                                                                       |
|-------------------------------------------|-----------------------------------------------------------------------------------------------------|
| Clean-layer (raw → parquet)               | `line_by_line_trace`, `property_assertions` (authoring only — invariants should live in pytest)     |
| Merge / join / linking                    | `line_by_line_trace`, `property_assertions` (same)                                                  |
| Estimation / statistics                   | `line_by_line_trace`, `output_sanity`                                                               |
| Table/figure generator referenced in §    | `line_by_line_trace`, `text_table_consistency` (on the figure/table)                                |
| Script that any section macro points at   | `interpretation_code_alignment` (once per macro definition, reruns only if script field or interpretation changes) |
| Any substantive section prose (default)   | `narrative_claim_check` — argument integrity, overstated verbs, unsupported "therefore", ambiguous denominators, evidence pointers. Fires even when the section has no macros/figures/tables. |
| Section prose citing macros               | `interpretation_prose_alignment` (plus `macro_provenance` ONLY if the project does not automate it via a build-time macro lint) |
| Section prose with non-macro literals     | `text_table_consistency`, `qualifier_alignment` (only for the non-macro literals)                   |
| Section prose citing external papers      | `citation_claim_check` (only for new or modified citations)                                         |
| Section prose stating institutional facts | `institutional_claim_check` (laws, thresholds, dates, modalities, enforcement bodies vs. the project's institutional-background reference) |
| Any section prose (always runs)           | `style_lint` (mechanical linter — run first, before AI checks). Then `style_prose` (AI semantic style checks — intro ordering, topic sentences, triangular structure, robot-body persuasion, caption self-containment, conclusion brevity). |

After scoping: if the union of applicable checks is empty — e.g. a
two-sentence connective paragraph with no cited data, no macros, no
external cites, no institutional claims — report "no applicable
checks" and exit without writing to the ledger. This is a
*post-scoping* short-circuit, replacing the old pre-emptive
artefact-count skip. Most sections that look "prose-only" on an
artefact count will still have applicable checks (narrative integrity,
citations, institutional facts) and should run through §4.

**Checks that should live in the build, not in this skill.** If the
project has:

- a macro-regeneration + macro lint (`check_macros.py` or equivalent)
  wired into SCons → don't run `macro_provenance`; the build already
  fails on any drift.
- a pytest invariant suite covering the script's outputs →
  `property_assertions` on that script reduces to authoring the
  invariants (once); the per-build rerun is pytest's job.
- a `scons repro` target (or equivalent clean-rebuild-diff) in CI →
  don't run `reproduction_run`; CI owns it.

Run these AI checks only when the mechanical guard isn't in place.

Projects using the paper numeric macro system
(`research-kit/rules/paper_macros.md`) get mechanical text-JSON
alignment for free — don't burn cycles re-checking that
`\MacroName{}` renders the value in `paper/numbers.json`. Spend them
on the three prose-level checks instead, where the failure modes the
macro system cannot catch actually live.

Required-method floors are enforced in the ledger spec. If the floor
isn't met after your pass, the row stays `pending` — say so explicitly
in the report. Sections that state institutional facts additionally
require `institutional_claim_check` before reaching `ai-verified`.

### 4. Run the checks

For each `(target, check_kind)` pair selected in §3, run the check per its
specification in [`reference/checks.md`](reference/checks.md) — **read it before
running.** It defines every check kind:

- **Code / data checks** — `line_by_line_trace`, `property_assertions`,
  `output_sanity`, `text_table_consistency`, `macro_provenance`,
  `interpretation_code_alignment`, `reproduction_run`.
- **Prose checks** — `interpretation_prose_alignment`, `qualifier_alignment`,
  `narrative_claim_check` (with its pass/fail calibration anchors),
  `citation_claim_check`, `institutional_claim_check`.
- **Style checks** — `style_lint` (mechanical, run first) then `style_prose`
  (AI semantic checks, with section-type scoping and the mandatory rule-file
  Read gate — a `style_prose` row written without the Read evidence is a false
  ledger claim).

Don't rubber-stamp. An `ai-verified` check that didn't actually run is worse
than `pending`.

### 5. Record results

**`docs/validation.yaml`** (or `paper/validation.yaml` — see File
locations) — for each script touched, find its entry under `scripts:`
and:

1. Compute the current short git hash: `git log -n 1 --format=%h <path>`.
   If the entry's `hash:` differs, update it.
2. Compute the current closure hash: `python3 scripts/closure_hash.py <path>`.
   If the entry's `closure_hash:` differs, update it. Both fields
   should move together on a new check pass.
3. Append to `ai_checks:` a new structured entry:
   ```yaml
   - kind: <check_kind>
     date: YYYY-MM-DD
     notes: <brief note>   # optional; keep to one line
   ```
   - If a check surfaced code issues that got fixed, note the severity
     (HIGH / MEDIUM / LOW) and a one-phrase description.
   - If a check is incomplete (e.g. pipeline rerun deferred), say so.
4. Update `status:` if the required-method floor is now met and
   `human_check:` is null → `ai-verified`.
5. Never set `human-verified` yourself. That's the human reviewer's
   action.

**`paper/validation_sections.yaml`** — if the project uses section-level
state:

- If the section has no entry, add one with `level: unreviewed`,
  `reviewer: null`, `date: null`, `ai_checks: []`,
  `last_ai_pass_sha: null`, and the discovered `backing_scripts`.
- If the entry exists, update `backing_scripts` with any new deps found
  in step 2. Do not change `level`, `reviewer`, or `date` — those are
  set by the human via the site form.
- Append section-level checks run this pass (interpretation_prose_alignment,
  qualifier_alignment, narrative_claim_check) to `ai_checks:` as
  structured entries:
  ```yaml
  - kind: <check_kind>
    date: YYYY-MM-DD
    notes: <optional>
  ```
  Same schema as the script ledger.
- Set `last_ai_pass_sha:` to the current short HEAD SHA
  (`git rev-parse --short HEAD`). This enables incremental rechecks
  (step 2b) on the next invocation.

### 6. Report

At the end, tell the user:

- Which section was validated (slug + title + number).
- Pass mode — `full` or `incremental since <sha>` (and if incremental,
  a one-line summary of what drove the scoping: N prose hunks and/or
  M drifted scripts).
- Which backing scripts were in scope.
- Which checks ran on each target, and what they found. For an
  incremental pass, also note which checks were deliberately skipped
  because nothing in their scope changed.
- Ledger updates made (which rows, which columns, new
  `last_ai_pass_sha`).
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
