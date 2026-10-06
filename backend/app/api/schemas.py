from pydantic import BaseModel, Field

class AnalyzeRequest(BaseModel):
    company: str = Field(min_length=1, max_length=120)

class AnalyzeResponse(BaseModel):
    job_id: str
    status: str

class JobStatusResponse(BaseModel):
    job_id: str
    company: str
    status: str
    error: str | None = None
    report: str | None = None
    citations: dict[str, dict] | None = None

    