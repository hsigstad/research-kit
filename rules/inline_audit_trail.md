# Inline Audit Trail (IAT) Convention

Convention for documenting data transformation scripts in projects and pipelines.
Applies when writing or editing scripts that perform data work (cleaning,
joining, transforming, analysing). Does not apply to `diarios`, configuration
files, SCons build files, LaTeX sources, or notebook cells.

---

## Philosophy

Prefer self-documenting code: small functions with clear names, organised as
readable pipelines. Well-named functions and explicit merge parameters already
communicate most of what a reader needs.

Comments should only preserve information that a careful reader **cannot
reliably recover from the code itself** — analytical rationale, hidden data
assumptions, institutional context, and external provenance. If deleting a
comment would not remove information that the code, file paths, or function
names already provide, omit it.

Over-commenting creates maintenance burden and risks code–documentation drift,
where the comment says one thing and the code does another. When in doubt,
improve function names, variable names, or pipeline structure rather than
adding explanatory comments.

---

## Comment types

| # | Type | Format | When to use |
|---|------|--------|-------------|
| 1 | **Stage documentation** | Docstring (function pipelines) or block comment (`# ---` sections) | Every major stage of a pipeline |
| 2 | **Intent** | `# INTENT: ...` | Analytically meaningful steps where the *reason* is not obvious: sample construction, inclusion/exclusion rules, classification logic |
| 3 | **Reasoning** | `# REASONING: ...` or `# WHY: ...` | Design choices with plausible alternatives, or institutional context that explains the choice |
| 4 | **Assumption** | `# ASSUMES: ...` | Hidden data properties the code depends on: uniqueness, join cardinality, duplicate definitions, identifier normalisation, interpretation of missing matches |
| 5 | **Source** | `# SOURCE: ...` | Genuinely external inputs (raw data from `$DATA_DIR`, URLs, APIs). Not needed for `build/` artifacts produced by upstream pipeline code |
| 6 | **Validation guard** | `assert` or explicit check | After joins, filters, reshapes, and recodes where assumptions can fail silently |

Inline annotations (end-of-line `# ...`) are used freely for complex
expressions, regex patterns, and edge-case handling.

---

### Stage documentation

In function pipelines (preferred), comments belong in the **function
docstring** — only when the function name alone does not convey the analytical
rationale. The calling script stays lean; function names act as the semantic
pipeline stages.

```python
def attach_audit_data(df: pd.DataFrame, audits: pd.DataFrame) -> pd.DataFrame:
    """Attach TCE audit records to the municipality-year panel.

    REASONING: Left join because not all municipios are audited every year.
    Missing rows mean "not audited", not missing data.

    ASSUMES:
        - one row per municipio-year in both datasets
        - cod_municipio is the 7-digit IBGE code
    """
    out = df.merge(audits, on=["cod_municipio", "ano"], how="left")
    assert len(out) == len(df), "Audit merge changed row count; check join cardinality"
    return out


df = (
    load_tse_candidates(DATA_DIR)
    .pipe(keep_elected_candidates)
    .pipe(attach_audit_data, audits=audits)
    .pipe(normalise_candidate_ids)
    .pipe(validate_panel_structure)
)
```

Note the docstring has no `INTENT` — the function name and one-liner already
say what it does. Only `REASONING` (why left join) and `ASSUMES` (hidden data
properties) add information the code does not convey.

In script-style code, use `# ---` section headers with a preamble comment
instead (`# --- Load ---`, `# --- Transform ---`, etc.).

---

### Examples

```python
# INTENT: Keep only elected candidates because downstream analyses
# in deterrence and audit use only officeholders.
df = df.loc[df["cod_sit_tot_turno"].isin([1, 2, 3])]

# REASONING: Outcome regexes are ordered most-specific-first because
# map_regex returns the first match. "regular com ressalva" must
# precede "regular".
outcome_regexes = get_outcome_regexes()

# ASSUMES:
#   - one row per municipio-year in both datasets (panel structure)
#   - CPF values normalised to 11-digit zero-padded strings upstream
df = df.merge(tse, on=["cod_municipio", "ano"], how="inner")
```

Note: no `SOURCE` here because these inputs come from `build/`. A `SOURCE`
comment would be appropriate in a script that reads raw data from an external
location:

```python
# SOURCE: TSE candidate files (candidatos, 2014-2022)
# https://dadosabertos.tse.jus.br/dataset/candidatos-2022
# Latin-1, semicolon-delimited, one ZIP per election year
```

---

### Validation guards

Major pipeline stages should include lightweight checks when they rely on
assumptions that can fail silently. Place the assert inside the function,
close to the transformation it guards. Typical checks:

- **Row-count preservation** — after joins, filters, deduplications
- **Key uniqueness** — before merges that assume one-to-one or many-to-one
- **Nulls in critical fields** — after recodes, parsing, joins
- **Value domains** — after classification or mapping logic
- **Expected cardinality** — after joins that should not expand rows

Before writing output, also validate the final dataset contract (key
uniqueness, no nulls in critical columns, expected time range). This catches
anything that slipped through the stage-level guards.

Focus on analytically important invariants, not trivial facts. The goal is
to catch errors where they are introduced, not forty steps later.

---

## What NOT to comment

- What the code already says (restating a filter, describing that a regex is
  used when `str.extract()` is visible)
- Provenance of `build/` artifacts (the pipeline structure documents this)
- Obvious implementation choices (that pandas is reading a CSV, that a
  function returns a DataFrame)
- Imports, simple literals, boilerplate, print formatting

**Rule of thumb:** if deleting the comment would not remove information that
a careful reader could not recover from the code, omit it.

---

## Applying IAT to existing code

When editing an existing script, add documentation for the lines being touched
and their immediate context. Do not rewrite entire files solely to add
comments — that creates noisy diffs. New scripts follow IAT from the start.
