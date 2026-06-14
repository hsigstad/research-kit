"""Canonical `example_value` helper for project `source/summary/compute.py`.

Returns one sampled non-null value from a column, truncated for display
in the column-info table on dataset pages. Deterministic given the seed.

## How to integrate

After pasting the snippet below into compute.py, change the columns
list-builder to attach `example` to each per-column dict:

    columns = [{
        "name": c,
        "dtype": str(df[c].dtype),
        "null_count": int(df[c].isna().sum()),
        "null_pct": round(df[c].isna().mean() * 100, 1),
        "example": example_value(df[c]),
    } for c in df.columns]

The dataset.html column-info table reads `c.example` and renders it
into a new "Example" column. The HTML edit is one extra `<th>` in the
header and one extra `<td>` per row.

## The canonical definition

(Copy from `# ──── BEGIN ────` to `# ──── END ────`, paste in compute.py.)
"""

# ──── BEGIN example_value snippet ────

import pandas as pd  # noqa: F401 — provided by compute.py.


def example_value(s: pd.Series, max_len: int = 60, seed: int = 42) -> str:
    """Return a sampled non-null value from `s`, truncated to `max_len` chars.

    Deterministic given `seed` and the underlying series — random across
    columns but stable across builds of the same data. Returns "<all NA>"
    when the column has no non-null values.

    Truncation appends an ellipsis ("…") inside `max_len` so the
    rendered cell never exceeds the requested width.
    """
    non_na = s.dropna()
    if non_na.empty:
        return "<all NA>"
    v = non_na.sample(n=1, random_state=seed).iloc[0]
    text = str(v)
    if len(text) > max_len:
        text = text[: max_len - 1].rstrip() + "…"
    return text

# ──── END example_value snippet ────
