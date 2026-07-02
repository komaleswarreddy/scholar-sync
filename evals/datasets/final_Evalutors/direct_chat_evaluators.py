"""
direct_chat_evaluators.py

LangSmith custom evaluators for Agent 6: Direct Chat.

Agent role:
- Terminal non-RAG path for conversational/product/navigation messages.
- It should NOT claim source/PDF/page evidence, because retrieval is bypassed.
- It may use optional chat summary/transcript for context, but must stay concise
  and product-accurate.

Schema under test:
    response: str

Expected input keys:
    message: str
Optional input keys:
    chat_rolling_summary: str
    conversation_transcript: str

Design choice:
- Code-first, not LLM/hybrid by default.
- Reason: this is a low-to-medium criticality terminal bypass agent. The important
  risks are deterministic enough: malformed output, source hallucination, wrong
  product navigation, missing product CTA, banned policy phrases, and bloated tone.
- A separate optional LLM judge can be added later for warmth/semantic nuance, but
  should not be required for model/prompt selection.

LangSmith usage:
    from direct_chat_evaluators import PER_EXAMPLE_EVALUATORS, SUMMARY_EVALUATORS

    client.evaluate(
        target_fn,
        data="nbm-prompt-direct_chat",
        evaluators=PER_EXAMPLE_EVALUATORS,
        summary_evaluators=SUMMARY_EVALUATORS,
    )
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional


REQUIRED_KEYS = {"response"}
ALLOWED_KEYS = {"response"}

MAX_RESPONSE_WORDS_DEFAULT = 120

VALID_NAV_LABELS = {
    "home", "library", "problem solver", "study plan", "study planner",
    "analytics", "assets", "studios", "tutor mode", "tutor", "sources", "upload",
}

VALID_ROUTES = {
    "/home", "/library", "/problem-solver", "/study-planner",
    "/analytics", "/assets", "/studios", "/tutor",
}

PRODUCT_FEATURE_TERMS = {
    "scholarsync", "sources", "upload", "pdf", "notes", "library", "home",
    "studios", "quiz", "flashcards", "mind map", "slide deck",
    "practice questions", "study plan", "tutor", "ncert", "analytics", "assets",
}

SOURCE_CLAIM_PATTERNS = [
    r"\baccording to (your|the) (pdf|file|notes|chapter|source)\b",
    r"\bfrom (your|the) (pdf|file|notes|chapter|source)\b",
    r"\bbased on (your|the) (pdf|file|notes|chapter|source)\b",
    r"\bpage\s+\d+\b",
    r"\[page\s*\d+\]",
    r"\bcitation\b",
    r"\bsource says\b",
]

BANNED_PATTERNS = {
    "as an ai language model",
}

OVERLY_SHAMING_PHRASES = {
    "too weak", "lazy", "obviously", "stupid", "dumb",
}

UNSUPPORTED_FEATURE_CLAIMS = {
    "guaranteed marks", "guaranteed score", "solve live exam",
    "bypass detector", "unlimited file size", "all languages supported",
}

PRODUCT_QUERY_HINTS = {
    "what can you do", "what is scholarsync", "features", "how does this work",
    "product", "study assistant", "help me study",
}

STUDIO_HINTS = {
    "quiz", "flashcard", "flashcards", "mind map", "slide", "deck",
    "practice questions", "study plan", "studios",
}

TUTOR_HINTS = {
    "tutor", "ncert", "class", "chapter",
}

NAVIGATION_HINTS = {
    "where", "click", "open", "go to", "find", "upload", "select",
    "navigate", "how do i",
}


def _safe_get_outputs(run) -> Optional[dict]:
    try:
        out = run.outputs
        return out if isinstance(out, dict) else None
    except Exception:
        return None


def _safe_get_inputs(example) -> dict:
    try:
        inputs = example.inputs
        return inputs if isinstance(inputs, dict) else {}
    except Exception:
        return {}


def _safe_get_reference(example) -> Optional[dict]:
    try:
        ref = example.outputs
        return ref if isinstance(ref, dict) else None
    except Exception:
        return None


def _safe_get_variation(example) -> str:
    try:
        meta = example.metadata or {}
        return str(meta.get("variation", "unknown"))
    except Exception:
        return "unknown"


def _norm(text: Any) -> str:
    if text is None:
        return ""
    return re.sub(r"\s+", " ", str(text).strip().lower())


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9/.-]+", _norm(text)))


def _jaccard(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _contains_any(text: str, needles) -> bool:
    t = _norm(text)
    return any(_norm(n) in t for n in needles)


def _regex_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text, flags=re.IGNORECASE) for p in patterns)


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def _extract_routes(text: str) -> set[str]:
    return set(re.findall(r"/[a-zA-Z0-9_-]+(?:/[a-zA-Z0-9_-]+)?", text or ""))


def parse_model_response_to_outputs(raw_text: str) -> dict:
    """
    Defensive parser for target functions that receive raw text.
    Direct Chat can return plain markdown. If raw text is not JSON, wrap it as:
        {"response": raw_text}
    """
    if not isinstance(raw_text, str):
        return {}
    text = raw_text.strip()
    if not text:
        return {"response": ""}

    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        candidate = fence.group(1)
    else:
        brace = re.search(r"\{.*\}", text, re.DOTALL)
        candidate = brace.group(0) if brace else None

    if candidate:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

    return {"response": text}


def schema_validity(run, example) -> dict:
    out = _safe_get_outputs(run)
    if out is None:
        return {"key": "schema_validity", "score": 0.0,
                "comment": "outputs missing or not a JSON object"}

    present = set(out.keys())
    missing = REQUIRED_KEYS - present
    extra = present - ALLOWED_KEYS
    if missing or extra:
        return {"key": "schema_validity", "score": 0.0,
                "comment": f"key set mismatch -- missing={sorted(missing)} extra={sorted(extra)}"}

    response = out.get("response")
    if not isinstance(response, str):
        return {"key": "schema_validity", "score": 0.0,
                "comment": f"response must be string, got {type(response).__name__}"}

    if not response.strip():
        return {"key": "schema_validity", "score": 0.0,
                "comment": "response is empty"}

    return {"key": "schema_validity", "score": 1.0, "comment": "schema valid"}


def response_alignment(run, example) -> dict:
    """
    Light semantic alignment against the gold response.
    Uses overlap plus variation-specific cues. Not exact string match.
    """
    out = _safe_get_outputs(run)
    ref = _safe_get_reference(example)
    variation = _safe_get_variation(example)

    if out is None or ref is None:
        return {"key": "response_alignment", "score": 0.0,
                "comment": "outputs or reference missing/malformed"}

    response = out.get("response", "")
    gold = ref.get("response", "")

    if not isinstance(response, str) or not isinstance(gold, str):
        return {"key": "response_alignment", "score": 0.0,
                "comment": "response/gold response must be strings"}

    overlap = _jaccard(response, gold)
    response_norm = _norm(response)

    cue_pass = False
    if variation == "greeting_thanks":
        cue_pass = (
            len(response.split()) <= 35
            and (
                _contains_any(response, {"scholarsync", "ready", "study", "home", "library"})
                or any(response_norm.startswith(x) for x in ["hey", "hi", "hello", "good"])
            )
        )
    elif variation == "product_overview":
        cue_pass = _contains_any(response, {"scholarsync"}) and _contains_any(response, {"study", "sources", "notes", "class"})
    elif variation == "feature_studio_tools":
        cue_pass = _contains_any(response, {"studios"}) and _contains_any(response, {"quiz", "flashcards", "mind map", "slide deck"})
    elif variation == "feature_tutor_ncert":
        cue_pass = _contains_any(response, {"tutor", "ncert"}) and _contains_any(response, {"class", "subject", "chapter"})
    elif variation == "navigation_cta":
        cue_pass = _contains_any(response, VALID_NAV_LABELS) or bool(_extract_routes(response))

    if overlap >= 0.22 or cue_pass:
        return {"key": "response_alignment", "score": 1.0,
                "comment": f"aligned; gold_overlap={overlap:.2f}"}

    if overlap >= 0.12:
        return {"key": "response_alignment", "score": 0.5,
                "comment": f"partially aligned; gold_overlap={overlap:.2f}"}

    return {"key": "response_alignment", "score": 0.0,
            "comment": f"weak alignment; gold_overlap={overlap:.2f}"}


def no_source_claims(run, example) -> dict:
    """
    Direct Chat bypasses RAG, so it must not claim facts from selected files,
    page numbers, citations, or uploaded sources.
    """
    out = _safe_get_outputs(run)
    if out is None:
        return {"key": "no_source_claims", "score": 0.0,
                "comment": "outputs missing/malformed", "hard_rule_violated": False}

    response = out.get("response", "")
    if not isinstance(response, str):
        return {"key": "no_source_claims", "score": 0.0,
                "comment": "response missing/non-string", "hard_rule_violated": False}

    if _regex_any(response, SOURCE_CLAIM_PATTERNS):
        return {
            "key": "no_source_claims",
            "score": 0.0,
            "comment": "response makes source/page/citation claim despite non-RAG direct chat path",
            "hard_rule_violated": True,
        }

    return {"key": "no_source_claims", "score": 1.0,
            "comment": "no unsupported source claims detected", "hard_rule_violated": False}


def product_navigation_accuracy(run, example) -> dict:
    """
    Checks product/navigation claims only when relevant.
    It does not require every answer to mention routes.
    """
    out = _safe_get_outputs(run)
    inputs = _safe_get_inputs(example)
    variation = _safe_get_variation(example)

    if out is None:
        return {"key": "product_navigation_accuracy", "score": 0.0,
                "comment": "outputs missing/malformed", "hard_rule_violated": False}

    response = out.get("response", "")
    message = inputs.get("message", "")

    if not isinstance(response, str):
        return {"key": "product_navigation_accuracy", "score": 0.0,
                "comment": "response missing/non-string", "hard_rule_violated": False}

    routes = _extract_routes(response)
    invalid_routes = routes - VALID_ROUTES

    if invalid_routes:
        return {
            "key": "product_navigation_accuracy",
            "score": 0.0,
            "comment": f"invalid route(s) mentioned: {sorted(invalid_routes)}",
            "hard_rule_violated": True,
        }

    if _contains_any(response, UNSUPPORTED_FEATURE_CLAIMS):
        return {
            "key": "product_navigation_accuracy",
            "score": 0.0,
            "comment": "unsupported product capability claim detected",
            "hard_rule_violated": True,
        }

    needs_product = (
        variation in {"product_overview", "feature_studio_tools", "feature_tutor_ncert", "navigation_cta"}
        or _contains_any(message, PRODUCT_QUERY_HINTS | STUDIO_HINTS | TUTOR_HINTS | NAVIGATION_HINTS)
    )

    if not needs_product:
        return {"key": "product_navigation_accuracy", "score": 1.0,
                "comment": "not a product/navigation request; no route errors detected",
                "hard_rule_violated": False}

    if not _contains_any(response, PRODUCT_FEATURE_TERMS | VALID_NAV_LABELS) and not routes:
        return {
            "key": "product_navigation_accuracy",
            "score": 0.0,
            "comment": "product/navigation request but response lacks product labels, features, or valid routes",
            "hard_rule_violated": False,
        }

    if variation == "feature_studio_tools" or _contains_any(message, STUDIO_HINTS):
        if not _contains_any(response, {"studios", "/studios", "quiz", "flashcards", "mind map", "slide deck"}):
            return {"key": "product_navigation_accuracy", "score": 0.5,
                    "comment": "studio request only partially addressed",
                    "hard_rule_violated": False}

    if variation == "feature_tutor_ncert" or _contains_any(message, TUTOR_HINTS):
        if not _contains_any(response, {"tutor", "/tutor", "ncert", "class", "chapter"}):
            return {"key": "product_navigation_accuracy", "score": 0.5,
                    "comment": "tutor/NCERT request only partially addressed",
                    "hard_rule_violated": False}

    return {"key": "product_navigation_accuracy", "score": 1.0,
            "comment": "product/navigation checks passed", "hard_rule_violated": False}


def brevity_and_tone(run, example) -> dict:
    """
    Keeps Direct Chat from becoming RAG-like or overly formal.
    """
    out = _safe_get_outputs(run)
    variation = _safe_get_variation(example)

    if out is None:
        return {"key": "brevity_and_tone", "score": 0.0,
                "comment": "outputs missing/malformed"}

    response = out.get("response", "")
    if not isinstance(response, str):
        return {"key": "brevity_and_tone", "score": 0.0,
                "comment": "response missing/non-string"}

    wc = _word_count(response)
    max_words = 160 if variation in {"product_overview", "navigation_cta"} else MAX_RESPONSE_WORDS_DEFAULT

    issues = []

    if wc > max_words:
        issues.append(f"too_long_{wc}_words")

    if _contains_any(response, BANNED_PATTERNS):
        issues.append("contains_banned_ai_language_model_pattern")

    if _contains_any(response, OVERLY_SHAMING_PHRASES):
        issues.append("contains_shaming_language")

    heading_count = len(re.findall(r"^\s{0,3}#{1,6}\s+", response, flags=re.MULTILINE))
    if heading_count > 2:
        issues.append("too_many_markdown_headings_for_direct_chat")

    if issues:
        hard = any(x in issues for x in ["contains_banned_ai_language_model_pattern", "contains_shaming_language"])
        return {"key": "brevity_and_tone", "score": 0.0 if hard else 0.5,
                "comment": "; ".join(issues)}

    return {"key": "brevity_and_tone", "score": 1.0,
            "comment": f"brevity/tone checks passed ({wc} words)"}


def direct_chat_severity_summary(runs: list, examples: list) -> dict:
    """
    BLOCK:
    - schema failure
    - unsupported source/page/citation claim
    - invalid product route
    - banned/shaming tone

    REVIEW:
    - weak alignment or partial product response above threshold
    """
    if len(runs) != len(examples):
        return {
            "key": "direct_chat_severity_summary",
            "score": 0.0,
            "comment": f"runs/examples length mismatch ({len(runs)} vs {len(examples)})",
            "ship_recommendation": "BLOCK",
        }

    tier_0 = []
    tier_1 = 0
    tier_1_applicable = 0
    variation_totals: dict[str, int] = {}
    variation_passes: dict[str, int] = {}

    for run, example in zip(runs, examples):
        variation = _safe_get_variation(example)
        variation_totals[variation] = variation_totals.get(variation, 0) + 1

        schema = schema_validity(run, example)
        if schema["score"] == 0.0:
            tier_0.append({"example_id": getattr(example, "id", None),
                           "reason": f"schema_validity failed: {schema['comment']}"})
            continue

        source = no_source_claims(run, example)
        nav = product_navigation_accuracy(run, example)
        tone = brevity_and_tone(run, example)
        align = response_alignment(run, example)

        if source.get("hard_rule_violated"):
            tier_0.append({"example_id": getattr(example, "id", None),
                           "reason": source["comment"]})

        if nav.get("hard_rule_violated"):
            tier_0.append({"example_id": getattr(example, "id", None),
                           "reason": nav["comment"]})

        if tone["score"] == 0.0:
            tier_0.append({"example_id": getattr(example, "id", None),
                           "reason": f"tone/brevity hard failure: {tone['comment']}"})

        tier_1_applicable += 2
        if align["score"] < 1.0:
            tier_1 += 1
        if nav["score"] < 1.0:
            tier_1 += 1

        if align["score"] == 1.0 and source["score"] == 1.0 and nav["score"] == 1.0 and tone["score"] == 1.0:
            variation_passes[variation] = variation_passes.get(variation, 0) + 1

    tier_1_rate = (tier_1 / tier_1_applicable) if tier_1_applicable else 0.0

    per_variation_pass_rate = {
        v: round(variation_passes.get(v, 0) / total, 3)
        for v, total in variation_totals.items()
    }

    if tier_0:
        recommendation = "BLOCK"
    elif tier_1_rate > 0.20:
        recommendation = "REVIEW"
    else:
        recommendation = "OK"

    return {
        "key": "direct_chat_severity_summary",
        "score": 0.0 if tier_0 else round(1.0 - tier_1_rate, 3),
        "comment": (
            f"ship_recommendation={recommendation} | "
            f"tier_0_blocking_count={len(tier_0)} | "
            f"tier_1_review_rate={tier_1_rate:.3f}"
        ),
        "tier_0_blocking_count": len(tier_0),
        "tier_0_blocking_examples": tier_0,
        "tier_1_review_rate": round(tier_1_rate, 3),
        "per_variation_pass_rate": per_variation_pass_rate,
        "ship_recommendation": recommendation,
    }


PER_EXAMPLE_EVALUATORS = [
    schema_validity,
    response_alignment,
    no_source_claims,
    product_navigation_accuracy,
    brevity_and_tone,
]

SUMMARY_EVALUATORS = [
    direct_chat_severity_summary,
]
