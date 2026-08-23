# TrendFlow AI

**Autonomous RAG Content Engine** — PS1 · Trial 1: The Content Engine

TrendFlow AI retrieves current AI/technology trends, performs lightweight RAG retrieval over a source dataset, generates social-media-ready content **grounded in retrieved sources**, and executes publishing through the real **Swytchcode CLI** — with an optional daily 7:00 PM automation and a full execution log.

---

## Problem Statement

Content teams need to react to fast-moving tech trends daily. Manually monitoring trends, writing posts, and publishing is slow and ungrounded. TrendFlow AI automates the pipeline:

```
Current trends → RAG retrieval → relevant sources → LLM generation
              → Swytchcode execution → simulated/sandbox publish → execution log
```

## Architecture

```
TrendFlowAI/
├── backend/
│   ├── main.py                  # FastAPI app + REST API
│   ├── rag/
│   │   └── retriever.py         # TF-IDF retrieval + trend derivation (pure Python)
│   ├── services/
│   │   ├── llm.py               # LLM client (env-based) + grounding indicator
│   │   ├── pipeline.py          # orchestration + 19:00 asyncio scheduler
│   │   └── state.py             # JSON-backed state, counters, logs
│   ├── swytchcode/
│   │   ├── client.py            # hardened wrapper around `swytchcode exec`
│   │   └── policy.py            # strict allowlist of actions × run modes
│   ├── data/
│   │   └── sources.json         # DEMO source dataset (10 curated AI news items)
│   └── models/
│       └── schemas.py           # Pydantic request models
└── frontend/                    # React + Vite + Tailwind v4 dashboard
    └── src/components/          # Header, Trends, Sources, ContentPanel,
                                 # ExecutionPanel, Automation, Logs
```

- **Backend:** Python + FastAPI (`uvicorn`), no database — JSON file state.
- **RAG:** pure-Python TF-IDF with cosine similarity + tag boosts. Deliberately simple: no vector DB, no embeddings service. It genuinely retrieves, scores, and ranks documents.
- **LLM:** any OpenAI-compatible chat completions endpoint configured via env vars.
- **Swytchcode:** the installed npm CLI invoked as a subprocess (`swytchcode exec stripe.create_payment --demo --json --body <file>`). The structured JSON result is captured, displayed, and logged.

## RAG Workflow

1. **Live source, NewsAPI (primary):** if `NEWSAPI_KEY` is set in `backend/.env`, the backend fetches technology top-headlines (`newsapi.org/v2/top-headlines`, cached <=10 min) and optionally GNews top-headlines (`GNEWS_API_KEY`). Articles are normalized into the retriever's document format (title, content/description, source name, URL, publication date, auto-tags) and merged into the same TF-IDF index. Live data goes through the identical RAG + grounding pipeline, never around it.
2. **Fallback dataset:** `backend/data/sources.json` (10 curated items) is always kept. With no key configured or if any API call fails, the dashboard clearly shows **DEMO SOURCE DATA** (plus a "fallback active" badge when a configured API was unavailable) and the demo continues unaffected.
3. **Indexing & retrieval:** cosine-similarity TF-IDF (+ tag boosts) ranks the merged corpus; each source carries an origin chip (**LIVE**, with clickable URL / **DEMO**) shown in both RAG Sources and Sources Used so judges can see exactly where information came from.
4. **Grounding:** retrieved source content is injected verbatim into the LLM prompt with numbered citations `[1]..[n]`. The generated post must cite sources inline.

### Data-source indicator

The header badge shows **LIVE API DATA (provider)** or **DEMO SOURCE DATA** based on actual retrieval status. We never claim data is live when the API is unavailable.

### Key handling

`NEWSAPI_KEY` / `GNEWS_API_KEY` live only in `backend/.env`, are read exclusively server-side, sent only to the provider host over HTTPS, and are never returned to the frontend or written to logs/errors (sanitized messages only).

### Grounding indicator (honest)

The UI shows whether each source was **explicitly cited** (`[n]`) or has meaningful keyword overlap with the post, plus a GROUNDED / NOT GROUNDED flag. This is a reference-presence check — **not** a factual accuracy score, and we make no such claim.

### Offline mode (explicit limitation)

If `OPENAI_API_KEY` is not set, generation falls back to a deterministic extractive composer that builds the post *only* from retrieved source sentences (keeping `[n]` citations). The UI badges this as `LLM: offline composer`. If a live API call fails, the fallback records `fallback_reason`.

## Swytchcode Role

Publishing is a **two-step, side-effect-free** flow:

1. **Preflight (genuine Swytchcode kernel):**
   `swytchcode exec ahrefs.social-media.post.create --explain --json --body <file>`
   The real CLI + kernel validate that the target integration/action exists and would accept the payload. Explain mode performs **no network call and needs no credentials**, so the demonstration is safe.
2. **Publish (clearly labeled simulation):** a mock publisher records a simulated post (`sim_…` id, `linkedin-sandbox` platform). **No real social post is created and no external service is called** — we do not pretend otherwise. A real social publishing integration (e.g., Ahrefs live mode) requires provider credentials; flipping it on only requires extending the allowlist in `backend/swytchcode/policy.py`.

### Execution policy (security)

`backend/swytchcode/policy.py` enforces a strict allowlist: only explicitly configured canonical IDs × modes may execute. Commands are built as argv lists (never shell strings), user input never touches the command line, request bodies are written server-side via `json.dump` to random temp files, and internal details (stdout/stderr/CLI path) are stripped from all API responses.

## How to Run

```bash
# 1) Install Swytchcode CLI (if missing)
npm install -g swytchcode

# 2) Backend (Python 3.11+)
cd backend
pip install -r requirements.txt
copy .env.example .env        # fill OPENAI_API_KEY to enable live LLM (optional)
python -m uvicorn backend.main:app --port 8000   # run from repo root

# 3) Frontend
cd frontend
npm install
npm run dev                   # http://localhost:5173  (proxies /api → :8000)
```

## Environment Variables (`backend/.env`)

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `OPENAI_API_KEY` | no | *(empty)* | Empty ⇒ offline extractive composer |
| `OPENAI_BASE_URL` | no | `https://api.openai.com/v1` | Any OpenAI-compatible endpoint |
| `OPENAI_MODEL` | no | `gpt-4o-mini` | Model name |
| `NEWSAPI_KEY` | no | *(empty)* | NewsAPI key — enables LIVE data (technology top-headlines) |
| `GNEWS_API_KEY` | no | *(empty)* | Optional additional live source (GNews) |

Secrets live only in `.env` (never hardcoded, never committed, never sent to the frontend or logs). Swytchcode explain mode needs no credentials.

## Demo Flow (judge script)

1. Dashboard opens: stats row, mode badges (`LLM: …`, `Swytchcode CLI: detected`, `demo source data`).
2. **Current Trends** — pick a trend (e.g., *Frontier LLM releases*).
3. **RAG Sources** — top-ranked sources appear with title, outlet, excerpt, relevance %.
4. Click **Generate Today's Content** → grounded post with `[1] [2]` citations, grounding indicator, sources-used list.
5. Click **Publish via Swytchcode** → panel shows (1) real Swytchcode preflight validation of `ahrefs.social-media.post.create` (explain mode, exit code, duration, timestamp) and (2) the clearly-labeled **SIMULATED** publish result with post id. Honest banner states no real post was created.
6. **Execution Logs** table records preflight + publish runs; counters update (Posts Generated, Swytchcode Executions).
7. **Automation** — toggle *Daily at 7:00 PM*: backend scheduler runs the full pipeline (retrieve → generate → sandbox publish) once per day at/after 19:00 local time and logs it.

## Known Limitations

- Source data is a local demo dataset (labeled everywhere); a live news API can be added via env key later.
- Publishing is **preflight validation (real Swytchcode kernel, explain mode) + clearly-labeled simulation** — no real posts are created and no external service is called.
- Scheduler is in-process (resets if backend restarts); automation toggle state persists in `data/state.json`.
