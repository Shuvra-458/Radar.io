import asyncio
from app.db.schema import ensure_schema
from app.db.documents import insert_docs, search_docs
from app.state import SourceDoc

async def main() -> None:
    await ensure_schema()
    print("[ok] schema")

    docs = [
        SourceDoc(
            url="https://example.com/a",
            title="Walmart grocery delivery expands",
            content="Walmart announced an expansion of its grocery delivery "
                    "network to 500 new stores across the Midwest.",
            task_id="t1", query="walmart grocery",
        ),
        SourceDoc(
            url="https://example.com/b",
            title="Stripe launches a new billing product",
            content="Stripe released a new usage-based billing product for "
                    "AI companies with per-token pricing.",
            task_id="t2", query="stripe billing",
        ),
    ]
    n = await insert_docs(company="TEST", docs=docs)
    print(f"[ok] inserted {n}")

    hits = await search_docs("grocery delivery", company="TEST", k=1)
    for h in hits:
        print(f"[ok] top hit: {h['url']} dist={h['distance']:.4f} "
              f"title={h['title']!r}")

if __name__ == "__main__":
    asyncio.run(main())