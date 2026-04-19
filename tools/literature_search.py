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
import sys
import time
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

    args = parser.parse_args()
    if args.command == "search":
        cmd_search(args)
    elif args.command == "cite-graph":
        cmd_cite_graph(args)
    elif args.command == "fetch-pdfs":
        cmd_fetch_pdfs(args)
    elif args.command == "crossref-verify":
        cmd_crossref_verify(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
