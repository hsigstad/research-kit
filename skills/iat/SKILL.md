---
name: iat
description: "Audit Python scripts for compliance with the Inline Audit Trail (IAT) convention — INTENT, REASONING, ASSUMES, SOURCE comments and validation guards — AND propose the comment text to add. LLM-driven, judgment-heavy, slower than /check. Use when the user invokes /iat, /iat <script>, /iat <slug>, or asks to 'check IAT compliance', 'audit comments in source/', 'add missing IAT comments'."
disable-model-invocation: true
---

# /iat — Inline Audit Trail compliance check (with proposed comments)

Audits data-transformation scripts against the Inline Audit Trail
convention defined in `research-kit/rules/inline_audit_trail.md`, and
proposes the exact comment text to add for every weak spot. Judgment-heavy
and slower than `/check` — that's why it lives as its own skill.

The default behavior is *propose, don't edit*. The skill emits the
suggested comment text with the line number; the researcher pastes it in.
IAT comments are subtle and benefit from a human read before they land.

## How to invoke

| Form | What it does |
|------|--------------|
| `/iat` | Audit all `source/**.py` in the current project |
| `/iat <script>` | Audit one script |
| `/iat <slug>` | Audit a specific project by slug |
| `/iat --no-suggestions` | Report only — no proposed comment text |

## Scope

By default, audit all `.py` files in `source/`. IAT applies to **data
transformation scripts** only. Skip:

- `diarios/` module code (shared library, separate convention).
- Configuration files, SCons build files.
- LaTeX sources.
- Notebook cells unless they contain substantial pipeline code.
- Pure utility/helper modules that don't do data work.
- Underscore-prefixed scripts (`_foo_check.py`) — exploratory; opted out.

## What to check

For each script, evaluate these six categories. Be **conservative**: only
flag what would genuinely surprise a careful reader who didn't write the
code. Over-commenting is also a problem.

### 1. Stage documentation

- **Function pipelines (preferred style):** functions have docstrings when
  the name alone doesn't convey analytical rationale.
- **Script-style code:** `# ---` section headers with preamble comments
  delimit logical stages.
- A clean `.pipe()` chain of well-named functions may need very few
  comments — that's fine. Don't penalize self-documenting code.

### 2. INTENT comments

Analytically meaningful steps should be documented:

- Sample construction / inclusion-exclusion rules.
- Classification logic.
- Non-obvious filters.

Don't flag obvious operations. If `keep_elected_candidates()` already
conveys intent, no INTENT comment is needed.

### 3. REASONING / WHY comments

Design choices with plausible alternatives should be documented:

- Join type choices (why left vs inner?).
- Ordering of regex patterns.
- Thresholds and parameter choices.
- Institutional context that explains the choice.

### 4. ASSUMES comments

Hidden data properties should be documented:

- Merge operations — expected cardinality?
- Uniqueness assumptions on keys.
- Identifier normalization assumptions.
- Interpretation of missing values or failed matches.

### 5. SOURCE comments

Scripts reading raw data from external locations should have a SOURCE
comment with URL, format, encoding, delimiter. NOT needed for `build/`
artifacts produced upstream by other pipeline code.

### 6. Validation guards

- After joins: row-count preservation assertions?
- Before merges: key uniqueness assertions?
- After recodes/classification: value domain checks?
- End of pipeline: final dataset contract validation?

## Propose comments

For each finding, emit the suggested comment text with the line number.
Format:

```
## <filename>

**Overall:** [Good / Needs attention / Significant gaps]

### Missing or weak documentation

- Line 47 (merge without ASSUMES):
  Add above the merge:
  # ASSUMES: each `cnpj_raiz` appears once in `firms` (one_to_one), zero or more in `establishments` (one_to_many).

- Line 113 (non-obvious filter without REASONING):
  Add above the filter:
  # REASONING: dropping inscrições filed before 2010 — the parser misclassifies
  # older format identifiers as nulls (see decisions.md 2024-08-12).

### Good practices found

- <one line on what's well-documented, when worth surfacing>
```

After all files, a one-line summary count.

## Output

Plain prose (markdown). No JSON mode — IAT findings are inherently
judgment calls that don't roundtrip well as machine data.

## Guardrails

- **Never edit files.** The skill reports and proposes; the researcher
  pastes the comments in themselves. This is deliberate — IAT comments
  are subtle and benefit from a read-and-edit pass before they land.
- **Be specific.** Propose the actual comment text, not generic advice.
  "Add an ASSUMES comment" is useless; "Add `# ASSUMES: one row per
  (cnpj, year) — enforced by upstream parser`" is useful.
- **Don't over-flag.** Don't suggest comments on obvious operations. If
  the function name already conveys intent, leave it alone.
- **Flag over-commenting too.** Comments that just restate the code are
  worse than no comments — they rot. Surface those as removal candidates.
- **Trust the reader.** A clean `.pipe()` chain of well-named functions
  doesn't need INTENT comments at every step.

## When to run

- After writing a new script (`/next` step 3 produces a script and hands
  off to `/iat` for the IAT pass).
- During the line-by-line review of critical-path scripts (see
  `$ROOT/research-kit/meta/ai_research_workflow.md` stage 5).
- After a refactor that changed merge semantics or filter logic — the
  ASSUMES/REASONING comments may have drifted out of sync.

## Related

- For doc-contract + source/build naming + ledger drift, use `/check`.
- For citation tokens, use `/check cite`. For manifest regeneration, `/cite-sync`.
- The IAT convention itself lives in
  `research-kit/rules/inline_audit_trail.md`.
