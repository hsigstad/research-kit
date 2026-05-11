---
name: cite-sync
description: "Regenerate each project's docs/refs/manifest.toml from the workspace citation registry. Walks docs/ and paper/ for [ns:key] tokens with external namespaces, looks each up in research/refs/registry.toml, and writes the public-facing subset (title + description, no internal paths) to the project manifest. Use when the user invokes /cite-sync, /cite-sync <slug>, or asks to 'sync the manifest', 'rebuild the refs manifest', 'regenerate citations manifest'."
user_invocable: true
---

# /cite-sync — Regenerate project citation manifests

Action skill: regenerates `docs/refs/manifest.toml` for each project from
the workspace citation registry at `research/refs/registry.toml`. Thin
wrapper over `research-kit/tools/citations.py --sync`.

This is a **write action**, not an audit. To validate citation tokens
without writing anything, use `/check cite`.

## What the manifest does

The project manifest is a privacy/scoping boundary. Coauthors who clone a
project repo without access to the full workspace registry need
human-readable titles for every external citation. `/cite-sync` builds
that file by:

1. Walking the project's `docs/` and `paper/` for `[ns:key]` tokens with
   **external** namespaces (`method`, `catalog`, `pipeline`, `var`,
   `idea`, `proj`, `inst`).
2. Looking each up in the workspace registry.
3. Writing the public-facing subset — `title` + `description` only, no
   paths, no internal pointers — to `docs/refs/manifest.toml`.

The manifest stays in sync with what the project actually cites: drop a
citation, `/cite-sync` removes the entry next run; add a new one,
`/cite-sync` adds it.

## How to invoke

| Form | What it does |
|------|--------------|
| `/cite-sync` | Regenerate manifests for every project in the workspace |
| `/cite-sync <slug>` | Regenerate one project's manifest |
| `/cite-sync --dry-run` | Show the diff per project, don't write |

Raw command:

```bash
python3 ~/research/research-kit/tools/citations.py [<slug>] --sync
```

## Procedure

### 1. Run in dry-run mode first

```bash
python3 $ROOT/research-kit/tools/citations.py [<slug>] --sync --dry-run
```

Surface the per-project diff: which projects would change, and the
added/removed entries. If nothing would change, exit cleanly with
"manifests already in sync."

### 2. Ask before writing

If any project would change, present the diff and ask for confirmation.
Don't auto-apply — even though `/cite-sync` is an action skill, the
manifests live in git and the user should see what's about to land.

### 3. Apply

```bash
python3 $ROOT/research-kit/tools/citations.py [<slug>] --sync
```

Report what changed per project.

### 4. Suggest commit

After writing, list the projects with modified manifests and ask whether
to commit per-repo. Don't auto-push.

## Common failures

- **Registry not found.** If `research/refs/registry.toml` is missing,
  surface the path and stop. Don't try to create the registry.
- **Unresolved external citation.** A `[ns:key]` token in a project doc
  has no matching registry entry. The token is silently dropped from the
  manifest (since there's nothing to write). Surface as a warning and
  suggest `/check cite` to see the full list of unresolved citations.

## Related

- `/check cite` — validate citation tokens (no writes).
- `/check` — full project-conventions audit.
- Citation registry spec: `workspace/research/rules/citations.md`.
