import httpx
from bs4 import BeautifulSoup

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US, en;q=0.9",
}

# Tags whose content are never useful for research
_JUNK_TAGS = ["script", "style", "nav", "footer", "header", "aside", "noscript", "form"]

async def scrape(url: str, max_chars: int = 8000, timeout_s: float = 10.0) -> str | None:
    """
    Fetch a URL and return clean text, or None on any failure.

    Every failure mode (DNS, TLS, 404, timeout, non-HTML) returns None instead of raising.
    The caller decides what to do with None.
    """
    try:
        async with httpx.AsyncClient(
            timeout=timeout_s,
            follow_redirects=True,
            headers=_HEADERS,
        ) as client:
            r = await client.get(url)
            r.raise_for_status()

            # Reject PDFs, images, etc.
            ctype = r.headers.get("content-type", "")
            if "text/html" not in ctype and "text/plain" not in ctype:
                return None

            soup = BeautifulSoup(r.text, "html.parser")
            for tag in soup(_JUNK_TAGS):
                tag.decompose()

            # Prefer a semantic content container.
            container = (
                soup.find("article")
                or soup.find("main")
                or soup.find(attrs={"role": "main"})
                or soup.body
                or soup
            )

            # Pull only paragraphs / headings / list items.
            paragraphs = container.find_all(["p", "h1", "h2", "h3", "li"])

            # Skip tiny fragments
            chunks = [p.get_text(" ", strip=True) for p in paragraphs]
            chunks = [c for c in chunks if len(c) >= 40]

            text = "\n".join(chunks)[:max_chars]
            return text if text else None

    except Exception:
        return None