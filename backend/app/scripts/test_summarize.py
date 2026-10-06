import asyncio
from rich import print as rprint

from app.tools.search import search
from app.tools.scraper import scrape
from app.llm import make_llm
from app.state import SubTask, SourceDoc


QUESTION = "What were Walmart's Q3 2024 earnings results?"


async def main():
    # 1. Reproduce the search + scrape steps for one sub-task.
    hits = await search(QUESTION, max_results=3)
    docs: list[SourceDoc] = []
    for h in hits:
        text = await scrape(h["url"])
        content = (text or h["snippet"] or "").strip()
        docs.append(SourceDoc(
            url=h["url"], title=h["title"], content=content,
            task_id="test", query=QUESTION,
        ))

    rprint(f"[cyan]scraped {len(docs)} docs[/cyan]")
    for d in docs:
        rprint(f"  {d.url}")
        rprint(f"    content={len(d.content)} chars")
        rprint(f"    first 300: {d.content[:300]!r}")

    # 2. Build the exact context string the node would use.
    context = "\n\n".join(
        f"[{d.url}]\n{d.content[:2000]}" for d in docs
    )
    rprint(f"\n[cyan]total context = {len(context)} chars[/cyan]")

    # 3. Build the exact prompt the node would use.
    prompt = f"""You are a competitive-intelligence analyst.
Company: Walmart
Research question: {QUESTION}

Below are excerpts from public web sources. Answer the question in 2–4
sentences, using ONLY the information in the excerpts. If the excerpts
don't answer the question, say "Insufficient information found."

Do NOT invent facts, dates, or numbers. Be specific and factual.

--- EXCERPTS ---
{context}
--- END EXCERPTS ---
"""
    rprint(f"[cyan]prompt = {len(prompt)} chars[/cyan]\n")

    # 4. Call the same LLM the researcher uses.
    llm = make_llm(temperature=0)
    resp = await llm.ainvoke(prompt)

    rprint("[green bold]═══ MODEL RESPONSE ═══[/green bold]")
    rprint(resp.content)
    rprint(f"\n[dim]content type: {type(resp.content)}[/dim]")


if __name__ == "__main__":
    asyncio.run(main())