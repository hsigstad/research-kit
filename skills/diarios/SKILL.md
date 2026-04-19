---
name: diarios
description: "Reference for the shared diarios Python module — API lookup, usage patterns, and gotchas. Use when writing code that involves court data, legal text parsing, Brazilian administrative data cleaning, or when checking if a utility already exists before writing a new one."
user_invocable: true
---

# diarios Module Reference

The `diarios` package is a shared Python module used across projects for Brazilian court and administrative data processing. **Always check here before writing new utility functions.**

## Quick API reference

The workspace root contains `CLAUDE.md` alongside `projects/`, `pipelines/`, `diarios/`, `research/`. If the current directory is inside a project or pipeline, search upward to find the root.

Read `$ROOT/research/meta/diarios_api.md` for the full module inventory. Key areas:

### Text & Data Cleaning (`diarios.clean.text`)
- `clean_text()` — clean text (character removal, case, accents)
- `map_regex()` / `remove_regexes()` / `extract_series()` — regex utilities
- `add_leads_and_lags()` — panel data lag/lead construction
- `read_csv()` — CSV reader with sensible defaults

### Number & ID Cleaning (`diarios.clean.numbers`)
- `clean_cnj_number()` / `is_cnj_number()` — CNJ case number normalization
- `clean_reais()` / `parse_brl()` — Brazilian currency parsing
- `clean_cpf()` — CPF tax ID cleaning
- `clean_oab()` — OAB lawyer number cleaning
- `get_tribunal()` / `get_filing_year()` — extract metadata from case numbers

### Legal Domain (`diarios.clean.legal`)
- `clean_parte()` / `clean_parte_key()` — party name cleaning
- `clean_classe()` — case class normalization
- `get_procedencia()` / `get_plaintiffwins()` — outcome extraction
- `load_datajud_jsonl()` / `normalize_datajud()` — DataJud data loading

### Geography (`diarios.clean.geo`)
- `TRT` / `TRF` classes — Regional Labor/Federal Court representations
- `clean_municipio()` / `get_municipio_id()` — municipality normalization
- `clean_comarca()` / `clean_vara()` — court jurisdiction cleaning

### Court Parsing (`diarios.parse`)
- `CaseParser` class — parse court cases with customizable regex
- `parse_diario_extract()` — parse diary extracts
- `inspect()` — inspection utility

### Court Docket Parsers (`diarios.consulta`)
- `consulta.TJSP` — `parse_consulta_tjsp_from_zip()`
- `consulta.STF` — `parse_consulta_stf()`
- `consulta.STJ` — `parse_consulta_stj()`
- `consulta.TRF1` — `parse_consulta_trf1()`

### Decision Parsing (`diarios.decision`)
- `DecisionParser` class — parse court rulings into structured components

### Other
- `diarios.database` — `query()`, `insert()`, `connect()`
- `diarios.io` — `read_files()`, `extract_pdf_text()`, `ocr_file()`
- `diarios.politica` — `split_coalition()`, `get_district()`, `get_office_type()`
- `diarios.close_election` — `is_close()` for RDD analysis

## Common patterns

| When you need to... | Use... |
|---|---|
| Parse BRL currency | `diarios.clean.numbers.clean_reais()` |
| Normalize municipality names | `diarios.clean.geo.clean_municipio()` |
| Clean CNJ case numbers | `diarios.clean.numbers.clean_cnj_number()` |
| Clean party names | `diarios.clean.legal.clean_parte()` |
| Parse TJSP docket data | `diarios.consulta.TJSP.parse_consulta_tjsp_from_zip()` |
| Extract text from PDFs | `diarios.io.extract_pdf_text()` |
| Determine plaintiff win | `diarios.clean.legal.get_plaintiffwins()` |
| Add leads/lags to panel | `diarios.clean.text.add_leads_and_lags()` |

## Gotchas

- **Always import from the specific submodule**, not top-level, for non-exported functions. E.g., `from diarios.clean.numbers import clean_reais`, not `from diarios import clean_reais`.
- **Top-level exports are limited to:** `CaseParser, DiarioParser, parse_diario_extract, inspect, Extractor, query, normalize_datajud`. Everything else requires submodule imports.
- **Do NOT duplicate diarios functionality.** If you're about to write a function for cleaning CPFs, parsing case numbers, normalizing municipalities, etc. — check this reference first. The function almost certainly exists.
- **Do NOT modify diarios** unless the user explicitly instructs you to. If you find a bug or need an enhancement, flag it to the user.
- The module has **optional dependencies**: `ocr` (pytesseract, pdf2image) and `db` (SQLAlchemy). Code using these features needs the optional extras installed.
- `map_regex()` returns the **first match** — order patterns most-specific-first.
- `clean_municipio()` and `clean_parte()` handle accent removal internally via Unidecode — don't pre-clean accents before calling them.
- For the full source code, read files in `$ROOT/diarios/diarios/`. For the API summary, read `$ROOT/research/meta/diarios_api.md`.

## When this skill triggers automatically

This skill should be consulted (even without explicit `/diarios` invocation) whenever you're about to:
- Write a new text cleaning function for Brazilian data
- Parse court case numbers or docket data
- Clean party names, CPFs, OAB numbers, or municipality names
- Work with DataJud data
- Extract text from PDFs or perform OCR
- Build panel data with leads/lags

Before writing new code, check if `diarios` already has the function you need.
