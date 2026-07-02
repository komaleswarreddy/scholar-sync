"""
hallucination_guard_retry_evaluators.py

LangSmith custom evaluators for Agent 9: Hallucination Guard Retry.

Agent role:
- Post-RAG correction pass.
- Triggered after Agent 7 when deterministic overlap checks flag unsupported sentences.
- The retry prompt suffix instructs the model to remove, soften, or label as
  `General knowledge:` any unsupported sentence.
- It must rewrite using only the provided context evidence.

Production dependencies:
- Depends on Agent 7 RAG answer + retrieved context chunks.
- Inputs:
    answer: str
    context: str | list[str] | list[dict]
    unsupported_sentences: list[str]
- Output:
    corrected_answer: str
- Bypass when:
    ENABLE_HALLUCINATION_GUARD=False
    context empty
    answer already well-supported

Design choice:
- Code-first, not LLM/hybrid by default.
- Criticality: important post-generation safety/grounding guard, but the task is
  narrow and deterministic: remove flagged claims, avoid new facts, preserve
  grounded context, and avoid over-stripping pass-through examples.
- Agent 7 already has the required LLM judge. Adding another LLM judge here would
  add cost and variance without much extra value.

LangSmith usage:
    from hallucination_guard_retry_evaluators import PER_EXAMPLE_EVALUATORS, SUMMARY_EVALUATORS

    client.evaluate(
        target_fn,
        data="nbm-prompt-hallucination_guard_retry",
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

REQUIRED_KEYS = {"corrected_answer"}
ALLOWED_KEYS = {"corrected_answer"}

PASS_VARIATIONS = {"pass_through", "pass_minor_edit"}
REWRITE_VARIATIONS = {"rewrite_remove", "rewrite_soften", "rewrite_label_gk"}

GENERAL_KNOWLEDGE_LABEL = "general knowledge:"

BANNED_PATTERNS = {
    "as an ai language model",
}

RETRY_SUFFIX_RULE_TERMS = {
    "general knowledge:", "context", "evidence",
}

UNSUPPORTED_ABSOLUTES = {
    "always", "never", "only", "all", "worldwide", "guaranteed",
    "certainly", "definitely",
}

# Domain-neutral specific fact cues. Used only to detect new facts not in context.
SPECIFIC_FACT_PATTERNS = [
    r"\b\d+(?:\.\d+)?\b",                         # numbers
    r"\b\d{4}\b",                                  # years
    r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b",         # multi-word names
    r"\b[A-Z][a-z]+(?:'s)?\b",                     # capitalized terms
    r"\b[A-Z]{2,}\b",                              # abbreviations
]

CITATION_OR_PAGE_PATTERNS = [
    r"\bpage\s+\d+\b",
    r"\[page\s*\d+\]",
    r"\bcitation\b",
    r"\bsource\s+\d+\b",
]

MIN_PASS_THROUGH_OVERLAP_WITH_ANSWER = 0.55
MIN_REWRITE_OVERLAP_WITH_CONTEXT = 0.18
MIN_REWRITE_OVERLAP_WITH_GOLD = 0.22


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


def _safe_get_metadata(example) -> dict:
    try:
        meta = example.metadata or {}
        return meta if isinstance(meta, dict) else {}
    except Exception:
        return {}


def _safe_get_variation(example) -> str:
    return str(_safe_get_metadata(example).get("variation", "unknown"))


def _norm(text: Any) -> str:
    if text is None:
        return ""
    return re.sub(r"\s+", " ", str(text).strip().lower())


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9Ωμ°/+=∩∪^²³().-]+", _norm(text)))


def _content_tokens(text: str) -> set[str]:
    stop = {
        "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with",
        "is", "are", "was", "were", "be", "been", "being", "this", "that",
        "it", "as", "by", "from", "answer", "context", "evidence", "source",
        "corrected", "sentence", "sentences", "general", "knowledge",
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


def _context_to_text(context: Any) -> str:
    if context is None:
        return ""
    if isinstance(context, str):
        return context
    if isinstance(context, dict):
        for k in ("text", "content", "page_content", "chunk", "body"):
            if isinstance(context.get(k), str):
                return context[k]
        return json.dumps(context, ensure_ascii=False)
    if isinstance(context, list):
        parts = []
        for item in context:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                found = ""
                for k in ("text", "content", "page_content", "chunk", "body"):
                    if isinstance(item.get(k), str):
                        found = item[k]
                        break
                if found:
                    parts.append(found)
                else:
                    parts.append(json.dumps(item, ensure_ascii=False))
            else:
                parts.append(str(item))
        return "\n\n".join(parts)
    return str(context)


def _get_context(inputs: dict) -> str:
    return _context_to_text(inputs.get("context"))


def _get_unsupported(inputs: dict) -> list[str]:
    raw = inputs.get("unsupported_sentences", [])
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    if isinstance(raw, str) and raw.strip():
        return [raw.strip()]
    return []


def _get_answer(inputs: dict) -> str:
    val = inputs.get("answer", "")
    return val if isinstance(val, str) else str(val)


def _get_corrected(out: Optional[dict]) -> Optional[str]:
    if not isinstance(out, dict):
        return None
    val = out.get("corrected_answer")
    return val if isinstance(val, str) else None


def _get_gold_corrected(ref: Optional[dict]) -> str:
    if not isinstance(ref, dict):
        return ""
    val = ref.get("corrected_answer", "")
    return val if isinstance(val, str) else str(val)


def _sentence_split(text: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if not cleaned:
        return []
    # Keep simple for eval; avoids dependency on NLP libraries.
    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    return [p.strip() for p in parts if p.strip()]


def _extract_specific_facts(text: str) -> set[str]:
    found = set()
    for p in SPECIFIC_FACT_PATTERNS:
        for m in re.findall(p, text or ""):
            item = str(m).strip()
            if len(item) < 2:
                continue
            # Avoid treating sentence-start common educational words as new facts.
            if item.lower() in {"the", "for", "in", "this", "general", "knowledge"}:
                continue
            found.add(_norm(item))
    return found


def _extract_formula_like(text: str) -> set[str]:
    patterns = [
        r"\b[A-Za-z][A-Za-z0-9]*\s*=\s*[^,\n.;]+",
        r"\bP\s*\([^)]*\)\s*=\s*[^,\n.;]+",
        r"\b[A-Za-z]\s*[∩∪]\s*[A-Za-z]\b",
        r"\b\d+\s*[A-Za-zΩ°]+\b",
        r"\b[a-zA-Z]\^?\d+\b",
        r"\b[0-9]+/[0-9]+\b",
    ]
    found = set()
    for p in patterns:
        for m in re.findall(p, text or ""):
            found.add(_norm(m))
    return found


def _phrase_present_or_nearly_present(phrase: str, text: str, threshold: float = 0.65) -> bool:
    p = _norm(phrase)
    t = _norm(text)
    if not p:
        return False
    if p in t:
        return True
    # Sentence-level near match.
    for sent in _sentence_split(text):
        if _jaccard(p, sent) >= threshold:
            return True
    return False


def _unsupported_softened_or_labeled(unsupported: str, corrected: str) -> bool:
    """
    Acceptable outcomes:
    - unsupported sentence removed
    - materially softened
    - explicitly labeled General knowledge:
    """
    u_norm = _norm(unsupported)
    c_norm = _norm(corrected)
    if not u_norm:
        return True

    if not _phrase_present_or_nearly_present(unsupported, corrected):
        return True

    # If retained, it must be clearly labeled or softened.
    if GENERAL_KNOWLEDGE_LABEL in c_norm:
        return True

    softened_markers = {
        "may", "might", "can", "could", "in some cases", "not directly stated",
        "not shown in the context", "not supported by the provided context",
        "the context does not state",
    }
    if _contains_any(corrected, softened_markers):
        return True

    return False


def parse_model_response_to_outputs(raw_text: str) -> dict:
    """
    Defensive parser for target functions that receive raw model text.
    If the response is not JSON, wrap it as:
        {"corrected_answer": raw_text}
    """
    if not isinstance(raw_text, str):
        return {}

    text = raw_text.strip()
    if not text:
        return {"corrected_answer": ""}

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

    return {"corrected_answer": text}


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

    corrected = out.get("corrected_answer")
    if not isinstance(corrected, str):
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"corrected_answer must be string, got {type(corrected).__name__}",
        }

    if not corrected.strip():
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": "corrected_answer is empty",
        }

    return {
        "key": "schema_validity",
        "score": 1.0,
        "comment": "schema valid",
    }


# ---------------------------------------------------------------------------
# Evaluator 2: unsupported_removed_or_labeled
# ---------------------------------------------------------------------------

def unsupported_removed_or_labeled(run, example) -> dict:
    """
    Core retry-suffix behavior:
    every flagged unsupported sentence must be removed, softened, or labeled.
    """
    out = _safe_get_outputs(run)
    inputs = _safe_get_inputs(example)
    corrected = _get_corrected(out)

    if corrected is None:
        return {
            "key": "unsupported_removed_or_labeled",
            "score": 0.0,
            "comment": "corrected_answer missing/non-string",
            "hard_rule_violated": False,
        }

    unsupported = _get_unsupported(inputs)

    # Pass-through examples may have empty unsupported_sentences.
    if not unsupported:
        return {
            "key": "unsupported_removed_or_labeled",
            "score": 1.0,
            "comment": "no unsupported sentences supplied",
            "hard_rule_violated": False,
        }

    failures = []
    for sent in unsupported:
        if not _unsupported_softened_or_labeled(sent, corrected):
            failures.append(sent)

    if failures:
        return {
            "key": "unsupported_removed_or_labeled",
            "score": 0.0,
            "comment": f"unsupported sentence(s) retained without softening/labeling: {failures[:3]}",
            "hard_rule_violated": True,
        }

    return {
        "key": "unsupported_removed_or_labeled",
        "score": 1.0,
        "comment": "all unsupported sentences removed, softened, or labeled",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 3: context_grounding
# ---------------------------------------------------------------------------

def context_grounding(run, example) -> dict:
    """
    Corrected answer should be grounded in provided context or gold correction.
    """
    out = _safe_get_outputs(run)
    ref = _safe_get_reference(example)
    inputs = _safe_get_inputs(example)

    corrected = _get_corrected(out)
    if corrected is None:
        return {
            "key": "context_grounding",
            "score": 0.0,
            "comment": "corrected_answer missing/non-string",
            "hard_rule_violated": False,
        }

    context = _get_context(inputs)
    gold = _get_gold_corrected(ref)

    if not context.strip():
        return {
            "key": "context_grounding",
            "score": 0.5,
            "comment": "context missing/empty; production should normally bypass guard",
            "hard_rule_violated": False,
        }

    # Fake source/page refs must be traceable to context.
    if _regex_any(corrected, CITATION_OR_PAGE_PATTERNS) and not _regex_any(context + "\n" + gold, CITATION_OR_PAGE_PATTERNS):
        return {
            "key": "context_grounding",
            "score": 0.0,
            "comment": "corrected_answer introduced citation/page/source claim not in context/gold",
            "hard_rule_violated": True,
        }

    context_overlap = _jaccard(corrected, context)
    gold_overlap = _jaccard(corrected, gold) if gold else 0.0

    if context_overlap >= MIN_REWRITE_OVERLAP_WITH_CONTEXT or gold_overlap >= MIN_REWRITE_OVERLAP_WITH_GOLD:
        return {
            "key": "context_grounding",
            "score": 1.0,
            "comment": f"grounded; context_overlap={context_overlap:.2f} gold_overlap={gold_overlap:.2f}",
            "hard_rule_violated": False,
        }

    if context_overlap >= 0.10 or gold_overlap >= 0.12:
        return {
            "key": "context_grounding",
            "score": 0.5,
            "comment": f"weak grounding; context_overlap={context_overlap:.2f} gold_overlap={gold_overlap:.2f}",
            "hard_rule_violated": False,
        }

    return {
        "key": "context_grounding",
        "score": 0.0,
        "comment": f"low grounding; context_overlap={context_overlap:.2f} gold_overlap={gold_overlap:.2f}",
        "hard_rule_violated": True,
    }


# ---------------------------------------------------------------------------
# Evaluator 4: no_new_facts
# ---------------------------------------------------------------------------

def no_new_facts(run, example) -> dict:
    """
    Corrected answer must not add new numbers, names, dates, formulas, or
    specific terms beyond context/gold.
    """
    out = _safe_get_outputs(run)
    ref = _safe_get_reference(example)
    inputs = _safe_get_inputs(example)

    corrected = _get_corrected(out)
    if corrected is None:
        return {
            "key": "no_new_facts",
            "score": 0.0,
            "comment": "corrected_answer missing/non-string",
            "hard_rule_violated": False,
        }

    context = _get_context(inputs)
    gold = _get_gold_corrected(ref)
    answer = _get_answer(inputs)

    allowed_text = "\n".join([context, gold, answer])
    allowed_facts = _extract_specific_facts(allowed_text)
    corrected_facts = _extract_specific_facts(corrected)

    new_facts = sorted([f for f in corrected_facts if f not in allowed_facts])

    allowed_formulas = _extract_formula_like(allowed_text)
    corrected_formulas = _extract_formula_like(corrected)
    new_formulas = sorted([
        f for f in corrected_formulas
        if not any(f in af or af in f or _jaccard(f, af) >= 0.30 for af in allowed_formulas)
    ])

    # Avoid over-flagging generic sentence-start terms.
    new_facts = [
        f for f in new_facts
        if f not in {"the", "for", "in", "context", "general knowledge"}
    ]

    if new_formulas:
        return {
            "key": "no_new_facts",
            "score": 0.0,
            "comment": f"new formula-like content introduced: {new_formulas[:3]}",
            "hard_rule_violated": True,
        }

    if len(new_facts) >= 3:
        return {
            "key": "no_new_facts",
            "score": 0.0,
            "comment": f"multiple new specific facts introduced: {new_facts[:8]}",
            "hard_rule_violated": True,
        }

    if new_facts:
        return {
            "key": "no_new_facts",
            "score": 0.5,
            "comment": f"possible new specific fact(s): {new_facts[:5]}",
            "hard_rule_violated": False,
        }

    return {
        "key": "no_new_facts",
        "score": 1.0,
        "comment": "no new specific facts detected",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 5: pass_through_preservation
# ---------------------------------------------------------------------------

def pass_through_preservation(run, example) -> dict:
    """
    Pass cases should preserve grounded content and avoid over-stripping.
    Rewrite cases get a neutral pass here.
    """
    out = _safe_get_outputs(run)
    inputs = _safe_get_inputs(example)
    variation = _safe_get_variation(example)

    corrected = _get_corrected(out)
    if corrected is None:
        return {
            "key": "pass_through_preservation",
            "score": 0.0,
            "comment": "corrected_answer missing/non-string",
        }

    if variation not in PASS_VARIATIONS:
        return {
            "key": "pass_through_preservation",
            "score": 1.0,
            "comment": "not a pass-through variation",
        }

    original = _get_answer(inputs)
    if not original.strip():
        return {
            "key": "pass_through_preservation",
            "score": 0.5,
            "comment": "original answer missing; cannot fully check pass-through preservation",
        }

    overlap = _jaccard(corrected, original)
    corrected_wc = _word_count(corrected)
    original_wc = _word_count(original)

    if corrected_wc < max(8, int(original_wc * 0.45)):
        return {
            "key": "pass_through_preservation",
            "score": 0.0,
            "comment": f"pass-through over-stripped: corrected_words={corrected_wc}, original_words={original_wc}",
        }

    if overlap < MIN_PASS_THROUGH_OVERLAP_WITH_ANSWER:
        return {
            "key": "pass_through_preservation",
            "score": 0.0,
            "comment": f"pass-through answer changed too much; overlap={overlap:.2f}",
        }

    return {
        "key": "pass_through_preservation",
        "score": 1.0,
        "comment": f"pass-through preserved; overlap={overlap:.2f}",
    }


# ---------------------------------------------------------------------------
# Evaluator 6: retry_suffix_compliance
# ---------------------------------------------------------------------------

def retry_suffix_compliance(run, example) -> dict:
    """
    Checks the retry instruction behavior without overfitting to exact wording.
    """
    out = _safe_get_outputs(run)
    inputs = _safe_get_inputs(example)
    variation = _safe_get_variation(example)

    corrected = _get_corrected(out)
    if corrected is None:
        return {
            "key": "retry_suffix_compliance",
            "score": 0.0,
            "comment": "corrected_answer missing/non-string",
            "hard_rule_violated": False,
        }

    issues = []
    hard = False

    if _contains_any(corrected, BANNED_PATTERNS):
        issues.append("contains_banned_ai_language_model_pattern")
        hard = True

    # Avoid exposing internal suffix/process details to students.
    internal_terms = {
        "unsupported sentences detected",
        "strict_retry_suffix",
        "hallucination guard",
        "deterministic overlap",
        "retry suffix",
    }
    if _contains_any(corrected, internal_terms):
        issues.append("leaks_internal_guard_process")
        hard = True

    # General knowledge label is allowed only when variation expects label behavior,
    # or when a retained unsupported claim is explicitly being labeled.
    if GENERAL_KNOWLEDGE_LABEL in _norm(corrected) and variation != "rewrite_label_gk":
        unsupported = _get_unsupported(inputs)
        if not any(_phrase_present_or_nearly_present(s, corrected) for s in unsupported):
            issues.append("unnecessary_general_knowledge_label")

    # Rewrite cases should not just return the original answer unchanged.
    if variation in REWRITE_VARIATIONS:
        original = _get_answer(inputs)
        unsupported = _get_unsupported(inputs)
        if original and _jaccard(corrected, original) > 0.90 and unsupported:
            issues.append("rewrite_case_returned_original_answer")
            hard = True

    if hard:
        return {
            "key": "retry_suffix_compliance",
            "score": 0.0,
            "comment": "; ".join(issues),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "retry_suffix_compliance",
            "score": 0.5,
            "comment": "; ".join(issues),
            "hard_rule_violated": False,
        }

    return {
        "key": "retry_suffix_compliance",
        "score": 1.0,
        "comment": "retry suffix behavior checks passed",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Summary evaluator
# ---------------------------------------------------------------------------

def hallucination_guard_severity_summary(runs: list, examples: list) -> dict:
    """
    BLOCK:
    - schema failure
    - unsupported sentence retained without softening/labeling
    - corrected answer ungrounded in context/gold
    - new formula or multiple new facts
    - internal guard process leaked

    REVIEW:
    - weak grounding
    - possible single new fact
    - pass-through over-edit rate
    """
    if len(runs) != len(examples):
        return {
            "key": "hallucination_guard_severity_summary",
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

        unsupported = unsupported_removed_or_labeled(run, example)
        grounding = context_grounding(run, example)
        facts = no_new_facts(run, example)
        preserve = pass_through_preservation(run, example)
        suffix = retry_suffix_compliance(run, example)

        for result in (unsupported, grounding, facts, suffix):
            if result.get("hard_rule_violated"):
                tier_0.append({
                    "example_id": getattr(example, "id", None),
                    "reason": f"{result['key']} hard failure: {result['comment']}",
                })

        # Pass-through over-stripping is blocking because it can degrade correct answers.
        if variation in PASS_VARIATIONS and preserve["score"] == 0.0:
            tier_0.append({
                "example_id": getattr(example, "id", None),
                "reason": f"pass-through preservation failed: {preserve['comment']}",
            })

        tier_1_applicable += 5
        if unsupported["score"] < 1.0:
            tier_1 += 1
        if grounding["score"] < 1.0:
            tier_1 += 1
        if facts["score"] < 1.0:
            tier_1 += 1
        if preserve["score"] < 1.0:
            tier_1 += 1
        if suffix["score"] < 1.0:
            tier_1 += 1

        if (
            unsupported["score"] == 1.0
            and grounding["score"] == 1.0
            and facts["score"] == 1.0
            and preserve["score"] == 1.0
            and suffix["score"] == 1.0
        ):
            variation_passes[variation] = variation_passes.get(variation, 0) + 1

    tier_1_rate = (tier_1 / tier_1_applicable) if tier_1_applicable else 0.0

    per_variation_pass_rate = {
        v: round(variation_passes.get(v, 0) / total, 3)
        for v, total in variation_totals.items()
    }

    if tier_0:
        recommendation = "BLOCK"
    elif tier_1_rate > 0.15:
        recommendation = "REVIEW"
    else:
        recommendation = "OK"

    return {
        "key": "hallucination_guard_severity_summary",
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
    unsupported_removed_or_labeled,
    context_grounding,
    no_new_facts,
    pass_through_preservation,
    retry_suffix_compliance,
]

SUMMARY_EVALUATORS = [
    hallucination_guard_severity_summary,
]
