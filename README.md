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
│   │   └── client.py            # genuine wrapper around `swytchcode exec`
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

1. **Dataset:** `backend/data/sources.json` contains 10 curated, realistic AI/tech items. **This is clearly-labeled demo source data — not live internet data.**
2. **Indexing:** at startup each document is tokenized into a TF-IDF vector (with IDF weighting).
3. **Retrieval:** selecting a trend builds a query from the trend topic; cosine similarity (+ exact tag-match boost) ranks all documents; top-k are returned with relevance percentages.
4. **Grounding:** retrieved source content is injected verbatim into the LLM prompt with numbered citations `[1]..[n]`. The generated post must cite sources inline.

### Grounding indicator (honest)

The UI shows whether each source was **explicitly cited** (`[n]`) or has meaningful keyword overlap with the post, plus a GROUNDED / NOT GROUNDED flag. This is a reference-presence check — **not** a factual accuracy score, and we make no such claim.

### Offline mode (explicit limitation)

If `OPENAI_API_KEY` is not set, generation falls back to a deterministic extractive composer that builds the post *only* from retrieved source sentences (keeping `[n]` citations). The UI badges this as `LLM: offline composer`. If a live API call fails, the fallback records `fallback_reason`.

## Swytchcode Role

Publishing runs through the genuine Swytchcode kernel:

```bash
swytchcode exec stripe.create_payment --demo --json --body request.json
```

- The wrapper locates the CLI on PATH (`swytchcode` or `swy`), writes the body to a temp file (the post text is passed in `description`), and parses the structured stdout JSON.
- `--demo` mode requires no API keys and has **no real-world side effects**.
- **Honest labeling:** every result is marked **"Sandbox execution"** — no real social post or live payment is created. A real social integration would require provider auth (out of scope for this trial); Swytchcode's sandbox demonstrates the identical execution path: canonical ID → kernel → normalized result → audit trail.

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

Secrets live only in `.env` (never hardcoded, never committed). Swytchcode demo mode needs no credentials.

## Demo Flow (judge script)

1. Dashboard opens: stats row, mode badges (`LLM: …`, `Swytchcode CLI: detected`, `demo source data`).
2. **Current Trends** — pick a trend (e.g., *Frontier LLM releases*).
3. **RAG Sources** — top-ranked sources appear with title, outlet, excerpt, relevance %.
4. Click **Generate Today's Content** → grounded post with `[1] [2]` citations, grounding indicator, sources-used list.
5. Click **Publish via Swytchcode** → panel shows *execution requested*, status, `stripe.create_payment`, sandbox label, returned payment result, timestamp, duration. Honest banner: sandbox only.
6. **Execution Logs** table records the run; counters update (Posts Generated, Swytchcode Executions).
7. **Automation** — toggle *Daily at 7:00 PM*: backend scheduler runs the full pipeline (retrieve → generate → sandbox publish) once per day at/after 19:00 local time and logs it.

## Known Limitations

- Source data is a local demo dataset (labeled everywhere); a live news API can be added via env key later.
- Publishing is a Swytchcode **sandbox/demo** operation by design — no real posts or payments.
- Scheduler is in-process (resets if backend restarts); automation toggle state persists in `data/state.json`.
