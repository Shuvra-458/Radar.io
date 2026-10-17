from tavily import AsyncTavilyClient

from app.config import TAVILY_API_KEY

_client = AsyncTavilyClient(api_key=TAVILY_API_KEY)

# We ask Tavily for `advanced` depth because it returns longer snippets
# and handles JS-rendered pages server-side.

# Source preferences by hint. These are HINTS — Tavily falls back to
# open search if the preferred domains return nothing. This keeps the
# pipeline resilient when a company has no Reddit presence, etc.
DOMAIN_HINTS: dict[str, list[str]] = {
    # Competitive mode
    "news":       ["techcrunch.com", "reuters.com", "bloomberg.com"],
    "blog":       ["medium.com", "substack.com"],
    "reviews":    ["g2.com", "capterra.com", "trustpilot.com"],

    # Employer mode
    "community":  ["reddit.com", "news.ycombinator.com", "teamblind.com"],
    "comp":       ["levels.fyi", "ambitionbox.com", "glassdoor.co.in",
                   "glassdoor.com"],
}


async def search(query: str, source_hint: str = "general", max_results: int = 4) -> list[dict]:
    """
    Returns a list of {url, title, snippet} dicts.
    """
    domains = DOMAIN_HINTS.get(source_hint)
    
    resp = await _client.search(
        query=query,
        max_results=max_results,
        search_depth="advanced",
        include_answer=False,
        include_domains=domains,
    )
    return [
        {"url": r["url"], "title": r.get("title", ""), "snippet": r.get("content", "")}
        for r in resp.get("results", [])
    ]
