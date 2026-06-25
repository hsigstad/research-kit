# Judgment-only writing rules

(Linter handles the deterministic subset per-edit; rules below are
what it can't see. `[ws]` = workspace-specific.)

## Top rules

- **`[ws]` Paper voice never references coauthors.** "Sigurd flagged
  X" / "Following a comment at NBER SI…" → make the claim in the
  paper's own voice.
- **`[ws]` No appendix forward-refs in the intro body.** No
  `Appendix~D` mid-sentence in the lede. Pointers to later *sections*
  are fine in footnotes and the "organized as follows" para.
- **Don't lead an opener with the conclusion.** Paragraph and
  subsection openers name the question, not the answer.
- **Editing a coauthor's draft: minimal intervention.** Change a word
  when wrong; restructure a sentence when broken; leave the paragraph
  alone when it works. Don't replace phrasing because "I would have
  written it this way" — voice is load-bearing.
- **Topic sentence first; headings name the specific subject.**
  "The phenomenon" → "Sponsorship bias in registered polls".
- **Vary sentence length within paragraphs.** Three 18–24-word
  sentences in a row is the strongest 2026 AI tell. After a long
  sentence, write a short one.
- **Negative parallelism is a ChatGPT tell.** *It is not X, it is Y*
  / *Not just X but Y* → state the positive directly.
- **Causal verbs only for causal designs.** *Cause, drive, induce,
  reduce, increase, affect* claim causality. For OLS/descriptive:
  *associate, predict, accompany, are linked to*.
- **Don't hedge in the main sentence.** Caveat goes in a footnote or
  follow-up.
- **`[ws]` Literature paragraph ties to OUR contribution** — not a
  roll-call. Tie each named tradition back to the contribution in
  the same sentence.
- **`[ws]` Referee reports = ASCII only** (no em/en-dashes, curly
  quotes, ellipsis, bullets) — prose under `~/Dropbox/referee/`.
- **Define every acronym on first use** (OLS, IV, FE, TSE). Acronyms
  used only twice should be expanded inline.
- **Prefer deletion to rewriting.** Most common Claude failure:
  *adding* — setup sentences, transitions, explanatory clauses.

---

*Sections below cover the rest in detail (posture, voice, sentences,
words, paragraphs, tables, citations, italics, writing-process
stages, per-section guides). Available via `Read` of this file at
`/workspace/research-kit/rules/writing_style_judgment.md`.*

## Posture

**Keep it simple and clear.** Plain words, short sentences, direct
claims. If a sentence runs more than two clauses or starts to need
re-reading, split it. If a paragraph reads fine when you delete a
sentence, delete it.

**Don't dress up the paper.** Most authors assume the opposite: less
math is usually better; simpler estimation is usually better; fewer
technical flourishes leave the contribution clearer.

## Voice and tense

- **First person.** "We show", "I find", "we exploit" — not "the paper
  finds", "it is shown".
- **Active unless the actor is genuinely irrelevant.** Institutional
  content where the actor doesn't matter ("cases are randomly assigned
  to judges") is the carve-out. When you write a passive, ask whether
  you've dropped the actor by habit.
- **Present tense within paragraphs.** Don't start in past and finish
  in future. *Table 5 shows…*, not *Table 5 will show…*.

## Sentences

- **"Where" vs "in which".** "Where" refers to a place; "in which" to
  a model or framework. *models in which consumers have uninsured
  shocks*, not *models where consumers have uninsured shocks*.
- **Don't bury the verb.** Subject and main verb stay close.

## Words

- **Technical terms used precisely.** Don't gloss with a synonym
  (monotonicity, 2SLS, LATE); gloss with intuition if needed.
- **No author-coined compounds without an immediate plain-English
  gloss.** "We construct the first large-scale dataset of
  mechanism-labeled procurement corruption" — bad. "…of
  procurement-corruption cases classified by mechanism" — good.
- **Tri-colon lists only when there are exactly three things.** Don't
  manufacture them for cadence.
- **Foreign-language terms — introduce once, prefer English
  thereafter.** `câmara` (courtroom) on first use; *courtroom* after.
  Carve-out: institutional roles with no English equivalent
  (`relator`). Linter catches hybrids like `comarca-level`.
- **Internal-workflow language stays out.** Analysis-ledger
  identifiers (`AN-098`), code names, temporary variables, build-stage
  names (`assemble layer`, `intermediate layer`), TODO references —
  all belong in scripts and project docs, not the paper.

## Paragraph structure

- **One idea per paragraph.**
- **State institutional details, sample definitions, and
  data-construction facts once.** Cross-reference rather than
  re-explain.
- **Question-then-answer.** Pose the question explicitly, then answer.

## Specifics over generalities

- **Cite numbers from the data, not vague qualifiers.** "65 percent
  less likely" beats "substantially less likely".
- **Name the example.** "São Paulo Appeal Court", not "a state
  appellate court".

## Hedging and caveats

- **If it's important, put it in the text; if it's not important,
  delete it (Cochrane).** Footnotes are not a place for parenthetical
  comments — those usually mean you haven't figured out where the
  thought belongs in the linear sequence. Use footnotes only for
  content the typical reader can skip: reference lists, side algebra,
  technical caveats some readers will want attached to the current
  point.

## Tables and figures

- **Self-contained captions.** A skimming reader should understand
  the table or figure without reading the body. Define every symbol;
  spell out variable names; state what each column shows. Captions
  and table notes are paper prose — the same rules apply (define
  acronyms, no pipeline-internal variable names like `cpf_proc`,
  describe restrictions in words not symbols).
- **Every number is discussed.** No number appears in a table that
  isn't discussed in the text. "Table 5 shows summary statistics"
  alone is not enough.
- **Sensible units.** "2.3 percent" is more readable than "0.0000023";
  use percentages, levels in millions where they make the number
  human-scaled.

## Citations

- **Order multi-cite parentheticals by year, not alphabetically.**
  `(Ferraz and Finan, 2011; Avis et al., 2018; Bobonis et al., 2022)`.
  Within a year, alphabetize.
- **Don't abbreviate author names.** "FF show that size matters" →
  "Fama and French show that size matters" (Cochrane).

## Italics

Use only for: terms being defined on first use, foreign-language
terms on first use, emphasis (rarely). Bullets only when content is
genuinely a list (steps, items in a typology) — default to prose.

## Connectives

Sparingly: **Thus**, **Furthermore**, **Moreover**, **However**, **In
contrast**, **Importantly**, **Note that**. Don't double them up
("Furthermore, moreover…" → one). The linter catches paragraph-opener
density; mid-sentence overuse is your call.

## Writing-process stages (Shapiro)

- **Aspirational intro** — early-stage thinking tool only. Make up
  the results; ask if you'd be excited about the paper that would
  deliver them. Does not survive into anything external.
- **Robot body** — linear, no forward references, no fancy talk,
  formal where the math is correct.
- **Contractual intro** — required for anything external. Rewrite the
  intro as a contract: the reader agrees to be excited provided the
  paper delivers what the intro promises.

By the time the paper goes anywhere external — conference, NBER
working paper, journal submission, even coauthors not in the
formulation — the intro must be contractual.

## Per-section guides (load on demand)

After getting the section's `type` from `section_deps.json[slug].type`
(or guessing from the LaTeX label per `section_labels.md`), read
`research-kit/rules/writing_style/<type>.md` for type-specific
structure (abstract opener, intro five-element formula, body
triangular structure, etc.).

## Sources

Full rules live in:
- `research-kit/rules/writing_style.md` — baseline (Cochrane, Shapiro,
  Head, Beatty & Shimshack)
- `research/rules/writing_style.md` — workspace overlay
- `research-kit/rules/writing_style/<type>.md` — per-section guides
