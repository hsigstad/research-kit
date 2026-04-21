# Paper Numeric Macros Convention

Convention for how numeric claims in a paper's prose reference their
source. Applies when writing or editing any paper draft where numbers
come from analysis scripts. Sits alongside the validation ledger
(`meta/validation_ledger.md`): the ledger tracks script-level
correctness, this rule closes the loop from the prose back to the code.

---

## Philosophy

A number in the paper should live in exactly one place — the analysis
script that computes it. The prose cites it by name, not by value.
When the pipeline reruns and the number shifts from 30.8% to 31.2%,
the paper updates automatically; no stale-figure bug, no tedious prose
sweep, no risk that a coauthor's edit reintroduces the old value.

The LaTeX-side mechanism is a single generated file of `\newcommand`
definitions. The site-side mechanism is a post-processor that adds
source-attribution tooltips to each rendered number in the HTML.
Together they answer two questions the reader might have: "what does
that number mean?" (the prose) and "where does it come from?"
(the tooltip).

---

## Scope

**Macroize** (the paper cites the macro, not the literal):

- Counts: sample sizes, N, number of rows, unique identifiers.
- Percentages and shares from the pipeline.
- Medians, means, maxes, minima, quartiles.
- Currency amounts computed from the data (UFESP, BRL).
- Any number that appears both in a table/figure and in the prose
  discussion of that table/figure.

**Keep as prose** (macros would overweight what's really a writing
choice):

- Narrative rounding: "nearly three years", "approximately R$9,000",
  "roughly a quarter". The author chose to round; forcing a macro
  would either strip the rounding or make it fragile.
- Hypothetical illustrations: "if a municipality had 50 contracts…".
- Institutional constants in framing prose: "the R$17,600 threshold"
  when quoted verbatim from legislation and not derived from the
  pipeline.
- Citation metadata: page numbers, publication years, author counts.
- Units in prose after a macro: "\PenMedianUFESP{}~UFESP" — the
  macro emits the number; "UFESP" stays in the text so unit renames
  don't require regenerating.

A thin rule of thumb: **if rerunning the pipeline with different
inputs should change this value, macroize it**. If the value is
editorial, leave it as prose.

---

## Mechanism

The files and the dataflow — described for procure's reference
implementation (`source/paper/numbers.py`,
`source/site/number_tooltips.py`). Other projects copy this layout.

1. `source/paper/numbers.py` reads `build/analysis/*.json` and emits:
   - `paper/numbers.tex` — a flat list of `\newcommand`
     definitions, one per macro. Included from the paper preamble via
     `\input{numbers}`.
   - `paper/numbers.json` — a sidecar recording, for each
     macro, its rendered value, its source label
     (`<script>.py → <json_path>`), and its semantic interpretation
     (a one-sentence description including the denominator, used by
     the validation skill to adjudicate prose-vs-semantics alignment
     without re-reading the source code).

2. The paper source uses `\MacroName{}` (the `{}` ensures correct
   spacing) wherever a structural number appears.

3. `bash build.sh site` (or equivalent) runs `numbers.py` before
   make4ht so the `.tex` is always fresh.

4. The site builder's HTML post-processor reads `numbers.json`, scans
   the compiled HTML, and wraps each rendered value with
   `<span class="v-num" title="<source>">value</span>`. The PDF
   build ignores the sidecar — tooltips are HTML-only.

---

## Adding a macro

When a new numeric claim enters the prose — whether you're writing a
new section or updating an old one:

1. **Locate the source.** Identify the script and JSON field the
   number comes from. If the number doesn't trace to a committed JSON
   output, pause: either update the script to emit it, or accept that
   the number stays as prose with a validation-ledger note that it
   can't be traced.

2. **Add the macro.** In `source/paper/numbers.py`, extend `_defs()`
   with a `(macro_name, formatted_value, source_label, interpretation)`
   4-tuple. Naming convention: TitleCase, grouped by theme prefix
   (e.g. `Enf*` for enforcement, `Pen*` for penalties, `Sus*` for
   sustained rates). Formatter choice (`_int`, `_pct`, `_brl`) depends
   on the number type; see the existing formatters for the exact
   output shape.

   The **interpretation** is a one-sentence semantic description
   answering "what does this number mean, and what's its base
   population?" Example:
   `"Share of sustained-irregularity processos (denominator = EnfNSustained) that received at least one monetary penalty."`
   Missing interpretations are tolerated for backward compatibility
   but prevent section-level validation: the `validate-section` skill
   treats a macro with `interpretation: null` as `pending` for the
   `interpretation_prose_alignment` check.

3. **Cite it in prose.** Replace the literal in `main.tex` with
   `\MacroName{}`. Keep units and narrative phrasing outside the
   macro.

4. **For the tooltip to scope correctly**, the section the macro
   appears in must have a `\label{sec:X}` and a corresponding entry
   in `ANCHOR_OVERRIDES` in `source/site/number_tooltips.py`. Adding
   a new labelled section requires one line there; existing sections
   are already mapped.

5. **Regenerate** with `python3 -m source.paper.numbers` to refresh
   `numbers.tex` and `numbers.json`. The site build will pick up the
   changes automatically.

---

## Naming

Macro names should describe the *quantity* so a reader skimming the
`.tex` can infer meaning without consulting `numbers.py`. Bad:
`\SectionSevenFourNumberThree`. Good: `\EnfLagOverallDays`,
`\PenRateDirecion`, `\SusIntencAlta`.

Theme prefixes (extend as the paper grows):

| Prefix  | Meaning                                     |
|---------|---------------------------------------------|
| `Enf*`  | Enforcement — counts, funnel, lag           |
| `Pen*`  | Penalties — amounts, rates, counts by tipo  |
| `Sus*`  | Sustained-rate statistics                   |
| `Lit*`  | Literature / institutional constants        |
| `Desc*` | Descriptive statistics                      |

Don't embed the *unit* in the macro name if it's better placed in
prose: `\EnfLagOverall` with "…days" after reads worse than
`\EnfLagOverallDays{}` with no unit in prose. We've used the
unit-in-name style throughout; stay consistent within a paper.

---

## When editing an existing paper

Check `source/paper/numbers.py` before replacing a literal: the macro
may already exist. The generated `paper/numbers.tex` is
human-readable — scan it if unsure.

If you change a number's underlying computation (different denominator,
different filter), remember that the macro name carries semantic
weight. Either rename the macro to reflect the new definition, or
leave the old macro untouched and add a second one — don't silently
redefine a macro to mean something different.

---

## Failure modes to avoid

- **Inlining a literal because "it's just one number"**: the whole
  point is uniformity. One exception breeds ten.
- **Macroizing a narrative rounding**: forces the prose to match the
  computation's precision, defeating the editorial choice.
- **Renaming a macro without updating the ledger-level attribution**:
  if `\PenRateBypass` becomes `\BypassPenaltyRate`, the validation
  ledger's `ai_checks` notes that reference it go stale.
- **Adding a macro without running the regenerator**: the paper builds
  with `\MacroName is undefined` and the error can be slow to notice
  if the missing macro only appears on a rarely-rendered page.
- **Assuming the tooltip post-processor will find your macro
  anywhere**: it scopes to the section the invocation appears in. A
  macro used in an un-`\label`led region won't get a tooltip.

---

## Relationship to other conventions

- **Build layers** (`rules/build_layers.md`): citation scripts in
  `source/paper/numbers/` must read *only* from the `build/assemble/`
  layer. That's what keeps them short enough to tooltip. If a number
  requires a column that's not in the assemble layer, add the column
  to the relevant assemble script — don't reach back into
  `build/clean/` from a citation script.
- **Validation ledger** (`meta/validation_ledger.md`): macros are
  complementary to the script-level ledger, and the macro's
  `interpretation` field is what makes prose-vs-code verification
  cleanly separable.
  - The **ledger** certifies that the script is correct (an AI check
    or a human review) and that its output hasn't drifted since
    review.
  - **`interpretation_code_alignment`** certifies that a macro's
    declared interpretation actually matches what the script
    computes at the referenced JSON path. Script-side check, once
    per macro definition.
  - **`interpretation_prose_alignment`** certifies that the prose
    around each macro invocation is consistent with the declared
    interpretation (denominator, direction, qualifier words, claim
    context). Section-side check, per section.
  - **Macros themselves** (via `macro_provenance`) certify that the
    rendered value in the PDF/HTML matches the source JSON field —
    purely mechanical.

  A number can be ledger-certified but still cited incorrectly in
  prose. A number can be macroized with a correct value but whose
  interpretation doesn't match what the script computes. A number
  can be correctly interpreted in the JSON but misquoted by prose.
  Three independent gates, one each.
