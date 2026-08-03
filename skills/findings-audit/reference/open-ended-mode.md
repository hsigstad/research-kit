# findings-audit — open-ended residual mode

Loaded when `/findings-audit --mode open-ended` is invoked. Replaces §3–6 of the
targeted procedure (skip falsification-pattern derivation and per-finding
adjudication). Slower; run quarterly or after a corpus expansion.

Instead of §3–6:

1. Sample (or take all, if corpus < 200) entries per source type.
2. For each, ask: does this fit naturally under any current finding /
   hypothesis? If yes, name it. If no, why — what new pattern does it
   suggest?
3. Cluster the "no" entries. Patterns that recur across ≥ 3 entries are
   candidate hypotheses.

Output: orphan-entry clusters with representative examples, candidate
hypothesis, and recommended next test. Aggregate-report findings here
often surface measurement gaps the project hasn't noticed (e.g., "CNJ
publishes a recovery-by-tribunal table that the project hasn't used").

Persist results the same way as a targeted run — see
[`reference/output-schemas.md`](output-schemas.md).
