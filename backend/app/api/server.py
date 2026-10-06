"""
FastAPI wrapper around the LangGraph research graph.

Endpoints:
    POST /analyze                   -> start a job, return job_id
    GET  /analyze/{job_id}          -> fetch job status + final state (polling)
    GET  /analyze/{job_id}/stream   -> SSE stream of progress events
    GET  /health                    -> liveness probe
"""

import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from rich import print as rprint

from app.api.jobs import Job, create_job, get_job
from app.api.schemas import AnalyzeRequest, AnalyzeResponse, JobStatusResponse
from app.db.schema import ensure_schema
from app.graph import build_graph

# The compiled graph is stateful (holds a MemorySaver checkpointer) so we build it once
# at startup and reuse it across requests.

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure the pgvector schema exists before we accept traffic.
    await ensure_schema()
    rprint("[bold green] schema ready, API listening[/bold green]")
    yield

app = FastAPI(title="Radar.io", lifespan=lifespan)

# Compiled once, shared across all requests.
_graph = build_graph(with_checkpointer=True)

def _summarize_update(node_name: str, update: dict | None) -> dict:
    """
    Reduce a node's state delta to a small JSON-safe payload.
    """
    if not update:
        return {}

    if node_name == "planner":
        tasks = update.get("sub_tasks", [])
        return {
            "sub_task_count": len(tasks),
            "sub_tasks": [{"id": t.id, "question": t.question} for t in tasks],
        }

    if node_name == "researcher":
        findings = update.get("findings", [])
        return {
            "task_id": findings[0].task_id if findings else None,
            "doc_count": len(update.get("docs", [])),
        }

    if node_name == "synthesizer":
        return {"report_chars": len(update.get("report", ""))}

    return {}

async def _run_graph(job: Job) -> None:
    """
    Runs the graph for one job, emitting SSE events as nodes complete.
    """
    job.status = "running"
    job.emit({"type": "start", "company": job.company})

    try:
        config = {"configurable": {"thread_id": job.job_id}}

        async for chunk in _graph.astream({"company": job.company}, config=config):
            for node_name, update in chunk.items():
                job.emit({
                    "type": "node",
                    "node": node_name,
                    **_summarize_update(node_name, update),
                })

        # After the stream ends, ask the checkpointer for the full state.
        snapshot = await _graph.aget_state(config)
        job.final_state = dict(snapshot.values)

        # `citations` uses int keys: JSON keys must be strings.
        citations = {
            str(k): v for k, v in job.final_state.get("citations", {}).items()
        }

        job.emit({
            "type": "complete",
            "report": job.final_state.get("report", ""),
            "citations": citations,
        })
        job.status = "complete"

    except Exception as e:
        job.status = "error"
        job.error = str(e)
        rprint(f"[red]job {job.job_id} failed: {e}[/red]")
        job.emit({"type": "error", "message": str(e)})

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/analyze", response_model=AnalyzeResponse)
async def start_analysis(req: AnalyzeRequest):
    job = create_job(req.company)
    # Task keeps running even after this handler returns.
    asyncio.create_task(_run_graph(job))
    rprint(f"[cyan]-> job {job.job_id} started for {req.company}[/cyan]")
    return AnalyzeResponse(job_id=job.job_id, status=job.status)

@app.get("/analyze/{job_id}", response_model=JobStatusResponse)
async def get_analysis(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "job not found")

    citations = None
    report = None
    if job.final_state:
        report = job.final_state.get("report")
        citations = {
            str(k): v for k, v in job.final_state.get("citations", {}).items()
        }

    return JobStatusResponse(
        job_id=job.job_id,
        company=job.company,
        status=job.status,
        error=job.error,
        report=report,
        citations=citations,
    )

@app.get("/analyze/{job_id}/stream")
async def stream_analysis(job_id: str, request: Request):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "job not found")

    async def event_source():
        try:
            async for event in job.subscribe():
                payload = json.dumps(event, default=str)
                yield f"data: {payload}\n\n"

        except asyncio.CancelledError:
            # Client disconnected, job keeps running in the background
            # a reconnecting client will replay from history

            rprint(f"[yellow]client disconnected from {job_id}[/yellow]")
            raise

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )