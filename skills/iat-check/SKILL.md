---
name: iat-check
description: "Audit Python scripts for compliance with the Inline Audit Trail (IAT) convention. Checks for missing INTENT, REASONING, ASSUMES, SOURCE comments and validation guards. Use when the user wants to check code documentation quality."
user_invocable: true
---

# IAT Compliance Check

Audit data transformation scripts for compliance with the Inline Audit Trail convention defined in `research/rules/inline_audit_trail.md`.

## Scope

By default, audit all `.py` files in the current project's `source/` directory. The user may specify a narrower scope (single file, specific directory).

IAT applies to **data transformation scripts** only. Skip:
- `diarios/` module code
- Configuration files, SCons build files
- LaTeX sources
- Notebook cells (unless they contain substantial pipeline code)
- Pure utility/helper modules that don't do data work

## What to check

For each script, evaluate these categories:

### 1. Stage documentation
- **Function pipelines (preferred style):** Do functions have docstrings when the name alone doesn't convey analytical rationale?
- **Script-style code:** Are there `# ---` section headers with preamble comments?
- A script that's organized as a clean `.pipe()` chain of well-named functions may need very few comments — that's fine.

### 2. INTENT comments
- Are analytically meaningful steps documented? Look for:
  - Sample construction / inclusion-exclusion rules
  - Classification logic
  - Non-obvious filters
- Do NOT flag obvious operations. If a function name like `keep_elected_candidates()` already conveys intent, no INTENT comment is needed.

### 3. REASONING / WHY comments
- Are design choices with plausible alternatives documented?
  - Join type choices (why left vs inner?)
  - Ordering of regex patterns
  - Choice of thresholds or parameters
- Institutional context that explains choices

### 4. ASSUMES comments
- Are hidden data properties documented? Look for:
  - Merge operations — what's the expected cardinality?
  - Uniqueness assumptions
  - Identifier normalization assumptions
  - Interpretation of missing values or failed matches

### 5. SOURCE comments
- Scripts reading raw data from external locations should have SOURCE comments
  - URL, format, encoding, delimiter
- NOT needed for `build/` artifacts from upstream pipeline code

### 6. Validation guards
- After joins: row-count preservation checks?
- Before merges: key uniqueness assertions?
- After recodes/classification: value domain checks?
- End of pipeline: final dataset contract validation?

## Output format

For each file, report:

```
## <filename>

**Overall:** [Good / Needs attention / Significant gaps]

### Missing or weak documentation
- Line X: <merge without ASSUMES comment — what cardinality is expected?>
- Line Y: <filter with non-obvious threshold — REASONING needed>
- Line Z: <raw data load without SOURCE>

### Missing validation guards
- Line X: <merge without row-count assertion>
- Line Y: <classification without value domain check>

### Good practices found
- <brief note on what's well-documented>
```

After all files, provide a summary count.

## Gotchas

- The IAT philosophy is **minimal, high-signal comments**. Do NOT flag missing comments on obvious code. The rule of thumb: "if deleting the comment would not remove information that a careful reader could not recover from the code, omit it."
- Well-named functions in a `.pipe()` chain are the preferred style. Don't penalize scripts for having few comments if the code is self-documenting.
- Over-commenting is also a problem. If you see comments that just restate what the code does, flag those too as "unnecessary comments that risk code-documentation drift."
- When suggesting fixes, give the actual comment text to add, not generic advice.
- Do NOT rewrite the file as part of this audit. Report findings only. The user decides what to fix.
