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
(`/findings`, `/hypothesis`, `/institutions`, `/check`, `/handoff`).
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
- `/next --auto` — **fully autonomous**. No stop-gates. If no description
  is given, propose internally, pick the top-ranked candidate, run it,
  propagate, close out. Use when you trust the proposal ranking and the
  doc-propagation defaults and want to leave it running. See "Auto modes"
  below for safety semantics.
- `/next --auto-after-pick` — **autonomous after task selection**.
  Proposes (or accepts your description), stops once for your pick (or
  to confirm the specified task), then runs the rest of the loop without
  further gates. Use when you want to keep judgment over *what* to run
  but trust the propagation step.

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

Produce 3–5 ranked candidates. For each, output the following fields:

- **Description**: one sentence.
- **Primary target**: one of —
  - `hypotheses.md:H<#>` — updates an existing hypothesis status block.
  - `key-findings.md:<slug>` — updates an existing finding entry.
  - `institutions.md:<section>` — updates an institutional section.
  - `theory.md:<framework-id>` — refines a theoretical framework.
  - `literature.md:<citekey>` — annotates a literature entry.
  - `(new entry, no current target)` — exploratory, will produce a new
    finding via `--extend` rather than a `--update`.
- **Secondary targets** (optional): any other docs the run will touch
  per the propagation checklist (briefs, stylized-facts, outline).
- **Required inputs**: existing build artifacts or pipeline outputs.
- **Effort**: single descriptive cut / multi-script empirical battery /
  new data linkage.
- **Risk flag** if any: "needs raw data we don't have", "duplicates
  existing `build/table/X`", "depends on a parser fix not yet shipped".

The primary target is what drives step 5's `--update <ID>` invocation.
If you can't name a target, that's a signal to talk through what the
run is for *before* writing the script — usually it means the candidate
is too vague or genuinely exploratory (in which case `(new entry)`).

Ranking criteria, in order:

1. Closes a load-bearing gap in the active paper outline.
2. Tests a hypothesis that's been pending for >2 sessions.
3. Cheaply confirms or refutes a finding currently tagged 🟡 or 🔴.
4. Resolves an explicit todo from the most recent handoff.

Candidate format example:

```
Candidate 2: H6 vara-FE × foro stratification (cross-jurisdictional follow-up)
  Description: refit H6 fixed effects with foro dummies to test whether
    the productivity axis collapses to between-foro composition.
  Primary target: hypotheses.md:H6 (status block)
  Secondary: key-findings.md:vara-productivity-axis,
             briefs/vara-productivity.md
  Required inputs: build/table/h6_vara_fe_by_foro.csv (existing)
  Effort: medium — refit + new cut.
  Risk: none.
```

**Then stop.** Wait for the researcher to pick one — or to specify
something different. Do not write any script.

## Step 2 — Restate

In one short paragraph, confirm:

- The **question** the analysis answers.
- The **primary target** (carried over from step 1, or asked here in
  specify mode): the single doc entry that will receive a `--update`
  in step 5. Format: `hypotheses.md:H<#>` / `key-findings.md:<slug>` /
  `institutions.md:<section>` / `theory.md:<framework-id>` /
  `literature.md:<citekey>` / `(new entry)`.
- The **unit of observation**, sample, and time window.
- The **outcome variable(s)** and the cut(s).
- The **output**: which `build/table/X.{csv,parquet,tex}` and/or
  `build/figure/X.{pdf,png}`. Follow the project's existing layout.
- The **secondary targets** (briefs, outline section, stylized-facts)
  the run will also touch.

If anything is unclear — sample definition, denominator, primary
target — **ask before proceeding**. Cheaper than redoing.

In **specify mode** (`/next <description>` with no proposal step), if
the researcher's description didn't name a primary target, the restate
must derive one or ask. A run with no nameable target is rare and
usually a sign the work is too unfocused.

## Step 3 — Write the script

Location and naming (per workspace.md "Source and build naming convention"):

- Table outputs → `source/table/X.py` → `build/table/X.{csv,parquet,tex}`
- Figure outputs → `source/figure/X.py` → `build/figure/X.{pdf,png}`
- **Multi-output scripts** (more than one output of the same suffix) must
  write into a folder named after the script:
  `source/figure/X.py` → `build/figure/X/<name>.png`, not sibling files like
  `build/figure/X_a.png` + `build/figure/X_b.png`. The script-to-output
  mapping must be recoverable from the path alone.
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

After writing, invoke `/iat <script>` on the new script (or note that it
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

### 5a. Update the primary target

The primary target declared in step 1/2 receives a **surgical
`--update`** call, scoped to one entry, with the triggering artifact
attached so the skill has the build context without re-reading the
project:

| Primary target | Invocation |
|---|---|
| `hypotheses.md:H<#>` | `/hypothesis --update H<#> --artifact build/<path>` |
| `key-findings.md:<slug>` | `/findings --update <slug> --artifact build/<path>` |
| `institutions.md:<section>` | `/institutions --update <section> --artifact build/<path>` |
| `theory.md:<framework-id>` | `/theory --update <framework-id> --artifact build/<path>` |
| `literature.md:<citekey>` | `/literature --update <citekey> --artifact build/<path>` |
| `(new entry, no current target)` | `/findings --extend` (or `/hypothesis --extend` if the run introduced a new testable claim) |

`--update` modes are surgical: they read only the project CLAUDE.md,
the target doc, and the artifact. They do not re-derive other entries.
This is what makes the propagation step cheap enough to run every
iteration.

### 5b. Secondary docs by run type

After the primary target is updated, walk this checklist for *secondary*
docs. Only update those the run actually affects.

| Run type | Secondary docs |
|---|---|
| Descriptive table or figure | `reference/stylized-facts.md` + relevant `briefs/*.md` |
| Identification-design run (D-series) | `methods.md` + the affected `outline*.md` |
| Institutional/legal finding | (sometimes) `literature.md` |
| Null result on a candidate hypothesis | propose a `decisions.md` entry if it demotes the hypothesis from the paper |
| Re-run with new data/parser | walk every cited number; run `/findings --refresh` to flag drift in `key-findings.md` and `stylized-facts.md` |

For each secondary doc, invoke the appropriate mode of its skill — never
hand-edit when a skill exists:

- `/findings --extend` — append a new finding (when a run produces an
  observation distinct from the primary target).
- `/findings --refresh` — recheck cited numbers against current build
  after a re-run.
- `/hypothesis --extend` — append a new hypothesis (when a run surfaces
  a testable claim that wasn't a prior hypothesis).
- `/findings-audit` — when an external corroboration/contradiction
  surfaces during step 4 inspection.

### 5c. `artifacts.yaml` maintenance

If the run produced a new artifact (not already in
`docs/reference/artifacts.yaml`), append an entry:

- `path`, `script`, one-line `description` (from the IAT title),
  `cited_in` (the docs you edited in 5a and 5b), and `tags`.
- If the run modified an existing artifact's set of citing docs, update
  the entry's `cited_in` list.

Schema: `research-kit/rules/artifacts_yaml.md`.

### 5d. `validation.yaml` row (if the project has a validation ledger)

If `docs/validation.yaml` (or legacy `paper/validation.yaml`) exists,
the project has opted into the formal validation ledger
(`research-kit/meta/validation_ledger.md`). When a `/next` iteration
produces a new script (one not already in the ledger), append a
`pending` row:

```yaml
- script: source/table/<new-script>.py
  layer: <inferred from path>     # e.g. analysis_<topic>, figure_<topic>
  produces: build/table/<new-script>.csv
  depends_on: []                   # filled in by /validate-section later
  hash: null                       # filled in at validation time
  closure_hash: null               # filled in at validation time
  ai_checks: []
  human_check: null
  reviewer: null
  status: pending
```

The bare minimum is `script`, `produces`, `status: pending`. Hash and
closure_hash get populated when `/validate-section` actually runs on
the script. `depends_on` is filled in by `/validate-section` step 2.

For runs that **re-use an existing script** (no new script, just a
re-run with different params): do **not** add a new row. If the
existing row was `ai-verified` or `human-verified`, the re-run *may*
have invalidated those checks — check `commit_dirty` and
`commit != ledger.hash` from the artifact's `.run.json`, and if so
flip the row's `status` to `stale`.

Do not promote rows past `pending` from `/next`. Verification is
`/validate-section`'s responsibility.

If neither location of `validation.yaml` exists, skip this step
cleanly — the project hasn't opted in.

### Conventions

- **Confidence tags**: default new findings to 🟡 (single source).
  Promote to 🟢 only on independent replication. Use 🔴 for
  parser-dependent or sample-sensitive results.
- **`@claim` registry**: for load-bearing inline numbers, wrap with
  the `@claim` tokens used elsewhere in the project. Lets
  `/findings --refresh` recheck mechanically after a re-run.

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

## Auto modes

Two flags bypass the stop-gates for unattended runs:

- **`--auto`** — both gates off. If no description is given, propose
  internally and pick the top-ranked candidate; otherwise accept the
  given description. Then write, run, propagate, close out without
  asking.
- **`--auto-after-pick`** — pick gate on, results gate off. Proposes
  (or accepts the description) and stops once. After your pick,
  run / inspect / propagate / close out without further confirmation.

Auto-mode semantics:

- **Errors are not gates.** A script that errors in step 4 still halts
  the loop and surfaces the traceback; auto means "no confirmation
  prompts at well-defined gates," not "ignore failures." After fixing
  the script, re-invoke `/next --auto`.
- **Auto-pick threshold.** In `--auto` with no description: only
  proceed if the top-ranked candidate (a) has no risk flag (no "needs
  raw data we don't have", no "duplicates existing artifact", no
  "depends on unshipped parser fix") AND (b) has a named primary
  target — `hypotheses.md:H<#>`, `key-findings.md:<slug>`, etc. A
  candidate that declared `(new entry, no current target)` is too
  exploratory for auto mode; bail and require manual pick.
- **Primary target drives propagation.** The candidate's declared
  primary target tells auto mode which `--update <ID>` call to make
  in step 5. No guessing. If the target is `(new entry)`, route to
  `--extend` instead.
- **Doc propagation runs by the same checklist** keyed to run type;
  no shortcuts. The propagation skills (`/findings --update`,
  `/hypothesis --update`, etc.) are invoked exactly as in attended mode.
- **`decisions.md` writes in auto mode** when the promotion bar is
  met (hypothesis demoted, design dropped, etc.) — the bar is policy,
  not a gate. The entry is flagged in the closing report so you can
  review next session and revert if you disagree.
- **End-of-iteration report is the audit trail.** In auto mode, the
  closing report enumerates: the script written, the headline result,
  every doc edited, any `decisions.md` entry created, and any
  surprises that would have been a gate prompt in attended mode.
  Read it; it's where you regain control.

When to use:

- `--auto` for batch / overnight runs where the proposal ranking is
  trustworthy and the cost of a wrong analysis is low (cheap reruns,
  exploratory descriptive cuts).
- `--auto-after-pick` when you know which analyses are next but
  don't want to babysit the inspection-and-propagation cycle for
  each.
- Default (both gates) for anything load-bearing for the paper or
  involving a sample-definition / parser change.

## Guardrails

- **Stop at greenlight gates** (unless `--auto` or `--auto-after-pick`).
  Step 1 → step 2 (researcher picks), step 4 → step 5 (researcher
  confirms results). Do not chain past these without an explicit
  go-ahead or an auto-mode flag.
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
