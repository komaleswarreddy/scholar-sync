"""
scope_narrower_evaluators_updated.py

LangSmith custom evaluators for ScholarSync Agent 4: Scope Narrower.

Agent under test:
    scope_narrower

Current output contract under test:
    key_terms: list[str] of 3-7 distinct retrieval terms/phrases
    focused_query: concise retrieval query string
    max_chunks: int in [3, 15]

Design decision:
- This is intentionally CODE-FIRST, not LLM-judge based.
- Scope Narrower has a compact structured output and a small number of critical,
  deterministic risks: malformed JSON, weak retrieval narrowing, exam-noise leakage,
  follow-up over-expansion, numerical overfitting, and bad max_chunks calibration.
- Optional upstream metadata from Intent Classifier may be present in example.inputs
  or target inputs:
      intent, scope, requires_retrieval, requires_attachment, content_type
  These fields are used for consistency checks when present, but the output schema
  remains exactly the Scope Narrower contract: key_terms, focused_query, max_chunks.

Expected LangSmith usage:
    from scope_narrower_evaluators_updated import (
        PER_EXAMPLE_EVALUATORS,
        SUMMARY_EVALUATORS,
        parse_model_response_to_outputs,
    )

    client.evaluate(
        target_fn,
        data="nbm-prompt-scope_narrower",
        evaluators=PER_EXAMPLE_EVALUATORS,
        summary_evaluators=SUMMARY_EVALUATORS,
    )

Notes:
- No external API calls.
- No LangSmith import required inside this file.
- Defensive by design: malformed runs score 0.0 with a clear comment instead of
  raising and crashing the experiment.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Schema constants
# ---------------------------------------------------------------------------

REQUIRED_KEYS = {"key_terms", "focused_query", "max_chunks"}
MIN_KEY_TERMS = 3
MAX_KEY_TERMS = 7
MIN_CHUNKS = 3
MAX_CHUNKS = 15

VALID_INTENTS = {
    "security_block",
    "conversational",
    "direct_answer",
    "explanation",
    "summarization",
    "comparison",
    "analytical_reasoning",
    "content_generation",
    "unclear",
}

VALID_SCOPES = {
    "specific_query",
    "selected_text",
    "section",
    "whole_document",
    "conversation_context",
    "none",
}

VALID_CONTENT_TYPES = {
    None,
    "quiz",
    "flashcards",
    "mind_map",
    "slide_deck",
    "practice_questions",
    "study_plan",
    "other",
}

EXAM_NOISE_TERMS = {
    "neet",
    "jee",
    "cbse",
    "board",
    "boards",
    "pyq",
    "mcq",
    "exam",
    "exams",
    "advanced",
    "mains",
    "practical",
}

ARTIFACT_NOISE_TERMS = {
    "quiz",
    "mcq",
    "flashcard",
    "flashcards",
    "mindmap",
    "mind",
    "map",
    "slide",
    "slides",
    "deck",
    "presentation",
    "studyplan",
    "study",
    "plan",
    "practice",
    "questions",
}

METADATA_LEAK_TERMS = {
    "requires_retrieval",
    "requires attachment",
    "requires_attachment",
    "content_type",
    "scope field",
    "intent field",
    "selected source required",
    "attachment required",
}

INJECTION_LEAK_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|rules)",
    r"reveal\s+(your\s+)?(system|hidden)\s+(prompt|instructions)",
    r"developer\s+mode",
    r"no\s+restrictions",
    r"disregard\s+(prior|previous|all)",
    r"system\s*:",
    r"note\s+to\s+ai",
]

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "could", "do",
    "does", "for", "from", "give", "how", "i", "in", "into", "is", "it", "me",
    "my", "of", "on", "or", "please", "should", "that", "the", "their", "this",
    "to", "using", "was", "what", "when", "where", "which", "why", "with", "you",
    "your", "about", "all", "entire", "whole", "explain", "teach", "tell",
}

VARIATION_CHUNK_RANGES = {
    "broad_topic": (9, 12),
    "multi_part": (7, 10),
    "exam_oriented": (5, 7),
    "numerical": (4, 6),
    "conversational_follow_up": (3, 5),
}


# ---------------------------------------------------------------------------
# Safe access helpers
# ---------------------------------------------------------------------------

def _get_attr_or_key(obj: Any, name: str, default: Any = None) -> Any:
    """Support both LangSmith SDK objects and dict-like smoke-test objects."""
    try:
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
    except Exception:
        return default


def _safe_get_outputs(run: Any) -> Optional[dict]:
    try:
        out = _get_attr_or_key(run, "outputs")
        return out if isinstance(out, dict) else None
    except Exception:
        return None


def _safe_get_reference(example: Any) -> Optional[dict]:
    try:
        ref = _get_attr_or_key(example, "outputs")
        return ref if isinstance(ref, dict) else None
    except Exception:
        return None


def _safe_get_inputs(example: Any) -> dict:
    try:
        inp = _get_attr_or_key(example, "inputs")
        return inp if isinstance(inp, dict) else {}
    except Exception:
        return {}


def _safe_get_variation(example: Any) -> str:
    try:
        meta = _get_attr_or_key(example, "metadata") or {}
        if isinstance(meta, dict):
            return str(meta.get("variation", "unknown"))
        return "unknown"
    except Exception:
        return "unknown"


def _example_id(example: Any) -> Any:
    return _get_attr_or_key(example, "id", None)


# ---------------------------------------------------------------------------
# Parsing helper for target functions
# ---------------------------------------------------------------------------

def parse_model_response_to_outputs(raw_text: str) -> dict:
    """
    Convert raw model text into the outputs dict expected by LangSmith.

    Handles:
    - clean JSON object
    - markdown-fenced JSON
    - JSON surrounded by prose
    - common key aliases from less compliant models

    On failure returns {}, so schema_validity scores 0.0 without crashing.
    """
    if not isinstance(raw_text, str) or not raw_text.strip():
        return {}

    text = raw_text.strip()

    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    else:
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            text = brace_match.group(0)

    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return {}

    if not isinstance(parsed, dict):
        return {}

    # Normalize common aliases if the model drifted slightly.
    alias_map = {
        "terms": "key_terms",
        "keywords": "key_terms",
        "focusedQuery": "focused_query",
        "focused query": "focused_query",
        "maxChunks": "max_chunks",
        "top_k": "max_chunks",
    }
    normalized: dict[str, Any] = {}
    for key, value in parsed.items():
        normalized[alias_map.get(key, key)] = value

    return normalized


# ---------------------------------------------------------------------------
# Text utilities
# ---------------------------------------------------------------------------

def _normalize_text(text: Any) -> str:
    if text is None:
        return ""
    text = str(text).lower()
    text = text.replace("-", " ").replace("_", " ")
    text = re.sub(r"[^a-z0-9+*/=<>^|. ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _simple_stem(token: str) -> str:
    # Conservative suffix trimming to improve overlap without requiring nltk.
    for suffix in ("ization", "isation", "ations", "tion", "ing", "ed", "es", "s"):
        if len(token) > len(suffix) + 3 and token.endswith(suffix):
            return token[: -len(suffix)]
    return token


def _tokens(text: Any) -> set[str]:
    norm = _normalize_text(text)
    out: set[str] = set()
    for tok in norm.split():
        if tok in STOPWORDS:
            continue
        if len(tok) <= 1 and not tok.isdigit():
            continue
        out.add(_simple_stem(tok))
    return out


def _joined_output(out: dict) -> str:
    terms = out.get("key_terms", [])
    if not isinstance(terms, list):
        terms = []
    return " ".join(str(x) for x in terms) + " " + str(out.get("focused_query", ""))


def _phrase_covered(phrase: str, candidate_text: str) -> bool:
    phrase_norm = _normalize_text(phrase)
    candidate_norm = _normalize_text(candidate_text)
    if not phrase_norm:
        return True
    if phrase_norm in candidate_norm:
        return True
    phrase_tokens = _tokens(phrase_norm)
    if not phrase_tokens:
        return True
    cand_tokens = _tokens(candidate_norm)
    overlap = len(phrase_tokens & cand_tokens) / max(1, len(phrase_tokens))
    return overlap >= 0.60


def _term_recall(predicted_text: str, gold_terms: list[Any]) -> float:
    if not gold_terms:
        return 1.0
    covered = 0
    for term in gold_terms:
        if _phrase_covered(str(term), predicted_text):
            covered += 1
    return covered / max(1, len(gold_terms))


def _token_f1(predicted: Any, gold: Any) -> float:
    p = _tokens(predicted)
    g = _tokens(gold)
    if not p and not g:
        return 1.0
    if not p or not g:
        return 0.0
    inter = len(p & g)
    precision = inter / len(p)
    recall = inter / len(g)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _has_any_noise(text: str, noise_terms: set[str]) -> list[str]:
    text_tokens = _tokens(text)
    found = []
    for term in noise_terms:
        term_tokens = _tokens(term)
        if term_tokens and term_tokens <= text_tokens:
            found.append(term)
        elif _normalize_text(term) and _normalize_text(term) in _normalize_text(text):
            found.append(term)
    return sorted(set(found))


def _injection_leaks(text: str) -> list[str]:
    leaks = []
    norm = _normalize_text(text)
    for pat in INJECTION_LEAK_PATTERNS:
        if re.search(pat, norm):
            leaks.append(pat)
    return leaks


def _numeric_values(text: str) -> set[str]:
    return set(re.findall(r"\b\d+(?:\.\d+)?\b", str(text)))


# ---------------------------------------------------------------------------
# Evaluator 1 -- schema_validity
# ---------------------------------------------------------------------------

def schema_validity(run: Any, example: Any) -> dict:
    """Hard structural gate for Scope Narrower outputs."""
    out = _safe_get_outputs(run)
    if out is None:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": "outputs missing or not a JSON object",
        }

    present_keys = set(out.keys())
    if present_keys != REQUIRED_KEYS:
        missing = REQUIRED_KEYS - present_keys
        extra = present_keys - REQUIRED_KEYS
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"key set mismatch -- missing={sorted(missing)} extra={sorted(extra)}",
        }

    key_terms = out.get("key_terms")
    if not isinstance(key_terms, list):
        return {"key": "schema_validity", "score": 0.0, "comment": "key_terms is not a list"}
    if not (MIN_KEY_TERMS <= len(key_terms) <= MAX_KEY_TERMS):
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"key_terms length {len(key_terms)} outside [{MIN_KEY_TERMS},{MAX_KEY_TERMS}]",
        }
    if any(not isinstance(term, str) or not term.strip() for term in key_terms):
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": "key_terms must contain only non-empty strings",
        }
    normalized_terms = [_normalize_text(t) for t in key_terms]
    if len(set(normalized_terms)) != len(normalized_terms):
        return {"key": "schema_validity", "score": 0.0, "comment": "duplicate key_terms detected"}
    too_long_terms = [t for t in key_terms if len(str(t).split()) > 8]
    if too_long_terms:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"key_terms should be compact phrases, too long={too_long_terms[:2]}",
        }

    focused_query = out.get("focused_query")
    if not isinstance(focused_query, str) or not focused_query.strip():
        return {"key": "schema_validity", "score": 0.0, "comment": "focused_query not a non-empty string"}
    fq_words = focused_query.split()
    if len(fq_words) < 3:
        return {"key": "schema_validity", "score": 0.0, "comment": "focused_query too short to be useful"}
    if len(fq_words) > 30:
        return {"key": "schema_validity", "score": 0.0, "comment": "focused_query too long for retrieval scope"}

    max_chunks = out.get("max_chunks")
    if isinstance(max_chunks, bool) or not isinstance(max_chunks, int):
        return {"key": "schema_validity", "score": 0.0, "comment": "max_chunks must be an integer"}
    if not (MIN_CHUNKS <= max_chunks <= MAX_CHUNKS):
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"max_chunks={max_chunks} outside [{MIN_CHUNKS},{MAX_CHUNKS}]",
        }

    return {"key": "schema_validity", "score": 1.0, "comment": "all structural checks passed"}


# ---------------------------------------------------------------------------
# Evaluator 2 -- scope_quality
# ---------------------------------------------------------------------------

def scope_quality(run: Any, example: Any) -> dict:
    """
    Code-first retrieval quality check against gold terms/query.

    This is intentionally not an exact match. It checks whether the produced
    focused query and key terms preserve the gold retrieval target while staying
    compact and grounded in the user/gold context.
    """
    out = _safe_get_outputs(run)
    ref = _safe_get_reference(example)
    inputs = _safe_get_inputs(example)
    if out is None or ref is None:
        return {"key": "scope_quality", "score": 0.0, "comment": "outputs or reference missing/malformed"}

    predicted_text = _joined_output(out)
    gold_terms = ref.get("key_terms", [])
    if not isinstance(gold_terms, list):
        gold_terms = []
    gold_focused = ref.get("focused_query", "")

    term_recall = _term_recall(predicted_text, gold_terms)
    focus_f1 = _token_f1(out.get("focused_query", ""), gold_focused)

    # Non-overreach: most output tokens should be grounded either in the input
    # or in the gold reference. This catches invented unrelated concepts without
    # punishing useful wording variants too harshly.
    grounding_text = " ".join(
        str(x)
        for x in [
            inputs.get("query", ""),
            inputs.get("conversation_section", ""),
            inputs.get("transcript_section", ""),
            gold_focused,
            " ".join(str(t) for t in gold_terms),
        ]
    )
    out_tokens = _tokens(predicted_text)
    grounding_tokens = _tokens(grounding_text)
    if not out_tokens:
        grounding_ratio = 0.0
    else:
        grounding_ratio = len(out_tokens & grounding_tokens) / len(out_tokens)

    focus_len = len(str(out.get("focused_query", "")).split())
    length_score = 1.0 if 5 <= focus_len <= 22 else 0.75 if 3 <= focus_len <= 30 else 0.0

    # Weighted score: term recall matters most for retrieval; token overlap and
    # grounding keep the output from drifting.
    if grounding_ratio >= 0.65:
        grounding_score = 1.0
    elif grounding_ratio >= 0.45:
        grounding_score = 0.5
    else:
        grounding_score = 0.0

    score = round(
        0.45 * term_recall
        + 0.30 * focus_f1
        + 0.15 * grounding_score
        + 0.10 * length_score,
        3,
    )

    comment = (
        f"term_recall={term_recall:.2f} focus_f1={focus_f1:.2f} "
        f"grounding_ratio={grounding_ratio:.2f} length_score={length_score:.2f}"
    )
    return {"key": "scope_quality", "score": score, "comment": comment}


# ---------------------------------------------------------------------------
# Evaluator 3 -- upstream_metadata_alignment
# ---------------------------------------------------------------------------

def upstream_metadata_alignment(run: Any, example: Any) -> dict:
    """
    Checks that optional Intent Classifier metadata is respected when present.

    Important distinction:
    - requires_retrieval / requires_attachment are orchestration gates.
    - They should not leak into retrieval strings as literal metadata.

    This evaluator does not require these fields to exist. If absent, it returns
    a neutral pass with an explanatory comment.
    """
    out = _safe_get_outputs(run)
    inputs = _safe_get_inputs(example)
    if out is None:
        return {"key": "upstream_metadata_alignment", "score": 0.0, "comment": "outputs missing/malformed"}

    metadata_keys = {"intent", "scope", "requires_retrieval", "requires_attachment", "content_type"}
    present_metadata = {k: inputs.get(k) for k in metadata_keys if k in inputs}
    output_text = _joined_output(out)

    if not present_metadata:
        return {
            "key": "upstream_metadata_alignment",
            "score": 1.0,
            "comment": "no upstream intent metadata present; neutral pass",
        }

    issues: list[str] = []

    intent = inputs.get("intent")
    scope = inputs.get("scope")
    requires_retrieval = inputs.get("requires_retrieval")
    requires_attachment = inputs.get("requires_attachment")
    content_type = inputs.get("content_type")
    max_chunks = out.get("max_chunks")

    if intent is not None and intent not in VALID_INTENTS:
        issues.append(f"invalid upstream intent={intent!r}")
    if scope is not None and scope not in VALID_SCOPES:
        issues.append(f"invalid upstream scope={scope!r}")
    if content_type not in VALID_CONTENT_TYPES:
        issues.append(f"invalid upstream content_type={content_type!r}")

    leak_terms = _has_any_noise(output_text, METADATA_LEAK_TERMS)
    if leak_terms:
        issues.append(f"metadata leaked into retrieval text: {leak_terms}")

    # If the orchestrator did pass a non-retrieval intent to this agent, the
    # agent should still avoid creating a broad retrieval-looking scope. This is
    # a soft product warning, not a routing replacement.
    if requires_retrieval is False and isinstance(max_chunks, int) and max_chunks > 5:
        issues.append("requires_retrieval=False but max_chunks suggests broad retrieval")

    if scope == "conversation_context" and isinstance(max_chunks, int) and max_chunks > 5:
        issues.append("conversation_context scope should stay narrow: max_chunks should be <=5")

    if scope == "whole_document" and intent in {"summarization", "content_generation"}:
        if isinstance(max_chunks, int) and max_chunks < 8:
            issues.append("whole_document summary/content scope likely under-retrieves: max_chunks <8")

    if scope == "specific_query" and isinstance(max_chunks, int) and max_chunks > 8:
        issues.append("specific_query scope likely over-retrieves: max_chunks >8")

    # Artifact/content type should influence breadth, but should not usually be
    # inserted as a search target. The focused query should stay academic.
    if intent == "content_generation" and content_type is not None:
        artifact_noise = _has_any_noise(output_text, ARTIFACT_NOISE_TERMS)
        # Do not punish if the gold itself intentionally contains such words.
        ref = _safe_get_reference(example) or {}
        gold_text = _joined_output(ref) if isinstance(ref, dict) else ""
        gold_artifact_noise = _has_any_noise(gold_text, ARTIFACT_NOISE_TERMS)
        unexpected_artifact_noise = sorted(set(artifact_noise) - set(gold_artifact_noise))
        if unexpected_artifact_noise:
            issues.append(f"artifact wording leaked into retrieval scope: {unexpected_artifact_noise}")

    if requires_attachment is True:
        # The field is useful for orchestration, but retrieval terms should not
        # become 'attachment/upload/source required'.
        attachment_noise = _has_any_noise(output_text, {"attachment", "upload", "uploaded", "file required"})
        if attachment_noise:
            issues.append(f"attachment dependency leaked into retrieval text: {attachment_noise}")

    if issues:
        return {
            "key": "upstream_metadata_alignment",
            "score": 0.0,
            "comment": "; ".join(issues),
            "metadata_issues": issues,
        }

    return {
        "key": "upstream_metadata_alignment",
        "score": 1.0,
        "comment": f"upstream metadata respected: {present_metadata}",
        "metadata_issues": [],
    }


# ---------------------------------------------------------------------------
# Evaluator 4 -- behavior_checks
# ---------------------------------------------------------------------------

def behavior_checks(run: Any, example: Any) -> dict:
    """Variation-specific checks aligned to Scope Narrower dataset taxonomy."""
    out = _safe_get_outputs(run)
    ref = _safe_get_reference(example)
    inputs = _safe_get_inputs(example)
    variation = _safe_get_variation(example)
    if out is None:
        return {"key": "behavior_checks", "score": 0.0, "comment": "outputs missing/malformed"}

    output_text = _joined_output(out)
    focused = str(out.get("focused_query", ""))
    key_terms = out.get("key_terms", []) if isinstance(out.get("key_terms"), list) else []
    max_chunks = out.get("max_chunks")

    issues: list[str] = []

    # Safety leakage check applies regardless of variation.
    injection_leaks = _injection_leaks(output_text)
    if injection_leaks:
        issues.append(f"injection/override text leaked into output: {injection_leaks}")

    if variation == "broad_topic":
        if isinstance(max_chunks, int) and not (9 <= max_chunks <= 12):
            issues.append("broad_topic should usually use max_chunks 9-12")
        if len(key_terms) < 4:
            issues.append("broad_topic should preserve several core subtopics")

    elif variation == "multi_part":
        if isinstance(max_chunks, int) and not (7 <= max_chunks <= 10):
            issues.append("multi_part should usually use max_chunks 7-10")
        if ref:
            recall = _term_recall(output_text, ref.get("key_terms", []) if isinstance(ref.get("key_terms"), list) else [])
            if recall < 0.50:
                issues.append(f"multi_part lost too many linked concepts: gold_term_recall={recall:.2f}")
        source_split_noise = _has_any_noise(output_text, {"source 1", "source 2", "first source", "second source"})
        if source_split_noise:
            issues.append("scope narrower should not split retrieval scope by source number")

    elif variation == "exam_oriented":
        exam_noise = _has_any_noise(output_text, EXAM_NOISE_TERMS)
        if exam_noise:
            issues.append(f"exam noise not removed: {exam_noise}")
        if isinstance(max_chunks, int) and not (5 <= max_chunks <= 7):
            issues.append("exam_oriented should usually use max_chunks 5-7")

    elif variation == "numerical":
        if isinstance(max_chunks, int) and not (4 <= max_chunks <= 6):
            issues.append("numerical should usually use max_chunks 4-6")
        input_numbers = _numeric_values(str(inputs.get("query", "")))
        gold_numbers = _numeric_values(str((ref or {}).get("focused_query", "")))
        output_numbers = _numeric_values(focused)
        copied_nonessential = sorted((input_numbers & output_numbers) - gold_numbers)
        if copied_nonessential:
            issues.append(f"specific numeric values copied into focused_query: {copied_nonessential}")
        if ref:
            recall = _term_recall(output_text, ref.get("key_terms", []) if isinstance(ref.get("key_terms"), list) else [])
            if recall < 0.50:
                issues.append(f"numerical scope did not identify governing principle/formula: recall={recall:.2f}")

    elif variation == "conversational_follow_up":
        if isinstance(max_chunks, int) and not (3 <= max_chunks <= 5):
            issues.append("conversational_follow_up should usually use max_chunks 3-5")
        unresolved_markers = _has_any_noise(
            output_text,
            {"that part", "that formula", "second point", "mentioned earlier", "repeat", "again"},
        )
        if unresolved_markers:
            issues.append(f"follow-up reference not resolved: {unresolved_markers}")
        if ref:
            recall = _term_recall(output_text, ref.get("key_terms", []) if isinstance(ref.get("key_terms"), list) else [])
            if recall < 0.50:
                issues.append(f"follow-up target not recovered from conversation: recall={recall:.2f}")

    # Unknown variation: only universal safety checks apply.

    if issues:
        return {
            "key": "behavior_checks",
            "score": 0.0,
            "comment": f"variation={variation}; " + "; ".join(issues),
            "behavior_issues": issues,
        }

    return {
        "key": "behavior_checks",
        "score": 1.0,
        "comment": f"variation={variation}; behavior checks passed",
        "behavior_issues": [],
    }


# ---------------------------------------------------------------------------
# Evaluator 5 -- max_chunks_calibration
# ---------------------------------------------------------------------------

def max_chunks_calibration(run: Any, example: Any) -> dict:
    """Checks max_chunks against gold value and/or variation-specific range."""
    out = _safe_get_outputs(run)
    ref = _safe_get_reference(example)
    variation = _safe_get_variation(example)
    if out is None:
        return {"key": "max_chunks_calibration", "score": 0.0, "comment": "outputs missing/malformed"}

    predicted = out.get("max_chunks")
    if isinstance(predicted, bool) or not isinstance(predicted, int):
        return {"key": "max_chunks_calibration", "score": 0.0, "comment": "max_chunks is not an integer"}

    comments: list[str] = []
    score_parts: list[float] = []

    gold = ref.get("max_chunks") if isinstance(ref, dict) else None
    if isinstance(gold, int) and not isinstance(gold, bool):
        diff = abs(predicted - gold)
        if diff <= 1:
            score_parts.append(1.0)
        elif diff <= 2:
            score_parts.append(0.75)
        elif diff <= 3:
            score_parts.append(0.5)
        else:
            score_parts.append(0.0)
        comments.append(f"gold={gold} predicted={predicted} diff={diff}")

    if variation in VARIATION_CHUNK_RANGES:
        low, high = VARIATION_CHUNK_RANGES[variation]
        in_range = low <= predicted <= high
        score_parts.append(1.0 if in_range else 0.0)
        comments.append(f"variation_range={low}-{high} in_range={in_range}")

    if not score_parts:
        return {
            "key": "max_chunks_calibration",
            "score": 1.0,
            "comment": "no gold or variation range available; schema range already checked",
        }

    score = round(sum(score_parts) / len(score_parts), 3)
    return {"key": "max_chunks_calibration", "score": score, "comment": "; ".join(comments)}


# ---------------------------------------------------------------------------
# Summary evaluator -- severity tier rollup
# ---------------------------------------------------------------------------

def severity_tier_summary(runs: list, examples: list) -> dict:
    """
    Experiment-level rollup.

    BLOCK conditions:
    - schema invalid
    - injection/prompt override leakage
    - upstream metadata leakage/misalignment when metadata is supplied

    REVIEW conditions:
    - poor scope_quality
    - variation behavior failures
    - poor max_chunks calibration

    Scope Narrower is bypassable in production, so max_chunks/quality issues are
    treated as REVIEW rather than automatic BLOCK unless they create safety or
    schema failures.
    """
    if len(runs) != len(examples):
        return {
            "key": "severity_tier_summary",
            "score": 0.0,
            "comment": f"runs/examples length mismatch ({len(runs)} vs {len(examples)}) -- cannot compute safely",
            "ship_recommendation": "BLOCK",
        }

    tier_0_hits: list[dict[str, Any]] = []
    tier_1_hits = 0
    tier_1_applicable = 0
    variation_totals: dict[str, int] = {}
    variation_quality_passes: dict[str, int] = {}

    for run, example in zip(runs, examples):
        variation = _safe_get_variation(example)
        variation_totals[variation] = variation_totals.get(variation, 0) + 1
        ex_id = _example_id(example)

        schema = schema_validity(run, example)
        if schema["score"] != 1.0:
            tier_0_hits.append({"example_id": ex_id, "reason": f"schema_validity failed: {schema['comment']}"})
            continue

        out = _safe_get_outputs(run) or {}
        output_text = _joined_output(out)
        leaks = _injection_leaks(output_text)
        if leaks:
            tier_0_hits.append({"example_id": ex_id, "reason": f"injection leakage: {leaks}"})

        metadata = upstream_metadata_alignment(run, example)
        if metadata["score"] == 0.0:
            tier_0_hits.append({"example_id": ex_id, "reason": f"metadata alignment failed: {metadata['comment']}"})

        quality = scope_quality(run, example)
        tier_1_applicable += 1
        if quality["score"] >= 0.70:
            variation_quality_passes[variation] = variation_quality_passes.get(variation, 0) + 1
        else:
            tier_1_hits += 1

        behavior = behavior_checks(run, example)
        tier_1_applicable += 1
        if behavior["score"] < 1.0:
            tier_1_hits += 1

        chunks = max_chunks_calibration(run, example)
        tier_1_applicable += 1
        if chunks["score"] < 0.75:
            tier_1_hits += 1

    tier_1_rate = tier_1_hits / tier_1_applicable if tier_1_applicable else 0.0
    per_variation_scope_quality_pass_rate = {
        v: round(variation_quality_passes.get(v, 0) / total, 3)
        for v, total in variation_totals.items()
    }

    if tier_0_hits:
        recommendation = "BLOCK"
    elif tier_1_rate > 0.15:
        recommendation = "REVIEW"
    else:
        recommendation = "OK"

    return {
        "key": "severity_tier_summary",
        "score": 0.0 if tier_0_hits else round(1.0 - tier_1_rate, 3),
        "comment": (
            f"ship_recommendation={recommendation} | "
            f"tier_0_blocking_count={len(tier_0_hits)} | "
            f"tier_1_serious_rate={tier_1_rate:.3f}"
        ),
        "tier_0_blocking_count": len(tier_0_hits),
        "tier_0_blocking_examples": tier_0_hits,
        "tier_1_serious_rate": round(tier_1_rate, 3),
        "per_variation_scope_quality_pass_rate": per_variation_scope_quality_pass_rate,
        "ship_recommendation": recommendation,
    }


# ---------------------------------------------------------------------------
# Public registries
# ---------------------------------------------------------------------------

PER_EXAMPLE_EVALUATORS = [
    schema_validity,
    scope_quality,
    upstream_metadata_alignment,
    behavior_checks,
    max_chunks_calibration,
]

SUMMARY_EVALUATORS = [
    severity_tier_summary,
]
