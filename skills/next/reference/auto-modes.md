# /next — auto modes

Loaded when `/next --auto` or `/next --auto-after-pick` is invoked. The Args
section of SKILL.md gives the one-line description of each flag; this is the full
safety semantics for unattended runs.

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
  target — `analyses/an-NNN`, `hypotheses.md:H<#>`,
  `findings.md:<slug>`, etc. A candidate that can't name its
  target is too unfocused for auto mode; bail and require manual pick.
- **Primary target drives propagation.** The candidate's declared
  primary target tells auto mode which `--update <ID>` call to make
  in step 5. No guessing. When the target is `analyses/an-NNN`, the
  AN page is written and finalized in steps 2 and 4 with no skill
  call (see step 5a); only the secondary targets receive `--update`
  invocations.
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
