---
name: next
description: "Run one iteration of the project analysis loop: accept (or propose) the next analysis, write the script in the right location with IAT, run it, then propagate to the right docs. Use when the researcher says 'next, do X' or asks 'what's next?'."
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

## Analysis ledger (`docs/analyses/`)

Every project uses the AN-NNN analysis ledger: each new-script iteration
of `/next` produces a new AN page at `docs/analyses/an-NNN-<slug>.md`
as the **primary target** of the iteration. The AN page is the
canonical home of the question, design, headline result, and
confidence. `findings.md` / `hypotheses.md` etc. cite the AN id; they
do not duplicate the magnitude.

The frontmatter contract is defined in
`research-kit/rules/project_docs_contract.md` §"analyses format". A
project may override status/confidence vocabulary and add design keys
via `$PROJ/docs/reference/analysis-schema.yaml` — read it if present
and conform; otherwise use the contract defaults.

If `$PROJ/docs/analyses/` does not yet exist (a project predating the
convention), scaffold it on first invocation: `mkdir
docs/analyses/`, write an `index.md` with the standard heading and a
"Summary table" placeholder, and report the scaffold once in the
end-of-iteration report so the researcher can wire it into the site
build.

## What to read

Always read 1–3. Read 4+ only in propose mode.

1. `$PROJ/CLAUDE.md` — current focus and conventions.
2. `$PROJ/docs/todo.md` — open tasks. Pay attention to the most recent
   `## Session handoff — YYYY-MM-DD` block at the top.
3. The active **paper outline** (`outline.md` or whichever the project's
   CLAUDE.md points at) — to know what section a result would feed.
4. `$PROJ/docs/hypotheses.md` (or `docs/hypotheses/index.md`) — pending tests, status blocks.
5. `$PROJ/docs/findings.md` (or `docs/findings/index.md`) — what's already established and
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
- **Primary target**: almost always `analyses/an-NNN` — every
  new-script iteration produces a new AN page. NNN is the next
  sequential id (max of existing `an-*.md` + 1, zero-padded to 3).
  Exception: an iteration that *re-uses* an existing script (a refit at
  a different sample, a re-run after a parser fix) without producing
  a new AN page declares one of the legacy targets instead —
  `hypotheses.md:H<#>` / `findings.md:<slug>` /
  `institutions.md:<section>` / `theory.md:<framework-id>` /
  `literature.md:<citekey>`. New work = AN page; touching old work =
  the doc that holds the claim.
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
5. Picks up a high-value lead from a prior `/next` iteration
   (the `## Leads from …` blocks in `todo.md`).

**Pursuit gate (estimation candidates).** Before ranking an estimation
candidate highly, ask whether a *null* would be as informative as a
significant result: will the CI be tight enough to rule out the effect
sizes we'd care about *whichever way it lands*? If yes, it's worth
running regardless of outcome. If only a significant result would be
interesting and power is thin, that's a significance-bias trap — the
"hit" would be a winner's-curse artifact and the "null" uninformative;
flag it (`Risk: underpowered — only a "hit" would be interesting`) and
either propose powering it up or deprioritize it. Do not rank a
candidate highly *because* it is likely to return significance. This
does not apply to descriptive/measurement cuts, and a genuinely
exploratory candidate can still be proposed if labelled `(exploratory)`.
See `research-kit/meta/ai_research_workflow.md`, "Significance is not the
win condition."

Candidate format example (new analysis):

```
Candidate 2: AN-019 — within-mayor 2nd-term irregularity contrast
  Description: refit the lame-duck regression on the subset of mayors
    whose 1st and 2nd consecutive terms both fall in the panel, with
    mayor FE to absorb selection-into-reelection.
  Primary target: analyses/an-019 (new AN page)
  Secondary: hypotheses.md:H:lame-duck (status block updated to
             reference AN-019 if confirmed); findings.md (new
             entry citing AN-019 if the result holds)
  Required inputs: build/clean/court_party.parquet (mayor identifiers),
                   build/analysis/doe_irregularity_panel.parquet
  Effort: medium — new script + sample restriction.
  Risk: power may be thin given the within-mayor subset.
```

Candidate format example (re-use of existing script):

```
Candidate 4: H6 vara-FE refit with post-fix sample
  Description: re-run AN-031's fixed-effect spec on the corrected
    sample after the parser fix; check that the productivity axis
    estimate survives.
  Primary target: hypotheses.md:H6 (status block — AN-031 re-run, not new AN)
  Secondary: findings.md:vara-productivity-axis (refresh magnitude)
  Required inputs: build/table/h6_vara_fe.csv (re-run target)
  Effort: low — sample swap + refit.
  Risk: none.
```

**Then stop.** Wait for the researcher to pick one — or to specify
something different. Do not write any script.

## Step 2 — Restate

In one short paragraph, confirm:

- The **question** the analysis answers.
- The **primary target** (carried over from step 1, or asked here in
  specify mode): the single doc entry that will receive a `--update`
  in step 5. Format: `hypotheses.md:H<#>` / `findings.md:<slug>` /
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

### Scaffold the AN page now (before step 3)

When the primary target is a new AN page, write the page *now* — at
the end of step 2, before writing the script. This makes the AN id
stable for the script's IAT header and lets step 4 update the same
file rather than scrambling to create it post-hoc.

Numbering: `ls $PROJ/docs/analyses/an-*.md`, parse the numeric prefix,
take the max and add 1, zero-pad to 3. Show the proposed id once in
the restate output ("Drafting AN-019 at `docs/analyses/an-019-<slug>.md`").

File contents at step 2:

```yaml
---
id: an-NNN
hypothesis: <slug | null>      # H slug if the run tests an existing H; null otherwise
type: <descriptive | causal | placebo | robustness>
status: pending                # use the project schema's "queued" / "draft" if it overrides
status_date: <today>
confidence: pending
created: <today>
script: source/<dir>/<base>.py
target: build/<dir>/<base>.<ext>
design:
  sample: <one line from the restate>
  specification: <one line, felm-style if applicable>
  notes: <free-form>
  # project-specific keys from docs/reference/analysis-schema.yaml
---
# AN-NNN: <research question>

## Question

<the question, in 2-3 sentences — copy from the restate>

## Design

<a few sentences on sample, specification, identification — what is
load-bearing for interpretation but not in the frontmatter>

## Results

*Pending — emits `<target>`.*

## Interpretation

*Pending.*

## Follow-ups

*Pending — see Step 4 of /next for the puzzles / extensions / blind-spots taxonomy.*
```

Read `$PROJ/docs/reference/analysis-schema.yaml` first if it exists
and conform the frontmatter to it (status vocabulary, design keys).
If the schema is absent, use the contract default above and flag
the absence once in the end-of-iteration report.

The script written in step 3 should include `# AN-NNN` in its IAT
header so the source-to-AN back-link is greppable.

## Step 3 — Write the script

Location and naming (per workspace.md "Source and build naming convention"):

- **Analysis backing an AN page (default)** → `source/analysis/an-NNN-<slug>.py`
  → outputs at `build/table/<slug>.{csv,tex}` and/or `build/figure/<slug>.{pdf,png}`
  per file extension. The AN-page is the unit; the script location mirrors
  `docs/analyses/`. Multi-AN scripts that back several AN pages (e.g. a regression
  module shared across AN-001/002/003) use a descriptive name without the AN
  prefix and each AN page's `script:` field points at the same path.
- Paper-table builder → `source/table/X.py` → `build/table/X.{csv,tex}`
- Paper-figure builder → `source/figure/X.py` → `build/figure/X.{pdf,png}`
- Legacy projects: `source/table/X.py` is also accepted for analysis scripts on
  projects that historically organized analyses there. New default for analysis
  is `source/analysis/`; mixing the two within a project is fine as long as each
  AN page's `script:` field is accurate.
- **Multi-output scripts** (more than one output of the same suffix) must
  write into a folder named after the script:
  `source/figure/X.py` → `build/figure/X/<name>.png`, not sibling files like
  `build/figure/X_a.png` + `build/figure/X_b.png`. The script-to-output
  mapping must be recoverable from the path alone.
- Underscore-prefix (`source/analysis/_foo_check.py`) for one-shot
  exploratory checks kept for reproducibility but not part of the
  pipeline. Use sparingly — most scripts should not need it.

**Table and figure.** When the result is quantitative *and* has a
natural visual form, produce both: a machine-readable table
(`.json` / `.csv` / `.parquet` — what the build, paper macros, and
review read) and a figure (`.png` / `.pdf` — what a human scans).
Emit both from the analysis script, or from the analysis script plus a
sibling figure script, sharing the script base name and following the
project's `source/` layout. The AN page's `## Results` then embeds the
figure and reports the table's headline numbers (step 4). A pure-count,
linkage, or paper-table analysis with no meaningful visual is exempt —
don't manufacture a figure. Defer to any project-specific output
convention in the project's `CLAUDE.md`.

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
- **Sanity-check against prior magnitudes** in `findings.md` or
  `stylized-facts.md`. This catches sign flips, unit confusions, sample
  mismatches.

Report a short summary to the researcher:

- N.
- Headline number(s) with SE/CI if applicable.
- Whether it confirms, refutes, or qualifies the prior expectation.
- Any surprise worth flagging.
- **Read the CI, not the p-value.** Significance is not the success
  condition of the run. A *tight* null (CI that rules out effects we'd
  care about) is a positive result — say so, don't treat it as a
  failure. A *significant* estimate from a thin-power design is suspect
  (winner's curse), not a discovery — flag it rather than headlining it.
  Never re-run specs in search of significance.

**Stop and let the researcher confirm before doc propagation.** Doc
edits are harder to reverse than re-running a script.

### Finalize the AN page before propagating

After a successful run (and before step 5), open the AN page created
in step 2 and fill in:

- `## Results` body: if the analysis produced a figure, **embed it**
  (`![caption](<repo-relative path>)`) at the top of the section, then
  give a short prose summary of the headline number(s) with the table
  reference and the surprise-or-not call. When the result is a named
  table (or several panels), use `### Table: <descriptive name>`
  subheaders so the eye lands on the right block first. Keep the prose
  tight — the place for full interpretation is downstream (a finding
  entry, a hypothesis status block), not the AN page.
- `## Interpretation`: narrative, not a re-listing of the numbers.
  When there are multiple distinct takeaways, lead each bullet with a
  short bolded handle (e.g., `- **Direction:** the coefficient flips
  sign on the runoff sample.`). A single-takeaway result can stay as
  one paragraph. **Close the section with a `**Confidence rationale
  (<color>).**` paragraph** justifying the badge in the frontmatter —
  what made it green vs yellow, what specific concern keeps yellow
  from being green, what would tip a yellow to green. This is the
  single most useful sentence on the page for a reader scanning
  badges; never omit it.
- `## Follow-ups`: brainstorm using the taxonomy below.
- Frontmatter: `status: done` (or the project schema's interpreted
  equivalent), `status_date: <today>`, `confidence: <green/yellow/red>`
  per the inspection, and `headline: <one sentence with direction,
  magnitude, significance>`.

This is a direct write to `docs/analyses/an-NNN-<slug>.md` — no skill
call. The AN page IS the primary target; step 5a below treats it as
already updated.

#### Follow-up taxonomy (`## Follow-ups`)

After interpreting the result, think hard about what it implies, what
it leaves unanswered, and what would make it more convincing. Organize
into three categories:

- **Puzzles** — things in the result that are surprising,
  counter-intuitive, or don't fit the prior. Each puzzle states
  what's unexpected and proposes a concrete diagnostic.
  Examples: a wrong-sign coefficient → subgroup decomposition; effect
  in one panel but absent in another → composition check; unexpectedly
  small N → trace the merge/filter; significant placebo → mechanical-
  correlation or specification-error check.

- **Extensions** — analyses that deepen or sharpen the finding,
  building on the same outcome with different cuts or robustness.
  Examples: heterogeneity by another covariate; alternative spec
  (different FE, clustering, sample); dose-response with treatment
  intensity; placebo not yet run.

- **Blind spots** — things *this* analysis cannot answer but that
  the result makes more important to investigate. May need different
  data, outcomes, or identification.
  Examples: result shows the effect exists — but does it affect
  downstream quality (appeals, reversals)?; we measure the connected
  party — but what about the counterparty?

**Format.** Rank globally by priority (1 = most urgent), tagging each
with its type:

```markdown
## Follow-ups

1. **<short title>** *(puzzle | extension | blind spot)*:
   <what's surprising / what it would test / what's missing>.
   Suggested script: `<slug>.<ext>`
```

If the result is clean and expected and there's nothing to chase:

```markdown
## Follow-ups

None — result is clean and expected.
```

**Ranking heuristics.** A puzzle that threatens the paper's main
result outranks an extension. An extension needed for the next draft
outranks a speculative blind spot. A diagnostic that unblocks other
analyses outranks a standalone robustness check.

**Calibration.** Aim for 0–5 follow-ups per analysis. Don't manufacture
follow-ups for completeness. Every item should be specific to *this*
result; skip boilerplate ("run more robustness checks").

**Routing** (handled in step 6; noted here so the brainstorm anticipates
where each item goes):

- Actionable puzzles → `todo.md` under a `## Leads from <script-name>
  — YYYY-MM-DD` heading.
- Broader blind spots → `docs/thinking.md` under the appropriate
  section ("Current open questions" or "Possible directions").
- If a follow-up tests an existing hypothesis, note the H slug in the
  entry so the hypothesis page can be cross-referenced later.

## Step 5 — Propagate to docs

### 5a. Update the primary target

The primary target declared in step 1/2 receives a **surgical
`--update`** call, scoped to one entry, with the triggering artifact
attached so the skill has the build context without re-reading the
project:

| Primary target | Invocation |
|---|---|
| `analyses/an-NNN` *(default)* | **No skill call** — the page was written in step 2 and finalized in step 4. Move to 5b. |
| `hypotheses.md:H<#>` | `/hypothesis --update H<#> --artifact AN-NNN` (the AN id of the script being re-used; the skill resolves it to script/target/headline) |
| `findings.md:<slug>` | `/findings --update <slug> --artifact AN-NNN` |
| `institutions.md:<section>` | `/institutions --update <section> --artifact AN-NNN` |
| `theory.md:<framework-id>` | `/theory --update <framework-id> --artifact AN-NNN` |
| `literature.md:<citekey>` | `/literature --update <citekey> --artifact AN-NNN` |

**`--artifact` takes an AN id, not a build path.** The propagation
skills resolve the AN id by reading `docs/analyses/an-NNN-*.md` to
recover script + target + headline. This keeps the citation in the
citing doc on the AN id (stable across re-runs) rather than the
build path (which may move under the script if the output set
changes). For one-off cases where the run produced an output not
yet ledgered, fall back to `--artifact build/<path>`; the resulting
edit will note the missing AN entry as a lint.

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
| Null result on a candidate hypothesis | first judge whether the null is *informative* (CI rules out effects we'd care about) or merely *underpowered* (wide CI). An informative null is a finding — record it via `/findings --extend` and note it in the hypothesis status block. Only propose a `decisions.md` demotion when the design was well-powered; an underpowered null demotes nothing on its own (flag it as "needs more power" instead) |
| Re-run with new data/parser | walk every cited number; run `/findings --refresh` to flag drift in `findings.md` and `stylized-facts.md` |

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

### 5c / 5d. Ledger maintenance (conditional)

If the project maintains an `artifacts.yaml` registry
(`docs/reference/artifacts.yaml`) or a validation ledger
(`docs/validation.yaml` / legacy `paper/validation.yaml`), update them now —
append an artifacts entry for any new output, and a `pending` validation row for
any new script. Exact fields and the re-use/stale rules are in
[`reference/propagation-ledgers.md`](reference/propagation-ledgers.md). If
neither file exists, skip cleanly — the project hasn't opted in.

### Conventions

- **Confidence tags**: default new findings to 🟡 (single source).
  Promote to 🟢 only on independent replication. Use 🔴 for
  parser-dependent or sample-sensitive results.
- **`@claim` registry**: for load-bearing inline numbers, wrap with
  the `@claim` tokens used elsewhere in the project. Lets
  `/findings --refresh` recheck mechanically after a re-run.

## Step 6 — Close out

- Append a one-line entry to `docs/done.md` under today's date with the
  script path and the headline number. In AN-mode, lead with the AN id:
  `AN-019 (source/analysis/an-019-within-mayor-lameduck.py) — within-mayor
  contrast: -0.4pp [CI: -1.2, +0.4], result attenuates to noise.`
- **Capture tangential leads in `todo.md`.** If steps 3–5 surfaced
  high-value tangential questions — a surprising coefficient, an
  unexplained pattern, a natural follow-up cut, a data quality issue
  worth investigating — append them as new tasks under a
  `## Leads from <script-name> — YYYY-MM-DD` heading in `todo.md`.
  Keep each item to one line; include enough context that a future
  `/next` proposal can pick it up without re-reading the build output.
  Only record genuinely useful leads — not every minor observation.
  Do not act on them in this iteration (one question per script).
- If the run **materially changed the paper outline** (added or removed a
  finding from a section, changed a load-bearing number, demoted a
  hypothesis), **propose a `decisions.md` entry** and ask before writing.
  Do not auto-append to `decisions.md`.
- **If the repo has convention-guard scripts (`source/diagnostic/*.py`
  that exit non-zero on a violation), run them and confirm green before
  the close-out commit.** These are the project's own drift guards (e.g.
  a canonical-spec / superseded-citation check). A red guard means this
  iteration introduced a NEW violation — fix it before committing. Run it
  here at the checkpoint rather than as a blocking commit hook: in a
  shared repo a repo-wide guard can go red for another session's change,
  so read the `[FAIL]` line and act only on your own.
- If the session is ending: invoke `/handoff`. Otherwise the session
  continues — the researcher can call `/next` again.

## Decisions.md — what goes in

At step 6, if the iteration materially changed how the project is **framed** or
**scoped** (hypothesis demoted, design dropped, paper restructured, load-bearing
number revised, sample-definition change with downstream effects), **propose** a
`decisions.md` entry and confirm before writing. Bug fixes, parser tweaks, and
finding refinements do NOT go here (commit message + `done.md`). The Yes/No
criteria and the entry format are in
[`reference/decisions-entries.md`](reference/decisions-entries.md).

## Auto modes

`--auto` (both gates off) and `--auto-after-pick` (pick gate on, results gate
off) bypass the stop-gates for unattended runs. Errors still halt the loop;
auto-pick requires a risk-free candidate with a named primary target; propagation
runs by the same checklist; the end-of-iteration report is the audit trail. Full
safety semantics and when-to-use in
[`reference/auto-modes.md`](reference/auto-modes.md) — read it before running
either flag.

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

## Completion gate (mandatory, all modes)

An iteration is not finished until every item below passes. Run these
before writing the end-of-iteration report; do not end the turn with
any of them failing:

1. **The script ran** and its outputs exist in `build/` at the
   bijection-correct paths (`source/analysis/X.py` → `build/.../X.*`).
   A written-but-not-run script is a mid-stream handoff note, not a
   completed iteration.
2. **Deterministic lint passes**: run
   `python3 $ROOT/research-kit/tools/check_docs.py <slug> --json` and
   `python3 $ROOT/research-kit/tools/citations.py <slug> --json` and fix
   any NEW errors your edits introduced (pre-existing errors: report,
   don't fix silently).
3. **The AN page's `script:` field** points at the actual script path.
4. **Real-data guard**: if the project runs analyses remotely (e.g.
   connect), confirm interpreted outputs are real returned artifacts,
   not stale local/synthetic files, before propagating a single number.

If a gate cannot pass (e.g. the script needs server data), say so
explicitly in the report and write a handoff note instead of
presenting the iteration as complete.
