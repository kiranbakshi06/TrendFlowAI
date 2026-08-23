"""Lightweight TF-IDF retrieval over the local demo source dataset.

No external ML dependencies: pure-python tokenization + cosine similarity.
"""
import json
import math
import re
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "sources.json"

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
    "is", "are", "was", "were", "be", "been", "as", "at", "by", "it", "its",
    "this", "that", "these", "those", "from", "has", "have", "had", "will",
    "can", "their", "they", "them", "than", "but", "not", "new", "now",
}

TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS and len(t) > 1]


class Retriever:
    def __init__(self):
        self.documents = []
        self._load()
        self._build_index()

    def _load(self):
        raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        self.dataset_notice = raw.get("_notice", "")
        self.demo_documents = []
        for doc in raw["documents"]:
            doc["text"] = f"{doc['title']} {doc['content']} {' '.join(doc['tags'])}"
            doc["excerpt"] = doc["content"].split(". ")[0] + "."
            doc.setdefault("origin", "demo")
            doc.setdefault("url", "")
            self.demo_documents.append(dict(doc))
        self.documents = list(self.demo_documents)

    def load_live(self, live_docs: list[dict]):
        """Merge live API articles with the fallback dataset and rebuild atomically."""
        merged = []
        for doc in live_docs:
            doc = dict(doc)
            doc["text"] = f"{doc['title']} {doc['content']} {' '.join(doc.get('tags', []))}"
            doc["excerpt"] = doc["content"].split(". ")[0] + "."
            doc.setdefault("origin", "live")
            merged.append(doc)
        for doc in self.demo_documents:
            merged.append(dict(doc))
        self.documents = merged
        self._build_index()

    def reset_to_demo(self):
        self.documents = [dict(d) for d in self.demo_documents]
        self._build_index()

    def _build_index(self):
        n_docs = len(self.documents)
        self.df = {}
        self.doc_tfs = []
        for doc in self.documents:
            tf = {}
            for tok in tokenize(doc["text"]):
                tf[tok] = tf.get(tok, 0) + 1
            self.doc_tfs.append(tf)
            for tok in tf:
                self.df[tok] = self.df.get(tok, 0) + 1
        self.idf = {
            tok: math.log((n_docs + 1) / (count + 1)) + 1.0
            for tok, count in self.df.items()
        }

    def _vectorize(self, text: str) -> dict[str, float]:
        tf = {}
        for tok in tokenize(text):
            tf[tok] = tf.get(tok, 0) + 1
        return {tok: (1 + math.log(count)) * self.idf.get(tok, math.log(len(self.documents) + 1) + 1.0)
                for tok, count in tf.items()}

    @staticmethod
    def _cosine(v1: dict[str, float], v2: dict[str, float]) -> float:
        if not v1 or not v2:
            return 0.0
        common = set(v1) & set(v2)
        dot = sum(v1[t] * v2[t] for t in common)
        norm = math.sqrt(sum(x * x for x in v1.values())) * math.sqrt(
            sum(x * x for x in v2.values()))
        return dot / norm if norm else 0.0

    def search(self, query: str, top_k: int = 4) -> list[dict]:
        qv = self._vectorize(query)
        scored = []
        for i, doc in enumerate(self.documents):
            score = self._cosine(qv, self._vectorize(doc["text"]))
            # small boost for exact tag matches
            q_tokens = set(tokenize(query))
            tag_hits = sum(1 for tag in doc["tags"] if any(t in tag or tag in t for t in q_tokens))
            score += 0.05 * tag_hits
            scored.append({"score": round(score, 4),
                           **{k: doc[k] for k in ("id", "title", "source_name", "excerpt", "content", "tags", "published_at", "url", "origin") if k in doc}})
        scored.sort(key=lambda x: x["score"], reverse=True)
        results = [s for s in scored if s["score"] > 0][:top_k]
        # normalize relevance to 0-100
        if results:
            max_score = max(r["score"] for r in results)
            for r in results:
                r["relevance_pct"] = round(min(99.0, (r["score"] / max_score) * 95 + 4), 1)
        return results

    def get_document(self, doc_id: str) -> dict | None:
        return next((d for d in self.documents if d["id"] == doc_id), None)

    def derive_trends(self) -> list[dict]:
        """Group documents by shared topic tags to form current 'trends'."""
        tag_docs: dict[str, list] = {}
        for doc in self.documents:
            for tag in doc["tags"]:
                tag_docs.setdefault(tag, []).append(doc)

        label_map = {
            "llms": ("Frontier LLM releases & upgrades", "GPT-5.2, Claude Opus 4.6 and the agentic leap"),
            "agents": ("Autonomous AI agents", "Agents moving from demos into daily production"),
            "rag": ("RAG over fine-tuning", "Retrieval quality becomes the enterprise moat"),
            "regulation": ("AI regulation & governance", "EU AI Act phase-two enforcement begins"),
            "hardware": ("AI hardware & compute", "Blackwell Ultra sell-outs and sovereign AI factories"),
            "social media": ("Synthetic media on social platforms", "Provenance labels reshape engagement"),
            "content": ("AI content automation", "Grounded, cited generation becomes table stakes"),
            "coding": ("AI-assisted development", "Pair programming saves ~9 hours/week"),
            "marketing": ("Marketing automation", "Trend-to-post pipelines go mainstream"),
        }

        trends = []
        seen_labels = set()
        for tag, docs in sorted(tag_docs.items(), key=lambda kv: -len(kv[1])):
            label, blurb = label_map.get(tag, (tag.replace("-", " ").title(), ""))
            if label in seen_labels:
                continue
            seen_labels.add(label)
            # relevance = doc coverage weighted by recency rank
            coverage = len(docs) / len(self.documents)
            trends.append({
                "id": tag,
                "topic": label,
                "summary": blurb,
                "doc_count": len(docs),
                "relevance_score": round(min(98.0, coverage * 100 * 1.6 + 40), 1),
                "sample_titles": [d["title"] for d in docs[:2]],
            })
        trends.sort(key=lambda t: -t["relevance_score"])
        return trends[:6]


_retriever: Retriever | None = None


def get_retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever
