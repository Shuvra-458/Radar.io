import asyncio
from rich import print as rprint
from app.db.documents import insert_docs
from app.state import ResearchState, SubTask, SourceDoc, Finding
from app.tools.search import search
from app.tools.scraper import scrape
from app.llm import make_llm, llm_with_retry

# ----- Module level singletons (built once, reused by every branch) --------
_llm = make_llm(model="qwen/qwen3.8-27b", temperature=0)

# Caps concurrent LLM calls at 3 to avoid 429s
_LLM_SEM = asyncio.Semaphore(3)

# One prompt per sub task
SUMMARIZE_PROMPT = """You are a competitive-intelligence analyst.
Company: {company}
Research question: {question}

Below are excerpts from public web sources. Extract every fact they
contain that is relevant to the question — numbers, dates, product names,
partnership names, financial figures, direct statements.

Write 2–4 sentences. Prefer specific facts over generalities. A partial
answer built from real excerpts is far more useful than a refusal.

If the excerpts are truly unrelated to the question, respond with exactly:
"Insufficient information found."

Otherwise, do NOT use that phrase — always produce an answer from what
you have, even if the excerpts only partially address the question.

--- EXCERPTS ---
{context}
--- END EXCERPTS ---

Answer:"""
def _format_context(docs: list[SourceDoc], per_doc_chars: int = 1000) -> str:
    """Concat doc excerpts with their URLs so the LLM can attribute claims."""
    blocks = []
    for d in docs:
        snippet = d.content[:per_doc_chars]
        blocks.append(f"[{d.url}]\n{snippet}")
    return "\n\n".join(blocks)

async def _summarize(company: str, task: SubTask, docs: list[SourceDoc]) -> str:
    """Ask the LLM to distill a set of docs into a 2-4 sentence answer."""
    if not docs:
        return "No sources were retrieved for this question."

    context = _format_context(docs)

    # For Debugging
    rprint(f"[dim]DEBUG {task.id}: context={len(context)} chars, "
           f"first 200={context[:200]!r}[/dim]")

    prompt = SUMMARIZE_PROMPT.format(
        company=company,
        question=task.question,
        context=context, 
    )
    async with _LLM_SEM:
        resp = await _llm.ainvoke(prompt)

    # For Debugging
    rprint(f"[dim]DEBUG {task.id}: response={resp.content[:200]!r}[/dim]")

    return resp.content

async def researcher_node(state: ResearchState) -> dict:
    """
    One branch of the fan-out. Receives `state` containing `company` and
    its own `sub_task` (injected via Send). Returns a partial update wit
    `docs` and `findings` - both accumulate via their reducers.
    """
    company = state["company"]
    task: SubTask = state["sub_task"]
    rprint(f"[cyan]▶ researcher[/cyan] [{task.id}] {task.question}")

    # 1. Search - Tavily, one call per sub task
    hits = await search(task.question, max_results=3)
    if not hits:
        rprint(f"[yellow] no results for {task.id}[/yellow]")
        return {"docs": [], "findings": []}

    # 2. Scrape all URLs concurrently
    scraped = await asyncio.gather(*(scrape(h["url"]) for h in hits))

    # 3. Build SourceDocs. Fall back to the search snippet when scraping fails
    docs: list[SourceDoc] = []
    for h, text in zip(hits, scraped):
        content = (text or h["snippet"] or "").strip()
        if not content:
            continue
        docs.append(SourceDoc(
            url=h["url"],
            title=h["title"] or h["url"],
            content=content,
            task_id=task.id,
            query=task.question,
        ))

    rprint(f"[green]  ✓ {task.id}: {len(docs)} docs "
           f"({sum(1 for s in scraped if s)} scraped, "
           f"{sum(1 for s in scraped if not s)} fell back)[/green]")

    # 4. persist to pgvector - embedding + insert
    try:
        await insert_docs(company=company, docs=docs)
    except Exception as e:
        rprint(f"[yellow]  ⚠ insert failed for {task.id}: {e}[/yellow]")

    # 5. Distill into a Finding.
    summary = await _summarize(company, task, docs)

    finding = Finding(
        task_id=task.id,
        question=task.question,
        summary=summary,
        sources=[d.url for d in docs],
    )
    return {"docs": docs, "findings": [finding]}



