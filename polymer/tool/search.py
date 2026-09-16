import anthropic
import hashlib
import re
from difflib import SequenceMatcher

_client = anthropic.Anthropic()

_SEARCH_CACHE = {}          # exact query -> result
_SEARCH_COUNT = 0
_SEARCH_BUDGET = 5          # per task; reset when you start a new user task
_RECENT_QUERIES = []        # for near-duplicate detection


def reset_search_budget(n: int = 3):
    global _SEARCH_COUNT, _RECENT_QUERIES, _SEARCH_CACHE
    _SEARCH_COUNT = 0
    _RECENT_QUERIES = []
    # keep _SEARCH_CACHE across tasks if you want; clear if papers change often


def _norm(q: str) -> str:
    q = q.lower()
    q = re.sub(r"[^a-z0-9\s\+\-\[\]]+", " ", q)
    q = re.sub(r"\s+", " ", q).strip()
    return q


def _too_similar(q: str, threshold: float = 0.72) -> str | None:
    nq = _norm(q)
    for prev in _RECENT_QUERIES:
        if SequenceMatcher(None, nq, _norm(prev)).ratio() >= threshold:
            return prev
    return None


def web_search_claude(query: str, max_uses: int = 1) -> str:
    """Search once. Near-duplicate queries are refused. Budget is per task."""
    global _SEARCH_COUNT

    if _SEARCH_COUNT >= _SEARCH_BUDGET:
        return (
            "SEARCH_BUDGET_EXHAUSTED. Do not call web_search_claude again. "
            "Write <solution> from evidence already in the conversation. "
            "If a number is missing, say it was not found."
        )

    dup = _too_similar(query)
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
            model="claude-sonnet-4-5",
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": (
                    "Answer ONLY from the search results. "
                    "If a requested table/number is not in the snippets, say NOT FOUND. "
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
        if blk.type == "text":
            out.append(blk.text)
    text = "\n".join(out) if out else "NOT FOUND"

    # Push the model toward stopping even on a thin hit
    text = (
        f"[search {_SEARCH_COUNT}/{_SEARCH_BUDGET}]\n"
        f"{text}\n"
        "Do not issue another query unless you make meaningful changes."
    )
    _SEARCH_CACHE[key] = text
    return text