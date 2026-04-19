---
name: dropbox
description: "Browse, upload, or download files on Dropbox via rclone. Use when the user wants to share files with collaborators or check what's on Dropbox."
user_invocable: true
---

# Dropbox

Browse, upload, and download files on Dropbox using rclone.

## Available remotes

- **`bi-dropbox:`** — BI/work Dropbox. Contains shared coauthor folders and `data/` directory.
- **`personal-dropbox:`** — Henrik's personal Dropbox. Parts synced locally to `~/Dropbox`.

## Common operations

**Browse:**
```bash
rclone lsd <remote>:path          # list directories
rclone ls <remote>:path           # list files with sizes
```

**Upload:**
```bash
rclone copy /local/path <remote>:destination/ --progress
```

**Download:**
```bash
rclone copy <remote>:path /local/destination/ --progress
```

**Sync (mirror local to remote):**
```bash
rclone sync /local/path <remote>:destination/ --progress --dry-run  # preview first
```

## Parsing the request

The user may say things like:
- `/dropbox upload camara-MG.csv to TCEAndreiHenrik`
- `/dropbox what's in the data folder?`
- `/dropbox download the latest file from ArntzenFivaSigstad`

Extract:
1. **Action** — browse, upload, download, or sync
2. **Remote** — which Dropbox account (guess from context: coauthor folders → bi-dropbox, personal shared folders like TCEAndreiHenrik → personal-dropbox)
3. **Path** — remote path and/or local path

## Known shared folders

- **`bi-dropbox:data/`** — shared datasets (TCEs, TSE, etc.)
- **`personal-dropbox:TCEAndreiHenrik/`** — shared with Andrei Leite (segredo project)
- Coauthor folders on bi-dropbox follow the pattern `{Surname1}{Surname2}` (e.g., `ArntzenFivaSigstad`, `ChenChoiSigstad`)

## Before destructive operations

Always confirm with the user before:
- `rclone sync` (can delete files on remote)
- Overwriting existing files
- Uploading large directories

## Gotchas

- Use `--progress` for uploads/downloads so the user sees progress.
- Quote paths with spaces: `"bi-dropbox:folder with spaces/file.csv"`
- `rclone copy` does not delete files at destination (safe). `rclone sync` does (dangerous).
