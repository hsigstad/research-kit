"""Canonical `detect_binary` helper for project `source/summary/compute.py`.

This file is the source of truth — when you change it here, port the
change into every project's compute.py (currently: ficha, fisc, saude,
procure, poll-sponsor-bias). The snippet below is meant to be pasted
near the top of each project's compute.py, alongside SAMPLE_ROWS /
SAMPLE_SEED / TOP_N.

It is also used by the data-page renderer in
`source/site/templates/dataset.html` via the `binary` block of the
cache JSON; pair this with `binary_chart_block.html`.

## How to integrate

After pasting the two definitions below into compute.py, change
`compute_stats` to:

1. Build a `binary` dict by iterating over every column of the
   dataframe and calling `detect_binary(df[c])`.
2. Skip binary-detected columns when building the `categorical` dict
   (avoid double display).
3. Add `"binary": binary` to the returned summary dict.

The site template's binary chart block reads `DATA.binary` and renders
itself only when at least one binary column is present.

## The canonical definitions

(Copy from `# ──── BEGIN ────` to `# ──── END ────`, paste in compute.py.)
"""

# ──── BEGIN detect_binary snippet ────

import pandas as pd  # noqa: F401  — provided by compute.py's own imports.

# String-encoded binaries. Each tuple = (set of allowed non-NA values, the
# label treated as "true" / 1). Order matters only for tie-breaking inside
# subsets; in practice these sets don't overlap.
BINARY_STRING_PAIRS: list[tuple[set[str], str]] = [
    ({"S", "N"}, "S"),
    ({"Y", "N"}, "Y"),
    ({"True", "False"}, "True"),
    ({"true", "false"}, "true"),
    ({"yes", "no"}, "yes"),
]


def detect_binary(s: pd.Series) -> dict | None:
    """If `s` is a binary column, return {mean, na_pct, true_label}; else None.

    Detected as binary:
    - bool dtype
    - integer dtype whose unique non-NA values are a subset of {0, 1}
    - object/string dtype whose unique non-NA values match one of
      BINARY_STRING_PAIRS (e.g. {"S","N"})

    `mean` is the share of "true" rows among non-NA rows; `na_pct` is the
    null share over the whole column.
    """
    if len(s) == 0:
        return None
    na_pct = round(s.isna().mean() * 100, 1)
    non_na = s.dropna()
    if non_na.empty:
        return None
    if pd.api.types.is_bool_dtype(s):
        mean = float(non_na.astype(int).mean())
        return {"mean": round(mean, 4), "na_pct": na_pct, "true_label": "True"}
    if pd.api.types.is_integer_dtype(s):
        unique = set(non_na.unique().tolist())
        if unique and unique.issubset({0, 1}):
            mean = float(non_na.astype(int).mean())
            return {"mean": round(mean, 4), "na_pct": na_pct, "true_label": "1"}
        return None
    if pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s):
        unique = set(non_na.astype(str).unique().tolist())
        for pair, pos in BINARY_STRING_PAIRS:
            if unique and unique.issubset(pair):
                mean = float((non_na.astype(str) == pos).mean())
                return {"mean": round(mean, 4), "na_pct": na_pct,
                        "true_label": pos}
    return None

# ──── END detect_binary snippet ────


# ──── BEGIN compute_stats integration sketch ────
#
# Inside `compute_stats(config)`, after loading `df`:
#
#     binary: dict[str, dict] = {}
#     for c in df.columns:
#         b = detect_binary(df[c])
#         if b is not None:
#             binary[c] = b
#
#     # Skip binaries when building the categorical block.
#     categorical = {}
#     for col in config.categorical_columns:
#         if col not in df.columns or col in binary:
#             continue
#         ...
#
# And in the returned dict:
#
#     return {
#         ...,
#         "columns": columns,
#         "binary": binary,
#         "categorical": categorical,
#         ...,
#     }
#
# ──── END compute_stats integration sketch ────
