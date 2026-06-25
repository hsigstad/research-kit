# Abstracts

Loads on top of [`../writing_style.md`](../writing_style.md) (general
baseline). The abstract is the most-read part of any paper; different
rules apply.

---

- **The first sentence of an abstract states the question.** No exceptions.
  Not the literature gap ("A large literature documents X; we extend it by
  Y"), not the contribution ("We construct the first dataset of …", "We
  develop a new method for …", "We propose a framework that …"), not the
  setting. The question — empirical, policy, or methodological — comes
  first; the contribution comes after the question is established. Compare:
  - Lit gap first (wrong): "A large detection literature has documented
    corruption in procurement using anomaly indicators. We extend it by …"
  - Contribution first (wrong): "We construct the first large-scale dataset
    of procurement-corruption cases classified by scheme."
  - Question first (right): "How is corruption in public procurement
    organized, and how does its organization respond to enforcement?"
  - Question first, methodological framing (right): "What does
    two-stage least squares identify in models with multiple treatments
    under treatment effect heterogeneity?"

  Methodological papers are not exceptions — the methodological question
  *is* the substantive question.

- **Plain language: every term understandable to anyone in the abstract's
  audience.** The abstract's audience is anyone who might be interested in
  reading the paper — not just specialists in your subfield. Every term
  must be understandable to that whole audience. Technical terms are fine
  only if every plausible reader would know them; otherwise define inline
  or paraphrase. Audience-dependence: in an econometrics paper, *2SLS* and
  *LATE* are fine without gloss; in an applied paper aimed at economists
  and policymakers, the same terms should be paraphrased or defined.
  Even when a category noun is technically appropriate (e.g., *causal
  mechanism* in applied work), prefer a plain paraphrase: "the effect is
  driven by X" reads better than "the mechanism is X". Specific
  applications:
  - **Category nouns standing in for paper-specific concepts**
    (*mechanism*, *framework*, *approach*, *method*, *factor*,
    *dimension*, *aspect*, *scheme type*, *channel*). When the meaning is
    paper-specific, either paraphrase in plain language, or keep the
    category noun and give 2–3 concrete examples inline. Compare:
    - Vague: "We classify procurement corruption by mechanism."
    - Paraphrased: "We classify procurement corruption by how the
      corrupt arrangement works — whether actors split expenditures, rig
      specifications, or overpay after the award."
    - Category noun with examples: "We classify procurement corruption
      by scheme type — for example, expenditure splitting, specification
      rigging, or post-award overpricing."
  - **Author-coined compounds** (*mechanism-labeled*,
    *validated-LLM-pipeline*). See general §4. Define inline on first
    use, or replace with self-explanatory phrasing. In the abstract,
    prefer the self-explanatory phrasing.
  - **Foreign-language terms** (italicized Portuguese, German, etc.). Use
    the English equivalent in the abstract; define in the paper body.
    Compare:
    - Avoid in abstract: "the share of decisions citing *fracionamento*
      fell from X to Y"
    - In abstract: "the share of decisions citing expenditure splitting
      fell from X to Y"
  - **Repurposed everyday terms.** When a common word ("compliance",
    "exposure", "treatment") has a paper-specific meaning that differs
    from its ordinary sense, paraphrase or define on first use.
- **Close with a takeaway or implication, not a categorical descriptive
  claim.** The last sentence of the abstract is the answer to "so what?".
  Should be a substantive implication for theory, policy, or further
  research. Compare:
  - Categorical: "Anti-corruption instruments are inherently
    scheme-specific."
  - Implication: "Our results suggest that anti-corruption tools targeting
    one mechanism push corruption into others; effective policy needs
    portfolio-level monitoring across margins."
- **No self-categorizing prefaces.** Drop "This is a descriptive paper:",
  "This study is theoretical in nature:", "In this paper, we provide a
  comprehensive overview of:", "The actionable response is:". The reader
  can tell from the content; flagging a finding as "actionable" or a
  sentence as a "takeaway" reads as scaffolding rather than substance.
- **Numbers, not qualifiers.** "65 percent" beats "substantial". Don't
  hedge in front of a number you have ("a substantial share — almost
  one-third"); just say "almost one-third".
- **Length: ~150 words is the default target.** Major economics
  journal caps for context — AER, QJE, ReStud: 150; Econometrica:
  250; AEJ, JPE: 100. 150 fits everywhere except JPE and AEJ. By
  general §1's deletion principle ("if a paragraph reads fine when
  you delete a sentence, delete it"), an abstract running to 300+
  words is almost always two or three content blocks too long. The
  abstract carries the question, the headline result with its
  magnitude, one load-bearing supporting fact (mechanism, robustness,
  or heterogeneity — pick one), and the takeaway. Secondary findings
  belong in the introduction, not the abstract. If you find yourself
  writing a fifth result-sentence, cut it; the reader will find it
  in the body.
