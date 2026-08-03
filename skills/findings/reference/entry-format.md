# /findings — document & entry format reference

The full formatting spec for `docs/findings`: document structure (folder and
legacy flat modes), the confidence-tag scheme, the per-entry schema, the headline
rule, the Sources footer, and folder-mode details (path conventions, naming,
migration, validation badge). Read this when drafting, extending, or updating
entries. SKILL.md carries the compact summary and the mode procedures.

## Document structure

**Default: folder mode** (`docs/findings/`, one file per finding). It matches the
canonical `project_docs_contract.md` §5 and the sibling `docs/hypotheses/` layout, and
is what nearly every project uses. Create it for new projects regardless of entry
count. The flat-file mode below is **legacy**: keep maintaining existing flat
`docs/findings.md` files, but do not create new ones — migrate them to a folder when
convenient (see "Migrating from flat to folder").

### Flat-file mode (`docs/findings.md`) — legacy

Required sections (in order):

```markdown
# Findings — <project topic>

<one-paragraph explanation of what this document is and isn't>

This page is the **directory of conclusions**. The companion page
[stylized-facts.md] is the **evidence ledger**. Use this page to scan
what we believe; use that page to look up the raw numbers.

---

## How to read the confidence tags

<confidence-tag scheme — see "Confidence-tag scheme" below; copy verbatim>

---

## Findings overview

<scannable index of every claim with anchored headline links, grouped by
theme: empirical vs interpretive, plus optional sub-themes>

---

## Empirical findings — detail

### <Finding headline 1>

<entry body — see "Entry schema" below>

### <Finding headline 2>

...

---

## Interpretations — detail

<bullet preamble: "The bullets below go beyond pure description — they
are readings of the evidence. Each names the empirical findings it draws
on, so a reader can challenge the inference without challenging the
underlying data.">

### <Interpretation headline 1>

...
```

### Folder mode (`docs/findings/`) — the default

Use one file per finding — this is the default layout for every project (see the
note above). See the "Folder mode" section below for the full specification. The
`index.md` carries the overview and links; each `<slug>.md` carries one entry.

## Confidence-tag scheme (verbatim — copy into `## How to read the confidence tags`)

A traffic-light convention runs across both scales: 🟢 = strongest confidence, 🟡 = middle, 🔴 = weakest. The *meaning* of each color depends on whether the claim is empirical or interpretive.

**Empirical findings** — the color reflects the *source* of confidence, not the size of the effect:

- 🟢 **Replicated** — the finding appears in multiple independent samples or studies that agree in direction and rough magnitude.
- 🟡 **Single source** — one solid study, or one of our own runs, with no independent replication yet.
- 🔴 **Provisional** — one descriptive cut that is parser-dependent, sensitive to sample definition, or flagged with a known caveat. Read the qualifier before quoting.

**Interpretations** — parallel scheme:

- 🟢 **Strong** — multiple converging lines of evidence; alternatives have been considered and rejected.
- 🟡 **Plausible** — consistent with the evidence but other readings remain open.
- 🔴 **Speculative** — suggested by the data but unverified; flagged for follow-up rather than relied on.

## Entry schema

Every empirical finding and interpretation entry must contain, in this order:

1. **Confidence tag + headline sentence.** First non-blank line of the entry's body. Format: `🟢/🟡/🔴 <one declarative sentence stating the finding as a claim about the world, with the load-bearing number(s) and AN cite(s)>`. See "Headline rule" below — this is the most quoted line in the doc and the bar is high.
2. **Expanded explanation.** Plain prose, 1–4 paragraphs, with inline anchored citations (no bare `[CNJ-DIAG22 p.198]` — use `[CNJ-DIAG22 p.198](../../references/cnj/file.pdf#page=198)` instead).
3. **Optional sub-paragraphs** for updates, robustness, caveats — each prefixed with a bold header like `**Forward-look caveat (added YYYY-MM-DD).**` so the reader can date the addition.
4. **Optional figure embed** with italicized caption underneath.
5. **The Sources footer** — see "Sources footer" below. Required, standardized, four-class.
6. **Optional Draws-on / Cross-refs paragraph** if the entry is an interpretation. Lists the empirical findings the inference rests on, by anchor link.

## Headline rule

The 🟢/🟡/🔴 line directly under the title is the single most-quoted unit in the doc — it gets linked, screenshotted, and dropped into emails out of context. It has to stand on its own.

1. **One declarative sentence stating the finding as a claim about the world.** Lead with the conclusion. Not a setup sentence, not a meta-introduction.
2. **Self-contained.** A reader landing here from a deep link must be able to parse the sentence without looking at the title or surrounding text. Spell out what "the asymmetry" / "the settlement effect" / "the gap" actually refers to — whose, between what, in what direction. Project-specific terms must be unpacked or replaced.
3. **Flesh out the title, don't echo it.** The title is the same claim in headline form; the sentence adds the load-bearing numbers, units, and scope. If the sentence reads like the title plus a comma, it's wasted space.
4. **Ground load-bearing magnitudes in numbers + AN cites.** Not "substantial" or "large". Significance markers (`*`, `**`, `***`) attach to the numbers they qualify.
5. **No evidence-as-subject, no meta-predicate, no hedged lead.** Confidence comes from the colored dot, not the verb. Avoid:
   - *"The asymmetry is the strongest evidence for X…"* (evidence as subject)
   - *"Three findings converge: …"* / *"Two patterns suggest…"* (meta-predicate)
   - *"X suggests that…"* / *"…is consistent with…"* (hedged lead)
   State the claim, then say why in the explanatory paragraph.
6. **Hard ceiling: 40 words, one sentence.** If you can't fit it in 40 words, the claim is compound — split it, or move secondary clauses into the explanatory paragraph below.

The headline rule applies equally to empirical and interpretation entries. Interpretations are still claims about the world — they just rest on multiple empirical premises (named in the `Draws on:` paragraph).

**Failing headlines look like:**

- *"The settlement effect tripled after the 2017 labor reform."* → what settlement effect, of what on what?
- *"Three findings converge: …"* → meta-predicate; the reader has to assemble the claim.
- *"The inverse value gradient combined with the flat dose-response suggests…"* → evidence-as-subject + hedged lead.
- *"Recusal reform intended to extend recusal to colleagues. Instead, …"* → setup-then-claim; the first sentence carries no information.

**Passing headlines look like:**

- *"Connected-judge assignment moves plaintiff awards by 30–40% (AN-044) but leaves defendant outcomes unchanged across every connection type tested (AN-031) — an asymmetry that contingency-paid plaintiff lawyers vs fixed-wage defendant lawyers can produce, but implicit bias cannot."*
- *"Connected-judge assignment raised the probability of settlement by 2.3pp (ns) before the 2017 labor reform and 7.1pp\*\*\* after — the settlement channel of favoritism roughly tripled (AN-038)."*

## Sources footer (the standard schema)

Every entry's footer is structured into four bulleted classes. Missing classes appear as `*<class>*: none direct` rather than being omitted — explicit absence is informative.

```markdown
**Sources.**
- *Own analysis*: <build artifacts and scripts as clickable file paths>
- *Reports*: <aggregate-report citations with `#page=N` deep links>
- *News anchors*: <`texts/NNN.txt` links + anchor quote when load-bearing>
- *Cross-refs*: <stylized-facts §, briefs/, audits/, related findings>
- *Validation*: <verification status per backing script>   <!-- only when project has validation.yaml -->
```

Path conventions (when the doc lives at `docs/findings.md`):
- Build artifacts: `[`stem.csv`](../build/table/stem.csv)`
- Scripts: `[`stem.py`](../source/table/stem.py)`
- Reports with page: `[CNJ-DEF24 p.205](../references/cnj/justica_em_numeros_2024.pdf#page=205)`
- News texts: `[outlet YYYY-MM-DD (short topic)](../references/news/texts/NNN.txt)`
- Cross-refs to same-dir docs: `[stylized-facts §X](reference/stylized-facts.md#anchor)` or `[briefs/Y §Z](briefs/Y.md#anchor)`

**Analysis ledger.** Every project maintains an analysis ledger
(`docs/analyses/` with `AN-NNN` entries indexed in
`docs/reference/analysis-index.yaml`). Cite the ledger entry in
`*Own analysis*` — e.g. `AN-026` — rather than raw build artifacts.
The ledger entry is the canonical record: it links to the backing
script and holds the results table and interpretation. Bare `AN-NNN`
tokens auto-link on the rendered site.

The finding's headline number must match the AN page's `headline:`
frontmatter (or `## Results` body) at write time. If they disagree,
the AN page wins — finding entries cite the AN; they do not
re-derive the magnitude. Drift between the two is a `--refresh`
target.

For news anchors that carry a load-bearing quote, append the quote inline:
> [Folha 2026-03 (Cucolo, Pesquisa Patrimonial CNJ)](../references/news/texts/070.txt) — anchor: *"a execução de sentenças judiciais que determinam o pagamento de dívidas seja hoje um dos principais gargalos do Judiciário"*

## Folder mode (`docs/findings/`)

The default layout — one file per finding (used for every new project and by
nearly all existing ones):

```
docs/findings/
  index.md           # overview + confidence scheme + linked index + open items
  <slug>.md          # one file per finding
```

### When to use folder vs flat file

- **Folder** (`docs/findings/`): **the default.** One file per finding — per-finding
  pages on the site, cleaner diffs, and you can edit one entry without touching
  others. Use it for every new project and any project going forward, regardless of
  entry count (it matches `project_docs_contract.md` §5 and `docs/hypotheses/`).
- **Flat file** (`docs/findings.md`): **legacy only.** A few early projects still use
  it; migrate to a folder when convenient. Do not create new flat findings docs.

### index.md structure

```markdown
# Findings — <project topic>

<intro paragraph, same as flat-file mode>

---

## How to read the confidence tags

<confidence-tag scheme — identical to flat-file mode>

---

## Findings overview

**<Theme 1>** *(empirical)*

- 🟢 [Headline sentence](slug.md) — one-line summary
- 🟡 [Another headline](another-slug.md) — one-line summary

**Interpretations**

- 🟢 [Interpretation headline](interp-slug.md) — one-line summary
```

### Per-finding file structure (`<slug>.md`)

Each finding file is standalone:

```markdown
# <Finding headline>

🟡 <Confidence tag + headline sentence with the load-bearing number.>

<Expanded explanation, 1–4 paragraphs.>

**Sources.**
- *Own analysis*: ...
- *Reports*: ...
- *News anchors*: ...
- *Cross-refs*: ...
```

- Heading is `#` (top-level) since the file is standalone.
- Entry schema and Sources footer are identical to flat-file mode.
- For interpretations, include the `**Draws on:** [...]` paragraph
  linking to the empirical findings it depends on, using relative file
  links: `[headline](other-slug.md)`.

### Path conventions in folder mode

Since files live at `docs/findings/<slug>.md`:
- Build artifacts: `[`stem.csv`](../../build/table/stem.csv)`
- Scripts: `[`stem.py`](../../source/table/stem.py)`
- Reports with page: `[CNJ-DEF24 p.205](../../references/cnj/file.pdf#page=205)`
- News texts: `[outlet YYYY-MM-DD](../../references/news/texts/NNN.txt)`
- Sibling docs: `[stylized-facts §X](../reference/stylized-facts.md#anchor)`
- Cross-refs between findings: `[other headline](other-slug.md)`

### File naming

- Slugs are lowercase, hyphens only, ≤40 characters.
- Derive from the heading: "Most exfis do not recover the debt" →
  `most-exfis-do-not-recover.md`.
- Avoid redundant prefixes like `finding-` — the directory provides context.

### Skill behavior in folder mode

- `/findings` (populate): creates `index.md` + one file per finding.
- `/findings --update <slug>`: edits only `docs/findings/<slug>.md` — the
  minimal-read-set is the same as flat-file `--update` mode.
- `/findings --extend`: appends new files and adds entries to
  `index.md`'s overview.
- `/findings --refresh`: walks all `docs/findings/*.md` files, compares
  numbers to build artifacts, reports drift per file.
- `/findings --audit`: checks each file for schema compliance and
  verifies `index.md` links resolve.
- `/findings --footer <slug>`: operates on one file.

### Migrating from flat to folder

When a flat `docs/findings.md` crosses ~20 entries:

1. Create `docs/findings/` directory.
2. Extract `index.md` (intro + confidence scheme + overview + open items).
3. Extract each `### ` entry into `<slug>.md`, promoting heading to `#`.
4. Rewrite overview links from `#anchor` to `slug.md`.
5. Fix relative paths (`../build/` → `../../build/`, etc.).
6. Delete the original `docs/findings.md`.
7. Update `artifacts.yaml` cited_in paths if the project has one.

### Validation badge (only when project has a validation ledger)

The *Validation* line renders per-script status from
`docs/validation.yaml` (or legacy `paper/validation.yaml`). Skip the
line entirely if neither location exists — the project hasn't opted
into the ledger. Schema: `research-kit/meta/validation_ledger.md`.

Format — one line per backing script cited in *Own analysis*:

```markdown
- *Validation*:
  - `h4_pgfn_filtering_break.py` — 🛡 ai-verified (2026-05-08, hash f311796)
  - `h4_cross_exequente_did.py` — ⏳ pending
  - `cnpj_firm_descriptives.py` — ⚠ stale (hash drift since 2026-04-29 sign-off)
```

Status glyph vocabulary (matches `validation.yaml::status`):

- 🛡 **`ai-verified`** — at least one AI check recorded; required-method floor met.
- ✅ **`human-verified`** — human reviewer signed off; hash matches reviewed bytes.
- ⏳ **`pending`** — row exists but no checks have run yet.
- ⚠ **`stale`** — script hash (or closure hash) has drifted since the recorded check date.

**Don't fabricate.** If a backing script isn't in `validation.yaml`,
omit it from the *Validation* block rather than guessing. Missing
script in the ledger means /next step 5d didn't add it, which is
itself a flag — log it in the entry's body, not as a fake validation
status.

**Confidence tag vs validation status are different axes** —
*confidence* (🟢/🟡/🔴) is about source robustness (replicated vs
single-source vs provisional); *validation* (🛡/✅/⏳/⚠) is about
verification of the analysis code. A finding can be 🟢 single-source
ai-verified, 🟡 single-source pending, or 🟢 replicated stale —
all meaningful.
