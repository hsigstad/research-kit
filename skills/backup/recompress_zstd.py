#!/usr/bin/env python3
"""Recompress a tree of parquet files SNAPPY -> ZSTD into a mirror tree.

For the "manageable-count corpus" backup case (see the backup skill): keeps
every file a normal, directly-readable parquet while cutting size to ~40% of
SNAPPY. Directly readable + incrementally syncable (rclone copy the delta).

Usage:
    python recompress_zstd.py --src <clean_dir> --dst <clean_zstd_dir> [--level 9]

Design notes (learned the hard way, do not "optimize" away):
- SERIAL, single process. Shared hosts are CPU/mem-contended; a ProcessPool
  gets its workers OOM-killed and then DEADLOCKS (hangs in as_completed, no
  BrokenProcessPool raised). Serial can't deadlock and is a good neighbour.
- Stream by iter_batches(2000). Big text parquets are ONE giant row group, so
  read_table / read_row_group loads the whole (>10x decompressed) thing and OOMs.
- Resume: skips outputs already present and newer than source. Re-run after a
  build adds files, then `rclone copy` the delta.
- ZSTD-9 is the sweet spot (level 19 is ~27x slower for a few % more).
"""
import argparse
import os
import sys
import time

import pyarrow.parquet as pq


def jobs(src, dst):
    for root, _, files in os.walk(src):
        for fn in files:
            if fn.endswith(".parquet"):
                s = os.path.join(root, fn)
                yield s, os.path.join(dst, os.path.relpath(s, src))


def is_done(pair):
    s, d = pair
    return os.path.exists(d) and os.path.getmtime(d) >= os.path.getmtime(s)


def recompress(pair, level):
    s, d = pair
    if is_done(pair):
        return
    os.makedirs(os.path.dirname(d), exist_ok=True)
    tmp = d + ".tmp"
    pf = pq.ParquetFile(s)
    w = pq.ParquetWriter(tmp, pf.schema_arrow, compression="zstd",
                         compression_level=level)
    try:
        for batch in pf.iter_batches(batch_size=2000):
            w.write_batch(batch)
    finally:
        w.close()
    os.replace(tmp, d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="source parquet tree (SNAPPY)")
    ap.add_argument("--dst", required=True, help="destination tree (ZSTD mirror)")
    ap.add_argument("--level", type=int, default=9)
    a = ap.parse_args()

    pairs = list(jobs(a.src, a.dst))
    total = len(pairs)
    print(f"[recompress] {total} parquet files: {a.src} -> {a.dst}", flush=True)
    t0 = time.time()
    pending = [p for p in pairs if not is_done(p)]
    print(f"[start] {len(pending)} remaining of {total}", flush=True)
    done = 0
    for pair in pending:
        try:
            recompress(pair, a.level)
        except Exception as e:  # noqa: BLE001 - one bad file must not halt the run
            print(f"[skip] {pair[0]}: {type(e).__name__}: {e}", flush=True)
            if os.path.exists(pair[1] + ".tmp"):
                os.remove(pair[1] + ".tmp")
            continue
        done += 1
        if done % 20 == 0:
            n = sum(1 for p in pairs if is_done(p))
            print(f"[{n}/{total}] {time.time()-t0:.0f}s", flush=True)

    so = sum(os.path.getsize(s) for s, _ in pairs)
    sn = sum(os.path.getsize(d) for _, d in pairs if os.path.exists(d))
    n = sum(1 for p in pairs if is_done(p))
    print(f"[done] {n}/{total} | {so/1e9:.2f}GB -> {sn/1e9:.2f}GB "
          f"({100*sn/max(so,1):.0f}% of snappy) in {time.time()-t0:.0f}s", flush=True)
    if n < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
