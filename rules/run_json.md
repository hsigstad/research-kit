# `.run.json` — per-artifact run provenance

Each scripted output in `build/table/` and `build/figure/` should be
accompanied by a sibling `.run.json` sidecar recording the script
that produced it, the git commit at run time, the parameters used,
and the date.

Reference implementation: `research-kit/tools/run_json.py`.
Reverse-index schema: `research-kit/rules/artifacts_yaml.md`.

## Why

`docs/reference/artifacts.yaml` indexes **which docs cite each
artifact** (path-level). The `.run.json` sidecar records **which
version of which script with which parameters produced the
artifact** (per-run). Together they let you answer:

- "After this re-run, which findings might have drifted?"
  → `artifacts.yaml` (which docs cite this path).
- "Was the cited number produced from the post-fix script or the
  pre-fix one?"
  → `.run.json` (commit at run time).
- "Did the run that wrote this CSV use the v0a or the v0b spec?"
  → `.run.json` (`params`).

Without the sidecar, you reconstruct provenance from `git log` of
the script *plus* mtime of the artifact, and pray the working tree
wasn't dirty when the run happened. With it, the metadata is
attached to the artifact.

## Schema (version 1)

```json
{
  "schema_version": 1,
  "script": "source/table/h4_pgfn_filtering_break.py",
  "outputs": [
    "build/table/h4_pgfn_cohort_annual.csv",
    "build/table/h4_pgfn_cohort_annual.md",
    "build/table/h4_pgfn_cohort_annual.tex"
  ],
  "commit": "f311796718425ee1603e4e0c874ec93298ea2646",
  "commit_dirty": false,
  "ran_at": "2026-05-08T16:09:07+02:00",
  "params": {
    "snapshot": "pgfn_2026_trimestre_01",
    "cohort_year_min": 2012,
    "cohort_year_max": 2022
  },
  "python": "3.11.5",
  "host": "fox"
}
```

### Fields

- **`schema_version`** — bump when the schema changes incompatibly.
- **`script`** — path to the producing script, relative to project root.
- **`outputs`** — paths the same run wrote, relative to project root.
  All outputs of a single invocation share the same payload; one
  sidecar per output is written.
- **`commit`** — `git rev-parse HEAD` at run time, or `null` if not in
  a git repo / git unavailable.
- **`commit_dirty`** — `true` if `git status --porcelain` returned any
  output at run time; `null` if undetermined. **A dirty tree means
  the `commit` field does not fully describe the source.** Treat
  results from dirty runs as provisional.
- **`ran_at`** — ISO 8601, local timezone, seconds resolution.
- **`params`** — caller-provided dict (argparse Namespace, mapping,
  or anything with `__dict__`). Serialized best-effort: Path → str,
  set → sorted list, unknown → repr().
- **`python`** — interpreter version. Catches `"this script broke
  because it ran under 3.12 instead of 3.11"`.
- **`host`** — `platform.node()`. Useful when scripts run on multiple
  machines (laptop vs server).
- **extra** — callers may add additional top-level keys via the
  `extra=` parameter for run-specific context: upstream dataset
  hash, RAIS vintage, LLM model id, etc.

## Sidecar location

For artifact `build/table/X.csv`, the sidecar is
`build/table/X.csv.run.json` — suffix **appended**, not replaced.
Rationale: `ls build/table/X.csv*` shows both files together; a glob
on `*.csv` doesn't pick up the sidecar; the discoverable path is
deterministic regardless of the artifact's extension.

For multi-format triples (`X.csv` + `X.md` + `X.tex`), three
identical sidecars are written (`X.csv.run.json`,
`X.md.run.json`, `X.tex.run.json`). Each artifact carries its own
provenance — simpler than a single sidecar that consumers would have
to look up by stripping a suffix.

## Integration

### In analysis scripts

One-line call at end of `__main__`:

```python
from source._run_json import write_run_json

if __name__ == "__main__":
    args = parse_args()
    df = compute(args)

    out_csv = BUILD / "table" / "h4_pgfn_cohort_annual.csv"
    out_md  = BUILD / "table" / "h4_pgfn_cohort_annual.md"
    out_tex = BUILD / "table" / "h4_pgfn_cohort_annual.tex"

    df.to_csv(out_csv, index=False)
    df.to_markdown(out_md, index=False)
    df.to_latex(out_tex, index=False)

    write_run_json([out_csv, out_md, out_tex], params=vars(args))
```

The helper auto-detects the script path (`__main__.__file__`) and
the git state. Pass `script=__file__` only to override.

For figures, same pattern with the .pdf/.png output paths.

### In `/findings --refresh`

The refresh skill should walk `artifacts.yaml`, and for each entry:

1. Read the artifact's `.run.json`.
2. Compare `commit` to the script's current HEAD. If they differ,
   the artifact is stale relative to the script.
3. Compare `ran_at` to the artifact's mtime. If they're far apart,
   the artifact may have been touched outside the build pipeline.
4. Read the artifact and recompute headline numbers cited in docs;
   flag drift.

### In `/findings --audit`

Audit checks specific to sidecars:

- Artifact present without `.run.json` → flag as "untracked
  provenance" (script may predate the convention or skip the helper).
- `.run.json` present whose `script` field points at a missing or
  renamed file → flag as "stale provenance".
- `commit_dirty: true` on an artifact cited from `key-findings.md` →
  flag for re-run from clean.

## Gitignore policy

`.run.json` files belong in git alongside their artifacts. With
`build/table/` and `build/figure/` tracked by default (per
`project_docs_contract.md`), they sync automatically.

For projects where `build/` is fully gitignored (none currently, but
older projects may be), add `!build/**/*.run.json` to keep
provenance tracked even when the data isn't.

## What it does NOT replace

- **IAT comments** in the script docstring — the *intent* and
  *reasoning* live in the source; the sidecar records the *run*.
  Both are needed.
- **`@claim` registry** for inline numbers — operates at the
  number-token level, not the artifact level.
- **`artifacts.yaml`** — records which docs cite the artifact;
  `.run.json` records how the artifact was produced. Complementary.

## Rollout

For an existing project:

1. Copy `research-kit/tools/run_json.py` into the project as
   `source/_run_json.py` (or `source/_helpers/run_json.py` if the
   project uses a helpers package).
2. Add `from source._run_json import write_run_json` and the
   one-line call to each `source/{table,figure}/*.py` `__main__`.
   No need to backfill historical artifacts — sidecars accumulate
   as scripts re-run.
3. (Optional) gitignore exception if `build/` is fully ignored:
   `!build/**/*.run.json`.

Backfill is unnecessary because the sidecar's value is forward-
looking: it makes the *next* re-run's provenance recoverable. The
first time a script writes its sidecar is when the provenance
becomes available; before that, fall back to `git log` + mtime.
