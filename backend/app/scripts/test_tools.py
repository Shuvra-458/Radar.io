import asyncio
from app.tools.search import search
from app.tools.scraper import scrape

async def main() -> None:
    results = await search("Walmart grocery delivery 2024", max_results=3)
    print(f"[ok] {len(results)} results")
    for r in results:
        print(f"    {r['url']}")

    for r in results:
        text = await scrape(r["url"])
        if text is None:
            print(f"[!!] scrape failed: {r['url']}")
        else:
            print(f"[ok] {len(text):>5} chars  {r['url']}")


if __name__ == "__main__":
    asyncio.run(main())