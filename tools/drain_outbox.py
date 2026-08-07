#!/usr/bin/env python3
"""Drain the sandbox->host upload outbox: <workspace>/inbox/to_dropbox/.

Sandboxed Claude sessions have no Dropbox upload rights. Instead of the
manual "tell a non-sandboxed claude" ritual, they drop a manifest here and
this script (run by host cron, or manually) does the upload with the
full-rights rclone config.

Manifest: inbox/to_dropbox/<name>.manifest.json
{
  "dest": "bi-dropbox:data/TSE/",          // default destination dir (rclone remote:path)
  "files": [
    {"path": "pipelines/politica/build/x.zip",   // relative to workspace root
     "sha256": "...",                            // optional: verified before upload
     "dest": "bi-dropbox:data/TSE/x.zip"}        // optional: overrides default dest
  ],
  "log_file": "pipelines/politica/docs/data.md", // optional: append log_entry after success
  "log_entry": "- 2026-07-05: uploaded x.zip to bi-dropbox:data/TSE/",
  "note": "free text for humans"
}

On success the manifest moves to inbox/to_dropbox/done/ (stamped). On
failure it stays put and a sibling <name>.error.txt explains why; fix and
re-run. Uploads use `rclone copyto` (checksum-verified by rclone) plus an
independent size check via `rclone lsjson`.

OVERWRITE POLICY (never clobber Dropbox data):
  The drain NEVER overwrites a file that already exists at the destination.
  On a collision it refuses that file and records it in <name>.error.txt;
  the manifest stays put. Overwriting requires a HOST operator to re-run
  the drain explicitly with --allow-overwrite. This flag lives only on the
  host command line: the cron entry never passes it, and there is
  deliberately NO manifest-level opt-in — a sandboxed session (which writes
  the manifest but has no Dropbox credentials of its own) therefore cannot
  authorize an overwrite. Replacing existing data is always a deliberate,
  human-initiated host action. If the remote state cannot be verified, the
  drain refuses the file rather than risk a blind overwrite (fail-safe).
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

RCLONE_TIMEOUT = 3600


def workspace() -> Path:
    env = os.environ.get("RESEARCH_WORKSPACE")
    if env:
        return Path(env)
    for cand in (Path.home() / "research", Path("/workspace")):
        if (cand / "research-kit").exists():
            return cand
    return Path.home() / "research"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def remote_size(dest: str) -> int:
    remote_dir, name = dest.rsplit("/", 1) if "/" in dest else (dest, "")
    out = subprocess.run(
        ["rclone", "lsjson", remote_dir], capture_output=True, text=True, timeout=120
    )
    if out.returncode != 0:
        return -1
    for entry in json.loads(out.stdout or "[]"):
        if entry.get("Name") == name:
            return entry.get("Size", -1)
    return -1


def remote_exists(dest: str):
    """Does a file already exist at `dest`?  Returns True / False / None.

    None means the remote state could not be determined (e.g. a transient
    listing error) and callers MUST treat it as unsafe — better to refuse
    than to overwrite blind. A missing parent directory is a definitive
    "absent" (False), which is the normal case for a brand-new dest folder.
    """
    remote_dir, name = dest.rsplit("/", 1) if "/" in dest else (dest, "")
    out = subprocess.run(
        ["rclone", "lsjson", remote_dir], capture_output=True, text=True, timeout=120
    )
    if out.returncode == 0:
        try:
            entries = json.loads(out.stdout or "[]")
        except Exception:
            return None
        return any(e.get("Name") == name for e in entries)
    stderr = (out.stderr or "").lower()
    if "directory not found" in stderr or "not found" in stderr:
        return False  # parent dir doesn't exist yet => file is absent
    return None  # genuine/unknown error => cannot vouch for remote state


def process(manifest: Path, ws: Path, allow_overwrite: bool = False) -> list[str]:
    """Returns list of error strings; empty list = success.

    allow_overwrite is host-only (see module docstring): it comes from the
    --allow-overwrite CLI flag, never from the manifest, so a sandboxed
    session cannot cause an existing Dropbox file to be replaced.
    """
    errors = []
    try:
        m = json.loads(manifest.read_text())
    except Exception as e:
        return [f"unreadable manifest: {e}"]

    default_dest = m.get("dest", "")
    files = m.get("files", [])
    if not files:
        return ["manifest has no files"]

    for f in files:
        rel = f.get("path", "")
        local = ws / rel
        if not local.is_file():
            errors.append(f"{rel}: file not found")
            continue
        want = f.get("sha256")
        if want:
            got = sha256(local)
            if got != want:
                errors.append(f"{rel}: sha256 mismatch (manifest {want[:12]}…, disk {got[:12]}…)")
                continue
        dest = f.get("dest") or (default_dest.rstrip("/") + "/" + local.name)
        if ":" not in dest:
            errors.append(f"{rel}: dest '{dest}' is not remote:path")
            continue
        exists = remote_exists(dest)
        if exists is None:
            errors.append(
                f"{rel}: could not verify remote state at {dest}; refusing "
                f"(fail-safe, will not risk a blind overwrite)"
            )
            continue
        if exists and not allow_overwrite:
            errors.append(
                f"{rel}: destination already exists at {dest}; refusing to "
                f"overwrite. A host operator must re-run the drain with "
                f"--allow-overwrite to replace it (the cron never does, and "
                f"the manifest cannot request it)."
            )
            continue
        if exists and allow_overwrite:
            print(f"  OVERWRITING existing {dest} (--allow-overwrite)")
        print(f"  uploading {rel} -> {dest}")
        r = subprocess.run(
            ["rclone", "copyto", str(local), dest],
            capture_output=True, text=True, timeout=RCLONE_TIMEOUT,
        )
        if r.returncode != 0:
            errors.append(f"{rel}: rclone failed: {r.stderr.strip()[:300]}")
            continue
        size = remote_size(dest)
        if size != local.stat().st_size:
            errors.append(f"{rel}: post-upload size check failed (local {local.stat().st_size}, remote {size})")

    if not errors and m.get("log_file") and m.get("log_entry"):
        log_path = ws / m["log_file"]
        if log_path.is_file():
            with open(log_path, "a") as fh:
                fh.write("\n" + m["log_entry"].rstrip() + "\n")
        else:
            errors.append(f"log_file {m['log_file']} not found (uploads succeeded)")
    return errors


def main() -> int:
    argv = sys.argv[1:]
    allow_overwrite = "--allow-overwrite" in argv
    # Named manifests may be passed to scope a run (e.g. an --allow-overwrite
    # retry of one file); bare basenames or full names both match.
    named = {a for a in argv if not a.startswith("-")}

    ws = workspace()
    outbox = ws / "inbox" / "to_dropbox"
    done = outbox / "done"
    outbox.mkdir(parents=True, exist_ok=True)
    done.mkdir(exist_ok=True)

    manifests = sorted(outbox.glob("*.manifest.json"))
    if named:
        manifests = [m for m in manifests if m.name in named or m.stem in named]
    if not manifests:
        return 0
    if allow_overwrite:
        print("!! --allow-overwrite: existing destinations MAY be replaced")
    failures = 0
    for man in manifests:
        print(f"[{datetime.now().isoformat(timespec='seconds')}] {man.name}")
        errs = process(man, ws, allow_overwrite=allow_overwrite)
        errfile = man.with_suffix(".error.txt")
        if errs:
            failures += 1
            errfile.write_text("\n".join(errs) + "\n")
            print(f"  FAILED ({len(errs)} error(s)) — see {errfile.name}")
        else:
            if errfile.exists():
                errfile.unlink()
            stamp = time.strftime("%Y%m%dT%H%M%S")
            shutil.move(str(man), done / f"{stamp}_{man.name}")
            print("  done")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
