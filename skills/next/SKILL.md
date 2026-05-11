---
name: next
description: "Run one iteration of the project analysis loop: accept (or propose) the next analysis, write the script in the right location with IAT, run it, then propagate to the right docs. Use when the researcher says 'next, do X' or asks 'what's next?'."
user_invocable: true
---

# /next — Run one iteration of the analysis loop

Orchestrate one cycle of: **read state → accept-or-propose → write → run →
propagate → close out**. Designed for projects past the initial data-pipeline
stage where the workflow is "identify a question, write a focused script
under `source/{table,figure}/`, inspect the build output, update the
relevant docs."

This is a *thin orchestrator*. Doc-writing steps invoke existing skills
(`/findings`, `/hypothesis`, `/institutions`, `/iat-check`, `/handoff`).
The skill's job is the **sequence** and the **doc-propagation checklist**,
not the writing of any one doc.

## Arguments

- `/next <description>` — **specify mode** (primary). The researcher
  dictates what to do ("test whether H17 holds in the 2018+ subsample",
  "rebuild figure X with the post-fix sample"). Skip to step 2.
- `/next` — **propose mode**. No description given. Scan project state and
  suggest 3–5 ranked candidates, then stop for greenlight.
- `/next --project <slug>` — run against a specific project under
  `projects/`. Otherwise inferred from CWD.
- `/next --propose-only` — stop after step 1; don't write or run anything.
  Useful for planning a session.
- `/next --no-run` — write the script and stop. Useful when you want to
  inspect the script before it touches data.

## Finding the workspace root

The workspace root contains `CLAUDE.md` alongside `projects/`, `pipelines/`,
`ideas/`, `research/`. If the current directory is inside a project, search
upward. `$ROOT` for paths below; `$PROJ = $ROOT/projects/<slug>/`.

## What to read

Always read 1–3. Read 4+ only in propose mode.

1. `$PROJ/CLAUDE.md` — current focus and conventions.
2. `$PROJ/docs/todo.md` — open tasks. Pay attention to the most recent
   `## Session handoff — YYYY-MM-DD` block at the top.
3. The active **paper outline** (`outline.md` or whichever the project's
   CLAUDE.md points at) — to know what section a result would feed.
4. `$PROJ/docs/hypotheses.md` — pending tests, status blocks.
5. `$PROJ/docs/reference/key-findings.md` — what's already established and
   at what confidence.
6. `$PROJ/docs/thinking.md` — candidate angles.
7. `git log --oneline -10` — what was just done; don't propose something
   already in flight.
8. `ls source/{table,figure}/` and `ls build/{table,figure}/` — don't
   re-derive what already exists; if it exists, the candidate is a *follow-
   up* not a *new* analysis.

## Step 1 — Propose (propose mode only)

Produce 3–5 ranked candidates. For each:

- One-sentence description.
- Which outline section / hypothesis / finding it would advance.
- Required inputs (existing build artifacts or pipeline outputs).
- Rough effort (single descriptive cut / multi-script empirical battery /
  new data linkage).
- Risk flag if any ("needs raw data we don't have", "duplicates existing
  `build/table/X`", "depends on a parser fix not yet shipped").

Ranking criteria, in order:

1. Closes a load-bearing gap in the active paper outline.
2. Tests a hypothesis that's been pending for >2 sessions.
3. Cheaply confirms or refutes a finding currently tagged 🟡 or 🔴.
4. Resolves an explicit todo from the most recent handoff.

**Then stop.** Wait for the researcher to pick one — or to specify
something different. Do not write any script.

## Step 2 — Restate

In one short paragraph, confirm:

- The **question** the analysis answers.
- The **unit of observation**, sample, and time window.
- The **outcome variable(s)** and the cut(s).
- The **output**: which `build/table/X.{csv,parquet,tex}` and/or
  `build/figure/X.{pdf,png}`. Follow the project's existing layout
  (some projects use sub-pages like `build/figure/d1_*`; respect it).
- The **docs that will be updated** after the run (preview the
  propagation list from step 5).

If anything is unclear — sample definition, denominator, which
hypothesis it maps to — **ask before proceeding**. Cheaper than redoing.

## Step 3 — Write the script

Location and naming (per workspace.md "Source and build naming convention"):

- Table outputs → `source/table/X.py` → `build/table/X.{csv,parquet,tex}`
- Figure outputs → `source/figure/X.py` → `build/figure/X.{pdf,png}`
- Underscore-prefix (`source/table/_foo_check.py`) for one-shot
  exploratory checks kept for reproducibility but not part of the
  pipeline. Use sparingly — most scripts should not need it.

IAT header per `research-kit/rules/inline_audit_trail.md`:

- `INTENT` — the question.
- `REASONING` — why this specification (sample choice, variable cuts).
- `ASSUMES` — required inputs, conventions the script depends on.

Code style (per workspace.md):

- Functions over procedural blocks.
- `pathlib.Path` over string paths.
- Parquet over CSV for intermediate data.
- Explicit `validate=` on every `.merge()`.
- `errors='coerce'` on numeric conversions of messy input.
- `diarios` for shared parsing — do not duplicate.

After writing, invoke `/iat-check` on the new script (or note that it
should be run).

If `--no-run` was passed: **stop here**.

## Step 4 — Run and inspect

Run the script. If it errors:

- Read the traceback carefully.
- Fix the **root cause**. Do not add `try/except` to hide the error.
- Re-run.

If it succeeds:

- Open the output. Print head/tail, summary stats, and any column with
  surprising values.
- For figures: dimensions, axis ranges, no clipped labels.
- **Sanity-check against prior magnitudes** in `key-findings.md` or
  `stylized-facts.md`. This catches sign flips, unit confusions, sample
  mismatches.

Report a short summary to the researcher:

- N.
- Headline number(s) with SE/CI if applicable.
- Whether it confirms, refutes, or qualifies the prior expectation.
- Any surprise worth flagging.

**Stop and let the researcher confirm before doc propagation.** Doc
edits are harder to reverse than re-running a script.

## Step 5 — Propagate to docs

Use this checklist, keyed by run type. Only update docs the run actually
affects. Don't touch a doc just because it exists.

| Run type | Docs to update |
|---|---|
| Descriptive table or figure | `reference/key-findings.md` + `reference/stylized-facts.md` + relevant `briefs/*.md` |
| Identification-design run (D-series) | `hypotheses.md` status block + `methods.md` + `key-findings.md` + the affected `outline*.md` |
| Institutional/legal finding | `institutions.md` + (sometimes) `literature.md` |
| Null result on a candidate hypothesis | `hypotheses.md` status block; propose a `decisions.md` entry if it demotes the hypothesis from the paper |
| Re-run with new data/parser | walk every cited number; flag drift in `key-findings.md` and `stylized-facts.md` (run `/findings --refresh` if available) |

For each affected doc, invoke the relevant skill rather than hand-editing:

- `/findings --extend` — append a new finding.
- `/findings --refresh` — recheck cited numbers against current build.
- `/hypothesis --extend` — append a status block or new hypothesis.
- `/institutions` — institutional fact.
- `/findings-audit` — when an external corroboration/contradiction surfaces.

Conventions to follow:

- **Confidence tags**: default new findings to 🟡 (single source). Promote
  to 🟢 only on independent replication. Use 🔴 for parser-dependent or
  sample-sensitive results.
- **@claim registry**: for load-bearing inline numbers, wrap with the
  `@claim` tokens used elsewhere in the project. Lets `/findings --refresh`
  recheck mechanically after a re-run.

## Step 6 — Close out

- Append a one-line entry to `docs/done.md` under today's date with the
  script path and the headline number.
- If the run **materially changed the paper outline** (added or removed a
  finding from a section, changed a load-bearing number, demoted a
  hypothesis), **propose a `decisions.md` entry** and ask before writing.
  Do not auto-append to `decisions.md`.
- If the session is ending: invoke `/handoff`. Otherwise the session
  continues — the researcher can call `/next` again.

## Decisions.md — what goes in

Keep it curated. An entry goes in only when the decision changes how the
project is **framed** or **scoped**.

Yes:

- Hypothesis demoted from paper claim to descriptive-only (e.g. fisc's H3).
- Identification design dropped.
- Paper restructure (one paper → multiple).
- Load-bearing number revised materially after a re-run.
- Sample-definition change with downstream effects.

No:

- Bug fixes, parser tweaks, finding refinements (commit message + `done.md`).
- Every script-level methodological choice (IAT comment in the script).

Format when proposing an entry:

```
## YYYY-MM-DD — <short title>

**Decision:** <one sentence>.

**Why:** <one or two sentences — the load-bearing reason, citing the
build artifact(s) that triggered the decision>.

**Implications:** <what changes downstream — paper sections, other
hypotheses, follow-on tests>.
```

The bar is: future-you, six months from now, needs to know why the
project looks this way. If a future reader could reconstruct it from
`done.md` + git log, it doesn't belong here.

## Guardrails

- **Stop at greenlight gates.** Step 1 → step 2 (researcher picks),
  step 4 → step 5 (researcher confirms results). Do not chain past
  these without explicit go-ahead.
- **Don't propagate doubt.** If step 4 inspection shows something
  surprising or off, surface it before touching docs. Walking back a
  finding is more expensive than running a sanity check.
- **Respect existing layout.** If the project has a custom output
  convention (e.g. project-specific `build/diagram/` subdir, paper
  macros via `build/paper/`), follow it. The skill enforces sequence,
  not layout.
- **One question per script.** Don't bundle a "while we're at it" cut
  into the same script — propose it as a separate `/next` iteration.
- **No silent doc edits.** Every doc change must come from invoking a
  named skill or be summarized in the end-of-iteration report.
- **Don't auto-append `decisions.md`.** Always propose and confirm.
