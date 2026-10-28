# Empirical Economics Writing Style

Conventions for clear, publishable prose in empirical economics. Applies to
papers, project documentation, working drafts, slides, and external
communication. Intended as a baseline that a Claude session (or a human
author) can follow to produce prose that reads as ordinary published-paper
style.

Projects may layer additional context-specific rules on top of this baseline
(e.g., a journal-specific style sheet, a referee-report typography rule,
or a coauthor-specific voice override).

---

## 1. Core principle

**Keep it simple and clear.** Plain words, short sentences, direct claims.
Technical terms used precisely; nothing else dressed up.

If a sentence runs more than two clauses or starts to need re-reading, split
it. If a noun phrase has three adjectives, drop two. If a paragraph reads
fine when you delete a sentence, delete it.

**Don't dress up the paper.** Counter-tendency worth surfacing because
most authors assume the opposite: less math is usually better; simpler
estimation is usually better; fewer technical flourishes leave the
contribution clearer. "Most students think they have to dress up a paper
to look impressive. The exact opposite is true" (Cochrane). If a simpler
model or estimator does the job, use it; if a layer of formalism can be
dropped without losing meaning, drop it.

---

## 2. Voice and tense

- **First person.** Use "I find" / "we show" / "I exploit" — not "it was
  found" / "it is shown" / "the paper finds". "We" for co-authored work;
  "I" for solo.
- **Prefer active voice.** Active reads more directly than passive: "we
  assigned cases to judges" beats "cases were assigned to judges by us";
  "the algorithm classifies decisions" beats "decisions are classified by
  the algorithm". Passive is sometimes necessary in academic writing —
  institutional or definitional content where the actor is irrelevant
  ("cases are randomly assigned to judges" — by the court, not the
  author; "the estimator is defined as..."), or when the object is the
  natural topic of the paragraph. When you write a passive, ask whether
  the actor is genuinely irrelevant or you've dropped them by habit.
- **State methods actively; don't give the estimator agency.** Write "we
  compare treated and control municipalities" / "we cluster standard
  errors by municipality", not "the fixed effect compares…" or a bare
  "standard errors cluster by municipality". The researcher performs the
  method; the estimator is not an actor.
- Direct claims, not aspirations. "We show that X" — not "this paper aims to
  show", "this study seeks to investigate", "we attempt to estimate".
- No throat-clearing meta-talk. Don't write "the contribution of this paper
  is to ...", "this is a descriptive paper:", "in this study, we will
  discuss". Just make the contribution.
- **Don't editorialize the data.** Don't tell the reader how to feel about
  the evidence. State the finding, cite the number, let the reader judge
  strength. Words to avoid as filler about your own results: *starkest*,
  *most compelling*, *remarkable*, *striking*, *notable*. Phrases to avoid:
  *the temporal evidence is starkest*, *most compelling is the result that*,
  *strikingly, we find*. Compare:
  - Editorializing: "The temporal evidence is starkest."
  - Direct: "We find evidence consistent with corruption migrating across
    margins as oversight tightened."
- **Don't address or stage-manage the reader.** Cut "A reader may worry
  that…", "One might think…", "Note that the reader…", "As the reader
  will see…". Put the concern in the paper's own impersonal voice and
  answer it ("One concern with this design is X. We address it by Y."),
  or just make the point directly.

## 3. Sentences

**Prefer short.** Shorter sentences ease reading. Longer sentences are
fine when they improve flow or when the content genuinely requires them —
but the default is short, and when you write a long one, ask whether it
splits cleanly into two without losing meaning. Vary length deliberately
for rhythm; don't write all short sentences either.

**Vary sentence length within paragraphs.** Cadence uniformity — three
or four 18-to-24-word sentences in a row — is the strongest 2026 AI
tell, and the one that survives surface-level rewriting. After a long
sentence, write a short one. After two clauses, write one. Read the
paragraph aloud: if every sentence has the same shape, restructure.

**When revising, prefer deletion to rewriting.** The most common
failure mode in Claude-drafted prose is *adding* — extra setup
sentences, explanatory clauses, "by elimination" framings, "across the
spec ladder" summaries, transition lines that restate the previous
paragraph. When a coauthor flags a sentence as too long or too
complicated, the right move is usually to delete a clause or the whole
sentence, not to rewrite it. Ask first: "does the paragraph still work
if I cut this?" — and if yes, cut.

**Unpack dense sentences.** Break a chain of appositives into separate
sentences — split, don't reword. Lift a dense embedded list out into its
own framed sentence. Recast one long qualified clause as two short
parallel sentences: "When the goal is prediction… But when the goal is
deterrence…".

**Don't repeat a distinctive key verb in adjacent sentences.** Vary a
weight-bearing content verb — *drives*, *produces* — across adjacent
sentences; reusing it reads as a tic. Ordinary verbs (*is*, *show*,
*find*) are exempt.

- At most two subordinate clauses. Three-clause stacks get split.
- Em-dashes are fine — used as parenthetical inserts, to introduce examples,
  or to gloss a term.
- Semicolons: use sparingly. The clear case for one is separating list
  items that themselves contain commas, where comma-only punctuation would
  be ambiguous; many authors avoid the clause-join entirely, and a project
  overlay may restrict semicolons further (the workspace overlay near-bans
  them).
- Don't bury the verb. Subject and main verb stay close.
- **"Where" vs "in which".** "Where" refers to a place; "in which" to a
  model or framework. Write *models in which consumers have uninsured
  shocks*, not *models where consumers have uninsured shocks* (Cochrane).
- **Tense consistency within paragraphs.** Don't start a paragraph in
  past tense and finish in future. Present tense is usually best,
  including for your own results: *Table 5 shows…*, not *Table 5 will
  show…*.

Example:

> I find that monotonicity is frequently violated. The share of nonunanimous
> cases violating monotonicity is 35 percent in the São Paulo Appeal Court,
> 49 percent in the Brazilian Superior Court, and 42 percent in the US
> Supreme Court.

Two sentences. The first states the finding; the second backs it with three
specific numbers. No hedging, no setup.

## 4. Words

**Prefer:**

| Plain                  | Over                                |
|------------------------|-------------------------------------|
| show                   | demonstrate                         |
| find                   | uncover, reveal, illustrate         |
| use                    | leverage, employ, utilize           |
| study                  | investigate, examine, explore       |
| test                   | interrogate, probe                  |
| affect / change        | impact (as a verb)                  |
| because                | due to the fact that                |
| but                    | however (as a sentence opener; ok mid-sentence) |
| also                   | additionally, moreover (sparingly)  |
| about                  | with respect to, concerning         |
| many / several / often | a multitude of, numerous, frequently |
| help                   | facilitate                          |
| let                    | enable, allow (when "let" fits)     |

**Technical terms** are different — use them precisely and don't paraphrase
when the term is the right name (`monotonicity`, `2SLS`, `LATE`,
`regression discontinuity`, `assemble layer`, `fixed effects`). Don't gloss
with a synonym; gloss with intuition if needed.

**Avoid author-coined compounds without an immediate plain-English gloss.**
If you invent a hyphenated technical term to describe what you're doing
("mechanism-labeled corruption", "validated large-language-model pipeline"),
either define it inline on first use in plain English, or replace with a
self-explanatory phrase. Coined compounds in an abstract or intro slow the
reader: they have to decode the term before they can read on. Compare:

- Coined, undefined: "We construct the first large-scale dataset of
  mechanism-labeled procurement corruption."
- Replaced with self-explanatory phrasing: "We construct the first
  large-scale dataset of procurement-corruption cases classified by
  mechanism."

**One term (and one symbol) per concept.** Pick one word for a construct
and use it throughout: *imprisonment* (not alternating with
*incarceration*); *reversal* (not also *crossing* and
*monotonicity-violation*); *case* (not also *vignette*). The same for
notation — don't reuse one symbol for two quantities: if `w` denotes
weights, write `n_{ij}` for the count, not `w` again.

**Reserve a word with precise technical meaning for that meaning.** If a
word names a specific metric or estimand, don't spend it loosely.
"accurate" is the literal accuracy metric — say "as good as a judge"
when you mean valid-enough, not "accurate". Keep "gap" for the estimand
and "bias" for the phenomenon; don't let them drift into each other.

**Name the standard a relative or evaluative word is measured against.**
A comparative needs its baseline stated. "optimal" → say what it
maximizes; "more-favorable / less-favorable states" → "states more
favorable to the worker's claim". Leaving the standard implicit makes
the reader guess the yardstick.

**Gloss specialized field terms on first use.** Domain vocabulary opaque
to a general reader gets a plain gloss the first time: *custody* →
"custody (unsuspended plus suspended prison)"; *clawback* → "a pay
clawback". Conversely, drop a specialist method-label where the plain
term carries the meaning: "95% Wilson confidence intervals" → "95%
confidence intervals", unless the Wilson construction is load-bearing.

**Avoid (AI-tell vocabulary):** delve into, leverage, navigate (as buzzword),
underscore, robust (as filler), comprehensive, multifaceted, paradigm,
seamless, pivotal, intricate, holistic, dynamic landscape, in today's
world, it is important to note that, it's worth mentioning that. Also:
crucial, vital, particularly suitable, highly competitive, substantial
(as filler), severe (as filler intensifier), sizeable, one of the most
X in the world, a testament to, "the takeaway:" (as paragraph opener).
These are the 2026-vintage promotional words that read as AI-drafted
scene-setting.

**Watch present-participle tail clauses (soft; not linted).** Sentences
ending in `…, providing / ensuring / reflecting / emphasizing /
highlighting / showcasing / fostering / underscoring / contributing to /
reinforcing X` can read as an AI cadence, and a true *dangling* participle
(where the tail's implied subject isn't the sentence's subject) is worth
fixing — recast as purpose (`to highlight…`) or a separate sentence. But a
clean summary tail (`…, reinforcing the conclusion that…`) is fine. This is
a judgment call, not an enforced rule (the `participle-tail` linter check
was retired 2026-10-28); don't flag these mechanically.

**No negative parallelism.** `It is not X, it is Y` and `Not just X but
Y` are now widely recognised as ChatGPT's signature rhetorical move.
State the positive claim directly. If the contrast genuinely matters,
two sentences are clearer than one balanced one.

**No stacked adjectives.** "A clean, well-identified, flexible design" → pick
one. "A flexible design" or "a well-identified design".

**No tri-colon lists everywhere.** Three-item lists are fine when there are
exactly three things. Don't manufacture them for cadence.

**No figurative or idiomatic phrasing.** State it literally. "makes the
case" → say what the exhibit shows; "fan out" → "vary across about 40
percentage points"; "within its reach" → the plain relation; "reach the
bias" / "check the bias" → "punish the bias". Figurative verbs and idioms
force the reader to translate; the literal statement is shorter and exact.

**Describe the behavior, not the plot geometry.** Say what the pattern
means, not what the line looks like. "the line is flat" → "the models
essentially do not respond to occupation"; "grant rates fan out" →
"grant rates vary across about 40 percentage points". The reader cares
about the behavior the figure encodes, not its shape.

**Clothe the naked "this".** Bare "This shows…" / "This implies…" leaves
the antecedent ambiguous, especially when the prior sentence has multiple
candidate referents. Always say "This *regression* shows…" / "This *rule*
implies…" / "This *finding* suggests…" — name what *this* refers to. The
fix is one extra word and removes a recurring source of reader confusion.

**Don't open a sentence with a bare "This" or an escalation connector.**
Beyond clothing the antecedent: don't *open* a sentence with a
content-free "This inverts…" / "This helps:…" — lead with the subject or
mechanism ("Because we never observe true conduct, …"). And don't open
with escalation adverbs — "Worse,", "Crucially,", "Strikingly," — which
editorialize before the content arrives.

**Translate code language into prose.** The data-engineering vocabulary
we use in scripts and design docs — `cell`, `within-cell`, `grain`,
`bucket`, `join`, `grid`, `panel grid` — should not appear in published
prose. State the level of observation, comparison, and fixed effects
directly. *Within-cell variation* → *variation within race × week*;
*candidacy grain* → *one observation per candidacy*; *we join X to Y*
→ *we link X to Y* or *we merge X with Y*. The reader is not reading
the SConstruct. The same rule applies to inline pseudocode: a
parenthetical like `(matched share = 1)` or `(treated = 1)` is code,
not prose — state the condition in words ("polls where every candidate
matched", "the treated cohort").

**Reserve causal verbs for causal designs.** Words like *cause, effect,
impact, drive, induce, penalize, lead to* claim a causal relationship.
Use them only when the design identifies causality (RD, IV, RCT, a
credible DID). For OLS associations, descriptive correlations, and
conditional means, use neutral language: *associate, correlate with,
predict, accompany, coincide with, are linked to*. Compare:

- Causal: "Pre-filing convictions reduce vote share by 8 points."
- Descriptive: "Pre-filing convictions are associated with an 8-point
  lower vote share."

**Don't refer to coefficients by Greek letter or estimator name in
prose.** Describe what the number measures, not how it was computed.
*Within-firm β* → *within-firm bias*; *β_c = β_a* → *equality of the
convicted and acquitted estimates*; *the within-candidate sponsor
coefficient is around +8 pp* → *sponsored polls overstate by about 8
percentage points*. Greek letters and estimator labels belong in tables
and the formal specification, not in narrative prose.

**Acronyms.** Define every acronym on first use, including the standard
ones (OLS, IV, FE, TSE). Acronyms that appear only once or twice in the
paper should be expanded inline and the abbreviation dropped — the
reader gains nothing from carrying an unfamiliar three-letter code that
saves five words across one paragraph.

**Keep internal workflow language out of prose.** Analysis-ledger
identifiers (`AN-098`), code names, temporary variables, debugging
notes, build-system stage names (`assemble layer`, `intermediate
layer`), and TODO references belong in scripts and project docs, not
in the paper. Replace with research-language descriptions of the
operation, the variable, or the design choice. This includes **internal
repository paths** (`pipelines/politica/source/llm/`,
`source/clean/parse.py`): never cite a repo path in the paper, in the
replication-materials prose, or in any doc a coauthor reads — name the
artifact by what it is ("the prompts and schema are in the replication
materials"), not by where it sits in our tree. The same applies to
**in-house shorthand and cross-paper dependencies**: don't compress a
quantity into private shorthand ("the quota share above five SM" → "the
share of respondents earning over five minimum wages"), and don't lean on
a companion or earlier paper's vocabulary, section labels, or table
numbers ("Own- and Cross-Weights (Q3)", "Table D.9"). The prose must be
self-contained.

## 5. Paragraph structure

- Topic sentence first. Don't make the reader work to find the point.
- **Topic sentences and section headings must name the specific
  subject.** Headings like *"The phenomenon"*, *"Brazilian context"*,
  or *"What to do about it?"* require the reader to remember the
  antecedent. Replace with specific labels: *"Sponsorship bias in
  registered polls"*, *"Brazilian electoral-poll regulation"*,
  *"Policy options to reduce poll bias"*. The cost is two more words;
  the gain is a skimmable structure where each heading earns its place
  in the table of contents. Prefer the action or question form —
  *"Testing for income-quota manipulation"*, *"Assessing the incentive
  properties"* — over a bare topic noun (*"Own- and Cross-Weights"*) or
  the method (*"Subsampling"*); name what the reader will learn, and if
  the title and the body disagree, fix one.
- **Don't lead an opener with the conclusion.** Paragraph and
  subsection openers should name the question or the object under
  discussion, not announce the answer the section is about to derive.
  "Capture is induced at production stages the registration system
  does not see" → start by naming what the section is asking ("This
  section asks where in the production chain the slant is induced"),
  then derive the answer in the body. Same for subsection openers
  like "The third lever is the only one currently operating in the
  data" — lead with the question the subsection answers, not the
  verdict. Leading with the conclusion robs the body of its work and
  trains the reader to stop reading after the opener.
- **Don't open a paragraph or subsection with the worry the test
  addresses.** "A natural worry is that ...", "A concern with this
  design is ...", "One might object that ..." — these put the alarm
  before the substance. State what the test does and what it finds;
  the reader will infer the worry from the choice to run the test.
  The exception is when the paper genuinely needs to acknowledge a
  limitation rather than dismiss a concern; in that case lead with
  the limitation and what cannot be ruled out, not with a rhetorical
  "natural worry".
- One idea per paragraph.
- **A separate topic gets its own heading; size a section to its
  weight.** When a buried paragraph turns to a genuinely separate topic,
  give it its own heading ("Beyond labor courts"). And the section
  carrying the key contribution should be long enough, and titled
  clearly enough, to signal that it is the center of the paper.
- **State institutional details, sample definitions, and data-construction
  facts once.** Cross-reference rather than re-explain. If the reader
  already learned in §3 that the sample is mayoral 1st-round candidates,
  do not restate the filter in §5 when discussing a robustness check —
  point at §3. The most common offender is the institutional setup
  paragraph that gets paraphrased every time it touches a new analysis.
- **Point to a given appendix section once.** Don't scatter repeated
  pointers to the same supplementary section across a short span.
  Consolidate them into one reference, placed at the end of the
  paragraph.
- Question-then-answer is a recurring pattern: pose the question explicitly,
  then answer.
- Formal + informal pairing for technical content: state the formal version,
  then a one-sentence intuition. Example:

  > **Assumption 3** (Average Conditional Monotonicity). For all s ∈ S,
  > E[P̃₁ | s(Z)=1] ≥ E[P̃₁ | s(Z)≠1].
  >
  > Informally, this requires that the partial effect of P₁ — instrument 1
  > — on treatment 1 is, on average, non-negative for each agent across
  > values of the instruments.

## 6. Specifics over generalities

- Cite numbers from the data, not vague qualifiers. "65 percent less likely"
  beats "substantially less likely".
- Name the example. "São Paulo Appeal Court", not "a state appellate court".
- **Genericize domain nouns in the general framing; keep the specific as
  the running example.** In the general claim, write "courts" or
  "decision-makers' rulings"; then introduce the labor court as the
  concrete example. This is the complement of "Name the example" — the
  general statement stays general, the illustration stays specific.
- **Foreign-language terms — introduce once, prefer English thereafter.**
  Gloss the term in parentheses on first use: `câmara` (courtroom),
  `comarca` (judicial district), `lista de antiguidade` (seniority list).
  After that, use the English equivalent in the rest of the paper. Keep
  the foreign term only when it names a specific institutional role
  the English gloss would mislabel (e.g., `relator` is the role of the
  judge who writes the lead opinion in Brazilian appellate panels —
  there is no clean English equivalent). Do not form hybrid expressions
  that combine the foreign term with English modifiers: write
  *judicial-district level*, not *comarca level*; *courtroom-level
  fixed effects*, not *câmara-level fixed effects*.

## 7. Hedging and caveats

- Don't hedge in the main sentence. State the claim; put the caveat in a
  footnote or a follow-up sentence.
- "We do not, however, detect a larger effect..." — fine, qualifies a
  specific finding.
- Inference-verbs that name the method ("the analyses suggest", "the
  evidence is consistent with", "the pattern points to") are fine when
  the conclusion rests on inference rather than direct observation.
  Distinguish from generic hedges ("perhaps", "it is possible that")
  which weaken claims without naming the inferential basis.
- "It is possible that..." opening a paragraph — usually weak; either show
  it's possible with evidence, or cut.
- Footnotes carry the technical caveats: standard-error clustering,
  alternative specifications, the "this is also true if..." asides.
- **"Ruled out" vs "not detected" vs "cannot be ruled out".** Pick
  the wording that matches the inferential reach of the test. *Ruled
  out* is a positive claim that something has been excluded — reserve
  it for cases where the test would have detected the effect if it
  were present (adequate power, the right design). *Not detected* is
  the right wording when a test came back null but the test's
  resolution doesn't license exclusion (small sample, low-frequency
  signal, observational data without a clean instrument). *Cannot be
  ruled out* is the right wording when the design is silent on a
  channel — the data simply doesn't speak to it. Example: "Crude
  per-candidate post-fielding tampering is *ruled out*" ⇒ "is *not
  detected*" if the digit-frequency test is observational; "pre-PDF
  tampering *would not be detected*" ⇒ "*cannot be ruled out*",
  because the design has no purchase on it.
- **Operational test for any softener.** Ask: *does removing it
  change what the reader knows?* If "perhaps" / "to some extent" /
  "arguably" drops out and the meaning is unchanged, it is a
  defensive hedge — delete it. If "the analyses suggest", "within
  candidate and within race-week", or "we do not detect a larger
  effect for X" drops out and the reader loses the inferential
  basis, scope, or data limit, the qualifier is doing work — keep
  it.
- **Don't editorialize method virtue.** Don't label your own procedure
  "without cherry-picking", "non-cherry-picked", "fully reproducible",
  "reproducibly", "principled", or "carefully". Describe what you did
  and let the description carry the credibility — "we rank cases by a
  hash of the case number and keep the lowest 200", not "we select the
  sample reproducibly and without cherry-picking". Same instinct as
  banning "frozen taxonomy": don't relabel a method with a virtue
  adjective, state the method.
- **Don't claim a guarantee the method can't give.** Verbs that assert
  certainty or perfect fidelity — *certify, prove, guarantee, ensure,
  reproduce* — usually overstate what a method delivers. An audit
  *tests* a property, it does not *certify* it; a model *reaches the
  judge's conclusion on 73% of cases*, it does not *reproduce the
  reasoning*; a model *could learn* a bias, it does not *inherit* or
  *absorb* it. This is the fidelity analogue of the causal-verb rule
  (§4).
- **State a tendency as a tendency, not an absolute.** "conditioning on
  type drives deterrence to zero" → "conditioning on type tends to
  weaken deterrence"; leave the limiting case to the following
  sentences. And don't assert "the" effect when several exist — write
  "typically" or "usually" and push the alternative to a footnote.
- **Don't overclaim data coverage.** "we observe everything the judge
  saw" → "the key documents the decision rests on". Don't claim
  "everything", and don't enumerate what is missing in the same breath —
  state what you do observe.

## 8. Signposting

- "In Section 2, we develop..." — fine and useful at the end of an intro.
- "In this paper, I show..." — fine to anchor the reader early.
- **Open a section/subsection with a substantive purpose sentence** — this
  is the preferred default, not merely tolerated: "In this section we
  estimate the rate at which two random judges agree" previews the estimand
  and orients the reader. The one thing to avoid is heading-restatement
  padding: "In this section we present our results" adds nothing over a
  "Results" heading and is cut. The line is content vs padding — name the
  question or estimand the section settles (fine); don't echo the title.
  Especially useful in technical / SI sections.
- **A preview must match what follows.** If a sentence says "what remains is to
  show X and Y", the next sections must be X then Y, in that order. Make the
  structure match the preview, or cut the preview — don't promise an order the
  paper doesn't keep.

## 9. Connectives

Use sparingly: **Thus**, **Furthermore**, **Moreover**, **However**,
**In contrast**, **Importantly**, **Note that**.

Don't open every paragraph with one. Don't double them up ("Furthermore,
moreover,..." → just one).

## 10. Formatting

- *Italics* only for: terms being defined on first use, foreign-language
  terms, emphasis (rarely).
- Bullet points only when the content is genuinely a list (steps, items in
  a typology). Default to prose.

### Citations

Order multi-cite parentheticals by year, not alphabetically:
`(Ferraz and Finan, 2011; Avis et al., 2018; Bobonis et al., 2022)`.
Within a year, alphabetize. The chronological reading lets the reader
see the literature accumulate; alphabetical scrambles that signal.

### Footnotes

The strong rule (Cochrane): if it's important, put it in the text; if
it's not important, delete it. Don't use footnotes for parenthetical
comments — those usually mean you haven't figured out where the thought
belongs in the linear sequence. Use footnotes only for content the
typical reader genuinely can skip: long lists of references, side
algebra, technical caveats some readers will want attached to the
current point. The same applies to parentheses — lots of parentheses are
just as bad as lots of footnotes.

Sampling and reproducibility mechanics are footnote material: hash-based
ordering, random seeds, and the exact post-attrition N belong in a
footnote hung on a plain main-text sentence. Main text: "we draw 200
random cases." Footnote: the hash rule, the seed, and the net count
after dropping incomplete records. Don't lead the main text with an
arbitrary-looking net N (e.g. 193) or the hashing details.

Formal definitions belong in a footnote too, with an informal gloss carrying
the idea in the body: say what a quantity means in words in the text, and hang
the formula and its boundary conditions (e.g. "balanced accuracy has a 50%
floor") on a footnote. The reader gets the idea inline and the precision on
demand.

### Tables and figures

- **Self-contained captions.** A skimming reader should understand the
  table or figure without reading the body. Define every symbol on a
  graph; spell out variable names; state what each column shows.
  *Captions and table notes are paper prose.* The same rules that apply
  to body prose apply here: define every acronym on first use in the
  table (don't assume it was defined in the text); never refer to
  pipeline-internal variable names (`cpf_proc`, `case-grain sample`);
  spell out what each column shows in plain English; describe parameter
  restrictions ("the test that the convicted and acquitted estimates
  are equal") rather than naming them by symbol ("P β_c = β_a"). A
  reader who turns straight to the tables should be able to follow them
  without consulting the body.
- **Every number is discussed.** No number appears in a table that is
  not discussed in the text. "Row 1 of Table 3 shows a u-shaped pattern"
  is fine; "Table 5 shows summary statistics" alone is not — if it's
  not worth writing about in the text, it's not worth being in the
  table.
- **2–3 significant digits.** A coefficient of 4.56783 with a standard
  error of 0.6789 should be 4.6 with a standard error of 0.7. Two to
  three digits are plenty for almost all econ applications.
- **Sensible units.** "2.3 percent" is more readable than "0.0000023";
  use percentages, levels in millions, etc., where they make the number
  human-scaled.
- **Spell out column headers; report rates as decimals.** Write "Balanced
  accuracy", not "Bal. acc."; define "N". Report rates, probabilities, and
  accuracies in decimal form (0.71) — always the `0.xx` form, not "71%" — and
  drop a redundant "(%)" when the column already carries the unit. (Treatment
  effects and differences stated in percentage points are a separate case; this
  is about reported rates and accuracies.)
- **Don't restate what the exhibit already shows.** Prose and caption
  should not duplicate the content of the table or figure — point to it
  and say what to take from it, don't transcribe its numbers back into
  words.
- **Choose a readable sign convention and direction label for a derived
  measure.** When a measure's sign is a modeling choice, orient it so
  the reader reads it naturally, and name its direction ("pro-poor
  skew") rather than leaving a bare signed number to be decoded.
- **Give a number-column group a spanning header.** Add a spanning
  `\cmidrule` column-group header that names what the number columns
  measure, so the reader sees what the block of figures is before
  reading any single column.
- **Captions describe; they do not interpret.** A caption states the
  sample, coding, units, and what a blank cell means — then stops. Keep
  interpretation ("the confidence intervals are wide", "underpowered",
  "rules out X") in the body, not the caption.

## 11. Typography

Default: follow standard style guides. Em-dashes, en-dashes, curly quotes,
ellipsis character — all fine where correct.

**On em-dashes specifically:** the published-econ baseline still allows
them, and LaTeX's `---` rendering is conventional. But mid-2026 readers
treat *high em-dash density* — em-dash substituting for commas, colons,
and parentheses across a paragraph — as a tell. The rule is per-paragraph:
at most one em-dash per paragraph; reserve it for the genuinely
parenthetical case where the comma or paren would lose structure. Where
a comma works, use a comma; where a colon works, use a colon.

**Use an em-dash, not a spaced en-dash.** For a parenthetical dash write
LaTeX's `---` — an em-dash with no surrounding spaces — not a spaced
en-dash ("Reports – a pollster…"). The spaced en-dash is a
word-processor substitution; the em-dash is the correct glyph.

**Avoid math symbols in prose.** Spell out the relationship: *district
× filing-year stratum* → *district-by-filing-year stratum* or *strata
defined by district and filing year*. Symbols (×, ÷, ≤, ≥, ⊆) belong
in equations and table headers, not in narrative sentences.

Context-specific exceptions may apply (e.g., referee reports often require
plain ASCII to avoid AI-detection cues). Authors should layer those
exceptions on top of this baseline; don't bake them into the general
style.

## 12. Drafts vs. finished prose

- Working drafts can use whatever formatting is convenient.
- Strip AI-tell phrasing as a final pass before anything leaves Claude for
  the author to keep.
- Apply context-specific typography rules in the same final pass.

**Editing a coauthor's draft: minimal intervention.** When the task is
revising prose that already exists — not drafting from scratch — prefer
small targeted edits over rewrites. Change a word when a word is wrong;
restructure a sentence when the sentence is broken; leave the paragraph
alone when it already works. The bar for replacing the author's
phrasing is a clear gain in accuracy, clarity, structure, or concision
— not "I would have written it this way". Voice is a load-bearing
property of a coauthored paper; do not flatten it.

## 13. Per-section guides

Section-type-specific rules live in [`writing_style/`](writing_style/),
one file per section type. Apply these on top of the general rules
above. Tools (`/style-review`, `/validate-section`) load the relevant
per-type file based on `section_deps.json[slug].type`; see
[`section_labels.md`](section_labels.md) for the LaTeX label convention
that drives the type resolution.

| Section type    | Guide                                                            |
|-----------------|------------------------------------------------------------------|
| Abstract        | [`writing_style/abstract.md`](writing_style/abstract.md)         |
| Introduction    | [`writing_style/intro.md`](writing_style/intro.md)               |
| Body (baseline) | [`writing_style/body.md`](writing_style/body.md)                 |
| Results         | [`writing_style/results.md`](writing_style/results.md)           |
| Methods         | [`writing_style/methods.md`](writing_style/methods.md)           |
| Theory          | [`writing_style/theory.md`](writing_style/theory.md)             |
| Data            | [`writing_style/data.md`](writing_style/data.md)                 |
| Institutions    | [`writing_style/institutions.md`](writing_style/institutions.md) |
| Discussion      | [`writing_style/discussion.md`](writing_style/discussion.md)     |
| Conclusion      | [`writing_style/conclusion.md`](writing_style/conclusion.md)     |
| Appendix        | [`writing_style/appendix.md`](writing_style/appendix.md)         |

Inheritance: body sections (results, methods, data, institutions,
discussion) inherit from `body.md` (triangular structure, etc.);
theory, abstract, intro, conclusion, and appendix inherit only from
this general baseline. See [`writing_style/README.md`](writing_style/README.md)
for the inheritance diagram.

## 14. Writing process

Jesse Shapiro's four-step process for producing an applied paper. The
process spans project formulation through first draft. **Stage matters**
— the aspirational step is for early formulation only; by submission,
only the contractual version of the intro should remain.

1. **Aspirational introduction (early-stage thinking tool).** Write the
   intro for the paper you *aspire* to write, before doing the work.
   Make up the results, within reason. Then ask: if I produce the paper
   outlined in this intro, will I be happy with it? If imaginary
   results don't excite you, real ones won't either. Iterate on the
   intro until it does. This step is for deciding whether the project
   is worth doing; the aspirational claims do not survive into anything
   externally shared.
2. **Research.** Do the work. Tackle the hardest, least-clear aspects
   first — the things most likely to prevent you from achieving your
   goals. Return to the aspirational intro frequently; it is your
   compass.
3. **Robot body.** Write the body of the paper as if you were writing
   it for a robot. State your assumptions, methods, and findings. Don't
   try to convince the robot you are right. Be linear (no forward
   references), clear (no undefined concepts), plain (no fancy talk),
   formal (mathematics is fine when correct). Gaps you find here send
   you back to step 2.
4. **Contractual introduction (required for any external version).**
   Rewrite the intro as a contract between you and the reader: the
   reader agrees to be excited about your paper, provided the paper
   delivers what the intro promises. If you find yourself wanting to
   claim things the paper doesn't deliver, return to steps 2–3.

**Stage discipline.** The aspirational intro is a thinking tool, not a
draft. By the time the paper goes anywhere external — a conference,
NBER working paper, journal submission, or even coauthors not involved
in the formulation — the intro must be contractual: every claim backed
by what the paper actually delivers. If you find yourself near a
deadline with an intro that promises more than the body delivers,
step 4 isn't done yet. Go back and tighten until they match.

When the paper delivers on a contract you are happy with, stop. That is
your first draft.

---

## Quick reference: things to delete on a final pass

- "It is worth noting that" / "It is important to note that" → cut entirely
  or rewrite the claim to stand on its own.
- "In order to" → "to".
- "Due to the fact that" → "because".
- "A wide variety of" / "a vast array of" → "many", or name them.
- "Arguably" / "perhaps" / "it could be argued" — usually cuttable.
- "Significantly" (when not statistical) — cut or replace with a number.
- Adjective stacks ("comprehensive, in-depth, rigorous analysis") — pick one.
- Synonym piling ("examine, investigate, and explore") — pick one verb.
- "This paper" / "this study" used three+ times — vary or drop.
- "We leave X for future research" — strike entirely; readers care about
  what's in the paper, not your follow-up agenda.
- Present-participle tail clauses ("…, providing X", "…, reflecting X",
  "…, reinforcing X") — fix only a true *dangling* participle; benign
  summary tails are fine (soft, not linted — see §4).
- Negative parallelism ("not X, but Y" / "it is not X, it is Y") —
  rewrite as a positive claim.
- Paragraphs of evenly long sentences — break one in half so the
  rhythm varies.
- Empty **"directly"** — "We test this directly" → "We test this".
- Filler **"also"** linking two independent findings — drop it; let the
  two findings stand.
- **Redundant apposition restating a quantifier** — "at least X%, a lower
  bound" → "at least X%" ("at least" already says lower bound).
- **Don't abbreviate author names.** "FF show that size matters" — spell
  out "Fama and French". (Cochrane)
- **"Illustrative test" / "illustrative empirical work" — strike.** Do
  real empirical work or don't do any at all (Cochrane).
- **Strive for precision.** Editing pass: read each sentence — does it
  say something, and does it mean what it says? (Cochrane)
- **Coding vocabulary in prose** (`cell`, `within-cell`, `grain`,
  `bucket`, `join`, `grid`) — rewrite in research language. State the
  level of observation and the comparison directly.
- **Internal workflow references** (`AN-098`, build-stage names,
  variable names from scripts, TODO references) — strip and describe
  the operation or design choice in prose.
- **Undefined acronyms** — define every acronym on first use, including
  OLS / IV / FE; drop any acronym that appears only once or twice.
- **Cite-list alphabetical order** — re-sort by year ascending.
- **Foreign-language hybrids** (`comarca level`, `vara-level`) — rewrite
  with the English equivalent or drop the modifier compound entirely.

---

## Sources

The rules above draw on four canonical guides to economics writing.
Vendored copies live in [`writing_style_refs/`](writing_style_refs/) so
the references resolve offline.

- **Keith Head, "The Introduction Formula"** —
  [`writing_style_refs/head_intro_formula.md`](writing_style_refs/head_intro_formula.md)
  ([original](https://blogs.ubc.ca/khead/research/research-advice/formula)).
  Source for the five-element intro formula in
  [`writing_style/intro.md`](writing_style/intro.md).
- **Jesse M. Shapiro, "Four Steps to an Applied Micro Paper" (2022)** —
  [`writing_style_refs/shapiro_foursteps_2022.pdf`](writing_style_refs/shapiro_foursteps_2022.pdf).
  Source for the 15-paragraph intro template in
  [`writing_style/intro.md`](writing_style/intro.md), the four-step
  writing process in §14, and the research-question criteria.
- **John H. Cochrane, "Writing Tips for Ph.D. Students" (2005)** —
  [`writing_style_refs/cochrane_writing_tips_2005.pdf`](writing_style_refs/cochrane_writing_tips_2005.pdf).
  Source for the triangular/newspaper structure in
  [`writing_style/body.md`](writing_style/body.md), footnote and
  table/figure rules in §10, "clothe the naked 'this'" in §4, and many
  small rules in the Quick reference.
- **Timothy Beatty & Jay P. Shimshack, "Practical Tips for Writing and
  Publishing Applied Economics Papers"** —
  [`writing_style_refs/beatty_shimshack_practical_tips.pdf`](writing_style_refs/beatty_shimshack_practical_tips.pdf).
  Background on the publication process and editor decision-making (most
  rejections happen at the abstract/intro stage — supporting the
  emphasis on the abstract and intro per-type guides).

Further suggested reading (not vendored): William Zinsser, *On Writing
Well*; Deirdre McCloskey, *Economical Writing*; William Thomson, *A Guide
for the Young Economist*; Marc F. Bellemare, *Doing Economics*.
