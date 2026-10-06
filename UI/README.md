# Radar.io — Frontend

**Live progress, cited reports, and a UI that gets out of the way.**

A React + Vite + TypeScript frontend for the Radar.io competitive
intelligence backend. Type a company name, watch the multi-agent
pipeline run in real time, read the SWOT report with clickable
citations.

---

## Table of Contents

- [What it does](#what-it-does)
- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [Getting started](#getting-started)
- [How SSE works here](#how-sse-works-here)
- [Component guide](#component-guide)
- [Design decisions](#design-decisions)
- [Debugging stories](#debugging-stories)
- [Known limitations](#known-limitations)
- [What's next](#whats-next)

---

## What it does

The frontend is a single-page app with one job: take a company name,
stream the backend's research progress, and render the resulting report.

1. **Search** — user types a company name or clicks an example pill.
2. **POST** `/analyze` returns a `job_id` in under a second.
3. **Subscribe** to `/analyze/{job_id}/stream` via `EventSource`.
4. **Progress panel** shows sub-tasks appearing as the planner emits
   them, then checking off one-by-one as each parallel researcher
   finishes.
5. **Report** renders when the `complete` event arrives — split into
   color-coded SWOT sections, with `[N]` markers turned into clickable
   source links.
6. **Sources** list at the bottom shows every URL with a favicon and
   the task that surfaced it.

The whole experience is designed around one principle: **the user should
never wonder whether something is happening.** Every state transition
has a visible signal.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Browser                                                        │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  App.tsx  (state machine)                                  │ │
│  │  ─────────────────────────────                             │ │
│  │  • POST /analyze → jobId                                   │ │
│  │  • EventSource(/stream) → reducer → setState               │ │
│  │  • Renders: SearchBox, ProgressPanel, StatBar, ReportView  │ │
│  └──────────┬─────────────────────────────────────────────────┘ │
│             │  fetch + SSE (proxied by Vite)                    │
└─────────────┼───────────────────────────────────────────────────┘
              │
              ▼
     ┌────────────────┐
     │ Vite dev proxy │  /analyze  →  http://backend:8000
     └────────┬───────┘
              │
              ▼
     ┌────────────────┐
     │ FastAPI backend│  (see ../backend/README.md)
     └────────────────┘
```

No CORS configuration anywhere. Vite's dev server proxies `/analyze` to
the backend inside the Docker network, so the browser sees one origin.

---

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Framework | **React 18** | Component model, hooks, mature ecosystem |
| Build | **Vite 5** | Instant HMR, near-zero config, fast builds |
| Language | **TypeScript** | Discriminated unions make the SSE event handling type-safe |
| Markdown | **react-markdown + remark-gfm** | Renders the report; GFM for tables |
| Streaming | **Native `EventSource`** | No library needed; auto-reconnect built in |
| Styling | **Plain CSS with custom properties** | No build-step bloat; themable via `:root` |
| Icons | **Google favicon service** | One HTTP request per source, no assets to bundle |

No state management library. No CSS framework. No component library.
Every dependency earns its place.

---

## Getting started

### Prerequisites

- Docker + Docker Compose
- Backend running (`docker compose up -d db backend`)

### Run via Docker

```bash
# From repo root
docker compose build frontend
docker compose up -d frontend
```

Open **http://localhost:5173**.

The Vite dev server runs inside the container with HMR. Editing any file
under `UI/src/` triggers an instant re-render — no rebuild, no refresh.

### Run locally (no Docker)

Requires Node 20+.

```bash
cd UI
npm install
npm run dev
```

But the backend proxy target changes when running on the host — you need
a `.env.local`:

```env
VITE_BACKEND_URL=http://localhost:8000
```

Then `npm run dev` and open `http://localhost:5173`.

### Build for production

```bash
npm run build     # emits UI/dist/
npm run preview   # serve it locally to sanity-check
```

For deploying: see the multi-stage Dockerfile sketch in the backend
README's "Production build" note. Short version: build with Node, serve
the static assets with nginx, and proxy `/analyze` to the backend.

---

## How SSE works here

Server-Sent Events are the backbone of the live progress UI. Worth
understanding exactly how they flow through this codebase.

### Wire format

The backend sends one line per event:

```
data: {"type":"node","node":"researcher","task_id":"recent_funding","doc_count":3}

data: {"type":"node","node":"researcher","task_id":"product_launches","doc_count":3}

data: {"type":"complete","report":"## Executive Summary\n...","citations":{...}}
```

Two newlines terminate each event. `EventSource` parses this
automatically — you just handle `.onmessage`.

### The subscription lifecycle

In `src/api.ts`:

```ts
export function subscribeToJob(jobId, onEvent, onTransportError) {
  const es = new EventSource(`/analyze/${jobId}/stream`);
  es.onmessage = (msg) => {
    const event = JSON.parse(msg.data) as SSEEvent;
    onEvent(event);
    if (event.type === "complete" || event.type === "error") {
      es.close();     // explicit close stops the reconnect loop
    }
  };
  es.onerror = (err) => {
    if (es.readyState === EventSource.CLOSED) return;
    onTransportError(err);
  };
  return () => es.close();
}
```

Four details that matter:

1. **Explicit `es.close()` on terminal events.** `EventSource` auto-
   reconnects on any disconnect. Without closing, the browser would
   re-request the stream forever after the job finishes, replaying the
   history each time.

2. **The `readyState === CLOSED` guard in `onerror`.** EventSource fires
   `onerror` even on the clean close we just triggered. Without the
   guard, the UI would flash an error at the exact moment the job
   succeeded.

3. **Auto-reconnect is a feature.** If the network hiccups mid-run,
   EventSource reconnects automatically. Because our backend replays
   event history to new subscribers, the reconnected client catches up
   seamlessly.

4. **Return a cleanup function.** `App.tsx` stores it in a ref and calls
   it before starting a second run — otherwise the first run's events
   would keep mutating state after the second began.

### The reducer in `App.tsx`

Every event flows through one `switch` that updates React state:

```tsx
setState((s) => {
  switch (event.type) {
    case "start":     return s;
    case "node":      /* update subTasks or completedTasks */
    case "complete":  return { ...s, status: "complete", report, citations };
    case "error":     return { ...s, status: "error", error: event.message };
  }
});
```

Note the **functional form** of `setState`. Multiple events can arrive
before React batches a re-render. Using `setState(newState)` would read
a stale closure; `setState((s) => ...)` guarantees we see the latest
state. This is the #1 streaming bug in React.

---

## Component guide

Six components. Each one owns one thing.

| Component | Responsibility |
|---|---|
| `App.tsx` | Owns all state. Renders everything else. |
| `SearchBox.tsx` | Controlled input + submit. Local `useState` only. |
| `EmptyState.tsx` | Hero example pills shown before first run. |
| `ProgressPanel.tsx` | Status dot + sub-task list with check-off animation. |
| `StatBar.tsx` | Company / sub-task count / source count / duration. |
| `ReportView.tsx` | Renders the markdown, splits sections, wires citations. |
| `Citation.tsx` | One source row: index, favicon, short URL, task badge. |

### Why `ReportView` has four helper functions

The report comes back as a raw markdown string. Rendering it well
requires four transforms, in order:

```ts
normalizeHeaders(report)          // `**## Foo**` → `## Foo`
injectCitationLinks(normalized)   // `[1]` → `[1](https://...)`
splitSections(withLinks)          // slice by `^## `
// then render each section with a color class based on its title
```

**Order matters.** `splitSections` matches `^## `, so if headers are
still wrapped in `**...**`, the regex misses them and the whole report
ends up in one unstyled section. Normalize first, split second.

**Splitting is the design lever.** Instead of one markdown blob with
markdown's default styling, each SWOT section gets its own
`.report-section` card with a colored left bar (green for Strengths, red
for Weaknesses, etc.) and an uppercase header. The report becomes a
visual artifact, not a wall of text.

### Why `Citation` uses the Google favicon service

```ts
`https://www.google.com/s2/favicons?domain=${domain}&sz=32`
```

One HTTP request per source, no assets to bundle, no backend work.
Adding favicons would otherwise require fetching each source's HTML and
parsing `<link rel="icon">` — a lot of complexity for a cosmetic win.
The service is public, fast, and cache-friendly.

Trade-off: it reveals source domains to Google. For a portfolio project
that's fine; for a privacy-sensitive deployment, you'd proxy through
your own backend or drop the favicons.

---

## Design decisions

### Why Vite's dev proxy instead of CORS

Three options when frontend and backend run on different ports:

1. **Enable CORS on the backend.** Works, but you now maintain a
   `CORSMiddleware` config, deal with preflight requests, and hit
   subtle bugs when the request origin drifts (localhost vs 127.0.0.1
   vs the Docker service name).
2. **Serve the frontend from the backend.** Couples build tooling and
   makes iteration sluggish — no HMR through a Python server.
3. **Proxy through Vite.** Frontend fetches `/analyze`; Vite forwards
   it to `http://backend:8000`. From the browser's perspective, both
   are same-origin.

Option 3 has zero config on the backend and zero CORS concepts for
the developer to internalize. It's the standard pattern for dev
environments with two services.

The proxy target is `http://backend:8000` inside Docker (service name),
`http://localhost:8000` on the host. `VITE_BACKEND_URL` switches between
them.

### Why only `src/`, `index.html`, and `vite.config.ts` are bind-mounted

A tempting shortcut is `./UI:/app` — mount the whole frontend folder into
the container. This **breaks on Windows and macOS hosts** because the
container's Linux `node_modules` would be shadowed by the host's
`node_modules` (built for the wrong OS). Vite would try to run Windows
binaries inside Linux. Instant crash.

The fix: mount only the files that change. `node_modules` stays where
Docker put it. The `.dockerignore` file keeps it out of the build
context too.

**Consequence:** adding a new top-level source file (say, `.env.local`)
requires adding a mount line to `docker-compose.yml`. Annoying once,
correct forever.

### Why no CSS framework

Tailwind is great. So is vanilla-extract, styled-components, and CSS
Modules. For a project this size, none of them earn their weight over
plain CSS with custom properties:

- **Theming via `:root`** is one file, one edit.
- **No build-step parser** means faster HMR and one less thing to
  configure.
- **Class names like `.report-section.strengths`** are self-documenting
  in DevTools.

The cost is that if the app grows to 40 components, you'd want
something more structured. At 6 components, plain CSS wins.

### Why `setState((s) => ...)` everywhere

React batches `setState` calls within the same tick. When five SSE
events arrive back-to-back (as they do when the researchers finish in
parallel), naive `setState({...state, x: newX})` reads a stale `state`
closure for the second through fifth events. The last write wins;
earlier updates are silently lost.

The functional form `setState((s) => ({ ...s, x: newX }))` guarantees
each updater runs against the freshest state React has. This is
non-negotiable in any streaming UI.

---

## Known limitations

- **No retry on the initial POST.** If `/analyze` fails (backend down,
  network blip), the user sees an error and has to click again. Fix:
  wrap `startAnalysis` in a small retry or surface a "Retry" button.

- **`EventSource` only works on the same origin.** We proxy through
  Vite, which works, but a production deployment with separate
  `api.example.com` and `app.example.com` domains needs CORS on the
  SSE endpoint (`Access-Control-Allow-Origin`). Straightforward but
  undocumented here.

- **No persistence across reloads.** If you refresh mid-run, the SSE
  connection drops and the job's progress is lost from the UI (the
  backend still has it). Fix: store `jobId` in `localStorage`, re-subscribe
  on mount. The backend already supports this — it replays event history
  to late subscribers.

- **Report rendering depends on well-formed markdown.** If the LLM
  emits something `react-markdown` can't parse (rare, but happens with
  malformed tables), the raw text renders instead. Fix: a markdown
  sanitizer pass, or catch render errors with an error boundary.

- **No streaming of the report text itself.** The report arrives in one
  `complete` event after the synthesizer finishes. A nicer UX would be
  token-level streaming (via `TextDecoderStream` on a fetch response),
  but it complicates the pipeline for a small visual win. Noted as a
  possible improvement.

- **The Docker dev container has no production build.** We serve via
  Vite's dev server. For deployment you'd want a multi-stage build that
  emits static files, served by nginx. Sketched in the backend README.

---

## What's next

- **Employer mode selector** — a segmented control above the search box
  that switches between "Competitor analysis" and "Employer report."
  Same SSE flow, different report shape.

- **Persist `jobId` in `localStorage`** — reconnect to a running job on
  page refresh. Small change, big UX improvement.

- **Source hover previews** — instead of just a URL on hover, show the
  first 200 chars of the scraped content. Turns "trust the link" into
  "here's the receipt."

- **Token-level report streaming** — pipe the synthesizer's output
  through SSE as tokens arrive, so the report types itself onto the
  page. Feels faster even when it isn't.

- **Export as PDF** — a "Download report" button that renders the
  ReportView to a printable PDF. Uses the browser's print stylesheet;
  ~30 lines of CSS plus a button.

---