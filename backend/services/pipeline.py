"""Pipeline orchestration + the daily 19:00 scheduler (asyncio background loop)."""
import asyncio
from datetime import datetime, timezone

from backend.rag.retriever import get_retriever
from backend.services import state
from backend.services.llm import generate_post, grounding_report
from backend.swytchcode import client as swy

PUBLISH_TARGET = "stripe.create_payment"  # sandbox/demo execution - no real side effects


def run_pipeline(trend_id: str, publish: bool = False) -> dict:
    """Full flow: retrieve -> generate -> (optional) swytchcode exec -> log."""
    retriever = get_retriever()
    trend = next((t for t in retriever.derive_trends() if t["id"] == trend_id), None)
    if not trend:
        raise ValueError(f"Unknown trend id: {trend_id}")

    sources = retriever.search(query=f"{trend['topic']} {trend['summary']} {trend['id']}",
                               top_k=4)
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
        result["execution"] = publish_post()
    return result


def publish_post(post_text: str | None = None) -> dict:
    """Send the generated post through the Swytchcode execution layer.

    Uses stripe.create_payment in --demo mode: a genuine Swytchcode kernel
    execution with NO real-world side effects. Honestly labeled sandbox.
    """
    current = state.get_current_post()
    text = post_text or (current or {}).get("post")
    if not text:
        return {"ok": False, "error": "No generated content available. Generate content first."}

    body = {
        "amount": 2500,
        "currency": "usd",
        "description": f"TrendFlow AI post: {text[:80]}",
    }
    execution = swy.exec_tool(PUBLISH_TARGET, body, demo_mode=True)

    status = "success" if execution.get("ok") else "failed"
    state.append_log({
        "action": "publish_content",
        "integration": f"{execution.get('integration', 'stripe')}.{execution.get('action', 'create_payment')}",
        "mode": "sandbox-demo",
        "status": status,
        "duration_ms": execution.get("duration_ms"),
        "result_summary": _summarize(execution),
        "raw_result": execution.get("result"),
        "error": execution.get("error") or (None if execution.get("ok") else execution.get("stderr", "")[-300:] or "unknown error"),
    })
    if execution.get("ok"):
        state.increment("swytchcode_executions")
    return execution


def _summarize(execution: dict) -> str:
    r = execution.get("result") or {}
    data = r.get("data") or {}
    label = "SANDBOX (demo) execution" if execution.get("demo_mode") else "LIVE execution"
    if r.get("summary"):
        return f"{label}: {r['summary']}" + (f" | payment_id={data.get('payment_id')}" if data.get("payment_id") else "")
    return f"{label}: exit_code={execution.get('exit_code')}"


async def scheduler_loop():
    """Checks every 30s; runs the full pipeline at/after the scheduled time once per day."""
    while True:
        try:
            auto = state.get_state().get("automation", {})
            now = datetime.now()
            hhmm = now.strftime("%H:%M")
            today = now.strftime("%Y-%m-%d")
            if (auto.get("enabled") and auto.get("last_run_date") != today
                    and hhmm >= auto.get("scheduled_time", "19:00")):
                trends = get_retriever().derive_trends()
                if trends:
                    run_pipeline(trends[0]["id"], publish=True)
                    state.mark_automation_run()
                    state.append_log({
                        "action": "automated_daily_run",
                        "integration": "internal.scheduler",
                        "mode": "automation",
                        "status": "success",
                        "result_summary": f"Scheduled 7:00 PM pipeline ran for trend '{trends[0]['topic']}' including sandbox publishing.",
                        "raw_result": None,
                    })
        except Exception as exc:  # noqa: BLE001 - never kill the loop
            try:
                state.append_log({
                    "action": "automated_daily_run", "integration": "internal.scheduler",
                    "mode": "automation", "status": "failed",
                    "result_summary": f"Scheduler error: {exc}", "raw_result": None,
                })
            except Exception:  # noqa: S110
                pass
        await asyncio.sleep(30)
