from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI

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

PROMPT = """You are a competitive-intelligence analyst.
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

def planner_node(state: ResearchState) -> dict:
    company = state["company"]
    plan: Plan = _planner.invoke(PROMPT.format(company=company))
    return {"sub_tasks": plan.tasks}
