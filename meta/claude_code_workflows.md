# Claude Code Workflows & Setup Guide

This document summarizes how I use Claude Code for research work, with pointers
to the attached files so you can adapt what's useful.

---

## 1. Workspace Architecture

The most impactful thing is how the workspace itself is organized. I have a
single top-level repo (`research/`) that contains everything, with a structure
that Claude learns once and then navigates autonomously:

```
research/                     # top-level repo
  CLAUDE.md                   # entry point — points to rules/workspace.md
  research/                   # workspace-level rules, tools, meta docs
    rules/                    # conventions Claude must follow
      workspace.md            # master instructions (directory layout, behavioral rules)
      project_docs_contract.md # what docs/ files mean and how to use them
      inline_audit_trail.md   # code documentation standard
    meta/                     # cross-project knowledge layer
      research_map.md         # all projects, their questions, methods, status
      identification_strategies.md
      variable_dictionary.md  # shared variables across projects
      data_linkages.md        # how datasets connect across projects/pipelines
      llm_pipelines.md        # LLM usage across projects
      priorities.md           # what to work on next
    tools/                    # shared scripts (e.g. literature_search.py)
    skills/                   # Claude Code slash commands
    contacts.yaml             # for meeting scheduling
    docker/                   # sandbox containers

  projects/                   # individual research projects
    <project-slug>/
    ...each with:
      CLAUDE.md               # project-specific instructions + current focus
      docs/                   # standardized documentation
        summary.md            # what the project is about
        thinking.md           # speculative/exploratory notes
        todo.md               # current tasks + session handoff notes
        done.md               # completed tasks (moved from todo.md)
        data.md               # datasets used and how
        methods.md            # estimation strategy
        literature.md         # curated papers
        institutions.md       # institutional context
        decisions.md          # design decisions with rationale
        meetings.md           # meeting notes
        feedback.md           # coauthor/referee feedback
      source/                 # scripts (Python, R, Stata)
      build/                  # outputs (parquet, csv, json)
      paper/                  # manuscript, tables, figures
        tables/
        figures/
        references.bib

  pipelines/                  # data cleaning repos (no paper/)
    <pipeline-slug>/
    ...each with:
      docs/                   # same structure minus paper-related files
      source/
      build/

  data_catalog/               # metadata-only registry of raw datasets
    DATA_CATALOG.md           # master list of all raw data
    codebooks/                # variable-level documentation

  diarios/                    # shared Python module (reusable utilities)

  ideas/                      # research ideas with YAML frontmatter + ranking
    index.md                  # master index with ranked tables
    *.md                      # individual idea files
    topics/                   # topical collections
```

### Why this structure matters for Claude Code

- **Each project has its own CLAUDE.md** with current focus, so Claude knows
  what to work on without being told every session.
- **Standardized docs/** means Claude always knows where to look for context
  (summary.md for overview, todo.md for tasks, data.md for datasets).
- **The meta/ layer** lets Claude reason across projects -- "which other project
  uses this variable?", "is there a shared pipeline for this data?".
- **Source/build naming convention**: `source/X.py` produces `build/X.parquet`.
  Claude can trace any output back to its generating code.
- **Session handoff**: at end of session, Claude appends a note to `docs/todo.md`
  saying what was done and where it left off. Next session picks up seamlessly.
- **data_catalog/** means Claude can look up any raw dataset's structure without
  needing access to the data itself.

### The docs contract

The `project_docs_contract.md` defines what each docs file means semantically:
- `thinking.md` is for speculation, not results
- `decisions.md` records the "why" behind choices (with date, alternatives considered)
- `todo.md` has current tasks; `done.md` is the archive
- Never mix content across files

This is what makes Claude reliable across projects -- it doesn't have to guess
what goes where.

**Files:** `rules/workspace.md`, `rules/project_docs_contract.md`

### CLAUDE.md (entry point)

Claude Code reads `CLAUDE.md` at the root of your project on every session
start. Mine points to `rules/workspace.md` which has the full instructions.

**Takeaway:** Even a short CLAUDE.md with your preferences (language, style,
what to avoid) makes a big difference. Claude follows these on every session.

---

## 2. Custom Skills (Slash Commands)

Skills are reusable prompts you invoke with `/skillname`. Each is a directory
with a `SKILL.md` file. You symlink them into `~/.claude/skills/` and they
appear as slash commands.

### My most useful skills:

| Skill | What it does |
|-------|-------------|
| `/literature` | Full academic literature pipeline: generates search queries, hits Semantic Scholar + OpenAlex APIs, Claude curates results, expands via citation graphs, writes bib entries, downloads PDFs |
| `/new-project` | Scaffolds a new research project with standard docs structure, reads existing seed files to extract context |
| `/new-pipeline` | Same for data processing pipelines |
| `/handoff` | End-of-session: commits and pushes all changes, updates todo/done docs |
| `/idea` | Records a research idea with YAML frontmatter and adds to index |
| `/iat-check` | Audits Python scripts for documentation quality (Inline Audit Trail convention) |
| `/data` | Searches across a data catalog, variable dictionary, and linkage docs |
| `/whatsapp` | Send/read WhatsApp messages to coauthors via MCP bridge |
| `/zoom` | Creates Zoom meetings as Google Calendar events, looks up contacts |
| `/drive` | Browse/upload/download Google Drive files via rclone |
| `/dropbox` | Same for Dropbox |
| `/llmkit` | Reference for an LLM extraction framework I use |
| `/diarios` | API reference for a shared Python module |

**How to create your own:** Make `~/.claude/skills/myskill/SKILL.md` with YAML
frontmatter (`name`, `description`, `user_invocable: true`) followed by the
prompt instructions. Then type `/myskill` in Claude Code.

---

## 3. MCP Integrations (External Tool Access)

Claude Code supports MCP (Model Context Protocol) servers that give it access to
external services. I have these configured in `.mcp.json`:

- **WhatsApp** -- Send messages to coauthors/project groups directly from Claude
  Code. Uses a local bridge that connects to WhatsApp Web.
- **Google Calendar** -- Create meetings, find free times, RSVP to events.
  Combined with a `contacts.yaml` file for name-to-email lookup.
- **Gmail** -- Read/search/draft emails.
- **Google Drive** -- (via rclone, not MCP, but same idea)

The Calendar + contacts setup is particularly nice: I say "set up zoom meeting
with Sigurd Tuesday 2pm" and it resolves your email, creates the event with my
Zoom link, correct timezone, etc.

**Files:** `.mcp.json` (WhatsApp config), `contacts.yaml`

---

## 4. Docker Sandbox for Autonomous Tasks

For tasks where Claude needs to run autonomously without permission prompts
(e.g., "scrape these 50 websites", "process this large dataset"), I run it
inside a Docker container with `--dangerously-skip-permissions`.

The container:
- Has full internet access but only the current working directory is mounted
- No SSH keys, git credentials, or home directory exposed
- Memory and CPU limited
- Auto-detects Docker (laptop) or Apptainer/Singularity (HPC server)

Usage: `./run.sh "collect news stories about corruption from Brazilian media"`

**Files:** `docker/` directory with Dockerfile, run.sh, Apptainer .def file.

See also `claude_code_sandbox.md` for a full writeup of permission modes and
security considerations.

---

## 5. Memory System

Claude Code has a built-in persistent memory that survives across sessions. I
use it to store:
- **Feedback** -- corrections about how I want Claude to work ("don't use inline
  python -c", "don't summarize at the end of responses")
- **References** -- where things are (rclone remotes, API keys, external systems)
- **Project context** -- non-obvious facts about ongoing work

Memory files live in `~/.claude/projects/<project>/memory/` with a `MEMORY.md`
index. Claude reads the index at session start and loads relevant memories.

**Takeaway:** If Claude keeps making the same mistake, tell it to remember the
correction. It persists across all future sessions.

---

## 6. Literature Search Pipeline

The `/literature` skill is worth highlighting separately. It:
1. Reads project docs to understand the research question
2. Generates 10-20 search queries
3. Searches Semantic Scholar + OpenAlex APIs (via `literature_search.py`)
4. Claude curates results (first pass: 20-60 papers)
5. Expands via citation graphs on 5-10 key papers
6. Second curation pass
7. Writes `literature.md` + BibTeX entries
8. Downloads PDFs (checks local Dropbox first, then Open Access, then paywalled
   via university proxy)

**Files:** `tools/literature_search.py`

---

## 7. Inline Audit Trail (IAT) Convention

A lightweight documentation standard for data processing scripts. Instead of
heavy comments everywhere, it requires structured comments only where they add
information a reader can't recover from the code:

- `# INTENT:` -- why a non-obvious filter or transformation exists
- `# REASONING:` -- why one approach was chosen over alternatives
- `# ASSUMES:` -- hidden data properties the code depends on
- `# SOURCE:` -- external data inputs
- Validation guards (asserts after joins/filters)

The `/iat-check` skill audits scripts against this convention.

**Files:** `rules/inline_audit_trail.md`

---

## 8. Auto Mode

For day-to-day work where you trust Claude but don't want to approve every file
edit: `claude --enable-auto-mode`. It uses a safety classifier that blocks
dangerous actions (mass deletion, credential exfiltration) but allows normal
file operations. Good middle ground between clicking "approve" on everything and
full bypass mode.

---

## Getting Started (Minimum Viable Setup)

If you want to try just one thing:
1. Create a `CLAUDE.md` in your project root with your preferences
2. Install Claude Code: `npm install -g @anthropic-ai/claude-code`
3. Run `claude` in your project directory

To add a skill:
```bash
mkdir -p ~/.claude/skills/myskill
# Create SKILL.md with instructions
# Type /myskill in Claude Code
```

To add MCP (e.g., Google Calendar):
- Add server config to `.mcp.json` in your project root
- Claude Code discovers it automatically
