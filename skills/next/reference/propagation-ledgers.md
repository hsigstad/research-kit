# /next — propagation ledger maintenance (5c, 5d)

Loaded during step 5 propagation **only if the project has opted into** an
`artifacts.yaml` registry and/or a `validation.yaml` ledger. If neither file
exists, skip both — the project hasn't opted in.

## 5c. `artifacts.yaml` maintenance

If the run produced a new artifact (not already in
`docs/reference/artifacts.yaml`), append an entry:

- `path`, `script`, one-line `description` (from the IAT title),
  `cited_in` (the docs you edited in 5a and 5b), and `tags`.
- If the run modified an existing artifact's set of citing docs, update
  the entry's `cited_in` list.

Schema: `research-kit/rules/artifacts_yaml.md`.

## 5d. `validation.yaml` row (if the project has a validation ledger)

If `docs/validation.yaml` (or legacy `paper/validation.yaml`) exists,
the project has opted into the formal validation ledger
(`research-kit/meta/validation_ledger.md`). When a `/next` iteration
produces a new script (one not already in the ledger), append a
`pending` row:

```yaml
- script: source/analysis/<new-script>.py
  layer: <inferred from path>     # e.g. analysis_<topic>, figure_<topic>
  produces: build/table/<new-script>.csv
  depends_on: []                   # filled in by /validate-section later
  hash: null                       # filled in at validation time
  closure_hash: null               # filled in at validation time
  ai_checks: []
  human_check: null
  reviewer: null
  status: pending
```

The bare minimum is `script`, `produces`, `status: pending`. Hash and
closure_hash get populated when `/validate-section` actually runs on
the script. `depends_on` is filled in by `/validate-section` step 2.

For runs that **re-use an existing script** (no new script, just a
re-run with different params): do **not** add a new row. If the
existing row was `ai-verified` or `human-verified`, the re-run *may*
have invalidated those checks — check `commit_dirty` and
`commit != ledger.hash` from the artifact's `.run.json`, and if so
flip the row's `status` to `stale`.

Do not promote rows past `pending` from `/next`. Verification is
`/validate-section`'s responsibility.
