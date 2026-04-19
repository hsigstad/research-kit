# diarios — API Summary

Module inventory for the shared `diarios` Python package. Updated 2026-02-27.

Check here before writing new utilities — the function you need may already exist.

---

## Top-level exports

```python
from diarios import CaseParser, DiarioParser, parse_diario_extract, inspect, Extractor, query, normalize_datajud
```

---

## Core modules

### `diarios.database`
Database connection and query utilities (SQLite, MySQL, PostgreSQL).
- `query()` — execute SQL, return DataFrame
- `insert()` — insert data into database
- `connect()` / `get_db_engine()` / `get_postgresql_engine()` — connection helpers
- `create_index()` — create database indexes

### `diarios.extract`
Regex-based text extraction from files using pcre2grep.
- `Extractor` class — extract text matching PCRE2 regex patterns from files

### `diarios.io`
File reading and OCR utilities for PDF, DOCX, DOC.
- `read_files()` / `read_file()` — read files into DataFrame
- `extract_pdf_text()` / `extract_docx_text()` / `extract_doc_text()` — format-specific extraction
- `ocr_file()` / `ocr_image()` — OCR utilities

### `diarios.parse`
Court case and diary parsers.
- `CaseParser` class — parse court cases with customizable regex, cleaners, text processing
- `parse_diario_extract()` — parse diary extracts
- `extract_regexes()` / `extract_keywords()` — pattern extraction
- `inspect()` — inspection utility
- `add_oab()` / `split_name_oab()` — OAB lawyer number utilities

### `diarios.politica`
Political data utilities.
- `split_coalition()` — split coalition strings into party names
- `get_district()` — determine electoral district
- `get_office_type()` — classify offices (proportional vs majority)

### `diarios.structure`
Hierarchical text parser using regex-based structure definitions.
- `Structure` class — tree node for hierarchically structured text
- `parse()` — parse hierarchical text

### `diarios.close_election`
Close-election RDD utilities.
- `is_close()` — identify candidates in close elections for RD analysis

---

## `diarios.clean` submodule

### `clean.text`
Core text cleaning and DataFrame utilities.
- `clean_text()` — clean text (character removal, case, accents)
- `clean_text_columns()` / `clean_diario_text()` — DataFrame text cleaning
- `get_data()` — load reference data files
- `get_estado_mapping()` — state mapping
- `map_regex()` / `remove_regexes()` / `extract_series()` / `extractall_series()` — regex utilities
- `add_leads_and_lags()` — panel data lag/lead construction
- `generate_id()` — ID generation
- `read_csv()` — CSV reader with defaults

### `clean.numbers`
Case number cleaning and numeric parsing.
- `clean_number()` / `clean_cnj_number()` / `is_cnj_number()` — CNJ case number utilities
- `get_verificador_cnj()` — CNJ check digit
- `convert_number_antigo()` — old-to-new format conversion
- `get_tribunal()` / `get_filing_year()` / `extract_info_from_case_numbers()` — case number metadata
- `clean_reais()` / `parse_brl()` — **Brazilian currency (BRL) parsing**
- `clean_cpf()` — CPF tax ID cleaning
- `clean_oab()` — OAB lawyer number cleaning
- `clean_integer()` — integer parsing

### `clean.legal`
Legal domain cleaning and extraction.
- `clean_parte()` / `clean_parte_key()` / `clean_tipo_parte()` — party name cleaning
- `clean_classe()` — case class normalization
- `clean_decision()` / `get_decision()` — decision text cleaning
- `get_procedencia()` / `get_plaintiffwins()` — outcome extraction
- `clean_valor()` / `clean_date()` — value and date parsing
- `extract_fundamentos()` / `get_alinea_paragrafo()` — legal grounds extraction
- `load_datajud_jsonl()` / `normalize_datajud()` — DataJud data loading

### `clean.geo`
Geographic data and court classes.
- `TRT` / `TRF` classes — Regional Labor/Federal Court representations
- `clean_estado()` / `get_capital()` — state utilities
- `extract_municipio()` / `clean_municipio()` / `get_municipio_id()` — **municipality normalization**
- `clean_comarca()` / `clean_vara()` — court jurisdiction cleaning
- `get_foro_id()` / `get_foro()` / `get_foro_info()` — forum utilities
- `get_comarca_id()` / `get_comarca()` — comarca utilities

---

## `diarios.decision` submodule

Court ruling parser.
- `DecisionParser` class — parse court rulings into structured components
- `clean_sentenca_text()` — sentence text cleaning
- `get_main_sentence_regexes()` / `get_dispositivo_regexes()` / `get_desfecho_regexes()` — ruling section extraction
- `get_pena_regexes()` — penalty extraction

---

## `diarios.consulta` submodule

Parsers for scraped court docket data (tribunal-specific).

### `consulta.TJSP`
- `parse_consulta_tjsp_from_zip()` → (proc, mov, parte, adv)

### `consulta.STF`
- `parse_consulta_stf()` → (df, proc, parte, adv, mov, decisao, deslocamento, pauta)

### `consulta.STJ`
- `parse_consulta_stj()` → (df, proc, parte, mov, adv, decisao, peticao, pauta)

### `consulta.TRF1`
- `parse_consulta_trf1()` → (df, proc, mov, parte, adv, pub, it, peticao)

---

## Common patterns for reuse

When you need to... | Use...
---|---
Parse BRL currency | `diarios.clean.numbers.clean_reais()`
Normalize municipality names | `diarios.clean.geo.clean_municipio()`
Clean CNJ case numbers | `diarios.clean.numbers.clean_cnj_number()`
Clean party names | `diarios.clean.legal.clean_parte()`
Parse TJSP docket data | `diarios.consulta.TJSP.parse_consulta_tjsp_from_zip()`
Extract text from PDFs | `diarios.io.extract_pdf_text()`
Determine plaintiff win | `diarios.clean.legal.get_plaintiffwins()`
Add leads/lags to panel | `diarios.clean.text.add_leads_and_lags()`
