from pydantic import BaseModel, Field
from typing import Literal

Mode = Literal["competitive", "employer"]

class AnalyzeRequest(BaseModel):
    company: str = Field(min_length=1, max_length=120)
    mode: Mode = "competitive"

class AnalyzeResponse(BaseModel):
    job_id: str
    status: str

class JobStatusResponse(BaseModel):
    job_id: str
    company: str
    mode: Mode
    status: str
    error: str | None = None
    report: str | None = None
    citations: dict[str, dict] | None = None
    verdict: dict | None = None

    