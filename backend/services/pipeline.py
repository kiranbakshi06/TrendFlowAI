"""Pipeline orchestration + the daily 19:00 scheduler (asyncio background loop).

Publishing flow (honest, side-effect free):
  1. PREFLIGHT (genuine Swytchcode): `swytchcode exec <target> --explain` runs
     the kernel in validation mode - no network call, no credentials needed.
  2. PUBLISH (clearly labeled SIMULATION): a mock social publisher records the
     post locally. No external service is called and nothing is really posted.
"""
import asyncio
import re
import uuid
from datetime import datetime, timezone

from backend.rag.retriever import get_retriever
from backend.services import state
from backend.services.llm import generate_post, grounding_report
from backend.swytchcode import client as swy

PUBLISH_TARGET = "ahrefs.social-media.post.create"
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
MAX_POST_LEN = 2000


def run_pipeline(trend_id: str, publish: bool = False) -> dict:
    """Full flow: retrieve -> generate -> (optional) publish -> log."""
    if not re.fullmatch(r"[a-z0-9\-]{1,40}", trend_id or ""):
        raise ValueError("Invalid trend id")
    from backend.services import news  # local import avoids circulars

    news.ensure_fresh()  # refresh live articles into RAG when available
    retriever = get_retriever()
    trend = next((t for t in retriever.derive_trends() if t["id"] == trend_id), None)
    if not trend:
        raise ValueError(f"Unknown trend id: {trend_id}")

    sources = retriever.search(f"{trend['topic']} {trend['summary']} {trend['id']}", top_k=4)
    gen = generate_post(trend["topic"], sources)
    grounding = grounding_report(gen["post"], sources)

    payload = {
        "post": gen["post"],
        "model": gen["model"],
        "mode": gen["mode"],
        "fallback_reason": gen.get("fallback_reason"),
        "trend": {"id": trend["id"], "topic": trend["topic"]},
        "sources_used": sources,
        "grounding": grounding,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    state.set_current_post(payload)
    state.increment("posts_generated")

    result = {"content": payload}
    if publish:
        preflight = validate_publish_payload(gen["post"])
        simulated = simulate_publish(gen["post"])
        state.append_log({
            "action": "preflight_validation",
            "integration": f"{preflight.get('integration')}.{preflight.get('action')}",
            "mode": f"swytchcode:{preflight.get('mode')}",
            "status": "success" if preflight.get("ok") else "failed",
            "duration_ms": preflight.get("duration_ms"),
            "result_summary": ("Swytchcode kernel validated action + payload "
                               "(explain mode, no network call)")
                              if preflight.get("ok") else preflight.get("error"),
            "raw_result": preflight.get("result"),
        })
        state.append_log({
            "action": "publish_content",
            "integration": "mock.social_publisher",
            "mode": "simulated-sandbox",
            "status": "success",
            "result_summary": f"SIMULATED post {simulated['post_id']} created for "
                              f"@trendflow-demo. No external service was called.",
            "raw_result": simulated,
        })
        if simulated.get("ok"):
            state.increment("swytchcode_executions")
        result["execution"] = {"preflight": _public_record(preflight),
                               "publish": simulated}
    return result


def _sanitize_post(text: str | None) -> str:
    return CONTROL_CHARS.sub("", (text or "")).strip()[:MAX_POST_LEN]


def validate_publish_payload(post_text: str) -> dict:
    """Genuine Swytchcode execution in explain mode: validates that the target
    integration/action exists and would accept this payload shape. NO network."""
    body = {
        "text": _sanitize_post(post_text),
        "social_network": "linkedin",
    }
    return swy.exec_tool(PUBLISH_TARGET, body, mode="explain")


def simulate_publish(post_text: str) -> dict:
    """Clearly-labeled simulated publishing. NOT a real social post."""
    now = datetime.now(timezone.utc)
    return {
        "requested": True,
        "ok": True,
        "simulated": True,
        "integration": "mock",
        "action": "social_publisher",
        "post_id": f"sim_{uuid.uuid4().hex[:12]}",
        "platform": "linkedin-sandbox",
        "chars": len(_sanitize_post(post_text)),
        "timestamp": now.isoformat(),
        "note": "SIMULATION ONLY - no external service was called; no real post exists.",
    }


def publish_post(post_text: str | None = None) -> dict:
    """Combined publish flow used by the API endpoint."""
    current = state.get_current_post()
    text = _sanitize_post(post_text or (current or {}).get("post"))
    if not text:
        return {"ok": False, "error": "No generated content available. Generate content first."}

    preflight = validate_publish_payload(text)
    state.append_log({
        "action": "preflight_validation",
        "integration": f"{preflight.get('integration')}.{preflight.get('action')}",
        "mode": f"swytchcode:{preflight.get('mode')}",
        "status": "success" if preflight.get("ok") else "failed",
        "duration_ms": preflight.get("duration_ms"),
        "result_summary": ("Swytchcode kernel validated action + payload "
                           "(explain mode, no network call)")
                          if preflight.get("ok") else preflight.get("error"),
        "raw_result": preflight.get("result"),
    })

    simulated = simulate_publish(text)
    state.append_log({
        "action": "publish_content",
        "integration": "mock.social_publisher",
        "mode": "simulated-sandbox",
        "status": "success" if simulated.get("ok") else "failed",
        "result_summary": f"SIMULATED post {simulated['post_id']} created for "
                          f"@trendflow-demo. No external service was called.",
        "raw_result": simulated,
    })
    if simulated.get("ok"):
        state.increment("swytchcode_executions")

    return {"ok": preflight.get("ok", False) and simulated.get("ok", False),
            "preflight": _public_record(preflight),
            "publish": simulated}


def _public_record(e: dict) -> dict:
    """Sanitized execution record safe to return to the frontend."""
    r = e.get("result")
    if isinstance(r, dict):
        r = {k: v for k, v in r.items() if k not in ("stdout", "stderr")}
    return {
        "requested": e.get("requested"),
        "ok": e.get("ok"),
        "integration": e.get("integration"),
        "action": e.get("action"),
        "canonical_id": e.get("canonical_id"),
        "mode": e.get("mode"),
        "exit_code": e.get("exit_code"),
        "result": r,
        "started_at": e.get("started_at"),
        "finished_at": e.get("finished_at"),
        "duration_ms": e.get("duration_ms"),
        "error": e.get("error"),
    }


async def scheduler_loop():
    """Checks every 30s; runs the full pipeline at/after the scheduled time once per day."""
    while True:
        try:
            auto = state.get_state().get("automation", {})
            now = datetime.now()
            today = now.strftime("%Y-%m-%d")
            if (auto.get("enabled") and auto.get("last_run_date") != today
                    and now.strftime("%H:%M") >= auto.get("scheduled_time", "19:00")):
                trends = get_retriever().derive_trends()
                if trends:
                    run_pipeline(trends[0]["id"], publish=True)
                    state.mark_automation_run()
                    state.append_log({
                        "action": "automated_daily_run",
                        "integration": "internal.scheduler",
                        "mode": "automation",
                        "status": "success",
                        "result_summary": f"Scheduled 7:00 PM pipeline ran for trend '{trends[0]['topic']}' including preflight + simulated publish.",
                        "raw_result": None,
                    })
        except Exception as exc:  # noqa: BLE001 - never kill the loop
            try:
                state.append_log({
                    "action": "automated_daily_run", "integration": "internal.scheduler",
                    "mode": "automation", "status": "failed",
                    "result_summary": f"Scheduler error: {type(exc).__name__}",
                    "raw_result": None,
                })
            except Exception:  # noqa: S110
                pass
        await asyncio.sleep(30)
