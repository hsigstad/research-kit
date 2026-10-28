# Results sections

Loads on top of [`../writing_style.md`](../writing_style.md) (general
baseline) and [`body.md`](body.md) (body baseline).

---

- **Lead with the headline — at the section scale.** The results
  section's *first* paragraph states the main result; order subsections
  so the big finding comes first; no warm-up exercises or exhaustive
  descriptive statistics before the main estimates. This is macro
  ordering (which result leads). It is **not** a license to open every
  analysis subsection or paragraph with its conclusion — within a single
  analysis unit the order is question → method → exhibit → results →
  suggested conclusion (see the next rule). Leading each paragraph with
  its takeaway is the most common conclusion-first failure.
- **Analysis-unit order: question first, conclusion last.** A subsection
  or single result paragraph runs: (1) name the question ("In this
  section we ask whether…"); (2) method, one sentence ("To test this,
  we…"); (3) name the exhibit *before* the numbers ("The results are
  shown in Table~X" / "Figure~X shows…"); (4) state the results; (5) the
  suggested conclusion, marked as inference ("these results suggest…").
  Do not open the unit with the finding and back-fill the evidence.
- **Every number is discussed.** No number in a cited table or figure
  goes without text discussion (Cochrane). "Row 1 of Table 3 shows a
  u-shaped pattern" is fine; "Table 5 shows summary statistics" alone
  is not. See general §10.
- **Name the exhibit a result comes from.** The converse of the rule
  above: when you state a number in prose, cite where the reader can
  see it — "the model agrees with the sitting judge on 69% (Table S1)".
  Every stated result points to its table or figure.
- **Results-paragraph shape: motivate → method → exhibit → interpret.**
  Pose the question, say how you address it ("To test this, we…"), **name
  the exhibit before the numbers** ("The results are shown in Table~X" /
  "Table~X reports…" / "Figure~X shows that…"), then interpret — marking
  the conclusion as inference ("suggests"). Never interpret a number
  before pointing to where it lives; the exhibit reference leads.
- **Open a results section/subsection with a scope sentence.** First
  sentence names the question or task the section settles ("In this
  section, we test whether…") — not a restatement of the heading (that
  padding is still cut; baseline §8).
- **Define the outcome before you report it; walk panels in order.**
  State what the metric is ("agreement is balanced accuracy") before the
  first result that uses it, and introduce a multi-panel exhibit in
  sequence — "In Panel A we show …; in Panel B …" — rather than dropping
  numbers the reader cannot yet interpret.
- **Always state economic significance, not just statistical
  significance.** Express effect sizes in concrete terms (percent,
  dollars, standard deviations, days) alongside the *t*-stat or
  *p*-value. A 2.10 *t*-stat on a 0.0001 effect is statistically
  significant and economically irrelevant.
- **Captions are self-contained.** A skimming reader should understand
  the table or figure from the caption alone. Define every symbol;
  spell out variable names; state what each column shows. See general
  §10.
- **Robustness and heterogeneity belong in subsections, not as preamble.**
  Lead with the main result; put alternatives after.
- **Appendix-pointer sentences lead with the claim, not the
  enumeration.** A sentence whose shape is "Robustness checks —
  dropping the largest sponsor, tightening name matching, party-by-
  sponsor interactions, permutation diagnostics — are reported in
  Appendix E" is hard to read because the reader has to hold a long
  list before reaching the verb. Flip it: "Appendix E shows the
  result survives [the load-bearing variations, named briefly]."
  Same for diagnostic paragraphs whose payload is "we ran X and
  found no anomaly": one sentence in the body, the detail in the
  appendix.
- **Reference figures and tables linearly.** Don't preview ("As we will
  see in Table 6") or recall ("Recall from Table 2"). If you find
  yourself doing this, the linear sequence is wrong.
- **2–3 significant digits.** A coefficient of 4.56783 with a standard
  error of 0.6789 should be 4.6 with a standard error of 0.7.
- **In prose, use one round summary magnitude; ranges and precise
  figures belong in the table.** "Sponsored polls overstate by
  around 7 percentage points" reads better in narrative than
  "sponsored polls overstate by +6.0 to +8.0 pp across the spec
  ladder". The table has the precision; the prose carries the
  headline. Applies to the introduction, the results-paragraph
  summary sentence, and the discussion. Specifications of when the
  magnitude *moves* across cuts (e.g., +8 pp in sparse-coverage
  races vs. +3 pp in dense-coverage races) belong in the
  heterogeneity subsection or the table, not in narrative summary.
- **Don't editorialize the data.** "The temporal evidence is starkest"
  → flag and rewrite. State the finding and the number; let the reader
  judge strength. See general §2.
