import sys
import asyncio
from rich import print as rprint
from rich.markdown import Markdown

from app.db.schema import ensure_schema
from app.graph import build_graph


async def main():
    company = sys.argv[1] if len(sys.argv) > 1 else input("Company: ").strip()

    await ensure_schema()

    graph = build_graph()
    rprint(f"[bold]Analyzing [green]{company}[/green][/bold]\n")

    final_state: dict = {}
    async for chunk in graph.astream({"company": company}):
        for node_name, update in chunk.items():
            rprint(f"[dim]── node: {node_name} done[/dim]")
            if not update:
                continue

            # Reducer applied manually
            for k, v in update.items():
                if k in ("docs", "findings"):
                    final_state[k] = final_state.get(k, []) + v
                else:
                    final_state[k] = v

    rprint("\n[bold cyan]═══ REPORT ═══[/bold cyan]\n")
    rprint(Markdown(final_state.get("report", "(no report)")))

    rprint(f"\n[bold cyan]═══ SOURCES ═══[/bold cyan]")
    for idx, src in sorted(final_state.get("citations", {}).items()):
        rprint(f"  [{idx}] {src['url']}")

if __name__ == "__main__":
    asyncio.run(main())