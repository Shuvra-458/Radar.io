# Radar.io — Backend

**Multi-agent competitive intelligence from live web research.**

Give it a company name. It plans a research strategy, fans out parallel
web researchers, distills findings, persists everything to pgvector, and
writes a citation-grounded SWOT report — all streamed live over SSE.

Built with **LangGraph**, **Groq**, **Tavily**, and **pgvector**.

---

## Table of Contents

- [What it does](#what-it-does)
- [Architecture](#architecture)
- [LangGraph concepts](#langgraph-concepts)
- [Tech stack](#tech-stack)
- [Getting started](#getting-started)
- [API reference](#api-reference)
- [Project layout](#project-layout)
- [Design decisions](#design-decisions)
- [Debugging stories](#debugging-stories)
- [Known limitations](#known-limitations)
- [What's next](#whats-next)
- [License](#license)

---

## What it does

Given a company name, the backend:

1. **Plans** 3–6 research sub-tasks covering funding, product, sentiment,
   partnerships, and pricing.
2. **Fans out** to N parallel researchers — each one searches the web via
   Tavily, scrapes the top hits, and summarizes findings.
3. **Persists** every scraped document to pgvector with 768-dim embeddings,
   so the corpus is queryable later.
4. **Synthesizes** a SWOT report in which every factual claim is
   traceable to a source URL.
5. **Validates** citations — hallucinated `[N]` markers are flagged; sources
   that were retrieved but never cited are reported.
6. **Streams** all of this over SSE so a frontend can show live progress.

The graph is provider-agnostic. It currently runs on Groq for the LLM
and Google for embeddings, but swapping either is a two-line change in
one file.

---

## Architecture

```
                  POST /analyze
                        │
                        ▼
              ┌──────────────────┐
              │   planner        │  LLM breaks "Analyze Company X"
              │   (1 call)       │  into 3–6 sub-tasks
              └────────┬─────────┘
                       │  fan_out → [Send, Send, ..., Send]
         ┌─────────────┼─────────────┬─────────────┬─────────────┐
         ▼             ▼             ▼             ▼             ▼
    ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
    │research │   │research │   │research │   │research │   │research │
    │  er     │   │  er     │   │  er     │   │  er     │   │  er     │
    │         │   │         │   │         │   │         │   │         │
    │ search  │   │ search  │   │ search  │   │ search  │   │ search  │
    │ scrape  │   │ scrape  │   │ scrape  │   │ scrape  │   │ scrape  │
    │ embed   │   │ embed   │   │ embed   │   │ embed   │   │ embed   │
    │ summarize│  │ summarize│  │ summarize│  │ summarize│  │ summarize│
    └────┬────┘   └────┬────┘   └────┬────┘   └────┬────┘   └────┬────┘
         │             │             │             │             │
         └─────────────┴──────┬──────┴─────────────┴─────────────┘
                              │  implicit join
                              ▼
                    ┌──────────────────┐
                    │  synthesizer     │  one big LLM call:
                    │  (1 call)        │  findings → SWOT markdown
                    └────────┬─────────┘
                             ▼
                    ┌──────────────────┐
                    │  citation        │  validate [N] markers,
                    │  (deterministic) │  report unused sources
                    └────────┬─────────┘
                             ▼
                          END

Side channels:  pgvector (persistence) · SSE (live events)
```

Total LLM calls per run: **1 (planner) + N (researchers) + 1 (synthesizer)**,
where N is 3–6. The citation node is pure Python — no LLM.

---

## LangGraph concepts

This project uses four LangGraph primitives. Understanding them is
understanding the whole architecture.

### 1. State with reducers

State is a `TypedDict`. Fields that multiple parallel nodes write to
must have a **reducer** — a function that tells LangGraph how to merge
concurrent writes.

```python
class ResearchState(TypedDict, total=False):
    company:    str
    sub_tasks:  list[SubTask]                    # single writer, no reducer

    # Parallel writers → reducer required. Without operator.add, the last
    # researcher to finish silently overwrites the other four.
    docs:     Annotated[list[SourceDoc], operator.add]
    findings: Annotated[list[Finding],   operator.add]

    report:    str
    citations: dict[int, dict]
```

This is the #1 gotcha in LangGraph. Every field that a fanned-out node
writes needs a reducer; everything else should not have one.

### 2. `Send` API for fan-out

Instead of a normal edge, `add_conditional_edges` takes a function that
returns a **list of `Send` objects** — one per parallel branch.

```python
def fan_out(state: ResearchState) -> list[Send]:
    return [
        Send("researcher", {"company": state["company"], "sub_task": t})
        for t in state["sub_tasks"]
    ]
```

LangGraph spawns one invocation of `researcher` per `Send`. Each branch
receives a merged state containing the shared `company` field and its
own `sub_task` — not the others'.

### 3. Edges as implicit joins

```python
graph.add_edge("researcher", "synthesizer")
```

This looks like a normal edge. It's actually a **barrier**: `synthesizer`
does not run until every branch spawned from the planner has completed.
The join is declarative; you never write "wait for all tasks."

### 4. Checkpointer for state retrieval

The graph is compiled with `MemorySaver`:

```python
graph.compile(checkpointer=MemorySaver())
```

This makes `graph.aget_state({"configurable": {"thread_id": job_id}})`
return the complete state after a run — no manual accumulation of
`astream` deltas. The FastAPI layer uses it to serve the final report.

---

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Orchestration | **LangGraph** | Explicit graph, first-class fan-out + join semantics |
| LLM | **Groq** (`gpt-oss-120b`, `qwen3.8-27b`) | Free tier, fast, reliable |
| Embeddings | **Google `gemini-embedding-001`** | Free, 768 dims (Matryoshka truncation) |
| Search | **Tavily** | LLM-optimized snippets, returns clean text |
| Scraping | **httpx + BeautifulSoup** | Async, no headless browser needed |
| Vector store | **pgvector (Postgres 16)** | Production-typical; real SQL, real indexes |
| API | **FastAPI** | Async-native, SSE fits cleanly |
| Logging | **rich** | Readable dev output, renders the report in the terminal |

No OpenAI, no Anthropic, no paid services. Runs entirely on free tiers.

---

## Getting started

### Prerequisites

- Docker + Docker Compose
- Free API keys:
  - **Groq**: https://console.groq.com/keys
  - **Google Gemini**: https://aistudio.google.com/app/apikey
  - **Tavily**: https://tavily.com

### Configuration

Create `backend/.env`:

```env
GROQ_API_KEY=gsk_...
GOOGLE_API_KEY=...
TAVILY_API_KEY=tvly-...
```

The `DATABASE_URL` is set in `docker-compose.yml`, not `.env` — it
depends on the Docker network service name (`db`), so it belongs with
the compose config.

### Run

```bash
docker compose build backend
docker compose up -d db backend

# Watch it start up
docker compose logs -f backend

# Fire a request
curl -s -X POST http://localhost:8000/analyze \
     -H 'Content-Type: application/json' \
     -d '{"company": "Stripe"}'
# → {"job_id":"abc123...","status":"pending"}

# Stream progress
curl -N http://localhost:8000/analyze/abc123/stream
```

### CLI mode (no HTTP)

For quick iteration on the graph itself:

```bash
docker compose run --rm backend python -m app.main Stripe
```

This runs the same graph once, prints node progress, and renders the
final report as formatted markdown in the terminal. No SSE, no job
registry — just the graph.

### Smoke tests

Two isolated scripts verify the storage layer and the tools layer
independently of the graph:

```bash
docker compose run --rm backend python -m app.scripts.test_storage
docker compose run --rm backend python -m app.scripts.test_tools
```

Debugging agent pipelines is much easier when you can verify each
primitive in isolation before wiring them together.

---

## API reference

### `POST /analyze`

Start a research job.

**Request:**
```json
{ "company": "Stripe" }
```

**Response:** `202` semantics on a 200 status (fire-and-forget)
```json
{ "job_id": "0c7f8be0...", "status": "pending" }
```

Returns in <50 ms. The graph runs in an `asyncio.create_task` decoupled
from the HTTP request.

### `GET /analyze/{job_id}`

Polling endpoint. Returns the final report and citations once
`status == "complete"`.

```json
{
  "job_id": "0c7f8be0...",
  "company": "Stripe",
  "status": "complete",
  "report": "## Executive Summary\n...",
  "citations": {
    "1": { "url": "https://...", "task_id": "recent_funding" },
    "2": { "url": "https://...", "task_id": "product_launches" }
  }
}
```

### `GET /analyze/{job_id}/stream`

Server-Sent Events stream. Every event is a JSON object on a `data:` line.

**Event types:**

| Type | Payload |
|---|---|
| `start` | `{ "company": "Stripe" }` |
| `node` (planner) | `{ "sub_task_count": 5, "sub_tasks": [...] }` |
| `node` (researcher) | `{ "task_id": "recent_funding", "doc_count": 3 }` |
| `node` (synthesizer) | `{ "report_chars": 3329 }` |
| `node` (citation) | `{}` |
| `complete` | `{ "report": "...", "citations": {...} }` |
| `error` | `{ "message": "..." }` |

**Late subscribers:** the job registry stores full event history, so a
client that connects after the POST replays from the beginning, then
tails the live queue. No missed events.

### `GET /health`

Liveness probe. Returns `{"status": "ok"}`.

---

## Project layout

```
backend/
├── app/
│   ├── __init__.py
│   ├── config.py              # env vars, model names, dimensions
│   ├── llm.py                 # Groq client + retry logic
│   ├── embeddings.py          # Gemini embeddings + Matryoshka truncation
│   ├── state.py               # ResearchState TypedDict + Pydantic models
│   ├── graph.py               # graph construction + fan-out function
│   ├── main.py                # CLI entry point
│   │
│   ├── api/
│   │   ├── server.py          # FastAPI app, SSE endpoints
│   │   ├── jobs.py            # in-memory job registry + pub/sub
│   │   └── schemas.py         # request/response Pydantic models
│   │
│   ├── nodes/
│   │   ├── planner.py         # company → 3–6 sub-tasks
│   │   ├── researcher.py      # one sub-task → docs + finding
│   │   ├── synthesizer.py     # findings → cited SWOT markdown
│   │   └── citations.py       # validate [N] markers, report unused
│   │
│   ├── db/
│   │   ├── connection.py      # async psycopg + pgvector registration
│   │   ├── schema.py          # CREATE TABLE IF NOT EXISTS + HNSW index
│   │   └── documents.py       # insert_docs() and search_docs()
│   │
│   ├── tools/
│   │   ├── search.py          # Tavily wrapper
│   │   └── scraper.py         # httpx + BeautifulSoup, readability pass
│   │
│   └── scripts/
│       ├── test_storage.py    # smoke test: embeddings + pgvector
│       ├── test_tools.py      # smoke test: search + scrape
│       └── test_summarize.py  # isolate one researcher's summarize step
│
├── db/
│   └── init.sql               # enables the `vector` extension
├── Dockerfile
├── requirements.txt
└── .env                       # NOT committed
```

---

## Design decisions

### Why pgvector instead of Chroma

Chroma is embedded — a Python library that writes to a directory. pgvector
is a real service. The distinction matters for a portfolio project:
"ran Postgres + pgvector in Docker Compose" reads differently to a
hiring manager than "used a vector library." It also forces you to
learn the production shape of the problem: schema design, migrations,
HNSW indexing, connection pooling.

Chroma is simpler and perfectly fine for prototypes. pgvector is what
you'd actually ship.

### Why the researcher node batches scraping with `asyncio.gather`

Two kinds of parallelism, both used:

- **Within a node:** one researcher searches, then scrapes 4 URLs
  concurrently with `asyncio.gather`. Same node, parallel IO.
- **Across nodes:** the `Send` fan-out runs N researchers in parallel.

They're different mechanisms solving different scopes. Using one where
the other belongs is a common mistake — `asyncio.gather` cannot do
LangGraph's fan-out, and `Send` cannot scrape 4 URLs inside one node.

### Why the readability pass in the scraper

`BeautifulSoup.get_text()` on a modern news page returns navigation
chrome ("About / Leadership / Contact / Privacy Policy...") before any
real content. Combined with per-doc truncation, this caused a full
debugging cycle where the LLM correctly reported "Insufficient
information found." — because it was looking at nav links.

The fix: prefer `<article>` / `<main>` / `role="main"`, then pull only
`<p>`, `<h1-3>`, `<li>` tags with length > 40 chars. This single change
took scraped-content quality from "mostly nav" to "mostly article."

### Why `output_dimensionality` is truncated in Python

`langchain-google-genai` versions below 2.0 silently drop the
`output_dimensionality` kwarg. Rather than depend on wrapper behavior,
`embeddings.py` calls the model at its native 3072 dims and truncates +
renormalizes to 768 in Python:

```python
def _truncate_normalize(vec: list[float], dim: int) -> list[float]:
    head = vec[:dim]
    norm = math.sqrt(sum(x * x for x in head))
    return [x / norm for x in head]
```

Matryoshka-trained models (which `gemini-embedding-001` is) are designed
for this. Renormalization is mandatory — cosine similarity assumes unit
vectors, and slicing breaks that assumption.

### Why `MemorySaver` instead of `AsyncPostgresSaver`

`MemorySaver` is in-process. Jobs are lost on backend restart. For a dev
tool that's fine; a production deployment would swap in the Postgres
checkpointer with a one-line import change. The LangGraph API surface
is identical.

---

## Known limitations

Honest list. Each is a "next step," not a bug:

- **Jobs are in-memory.** Backend restart wipes them. Fix: Redis for
  the event stream + `AsyncPostgresSaver` for graph state.
- **No auth.** Anyone with the URL can spawn jobs. Fix: API key header
  check or OAuth, depending on deployment.
- **No recency filter on search.** Tavily returns what's indexed; a
  query about "2024 earnings" can surface a 2019 survey (and did, in one
  run). Fix: pass `start_published_date` to Tavily, or post-filter by
  source metadata.
- **No claim-level entailment check.** The citation validator verifies
  `[N]` markers exist in the source map — it does not verify the source
  actually supports the claim. Fix: an LLM-judge step comparing each
  claim to its cited source. Out of scope for the current build; noted
  as the biggest remaining grounding gap.
- **Single-worker server.** The job registry is a Python dict, so
  `uvicorn --workers 4` would split jobs across processes. Fix: move the
  registry to Redis.
- **Windows host bind mounts are slow.** Volume I/O for `./backend/app`
  on Windows can make HMR sluggish. Not a bug; a known Docker Desktop
  quirk. Native Linux/Mac hosts are fine.

---

## What's next

- **Employer mode** — same graph, different planner prompt + a
  `redflag_scorer` node, producing a rubric-based "should I work here?"
  report. Same fan-out, same citations, same storage.
- **AsyncPostgresSaver** — persists graph state across restarts.
- **Claim-level citation validation** — the missing piece for full
  grounding.
- **Multilingual report output** — the LLM already handles it; just
  plumb a `language` field through state.

---

## License

MIT.
```
