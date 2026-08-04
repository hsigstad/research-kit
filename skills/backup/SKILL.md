---
name: backup
description: "Back up expensive-to-regenerate pipeline/project artifacts to Dropbox with the right format and location. Use when the user wants to offload, back up, or archive data to Dropbox — a corpus, a cache, scraped raw, or a whole pipeline's build outputs."
---

# Back up data to Dropbox

Disaster-recovery copies of expensive-to-regenerate artifacts (scraped corpora, LLM
caches, geoblocked raw PDFs, BigQuery exports). Dropbox is a **cold backup**, not a
working store. For ad-hoc file sharing / browsing, use the `dropbox` skill instead.

Writable remotes exist only on the **host** (`bi-dropbox:`), not the sandbox
(`*-ro:` only). Stage compressed archives on `/projects` (has TBs free), not `/tmp`.

## The two decisions: FORMAT and LOCATION

### FORMAT — keyed on file count/size, not one-size-fits-all

The dividing line is Dropbox's `too_many_write_operations` failure (bursts of many
small files). Pick by artifact shape:

| Shape | Form | Why |
|---|---|---|
| **Corpus**: hundreds–low-thousands of medium/large files (parquet, MB–GB each) | **Per-file**, recompressed to **ZSTD-9**, mirroring the local tree | Directly readable + partial restore; `rclone copy` gives free **incremental sync**; ZSTD-in-parquet beats tar-of-snappy (a real case: 44 GB SNAPPY → 18 GB ZSTD vs 34 GB tar.zst) |
| **Tiny-file cache**: 10k–100k files, few KB each (LLM caches) | **Single `tar.zst`** | Per-file trips the write-op limit; FS block-slack inflates size (a "1 GB" cache was 411 MB of data across 63k files → 20 MB zstd) |
| **Bulk incompressible**: 10k+ PDFs/images | **`tar` with `zstd -3`** (combine, don't compress) | Compression won't help; combining dodges the write-op limit |

Rule of thumb: per-file is strictly better **until** files get too many/too tiny
(~a few thousand medium files is the comfortable ceiling), then you must combine.
Already-compressed files (`.zip`, `.pdf`) at low count → upload per-file as-is
(don't re-compress). ZSTD-9 is the sweet spot; level 19 is ~27× slower for a few %.

### LOCATION — ownership/consumption, NOT "produced by a pipeline"

Fetching ≠ owning. Decide by who reads it:

- **`bi-dropbox:data/<x>/`** — the **shared data lake**: raw inputs read across many
  projects (TSE, cnpj, court corpus) *and* deliberate cross-cutting namespaces
  (`data/TCEs/` for all TCE state pulls, `data/mides/` for the shared procurement
  bulk). These stay in `data/` even if one pipeline scraped them.
- **`bi-dropbox:pipelines/<slug>/`** — artifacts **owned and consumed by only that
  pipeline**: its `build/` outputs and its *own* scrape/LLM caches nothing else reads.
  Build outputs → `pipelines/<slug>/build/...`; caches → `pipelines/<slug>/` root.

**Do NOT blanket-move `data/` → `pipelines/`.** Most of what a pipeline "produces"
into `data/` is shared raw. Match the existing sibling's layout (e.g. new TCE state
pull → mirror the other `data/TCEs/tce_<state>/` dirs).

## Workflow

1. **Assess shape.** `du -sh`, `find <dir> -type f | wc -l`, extension breakdown,
   and for parquet check the codec (`pq.ParquetFile(f).metadata...compression`).
   Choose FORMAT + LOCATION from the tables above.
2. **Check for prior backups first.** List the destination and siblings — a previous
   session may already have offloaded it (possibly under a different name/layout).
   Reconcile before duplicating; surface (don't silently delete) anything you didn't
   create that overlaps.
3. **Compress if needed.**
   - Corpus → recompress to ZSTD parquet with the bundled helper:
     `python recompress_zstd.py --src <clean> --dst <clean_zstd>` (serial, resumable;
     see its header for the OOM/deadlock gotchas). Verify row counts match a sample.
   - Cache/PDF → `tar -C <parent> -cf - <dir> | zstd -<L> -T3 -o <name>_<startYr>-<endYr>.tar.zst`
     then `zstd -t` to verify. Name archives by **time coverage**.
4. **Upload.** `rclone copy -P --transfers 4 --checkers 8 <local> <remote>`
   (`copy` never deletes on remote; reserve `sync` for the user, with `--dry-run` first).
5. **Verify.** `rclone check <local> <remote>` (0 differences) or compare `rclone size`
   file counts + bytes. Small byte deltas = dir-inode accounting, not content.
6. **Beware mid-build races.** If the pipeline is still writing, files added after your
   enumeration are missed — re-scan and `rclone copy` the delta (it's cheap).
7. **Update the data catalog** (`$ROOT/data_catalog/`, hand-curated — edit
   `_annotations/datasets/<x>.yaml` `storage.backup` **and** the matching
   `DATA_CATALOG.md` section; do NOT regenerate). Validate:
   `.venv/bin/python scripts/validate_annotations.py`.
8. **Record in memory** what was non-obvious (new location, a gotcha, an audit result).

## Auditing for stranded local-only data

To find artifacts that were never offloaded: reconcile local scrape/build dirs against
the remote. **Compare by archive/coverage, NOT raw file count** — a dir of 44k loose
zips correctly backed up as 2 consolidated tars will falsely look like a 44k→2 "gap".
Where remote count > local, that's usually extra older pulls, not a gap. Confirm true
gaps (`local > remote` in coverage) before uploading.

## Restore

- Per-file parquet: `rclone copy <remote-dir> <local>` (or `rclone cat` one file).
- Archive: `rclone cat <archive> | tar -x{--zstd or z}f - -C <parent>`.

## Gotchas

- `too_many_write_operations` fires on bursts of many files — combine into few archives.
- Foreground `sleep` may be blocked in-session; use background jobs / `Monitor` to wait.
- `rclone move` leaves empty dir markers — clean with `rclone rmdirs`.
- Commit catalog + skill changes (standing authorization); confirm before any purge/force.
