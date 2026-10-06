from tavily import AsyncTavilyClient

from app.config import TAVILY_API_KEY

_client = AsyncTavilyClient(api_key=TAVILY_API_KEY)

# We ask Tavily for `advanced` depth because it returns longer snippets
# and handles JS-rendered pages server-side.

async def search(query: str, max_results: int = 5) -> list[dict]:
    """
    Returns a list of {url, title, snippet} dicts.
    """
    resp = await _client.search(
        query=query,
        max_results=max_results,
        search_depth="advanced",
        include_answer=False,
    )
    return [
        {"url": r["url"], "title": r.get("title", ""), "snippet": r.get("content", "")}
        for r in resp.get("results", [])
    ]
