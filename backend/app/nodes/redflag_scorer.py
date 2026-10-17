"""
Employer-mode scoring node.

Runs after all researchers complete, before synthesis. Takes the
accumulated findings and produces a structured `Verdict` object —
7 dimension scores with cited evidence and confidence levels.

The scoring prompt is deliberately biased toward negative signals.
A job seeker's downside risk matters more than the average review; a
tool that hedges "it might be fine!" when three sources report unpaid
salaries is a bad tool.
"""

from rich import print as rprint

from app.llm import make_llm, llm_with_retry
from app.state import ResearchState, Finding, Verdict

_llm = make_llm(model="openai/gpt-oss-120b", temperature=0)
_scorer = _llm.with_structured_output(Verdict)

DIMENSIONS = [
    "legitimacy",
    "compensation",         # pay levels, pay parity, offer honoring
    "payment_reliability",  # on-time salary, PF/gratuity, no "adjustments"
    "work_life_balance",    # overtime, weekend work, leave
    "management_quality",   # toxicity, micromanagement, churn
    "hiring_integrity",     # bonds, notice-period traps, offers honored
    "job_security",         # layoffs, off-roll, contract-to-hire
    "growth_credibility",   # real promotions vs title inflation
]

SCORER_PROMPT = """You are a rigorous employment analyst helping a job
seeker evaluate {company} as an employer.

Score each of the following 7 dimensions from 0 to 10 using ONLY the
numbered findings below. 0 = severe, systemic problems. 10 = excellent,
well-evidenced.

Dimensions:
  legitimacy            — Is this a real employer, or does it charge candidates
                          fees for internships, certificates, or "training"?
                          Are there widespread fraud or refund complaints?
                          A score below 3 here forces the overall verdict to
                          "red" regardless of the other dimensions.

  compensation          — are pay levels and pay parity reasonable?
  payment_reliability   — are salaries, PF, and gratuity paid on time?
  work_life_balance     — overtime, weekend work, leave enforcement
  management_quality    — toxicity, micromanagement, leadership churn
  hiring_integrity      — bonds, notice-period traps, offer honoring
  job_security          — layoffs, contract-to-hire, off-roll practices
  growth_credibility    — real promotions vs. title inflation

For each dimension produce:
  - score: 0–10
  - evidence: 1–2 sentences citing [N] markers from the findings
  - confidence: "low" | "medium" | "high" (based on number and diversity
    of independent sources)
  - sources: list of the [N] indices you relied on

RULES (strict):
1. NEVER invent evidence. Only cite findings shown below.
2. If a dimension has NO supporting sources, score it 5.0 with confidence
   "low" and evidence "Insufficient public evidence to score."
3. When sources conflict, weight NEGATIVE signals higher — a job
   seeker's downside risk matters more than average sentiment.
4. Prefer specific, verifiable claims (salary delays, bond periods)
   over vague sentiment ("culture is bad").
5. If a claim appears in only one source, cap confidence at "low".

Then produce:
  - overall_score: mean of the 7 dimension scores, 1 decimal
  - verdict: "green" (≥7.0), "mixed" (4.0–6.9), "red" (<4.0)
  - summary: one actionable sentence a job seeker could act on

--- FINDINGS ---
{findings}
--- END FINDINGS ---

Return a Verdict object.
"""

def _format_findings(findings: list[Finding]) -> tuple[str, dict[int, dict]]:
    """Numbered sources with a map."""
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

async def redflag_scorer_node(state: ResearchState) -> dict:
    company = state["company"]
    findings = state.get("findings", [])

    if not findings:
        rprint("[yellow]◆ scorer: no findings to evaluate[/yellow]")
        return {"verdict": None}

    findings_text, _ = _format_findings(findings)

    rprint(f"[magenta]◆ scoring employer: {company} "
           f"({len(findings)} findings)...[/magenta]")

    prompt = SCORER_PROMPT.format(company=company, findings=findings_text)
    verdict: Verdict = await llm_with_retry(lambda: _scorer.ainvoke(prompt))

    # Ensure all dimensions exist even if the LLM omitted one
    missing = [d for d in DIMENSIONS if d not in verdict.dimensions]
    if missing:
        rprint(f"[yellow]  ⚠ missing dimensions: {missing}[/yellow]")

    badge = {"green": "🟢", "mixed": "🟡", "red": "🔴"}[verdict.verdict]
    rprint(f"[bold]  {badge} {verdict.verdict.upper()} — "
           f"{verdict.overall_score}/10[/bold]")

    return {"verdict": verdict}

