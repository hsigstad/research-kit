# Theory sections (model / framework)

Loads on top of [`../writing_style.md`](../writing_style.md) (general
baseline). Theory sections do **not** inherit from `body.md` — the
structural rules differ. Formal+informal pairing matters more here than
triangular ordering.

---

- **Formal + informal pairing.** Every formal definition or assumption
  gets a one-sentence intuition gloss alongside it. See general §5.
  Example:
  > **Assumption 3** (Average Conditional Monotonicity). For all
  > s ∈ S, E[P̃₁ | s(Z)=1] ≥ E[P̃₁ | s(Z)≠1].
  >
  > Informally, this requires that the partial effect of P₁ —
  > instrument 1 — on treatment 1 is, on average, non-negative for
  > each agent across values of the instruments.
- **Minimum theory required.** Only the model that is taken to the data
  (in empirical papers) or the result that motivates the empirical work.
  Don't write a general model and specialize. See [`body.md`](body.md)
  for the broader rule.
- **Mathematical tools are fine when correct** (Shapiro). The robot reads
  formal mathematics; what it cannot read is fancy talk dressed up as
  formality. Less notation is usually better; introduce only the symbols
  the reader needs to follow the result.
- **Inferential phrasing is fine in theory.** "The model implies", "this
  distinction implies", "should displace" are derivations from prior
  theory to predictions, not empirical overclaims. The
  `narrative_claim_check` calibration in `validate-section` recognizes
  this — flag rhetorical overreach but not theoretical inference.
- **Predictions are testable claims.** Each theoretical prediction the
  paper plans to test should be stated as a falsifiable empirical claim,
  not a hand-wavy implication.
- **Don't dress up the model.** Less math is usually better; simpler
  setups leave the result clearer. See general §1.
