"""
chat_summarizer_evaluators.py

LangSmith custom evaluators for Agent 8: Chat Summarizer.

Agent role:
- Compresses old conversation history into structured Markdown.
- Runs in the Memory node when conversation history exceeds the summarization threshold.
- Feeds later Direct Chat and RAG turns via effective_history.
- It must summarize the transcript only. No source/PDF retrieval happens inside this agent.

Schema under test:
    summary_markdown: str

Expected input keys:
    old_conversation: str

Design choice:
- Code-first, not LLM/hybrid by default.
- Criticality: Tier 2. A bad summary can poison future chat/RAG context, but the
  output contract is structured and the main failure risks are deterministic:
  malformed Markdown structure, overlong summaries, missing formulas, invented
  unsupported facts, empty-section bloat, and weak alignment with gold summary.
- Add an optional LLM judge later only if you want a human-style assessment of
  narrative summary quality. Keep these evaluators as hard, cheap gates.

LangSmith usage:
    from chat_summarizer_evaluators import PER_EXAMPLE_EVALUATORS, SUMMARY_EVALUATORS

    client.evaluate(
        target_fn,
        data="nbm-prompt-chat_summarizer",
        evaluators=PER_EXAMPLE_EVALUATORS,
        summary_evaluators=SUMMARY_EVALUATORS,
    )
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REQUIRED_KEYS = {"summary_markdown"}
ALLOWED_KEYS = {"summary_markdown"}

ALLOWED_HEADINGS = [
    "## Summary",
    "## Key points from the chat",
    "## Definitions / formulas (if any)",
    "## Examples / analogies used",
    "## Open questions / next steps",
]

REQUIRED_BASE_HEADINGS = [
    "## Summary",
    "## Key points from the chat",
]

MAX_SUMMARY_WORDS = 220
MAX_SUMMARY_SECTION_SENTENCES = 4
MIN_KEY_BULLETS = 1
MAX_KEY_BULLETS = 8

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

LOW_VALUE_SECTION_PHRASES = {
    "none",
    "n/a",
    "not applicable",
    "no formulas",
    "no examples",
    "no open questions",
    "nothing",
}

EXAM_TERMS = {
    "neet", "cbse", "board", "exam", "pyq", "numerical", "mcq",
}


# ---------------------------------------------------------------------------
# Safe helpers
# ---------------------------------------------------------------------------

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
    # Keep simple formula-ish tokens too.
    return set(re.findall(r"[a-zA-Z0-9Ωμ°/+=∩∪^²³().-]+", _norm(text)))


def _content_tokens(text: str) -> set[str]:
    stop = {
        "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with",
        "is", "are", "was", "were", "be", "been", "being", "this", "that",
        "it", "as", "by", "from", "chat", "user", "assistant", "summary",
        "key", "points", "reviewed", "discussed", "explained", "asked",
    }
    return {t for t in _tokens(text) if len(t) > 2 and t not in stop}


def _jaccard(a: str, b: str) -> float:
    ta, tb = _content_tokens(a), _content_tokens(b)
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


def _headings(markdown: str) -> list[str]:
    return re.findall(r"^## .+$", markdown or "", flags=re.MULTILINE)


def _section(markdown: str, heading: str) -> str:
    pattern = rf"^{re.escape(heading)}\s*\n(.*?)(?=^## |\Z)"
    m = re.search(pattern, markdown or "", flags=re.MULTILINE | re.DOTALL)
    return m.group(1).strip() if m else ""


def _bullets(text: str) -> list[str]:
    return re.findall(r"^\s*[-*]\s+(.+)$", text or "", flags=re.MULTILINE)


def _sentence_count(text: str) -> int:
    # Simple sentence approximation.
    cleaned = re.sub(r"\n+", " ", text or "").strip()
    if not cleaned:
        return 0
    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    return len([p for p in parts if p.strip()])


def _extract_formulas(text: str) -> set[str]:
    """
    Pull formula-like snippets from transcript/summary.
    Intentionally simple and NCERT-friendly.
    """
    if not text:
        return set()

    patterns = [
        r"\b[A-Za-z][A-Za-z0-9]*\s*=\s*[^,\n.;]+",
        r"\bP\s*\([^)]*\)\s*=\s*[^,\n.;]+",
        r"\b[A-Za-z]\s*[∩∪]\s*[A-Za-z]\b",
        r"\b\d+\s*[A-Za-zΩ°]+\b",
        r"\b[a-zA-Z]\s*(?:squared|cubed)\b",
        r"\b[a-zA-Z]\^?\d+\b",
    ]
    found = set()
    for p in patterns:
        for m in re.findall(p, text):
            val = re.sub(r"\s+", " ", str(m)).strip()
            if len(val) >= 2:
                found.add(_norm(val))
    return found


def _numeric_tokens(text: str) -> set[str]:
    return set(re.findall(r"\b\d+(?:\.\d+)?\b", text or ""))


def parse_model_response_to_outputs(raw_text: str) -> dict:
    """
    Defensive parser for target functions that receive raw model text.
    Chat Summarizer usually returns Markdown. If not JSON, wrap as:
        {"summary_markdown": raw_text}
    """
    if not isinstance(raw_text, str):
        return {}
    text = raw_text.strip()
    if not text:
        return {"summary_markdown": ""}

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

    return {"summary_markdown": text}


# ---------------------------------------------------------------------------
# Evaluator 1: schema_validity
# ---------------------------------------------------------------------------

def schema_validity(run, example) -> dict:
    out = _safe_get_outputs(run)
    if out is None:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": "outputs missing or not a JSON object",
        }

    present = set(out.keys())
    missing = REQUIRED_KEYS - present
    extra = present - ALLOWED_KEYS
    if missing or extra:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"key set mismatch -- missing={sorted(missing)} extra={sorted(extra)}",
        }

    summary = out.get("summary_markdown")
    if not isinstance(summary, str):
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"summary_markdown must be string, got {type(summary).__name__}",
        }

    if not summary.strip():
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": "summary_markdown is empty",
        }

    return {
        "key": "schema_validity",
        "score": 1.0,
        "comment": "schema valid",
    }


# ---------------------------------------------------------------------------
# Evaluator 2: markdown_structure
# ---------------------------------------------------------------------------

def markdown_structure(run, example) -> dict:
    """
    Checks exact heading contract and basic bullet structure.
    Empty optional sections should usually be omitted, not filled with N/A.
    """
    out = _safe_get_outputs(run)
    if out is None:
        return {
            "key": "markdown_structure",
            "score": 0.0,
            "comment": "outputs missing/malformed",
            "hard_rule_violated": False,
        }

    md = out.get("summary_markdown", "")
    if not isinstance(md, str):
        return {
            "key": "markdown_structure",
            "score": 0.0,
            "comment": "summary_markdown missing/non-string",
            "hard_rule_violated": False,
        }

    headings = _headings(md)
    issues = []
    hard = False

    for h in REQUIRED_BASE_HEADINGS:
        if h not in headings:
            issues.append(f"missing_required_heading:{h}")
            hard = True

    disallowed = [h for h in headings if h not in ALLOWED_HEADINGS]
    if disallowed:
        issues.append(f"disallowed_heading:{disallowed}")
        hard = True

    # Heading order must follow allowed order.
    indices = [ALLOWED_HEADINGS.index(h) for h in headings if h in ALLOWED_HEADINGS]
    if indices != sorted(indices):
        issues.append("headings_out_of_order")

    key_section = _section(md, "## Key points from the chat")
    key_bullets = _bullets(key_section)
    if not key_bullets:
        issues.append("key_points_has_no_bullets")
        hard = True
    elif len(key_bullets) > MAX_KEY_BULLETS:
        issues.append(f"too_many_key_bullets:{len(key_bullets)}")

    # Optional sections should not be present just to say empty.
    for h in ALLOWED_HEADINGS[2:]:
        body = _section(md, h)
        if body and _norm(body).strip("-* ").strip() in LOW_VALUE_SECTION_PHRASES:
            issues.append(f"empty_optional_section_not_omitted:{h}")

    if hard:
        return {
            "key": "markdown_structure",
            "score": 0.0,
            "comment": "; ".join(issues),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "markdown_structure",
            "score": 0.5,
            "comment": "; ".join(issues),
            "hard_rule_violated": False,
        }

    return {
        "key": "markdown_structure",
        "score": 1.0,
        "comment": "markdown structure checks passed",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 3: transcript_grounding
# ---------------------------------------------------------------------------

def transcript_grounding(run, example) -> dict:
    """
    Code-based hallucination screen.
    It checks:
    - no source/page/PDF claims
    - important summary tokens should mostly come from transcript or gold summary
    - numbers/formulas in summary should be traceable to transcript or gold
    """
    out = _safe_get_outputs(run)
    ref = _safe_get_reference(example)
    inputs = _safe_get_inputs(example)

    if out is None:
        return {
            "key": "transcript_grounding",
            "score": 0.0,
            "comment": "outputs missing/malformed",
            "hard_rule_violated": False,
        }

    md = out.get("summary_markdown", "")
    old_conv = inputs.get("old_conversation", "")
    gold = ref.get("summary_markdown", "") if isinstance(ref, dict) else ""

    if not isinstance(md, str):
        return {
            "key": "transcript_grounding",
            "score": 0.0,
            "comment": "summary_markdown missing/non-string",
            "hard_rule_violated": False,
        }

    if _regex_any(md, SOURCE_CLAIM_PATTERNS):
        return {
            "key": "transcript_grounding",
            "score": 0.0,
            "comment": "summary makes source/PDF/page/citation claim though summarizer only sees transcript",
            "hard_rule_violated": True,
        }

    if _contains_any(md, BANNED_PATTERNS):
        return {
            "key": "transcript_grounding",
            "score": 0.0,
            "comment": "summary contains banned self-reference pattern",
            "hard_rule_violated": True,
        }

    transcript_tokens = _content_tokens(old_conv)
    gold_tokens = _content_tokens(gold)
    summary_tokens = _content_tokens(md)

    if not transcript_tokens:
        return {
            "key": "transcript_grounding",
            "score": 0.5,
            "comment": "old_conversation missing/empty; cannot fully check grounding",
            "hard_rule_violated": False,
        }

    # Ignore markdown headings.
    heading_tokens = _content_tokens(" ".join(ALLOWED_HEADINGS))
    check_tokens = summary_tokens - heading_tokens - {"formula", "formulas", "definitions", "examples", "analogies", "next", "steps"}

    unsupported = sorted([t for t in check_tokens if t not in transcript_tokens and t not in gold_tokens])
    unsupported_ratio = len(unsupported) / max(1, len(check_tokens))

    # Numeric/formula hallucination: summary should not introduce new numeric values.
    conv_nums = _numeric_tokens(old_conv) | _numeric_tokens(gold)
    sum_nums = _numeric_tokens(md)
    new_nums = sum_nums - conv_nums

    conv_formulas = _extract_formulas(old_conv) | _extract_formulas(gold)
    sum_formulas = _extract_formulas(md)
    # Formula tokenization is imperfect; only flag if summary contains formula-like snippets
    # and none overlap with transcript/gold formula-like snippets.
    new_formula_risk = bool(sum_formulas and conv_formulas and not any(_jaccard(a, b) >= 0.3 for a in sum_formulas for b in conv_formulas))

    if new_nums:
        return {
            "key": "transcript_grounding",
            "score": 0.0,
            "comment": f"summary introduces numeric value(s) not in transcript/gold: {sorted(new_nums)}",
            "hard_rule_violated": True,
        }

    if new_formula_risk:
        return {
            "key": "transcript_grounding",
            "score": 0.0,
            "comment": "summary appears to introduce formula-like content not grounded in transcript/gold",
            "hard_rule_violated": True,
        }

    if unsupported_ratio > 0.45 and len(check_tokens) >= 10:
        return {
            "key": "transcript_grounding",
            "score": 0.0,
            "comment": f"high unsupported token ratio={unsupported_ratio:.2f}; sample={unsupported[:10]}",
            "hard_rule_violated": True,
        }

    if unsupported_ratio > 0.30 and len(check_tokens) >= 10:
        return {
            "key": "transcript_grounding",
            "score": 0.5,
            "comment": f"moderate unsupported token ratio={unsupported_ratio:.2f}; sample={unsupported[:10]}",
            "hard_rule_violated": False,
        }

    return {
        "key": "transcript_grounding",
        "score": 1.0,
        "comment": f"grounding checks passed; unsupported_ratio={unsupported_ratio:.2f}",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 4: summary_completeness
# ---------------------------------------------------------------------------

def summary_completeness(run, example) -> dict:
    """
    Checks alignment with gold summary and preservation of important chat details.
    This is intentionally lightweight, not exact-match.
    """
    out = _safe_get_outputs(run)
    ref = _safe_get_reference(example)
    inputs = _safe_get_inputs(example)
    variation = _safe_get_variation(example)

    if out is None or ref is None:
        return {
            "key": "summary_completeness",
            "score": 0.0,
            "comment": "outputs or reference missing/malformed",
        }

    md = out.get("summary_markdown", "")
    gold = ref.get("summary_markdown", "")
    old_conv = inputs.get("old_conversation", "")

    if not isinstance(md, str) or not isinstance(gold, str):
        return {
            "key": "summary_completeness",
            "score": 0.0,
            "comment": "summary_markdown/gold must be strings",
        }

    overlap = _jaccard(md, gold)

    # Formula preservation: if transcript/gold has formula-like snippets, summary should
    # contain at least some formula/value cues.
    conv_formulas = _extract_formulas(old_conv) | _extract_formulas(gold)
    md_formulas = _extract_formulas(md)
    formula_ok = True
    if variation == "numerical_formula" or conv_formulas:
        formula_ok = bool(md_formulas or (_numeric_tokens(md) & (_numeric_tokens(old_conv) | _numeric_tokens(gold))))

    # Exam framing: preserve NEET/CBSE drill tone if it was part of the transcript/gold.
    exam_expected = variation == "neet_exam_framing" or bool(EXAM_TERMS & _tokens(old_conv))
    exam_ok = True
    if exam_expected:
        exam_ok = bool(EXAM_TERMS & _tokens(md) or EXAM_TERMS & _tokens(gold))

    if overlap >= 0.25 and formula_ok and exam_ok:
        return {
            "key": "summary_completeness",
            "score": 1.0,
            "comment": f"summary aligned with gold; overlap={overlap:.2f}",
        }

    issues = []
    if overlap < 0.25:
        issues.append(f"low_gold_overlap={overlap:.2f}")
    if not formula_ok:
        issues.append("formula_or_numeric_content_not_preserved")
    if not exam_ok:
        issues.append("exam_framing_not_preserved")

    # Partial credit if only overlap is weak but core structure exists.
    if overlap >= 0.15 and formula_ok and exam_ok:
        return {
            "key": "summary_completeness",
            "score": 0.5,
            "comment": "; ".join(issues),
        }

    return {
        "key": "summary_completeness",
        "score": 0.0,
        "comment": "; ".join(issues),
    }


# ---------------------------------------------------------------------------
# Evaluator 5: conciseness
# ---------------------------------------------------------------------------

def conciseness(run, example) -> dict:
    """
    Keeps memory summaries compact. They are context-compression artifacts,
    not full lesson rewrites.
    """
    out = _safe_get_outputs(run)
    variation = _safe_get_variation(example)

    if out is None:
        return {
            "key": "conciseness",
            "score": 0.0,
            "comment": "outputs missing/malformed",
        }

    md = out.get("summary_markdown", "")
    if not isinstance(md, str):
        return {
            "key": "conciseness",
            "score": 0.0,
            "comment": "summary_markdown missing/non-string",
        }

    wc = _word_count(md)
    max_words = 280 if variation == "long_multi_topic" else MAX_SUMMARY_WORDS

    issues = []

    if wc > max_words:
        issues.append(f"too_long:{wc}_words")

    summary_body = _section(md, "## Summary")
    sent_count = _sentence_count(summary_body)
    if sent_count > MAX_SUMMARY_SECTION_SENTENCES:
        issues.append(f"summary_section_too_many_sentences:{sent_count}")

    key_bullets = _bullets(_section(md, "## Key points from the chat"))
    if len(key_bullets) > MAX_KEY_BULLETS:
        issues.append(f"too_many_key_point_bullets:{len(key_bullets)}")

    other_bullets = []
    for h in ALLOWED_HEADINGS[2:]:
        other_bullets.extend(_bullets(_section(md, h)))
    if len(other_bullets) > 8:
        issues.append(f"too_many_optional_section_bullets:{len(other_bullets)}")

    if issues:
        return {
            "key": "conciseness",
            "score": 0.5 if wc <= max_words * 1.25 else 0.0,
            "comment": "; ".join(issues),
        }

    return {
        "key": "conciseness",
        "score": 1.0,
        "comment": f"concise summary ({wc} words)",
    }


# ---------------------------------------------------------------------------
# Summary evaluator
# ---------------------------------------------------------------------------

def chat_summarizer_severity_summary(runs: list, examples: list) -> dict:
    """
    BLOCK:
    - schema failure
    - missing required Markdown headings
    - source/PDF/page claims
    - clear hallucination of numbers/formulas/unsupported concepts

    REVIEW:
    - low gold alignment
    - conciseness / optional-section issues above threshold
    """
    if len(runs) != len(examples):
        return {
            "key": "chat_summarizer_severity_summary",
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
            tier_0.append({
                "example_id": getattr(example, "id", None),
                "reason": f"schema_validity failed: {schema['comment']}",
            })
            continue

        structure = markdown_structure(run, example)
        grounding = transcript_grounding(run, example)
        complete = summary_completeness(run, example)
        concise = conciseness(run, example)

        if structure.get("hard_rule_violated"):
            tier_0.append({
                "example_id": getattr(example, "id", None),
                "reason": f"structure hard failure: {structure['comment']}",
            })

        if grounding.get("hard_rule_violated"):
            tier_0.append({
                "example_id": getattr(example, "id", None),
                "reason": f"grounding hard failure: {grounding['comment']}",
            })

        tier_1_applicable += 3
        if complete["score"] < 1.0:
            tier_1 += 1
        if concise["score"] < 1.0:
            tier_1 += 1
        if structure["score"] < 1.0:
            tier_1 += 1

        if (
            structure["score"] == 1.0
            and grounding["score"] == 1.0
            and complete["score"] == 1.0
            and concise["score"] == 1.0
        ):
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
        "key": "chat_summarizer_severity_summary",
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


# ---------------------------------------------------------------------------
# Public registries
# ---------------------------------------------------------------------------

PER_EXAMPLE_EVALUATORS = [
    schema_validity,
    markdown_structure,
    transcript_grounding,
    summary_completeness,
    conciseness,
]

SUMMARY_EVALUATORS = [
    chat_summarizer_severity_summary,
]
