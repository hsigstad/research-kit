"""
Per-artifact run-provenance sidecar.

When an analysis script writes `build/table/X.csv` (or any
`build/{table,figure}/X.*`), it should also emit a sibling
`build/table/X.run.json` carrying:

  {script, outputs, commit, commit_dirty, ran_at, params, python, host}

Together with `docs/reference/artifacts.yaml` (schema:
research-kit/rules/artifacts_yaml.md), the sidecar closes the
script ↔ doc provenance loop: given any tracked artifact, you can
recover the exact source commit, the parameters used, and the run
date — without bloating doc citations with version metadata.

Convention and rationale: research-kit/rules/run_json.md.

------------------------------------------------------------------
USAGE

Most callers want the one-line form at end of `__main__`:

    from source._run_json import write_run_json
    ...
    df.to_csv(out_csv, index=False)
    df.to_markdown(out_md, index=False)
    df.to_latex(out_tex, index=False)
    write_run_json([out_csv, out_md, out_tex], params=vars(args))

The helper writes one sidecar per output path. `script` and the git
state are detected automatically; pass `script=...` to override.

------------------------------------------------------------------
DISTRIBUTION

This module is a research-kit reference implementation. Copy it
verbatim into each project's `source/_run_json.py` and import from
there. Updates are rare; copy-paste is cheaper than the import-path
gymnastics needed to share across projects.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = 1


# ---------------------------------------------------------------------------
# Git inspection (best-effort — never crashes the script)
# ---------------------------------------------------------------------------


def _git(args: list[str], cwd: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
            timeout=2.0,
        )
        if out.returncode != 0:
            return None
        return out.stdout.strip() or None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def _project_root(start: Path) -> Path:
    """Walk up from `start` to the nearest dir containing .git or CLAUDE.md."""
    p = start.resolve()
    # Always start the walk from a directory.
    if p.is_file():
        p = p.parent
    for parent in [p, *p.parents]:
        if (parent / ".git").exists() or (parent / "CLAUDE.md").exists():
            return parent
    return p


def _git_commit(repo: Path) -> tuple[str | None, bool | None]:
    """Return (HEAD sha, dirty?). (None, None) if not a git repo."""
    sha = _git(["rev-parse", "HEAD"], repo)
    if sha is None:
        return (None, None)
    dirty_out = _git(["status", "--porcelain"], repo)
    dirty = bool(dirty_out) if dirty_out is not None else None
    return (sha, dirty)


# ---------------------------------------------------------------------------
# Params serialization
# ---------------------------------------------------------------------------


def _coerce_params(params: Any) -> dict[str, Any]:
    """
    Convert argparse.Namespace, dict, or arbitrary objects into a
    JSON-serializable dict. Path objects → str. Sets → sorted lists.
    Anything else falls back to repr().
    """
    if params is None:
        return {}
    if hasattr(params, "__dict__") and not isinstance(params, Mapping):
        params = vars(params)
    if not isinstance(params, Mapping):
        return {"_value": _json_safe(params)}
    return {str(k): _json_safe(v) for k, v in params.items()}


def _json_safe(v: Any) -> Any:
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, Path):
        return str(v)
    if isinstance(v, (list, tuple)):
        return [_json_safe(x) for x in v]
    if isinstance(v, set):
        return sorted(_json_safe(x) for x in v)
    if isinstance(v, Mapping):
        return {str(k): _json_safe(x) for k, x in v.items()}
    return repr(v)


# ---------------------------------------------------------------------------
# Caller detection
# ---------------------------------------------------------------------------


def _caller_script() -> Path | None:
    """Resolve the calling script's path. Returns None if undeterminable."""
    try:
        import __main__
        return Path(__main__.__file__).resolve()
    except (AttributeError, TypeError):
        pass
    # Fallback: scan the call stack for the first frame outside this module.
    import inspect
    here = Path(__file__).resolve()
    for frame in inspect.stack():
        fp = Path(frame.filename).resolve()
        if fp != here:
            return fp
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def write_run_json(
    outputs: Iterable[str | Path],
    *,
    params: Any = None,
    script: str | Path | None = None,
    extra: Mapping[str, Any] | None = None,
) -> list[Path]:
    """
    Write a `.run.json` sidecar next to each output.

    Parameters
    ----------
    outputs
        Paths to artifacts the script just produced. One sidecar is written
        per output, alongside it: `build/table/X.csv` →
        `build/table/X.csv.run.json`. (Yes, the suffix is appended, not
        replaced — keeps the sidecar discoverable by glob alongside its
        exact-extension partner.)
    params
        argparse.Namespace, dict, or any object with `__dict__`. Serialized
        best-effort; Path objects become strings, sets become sorted lists,
        unknown objects fall back to repr().
    script
        Override for the calling script path. Auto-detected from
        `__main__.__file__` if omitted.
    extra
        Optional dict merged into the top-level JSON. Use sparingly — for
        run-specific context that doesn't fit the standard fields (e.g.
        upstream dataset hash, RAIS vintage, LLM model id).

    Returns
    -------
    list[Path]
        The sidecar paths written.
    """
    script_path = Path(script) if script else _caller_script()
    if script_path is None:
        # Last resort — fail gracefully rather than crashing the script.
        sys.stderr.write(
            "write_run_json: could not determine script path; "
            "pass script=__file__ explicitly\n"
        )
        return []

    script_path = script_path.resolve()
    repo = _project_root(script_path)
    commit, dirty = _git_commit(repo)

    out_paths = [Path(o).resolve() for o in outputs]
    rel_outputs = [_relative_to(p, repo) for p in out_paths]
    rel_script = _relative_to(script_path, repo)

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "script": rel_script,
        "outputs": rel_outputs,
        "commit": commit,
        "commit_dirty": dirty,
        "ran_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "params": _coerce_params(params),
        "python": platform.python_version(),
        "host": platform.node() or None,
    }
    if extra:
        for k, v in extra.items():
            payload.setdefault(k, _json_safe(v))

    written: list[Path] = []
    for out in out_paths:
        sidecar = out.with_suffix(out.suffix + ".run.json")
        sidecar.parent.mkdir(parents=True, exist_ok=True)
        sidecar.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        written.append(sidecar)
    return written


def _relative_to(p: Path, root: Path) -> str:
    try:
        return str(p.relative_to(root))
    except ValueError:
        return str(p)


# ---------------------------------------------------------------------------
# CLI sanity check — `python -m run_json some/output.csv` writes a sidecar
# describing this invocation. Useful for ad-hoc shell pipelines.
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(
        description="Write a .run.json sidecar describing this invocation."
    )
    ap.add_argument("outputs", nargs="+", help="Output paths to annotate.")
    ap.add_argument(
        "--params", help="JSON string of params to record.", default="{}"
    )
    args = ap.parse_args()
    parsed = json.loads(args.params)
    paths = write_run_json(args.outputs, params=parsed, script=__file__)
    for p in paths:
        print(p)
