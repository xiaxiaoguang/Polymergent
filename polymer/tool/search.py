
"""
Cheap paper search + fetch.

Cost:
  - Uses Claude Haiku 4.5 instead of Sonnet for search/fetch.
  - Resolves DOI -> open PDF via public APIs *before* calling Anthropic web_fetch.
    That avoids science.org / nature.com paywalls and wasted tokens.

Public APIs used (no publisher scrape):
  1. Unpaywall   GET https://api.unpaywall.org/v2/{doi}?email=...
  2. OpenAlex    GET https://api.openalex.org/works/https://doi.org/{doi}
  3. Semantic Scholar  GET https://api.semanticscholar.org/graph/v1/paper/{doi}
  4. arXiv abs rewrite when the URL is already an arXiv pdf

Set UNPAYWALL_EMAIL (required by Unpaywall) and optionally
SEMANTIC_SCHOLAR_API_KEY / OPENALEX_API_KEY for higher rate limits.
"""

from __future__ import annotations

import hashlib
import os
import re
from difflib import SequenceMatcher
from typing import Optional
from urllib.parse import quote

import anthropic
import requests

# ---------------------------------------------------------------------------
# Models: cheap by default. Override with env if you want.
# ---------------------------------------------------------------------------
SEARCH_MODEL = os.getenv("PAPER_SEARCH_MODEL", "claude-haiku-4-5-20251001")
FETCH_MODEL = os.getenv("PAPER_FETCH_MODEL", "claude-haiku-4-5-20251001")

# Unpaywall requires a contact email. Use a real one.
UNPAYWALL_EMAIL = os.getenv("UNPAYWALL_EMAIL", "research@example.com")
S2_API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")
OPENALEX_API_KEY = os.getenv("OPENALEX_API_KEY", "")

_HTTP_TIMEOUT = 12
_HTTP_HEADERS = {
    "User-Agent": "cheap-paper-tools/1.0 (mailto:%s)" % UNPAYWALL_EMAIL
}

_client = anthropic.Anthropic()

# ---------------------------------------------------------------------------
# Budgets + caches (same idea as your original code)
# ---------------------------------------------------------------------------
_SEARCH_CACHE: dict[str, str] = {}
_SEARCH_COUNT = 0
_SEARCH_BUDGET = 10
_RECENT_QUERIES: list[str] = []

_FETCH_CACHE: dict[str, str] = {}
_FETCH_COUNT = 0
_FETCH_BUDGET = 20
_FETCH_RECENT: list[str] = []

# Hosts Anthropic web_fetch may open. Include metadata APIs + OA hosts.
_FETCH_DOMAIN_SUFFIXES = (
    "arxiv.org",
    "export.arxiv.org",
    "arxiv-export-lb.library.cornell.edu",
    "doi.org",
    "dx.doi.org",
    "api.crossref.org",
    "crossref.org",
    "api.unpaywall.org",
    "unpaywall.org",
    "api.semanticscholar.org",
    "semanticscholar.org",
    "pdfs.semanticscholar.org",
    "api.openalex.org",
    "openalex.org",
    "biorxiv.org",
    "chemrxiv.org",
    "medrxiv.org",
    "ssrn.com",
    "plos.org",
    "nih.gov",
    "ncbi.nlm.nih.gov",
    "pubmed.ncbi.nlm.nih.gov",
    "pmc.ncbi.nlm.nih.gov",
    "europepmc.org",
    "par.nsf.gov",
    "mdpi.com",
    "frontiersin.org",
    "springeropen.com",
    "nature.com",          # only after OA resolver says it is free
    "science.org",
    "sciencemag.org",
    "pnas.org",
    "rsc.org",
    "rsc.li",
    "acs.org",
    "wiley.com",
    "springer.com",
    "cell.com",
    "elsevier.com",
    "sciencedirect.com",
    "tandfonline.com",
    "oup.com",
    "academic.oup.com",
    "ieee.org",
    "ieeexplore.ieee.org",
    "acm.org",
    "dl.acm.org",
    "researchgate.net",
    "iop.org",
    "aip.org",
    "aps.org",
    "beilstein-journals.org",
    "zenodo.org",
    "osti.gov",
    "hal.science",
    "escholarship.org",
)

# Paywalled publishers: never fetch these hosts directly.
# Resolve an OA copy first.
_PAYWALL_HINTS = (
    "science.org",
    "sciencemag.org",
    "nature.com",
    "cell.com",
    "sciencedirect.com",
    "elsevier.com",
    "wiley.com",
    "springer.com",
    "tandfonline.com",
    "oup.com",
    "academic.oup.com",
    "ieee.org",
    "ieeexplore.ieee.org",
    "acm.org",
    "dl.acm.org",
    "acs.org",
)

_URL_RE = re.compile(r"^https?://[^\s<>\"']+$", re.I)
_BARE_DOI_RE = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Z0-9]+$", re.I)
_DOI_IN_TEXT_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.I)


def reset_search_budget(n: int = 3) -> None:
    """Call this at the start of each new user task."""
    global _SEARCH_COUNT, _RECENT_QUERIES, _SEARCH_BUDGET
    global _FETCH_COUNT, _FETCH_RECENT
    _SEARCH_COUNT = 0
    _RECENT_QUERIES = []
    _FETCH_COUNT = 0
    _FETCH_RECENT = []
    _SEARCH_BUDGET = n


def _norm(q: str) -> str:
    q = q.lower()
    q = re.sub(r"[^a-z0-9\s\+\-\[\]]+", " ", q)
    q = re.sub(r"\s+", " ", q).strip()
    return q


def _too_similar(q: str, recent: list[str], threshold: float) -> Optional[str]:
    nq = _norm(q)
    for prev in recent:
        if SequenceMatcher(None, nq, _norm(prev)).ratio() >= threshold:
            return prev
    return None


def _host(url: str) -> str:
    m = re.match(r"^https?://([^/]+)", url, re.I)
    return (m.group(1) if m else "").lower().split(":")[0]


def _allowed_host(host: str) -> bool:
    host = host.lower().removeprefix("www.")
    return any(host == d or host.endswith("." + d) for d in _FETCH_DOMAIN_SUFFIXES)


def _is_paywall_host(host: str) -> bool:
    host = host.lower().removeprefix("www.")
    return any(host == d or host.endswith("." + d) for d in _PAYWALL_HINTS)


def _extract_doi(raw: str) -> Optional[str]:
    if not raw:
        return None
    from urllib.parse import unquote
    s = unquote(raw.strip().strip("<>\"'"))
    s = re.sub(r"^https?://(dx\.)?doi\.org/", "", s, flags=re.I)
    s = s.replace("%2F", "/").replace("%2f", "/")
    m = _DOI_IN_TEXT_RE.search(s)
    if m:
        return m.group(0).rstrip(").,;")
    if _BARE_DOI_RE.match(s):
        return s
    return None


def _rewrite_arxiv(url: str) -> str:
    """Prefer the abstract HTML page; fetch can read it more reliably than pdf."""
    return re.sub(
        r"^https?://arxiv\.org/pdf/(\d{4}\.\d{4,5})(?:v\d+)?(?:\.pdf)?$",
        r"https://arxiv.org/abs/\1",
        url,
        flags=re.I,
    )


# ---------------------------------------------------------------------------
# OA resolvers — these are the APIs that actually work
# ---------------------------------------------------------------------------
def _http_get_json(url: str, extra_headers: Optional[dict] = None) -> Optional[dict]:
    headers = dict(_HTTP_HEADERS)
    if extra_headers:
        headers.update(extra_headers)
    try:
        r = requests.get(url, headers=headers, timeout=_HTTP_TIMEOUT)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


def resolve_unpaywall(doi: str) -> Optional[str]:
    """Return best OA PDF or landing URL, or None."""
    url = f"https://api.unpaywall.org/v2/{quote(doi)}?email={quote(UNPAYWALL_EMAIL)}"
    data = _http_get_json(url)
    if not data:
        return None
    loc = data.get("best_oa_location") or {}
    return loc.get("url_for_pdf") or loc.get("url") or None


def resolve_openalex(doi: str) -> Optional[str]:
    """Return best OA PDF or landing URL from OpenAlex."""
    url = f"https://api.openalex.org/works/https://doi.org/{quote(doi)}"
    if OPENALEX_API_KEY:
        url += f"?api_key={quote(OPENALEX_API_KEY)}"
    data = _http_get_json(url)
    if not data:
        return None
    loc = data.get("best_oa_location") or {}
    return loc.get("pdf_url") or loc.get("landing_page_url") or None


def resolve_semantic_scholar(doi: str) -> Optional[str]:
    """Return openAccessPdf.url or an arXiv abs URL if S2 knows one."""
    url = (
        "https://api.semanticscholar.org/graph/v1/paper/"
        + quote(doi)
        + "?fields=openAccessPdf,externalIds,title,abstract"
    )
    headers = {}
    if S2_API_KEY:
        headers["x-api-key"] = S2_API_KEY
    data = _http_get_json(url, extra_headers=headers)
    if not data:
        return None
    pdf = (data.get("openAccessPdf") or {}).get("url")
    if pdf:
        return pdf
    ext = data.get("externalIds") or {}
    arxiv_id = ext.get("ArXiv") or ext.get("ARXIV")
    if arxiv_id:
        return f"https://arxiv.org/abs/{arxiv_id}"
    return None


def resolve_oa_url(doi: str) -> Optional[str]:
    """Unpaywall first (email only). Then Semantic Scholar (no key needed).
    OpenAlex is skipped unless OPENALEX_API_KEY is set."""
    for fn in (resolve_unpaywall, resolve_semantic_scholar):
        hit = fn(doi)
        if hit:
            return hit
    if OPENALEX_API_KEY:
        hit = resolve_openalex(doi)
        if hit:
            return hit
    return None


def crossref_metadata(doi: str) -> Optional[dict]:
    """Title + abstract from Crossref. No key, no signup."""
    url = f"https://api.crossref.org/works/{quote(doi)}"
    data = _http_get_json(url)
    if not data:
        return None
    msg = data.get("message") or {}
    title = " ".join(msg.get("title") or [])
    abstract = msg.get("abstract") or ""
    abstract = re.sub(r"<[^>]+>", " ", abstract)
    abstract = re.sub(r"\s+", " ", abstract).strip()
    authors = []
    for a in msg.get("author") or []:
        name = " ".join(p for p in (a.get("given"), a.get("family")) if p)
        if name:
            authors.append(name)
    return {
        "doi": doi,
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "url": (msg.get("URL") or f"https://doi.org/{doi}"),
    }


# ---------------------------------------------------------------------------
# URL gate: accept a paper URL or DOI, rewrite paywalls to OA copies
# ---------------------------------------------------------------------------
def _normalize_paper_url(raw: str) -> Optional[str]:
    """
    Return a fetchable URL.
    Paywall journal / supplement links are rewritten to an OA PDF if one exists.
    If no OA PDF exists but a DOI is present, return the Crossref works URL
    so the agent still gets title + abstract instead of INVALID_PAPER_URL.
    """
    if raw is None:
        return None
    s = raw.strip().strip("<>\"'")

    md = re.search(r"\((https?://[^)\s]+)\)", s)
    if md:
        s = md.group(1)
    else:
        embedded = re.search(r"(https?://[^\s<>\"']+)", s)
        if embedded and len(s) > len(embedded.group(1)) + 8:
            return None
        if embedded:
            s = embedded.group(1)

    s = s.rstrip(").,;")
    doi = _extract_doi(s)
    host = _host(s) if _URL_RE.match(s) else ""

    # Metadata APIs are always allowed as-is.
    if host.endswith("api.crossref.org") or host.endswith("api.unpaywall.org") \
            or host.endswith("api.semanticscholar.org") or host.endswith("api.openalex.org"):
        return s

    if doi:
        oa = resolve_oa_url(doi)
        if oa and not _is_paywall_host(_host(oa)):
            return _rewrite_arxiv(oa)
        # No OA full text: fall back to Crossref metadata (always public).
        return f"https://api.crossref.org/works/{doi}"

    if not _URL_RE.match(s):
        return None
    if not _allowed_host(host):
        return None
    if _is_paywall_host(host):
        return None
    return _rewrite_arxiv(s)


# ---------------------------------------------------------------------------
# Public tools
# ---------------------------------------------------------------------------
def web_search_claude(query: str, max_uses: int = 1) -> str:
    """Search once with Haiku. Near-duplicates and budget are enforced."""
    global _SEARCH_COUNT

    if _SEARCH_COUNT >= _SEARCH_BUDGET:
        return (
            "SEARCH_BUDGET_EXHAUSTED. Do not call web_search_claude again. "
            "If a number is missing, say it was not found."
        )

    dup = _too_similar(query, _RECENT_QUERIES, 0.72)
    if dup:
        return (
            f"DUPLICATE_QUERY of: {dup!r}. "
            "Do not rephrase the same search. Use the previous result. "
            "If that result lacked a table, stop and write <solution>."
        )

    key = hashlib.sha256(_norm(query).encode()).hexdigest()
    if key in _SEARCH_CACHE:
        return "CACHED_RESULT (do not search variants):\n" + _SEARCH_CACHE[key]

    _SEARCH_COUNT += 1
    _RECENT_QUERIES.append(query)

    try:
        response = _client.messages.create(
            model=SEARCH_MODEL,
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": (
                    "Answer ONLY from the search results. "
                    "If a requested table/number is not in the snippets, say NOT FOUND. "
                    "Prefer arXiv / DOI / Unpaywall / OpenAlex links over journal landing pages. "
                    "Do not suggest follow-up queries.\n\n"
                    f"Query: {query}"
                ),
            }],
            tools=[{
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": max_uses,
            }],
        )
    except anthropic.APIError as e:
        if "max_uses_exceeded" in str(e):
            return "SEARCH_BUDGET_EXHAUSTED. Answer with what you already have."
        return f"Search error: {e}"

    out = []
    for blk in response.content:
        if getattr(blk, "type", None) == "text":
            out.append(blk.text)
    text = "\n".join(out) if out else "NOT FOUND"

    text = (
        f"[search {_SEARCH_COUNT}/{_SEARCH_BUDGET} model={SEARCH_MODEL}]\n"
        f"{text}\n"
        "Do not issue another query unless you make meaningful changes. "
        "Searching outside of this tool is not permitted."
    )
    _SEARCH_CACHE[key] = text
    return text


def fetch_paper_url(url: str, max_uses: int = 1) -> str:
    """
    Open one paper URL.

    If you pass a DOI or a paywalled journal link (science.org, nature.com, …),
    this first asks Unpaywall / OpenAlex / Semantic Scholar for an OA copy,
    then fetches that copy. Keyword queries are rejected.
    """
    global _FETCH_COUNT

    doi_hint = _extract_doi(url)
    normalized = _normalize_paper_url(url)
    if not normalized:
        if doi_hint:
            meta = crossref_metadata(doi_hint)
            if meta:
                return (
                    f"PAYWALL. No open-access PDF for {doi_hint}. "
                    "Full text on science.org / nature.com cannot be fetched. "
                    f"Title: {meta.get('title')}\n"
                    f"Authors: {', '.join(meta.get('authors') or [])}\n"
                    f"Abstract: {meta.get('abstract') or 'NOT FOUND'}"
                )
        return (
            "INVALID_PAPER_URL. Pass a single http(s) paper link or a bare DOI. "
            "Keyword queries are not allowed. Use web_search_claude first."
        )

    if _FETCH_COUNT >= _FETCH_BUDGET:
        return (
            "FETCH_BUDGET_EXHAUSTED. Do not call fetch_paper_url again. "
            "Use the paper text you already have, or say NOT FOUND."
        )

    dup = _too_similar(normalized, _FETCH_RECENT, 0.92)
    if dup:
        return (
            f"DUPLICATE_FETCH of: {dup!r}. Use the previous paper text. "
            "Do not refetch the same URL."
        )

    key = hashlib.sha256(normalized.encode()).hexdigest()
    if key in _FETCH_CACHE:
        return "CACHED_PAPER (do not refetch):\n" + _FETCH_CACHE[key]

    _FETCH_COUNT += 1
    _FETCH_RECENT.append(normalized)

    try:
        response = _client.messages.create(
            model=FETCH_MODEL,
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": (
                    "Fetch ONLY this URL and extract content useful for a scientific "
                    "question: title, authors, abstract, methods, key numbers/tables, "
                    "conclusions. If the page is a landing/paywall page, say PAYWALL "
                    "or NOT FOUND and quote any available abstract. "
                    "Do not search the web. Do not invent a different URL.\n\n"
                    f"URL: {normalized}"
                ),
            }],
            tools=[{
                "type": "web_fetch_20250910",
                "name": "web_fetch",
                "max_uses": max_uses,
                "allowed_domains": list(_FETCH_DOMAIN_SUFFIXES),
                "max_content_tokens": 20000,
            }],
        )
    except anthropic.APIError as e:
        err = str(e)
        if "max_uses_exceeded" in err:
            return "FETCH_BUDGET_EXHAUSTED. Answer with the paper text you already have."
        return f"Fetch error: {e}"
    except Exception as e:
        return f"Fetch error: {type(e).__name__}: {e}"

    out = []
    for blk in response.content:
        if getattr(blk, "type", None) == "text":
            out.append(blk.text)
    text = "\n".join(out) if out else "NOT FOUND"

    text = (
        f"[fetch {_FETCH_COUNT}/{_FETCH_BUDGET} model={FETCH_MODEL}] {normalized}\n"
        f"{text}\n"
        "This tool cannot run keyword search. "
        "Searching outside of web_search_claude / fetch_paper_url is not permitted."
    )
    _FETCH_CACHE[key] = text
    return text