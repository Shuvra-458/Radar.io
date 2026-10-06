from rich import print as rprint
from app.state import ResearchState

async def aggregator_node(state: ResearchState) -> dict:
    """
    Runs ONCE, after all researches complete. For now it just prints a 
    summary.
    """
    docs = state.get("docs", [])
    findings = state.get("findings", [])

    rprint(f"\n[bold magenta]═══ JOIN reached ═══[/bold magenta]")
    rprint(f"[magenta]  {len(findings)} findings from "
           f"{len(docs)} total docs[/magenta]\n")

    for f in findings:
        rprint(f"[bold]{f.task_id}[/bold] — {f.question}")
        rprint(f"  {f.summary}\n")

    return {}
