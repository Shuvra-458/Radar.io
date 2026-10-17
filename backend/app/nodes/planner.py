from pydantic import BaseModel, Field
from rich import print as rprint

from app.config import LLM_MODEL, LLM_MAX_RETRIES, LLM_TIMEOUT_S
from app.state import ResearchState, SubTask
from app.llm import make_llm, llm_with_retry

class Plan(BaseModel):
    """Wrapper so we can use structured output cleanly."""
    tasks: list[SubTask] = Field(
        description="3-6 focused research sub-tasks covering news, product, customers and financials.",
        min_length=3,
        max_length=6,
    )

# ------ LLL Instantiation -------
_llm = make_llm(temperature=0)
_planner = _llm.with_structured_output(Plan)

COMPETITIVE_PROMPT = """You are a competitive-intelligence analyst.
Break the task "Analyze the company {company}" into 3-6 concrete,
search-friendly research sub-tasks.

Cover these angles when relevant:
    • recent funding / financial news
    • product launches or major releases
    • customer reviews / sentiment
    • key hires, partnerships, or acquisitions
    • pricing or positioning changes

Rules:
- Each sub-task must be a single, specific question.
- `source_hint` should be "news" for funding/PR, "blog" for product/engineering,
  "reviews" for sentiment, "general" for otherwise.
- Keep `id` short snake_case.
"""

EMPLOYER_PROMPT = """You are a rigorous employment analyst helping a
job seeker evaluate whether {company} is a safe employer.

Break "Evaluate {company} as an employer" into 5–6 concrete research
sub-tasks. Cover these angles:

  • Compensation & salary reliability (any reports of delayed salaries,
    missing PF/gratuity, "adjusted" payslips?)
  • Work-life balance (overtime culture, weekend work, "always-on"
    expectations, leave policy enforcement)
  • Management quality (micromanagement, toxicity, favoritism,
    leadership churn)
  • Hiring process integrity (bond periods, notice-period traps,
    verbal-only offers, offer revocations)
  • Job security (layoff patterns, contract-to-hire, off-roll practices,
    restructuring in the last 18 months)
  • Growth credibility (are promotions real or title-only? is "we promote
    from within" backed by evidence?)

Rules:
- Each sub-task is a single, specific question answerable from public
  reviews, forums, news, or company disclosures.
- `source_hint` values:
    "reviews"    → AmbitionBox, Glassdoor, Indeed
    "community"  → Reddit, Blind, Hacker News, team-blind
    "comp"       → levels.fyi, AmbitionBox salary pages
    "news"       → layoffs.fyi, mainstream press
    "general"    → open search
- Keep `id` short snake_case.
- Do NOT ask questions that require non-public information.
"""

async def planner_node(state: ResearchState) -> dict:
    company = state["company"]
    mode = state.get("mode", "competitive")

    prompt_template = EMPLOYER_PROMPT if mode == "employer" else COMPETITIVE_PROMPT
    prompt = prompt_template.format(company=company)

    plan: Plan = await llm_with_retry(lambda: _planner.ainvoke(prompt))

    rprint(f"[green]✓ planned {len(plan.tasks)} sub-tasks ({mode} mode)[/green]")
    return {"sub_tasks": plan.tasks}
