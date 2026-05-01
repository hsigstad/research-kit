# Writing style — per-section guides

Section-type-specific rules. Each file applies on top of
[`../writing_style.md`](../writing_style.md) (general baseline). Tools
(`/style-review`, `/validate-section`) resolve the relevant file from
`section_deps.json[slug].type`; see
[`../section_labels.md`](../section_labels.md) for the label convention.

## Files

- [`abstract.md`](abstract.md) — Abstracts and paper openings
- [`intro.md`](intro.md) — Introductions
- [`body.md`](body.md) — Body sections (baseline)
- [`results.md`](results.md) — Results / main findings
- [`methods.md`](methods.md) — Methods / identification / empirical strategy
- [`theory.md`](theory.md) — Theoretical model / framework
- [`data.md`](data.md) — Data sections
- [`institutions.md`](institutions.md) — Institutional / background sections
- [`discussion.md`](discussion.md) — Discussion / mechanisms / interpretation
- [`conclusion.md`](conclusion.md) — Conclusions
- [`appendix.md`](appendix.md) — Appendices

## Inheritance

```
writing_style.md  (general baseline — sentences, words, voice, paragraphs)
├── abstract.md
├── intro.md
├── body.md  (body baseline — triangular structure, get to result fast)
│   ├── results.md
│   ├── methods.md
│   ├── data.md
│   ├── institutions.md
│   └── discussion.md
├── theory.md  (inherits general only — formal+informal matters more
│              than triangular structure here)
├── conclusion.md
└── appendix.md
```

When validating a section, load: general baseline + the matching per-type
file + (if a body section) `body.md`. Theory sections skip body.md
because the structural rules differ.
