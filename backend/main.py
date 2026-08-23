import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware


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

from backend.models.schemas import AutomationUpdate, GenerateRequest, PublishRequest, RetrieveRequest
from backend.rag.retriever import get_retriever
from backend.services import state
from backend.services.llm import generate_post, grounding_report, llm_mode
from backend.services.pipeline import publish_post, run_pipeline, scheduler_loop
from backend.swytchcode import client as swy


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = __import__("asyncio").create_task(scheduler_loop())
    get_retriever()  # warm the index
    yield
    task.cancel()


app = FastAPI(title="TrendFlow AI", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/config")
def config():
    return {
        "llm_mode": llm_mode(),
        "swytchcode_available": swy.cli_available(),
        "swytchcode_cli_path": swy.find_cli(),
        "dataset_notice": get_retriever().dataset_notice,
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
    retriever = get_retriever()
    return {"trends": retriever.derive_trends(), "dataset_notice": retriever.dataset_notice}


@app.post("/api/retrieve")
def retrieve(req: RetrieveRequest):
    retriever = get_retriever()
    trend = next((t for t in retriever.derive_trends() if t["id"] == req.trend_id), None)
    if not trend:
        raise HTTPException(404, f"Unknown trend id: {req.trend_id}")
    sources = retriever.search(f"{trend['topic']} {trend['summary']} {trend['id']}", top_k=req.top_k)
    return {
        "trend": trend,
        "sources": [
            {k: s[k] for k in ("id", "title", "source_name", "published_at", "tags", "excerpt", "score", "relevance_pct")}
            for s in sources
        ],
        "dataset_notice": retriever.dataset_notice,
    }


@app.post("/api/generate")
def generate(req: GenerateRequest):
    try:
        result = run_pipeline(req.trend_id, publish=False)
        return result["content"]
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@app.post("/api/publish")
def publish(req: PublishRequest):
    execution = publish_post(req.post)
    if not execution.get("ok"):
        raise HTTPException(status_code=502, detail=execution)
    return _serialize_execution(execution)


def _serialize_execution(e: dict) -> dict:
    r = e.get("result") or {}
    return {
        "requested": True,
        "ok": e.get("ok"),
        "integration": e.get("integration"),
        "action": e.get("action"),
        "canonical_id": e.get("canonical_id"),
        "demo_mode": e.get("demo_mode"),
        "exit_code": e.get("exit_code"),
        "summary": r.get("summary"),
        "data": r.get("data"),
        "simulated": bool(r.get("_simulated")),
        "started_at": e.get("started_at"),
        "finished_at": e.get("finished_at"),
        "duration_ms": e.get("duration_ms"),
        "error": e.get("error"),
    }


@app.get("/api/logs")
def logs():
    return {"logs": state.get_state()["logs"]}


@app.get("/api/automation")
def automation_get():
    return state.get_state().get("automation")


@app.post("/api/automation")
def automation_set(update: AutomationUpdate):
    return state.set_automation(update.enabled, update.scheduled_time)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)
