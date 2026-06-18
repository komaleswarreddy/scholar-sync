"""
Unified RAG context support check before the answer LLM.

Blocks answers when retrieved/packed chunks are semantically weak or do not contain
enough lexical overlap with the user question — prevents confident hallucinations
from general knowledge when evidence is off-topic (e.g. wrong NCERT chapter).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

from config.settings import settings
from packages.core.rag.embedder import Embedder
from packages.core.rag.tutor_relevance import max_relevance_vs_chunks

# Minimal English stopword set; avoids requiring NLTK.
_STOPWORDS: frozenset[str] = frozenset(
    """
    a an the and or but if then else when while of in on at to for from by with without
    as is are was were be been being it its this that these those i you we they he she
    what which who whom whose how why where there here about into over under again further
    then once both each few more most other some such no nor not only own same so than too
    very can could should would will just don do does did doing done have has had having
    my your our their me him her us them any all both each every either neither much many
    explain describe define tell give list compare difference between summarize summary
    chapter section page book read material source document notes help please question answer
    named passage reading according summarizes summarise summarize main process food colors colour
    absorbs produced plays role named assertion reason
    """.split()
)

# Query terms that may not appear literally in chunks but have corpus synonyms.
_TERM_ALIASES: dict[str, tuple[str, ...]] = {
    "sugar": ("sugar", "glucose", "c6h12o6"),
    "cycle": ("cycle", "calvin"),
}


def significant_terms(query: str, *, min_len: int = 3) -> List[str]:
    """Lowercased alphanumeric tokens, stopwords removed, min length."""
    q = (query or "").lower()
    raw = re.findall(r"[a-z0-9]+", q, flags=re.I)
    out: List[str] = []
    for t in raw:
        if len(t) < min_len:
            continue
        if t in _STOPWORDS:
            continue
        out.append(t)
    # De-dupe preserving order
    seen: set[str] = set()
    uniq: List[str] = []
    for t in out:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    return uniq


def lexical_support_ratio(query_terms: Sequence[str], chunk_texts: Sequence[str]) -> Tuple[int, int]:
    """
    How many query terms appear as substrings in the combined chunk corpus.
    Returns (matched_count, total_terms_considered).
    """
    if not query_terms:
        return (0, 0)
    cap = int(getattr(settings, "CONTEXT_GROUNDING_LEXICAL_MAX_TERMS", 8))
    terms = list(query_terms)[: max(1, cap)]
    blob = " ".join((t or "").lower() for t in chunk_texts)
    matched = 0
    for term in terms:
        if not term:
            continue
        aliases = _TERM_ALIASES.get(term, (term,))
        if any(alias in blob for alias in aliases):
            matched += 1
    return (matched, len(terms))


def lexical_gate_passes(
    query_terms: Sequence[str],
    chunk_texts: Sequence[str],
    *,
    max_cosine: float,
    bypass_cosine: float,
) -> Tuple[bool, str]:
    """
    Lexical requirement is skipped when embedding similarity is already very high
    (paraphrases / definitions without literal token overlap).
    """
    if max_cosine >= bypass_cosine:
        return True, "lexical_skipped_high_cosine"
    n_matched, n_terms = lexical_support_ratio(query_terms, chunk_texts)
    if n_terms == 0:
        return True, "no_significant_terms"
    min_frac = float(getattr(settings, "CONTEXT_GROUNDING_LEXICAL_MIN_TERM_FRACTION", 0.5))
    required = max(1, int((n_terms * min_frac) + 0.999))  # ceil
    if n_matched >= required:
        return True, f"lexical_ok:{n_matched}/{n_terms}"
    return False, f"lexical_fail:{n_matched}/{n_terms}_need_{required}"


@dataclass
class GroundingDecision:
    ok: bool
    reason: str
    max_cosine: float
    max_retrieval_score: float
    detail: str


async def evaluate_context_grounding(
    *,
    embedder: Embedder,
    query: str,
    selected_matches: List[Dict[str, Any]],
    chunk_texts: List[str],
    enable_lexical: bool = True,
) -> GroundingDecision:
    """
    Returns ok=True only if cosine, retrieval score, and (when enabled) lexical checks pass.
    """
    q = (query or "").strip()
    if not q or not chunk_texts:
        return GroundingDecision(False, "no_query_or_chunks", 0.0, 0.0, "empty")

    scores: List[float] = []
    for m in selected_matches:
        if isinstance(m, dict):
            scores.append(float(m.get("score", 0.0) or 0.0))
    max_score = max(scores) if scores else 0.0

    min_cos = float(getattr(settings, "CONTEXT_GROUNDING_MIN_COSINE", 0.40))
    min_ret = float(getattr(settings, "CONTEXT_GROUNDING_MIN_RETRIEVAL_SCORE", 0.28))

    max_sim, err = await max_relevance_vs_chunks(embedder, q, chunk_texts)
    if err:
        return GroundingDecision(
            False,
            "embedding_error",
            float(max_sim),
            float(max_score),
            err[:120],
        )

    if float(max_sim) < min_cos:
        return GroundingDecision(
            False,
            "cosine_below_threshold",
            float(max_sim),
            float(max_score),
            f"max_cosine={max_sim:.4f}<{min_cos}",
        )

    if float(max_score) < min_ret:
        return GroundingDecision(
            False,
            "retrieval_score_below_threshold",
            float(max_sim),
            float(max_score),
            f"max_score={max_score:.4f}<{min_ret}",
        )

    if enable_lexical and getattr(settings, "CONTEXT_GROUNDING_LEXICAL_ENABLED", True):
        terms = significant_terms(
            q,
            min_len=int(getattr(settings, "CONTEXT_GROUNDING_LEXICAL_MIN_TERM_LEN", 3)),
        )
        bypass = float(getattr(settings, "CONTEXT_GROUNDING_LEXICAL_BYPASS_MIN_COSINE", 0.52))
        ok_lex, lex_detail = lexical_gate_passes(terms, chunk_texts, max_cosine=float(max_sim), bypass_cosine=bypass)
        if not ok_lex:
            return GroundingDecision(
                False,
                "lexical_mismatch",
                float(max_sim),
                float(max_score),
                lex_detail,
            )

    return GroundingDecision(True, "ok", float(max_sim), float(max_score), "passed")


def extract_chunk_texts_from_matches(selected_matches: List[Dict[str, Any]]) -> List[str]:
    texts: List[str] = []
    for m in selected_matches or []:
        if not isinstance(m, dict):
            continue
        md = m.get("metadata") or {}
        if not isinstance(md, dict):
            md = {}
        t = (md.get("text") or "").strip()
        if t:
            texts.append(t)
    return texts
