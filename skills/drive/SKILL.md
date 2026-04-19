---
name: drive
description: "Browse, upload, or download files on Google Drive via rclone. Use when the user wants to access or share files on Google Drive."
user_invocable: true
---

# Google Drive

Browse, upload, and download files on Google Drive using rclone.

## Remote

- **`gdrive:`** — Henrik's Google Drive

## Common operations

**Browse:**
```bash
rclone lsd gdrive:path          # list directories
rclone ls gdrive:path           # list files with sizes
```

**Upload:**
```bash
rclone copy /local/path gdrive:destination/ --progress
```

**Download:**
```bash
rclone copy gdrive:path /local/destination/ --progress
```

## Parsing the request

The user may say things like:
- `/drive upload results to judgeGPT/data`
- `/drive what's in the two_judges folder?`
- `/drive download the latest from judgeGPT`

Extract:
1. **Action** — browse, upload, or download
2. **Path** — remote path and/or local path

## Known folders

- **`gdrive:judgeGPT/`** — judgeGPT project (data/, for_ramya/, two_judges/)

## Before destructive operations

Always confirm with the user before:
- `rclone sync` (can delete files on remote)
- Overwriting existing files

## Gotchas

- Use `--progress` for uploads/downloads.
- Google Drive may have duplicate filenames — rclone handles this but it can be confusing.
- Large uploads may be slow due to Drive API rate limits.
