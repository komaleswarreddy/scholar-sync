"""
Hallucination guard (deterministic, no extra LLM pass by default).

This module scores whether high-risk sentences in the generated answer appear to be
supported by retrieved context evidence. It is intentionally lightweight:
- token overlap (no embeddings)
- heuristics for "needs support" sentences

It can be used to decide whether to run a single conditional retry with stricter
grounding instructions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple


_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
_WORD = re.compile(r"[a-zA-Z0-9]+")

# Answer tokens shorter than this are ignored for coarse recall (noise).
_MIN_TOKEN_LEN = 3

# If sentence-level overlap is harsh (paraphrase, reordering), require this share of
# substantive answer tokens to appear in context to treat the answer as grounded.
_DEFAULT_COARSE_RECALL_MIN = 0.26


_STOPWORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "if",
        "then",
        "than",
        "that",
        "this",
        "these",
        "those",
        "it",
        "its",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "not",
        "no",
        "yes",
        "to",
        "of",
        "in",
        "on",
        "for",
        "with",
        "as",
        "at",
        "by",
        "from",
        "into",
        "about",
        "your",
        "you",
        "we",
        "our",
        "they",
        "their",
        "can",
        "could",
        "would",
        "should",
        "may",
        "might",
        "will",
        "just",
        "also",
        "very",
        "more",
        "most",
        "some",
        "any",
        "each",
        "all",
        "both",
        "such",
        "when",
        "where",
        "which",
        "who",
        "what",
        "how",
        "why",
        "there",
        "here",
    }
)


def _tokens(text: str) -> List[str]:
    if not text:
        return []
    return [t.lower() for t in _WORD.findall(text)]


def _overlap_score(sentence: str, context: str) -> float:
    """
    Token overlap score in [0,1]. Designed to be cheap and robust.
    """
    st = set(_tokens(sentence))
    if not st:
        return 0.0
    ct = set(_tokens(context))
    if not ct:
        return 0.0
    inter = len(st & ct)
    denom = max(1, min(len(st), 20))  # cap to avoid long-sentence dilution
    return inter / float(denom)


def _coarse_content_recall(answer: str, context: str) -> float:
    """
    Share of substantive answer tokens that appear anywhere in context.
    Paraphrase-tolerant vs per-sentence overlap (same wording not required).
    """
    atoks = [
        t
        for t in _tokens(answer)
        if len(t) >= _MIN_TOKEN_LEN and t not in _STOPWORDS
    ]
    if not atoks:
        return 1.0
    cset = set(_tokens(context))
    hits = sum(1 for t in atoks if t in cset)
    return hits / float(len(atoks))


def _looks_like_general_knowledge(sentence: str) -> bool:
    return sentence.strip().lower().startswith("general knowledge:")


def _needs_support(sentence: str) -> bool:
    """
    Mark sentences that are likely to hallucinate if not grounded.
    We intentionally avoid complex NLP; keep stable for production.
    """
    s = sentence.strip()
    if not s:
        return False
    if _looks_like_general_knowledge(s):
        return False

    sl = s.lower()

    # Quotes should be supported.
    if '"' in s or "“" in s or "”" in s or "'" in s:
        return True

    # Numbers / years.
    if re.search(r"\b\d{2,}\b", s):
        return True

    # Strong factual verbs.
    if re.search(r"\b(is|are|was|were|causes|results in|leads to|means|defined as|consists of)\b", sl):
        return True

    # Named-entity-ish: multiple capitalized tokens not at sentence start.
    caps = re.findall(r"\b[A-Z][a-z]{2,}\b", s)
    if len(caps) >= 2:
        return True

    return False


@dataclass(frozen=True)
class HallucinationGuardResult:
    supported_ratio: float
    checked_sentences: int
    unsupported_sentences: List[str]


def analyze_answer_support(
    *,
    answer: str,
    context: str,
    min_sentence_chars: int = 28,
    min_overlap_score: float = 0.22,
    enable_coarse_rescue: bool = True,
    coarse_recall_min: float = _DEFAULT_COARSE_RECALL_MIN,
    coarse_rescue_supported_ratio: float = 0.72,
) -> HallucinationGuardResult:
    """
    Analyze answer support against retrieved context evidence.

    - Only checks "needs support" sentences.
    - Ignores very short sentences.
    - Uses token overlap score to determine support.
    """
    a = (answer or "").strip()
    c = (context or "").strip()
    if not a or not c:
        return HallucinationGuardResult(
            supported_ratio=1.0,
            checked_sentences=0,
            unsupported_sentences=[],
        )

    parts = _SENT_SPLIT.split(a)
    to_check: List[str] = []
    for p in parts:
        ps = (p or "").strip()
        if len(ps) < int(min_sentence_chars):
            continue
        if _needs_support(ps):
            to_check.append(ps)

    if not to_check:
        return HallucinationGuardResult(
            supported_ratio=1.0,
            checked_sentences=0,
            unsupported_sentences=[],
        )

    unsupported: List[str] = []
    supported = 0
    for s in to_check:
        sc = _overlap_score(s, c)
        if sc >= float(min_overlap_score):
            supported += 1
        else:
            unsupported.append(s)

    ratio = supported / float(len(to_check))
    # Rescue: model often paraphrases; sentence-level token overlap can falsely flag support.
    if (
        enable_coarse_rescue
        and to_check
        and ratio < float(coarse_rescue_supported_ratio)
        and _coarse_content_recall(a, c) >= float(coarse_recall_min)
    ):
        ratio = max(ratio, float(coarse_rescue_supported_ratio))
        unsupported = []

    return HallucinationGuardResult(
        supported_ratio=ratio,
        checked_sentences=len(to_check),
        unsupported_sentences=unsupported,
    )


def strict_retry_suffix(unsupported_sentences: List[str]) -> str:
    """
    A minimal instruction suffix to reduce hallucinations on a retry.
    """
    examples = unsupported_sentences[:3]
    ex = "\n".join([f"- {s}" for s in examples if s])
    hint = f"\n\nUnsupported sentences detected:\n{ex}\n" if ex else ""
    return (
        "\n\nGrounding instruction (hallucination guard):\n"
        "- Remove, soften, or label as `General knowledge:` any sentence not directly supported by the Context evidence.\n"
        "- Prefer restating the evidence using the same terms as the excerpts.\n"
        "- Do not add new specific numbers, names, dates, or quotes unless they appear in the evidence.\n"
        + hint
    )

