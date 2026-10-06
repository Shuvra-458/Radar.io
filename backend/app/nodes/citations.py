import re
from rich import print as rprint

from app.state import ResearchState

# Matches [1], [2], etc. - same marker format the synthesizer writes.
_CITATION_RE = re.compile(r"[\[【](\d+)[\]】]")

async def citation_node(state: ResearchState) -> dict:
    """
    Validate the report's citations. Doesn't rewrite the report - just
    checks integrity and emits diagnostics. The source map itself passes
    through unchanged so downstream consumers can serve it.
    """
    report = state.get("report", "")
    source_map: dict[int, dict] = state.get("citations", {})

    cited = {int(m) for m in _CITATION_RE.findall(report)}
    available = set(source_map.keys())

    missing = cited - available
    unused = available - cited

    if missing:
        rprint(f"[yellow] {len(missing)} citation(s) point to "
               f"unknown sources: {sorted(missing)}[/yellow]")

        rprint(f"[green] citations: {len(cited & available)} used, "
               f"{len(unused)} unused of {len(available)} retrieved[/green]")

    # Logs which task_ids had no cited sources - helps to spot weak branches
    if unused:
        unused_tasks = {source_map[i]["task_id"] for i in unused}
        rprint(f"[dim] ℹ unused sources came from: "
               f"{sorted(unused_tasks)}[/dim]")


    return {}
