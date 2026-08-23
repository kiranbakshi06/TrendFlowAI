"""Simple JSON-file backed state: counters, generated post, automation config, logs."""
import json
import threading
from datetime import datetime, timezone
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parent.parent / "data" / "state.json"

_lock = threading.Lock()
_default = {
    "posts_generated": 0,
    "swytchcode_executions": 0,
    "current_post": None,       # {post, model, mode, trend_topic, sources_used, grounding}
    "automation": {"enabled": False, "scheduled_time": "19:00", "last_run_date": None},
    "logs": [],                 # execution logs (newest first), capped at 100
}


def _read() -> dict:
    if STATE_PATH.exists():
        try:
            return {**_default, **json.loads(STATE_PATH.read_text(encoding="utf-8"))}
        except (json.JSONDecodeError, OSError):
            pass
    return dict(_default)


def _write(state: dict):
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def get_state() -> dict:
    with _lock:
        return _read()


def increment(counter: str) -> int:
    with _lock:
        state = _read()
        state[counter] = state.get(counter, 0) + 1
        value = state[counter]
        _write(state)
        return value


def set_current_post(payload: dict):
    with _lock:
        state = _read()
        state["current_post"] = payload
        _write(state)


def get_current_post() -> dict | None:
    return get_state().get("current_post")


def set_automation(enabled: bool, scheduled_time: str | None = None) -> dict:
    with _lock:
        state = _read()
        state["automation"]["enabled"] = enabled
        if scheduled_time:
            state["automation"]["scheduled_time"] = scheduled_time
        _write(state)
        return state["automation"]


def mark_automation_run():
    with _lock:
        state = _read()
        state["automation"]["last_run_date"] = datetime.now().strftime("%Y-%m-%d")
        _write(state)


def append_log(entry: dict):
    with _lock:
        state = _read()
        entry["timestamp"] = datetime.now(timezone.utc).isoformat()
        state["logs"].insert(0, entry)
        state["logs"] = state["logs"][:100]
        _write(state)
