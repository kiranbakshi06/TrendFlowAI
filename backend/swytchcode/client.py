"""Hardened wrapper around the installed Swytchcode CLI.

Security model:
- Only canonical IDs/modes in swytchcode.policy.ALLOWED_ACTIONS may execute.
- Commands are argv lists (never shell strings); user input never touches argv.
- Request bodies are json.dump'd to a random server-side temp file.
- stdin gets "n" so first-run prompts can never block a headless process.
- Internal details (stdout/stderr tails, CLI path) are never returned to callers.
"""
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone

from backend.swytchcode.policy import MODE_FLAG, is_allowed

EXEC_TIMEOUT_SECONDS = 60


def find_cli():
    for name in ("swytchcode", "swy"):
        path = shutil.which(name)
        if path:
            return path
    return None


def cli_available() -> bool:
    return find_cli() is not None


def _reject(canonical_id: str, error: str) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    parts = (canonical_id or "unknown.action").split(".")
    return {
        "requested": True, "ok": False,
        "integration": parts[0], "action": ".".join(parts[1:]) or canonical_id,
        "canonical_id": canonical_id, "mode": "n/a", "exit_code": -1,
        "error": error, "result": None,
        "started_at": now, "finished_at": now, "duration_ms": 0,
    }


def exec_tool(canonical_id: str, body: dict, mode: str = "explain") -> dict:
    """Run an allowlisted `swytchcode exec` and return a sanitized record."""
    if not is_allowed(canonical_id, mode):
        return _reject(canonical_id, f"Blocked by execution policy: '{canonical_id}' with mode '{mode}' is not allowlisted")

    cli = find_cli()
    if not cli:
        return _reject(canonical_id, "Swytchcode CLI not found on PATH")

    tmp_path = None
    try:
        fd = tempfile.NamedTemporaryFile(prefix="swy_body_", suffix=".json",
                                         delete=False, mode="w", encoding="utf-8")
        json.dump(body, fd)
        fd.close()
        tmp_path = fd.name

        cmd = [cli, "exec", canonical_id]
        flag = MODE_FLAG[mode]
        if flag:
            cmd.append(flag)
        cmd += ["--json", "--body", tmp_path]

        started = datetime.now(timezone.utc)
        proc = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8",
            errors="replace", input="n\n", timeout=EXEC_TIMEOUT_SECONDS,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        finished = datetime.now(timezone.utc)

        parsed, parse_error = None, None
        if proc.returncode == 0 and proc.stdout.strip():
            try:
                parsed = json.loads(proc.stdout.strip().splitlines()[-1])
            except json.JSONDecodeError as exc:
                parse_error = str(exc)

        ok = proc.returncode == 0 and parsed is not None
        return {
            "requested": True, "ok": ok,
            "integration": canonical_id.split(".")[0],
            "action": ".".join(canonical_id.split(".")[1:]) or canonical_id,
            "canonical_id": canonical_id, "mode": mode,
            "exit_code": proc.returncode, "result": parsed,
            "parse_error": parse_error,
            "error": None if ok else f"CLI exited with code {proc.returncode}"
                     + (f"; invalid JSON output" if parse_error else ""),
            "started_at": started.isoformat(), "finished_at": finished.isoformat(),
            "duration_ms": int((finished - started).total_seconds() * 1000),
        }
    except subprocess.TimeoutExpired:
        return _reject(canonical_id, f"Execution timed out after {EXEC_TIMEOUT_SECONDS}s")
    except Exception as exc:  # noqa: BLE001 - expose type only, never internals
        return _reject(canonical_id, f"Execution error: {type(exc).__name__}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
