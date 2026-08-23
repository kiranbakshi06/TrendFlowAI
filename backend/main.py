import os
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.models.schemas import AutomationUpdate, GenerateRequest, PublishRequest, RetrieveRequest
from backend.rag.retriever import get_retriever
from backend.services import news, state
from backend.services.llm import generate_post, grounding_report, llm_mode
from backend.services.pipeline import publish_post, run_pipeline, scheduler_loop
from backend.swytchcode import client as swy
from backend.swytchcode.policy import describe_allowlist

ALLOWED_ORIGINS = [
    "http://localhost:5173", "http://127.0.0.1:5173",
    "http://localhost:4173", "http://127.0.0.1:4173",
]
TREND_ID_RE = re.compile(r"^[a-z0-9\-]{1,40}$")


def _load_env() -> None:
    """Minimal .env loader (backend/.env if present). No third-party dependency."""
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and value:
            os.environ.setdefault(key, value)


_load_env()


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio

    task = asyncio.create_task(scheduler_loop())
    get_retriever()
    yield
    task.cancel()


app = FastAPI(title="TrendFlow AI", version="1.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/config")
def config():
    # Deliberately minimal: never expose API keys, CLI paths, or internal details.
    ns = news.ensure_fresh()
    return {
        "llm_mode": llm_mode(),
        "swytchcode_available": swy.cli_available(),
        "swytchcode_allowlist": describe_allowlist(),
        "news_mode": ns["news_mode"],
        "news_providers": ns["providers"],
        "dataset_notice": ns["notice"],
    }


@app.get("/api/stats")
def stats():
    s = state.get_state()
    retriever = get_retriever()
    return {
        "trends_found": len(retriever.derive_trends()),
        "sources_indexed": len(retriever.documents),
        "sources_retrieved": len((s.get("current_post") or {}).get("sources_used", [])),
        "posts_generated": s.get("posts_generated", 0),
        "swytchcode_executions": s.get("swytchcode_executions", 0),
        "automation": s.get("automation"),
    }


@app.get("/api/trends")
def trends():
    ns = news.ensure_fresh()
    retriever = get_retriever()
    return {"trends": retriever.derive_trends(), "dataset_notice": ns["notice"],
            "news_mode": ns["news_mode"], "news_providers": ns["providers"]}


@app.post("/api/retrieve")
def retrieve(req: RetrieveRequest):
    if not TREND_ID_RE.match(req.trend_id):
        raise HTTPException(400, "Invalid trend id")
    ns = news.ensure_fresh()
    retriever = get_retriever()
    trend = next((t for t in retriever.derive_trends() if t["id"] == req.trend_id), None)
    if not trend:
        raise HTTPException(404, f"Unknown trend id: {req.trend_id}")
    sources = retriever.search(f"{trend['topic']} {trend['summary']} {trend['id']}", top_k=req.top_k)
    return {
        "trend": trend,
        "sources": [
            {k: s[k] for k in ("id", "title", "source_name", "published_at", "tags", "excerpt", "score", "relevance_pct", "url", "origin") if k in s}
            for s in sources
        ],
        "dataset_notice": ns["notice"],
        "news_mode": ns["news_mode"],
    }


@app.post("/api/generate")
def generate(req: GenerateRequest):
    if not TREND_ID_RE.match(req.trend_id):
        raise HTTPException(400, "Invalid trend id")
    try:
        result = run_pipeline(req.trend_id, publish=False)
        return result["content"]
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@app.post("/api/publish")
def publish(req: PublishRequest):
    execution = publish_post(req.post)
    if not execution.get("ok"):
        raise HTTPException(status_code=502, detail={
            "message": "Publish flow failed (see execution logs for details).",
            "preflight_ok": (execution.get("preflight") or {}).get("ok"),
            "error": (execution.get("preflight") or {}).get("error") or "unknown error",
        })
    return execution


@app.get("/api/logs")
def logs():
    safe_logs = []
    for log in state.get_state()["logs"]:
        safe_logs.append(log)  # logs store summaries + curated raw results only
    return {"logs": safe_logs}


@app.get("/api/automation")
def automation_get():
    return state.get_state().get("automation")


@app.post("/api/automation")
def automation_set(update: AutomationUpdate):
    if not re.fullmatch(r"^([01]\d|2[0-3]):[0-5]\d$", update.scheduled_time):
        raise HTTPException(400, "scheduled_time must be HH:MM (24h)")
    return state.set_automation(update.enabled, update.scheduled_time)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=False)
