"""
Literature search tool: queries Semantic Scholar and OpenAlex APIs,
saves raw responses, merges candidates, downloads OA PDFs.

Usage:
    python literature_search.py search --queries queries.json --outdir docs/literature
    python literature_search.py fetch-pdfs --candidates docs/literature/candidates.json --outdir ~/Dropbox/slug/literature
    python literature_search.py cite-graph --doi 10.1086/699209 --outdir docs/literature

All API responses are saved as raw JSON for reproducibility.
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

SEMANTIC_SCHOLAR_FIELDS = (
    "title,authors,year,abstract,externalIds,citationCount,"
    "openAccessPdf,publicationTypes,journal,url"
)

OPENALEX_SELECT = (
    "id,doi,title,authorships,publication_year,cited_by_count,"
    "open_access,primary_location,abstract_inverted_index"
)


S2_API_KEY = os.environ.get("S2_API_KEY", "")

# Track last request time per domain to enforce rate limits
_last_request = {}


def _rate_limit(url, min_interval=1.1):
    """Enforce minimum interval between requests to the same domain."""
    from urllib.parse import urlparse
    domain = urlparse(url).netloc
    now = time.time()
    last = _last_request.get(domain, 0)
    wait = min_interval - (now - last)
    if wait > 0:
        time.sleep(wait)
    _last_request[domain] = time.time()


def _api_get(url, retries=3, delay=2.0):
    """GET with retry on 429."""
    for attempt in range(retries):
        _rate_limit(url)
        try:
            headers = {"User-Agent": "literature-search/1.0"}
            if S2_API_KEY and "semanticscholar.org" in url:
                headers["x-api-key"] = S2_API_KEY
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                wait = delay * (2 ** attempt)
                print(f"  Rate limited, waiting {wait:.0f}s...", file=sys.stderr)
                time.sleep(wait)
            else:
                print(f"  HTTP {e.code} for {url}", file=sys.stderr)
                return None
        except Exception as e:
            print(f"  Error: {e}", file=sys.stderr)
            return None
    return None


def search_semantic_scholar(query, limit=20):
    """Search Semantic Scholar API."""
    encoded = urllib.parse.quote(query)
    url = (
        f"https://api.semanticscholar.org/graph/v1/paper/search"
        f"?query={encoded}&limit={limit}&fields={SEMANTIC_SCHOLAR_FIELDS}"
    )
    return _api_get(url)


def search_openalex(query, limit=20):
    """Search OpenAlex API."""
    encoded = urllib.parse.quote(query)
    url = (
        f"https://api.openalex.org/works"
        f"?search={encoded}&per_page={limit}&select={OPENALEX_SELECT}"
    )
    return _api_get(url)


def get_citations(doi_or_id, direction="citations", limit=50):
    """Get papers citing or cited by a paper via Semantic Scholar."""
    if doi_or_id.startswith("10."):
        paper_id = f"DOI:{doi_or_id}"
    else:
        paper_id = doi_or_id
    url = (
        f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}"
        f"/{direction}?fields={SEMANTIC_SCHOLAR_FIELDS}&limit={limit}"
    )
    return _api_get(url)


def get_crossref_metadata(doi):
    """Get verified bibliographic metadata from Crossref."""
    encoded = urllib.parse.quote(doi, safe="")
    url = f"https://api.crossref.org/works/{encoded}"
    return _api_get(url)


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def _extract_doi(paper, source):
    """Extract DOI from a paper record."""
    if source == "semantic_scholar":
        eids = paper.get("externalIds") or {}
        return eids.get("DOI")
    elif source == "openalex":
        doi = paper.get("doi") or ""
        return doi.replace("https://doi.org/", "") if doi else None
    return None


def _normalize_authors(paper, source):
    """Extract author list as strings."""
    if source == "semantic_scholar":
        return [a.get("name", "") for a in (paper.get("authors") or [])]
    elif source == "openalex":
        return [
            a.get("author", {}).get("display_name", "")
            for a in (paper.get("authorships") or [])
        ]
    return []


def _reconstruct_abstract(inv_index):
    """Reconstruct abstract from OpenAlex inverted index."""
    if not inv_index:
        return None
    word_positions = []
    for word, positions in inv_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort()
    return " ".join(w for _, w in word_positions)


def normalize_paper(paper, source):
    """Convert to a common format."""
    doi = _extract_doi(paper, source)
    authors = _normalize_authors(paper, source)

    if source == "semantic_scholar":
        abstract = paper.get("abstract")
        year = paper.get("year")
        title = paper.get("title", "")
        citations = paper.get("citationCount", 0)
        oa_pdf = None
        oa_info = paper.get("openAccessPdf")
        if oa_info:
            oa_pdf = oa_info.get("url")
        journal_info = paper.get("journal") or {}
        journal = journal_info.get("name")
    elif source == "openalex":
        abstract = _reconstruct_abstract(paper.get("abstract_inverted_index"))
        year = paper.get("publication_year")
        title = paper.get("title", "")
        citations = paper.get("cited_by_count", 0)
        oa = paper.get("open_access") or {}
        oa_pdf = oa.get("oa_url")
        loc = paper.get("primary_location") or {}
        src = loc.get("source") or {}
        journal = src.get("display_name")
    else:
        return None

    return {
        "title": title,
        "authors": authors,
        "year": year,
        "doi": doi,
        "abstract": abstract,
        "citation_count": citations,
        "oa_pdf_url": oa_pdf,
        "journal": journal,
        "source_api": source,
    }


# ---------------------------------------------------------------------------
# Merging and deduplication
# ---------------------------------------------------------------------------

def _dedup_key(paper):
    """Generate dedup key from DOI or title hash."""
    if paper.get("doi"):
        return f"doi:{paper['doi'].lower()}"
    title = (paper.get("title") or "").lower().strip()
    return f"title:{hashlib.md5(title.encode()).hexdigest()}"


def merge_candidates(all_papers):
    """Deduplicate papers, preferring the record with more metadata."""
    seen = {}
    for p in all_papers:
        key = _dedup_key(p)
        if key in seen:
            existing = seen[key]
            # Prefer the one with abstract
            if not existing.get("abstract") and p.get("abstract"):
                seen[key] = p
            # Prefer higher citation count
            elif (p.get("citation_count") or 0) > (existing.get("citation_count") or 0):
                seen[key] = p
        else:
            seen[key] = p
    return list(seen.values())


# ---------------------------------------------------------------------------
# PDF downloading
# ---------------------------------------------------------------------------

def download_pdf(url, dest_path):
    """Download a PDF file."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "literature-search/1.0",
            "Accept": "application/pdf",
        })
        with urllib.request.urlopen(req, timeout=60) as resp:
            content_type = resp.headers.get("Content-Type", "")
            if "pdf" not in content_type and not url.endswith(".pdf"):
                print(f"  Skipping {url} — not a PDF (Content-Type: {content_type})", file=sys.stderr)
                return False
            with open(dest_path, "wb") as f:
                f.write(resp.read())
            return True
    except Exception as e:
        print(f"  Download failed for {url}: {e}", file=sys.stderr)
        return False


def make_citekey(paper):
    """Generate a citekey like 'olken2007' from paper metadata."""
    authors = paper.get("authors") or []
    if authors:
        first = authors[0].split()[-1].lower()
        # Remove non-ascii
        first = "".join(c for c in first if c.isalpha())
    else:
        first = "unknown"
    year = paper.get("year") or "nd"
    return f"{first}{year}"


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_search(args):
    """Run search queries and save results."""
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    with open(args.queries) as f:
        queries = json.load(f)

    # Load existing candidates if merging
    candidates_file = outdir / "candidates.json"
    all_papers = []
    if candidates_file.exists():
        with open(candidates_file) as f:
            all_papers = json.load(f)
        print(f"Loaded {len(all_papers)} existing candidates")

    search_log = {
        "timestamp": datetime.now().isoformat(),
        "queries": [],
    }

    for i, query in enumerate(queries):
        print(f"[{i+1}/{len(queries)}] Searching: {query}")
        search_entry = {"query": query, "results": {}}

        # Semantic Scholar
        ss_result = search_semantic_scholar(query, limit=args.limit)
        if ss_result:
            papers = ss_result.get("data") or []
            normalized = [normalize_paper(p, "semantic_scholar") for p in papers]
            normalized = [p for p in normalized if p]
            all_papers.extend(normalized)
            search_entry["results"]["semantic_scholar"] = len(papers)
            print(f"  Semantic Scholar: {len(papers)} results")
        else:
            search_entry["results"]["semantic_scholar"] = 0
            print(f"  Semantic Scholar: failed")

        # OpenAlex (rate limit handled by _rate_limit per domain)
        oa_result = search_openalex(query, limit=args.limit)
        if oa_result:
            papers = oa_result.get("results") or []
            normalized = [normalize_paper(p, "openalex") for p in papers]
            normalized = [p for p in normalized if p]
            all_papers.extend(normalized)
            search_entry["results"]["openalex"] = len(papers)
            print(f"  OpenAlex: {len(papers)} results")
        else:
            search_entry["results"]["openalex"] = 0
            print(f"  OpenAlex: failed")

        search_log["queries"].append(search_entry)

    # Deduplicate
    candidates = merge_candidates(all_papers)
    candidates.sort(key=lambda p: -(p.get("citation_count") or 0))

    # Save
    with open(candidates_file, "w") as f:
        json.dump(candidates, f, indent=2, ensure_ascii=False)

    with open(outdir / "search_log.json", "w") as f:
        json.dump(search_log, f, indent=2)

    print(f"\nDone: {len(candidates)} unique candidates saved to {candidates_file}")
    print(f"Search log saved to {outdir / 'search_log.json'}")


def cmd_cite_graph(args):
    """Fetch citation graph for one or more papers."""
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # Support multiple DOIs (comma-separated)
    dois = [d.strip() for d in args.doi.split(",")]

    new_papers = []
    for doi in dois:
        # Citing papers
        print(f"Fetching papers citing {doi}...")
        citations = get_citations(doi, "citations", limit=args.limit)
        if citations:
            citing = citations.get("data") or []
            for entry in citing:
                paper = entry.get("citingPaper") or entry
                norm = normalize_paper(paper, "semantic_scholar")
                if norm:
                    new_papers.append(norm)
            print(f"  Found {len(citing)} citing papers")

        # Referenced papers
        print(f"Fetching papers cited by {doi}...")
        references = get_citations(doi, "references", limit=args.limit)
        if references:
            refs = references.get("data") or []
            for entry in refs:
                paper = entry.get("citedPaper") or entry
                norm = normalize_paper(paper, "semantic_scholar")
                if norm:
                    new_papers.append(norm)
            print(f"  Found {len(refs)} referenced papers")

    # Merge with existing candidates
    candidates_file = outdir / "candidates.json"
    all_papers = []
    if candidates_file.exists():
        with open(candidates_file) as f:
            all_papers = json.load(f)

    all_papers.extend(new_papers)
    candidates = merge_candidates(all_papers)
    candidates.sort(key=lambda p: -(p.get("citation_count") or 0))

    with open(candidates_file, "w") as f:
        json.dump(candidates, f, indent=2, ensure_ascii=False)

    print(f"\nDone: {len(candidates)} total unique candidates (+{len(new_papers)} from citation graphs)")


def cmd_fetch_pdfs(args):
    """Download PDFs for curated papers.

    Expects a manifest JSON file: a list of objects with fields:
      - citekey: the bib citekey (used as filename)
      - doi: (optional) for proxy URL generation
      - oa_pdf_url: (optional) direct OA PDF link

    If --manifest is not provided, falls back to candidates.json and
    auto-generates citekeys (less reliable).
    """
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    if args.manifest:
        with open(args.manifest) as f:
            papers = json.load(f)
    else:
        # Fallback: use candidates.json with auto-generated citekeys
        with open(args.candidates) as f:
            papers = json.load(f)
        for p in papers:
            if "citekey" not in p:
                p["citekey"] = make_citekey(p)

    downloaded = 0
    skipped = 0
    failed = 0
    no_oa = 0
    proxy_urls = []

    for paper in papers:
        citekey = paper.get("citekey", make_citekey(paper))
        pdf_path = outdir / f"{citekey}.pdf"

        if pdf_path.exists():
            skipped += 1
            continue

        oa_url = paper.get("oa_pdf_url")
        if oa_url:
            print(f"  Downloading: {citekey} — {paper.get('title', '')[:60]}")
            if download_pdf(oa_url, str(pdf_path)):
                downloaded += 1
            else:
                failed += 1
                doi = paper.get("doi")
                if doi:
                    proxy_urls.append({
                        "citekey": citekey,
                        "title": paper.get("title"),
                        "doi": doi,
                        "proxy_url": f"http://ezproxy.library.bi.no/login?url=https://doi.org/{doi}",
                    })
        else:
            no_oa += 1
            doi = paper.get("doi")
            if doi:
                proxy_urls.append({
                    "citekey": citekey,
                    "title": paper.get("title"),
                    "doi": doi,
                    "proxy_url": f"http://ezproxy.library.bi.no/login?url=https://doi.org/{doi}",
                })

    # Save proxy URL list for paywalled papers
    if proxy_urls:
        proxy_file = outdir / "paywalled_urls.json"
        with open(proxy_file, "w") as f:
            json.dump(proxy_urls, f, indent=2, ensure_ascii=False)

    print(f"\nPDF download summary:")
    print(f"  Downloaded: {downloaded}")
    print(f"  Already existed: {skipped}")
    print(f"  Failed: {failed}")
    print(f"  No OA URL: {no_oa}")
    if proxy_urls:
        print(f"  Paywalled (proxy URLs saved): {len(proxy_urls)}")


def cmd_crossref_verify(args):
    """Verify and enrich candidates with Crossref metadata."""
    with open(args.candidates) as f:
        candidates = json.load(f)

    verified = 0
    for paper in candidates:
        doi = paper.get("doi")
        if not doi or paper.get("crossref_verified"):
            continue

        print(f"  Verifying: {doi}")
        meta = get_crossref_metadata(doi)
        if meta and "message" in meta:
            msg = meta["message"]
            paper["crossref_verified"] = True
            paper["crossref"] = {
                "title": msg.get("title", [None])[0],
                "container_title": msg.get("container-title", [None])[0],
                "volume": msg.get("volume"),
                "issue": msg.get("issue"),
                "page": msg.get("page"),
                "published": msg.get("published-print", {}).get("date-parts", [[None]])[0],
                "type": msg.get("type"),
            }
            verified += 1

    with open(args.candidates, "w") as f:
        json.dump(candidates, f, indent=2, ensure_ascii=False)

    print(f"\nVerified {verified} papers via Crossref")


# ---------------------------------------------------------------------------
# Bibliography audit (verify EXISTING .bib entries against Crossref)
#
# The discovery pipeline's hallucination guard is preventive ("never add a
# paper not returned by an API"). This is the complementary *detective* check:
# given a .bib that has accreted entries from many sources (coauthors, hand
# edits, Claude drafting the paper), flag entries whose metadata does not match
# the authoritative record. It REPORTS ONLY and never rewrites the bib — and
# every verdict comes from a live Crossref lookup, never from model memory
# (the whole point is to catch fabrications, not launder them).
# ---------------------------------------------------------------------------

_BIB_SHOULD_HAVE_DOI = {"article", "inproceedings", "incollection", "conference"}


def _bib_balanced(s, start):
    """s[start] must be '{'; return (inner_text, index_after_matching_'}')."""
    depth = 0
    for i in range(start, len(s)):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return s[start + 1:i], i + 1
    return s[start + 1:], len(s)


def _bib_field(body, name):
    """Extract one bib field, honoring brace nesting and quoted values."""
    m = re.search(r"\b" + name + r"\s*=\s*", body, re.I)
    if not m:
        return ""
    j = m.end()
    if j < len(body) and body[j] == "{":
        val, _ = _bib_balanced(body, j)
    elif j < len(body) and body[j] == '"':
        k = body.find('"', j + 1)
        val = body[j + 1:k] if k != -1 else body[j + 1:]
    else:
        mm = re.match(r"([^,\n}]+)", body[j:])
        val = mm.group(1) if mm else ""
    return re.sub(r"\s+", " ", val).strip()


def parse_bib(path):
    """Parse a .bib into [{key,type,title,author,year,doi,url,venue}]."""
    raw = Path(path).read_text(encoding="utf-8", errors="replace")
    out = []
    for m in re.finditer(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", raw):
        etype, key = m.group(1).lower(), m.group(2).strip()
        if etype in ("comment", "string", "preamble"):
            continue
        nxt = raw.find("\n@", m.end())
        body = raw[m.end(): nxt if nxt != -1 else len(raw)]
        out.append({
            "key": key, "type": etype,
            "title": _bib_field(body, "title"),
            "author": _bib_field(body, "author"),
            "year": _bib_field(body, "year"),
            "doi": _bib_field(body, "doi").replace("https://doi.org/", ""),
            "url": _bib_field(body, "url"),
            "venue": (_bib_field(body, "journal") or _bib_field(body, "booktitle")
                      or _bib_field(body, "publisher")),
        })
    return out


def extract_cited_keys(tex_paths):
    """Collect all \\cite{...} keys from the given .tex files."""
    keys = set()
    pat = re.compile(r"\\[a-zA-Z]*cite[a-zA-Z]*\s*(?:\[[^\]]*\]\s*)*\{([^}]*)\}")
    for p in tex_paths:
        try:
            txt = Path(p).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in pat.finditer(txt):
            for k in m.group(1).split(","):
                if k.strip():
                    keys.add(k.strip())
    return keys


def _norm_title(t):
    """Fold a title to a comparable ascii form. Handles LaTeX accent macros
    (\\c{c}, \\~a, \\'e, ...) and real Unicode diacritics so a bib entry with
    LaTeX accents matches Crossref's Unicode without false 'mismatch' flags."""
    t = t or ""
    t = re.sub(r"\\[a-zA-Z]\{([a-zA-Z])\}", r"\1", t)        # \c{c}, \u{g}, \v{s}
    t = re.sub(r"\\[`'^\"~=.]\{?([a-zA-Z])\}?", r"\1", t)    # \'e \~a \"o \^o \`a
    t = t.replace("{", "").replace("}", "").replace("\\", "")
    t = "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", t.lower())).strip()


def _first_author_family(author):
    if not author:
        return ""
    first = author.split(" and ")[0].strip().strip("{}")
    fam = first.split(",")[0] if "," in first else (first.split()[-1] if first.split() else first)
    return re.sub(r"[{}\\]", "", fam).strip().lower()


def _crossref_years(msg):
    years = set()
    for k in ("published-print", "published-online", "issued", "published"):
        dp = msg.get(k, {}).get("date-parts", [[None]])
        if dp and dp[0] and dp[0][0]:
            years.add(int(dp[0][0]))
    return years


def crossref_search_title(title, author=""):
    """Best-match Crossref search for a title (+ optional first author)."""
    q = urllib.parse.quote((title + " " + author).strip())
    return _api_get(f"https://api.crossref.org/works?query.bibliographic={q}&rows=3")


def _titles_match(a, b):
    na, nb = _norm_title(a), _norm_title(b)
    return bool(na) and bool(nb) and (na == nb or na[:40] in nb or nb[:40] in na)


def cmd_audit_bib(args):
    entries = parse_bib(args.bib)
    by_key = {e["key"]: e for e in entries}

    if args.cited_from:
        cited = extract_cited_keys(args.cited_from)
        targets = [by_key[k] for k in sorted(cited) if k in by_key]
        missing = sorted(cited - set(by_key))
        scope = f"{len(targets)} cited entries (of {len(entries)} in bib)"
    else:
        targets, missing = entries, []
        scope = f"all {len(entries)} entries"

    findings = []  # (severity, verdict, key, detail)
    for k in missing:
        findings.append(("HIGH", "MISSING-ENTRY", k, "cited in tex but absent from the bib"))

    for e in targets:
        key, title, year = e["key"], e["title"], e["year"]
        fam = _first_author_family(e["author"])
        if e["doi"]:
            meta = get_crossref_metadata(e["doi"])
            if not meta or "message" not in meta:
                findings.append(("HIGH", "DOI-UNRESOLVED", key,
                                 f"doi {e['doi']} did not resolve at Crossref"))
                continue
            msg = meta["message"]
            cr_title = (msg.get("title") or [""])[0]
            cr_fam = (msg.get("author") or [{}])[0].get("family", "").lower()
            if not _titles_match(title, cr_title):
                findings.append(("HIGH", "TITLE-MISMATCH", key,
                                 f"bib='{title[:55]}' | crossref='{cr_title[:55]}'"))
            elif cr_fam and fam and fam not in cr_fam and cr_fam not in fam:
                findings.append(("MED", "AUTHOR-MISMATCH", key,
                                 f"bib first author '{fam}' | crossref '{cr_fam}'"))
            else:
                yrs = _crossref_years(msg)
                ynum = int(re.sub(r"[^0-9]", "", year) or 0)
                if ynum and yrs and ynum not in yrs:
                    findings.append(("LOW", "YEAR-OFF", key,
                                     f"bib {year} | crossref {sorted(yrs)}"))
        else:
            hit = crossref_search_title(title, fam)
            items = ((hit or {}).get("message", {}) or {}).get("items", [])
            found = None
            if items and _titles_match(title, (items[0].get("title") or [""])[0]):
                found = items[0].get("DOI")
            if found:
                findings.append(("INFO", "DOI-FOUND", key,
                                 f"Crossref match has DOI {found} (verify, consider adding)"))
            elif e["type"] in _BIB_SHOULD_HAVE_DOI:
                findings.append(("HIGH", "SUSPECT", key,
                                 f"@{e['type']} with no DOI and no Crossref title match "
                                 "-- possible hallucination; verify by hand"))
            else:
                findings.append(("INFO", "NO-DOI-MANUAL", key,
                                 f"@{e['type']} ({e['venue'][:28]}); verify URL/source by hand"))

    rank = {"HIGH": 0, "MED": 1, "LOW": 2, "INFO": 3}
    findings.sort(key=lambda f: (rank[f[0]], f[2]))

    if args.json:
        print(json.dumps([{"severity": s, "verdict": v, "key": k, "detail": d}
                          for s, v, k, d in findings], indent=2, ensure_ascii=False))
    else:
        print(f"Bib audit: {scope}\n" + "=" * 70)
        for sev, verdict, key, detail in findings:
            print(f"  [{sev:4}] {verdict:15} {key}")
            print(f"         {detail}")
        counts = {s: sum(1 for f in findings if f[0] == s) for s in rank}
        print("-" * 70)
        print(f"{len(targets)} checked | HIGH {counts['HIGH']} | MED {counts['MED']} "
              f"| year-notes {counts['LOW']} | info {counts['INFO']}")
        if counts["HIGH"]:
            print("\nHIGH items are possible hallucinations or wrong metadata -- "
                  "verify each against the source before trusting the entry.")
    return 1 if any(f[0] == "HIGH" for f in findings) else 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Literature search tool")
    sub = parser.add_subparsers(dest="command")

    # search
    p_search = sub.add_parser("search", help="Run search queries")
    p_search.add_argument("--queries", required=True, help="JSON file with list of query strings")
    p_search.add_argument("--outdir", required=True, help="Output directory for results")
    p_search.add_argument("--limit", type=int, default=50, help="Results per query per API")

    # cite-graph
    p_cite = sub.add_parser("cite-graph", help="Fetch citation graph for a paper")
    p_cite.add_argument("--doi", required=True, help="DOI of the seed paper")
    p_cite.add_argument("--outdir", required=True, help="Output directory")
    p_cite.add_argument("--limit", type=int, default=50, help="Max citations to fetch")

    # fetch-pdfs
    p_pdf = sub.add_parser("fetch-pdfs", help="Download OA PDFs")
    p_pdf.add_argument("--candidates", default=None, help="Path to candidates.json (fallback if no manifest)")
    p_pdf.add_argument("--manifest", default=None, help="Path to manifest.json with citekeys and OA URLs")
    p_pdf.add_argument("--outdir", required=True, help="Directory for PDFs")

    # crossref-verify
    p_verify = sub.add_parser("crossref-verify", help="Verify DOIs via Crossref")
    p_verify.add_argument("--candidates", required=True, help="Path to candidates.json")

    # audit-bib
    p_audit = sub.add_parser(
        "audit-bib",
        help="Audit an existing .bib for hallucinated/wrong entries (reports, never edits)")
    p_audit.add_argument("--bib", required=True, help="Path to the .bib file to audit")
    p_audit.add_argument("--cited-from", nargs="+", default=None,
                         help="One or more .tex files; audit only keys cited there "
                              "(default: audit every entry in the bib)")
    p_audit.add_argument("--json", action="store_true", help="Emit findings as JSON")

    args = parser.parse_args()
    if args.command == "search":
        cmd_search(args)
    elif args.command == "cite-graph":
        cmd_cite_graph(args)
    elif args.command == "fetch-pdfs":
        cmd_fetch_pdfs(args)
    elif args.command == "crossref-verify":
        cmd_crossref_verify(args)
    elif args.command == "audit-bib":
        sys.exit(cmd_audit_bib(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
