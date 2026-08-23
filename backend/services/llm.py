"""LLM content generation via any OpenAI-compatible API configured through env vars.

Env:
  OPENAI_API_KEY   (required for live mode)
  OPENAI_BASE_URL  (optional, default https://api.openai.com/v1)
  OPENAI_MODEL     (optional, default gpt-4o-mini)

If no key is configured, falls back to a deterministic extractive composer
built strictly from retrieved sources (clearly labeled OFFLINE mode).
"""
import os
import re
from datetime import datetime

import requests

from backend.rag.retriever import get_retriever

PROMPT_TEMPLATE = """You are TrendFlow AI, a social media content engine.
Write ONE concise social-media post (max 60 words, punchy, no hashtags spam - at most 2 hashtags).

STRICT GROUNDING RULES:
- Use ONLY facts contained in the sources below.
- Cite sources inline using their bracket numbers like [1] or [2] whenever you state a fact from them.
- Do NOT invent statistics, names, or events not present in the sources.
- End with a short engaging hook question.

TREND: {trend}

SOURCES:
{sources}

Write the post now:"""


def _format_sources(sources: list[dict]) -> str:
    blocks = []
    for i, s in enumerate(sources, 1):
        blocks.append(f"[{i}] \"{s['title']}\" - {s['source_name']} ({s.get('published_at', 'n/a')})\n{s['content']}")
    return "\n\n".join(blocks)


def _llm_config() -> dict:
    return {
        "api_key": os.environ.get("OPENAI_API_KEY", ""),
        "base_url": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
    }


def llm_mode() -> str:
    return "live" if _llm_config()["api_key"] else "offline"


def generate_post(trend_topic: str, sources: list[dict]) -> dict:
    """Returns {post, model, mode, prompt_used}."""
    if llm_mode() == "live":
        cfg = _llm_config()
        prompt = PROMPT_TEMPLATE.format(
            trend=trend_topic, sources=_format_sources(sources))
        try:
            resp = requests.post(
                f"{cfg['base_url']}/chat/completions",
                headers={"Authorization": f"Bearer {cfg['api_key']}"},
                json={
                    "model": cfg["model"],
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 300,
                },
                timeout=45,
            )
            resp.raise_for_status()
            post = resp.json()["choices"][0]["message"]["content"].strip()
            return {"post": post, "model": cfg["model"], "mode": "live",
                    "prompt_used": prompt}
        except Exception as exc:  # noqa: BLE001
            fallback = _compose_offline(trend_topic, sources)
            fallback["fallback_reason"] = f"LLM call failed: {exc}"
            return fallback
    return _compose_offline(trend_topic, sources)


def _compose_offline(trend_topic: str, sources: list[dict]) -> dict:
    """Extractive composer: builds the post ONLY from retrieved source sentences."""
    parts = [f"{trend_topic}:"]
    for i, s in enumerate(sources[:3], 1):
        sentence = s["content"].split(". ")[0].strip().rstrip(".") + "."
        parts.append(f"{sentence} [{i}]")
    parts.append("What's your take?")
    post = " ".join(parts)
    return {"post": post.strip(), "model": "extractive-composer (offline)",
            "mode": "offline", "prompt_used": None}


def grounding_report(post: str, sources: list[dict]) -> dict:
    """Honest grounding indicator: which sources are explicitly referenced,
    plus keyword overlap between the post and each source."""
    cited_nums = set(int(n) for n in re.findall(r"\[(\d+)\]", post))
    post_tokens = set(re.findall(r"[a-z0-9]{4,}", post.lower()))
    per_source = []
    for i, s in enumerate(sources, 1):
        src_tokens = set(re.findall(r"[a-z0-9]{4,}", (s["title"] + " " + s["content"]).lower()))
        overlap = len(post_tokens & src_tokens) / max(1, len(src_tokens))
        per_source.append({
            "index": i,
            "id": s["id"],
            "title": s["title"],
            "source_name": s["source_name"],
            "explicit_citation": i in cited_nums,
            "keyword_overlap_pct": round(overlap * 100, 1),
        })
    grounded_count = sum(1 for p in per_source if p["explicit_citation"] or p["keyword_overlap_pct"] >= 8.0)
    return {
        "grounded": grounded_count > 0 and (len(cited_nums) > 0 or grounded_count >= len(sources) // 2),
        "sources_referenced": grounded_count,
        "total_sources": len(sources),
        "explicit_citations": sorted(cited_nums),
        "per_source": per_source,
        "note": "Grounding = explicit [n] citations and/or meaningful keyword overlap with retrieved sources. Not a factual accuracy score.",
    }
