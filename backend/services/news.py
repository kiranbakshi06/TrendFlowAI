"""Live news retrieval: NewsAPI (primary) + optional GNews, with graceful
fallback to the curated demo dataset.

Security: API keys are read from environment (backend/.env) ONLY, sent solely
to the provider host, never returned to the frontend, never logged. Error
messages are sanitized (status codes / generic reasons only).
"""
import os
import time
from datetime import datetime, timezone

import requests

from backend.rag.retriever import get_retriever

TTL_SECONDS = 600  # refetch at most every 10 min (demo-friendly rate limits)

_cache = {"at": 0.0, "mode": "demo", "providers": [], "notice": None}

_TAG_RULES = [
    (("ai", "artificial intelligence", "machine learning"), "ai"),
    (("llm", "gpt", "chatbot", "model"), "llms"),
    (("chip", "gpu", "nvidia", "semiconductor", "intel", "amd"), "hardware"),
    (("cyber", "hack", "breach", "security"), "security"),
    (("robot", "drone"), "robotics"),
    (("social", "tiktok", "meta ", "instagram"), "social media"),
    (("startup", "funding", "ipo", "valuation"), "business"),
    (("space", "spacex", "satellite"), "space"),
    (("apple", "google", "microsoft", "openai", "anthropic"), "big tech"),
]


def configured_providers():
    p = []
    if os.environ.get("NEWSAPI_KEY"):
        p.append("newsapi")
    if os.environ.get("GNEWS_API_KEY"):
        p.append("gnews")
    return p


def _auto_tags(title: str) -> list[str]:
    t = title.lower()
    tags = [tag for needles, tag in _TAG_RULES if any(n in t for n in needles)]
    return tags or ["tech"]


def _normalize(article: dict, idx: int) -> dict | None:
    title = (article.get("title") or "").strip()
    body = (article.get("description") or article.get("content")
            or article.get("snippet") or "").strip()
    if not title or not body or "[removed]" in body:
        return None
    source = ((article.get("source") or {}).get("name")
              or article.get("source_name") or "Unknown outlet")
    published = (article.get("publishedAt") or article.get("published") or "")[:10]
    return {
        "id": f"live-{idx}",
        "title": title,
        "source_name": source,
        "published_at": published or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "tags": _auto_tags(title),
        "content": f"{title}. {body}"[:1200],
        "url": article.get("url") or "",
        "origin": "live",
    }


def _fetch_newsapi(key: str) -> list[dict]:
    resp = requests.get(
        "https://newsapi.org/v2/top-headlines",
        params={"category": "technology", "language": "en", "pageSize": 20},
        headers={"X-Api-Key": key},
        timeout=8,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "success":
        raise ValueError(f"provider returned status={data.get('status')}")
    return data.get("articles") or []


def _fetch_gnews(key: str) -> list[dict]:
    resp = requests.get(
        "https://gnews.io/api/v4/top-headlines",
        params={"category": "technology", "lang": "en", "max": 15, "apikey": key},
        timeout=8,
    )
    resp.raise_for_status()
    return (resp.json() or {}).get("articles") or []


_FETCHERS = {"newsapi": _fetch_newsapi, "gnews": _fetch_gnews}


def _fetch_all(providers: list[str]) -> tuple[list[dict], list[str]]:
    """Try each provider; keep successes. One failing provider never breaks the other."""
    ok_articles, ok_providers = [], []
    for name in providers:
        try:
            raw = _FETCHERS[name](os.environ.get("NEWSAPI_KEY" if name == "newsapi" else "GNEWS_API_KEY", ""))
            normalized = [a for a in (_normalize(r, i) for i, r in enumerate(raw)) if a]
            if normalized:
                ok_articles.extend(normalized)
                ok_providers.append(name)
        except Exception:  # noqa: BLE001 - never leak provider error details
            continue
    return ok_articles, ok_providers


def ensure_fresh(force: bool = False) -> dict:
    """Refresh live docs into the retriever if due. Returns public status info."""
    now = time.time()
    providers = configured_providers()
    if not providers:
        return {"news_mode": "demo", "providers": [],
                "notice": "DEMO SOURCE DATA - local curated dataset (no NEWSAPI_KEY configured)."}

    if not force and now - _cache["at"] < TTL_SECONDS:
        return {"news_mode": _cache["mode"], "providers": _cache["providers"],
                "notice": _cache["notice"]}

    articles, ok_providers = _fetch_all(providers)
    if articles:
        get_retriever().load_live(articles)
        _cache.update(at=now, mode="live", providers=ok_providers,
                      notice=f"LIVE API DATA via {', '.join(ok_providers)} "
                             f"(top-headlines, technology) - {len(articles)} articles indexed.")
    else:
        _cache.update(at=now, mode="demo", providers=[],
                      notice="LIVE API unavailable - fell back to DEMO SOURCE DATA "
                             "(local curated dataset).")
    return {"news_mode": _cache["mode"], "providers": _cache["providers"],
            "notice": _cache["notice"]}
