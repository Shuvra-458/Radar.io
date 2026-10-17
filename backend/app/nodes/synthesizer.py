from rich import print as rprint

from app.llm import make_llm, llm_with_retry
from app.state import ResearchState, Finding, Verdict

# Using a Bigger model for synthesis - coz quality matters
_llm = make_llm(model="openai/gpt-oss-120b", temperature=0)

COMPETITIVE_PROMPT = """You are a senior competitive-intelligence analyst.
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

EMPLOYER_PROMPT = """You are a rigorous employment analyst writing a
report for a job seeker considering {company}.

A structured verdict has already been scored. Your job is to narrate it
in a way a candidate can act on.

Structure your report with these sections:

## Summary
Narrate the verdict in 3–4 sentences. Include the overall score and the
verdict label {{"red", "mixed", "green"}}.

## Green flags
What the sources actually praise, with cited evidence. If there are
none, write "No positive signals found in the sources reviewed."

## Red flags
Specific, cited concerns. Order by severity. Each bullet must end with
[N] citations. Be concrete: "salary delays reported [3][7]", not "some
issues".

## What employees say
3–5 representative quotes or paraphrases, each with citations. Do not
embellish.

## Caveats
What a job seeker should keep in mind: sample size, source bias (reviews
skew negative), and one sentence that this is an AI summary of public
sources, not legal or employment advice.

Rules:
- Use markdown headers exactly as `## Summary`, `## Green flags`, etc.
- Do NOT wrap headers in bold.
- Do NOT invent facts. Every claim cites a [N].
- Do NOT hedge when the verdict is red — job seekers need clear signal.
- Do NOT overclaim when confidence is low — say so plainly.

--- VERDICT ---
{verdict_block}
--- END VERDICT ---

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

def _format_verdict(verdict: Verdict | None) -> str:
    if not verdict:
        return "No structured verdict available."

    rows = [
        f"Overall: {verdict.overall_score}/10 ({verdict.verdict})",
        f"Summary: {verdict.summary}",
        "",
        "Dimensions",
    ]
    for name, dim in verdict.dimensions.items():
        rows.append(
            f"  {name}: {dim.score}/10 [{dim.confidence} confidence] "
            f"({dim.evidence})"
        )
    return "\n".join(rows)


async def synthesizer_node(state: ResearchState) -> dict:
    """Runs ONCE, after all researchers complete (this is the join point). """
    company = state["company"]
    mode = state.get("mode", "competitive")
    findings = state.get("findings", [])

    if not findings:
        return {"report": "No findings to synthesize.", "citations": {}}

    findings_text, source_map = _format_findings(findings)

    if mode == "employer":
        verdict_block = _format_verdict(state.get("verdict"))
        prompt = EMPLOYER_PROMPT.format(
            company=company, findings=findings_text, verdict_block=verdict_block,
        )
    else:
        prompt = COMPETITIVE_PROMPT.format(
          company=company, findings=findings_text,  
        )

    rprint(f"[magenta]◆ synthesizing report from {len(findings)} findings "
           f"({len(source_map)} sources)...[/magenta]")

    resp = await llm_with_retry(lambda: _llm.ainvoke(prompt))

    rprint(f"[green]✓ report: {len(resp.content)} chars[/green]")

    return {"report": resp.content, "citations": source_map}
