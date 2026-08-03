# /next — decisions.md entries

Loaded at step 6 when an iteration materially changed how the project is framed
or scoped and a `decisions.md` entry may be warranted. Keep `decisions.md`
curated. An entry goes in only when the decision changes how the project is
**framed** or **scoped**.

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

Always **propose and confirm** — never auto-append to `decisions.md`
(the one exception is auto mode's policy bar; see
[`reference/auto-modes.md`](auto-modes.md)).
