"""Execution policy: strict allowlist of Swytchcode actions and modes.

- Only canonical IDs listed here may ever be executed by the backend.
- Modes map to real CLI flags. "explain" validates the action/payload through
  the Swytchcode kernel WITHOUT any network call (side-effect free), which we
  use until real provider credentials are configured for live publishing.
"""
import re

CANONICAL_RE = re.compile(r"^[a-z0-9][a-z0-9.\-_]{2,80}$")

ALLOWED_ACTIONS = {
    "ahrefs.social-media.post.create": {"explain"},
}

MODE_FLAG = {"explain": "--explain", "demo": "--demo", "live": None}


def is_allowed(canonical_id: str, mode: str) -> bool:
    if not CANONICAL_RE.match(canonical_id or ""):
        return False
    return canonical_id in ALLOWED_ACTIONS and mode in ALLOWED_ACTIONS[canonical_id]


def describe_allowlist():
    return [{"canonical_id": cid, "modes": sorted(modes)}
            for cid, modes in ALLOWED_ACTIONS.items()]
