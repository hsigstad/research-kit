"""Empirical archetype: data sources, dataset/source pages, descriptives, tables.

Initial scope: thin stub that delegates back to project hooks. Full port of
fisc's machinery (build_dataset_page, build_source_page, descriptives,
tables, source-script pages, binary detection, grain checks, pseudocode)
lands in a follow-up — the pilot is serasa, which doesn't exercise this.

When the fisc migration happens, expand this module to subsume what's
currently in fisc/source/site/build_all.py + the /site skill snippets dir.
"""

from __future__ import annotations

from ..context import BuildContext


def run_empirical(
    ctx: BuildContext,
    docs_info: list[dict],
    subdir_info: list[dict],
) -> dict:
    """Empirical-archetype build steps (TODO: port from fisc)."""
    return {}
