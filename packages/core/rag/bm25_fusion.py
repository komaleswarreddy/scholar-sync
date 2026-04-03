from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


def _tokenize(s: str) -> List[str]:
    return [t for t in (s or "").lower().split() if t]


@dataclass(frozen=True)
class ScoredDoc:
    doc_id: str
    score: float
    payload: Dict[str, Any]


def rrf_fuse(
    *,
    dense: List[Dict[str, Any]],
    sparse: List[Dict[str, Any]],
    k: int = 60,
    top_n: int = 150,
) -> List[Dict[str, Any]]:
    """
    Reciprocal Rank Fusion (RRF) for combining two ranked lists.
    """
    def _id(m: Dict[str, Any]) -> str:
        return str((m or {}).get("id") or "")

    fused: Dict[str, float] = {}
    payload: Dict[str, Dict[str, Any]] = {}

    for rank, m in enumerate(dense, start=1):
        mid = _id(m)
        if not mid:
            continue
        fused[mid] = fused.get(mid, 0.0) + 1.0 / (k + rank)
        payload[mid] = m

    for rank, m in enumerate(sparse, start=1):
        mid = _id(m)
        if not mid:
            continue
        fused[mid] = fused.get(mid, 0.0) + 1.0 / (k + rank)
        payload.setdefault(mid, m)

    out = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)[: max(1, int(top_n))]
    res: List[Dict[str, Any]] = []
    for mid, s in out:
        m = dict(payload.get(mid) or {})
        m["score"] = float(s)
        md = dict(m.get("metadata", {}) or {})
        md["rrf_score"] = float(s)
        m["metadata"] = md
        res.append(m)
    return res


class LocalBM25:
    """
    Simple BM25 over an in-memory corpus.

    Requires dependency: rank-bm25
    """

    def __init__(self, docs: List[Tuple[str, str, Dict[str, Any]]]):
        from rank_bm25 import BM25Okapi  # type: ignore

        self._docs = docs
        self._ids = [d[0] for d in docs]
        self._payloads = [d[2] for d in docs]
        tokenized = [_tokenize(d[1]) for d in docs]
        self._bm25 = BM25Okapi(tokenized)

    def query(self, query: str, top_n: int = 150) -> List[Dict[str, Any]]:
        q = _tokenize(query)
        if not q or not self._docs:
            return []
        scores = self._bm25.get_scores(q)
        # Take top_n indices by score
        idxs = sorted(range(len(scores)), key=lambda i: float(scores[i]), reverse=True)[: max(1, int(top_n))]
        out: List[Dict[str, Any]] = []
        for i in idxs:
            mid = self._ids[i]
            m = dict(self._payloads[i])
            m["id"] = mid
            m["score"] = float(scores[i])
            md = dict(m.get("metadata", {}) or {})
            md["bm25_score"] = float(scores[i])
            m["metadata"] = md
            out.append(m)
        return out

