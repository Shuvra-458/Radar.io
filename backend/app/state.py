from typing import TypedDict, Annotated, Literal
import operator
from pydantic import BaseModel, Field

Mode = Literal["competitive", "employer"]

# ------- Structured pieces of the state --------

class SubTask(BaseModel):
    """One research question the planner decides we need to answer."""
    id: str = Field(description="Short unique slug, e.g: 'recent funding'")
    question: str = Field(description="Natural language research question")
    source_hint: Literal["news", "blog", "reviews", "general", "community", "comp"] = Field(description="Where to look first")

class SourceDoc(BaseModel):
    """A single scraped/search result we keep for RAG."""
    url: str
    title: str
    content: str
    task_id: str   # Which sub task produced this
    query: str     # The search query that found it

class Finding(BaseModel):
    """Distilled answer for one sub-task, with source URLs attached."""
    task_id: str
    question: str
    summary: str
    sources: list[str]

class DimensionScore(BaseModel):
    """One dimension of the employer rubric"""
    score: float = Field(ge=0, le=10, description="0 = severe problems, 10 = excellent")
    evidence: str = Field(description="1-2 sentences of reasoning with [N] markers")
    confidence: Literal["low", "medium", "high", "unknown"] = Field(
        description="Based on number and diversity of sources"
    )
    sources: list[int] = Field(
        default_factory=list,
        description="Citation indices from the findings that support this score",
    )

# app/state.py

class DimensionScores(BaseModel):
    """Fixed-shape container so the LLM can't invent or omit keys."""
    legitimacy: DimensionScore = Field(
        description="Is this a real employer, or does it charge candidates "
                    "fees for internships/certificates/training? Are there "
                    "widespread fraud or refund complaints? "
                    "Below 3 forces the overall verdict to 'red'."
    )
    compensation: DimensionScore = Field(
        description="Pay levels and pay parity relative to industry."
    )
    payment_reliability: DimensionScore = Field(
        description="Salaries, PF, gratuity paid on time. No 'adjustments'."
    )
    work_life_balance: DimensionScore = Field(
        description="Overtime culture, weekend work, leave enforcement."
    )
    management_quality: DimensionScore = Field(
        description="Toxicity, micromanagement, leadership churn."
    )
    hiring_integrity: DimensionScore = Field(
        description="Bond periods, notice traps, offer honoring."
    )
    job_security: DimensionScore = Field(
        description="Layoffs, contract-to-hire, off-roll practices."
    )
    growth_credibility: DimensionScore = Field(
        description="Real promotions vs title-only inflation."
    )


class Verdict(BaseModel):
    """Structured employer verdict, produced by the redflag_scorer node."""
    dimensions: DimensionScores
    overall_score: float = Field(
        ge=0, le=10,
        description="Average of the 7 dimension scores, one decimal place", 
    )
    verdict: Literal["green", "mixed", "red", "unknown"] = Field(
        description="green if avg >= 7, mixed if 4-6.9, red if < 4, "
                    "unknown if fewer than 4 dimensions have real evidence"
    )
    summary: str = Field(
        description="One actionable sentence a job seeker could act on",
    )

# --------- The Graph State ------------

class ResearchState(TypedDict, total=False):
    """
    total=False means every key is optional — nodes can return partial updates
    without us having to declare all keys up front.

    When multiple parallel branches write to the same key, LangGraph calls the
    reducer to merge them. `operator.add` on a list means "concatenate".
    Without a reducer, the default is "last write wins" — and you'd lose data
    from parallel branches.
    """
    company: str
    mode: Mode

    # Planner output: overwrite (single writer, no reducer needed)
    sub_tasks: list[SubTask]

    # Populated per branch via the Send payload. Declared here for typing/documentation; Send merges it at runtime.
    sub_task: SubTask

    # Written by MANY parallel researcher nodes -> must accumulate
    docs: Annotated[list[SourceDoc], operator.add]
    findings: Annotated[list[Finding], operator.add]

    verdict: Verdict | None

    # Synthesis output
    report: str
    citations: dict[int, dict]

