from rich import print as rprint

from app.llm import make_llm, llm_with_retry
from app.state import ResearchState, Finding

# Using a Bigger model for synthesis - coz quality matters
_llm = make_llm(model="openai/gpt-oss-120b", temperature=0)

SWOT_PROMPT = """You are a senior competitive-intelligence analyst.
Produce a SWOT analysis for {company} using ONLY the research findings
below. Every claim must be traceable to one of the numbered sources.

Each finding lists its sources, labelled [1], [2], etc. Use those exact
markers in your report.

Structure your report with these sections:

## Executive Summary
2-3 sentences on {company}'s current strategic position.

## Strengths
2-4 bullets on internal capabilities and market position.

## Weaknesses
2-4 bullets on internal gaps and limitations.

## Opportunities
2-4 bullets on external trends and openings.

## Threats
2-4 bullets on competitive and market risks.

Rules:
- Every factual claim MUST end with a [N] citation to a source above.
- Do NOT invent facts, numbers, or dates not present in the findings.
- If a section lacks evidence, write "Insufficient evidence in sources."
- Prefer specific numbers, dates, and names where the sources provide them.
- One or two sentences per bullet.

--- FINDINGS ---
{findings}
--- END FINDINGS ---

Report:"""

def _format_findings(findings: list[Finding]) -> tuple[str, dict[int, dict]]:
    """
    Render findings as numbered markdown AND build the [N] -> source map.
    """
    lines: list[str] = []
    source_map: dict[int, dict] = {}
    n = 1

    for f in findings:
        lines.append(f"### {f.question}")
        lines.append(f"Summary: {f.summary}")
        lines.append("Sources:")
        for url in f.sources:
            source_map[n] = {"url": url, "task_id": f.task_id}
            lines.append(f"  [{n}] {url}")
            n += 1
        lines.append("")

    return "\n".join(lines), source_map

async def synthesizer_node(state: ResearchState) -> dict:
    """Runs ONCE, after all researchers complete (this is the join point). """
    company = state["company"]
    findings = state.get("findings", [])

    if not findings:
        return {"report": "No findings to synthesize.", "citations": {}}

    findings_text, source_map = _format_findings(findings)

    rprint(f"[magenta]◆ synthesizing report from {len(findings)} findings "
           f"({len(source_map)} sources)...[/magenta]")

    prompt = SWOT_PROMPT.format(company=company, findings=findings_text)
    resp = await llm_with_retry(lambda: _llm.ainvoke(prompt))

    rprint(f"[green]✓ report: {len(resp.content)} chars[/green]")

    return {"report": resp.content, "citations": source_map}
