# How to Use AI for Research

A methodology doc (not a tooling doc — see `claude_code_workflows.md` for
setup/skills/MCP). The question this answers: **at each stage of a research
project, what should AI do, what must I still do myself, and how do I verify
the AI's output well enough to put my name on the paper?**

Guiding principle: exploit AI as much as possible while keeping my credibility
intact. That means aggressive delegation paired with deliberate, stage-specific
human checks — not blanket distrust, and not blind acceptance.

---

## Project lifecycle: front-loaded AI, then human steers + validates

The stages below describe *what happens at each step*. This section describes
*how AI involvement shifts over the arc of a project*.

**Early phase — AI heavy.** In the exploration phase of a new idea, AI is
doing most of the work: mapping the literature, identifying data sources,
brainstorming identification strategies and quickly checking them, running
descriptives, collecting anecdotal evidence, generating and testing
hypotheses. This is the right place to delegate aggressively because being
wrong is cheap — bad directions get abandoned, not published.

**Middle phase — human steers.** Once an AI-generated draft has real
potential, the human role shifts to *directional guidance*: pushing the idea
toward the novel insight the AI didn't see, reframing, killing dead ends
that the AI won't kill on its own. I find AI consistently misses the
strongest version of an idea, and this is where my comparative advantage
sits.

**Late phase — human validates.** As the paper stabilizes, the human role
becomes validation and quality control: the stage-by-stage checks below,
culminating in stages 8-9.

### Risks specific to the transition

1. **Per-script validation rather than a project-wide gate.** A hard
   project-wide gate ("stop, rebuild from scratch") is too strict. Instead,
   every script on the build path of a paper result carries a status in
   the validation ledger — see stage 8. Validation happens
   script-by-script, not project-by-project.

2. **Provenance of exploration-phase choices.** In the AI-heavy early
   phase, sample filters, variable definitions, and analytic choices
   accumulate without anyone tracking *why*. By the validation phase,
   "why is the sample restricted to X" often has no recoverable answer.
   Cheap fix: `docs/decisions.md` updated in near-real-time during
   exploration (see stage 4). AI can draft entries; the point is that
   *something* exists to audit later.

3. **False convergence.** AI is good at making a half-formed idea *look*
   finished — coherent prose, plausible tables, a clean narrative. The
   "this has real potential" signal can fire too early. Countermeasure:
   before committing meaningful human effort, run an adversarial agent
   (as in stage 6, but earlier and harsher) whose sole job is to kill the
   paper. If the draft survives, commit. If not, back to exploration.

### Shape of validation tracking

The unit of validation is a **script**, not a result. A validated script
stays trusted even if its upstream inputs change — what needs revalidation
is whichever upstream script actually changed. This gives a dependency
graph: a paper result is trustworthy iff every script on its build path
(cleaning → intermediate → table/figure generation) is validated and
unchanged since validation.

This plays well with the "one script per table/figure" convention already
in place — the mapping from paper element to validation unit is mechanical.
Long, multi-purpose scripts defeat per-script validation, so short scripts
are a prerequisite.

Git branches for "AI-generated" vs. "human-validated" code are tempting
but don't work: branches track code state, not validation state, and they
miss the failure where editing a previously-validated script silently
invalidates downstream results.

**Mechanics — ledger schema, hash staleness, AI validation methods — live
in stage 8.**

---

## Stages

### 1. Ideation

- **AI does:** help *develop* my own ideas — stress-test, find related
  work, poke holes, suggest extensions. Not primarily a source of ideas.
- **I do:** generate the seed ideas myself, pick what's worth pursuing,
  judge fit with my agenda. I want to decide myself what to work on.

### 2. Literature review

- **AI does:** generate queries, hit Semantic Scholar / OpenAlex, curate,
  expand via citation graphs, write `literature.md` + bib, download PDFs.
  (See `/literature` skill.)
- **I do:** skim the curated list, read the key papers myself.
- **Check:** the dangerous failure mode isn't fabricated citations (easy
  to catch) — it's real papers cited for claims they don't actually make,
  or citations where the AI inverted the finding. Procedure: for every
  citation that survives into the final draft, download the PDF and have
  AI verify the specific claim attributed to it is actually in the paper
  (*citation-claim check* — see AI validation methods in stage 8). Human
  spot-check before submission on the load-bearing citations.

### 3. Proofs / theory

- **AI does:** work out proofs, propose propositions, suggest alternatives.
- **Adversarial check:** second AI agent tries to break the proof.
- **Before publication:** consider formalizing load-bearing results in
  **Lean**. Converts "I think this is right" into machine-checked
  certainty, with caveats below.
- **I do:** understand every step well enough to defend it in a seminar.

**Lean caveats.** Lean verifies the formal statement follows from the
formal assumptions — not that the formal statement matches the paper's
informal claim. The dominant risk is the *statement-translation gap*: AI
is prone to silently weakening a hypothesis to make a proof go through.
Secondary risks: mathlib's definitions of standard concepts may drift
from what the paper assumes; applied-micro objects (equilibrium,
mechanism design) have thin mathlib coverage, forcing infrastructure
work; watch for `sorry`, classical axioms, and `native_decide`.
**Upshot:** Lean converts "is the proof correct?" into "does the formal
statement faithfully encode the claim?" — much easier to check by eye.
Worth it for one or two load-bearing theorems, not the whole theory
section.

### 4. Data work / coding

- **AI does:** write cleaning, intermediate-build, and table/figure
  scripts. Happy to delegate heavily.
- **I do:** comment on design decisions, review outputs, catch framing
  mistakes the AI can't see.
- **Script discipline (prerequisite for stages 8–9):** one script per
  table/figure, short and single-purpose, so per-script validation is
  tractable. Long multi-purpose scripts defeat the whole scheme.
- **Running provenance in `docs/decisions.md`:** updated in near-real-time
  as sample filters, variable definitions, and analytic choices are made.
  AI can draft entries; the point is that the *why* exists to audit
  later. This is the only defense against "no one remembers why the
  sample is restricted to X" showing up at submission.
- **IAT convention** (`/iat-check`) for per-script documentation: INTENT,
  REASONING, ASSUMES, SOURCE comments plus validation guards after joins
  and filters.
- **Sanity checks** on summary stats, distributions, and pre/post-join
  row counts. AI-generated code is sloppy about silent row drops — every
  join and filter gets an assertion.
- The final targeted pass over critical-path scripts happens in **stage
  9**.

### 5. Writing

- **AI does:** draft sections, revise, tighten prose, format tables.
- **I do:** comment, redirect, rewrite where voice/argument matters.
- **Check:** I read every sentence before submission. Non-negotiable.

### 6. Adversarial referee

Before submission, have an AI agent read the draft cold as a skeptical
referee: list the strongest objections, flag weak identification claims,
question robustness. Cheap and surprisingly useful — covers ground beyond
the proof-checking agent in stage 3 (which only sees the math). Runs
*before* stage 7 because referee critique often changes what code needs
to run.

### 7. Clean-room reproducibility run

Fresh environment, locked package versions, fixed seeds, run the full
pipeline end-to-end from raw data to final tables/figures. AI-written
code is sloppy about hidden state and implicit dependencies, so this
catches real bugs. Required for replication packages anyway.

### 8. Final paper check

The highest-stakes stage. A **validation ledger** at `paper/validation.md`
tracks every script on the build path of anything in the paper. Rows are
scripts, not results (see the lifecycle section for why code is the right
unit).

**Ledger schema — one row per script:**

| Column        | Contents                                                  |
|---------------|-----------------------------------------------------------|
| `script`      | Path, e.g. `source/table2_main.py`.                       |
| `produces`    | Table/figure name or build artifact.                      |
| `depends_on`  | Upstream scripts by path.                                 |
| `hash`        | Git hash of the script at validation time.                |
| `ai_checks`   | List of AI validation methods applied, with dates.        |
| `human_check` | Date of human review (empty = not yet reviewed).          |
| `reviewer`    | Who did the human review (relevant for joint projects).   |
| `status`      | pending / ai-verified / human-verified / stale.           |

A paper result is trustworthy iff its generating script and every
upstream script it depends on are `human-verified` and unchanged —
computed from the dependency graph, not tracked per-result.

**Pre-submission checker.** Walks every script in the ledger, recomputes
its hash, flips changed scripts to `stale`, and propagates staleness
through `depends_on`. Nothing submits with `pending` or `stale` on the
critical path.

#### AI validation methods (`ai_checks` vocabulary)

Different scripts and stages call for different forms of AI verification.
The ledger records *which* methods were applied, not just "AI looked at
it" — otherwise `ai-verified` collapses to rubber-stamping.

| Method                    | What it does                                                                            | Used at                     |
|---------------------------|-----------------------------------------------------------------------------------------|-----------------------------|
| `lean`                    | Formal proof in Lean.                                                                   | Stage 3 (proofs).           |
| `adversarial_proof`       | Second AI tries to break the proof.                                                     | Stage 3.                    |
| `adversarial_referee`     | Skeptical-referee read of the full draft.                                               | Stage 6 (whole paper).      |
| `citation_claim_check`    | AI reads the cited PDF and verifies the attributed claim is actually in it.             | Stage 2.                    |
| `line_by_line_trace`      | AI walks each line of a script and explains the logic.                                  | Data / coding scripts.      |
| `property_assertions`     | AI generates invariants (row counts, key uniqueness, distributions) and checks them.    | Cleaning / join scripts.    |
| `output_sanity`           | AI compares script outputs against ex-ante priors (signs, magnitudes, sample sizes).    | Estimation scripts.         |
| `reproduction_run`        | AI re-runs the script from a clean state and diffs outputs against the committed build. | Any script.                 |
| `text_table_consistency`  | AI checks every number quoted in the text matches the corresponding table cell.         | Full draft (stage 8).       |
| `spec_grid`               | AI runs the pre-specified multiverse and reports the full distribution.                 | Estimation (p-hacking).     |

Load-bearing scripts should carry **multiple methods** — e.g. a main
estimation script might have `line_by_line_trace` + `output_sanity` +
`reproduction_run` before a human ever touches it. A thin `ai_checks`
list is itself a warning.

This vocabulary is extensible: new methods go in as they prove useful.

#### Text-table consistency

Runs as part of the stage 8 checker regardless of script validation
status, because it catches a different failure mode (prose quoting a
stale table number). Applied as `text_table_consistency` in the ledger
on the draft itself, plus a **coarse.ink pass** (or equivalent) for
broader claim consistency. Human spot-check on load-bearing claims —
headline coefficients, main percentages, the one-sentence takeaway.

#### Draft reading ledger

Non-negotiable #2 says I read every sentence before submission — but
without tracking, that promise silently decays across revisions (I read
§3 in March, it was rewritten in April, and I never notice). The same
hash-and-stale machinery that tracks scripts also tracks draft prose, at
**subsection granularity**. Sentence-level is too fine (any typo fix
invalidates); section-level is too coarse (one edited paragraph
shouldn't force re-reading everything).

A second table in `paper/validation.md`, parallel to the script ledger.
One row per subsection:

| Column       | Contents                                                       |
|--------------|---------------------------------------------------------------|
| `subsection` | Path, e.g. `sections/identification.tex::Instrument_validity`. |
| `hash`       | Hash of the subsection text at read time.                     |
| `human_read` | Date I last read it.                                          |
| `reviewer`   | Who read it (joint projects).                                 |
| `status`     | pending / read / stale.                                       |

**Hash target.** The raw text between `\subsection{...}` markers,
normalized lightly (collapse whitespace, strip comments) so trivial
reformatting doesn't invalidate but any real edit does. Tables and
figures inside a subsection are excluded from the hash (they're tracked
via the script ledger); surrounding prose, footnotes, and displayed
math *are* included.

**Rows without a parent `\subsection{}`.** Abstract, intro lead-in,
acknowledgements, and similar top-level prose each get their own row —
they're the highest-stakes text in the paper.

**Pre-submission checker.** Walks the `.tex` source, rehashes each
subsection, flips changed ones to `stale`. Same machinery as the
script checker.

#### Sign-off rule

Nothing submits with `pending` or `stale` rows, in either ledger, on
the critical path. Critical path = every script producing a headline
result plus its dependencies, **plus every subsection of the final
draft**.

### 9. Final code review

Not "read everything" — a targeted, time-boxed pass with a checklist.

1. **Identify the critical path.** For each headline result, trace
   backward through `source/` → `build/` → table/figure. Those scripts
   are in scope.
2. **Line-by-line review** of critical-path scripts. Checklist per file:
   filter logic, join keys, sign conventions, sample construction,
   variable definitions match `data.md`.
3. **Spot-check** non-critical-path scripts — read 2-3 randomly, plus
   anything flagged by `/iat-check`.
4. **Record in the ledger.** Human-reviewed scripts get a `human_check`
   date, flipping status to `human-verified`.
5. **Calibration** (occasional, not every paper). Deliberately inject a
   known bug before starting review and check whether the process catches
   it. If it doesn't, the process isn't working.

---

## P-hacking under AI acceleration

When iteration is near-free, the risk of (conscious or unconscious)
p-hacking goes up sharply — you can run hundreds of specifications in an
afternoon. The standard defense is to show the reader everything:

- **Multiverse analysis**: report the distribution of estimates across
  all defensible specification choices (controls, samples, functional
  forms, clustering), not just a preferred spec with a robustness table.
- **Specification curves** as a default figure for headline results.
- **Be generous with robustness checks in the final paper** — if AI
  makes running them cheap, there's no excuse not to show them.

This converts "which spec did you pick and why" from a credibility
problem into a transparency exercise.

**Unsolved issues I'm aware of:**

- *Pre-registration isn't a credible alternative.* I mostly work with
  pre-existing administrative data. PAPs on already-collected data are
  trust-based — nothing prevents filing multiple plans and reporting
  the one that worked, and no one can verify the author hadn't looked
  at the data first. The same trust problem sinks every other proposed
  defense (split-sample with a hold-out, outcome-masking, out-of-sample
  replication on a different dataset): if a researcher is willing to
  cheat, nothing stops them from peeking in parallel. The multiverse is
  the only defense that doesn't depend on trusting the researcher at
  all — a referee or replicator can re-run the full grid themselves and
  see whether the paper's number sits in a typical place. That's why
  it's the answer.
- *Cleaning and sample-selection choices belong in the multiverse.* The
  garden of forking paths includes the cleaning code, not just the
  estimation code. The principled response is to expand the multiverse
  grid to include cleaning and sample-selection dimensions (filter
  thresholds, deduplication rules, which subsample is "main"), not to
  treat cleaning as fixed. Combinatorial explosion is the cost —
  tractable with AI running the specs. This collapses into the
  researcher-DoF point below: the grid only helps if the dimensions are
  honestly chosen.
- *"Defensible spec" is itself researcher-DoF.* The multiverse only
  helps if the *set* of specs is honest. AI is happy to expand or
  contract the set to taste. Partial mitigation: define the spec grid
  upfront, in writing, before running anything.

---

## Review fatigue

The biggest practical failure mode: rubber-stamping AI output because
checking feels like busywork. Named defenses:

- **Time-boxed checklist reviews** instead of open-ended reading. A fixed
  checklist per file type forces a floor of attention and makes stopping
  points obvious.
- **The ledger makes unverified work visible.** `pending` and `stale`
  rows in `paper/validation.md` are a concrete count, not a vague sense
  of "I've looked at most of it."
- **Specific methods required for `ai-verified` status.** Just "an agent
  looked at it" doesn't count — the ledger's `ai_checks` column records
  *which* methods, so rubber-stamping is visible as a thin list.
- **Calibration via injected bugs** (stage 9). Periodically insert a
  known bug and verify the process catches it.

---

## Working with co-authors

Joint projects complicate validation. Key points:

- **Shared ledger.** `paper/validation.md` is version-controlled and
  co-authored like the rest of the paper. The `reviewer` column
  attributes each `human_check` to a specific person.
- **AI code from co-authors.** A co-author sends code they generated
  with AI but didn't carefully review. It arrives looking like "their
  code," but it carries the same risk as my own AI output. Authorship
  and validation are separate: the ledger tracks who *validated* a
  script, not who first wrote it, and a critical-path script needs my
  `human_check` regardless of whose name is on the commit.
- **Credibility floor is per-author.** My non-negotiables apply
  regardless of how much my co-authors delegated. If I put my name on
  it, headline numbers trace back to code *I* verified, even if a
  co-author already did. Their `human_check` doesn't substitute for
  mine on the critical path.

---

## Cross-cutting conventions

- **Data provenance / PII / licensing.** AI assistants have no
  automatic awareness of PII boundaries, scraped-data licensing, or DUA
  terms. I check sources and restrictions at project start; re-check
  when adding data.
- **Data in hosted models.** Concrete rule: no identifiers, no raw
  records from restricted datasets, no DUA-protected schemas pasted
  into hosted models. Synthetic examples or anonymized samples are
  fine for getting code help. When in doubt, work with a local model or
  write code blind against the schema.

---

## Open questions

- How much of stage 8 can be automated vs. needs human eyes?
- Is Lean formalization worth it for applied-micro-style proofs, or
  only for the rare theory-heavy paper?

---

## Non-negotiables (credibility floor)

Regardless of how much AI does upstream, before my name goes on a paper:

1. I understand every proof step.
2. I've read every sentence of the final draft. Concretely: every
   subsection in the draft reading ledger has my `human_read` against
   its current hash.
3. Headline numbers have been traced back to their generating code by
   me — not just an AI, not just a co-author. Concretely: every
   critical-path script has my `human_check` in the script ledger.
4. I can answer seminar questions about methods without looking things
   up.

---

## People to follow / read

- **Anton Korinek** — JEL piece on LLMs for economics research;
  closest match to this use case.
- **Andrew Gelman** — on researcher degrees of freedom, multiverse, and
  the garden of forking paths. Directly relevant to the p-hacking
  section.
- **Ethan Mollick** (*One Useful Thing* blog) — academic workflow angle,
  practical.
- **Terence Tao** — has written publicly about AI + Lean for proof
  verification; directly relevant to stage 3.
- **Simon Willison's blog** — best practical day-to-day LLM workflow
  coverage.
- **Kevin Bryan** (@Afinetheorem on Twitter/X) — econ + AI takes.
- **Lean / mathlib community** — ongoing discussions on what's tractable
  for AI-assisted formalization vs. not.
