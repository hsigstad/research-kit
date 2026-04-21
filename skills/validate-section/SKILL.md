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
  `\input{…}`, grep `source/figure/` and `source/analysis/` for the
  script that produces the referenced artefact.
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
entry in `paper/validation.yaml` with its own `ai_checks` and `status`.
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
   the entry's `closure_hash:` in `paper/validation.yaml`. A drifted
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

For each `(target, check_kind)` pair:

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
- **`text_table_consistency`** — for any non-macro numeric literal
  in the section prose and for every number inside a cited table or
  figure, locate the source in the backing script's output and confirm
  the rendered value matches to within expected rounding. Skip
  `\MacroName{}` — those are covered by `macro_provenance`.
- **`macro_provenance`** — purely mechanical. For each `\MacroName{}`
  the section cites:
  1. Look up the macro in `paper/numbers.json`.
  2. Confirm the `source` field points at an existing script + JSON
     path.
  3. Open the source JSON and confirm the value at that path matches
     the macro's rendered value.
  4. Flag mismatches: missing macro, missing JSON field, value
     mismatch, macro defined but unused, macro used but not defined.
  Do NOT re-adjudicate whether the quantity matches the claim — that's
  `interpretation_code_alignment` (script-side, once) and
  `interpretation_prose_alignment` (prose-side, per section).
- **`interpretation_code_alignment`** — script-side check that a
  macro's declared interpretation matches what the source script
  computes. For each macro whose source script is being validated:
  1. Read the macro's `interpretation` field from `paper/numbers.json`.
     If null, record `pending` and stop — the macro author has not
     declared a semantic description.
  2. Open the source script and locate the code that writes the
     referenced JSON path.
  3. Compare: denominator, numerator, filter, aggregation. Does the
     code actually produce what the interpretation describes?
     Common mismatches: interpretation says "sustained" but code
     computes over all; interpretation says "share of processos" but
     code's denominator is documents; interpretation omits a filter
     the code applies.
  4. Record per macro. Mismatch is a HIGH severity finding — fix the
     script, the interpretation, or both, then re-verify.
  This is a ONE-TIME check per `(macro, script-hash)` pair — it does
  not need to rerun unless the script's referenced field or the
  interpretation text changes.
- **`interpretation_prose_alignment`** — prose-side check that the
  text around each macro invocation is consistent with the macro's
  declared interpretation. For each `\MacroName{}` in the section:
  1. Pull the macro's `interpretation` from `paper/numbers.json`. If
     null, record `pending` (cannot verify without an interpretation).
  2. Read the prose sentence(s) containing the macro. Check:
     - Denominator: does the prose imply the same base population?
       ("N% of cases" vs. interpretation's explicit denominator).
     - Direction/sign: claims about increase/decrease consistent with
       rendered value.
     - Qualifier and magnitude words: "majority", "tripled", "rare" —
       matching the value under the interpretation's semantics.
     - Claim context: the interpretation says what the number is; the
       prose should use it that way, not a different way.
  3. Report per macro, per prose location. Severities: MEDIUM for
     qualifier drift, HIGH for denominator swap (e.g. prose implies
     "share of all cases" when interpretation says "share of
     sustained cases").
- **`qualifier_alignment`** — for *non-macro* numbers (narrative
  literals still in prose), check scale/direction/magnitude words:
  - Scale words: "doubled"/"tripled"/"fivefold" vs. actual ratio.
  - Direction words: "rose"/"fell"/"flat" vs. actual change.
  - Magnitude adjectives: "majority", "nearly half", "vast majority",
    "a handful", "dominant", "rare" — against the actual fraction.
  - Cross-number claims: "larger than", "overtake", "crossed over" —
    verify across the two cited values.
  Macros are covered by `interpretation_prose_alignment` instead.
- **`narrative_claim_check`** — read the section as an argument. Ask:
  does the conclusion actually follow from the shown data? Flag:
  - Overstated verbs ("demonstrate", "prove", "establish" when the
    evidence is descriptive).
  - Missing caveats — no noted confounds in a causal reading of
    observational data; no mention of selection when sample is not
    the target population.
  - "Therefore" / "thus" bridging steps the data doesn't support.
  - Ambiguous denominators — every percentage and ratio should have
    an unambiguous base population. Flag phrases like "X% of cases"
    where "cases" could mean several things (all / sustained /
    procurement-related / linked). Require explicit base or confirm
    from context.
  - Cross-section consistency — when the section cites a quantity
    that also appears elsewhere in the paper, check that the two
    values reconcile (same number, or explicitly different
    denominators with both named). Bookkeep quantities like
    "N processos", "% sustained", "N municipalities".
  - Evidence pointers — phrases like "Figure X shows", "Table Y
    reports", "as discussed in §Z", "we find". Walk each pointer:
    does the referenced figure/table/section actually show what
    the claim attributes to it?
- **`citation_claim_check`** — for each external reference cited in
  the section (new cite or one whose surrounding prose changed),
  open the cited PDF or abstract and verify the attributed claim is
  in there, with the numeric magnitude the prose asserts. Record
  per-citation status. (Cross-listed in the script ledger for the
  bibliography; the section-level pass catches cites introduced with
  the section prose, before they propagate to other sections.)
- **`institutional_claim_check`** — for sections that state institutional
  facts (laws, thresholds, dates, modalities, enforcement bodies), run
  the project's institutional-claim checker if present (procure:
  `python3 -m source.paper.check_institutional_claims --section N`). The
  script extracts every institutional claim from the section and
  classifies each as BACKED / UNBACKED / CONTRADICTED against the
  project's institutional-background reference (`docs/institutions.md`),
  with a verbatim quote and an anchor sentence from the reference.
  Output lands in `build/paper/institutional_claims_check.json` and is
  cached on section + reference content hashes. Severity mapping:
  CONTRADICTED → HIGH (must reconcile paper, reference, or both before
  claiming `ai-verified`); UNBACKED → MEDIUM (add a primary source to
  the institutional reference, or remove/soften the claim). Record a
  one-line `notes:` in the section's `ai_checks:` entry with the counts
  (e.g. `12 backed, 2 unbacked, 0 contradicted`).
- **`reproduction_run`** — re-run the script from a clean state and
  diff the output against the committed artifact. For projects using
  SCons (see `research-kit/rules/scons_builds.md`):
  ```
  scons --clean <target> && scons <target>
  # then diff the rebuilt <target> against the previous version
  ```
  This catches three failure modes the simpler `python -m …` rerun
  misses: (a) incomplete `source=[...]` declarations in the SConstruct
  (an imported helper was edited but the output didn't rebuild),
  (b) stale upstream parquets that the manual rerun would have reused
  as-is, (c) committed artifact produced under a different dep state
  than the current one. For procure specifically, where `build/` is
  gitignored and authoritative artefacts live on dropbox, diff the
  rebuild against the dropbox copy (`rclone copy … --dry-run` shows
  what differs). Optional for routine validation; use when a previous
  check flags concerns, after editing a helper module, or before
  pushing a refreshed artefact to dropbox.

Don't rubber-stamp. An `ai-verified` check that didn't actually run is
worse than `pending`.

### 5. Record results

**`paper/validation.yaml`** — for each script touched, find its entry
under `scripts:` and:

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
