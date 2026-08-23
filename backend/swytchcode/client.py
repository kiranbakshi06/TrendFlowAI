"""Genuine wrapper around the installed Swytchcode CLI.

Executes: swytchcode exec <integration>.<action> --demo --json --body <file>

- Locates the CLI on PATH (swytchcode, or the shorter alias 'swy').
- Writes the request body to a temp file (avoids shell quoting issues).
- Captures stdout and parses the structured JSON result.
"""
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone

EXEC_TIMEOUT_SECONDS = 120


def find_cli() -> str | None:
    for name in ("swytchcode", "swy"):
        path = shutil.which(name)
        if path:
            return path
    return None


def cli_available() -> bool:
    return find_cli() is not None


def exec_tool(canonical_id: str, body: dict, demo_mode: bool = True,
              extra_args: list[str] | None = None) -> dict:
    """Run `swytchcode exec` and return a structured execution record."""
    cli = find_cli()
    if not cli:
        return _failure(canonical_id, "Swytchcode CLI not found on PATH")

    tmp_path = None
    try:
        fd = tempfile.NamedTemporaryFile(
            prefix="swy_body_", suffix=".json", delete=False, mode="w",
            encoding="utf-8")
        json.dump(body, fd)
        fd.close()
        tmp_path = fd.name

        cmd = [cli, "exec", canonical_id]
        if demo_mode:
            cmd.append("--demo")
        cmd += ["--json", "--body", tmp_path] + (extra_args or [])

        started = datetime.now(timezone.utc)
        proc = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            input="n\n",
            timeout=EXEC_TIMEOUT_SECONDS,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        finished = datetime.now(timezone.utc)

        parsed = None
        parse_error = None
        if proc.returncode == 0 and proc.stdout.strip():
            try:
                parsed = json.loads(proc.stdout.strip().splitlines()[-1])
            except json.JSONDecodeError as exc:
                parse_error = str(exc)

        ok = proc.returncode == 0 and parsed is not None
        return {
            "requested": True,
            "ok": ok,
            "integration": canonical_id.split(".")[0],
            "action": ".".join(canonical_id.split(".")[1:]) or canonical_id,
            "canonical_id": canonical_id,
            "demo_mode": demo_mode,
            "cli_path": cli,
            "command": " ".join(cmd[:2]) + f" exec {canonical_id} ...",
            "exit_code": proc.returncode,
            "result": parsed,
            "stdout": proc.stdout[-2000:] if proc.stdout else "",
            "stderr": proc.stderr[-2000:] if proc.stderr else "",
            "parse_error": parse_error,
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
            "duration_ms": int((finished - started).total_seconds() * 1000),
        }
    except subprocess.TimeoutExpired:
        return _failure(canonical_id, f"Execution timed out after {EXEC_TIMEOUT_SECONDS}s")
    except Exception as exc:  # noqa: BLE001
        return _failure(canonical_id, f"Execution error: {exc}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def _failure(canonical_id: str, error: str) -> dict:
    return {
        "requested": True,
        "ok": False,
        "integration": canonical_id.split(".")[0],
        "action": ".".join(canonical_id.split(".")[1:]) or canonical_id,
        "canonical_id": canonical_id,
        "demo_mode": True,
        "exit_code": -1,
        "error": error,
        "result": None,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "duration_ms": 0,
    }
