---
name: literature
description: "Discover academic literature for a project: search APIs, curate relevant papers, write literature.md + bib entries, download PDFs. Use when user wants to find, update, or expand a project's literature review."
user_invocable: true
---

# Literature Discovery

Search academic databases, curate relevant papers, and populate a project's
`docs/literature.md`, bib file, and PDF collection.

## Arguments

- `/literature [project-slug]` — run full pipeline for a project
- `/literature [project-slug] --refresh` — re-run searches, merge with existing candidates
- `/literature [project-slug] --fetch-pdfs` — only download PDFs for already-curated papers
- `/literature [project-slug] --cite-graph DOI` — expand candidates via citation graph of a specific paper

If no project slug is given, infer from the current working directory.

## Pipeline overview

```
1. Read context  →  2. Generate queries  →  3. API search
                                                  ↓
4. First curation (Claude)  →  5. Citation graph on key papers  →  6. Second curation
                                                                          ↓
7. Write literature.md + bib  →  8. Download PDFs
```

## Step-by-step

### 1. Find workspace root and project

Locate `$ROOT` by searching upward for `CLAUDE.md` next to `projects/` and `pipelines/`.
Resolve the project path: `$ROOT/projects/{slug}/`.

Read these files to build project context:
- `docs/summary.md` (required)
- `docs/thinking.md`
- `docs/methods.md`
- `docs/hypotheses.md`
- `docs/institutions.md`
- `docs/literature.md` (existing entries)
- `paper/*.tex` (if exists, scan for `\cite{}` keys)
- `paper/references.bib` or `paper/library.bib` (existing bib entries)

### 2. Generate search queries

From the project context, generate 10–20 search queries covering:
- The core research question
- The identification strategy / methods
- The institutional setting
- Key theoretical mechanisms
- Adjacent literatures that the paper should cite or position against

Save queries to `docs/literature/queries.json` as a JSON array of strings.

### 3. Run API searches

```bash
python3 $ROOT/research/tools/literature_search.py search \
    --queries $PROJECT/docs/literature/queries.json \
    --outdir $PROJECT/docs/literature
```

Saves:
- `docs/literature/candidates.json` — merged, deduplicated candidates with abstracts
- `docs/literature/search_log.json` — queries, timestamps, result counts

The script merges with any existing `candidates.json`, so re-running is safe.

### 4. First curation (Claude)

Read `candidates.json`. Skim titles and abstracts. Identify:
- The 20–60 **genuinely relevant** papers
- The 5–10 **most central** papers (for citation graph expansion)

**Important:** Do NOT invent or hallucinate paper details. Every paper in the final
output must come from `candidates.json` (i.e., from an API response).

### 5. Citation graph expansion on key papers

For the 5–10 most central papers identified in step 4, expand via citation graphs.
Pass multiple DOIs comma-separated:

```bash
python3 $ROOT/research/tools/literature_search.py cite-graph \
    --doi 10.xxxx/yyyy,10.aaaa/bbbb,10.cccc/dddd \
    --outdir $PROJECT/docs/literature
```

This fetches papers that cite and are cited by each key paper, and merges
them into `candidates.json`.

### 6. Second curation (Claude)

Re-read the now-expanded `candidates.json`. Check the newly added papers
from citation graphs for relevance. This catches important papers that
keyword search missed but are one hop from the core literature.

### 7. Write literature.md and bib entries

Update `docs/literature.md` following the project docs contract format.
Include a `file:` field for each paper so the PDF is easy to locate:
```markdown
## Topic heading

- Author (Year) "Title"
  - topic: what the paper is about
  - relevance: why it matters for this project
  - file: citekey.pdf
```

The `file:` field uses the **bib citekey** as the filename (e.g., `avis2018government.pdf`).
This ensures PDFs, bib entries, and literature.md all use the same identifier.

#### Citekey convention

Citekeys follow the format `{author}{year}{word}`, all lowercase, no separators:

- **`{author}`** — first author's last name only. No `EtAl`, no coauthor names.
  Hyphenated names collapse the hyphen: `Genicolo-Martins` → `genicolomartins`.
  Particles stay attached: `Della Porta` → `dellaporta`, `Di Tella` → `ditella`.
- **`{year}`** — four-digit publication year.
- **`{word}`** — first substantive word of the title (lowercase). Skip articles
  and prepositions: *a, an, the, of, in, on, for, and, to, do, how, is, are, as*.
  Examples: "The Spoils of Victory" → `spoils`; "Do Government Audits
  Reduce Corruption?" → `government`.
- **Institutional authors:** lowercase the institution: `oecd2016preventing`,
  `worldbank2020procurement`.
- **Disambiguation:** if two papers produce the same key (same first author,
  year, and first substantive word), use the **second** substantive title word
  instead. If still ambiguous, concatenate the first two: `decarolis2022rules`
  vs `decarolis2022corruption`.

For bib entries:
- Prefer metadata from Crossref (run `crossref-verify` if needed)
- If Crossref is unavailable, use API metadata but flag as unverified
- Add new entries to existing `paper/references.bib` or `paper/library.bib`
- Do NOT overwrite existing entries — only append new ones

### 8. Create PDF manifest and download

After writing literature.md and bib entries, create a manifest file at
`docs/literature/manifest.json` — a JSON array of objects with:
```json
[
  {
    "citekey": "avis2018government",
    "title": "Do Government Audits Reduce Corruption?",
    "doi": "10.1086/699209",
    "oa_pdf_url": "https://..."
  }
]
```

The citekey must match the bib entry key exactly. To populate `oa_pdf_url`,
look up each paper's DOI in `candidates.json` for the OA URL. Also populate
`doi` for every paper — look up DOIs manually for papers where candidates.json
has none (working papers, older papers, etc.).

#### 8a. Check existing PDFs first

Before downloading anything, check if PDFs already exist locally. Many papers
will already be in the shared literature folder or other project folders:

```bash
# Check shared literature folder
ls ~/Dropbox/literature/ | grep -i {author-name}

# Check other project literature folders
find ~/Dropbox/*/literature/ -iname "*{author}*" 2>/dev/null
```

Copy any matches to the project's literature folder with the correct citekey name:
```bash
cp ~/Dropbox/literature/"Author - Year - Title.pdf" ~/Dropbox/{project-folder}/literature/{citekey}.pdf
```

#### 8b. Download OA and preprint PDFs

Determine the Dropbox path for the project:
```bash
ls ~/Dropbox/ | grep -i {slug-or-keywords}
```

Create `literature/` subdirectory if needed. Then run:
```bash
python3 $ROOT/research/tools/literature_search.py fetch-pdfs \
    --manifest $PROJECT/docs/literature/manifest.json \
    --outdir ~/Dropbox/{project-folder}/literature
```

This downloads OA PDFs and saves paywalled URLs. PDFs are named
`{citekey}.pdf` — matching the bib key and the `file:` field in literature.md.

#### 8c. Download paywalled PDFs (requires campus network)

Programmatic HTTP clients (Python requests, curl, wget, headless browsers)
**cannot download paywalled PDFs** — publishers use bot detection that blocks
everything except real browser sessions, even from authorized university IPs.

The only reliable method is to use the user's actual Chrome browser. To do this:

1. **Set Chrome to auto-download PDFs** via system policy (survives restarts,
   takes effect immediately after policy reload):
   ```bash
   sudo mkdir -p /etc/opt/chrome/policies/managed
   echo '{"AlwaysOpenPdfExternally":true,"DownloadDirectory":"/path/to/literature/folder"}' \
     | sudo tee /etc/opt/chrome/policies/managed/download_pdf.json
   ```
   The user needs to run this with sudo (use `! sudo ...` from the prompt).
   Verify at `chrome://policy` → click "Reload policies".

2. **Generate an HTML download page** at `/tmp/download_papers.html` that uses
   `<a target="_blank">` clicks to open each PDF URL. With the policy active,
   Chrome downloads the PDF instead of displaying it. Use DOI URLs
   (`https://doi.org/...`) for publisher papers — direct PDF URLs often 404.
   Use direct links only for NBER, SSRN, arXiv preprints.

   Structure the page with a "Download All" button that clicks each link
   sequentially with ~4s delays. Group papers into:
   - Direct PDF links (NBER, SSRN, arXiv) — auto-download
   - DOI links (publisher articles) — opens article page, user clicks PDF button
   - Books/working papers without URLs — skip

3. **Rename downloaded files** after the user confirms downloads are complete.
   Publishers use their own filenames (e.g., `w31266.pdf`, `rest_a_01101.pdf`,
   `1-s2.0-S030440762030378X-main.pdf`). Write a rename script that maps
   publisher filenames to citekeys.

4. **Clean up**: Remove the Chrome policy and restore settings when done:
   ```bash
   sudo rm /etc/opt/chrome/policies/managed/download_pdf.json
   ```

If the user is **not on campus**, skip paywalled downloads and report which
papers need to be downloaded later from the campus network.

Report to the user:
- How many PDFs were found locally (from shared folders)
- How many OA PDFs were downloaded
- How many paywalled PDFs were downloaded via browser
- How many are still missing (with reasons: book, no URL, no access)

## Directory structure

After running, the project should have:
```
project/
  docs/
    literature.md                        # curated, annotated (with file: fields)
    literature/
      queries.json                       # search queries used
      candidates.json                    # all API results merged + deduplicated
      search_log.json                    # timestamps and counts
      manifest.json                      # curated papers with citekeys + OA URLs
  paper/
    references.bib or library.bib        # bib entries (existing + new)
```

And in Dropbox:
```
~/Dropbox/{project-folder}/literature/
  {citekey}.pdf                          # named after bib key (e.g., avis2018government.pdf)
  paywalled_urls.json                    # URLs for manual download on campus
```

The naming chain: `literature.md` → `file: avis2018government.pdf` → bib key
`@article{avis2018government, ...}` → PDF `avis2018government.pdf`. One identifier
across all three locations.

## Gotchas

- **Rate limits:** Semantic Scholar allows ~100 req/sec unauthenticated but can
  throttle. The script has built-in retry with backoff. If many queries fail,
  wait a few minutes and re-run with `--refresh`.
- **Hallucination prevention:** Never add a paper to literature.md that is not in
  `candidates.json`. All metadata must come from APIs, not from Claude's memory.
  If a paper seems relevant but wasn't found by the APIs, add it to queries and
  re-search rather than inventing the entry.
- **Existing literature.md:** When updating, merge with existing entries. Do not
  remove entries that were previously curated — only add new ones.
- **Bib entry quality:** Crossref metadata is authoritative. If `crossref-verify`
  fails for a DOI, flag the entry with a `% UNVERIFIED` comment in the bib file.
- **PDF downloads:** Some OA URLs point to HTML landing pages, not PDFs. The script
  checks Content-Type and skips non-PDFs. These will appear in the paywalled list.
- **Paywalled PDFs cannot be downloaded programmatically.** Python requests, curl,
  headless Chromium (Playwright/Selenium), and even headless Chrome with copied
  user profiles all get blocked by publisher bot detection (403 errors). The only
  method that works is the user's actual Chrome browser with the
  `AlwaysOpenPdfExternally` policy set. Do not waste time trying programmatic
  approaches — go straight to the HTML download page method.
- **Chrome Preferences vs policies:** Editing `~/.config/google-chrome/Default/Preferences`
  while Chrome is running has no effect — Chrome holds prefs in memory and overwrites
  the file on exit. Use `/etc/opt/chrome/policies/managed/*.json` instead, which
  takes effect after clicking "Reload policies" on `chrome://policy`. Policies
  require sudo to write.
- **Chrome PDF viewer vs download:** By default Chrome renders PDFs inline in
  iframes and tabs. The `AlwaysOpenPdfExternally` policy only applies to
  **top-level navigation**, not iframes. The download page must use `<a>` clicks
  with `target="_blank"`, not iframes or `fetch()`.
- **Publisher filename renaming:** Publishers save PDFs with their own names
  (e.g., `w31266.pdf`, `rest_a_01101.pdf`, Elsevier PII codes). After each
  download round, check for new files and rename to citekey format. Some
  downloaded files may be wrong (appendices, unrelated papers from mismatched
  DOIs) — verify file size and spot-check with `pdftotext`.
- **Check existing PDFs first:** `~/Dropbox/literature/` contains ~4000 PDFs
  from prior work. Always search there before downloading. Filenames follow
  the pattern `Author - Year - Title.pdf`.
- **Dropbox folder naming:** Project Dropbox folders may not match the git slug
  exactly. Always `ls ~/Dropbox/` and find the right folder before writing.
- **Git tracking:** `docs/literature/` (candidates.json, queries, search log) should
  be committed to git. PDFs should NOT be in git — they go to Dropbox only.
- **Clean up Chrome policy** after downloading — remove
  `/etc/opt/chrome/policies/managed/download_pdf.json` so Chrome returns to
  normal PDF viewing behavior.
