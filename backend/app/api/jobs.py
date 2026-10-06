"""
In memory job registry + pub/sub for SSE.

A Job holds:
    - a metadata(id, company, status)
    - a full event history(for late subscribers)
    - a list of live subscriber queues

"""
import asyncio
import uuid
from dataclasses import dataclass, field
from typing import AsyncIterator

@dataclass
class Job:
    job_id: str
    company: str
    status: str = "pending"
    events: list[dict] = field(default_factory=list)
    subscribers: list[asyncio.Queue] = field(default_factory=list)
    final_state: dict | None = None
    error: str | None = None

    def emit(self, event: dict) -> None:
        """Append to history and fan out to every live subscriber."""
        self.events.append(event)
        for q in self.subscribers:
            q.put_nowait(event)

    async def subscribe(self) -> AsyncIterator[dict]:
        """
        Yield events forever. New subscribers first get full history
        and then live events as they arrive.
        """ 
        q: asyncio.Queue = asyncio.Queue()
        for e in self.events:
            q.put_nowait(e)

        # If the job already finished, just drain and return
        if self.status in ("complete", "error"):
            while not q.empty():
                yield q.get_nowait()

            return

        self.subscribers.append(q)
        try:
            while True:
                event = await q.get()
                yield event
                if event.get("type") in ("complete", "error"):
                    break

        finally:
            if q in self.subscribers:
                self.subscribers.remove(q)

# The registry. One process, one dict.
_JOBS: dict[str, Job] = {}

def create_job(company: str) -> Job:
    job_id = uuid.uuid4().hex
    job = Job(job_id=job_id, company=company)
    _JOBS[job_id] = job
    return job

def get_job(job_id: str) -> Job | None:
    return _JOBS.get(job_id)