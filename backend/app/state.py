from typing import TypedDict, Annotated, Literal
import operator
from pydantic import BaseModel, Field

# ------- Structured pieces of the state --------

class SubTask(BaseModel):
    """One research question the planner decides we need to answer."""
    id: str = Field(description="Short unique slug, e.g: 'recent funding'")
    question: str = Field(description="Natural language research question")
    source_hint: Literal["news", "blog", "reviews", "general"] = Field(description="Where to look first")

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

    # Planner output: overwrite (single writer, no reducer needed)
    sub_tasks: list[SubTask]

    # Populated per branch via the Send payload. Declared here for typing/documentation; Send merges it at runtime.
    sub_task: SubTask

    # Written by MANY parallel researcher nodes -> must accumulate
    docs: Annotated[list[SourceDoc], operator.add]
    findings: Annotated[list[Finding], operator.add]

    # Synthesis output
    report: str
    citations: dict[int, dict]

