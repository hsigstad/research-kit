"""Archetype dispatch.

Each archetype is a callable(ctx, docs_info, subdir_info) -> dict that
performs archetype-specific build steps and returns a dict of values the
index builder may use (e.g. {"extra_cards": "..."}).
"""

from __future__ import annotations

from typing import Callable

from ..context import BuildContext

ArchetypeFn = Callable[[BuildContext, list[dict], list[dict]], dict]


def get_archetype(name: str) -> ArchetypeFn:
    if name == "empirical":
        from .empirical import run_empirical
        return run_empirical
    if name == "theoretical":
        from .theoretical import run_theoretical
        return run_theoretical
    if name in ("minimal", "mixed"):
        return _noop
    raise ValueError(f"unknown archetype: {name!r}")


def _noop(ctx: BuildContext, docs_info: list[dict], subdir_info: list[dict]) -> dict:
    return {}
