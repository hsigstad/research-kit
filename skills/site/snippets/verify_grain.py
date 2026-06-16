"""Canonical `verify_grain` helper for project `source/summary/compute.py`.

When a dataset declares its grain (the columns that uniquely identify
each row) via a `key_columns: list[str]` field on `DatasetConfig`,
verify_grain checks that the contract holds and emits a `grain_check`
block in the cache JSON. The dataset page renders the result as a
green ✓ badge when grain is unique, or a red ✗ badge with the
duplicate / null-key counts when it isn't.

The point is end-to-end data quality observable on the page itself:
if a future change to the assemble script silently breaks grain, the
data-page badge flips red on the next cache rebuild — no separate
ledger entry, no test failure that goes unread.

## How to integrate

Add a `key_columns` field to `DatasetConfig`:

    @dataclass
    class DatasetConfig:
        ...
        key_columns: list[str] | None = None

Set it on the assembled-table entries that have a declared grain:

    DatasetConfig(
        id="cand_poll",
        ...,
        key_columns=["protocol", "politico_id"],
    )

In compute_stats, after loading `df`:

    grain_check = verify_grain(df, config.key_columns)

Add `"grain_check": grain_check` to the returned dict.

In templates/dataset.html, the grain-check JS block reads
`DATA.grain_check` and renders a colored badge. Paired template
snippet: grain_check_badge.html.

## The canonical definition

(Copy from `# ──── BEGIN ────` to `# ──── END ────`, paste in compute.py.)
"""

# ──── BEGIN verify_grain snippet ────

import pandas as pd  # noqa: F401 — provided by compute.py.


def verify_grain(df: pd.DataFrame, key_columns: list[str] | None) -> dict | None:
    """Check that `key_columns` is a unique key on `df`.

    Returns None if `key_columns` is empty / None (no contract to check).
    Otherwise returns a dict with the row / unique-key / duplicate-row /
    null-key counts and an `is_unique` flag. Missing columns short-
    circuit to an `error` field.
    """
    if not key_columns:
        return None
    cols = list(key_columns)
    missing = [c for c in cols if c not in df.columns]
    if missing:
        return {"key_columns": cols, "error": f"columns not in dataframe: {missing}"}
    keys = df[cols]
    n_rows = int(len(df))
    n_null_keys = int(keys.isna().any(axis=1).sum())
    n_unique_keys = int(keys.drop_duplicates().shape[0])
    n_duplicate_rows = n_rows - n_unique_keys
    return {
        "key_columns": cols,
        "n_rows": n_rows,
        "n_unique_keys": n_unique_keys,
        "n_duplicate_rows": n_duplicate_rows,
        "n_null_keys": n_null_keys,
        "is_unique": n_duplicate_rows == 0 and n_null_keys == 0,
    }

# ──── END verify_grain snippet ────
