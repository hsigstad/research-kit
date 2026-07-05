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


def process(manifest: Path, ws: Path) -> list[str]:
    """Returns list of error strings; empty list = success."""
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
    ws = workspace()
    outbox = ws / "inbox" / "to_dropbox"
    done = outbox / "done"
    outbox.mkdir(parents=True, exist_ok=True)
    done.mkdir(exist_ok=True)

    manifests = sorted(outbox.glob("*.manifest.json"))
    if not manifests:
        return 0
    failures = 0
    for man in manifests:
        print(f"[{datetime.now().isoformat(timespec='seconds')}] {man.name}")
        errs = process(man, ws)
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
