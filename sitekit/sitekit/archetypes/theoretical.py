"""Theoretical archetype: cases, briefs, multi-tex paper builder.

Initial scope: thin stub. Full port of bind's machinery (cases discovery,
build_case_page, build_cases_index, briefs, holdings.tex, citation-notes
pages) lands when bind is migrated. The pilot is serasa, which doesn't
exercise this.
"""

from __future__ import annotations

from ..context import BuildContext


def run_theoretical(
    ctx: BuildContext,
    docs_info: list[dict],
    subdir_info: list[dict],
) -> dict:
    """Theoretical-archetype build steps (TODO: port from bind)."""
    return {}
