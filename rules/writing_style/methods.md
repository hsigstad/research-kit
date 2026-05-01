# Methods sections (identification / empirical strategy)

Loads on top of [`../writing_style.md`](../writing_style.md) (general
baseline) and [`body.md`](body.md) (body baseline).

---

- **State the identification strategy clearly.** "Identification,
  identification, identification" (Cochrane). Much empirical work boils
  down to a claim that "A causes B" — explain how the causal effect is
  identified, in plain language, before the equations.
- **State the assumptions explicitly.** Each identifying assumption
  named, motivated, and defended. Discuss what could break each and how
  the design responds.
- **Keep theory minimal.** Only the model that is actually taken to the
  data. Don't write a "general" model and specialize. See [`body.md`](body.md).
- **Specification choices justified.** Each non-obvious choice — clustering
  level, fixed effects, sample restrictions — needs a one-sentence
  justification when introduced.
- **Robustness story planned.** What variations of the specification
  appear later, and why each addresses a specific concern.
- **What the design cannot identify.** Be explicit about parameters
  the design does not pin down (LATEs vs. ATEs, weighted vs. unweighted,
  always-takers vs. compliers). Naming the limitation here is honest;
  hiding it invites a referee to find it.
- **Formal + informal pairing.** A formal expression (the regression,
  the IV setup, the discontinuity equation) gets a one-sentence intuition
  alongside it. See general §5.
