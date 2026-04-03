"""
Post-rerank metadata boosts for retrieval.

Adjusts match scores using chunk metadata (concept_hint, chunk_type) so the final
ordering can reflect usefulness after the cross-encoder / reranker stage.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from packages.core.rag.agents.intent_classifier import UserIntent


def _compute_boost(
    match: Dict[str, Any],
    query_lower: str,
    max_boost: float,
) -> float:
    md = (match or {}).get("metadata", {}) or {}
    hint = str(md.get("concept_hint", "") or "").lower()
    ctype = str(md.get("chunk_type", "") or "").lower()
    score = float((match or {}).get("score", 0.0) or 0.0)
    boost = 0.0
    if hint:
        for term in [t.strip() for t in hint.split(",") if t.strip()]:
            if term and term in query_lower:
                boost += max_boost * 0.5
                break
    if ctype:
        if "definition" in query_lower and ctype == "definition":
            boost += max_boost
        elif ("how" in query_lower or "steps" in query_lower) and ctype in ("procedure", "qa"):
            boost += max_boost * 0.6
        elif ("example" in query_lower) and ctype == "example":
            boost += max_boost * 0.6
    boost = max(0.0, min(max_boost, boost))
    return score + boost


def apply_context_aware_scores(
    matches: List[Dict[str, Any]],
    query: str,
    max_boost: float = 0.15,
    intent: Optional[UserIntent] = None,
) -> List[Dict[str, Any]]:
    """
    Return a new list of matches with adjusted scores, sorted by score descending.

    ``intent`` is reserved for future intent-specific boosts; current heuristics
    are query-lexicon + metadata only.
    """
    _ = intent  # noqa: ARG001 — API stability for callers
    if not matches:
        return []
    ql = (query or "").lower()
    mb = float(max_boost)
    out: List[Dict[str, Any]] = []
    for m in matches:
        if not isinstance(m, dict):
            continue
        row = dict(m)
        row["score"] = _compute_boost(m, ql, mb)
        out.append(row)
    out.sort(key=lambda x: float((x or {}).get("score", 0.0) or 0.0), reverse=True)
    return out
