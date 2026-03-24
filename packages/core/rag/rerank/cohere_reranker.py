from __future__ import annotations

from typing import Any, Dict, List, Optional

from config.settings import settings


class CohereReranker:
    """
    Rerank retrieved chunks using Cohere Rerank API while preserving the
    existing chunk/match dict shape.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or getattr(settings, "COHERE_API_KEY", "")
        self.model = model or getattr(settings, "COHERE_RERANK_MODEL", "rerank-v3.5")

        if not self.api_key:
            raise ValueError("COHERE_API_KEY not configured")

        try:
            import cohere  # noqa: F401
        except Exception as e:  # pragma: no cover
            raise ValueError("Cohere SDK not installed. Install with: pip install cohere") from e

    def _client(self):
        import cohere

        # Cohere v2 client (works for rerank in recent SDKs)
        return cohere.ClientV2(self.api_key)

    def rerank(
        self,
        *,
        query: str,
        matches: List[Dict[str, Any]],
        top_n: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        if not matches:
            return []

        documents: List[str] = []
        for m in matches:
            md = m.get("metadata", {}) or {}
            documents.append((md.get("text") or "")[:2000])  # avoid overlong docs

        client = self._client()
        resp = client.rerank(model=self.model, query=query, documents=documents, top_n=top_n)

        # Cohere returns a list of results with index and relevance_score
        results = getattr(resp, "results", None) or []
        reranked: List[Dict[str, Any]] = []

        for r in results:
            idx = int(getattr(r, "index", -1))
            if idx < 0 or idx >= len(matches):
                continue
            score = float(getattr(r, "relevance_score", 0.0) or 0.0)
            m = dict(matches[idx])
            m["score"] = score
            md = dict(m.get("metadata", {}) or {})
            md["rerank_score"] = score
            m["metadata"] = md
            reranked.append(m)

        # If API returned nothing, fall back to original ordering
        return reranked if reranked else matches

