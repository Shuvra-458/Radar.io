# Radar.io

**Competitive intelligence, on demand. Type a company name. Get a cited SWOT report in under a minute.**

Radar.io is a multi-agent research pipeline that browses the live web —
search, scrapes, reads, and reasons — then writes a structured
competitive analysis with every claim traceable to a source URL. It
runs entirely on free-tier APIs and Docker Compose.

[Backend README →](backend/README.md) · [Frontend README →](UI/README.md)

---

## Why this exists

Most "AI research tools" are wrappers around a single LLM prompt. They
hallucinate, they can't cite sources, and they're impossible to debug
when they go wrong.

Radar.io is built the other way around:

- **A real graph, not a prompt chain.** LangGraph orchestrates a
  planner, N parallel researchers, a synthesizer, and a citation
  validator. Each node has one job.
- **Every claim is grounded.** The report contains `[N]` markers that
  link to actual source URLs. A deterministic validator catches
  hallucinated citations before they reach the user.
- **Live progress, not a spinner.** Server-Sent Events stream each
  node's completion to the browser as it happens. You watch the
  researchers fan out and finish in real time.
- **Runs on free tiers.** Groq for the LLM, Google for embeddings,
  Tavily for search. No OpenAI key, no credit card, no surprises.

It's a portfolio project, but it's built the way you'd build the real
thing — because the interesting part of agent engineering is the
architecture, not the API call.

---

## Architecture at a glance

```
       Browser  ──── POST /analyze ────▶  FastAPI
          ▲                                  │
          │                                  ▼
          │                          ┌───────────────┐
          │                          │   planner     │  1 LLM call
          │                          └───────┬───────┘
          │                                  │  Send × N (fan-out)
          │                    ┌─────────────┼─────────────┐
          │                    ▼             ▼             ▼
          │              ┌──────────┐  ┌──────────┐  ┌──────────┐
          │              │ research │  │ research │  │ research │
          │              │  search  │  │  search  │  │  search  │
          │              │  scrape  │  │  scrape  │  │  scrape  │
          │              │  embed   │  │  embed   │  │  embed   │
          │              └────┬─────┘  └────┬─────┘  └────┬─────┘
          │                   │             │             │
          │                   └─────────────┼─────────────┘
          │                                 ▼
          │                          ┌───────────────┐
          │                          │  synthesizer  │  1 LLM call
          │                          └───────┬───────┘
          │                                  ▼
          │                          ┌───────────────┐
          │                          │  citation     │  deterministic
          │                          └───────┬───────┘
          │                                  │
          └──── SSE stream ◀────────────────┘

     pgvector (Postgres) persists every retrieved document.
```

The whole pipeline — plan, fan out, join, synthesize, validate — is
declared as a LangGraph state machine. Adding a new research angle means
adding a node, not rewriting control flow.

---

## Try it

Requires Docker and three free API keys.

```bash
# 1. Clone and configure
git clone Shuvra-458/radar-io
cd radar-io

# 2. Add your API keys
cat > backend/.env <<'EOF'
GROQ_API_KEY=gsk_...          # https://console.groq.com/keys
GOOGLE_API_KEY=...            # https://aistudio.google.com/app/apikey
TAVILY_API_KEY=tvly-...       # https://tavily.com
EOF

# 3. Start everything
docker compose up -d

# 4. Open the app
open http://localhost:5173   # or just visit it in your browser
```

Type a company name — `Stripe`, `Notion`, `Flipkart`, anything — and
watch the researchers work. A typical run takes 30–45 seconds and
produces a 4–5 section SWOT report with 10–15 cited sources.

### Just want the API?

```bash
curl -X POST http://localhost:8000/analyze \
     -H 'Content-Type: application/json' \
     -d '{"company": "Stripe"}'
# → {"job_id": "abc123...", "status": "pending"}

curl -N http://localhost:8000/analyze/abc123/stream
# → streams progress events as JSON
```

Full API reference in the [backend README](backend/README.md).

---

## What makes it interesting (for the technically curious)

**LangGraph fan-out with the `Send` API.** The planner doesn't call the
researchers in a loop. It returns a list of `Send` objects, and
LangGraph spawns N concurrent invocations. The graph engine tracks the
join for us — the synthesizer runs only after every branch completes.
[Details →](backend/README.md#2-send-api-for-fan-out)

**State with reducers.** Parallel branches write to the same `docs` and
`findings` fields. Without a reducer, the last branch to finish silently
overwrites the other four. We use `Annotated[list, operator.add]` so
writes accumulate.
[Details →](backend/README.md#1-state-with-reducers)

**Two levels of parallelism.** Inside each researcher, `asyncio.gather`
scrapes four URLs concurrently. Across the graph, `Send` runs N
researchers concurrently. Different mechanisms for different scopes.

**Citation validation as a first-class node.** The synthesizer's job is
to write; the citation node's job is to verify. A parser extracts every
`[N]` marker from the report and checks it against the source map.
Hallucinated citations get flagged. It's a small, deterministic
security layer over an inherently fuzzy process.

**A readability pass in the scraper.** `BeautifulSoup.get_text()` on a
modern news page returns nav chrome before any real content. We prefer
`<article>` / `<main>` containers, then filter to `<p>` / `<h1-3>` /
`<li>` tags with length > 40. This one change was the difference
between "mostly nav links" and "mostly article body."
[Details →](backend/README.md#why-the-readability-pass-in-the-scraper)

**Provider-agnostic.** Groq, Google, or any OpenAI-compatible LLM
behind a single `make_llm()` factory. Swapping providers is a two-line
change in one file.

---

## Repo layout

```
radar.io/
├── backend/           FastAPI + LangGraph pipeline (Python 3.11)
│   ├── app/
│   │   ├── nodes/     planner · researcher · synthesizer · citations
│   │   ├── tools/     tavily search · httpx scraper
│   │   ├── db/        pgvector schema + queries
│   │   └── api/       FastAPI server + SSE + job registry
│   └── README.md      ← full backend docs
│
├── UI/                React + Vite + TypeScript frontend
│   └── src/
│       ├── App.tsx    state machine + SSE reducer
│       └── components/
│   └── README.md      ← full frontend docs
│
├── docker-compose.yml 4 services: db · backend · frontend · dev
└── README.md          ← you are here
```

---

## Tech stack

| Layer | Choice |
|---|---|
| Agent orchestration | **LangGraph** (StateGraph, `Send`, `MemorySaver`) |
| LLM | **Groq** — `gpt-oss-120b` (planner) + `qwen3.8-27b` (researchers) |
| Embeddings | **Google `gemini-embedding-001`** (768d via Matryoshka truncation) |
| Search | **Tavily** (LLM-optimized snippets) |
| Scraping | **httpx** + **BeautifulSoup** with readability filtering |
| Vector store | **pgvector** on Postgres 16, HNSW index |
| Backend API | **FastAPI** + Server-Sent Events |
| Frontend | **React 18** + **Vite** + **TypeScript** |
| Container | **Docker Compose** (4 services) |

No OpenAI. No paid APIs. Runs end-to-end on free tiers.

---

## Known limitations

Honest about what this is and isn't:

- **Not production-hardened.** Jobs are in-memory (lost on restart), no
  auth, single-worker only. The backend README documents the fix for
  each.
- **No claim-level entailment.** Citations are validated for *existence*
  (`[N]` must map to a source), not *support* (does the source actually
  say this?). That's the biggest remaining grounding gap.
- **Search recency is uncontrolled.** Tavily returns what's indexed. A
  query about "2024 earnings" can surface a 2019 survey. Fixable with
  `start_published_date` filtering.
- **Free-tier rate limits are real.** The pipeline handles them with
  semaphores and retries, but a burst of concurrent runs will still
  queue.

Each of these is a "next step," not a flaw — but the README lists them
because honest engineering means knowing where the edges are.

---

## What's next

- **Employer mode** — swap the planner prompt and add a red-flag scorer;
  produce a "should I work here?" report over the same graph.
- **AsyncPostgresSaver** — persist graph state across backend restarts.
- **Token-level report streaming** — pipe the synthesizer's output
  through SSE token-by-token so the report types itself onto the page.
- **Source previews on hover** — show the first 200 chars of scraped
  content next to every citation.

---

## License

MIT — use it, fork it, ship it.

---

<p align="center">
  <sub>Built by <a href="https://github.com/Shuvra-458">@Shuvra-458</a>. Feedback welcome.</sub>
</p>


