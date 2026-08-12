---
name: referee
description: "Manage Henrik's journal peer-review (refereeing) work — where it lives, the folder convention, confidentiality, and the report/submission workflow. Use when starting a new referee report, organizing an assignment, or asking where referee work goes."
---

# referee

Henrik's journal refereeing lives in **`research/referee/`** on Educloud (peer to `projects/`
and `pipelines/`). This skill knows the location and conventions so nothing has to be re-derived.

## Location & naming
- One folder per manuscript under `research/referee/`, named **`YYYYMM<Venue>[_ShortName]`**
  (mirrors the historical Dropbox archive: `202203JPE`, `202404RESTUD_ReformMultiplier`, `202406AERI`).
  - `YYYYMM` = month the assignment came in · `<Venue>` = journal abbrev (JPE, JEEA, RESTUD, AERI,
    OBES, JBES, …) · optional `_ShortName` = a memorable tag from the title.
- Inside each folder: the **manuscript PDF**, **`report.md`** (the review), and any notes.

## ⚠ Confidentiality — non-negotiable
Peer review is confidential. Manuscripts and reports **must never** be committed to git or placed in
any shared/public location. `research/referee/` is under gitignored `research/` and is not a git repo —
keep it that way: **never `git init` here**, never copy a manuscript into a project repo or a site.

## Workflow — a new assignment
1. **Track it:** the deadline goes in the Saga Todoist queue (`meta/projects.md` / the `Saga` project,
   §📋 Other actions) with the journal's due date as a Todoist deadline.
2. **Make the folder:** `research/referee/<YYYYMM><Venue>[_Short]/`.
3. **Get the manuscript:** Henrik downloads the PDF from the journal's portal (Editorial Manager etc. —
   reviewer login is his; Saga can't fetch it) into the folder.
4. **Write `report.md`:** the review. Match Henrik's own style; the archive (below) has 30+ examples of
   his format. Style guides apply (`research-kit/rules/writing_style*.md`, `/style-review`).
5. **Submit:** Henrik submits via the journal portal (e.g. editorialmanager.com/<jrnl>, login `hsigstad`).
   The Saga review-task auto-completes when done.

## Archive & backup
- Past reports: **`personal-dropbox-ro:referee/`** — **read-only** from Educloud (pull with
  `rclone copy personal-dropbox-ro:referee/ research/referee/`). Already pulled into `research/referee/`.
- **Backup is manual:** Henrik syncs `research/referee/` → Dropbox from his laptop periodically (both
  Educloud dropbox remotes are read-only, so Saga can't push).

## Notes
- Refereeing is academic **service** (work), but kept on **personal** Dropbox and out of shared repos.
- See `research/referee/README.md` for the same conventions in-place.
