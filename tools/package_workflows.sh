#!/usr/bin/env bash
# Package Claude Code workflow documentation into a shareable zip.
#
# Usage:
#   ./package_workflows.sh                  # creates /tmp/claude-code-workflows.zip
#   ./package_workflows.sh ~/Desktop/out    # creates ~/Desktop/out/claude-code-workflows.zip

set -euo pipefail

# Find workspace root (directory containing CLAUDE.md next to projects/)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RESEARCH="$ROOT/research"

OUTDIR="${1:-/tmp}"
TMPDIR=$(mktemp -d)
DEST="$TMPDIR/claude-code-workflows"

mkdir -p "$DEST"/{rules,skills,docker,tools,meta,examples}

# --- README / overview ---
cp "$RESEARCH/meta/claude_code_workflows.md" "$DEST/README.md"

# --- Rules ---
cp "$RESEARCH/rules/workspace.md"              "$DEST/rules/"
cp "$RESEARCH/rules/project_docs_contract.md"  "$DEST/rules/"
cp "$RESEARCH/rules/inline_audit_trail.md"     "$DEST/rules/"

# --- Meta (cross-project knowledge layer) ---
for f in research_map.md identification_strategies.md variable_dictionary.md \
         data_linkages.md llm_pipelines.md priorities.md; do
    cp "$RESEARCH/meta/$f" "$DEST/meta/" 2>/dev/null || true
done

# --- Skills ---
for skill_dir in "$RESEARCH/skills"/*/; do
    name=$(basename "$skill_dir")
    mkdir -p "$DEST/skills/$name"
    cp "$skill_dir/SKILL.md" "$DEST/skills/$name/" 2>/dev/null || true
done

# --- Docker sandbox ---
for f in Dockerfile run.sh claude-sandbox.def monitor_memory.sh; do
    cp "$RESEARCH/docker/claude-sandbox/$f" "$DEST/docker/" 2>/dev/null || true
done

# --- Sandbox docs ---
cp "$RESEARCH/meta/claude_code_sandbox.md" "$DEST/"

# --- Tools ---
cp "$RESEARCH/tools/literature_search.py" "$DEST/tools/"

# --- Config examples ---
cp "$ROOT/.mcp.json"             "$DEST/"          2>/dev/null || true
cp "$RESEARCH/contacts.yaml"     "$DEST/"          2>/dev/null || true
cp "$ROOT/CLAUDE.md"             "$DEST/CLAUDE.md.example" 2>/dev/null || true

# --- Example project structure ---
# Include a real project's CLAUDE.md and docs/ as a concrete example
EXAMPLE_PROJECT="causal-judge"
EXAMPLE_SRC="$ROOT/projects/$EXAMPLE_PROJECT"
if [ -d "$EXAMPLE_SRC" ]; then
    mkdir -p "$DEST/examples/project-$EXAMPLE_PROJECT/docs"
    cp "$EXAMPLE_SRC/CLAUDE.md" "$DEST/examples/project-$EXAMPLE_PROJECT/"
    for f in summary.md todo.md data.md methods.md decisions.md thinking.md; do
        cp "$EXAMPLE_SRC/docs/$f" "$DEST/examples/project-$EXAMPLE_PROJECT/docs/" 2>/dev/null || true
    done
fi

# Include a few project CLAUDE.md files to show the variety
mkdir -p "$DEST/examples/project-claude-mds"
for proj in audit bind connect deterrence procure saude vague; do
    cp "$ROOT/projects/$proj/CLAUDE.md" \
       "$DEST/examples/project-claude-mds/$proj-CLAUDE.md" 2>/dev/null || true
done

# --- Create zip ---
mkdir -p "$OUTDIR"
(cd "$TMPDIR" && zip -r "$OUTDIR/claude-code-workflows.zip" claude-code-workflows/)

rm -rf "$TMPDIR"

echo "Created: $OUTDIR/claude-code-workflows.zip"
echo "Contents:"
unzip -l "$OUTDIR/claude-code-workflows.zip" | tail -n +4 | head -n -2
