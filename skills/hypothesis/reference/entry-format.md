# /hypothesis — folder-mode entry format reference

The full folder-mode spec for `docs/hypotheses/`: index structure, the
per-hypothesis narrative-sectioned file template, the verdict-callout convention,
style notes, file naming, path conventions, and per-mode skill behavior. Read
this when creating or editing hypothesis entries (folder mode is the default).
SKILL.md carries the compact summary, template choice, and the mode procedures.

## Folder mode (`docs/hypotheses/`)

When the project has 15+ hypotheses or individual entries grow long
(accumulating evidence blocks, robustness notes, status updates),
promote to a folder:

```
docs/hypotheses/
  index.md           # intro + field schema + cluster index + summary table
  <slug>.md          # one file per hypothesis, named by slug field
```

### index.md structure

- Title and intro paragraph
- "How to read this document" field descriptions
- Cluster sections with brief descriptions and bulleted links to
  individual files: `- [H1: Headline](slug.md)`
- Cross-cluster notes (e.g., mechanisms taxonomy references)
- Summary table at the end

### Per-hypothesis file (`<slug>.md`) — narrative-sectioned format

Each per-hypothesis file is a self-contained mini-document. The reader
should be able to land here from anywhere and grasp the claim, the
verdict, and what's still open without ever opening another file.

```markdown
# H<N>: <Headline statement of the hypothesis>

<1-2 paragraph intro framing the question. State the mechanism in plain
prose, point to what would change in the data if the hypothesis is true,
and link to the theory framework that motivates it.>

> **Evidence strength: <verdict> by AN-<id> (<YYYY-MM-DD>).** <2-3
> sentences summarizing what the named analysis found and what it
> means for this hypothesis. Quote one headline number.>

## Theory

<Narrative paragraph: name the framework from theory.md, explain how it
implies this prediction, link to the theory.md anchor.>

## Prediction

<Narrative paragraph: the specific directional prediction, with the
empirical object that would carry the signal (coefficient on X, density
discontinuity, event-study step, etc.). Concrete enough that a reader
can imagine the table.>

## Competing prediction(s)

<One paragraph per rival explanation. Open each with **<short name>.**
in bold, then 2-3 sentences on what that alternative implies and how it
would differ in the data from the lead hypothesis. List 1-3 rivals; if
there's only one plausible alternative, name it.>

## Prior research

<Narrative paragraph(s) citing what's already known. Use the project's
citation conventions — `[cite:author-year]`, `[stories.csv #NNN]`,
`[institutions.md §N]`. Never cite from memory.>

## Evidence

| Analysis | Bearing | Key takeaway |
|----------|---------|--------------|
| AN-<id>  | Confirms / Refutes (placebo fails) / Mixed / Pending | <1-2 sentence finding with the headline number.> |

<Add one row per AN page that bears on this hypothesis. If none yet,
omit the table and write "No analyses yet — see Open tests below.">

## Open tests

### <Specific next test title>

<Paragraph: what variation would carry the test, why it's the natural
next step, what data is needed. Make each open test concrete enough
that it could become an AN page on the spot.>
```

**Verdict callout convention.** The `> **Evidence strength: …**`
blockquote opening with `Evidence strength` (or `Verdict` / `Status`)
is detected by sitekit's `style_verdict_callouts` and auto-styled as a
colored card. Keywords that drive the color:

- **Refuted** (any form) → red
- **Strong / Confirmed / Supported / Very strong** → green
- **Mixed / Partial / Moderate / Weak** → yellow
- **Not tested / Pending / First descriptive** → gray
- everything else → neutral blue

Order matters in the classifier: "Refuted" wins over "strong" if both
appear, so "Strong evidence of refutation" still reads as refuted.
Write the lead clause to make the bucket unambiguous.

**Style notes.**

- Lead with the verdict callout right after the intro — it's the first
  thing a reader scans. If the hypothesis is untested, write
  `> **Evidence strength: Not tested.** <one-sentence reason or
  blocking dependency>.`
- Use full sentences, not bullet lists. The reader is looking for an
  argument, not a form. Bullets are fine inside a section when
  enumerating items (e.g., listing data sources), but the section
  bodies themselves are prose.
- AN references in the Evidence table should use the bare AN id
  (`AN-019`); sitekit auto-links them.
- Cross-refs to other hypotheses use `[H<N>](other-slug.md)`.
- Keep the file under ~150 lines. If it grows beyond that, the
  hypothesis is probably actually two — split it.

### File naming

Use the **Slug** field as the filename (e.g., `plaintiff-awards.md`).
No numeric prefixes — ordering lives in `index.md`, not filenames.

### Path conventions

Since files live at `docs/hypotheses/<slug>.md`:
- Theory: `[theory.md](../theory.md)`
- Mechanisms: `[mechanisms.md](../reference/mechanisms.md)`
- Build artifacts: `[stem.csv](../../build/table/stem.csv)`
- Cross-refs between hypotheses: `[H<N>](other-slug.md)`

### Skill behavior in folder mode

- `/hypothesis` (populate): creates `index.md` + one file per hypothesis.
- `/hypothesis --update <slug>`: edits only `docs/hypotheses/<slug>.md`.
- `/hypothesis --extend`: appends new files and adds entries to index.
- `/hypothesis --audit`: checks each file for schema compliance and
  verifies index links resolve.
