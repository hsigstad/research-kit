---
name: referee-panel
description: "Run a finding-level mechanical auditor panel over a project's paper build: ~12 single-failure-mode lenses (identification, claim-evidence, numerical, model-equation, theory-logic, robustness, sample-construction, abstract-conclusion, literature, external-validity, measurement-validity, power/multiple-testing), each emitting structured findings under a cannot_verify-or-cite contract, then an adversarial verify pass, then an editor memo. Use for a pre-submission red-team of a paper, complementary to /findings-audit (evidence) and the community-persona referee reports."
---

# /referee-panel — pre-submission mechanical auditor panel

A multi-agent **finding-level** red-team of a paper build. Each of ~12 lenses
audits ONE failure mode, returns structured findings under a shared
`cannot_verify`-or-cite contract, every finding is then **adversarially
verified** (a skeptic tries to refute it), and an editor **dedups, ranks, and
writes a memo**. Pattern borrowed from `github.com/Ingar30/reviewer`.

This is the **mechanical-failure-mode** axis of review. It complements, and does
not replace:
- **community-persona referee reports** (`docs/reference/referee_reports/R*.md`) —
  the "which reviewer community reacts, and how" axis;
- **`/findings-audit`** — stress-tests headline findings against *external*
  evidence;
- **`/style-review`** — prose.

Output is AI-generated: **triage before acting**. The memo's "Cannot verify"
section names what artifact would settle each open question.

## Arguments

- `/referee-panel` — infer the project from cwd; audit its primary maintained
  build (see "Resolving the build" below). Confirm the build with the user if
  ambiguous.
- `/referee-panel <build>` — audit a specific build, e.g.
  `/referee-panel paper/oe.tex` or `/referee-panel projects/deterrence paper/science.tex`.
- `/referee-panel --lenses id,claim-evidence,numerical,power-multiple-testing` —
  run only a subset of lenses (keys below). Default runs all 12.

## What this skill does (the flow)

1. **Resolve the build and its sources.** Identify the driver `.tex` under review
   and the fragments it `\input`s, IN READING ORDER. A build's `paper.tex`-style
   driver often assembles from `shared/*.tex`; open the driver and follow every
   `\input`. Include the numerical-claim ledger (`numbers.json`) if the project
   keeps one. **Do not audit an archived/unmaintained build** — check the
   project `CLAUDE.md` for which build is maintained (e.g. deterrence marks
   `paper/paper.tex` archived; the OE submission is `paper/oe.tex`).
2. **Write the one-liner.** Distill the paper's thesis to one sentence (read the
   abstract + intro). This orients every auditor; a vague one-liner yields vague
   findings.
3. **Run the panel** via the bundled Workflow script (next section).
4. **Persist the output.** When the workflow completes, extract `memo` and
   `confirmed` from the result and write:
   - `docs/reference/referee_reports/<build>_audit_panel.md` — the memo, with a
     provenance header (target build, method, raw/refuted/confirmed counts, date,
     an "AI-generated, triage before acting" note).
   - `docs/reference/referee_reports/<build>_audit_panel_findings.json` — the
     structured `confirmed` findings (traceability: per-finding location,
     verdict, verify_reason, suggested_fix).
5. **Report to the user**: counts (raw -> refuted -> confirmed), the blocking /
   major issues, and where lenses converged (convergence = signal). Offer to
   commit. Do not commit unprompted.

## Running the workflow

The generalized, args-driven script lives at
`reference/panel_workflow.js` (relative to this skill). Invoke it with the
`Workflow` tool, passing **real JSON** as `args` (never a stringified blob):

```
Workflow({
  scriptPath: "<abs path to this skill>/reference/panel_workflow.js",
  args: {
    project:   "deterrence",
    target:    "paper/oe.tex",
    dir:       "/workspace/projects/deterrence/paper",
    sources:   ["oe.tex", "shared/intro_oe.tex", "shared/framework.tex",
                "shared/methods.tex", "shared/results.tex", "shared/discussion.tex",
                "shared/si.tex"],
    numbers:   "numbers.json",
    one_liner: "Accuracy-equivalent ML vs LLM predictors have opposite incentive properties: classifiers key on defendant type (destroying deterrence), LLMs key on case evidence (preserving it).",
    lenses:    null
  }
})
```

- `dir` is ABSOLUTE; `sources` and `numbers` are relative to it, in reading order.
- `numbers`: pass the ledger filename, or `null` if the project has none.
- `lenses`: `null` runs all 12; or pass an array of keys to run a subset.
- The workflow runs in the background and returns `{ counts, confirmed, memo }`
  via a task notification. The script has **no filesystem access** — step 4
  (persisting to the repo) is done by you, the caller, after it completes.

To iterate on the panel itself (add a lens, retune a focus), edit
`reference/panel_workflow.js` and re-invoke; use `resumeFromRunId` to replay
unchanged agents from cache.

## Lens keys

`identification`, `claim-evidence`, `numerical`, `model-equation`,
`theory-logic`, `robustness`, `sample-construction`, `abstract-conclusion`,
`literature`, `external-validity`, `measurement-validity`,
`power-multiple-testing`.

`measurement-validity` covers ML/LLM-derived measures (rater independence, prompt
sensitivity, contamination, reproducibility) — keep it in for any paper whose
evidence is model-generated. `power-multiple-testing` carries the
informative-null discipline (a tight null is a finding; a wide one dressed as
"no effect" is not) and checks for **asymmetric inference** across the arms of a
central contrast.

## Cost & scale

A full 12-lens run is ~25 agents (12 audit + up to 12 verify + 1 editor),
roughly 30-40 min and ~1.5-2M subagent tokens at medium size. Subset with
`--lenses` for a cheaper focused pass. This exceeds the default medium
workflow-size guideline (~15 agents) by design — a full panel is the point;
say so to the user if they expect a small run.

## Notes

- Findings cite `file:line`; verify them against the current build before acting
  (line numbers drift as the draft changes).
- Convergence across independent lenses is the strongest signal — the editor is
  told to elevate a multi-lens finding toward blocking.
- Re-run after major revisions; use `--lenses` to re-check only the lenses whose
  findings you addressed.
