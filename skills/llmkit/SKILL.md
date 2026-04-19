---
name: llmkit
description: "Reference for the llmkit LLM extraction framework — cache design, Pydantic validation, audit workflow, and per-project setup. Use when writing code that does LLM-based structured extraction, setting up new extraction tasks, or working with cached LLM outputs."
user_invocable: true
---

# llmkit — LLM Extraction Framework

Shared package at `~/research/packages/llmkit/` (`pip install -e`). Provides deterministic, auditable LLM extraction with Pydantic validation and file-backed caching. Designed for academic research where referees need to understand exactly what happened.

## Core API

```python
from llmkit import LLMCache, ExtractionSchema, extract, audit_sample
from llmkit.cache import text_hash, content_hash
from llmkit.extract import ExtractionResult
```

### `LLMCache(directory: Path)`

File-backed cache. Each entry is a JSON file with three sections: `_cache_meta`, `input_text`, `extraction`.

```python
cache = LLMCache(Path("cache_dir"))
key = cache.key(doc_id, text_hash, model)  # composite key
hit = cache.get(key)                       # by composite key
hit = cache.get_by_doc(doc_id)             # legacy fallback (doc_id.json)
cache.put(key, extraction, doc_id=..., text_hash=..., ...)
entries = cache.iter_entries()
```

### `ExtractionSchema(BaseModel)`

Base class for Pydantic schemas. Subclass and set `schema_name`/`schema_version` as `ClassVar[str]`:

```python
from typing import ClassVar
from llmkit import ExtractionSchema

class MySchema(ExtractionSchema):
    schema_name: ClassVar[str] = "my_task"
    schema_version: ClassVar[str] = "v1"
    field_a: str = ""
```

### `extract(...) -> ExtractionResult`

Main entry point. Checks cache → calls LLM → validates → caches.

```python
result = extract(
    doc_id="ABC", text="...",
    system_prompt="...", user_prompt="...",
    schema=MySchema, model="gpt-4o-mini",
    prompt_file="my_prompt.txt",
    cache=cache, client=openai_client,
    reextract=False,  # True to redo stale entries
)
result.valid        # bool — did Pydantic validation pass
result.parsed       # MySchema instance (or None if invalid)
result.raw          # dict — raw LLM JSON
result.cached       # bool — loaded from cache
result.stale        # bool — cached but prompt changed since
result.usage        # dict — token counts
```

### `audit_sample(results, n=50, ...)`

Stratified sampling for human review. See `llmkit/audit.py`.

## Cache design

### Cache key = `hash(doc_id, text_hash, model)`

- **Prompt changes do NOT invalidate cache** — intentional, to avoid re-extraction during iterative development
- **Text changes DO invalidate** — different text = different key = cache miss
- **Model changes DO invalidate** — different model = different key

### Cache metadata (audit trail, not part of key)

Each cached JSON file contains:

```json
{
  "_cache_meta": {
    "doc_id": "2Q6JZRW4NZ243MR",
    "text_hash": "f3a1b2c4d5e6f7a8",
    "prompt_hash": "9791af5d5643f4dc",
    "model": "gpt-4o-mini",
    "model_version": "gpt-4o-mini-2024-07-18",
    "temperature": 0,
    "max_tokens": 4000,
    "schema_name": "irregularity_extraction",
    "schema_version": "v1",
    "source_commit": "ccfb959",
    "validation_status": "valid",
    "finish_reason": "stop",
    "timestamp": "2026-03-23T10:01:06+00:00",
    "usage": {"prompt_tokens": 7838, "completion_tokens": 1737},
    "api_params": {"response_format": "json_object", "top_p": 1}
  },
  "messages": [
    {"role": "system", "content": "You are an expert..."},
    {"role": "user", "content": "Extract all irregularities..."}
  ],
  "extraction": { ... LLM output ... }
}
```

Three top-level sections: `_cache_meta` (audit trail), `messages` (exact API input), `extraction` (LLM output). No redundancy — document text lives inside the user message.

### Staleness and `--reextract`

```python
entry.is_stale(current_prompt_hash="...")  # True if prompt changed
```

- **Day-to-day**: run normally, cache accumulates, prompt edits don't trigger re-extraction
- **Before submission**: pass `--reextract` to bring all entries in line with final prompt/data
- Legacy entries (no metadata) are always considered stale

### Backward compatibility

Old-style caches (`{doc_id}.json` with raw extraction, no metadata wrapper) are readable via `get_by_doc()`. The `_load()` method detects both formats.

## Per-project setup

Each project defines its own schemas and prompts; llmkit provides the machinery.

### Directory structure

```
project/source/llm/
    __init__.py
    schemas.py          # Pydantic models (inherit ExtractionSchema)
    irregularity.py     # Wrapper wiring llmkit to project config
    prompts/
        irregularity_system.txt
        irregularity_user.txt
```

### Prompt versioning

Prompts are plain text files tracked by git. **No version suffixes in filenames** — git history IS the version control. The prompt's content hash is stored in cache metadata, and `source_commit` records which repo state produced the extraction.

To reconstruct the exact prompt for a cached entry:
```bash
git show <source_commit>:source/llm/prompts/irregularity_system.txt
```

### Project wrapper pattern

The project wrapper handles legacy cache fallback and project-specific config:

```python
# source/llm/my_task.py
from llmkit import LLMCache, extract
from llmkit.cache import content_hash, text_hash
from source.llm.schemas import MySchema

CACHE = LLMCache(DATA_DIR / "my_cache")

def extract_my_task(*, doc_id, text, client, reextract=False):
    # 1. Try new composite key
    # 2. Try legacy get_by_doc() fallback
    # 3. Call LLM via extract()
    ...
```

See `procure/source/llm/irregularity.py` for the full pattern including legacy cache handling.

## Existing implementation: procure

The `procure` project has a working extraction pipeline:

- **Schema**: `source/llm/schemas.py` → `IrregularityExtraction` (document-level + per-irregularity fields)
- **Prompts**: `source/llm/prompts/irregularity_system.txt`, `irregularity_user.txt`
- **Wrapper**: `source/llm/irregularity.py` → `extract_irregularities()`
- **Script**: `source/analysis/llm_extract_irregularities.py`
- **Cache**: `DATA_DIR/tce_sp/consulta/llm_cache/` (~6,141 legacy entries + new-format entries)
- **Downstream**: `source/analysis/build_consulta_llm.py` reads `llm_extract_irregularities.json`

CLI:
```bash
python3 -m source.analysis.llm_extract_irregularities            # use cache
python3 -m source.analysis.llm_extract_irregularities --reextract # redo stale
python3 -m source.analysis.llm_extract_irregularities --force     # redo all
python3 -m source.analysis.llm_extract_irregularities --dry-run   # preview
```

## When this skill triggers automatically

Consult this skill (even without explicit `/llmkit` invocation) whenever you're about to:
- Set up LLM-based structured extraction in any project
- Work with cached LLM outputs or cache metadata
- Write Pydantic schemas for LLM validation
- Design prompts for extraction tasks
- Implement audit/review workflows for LLM outputs
- Debug cache staleness or re-extraction issues

## Gotchas

- **Cache key excludes prompt** — by design. Don't add prompt to the key.
- **`model` in key vs `model_version` in metadata** — `model` is what you requested (e.g. "gpt-4o-mini"), `model_version` is what the API actually used (e.g. "gpt-4o-mini-2024-07-18"). Both are saved.
- **Legacy cache `_usage`** — old entries store `_usage` inside the extraction dict. The wrapper strips it out before validation. Don't rely on `_usage` being in `extraction` for new entries.
- **`ExtractionSchema` uses `ClassVar`** — not underscore-prefixed attrs (Pydantic v2 treats `_`-prefixed as private attrs, which aren't JSON-serializable).
- **`messages` stores the full API input** — each file is a self-contained audit record. Expect cache files to be large for long documents. Access document text via `entry.messages[1]["content"]`.
- **`diarios` moved** — the package is now at `~/research/packages/diarios/` (was `~/research/diarios/`). Imports unchanged.
