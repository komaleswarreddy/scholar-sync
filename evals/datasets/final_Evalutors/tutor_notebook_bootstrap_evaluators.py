"""
tutor_notebook_bootstrap_evaluators.py

LangSmith custom evaluators for Agent 23: Tutor Notebook Bootstrap.

Agent role:
- Generates the first-open Tutor Notebook payload.
- Opens a chapter/concept tutoring session with:
  1) NCERT-grounded opening Markdown summary,
  2) exactly four specific suggestion chips,
  3) ranked Studio recommendations across all four Studio tools,
     with exactly two `auto_generate=true`.

Production dependencies:
- Inputs:
    class_num: int | str
    subject_label: str
    chapter_no: int | str
    chapter_title: str
    ncert_context: str
    concept: str
- Output:
    bootstrap_json: {
      "opening_summary": str,
      "suggestions": [
        {"label": str, "prompt": str}
      ],
      "studio_recommendations": [
        {"type": "flashcards"|"quiz"|"mind_map"|"slide_deck",
         "reason": str,
         "auto_generate": bool}
      ]
    }

Dependency note:
- Agent 23 is independent at API level.
- It depends on NCERT retrieval context, not on another eval agent.
- Agent 24 later depends on this tutor session context.

Evaluator design:
- Hybrid by default, but lighter than Problem Solver Tier 1 coaches.
- Code gates verify schema, exact opening structure, four unique chips, studio
  recommendation contract, basic grounding, and variation/subject cues.
- Required LLM judge verifies semantic grounding, subject-aware Studio ranking,
  and whether the bootstrap is useful as an opening tutor notebook payload.
- Tier 2: student-facing and onboarding-critical, but not a problem-answer solver.

LangSmith usage:
    from tutor_notebook_bootstrap_evaluators import (
        build_per_example_evaluators,
        SUMMARY_EVALUATORS,
    )

    evaluators = build_per_example_evaluators(judge_llm)

Judge callable:
    judge_llm(prompt: str) -> str

Judge must return JSON:
{
  "opening_quality_score": 0.0-1.0,
  "ncert_grounding_score": 0.0-1.0,
  "suggestion_quality_score": 0.0-1.0,
  "studio_ranking_score": 0.0-1.0,
  "format_score": 0.0-1.0,
  "comment": "short reason"
}
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REQUIRED_INPUT_KEYS = {
    "class_num",
    "subject_label",
    "chapter_no",
    "chapter_title",
    "ncert_context",
    "concept",
}

REQUIRED_OUTPUT_KEYS = {"bootstrap_json"}

BOOTSTRAP_REQUIRED_KEYS = {
    "opening_summary",
    "suggestions",
    "studio_recommendations",
}

VALID_STUDIO_TYPES = {"flashcards", "quiz", "mind_map", "slide_deck"}

OPENING_REQUIRED_MARKERS = [
    "## Summary",
    "### Key topics",
    "### Exam highlights",
    "### Ask me for full clarity",
    "Tap a suggestion below or ask your own question.",
]

BANNED_PATTERNS = {
    "as an ai language model",
    "i cannot access",
    "i don't have access",
    "not enough context",
    "placeholder",
    "todo",
    "lorem ipsum",
}

INTERNAL_LEAKS = {
    "bootstrap_json",
    "tutor/notebook_bootstrap.j2",
    "jinja",
    ".j2",
    "system prompt",
    "sanitize",
    "service",
}

GENERIC_SUGGESTION_LABELS = {
    "main topics",
    "key points",
    "summary",
    "learn more",
    "explain",
    "quiz",
    "flashcards",
    "mind map",
    "slide deck",
    "practice",
}

GENERIC_WORDS = {
    "chapter", "class", "ncert", "context", "concept", "summary", "topic",
    "topics", "key", "exam", "highlights", "student", "students", "study",
    "learn", "question", "questions", "suggestion", "suggestions", "studio",
    "quiz", "flashcards", "mind", "map", "slide", "deck", "tool", "revision",
    "practice", "important", "focus", "chapter", "title",
}

VARIATION_CUES = {
    "numerical": {"formula", "value", "solve", "calculate", "equation", "numerical", "unit"},
    "diagram": {"diagram", "ray", "figure", "label", "visual", "draw", "image"},
    "cbse": {"board", "exam", "steps", "marks", "derivation", "short answer"},
    "neet": {"neet", "mcq", "biology", "assertion", "reason", "option"},
    "jee": {"jee", "numerical", "conceptual", "application", "problem-solving"},
    "multi_part": {"link", "connect", "multiple", "relations", "process", "overview"},
    "conceptual": {"why", "concept", "principle", "meaning", "explain"},
    "case_study": {"case", "scenario", "passage", "interpret", "application"},
    "ncert_strict": {"ncert", "textbook", "definition", "standard", "term"},
    "typo": set(),  # robust-to-typo tested mostly through grounding/context alignment.
    "proof": {"prove", "derive", "derivation", "theorem", "show"},
    "conversational": {"ask", "learn", "start", "clarity", "explore"},
}

SUBJECT_STUDIO_PREFERENCES = {
    # These are soft preferences, not strict gold labels.
    "mathematics": {"quiz", "mind_map"},
    "maths": {"quiz", "mind_map"},
    "physics": {"quiz", "mind_map"},
    "chemistry": {"flashcards", "quiz"},
    "biology": {"flashcards", "mind_map"},
}


# ---------------------------------------------------------------------------
# Helpers
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


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9Ωμ°/+=∩∪^²³().-]+", _norm(text)))


def _content_tokens(text: str) -> set[str]:
    stop = {
        "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with",
        "is", "are", "was", "were", "be", "been", "being", "this", "that",
        "it", "as", "by", "from", "class", "chapter", "ncert", "context",
        "summary", "topic", "topics", "exam", "study", "learn",
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


def _parse_bootstrap(value: Any) -> tuple[bool, Optional[dict], str]:
    if isinstance(value, dict):
        return True, value, json.dumps(value, ensure_ascii=False)

    if not isinstance(value, str):
        return False, None, str(value)

    raw = value.strip()
    if not raw or "```" in raw:
        return False, None, raw

    try:
        parsed = json.loads(raw)
    except Exception:
        return False, None, raw

    return (True, parsed, raw) if isinstance(parsed, dict) else (False, None, raw)


def _get_bootstrap(out: Optional[dict]) -> Optional[dict]:
    if not isinstance(out, dict):
        return None
    ok, parsed, _ = _parse_bootstrap(out.get("bootstrap_json"))
    return parsed if ok else None


def _get_gold_bootstrap(ref: Optional[dict]) -> Optional[dict]:
    if not isinstance(ref, dict):
        return None
    ok, parsed, _ = _parse_bootstrap(ref.get("bootstrap_json"))
    return parsed if ok else None


def _flatten_bootstrap_text(bootstrap: Optional[dict]) -> str:
    if not isinstance(bootstrap, dict):
        return ""
    try:
        return json.dumps(bootstrap, ensure_ascii=False)
    except Exception:
        return str(bootstrap)


def _specific_terms(text: str) -> set[str]:
    found = set()

    for m in re.findall(r"\b[A-Za-zρΔ][A-Za-z0-9_]*\s*=\s*[^.;,\n]+", text or ""):
        found.add(_norm(m))

    for m in re.findall(r"\b\d+(?:\.\d+)?\b", text or ""):
        found.add(_norm(m))

    for m in re.findall(r"[ρΔθΩμ][A-Za-z0-9_/*+^²³·=-]*", text or ""):
        found.add(_norm(m))

    for m in re.findall(r"\b[A-Z][a-z]+(?:'s)?(?:\s+[A-Z][a-z]+(?:'s)?)+\b", text or ""):
        found.add(_norm(m))

    for tok in _content_tokens(text or ""):
        if tok not in GENERIC_WORDS and len(tok) > 3:
            found.add(tok)

    return found


def _opening_section_text(opening: str, heading: str) -> str:
    lines = opening.splitlines()
    start = None
    for idx, line in enumerate(lines):
        if line.strip() == heading:
            start = idx + 1
            break
    if start is None:
        return ""

    end = len(lines)
    for idx in range(start, len(lines)):
        if re.match(r"^#{2,3}\s+", lines[idx].strip()):
            end = idx
            break
    return "\n".join(lines[start:end]).strip()


def _count_bullets(text: str) -> int:
    return len(re.findall(r"^\s*[-*]\s+", text or "", flags=re.MULTILINE))


def _count_numbered(text: str) -> int:
    return len(re.findall(r"^\s*\d+[.)]\s+", text or "", flags=re.MULTILINE))


def _json_from_text(text: str) -> Optional[dict]:
    if not isinstance(text, str):
        return None
    raw = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if fence:
        raw = fence.group(1)
    else:
        obj = re.search(r"\{.*\}", raw, re.DOTALL)
        if obj:
            raw = obj.group(0)
    try:
        parsed = json.loads(raw)
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) else None


def _coerce_score(value: Any) -> float:
    try:
        x = float(value)
    except Exception:
        return 0.0
    return max(0.0, min(1.0, x))


def parse_model_response_to_outputs(raw_text: str) -> dict:
    if not isinstance(raw_text, str) or not raw_text.strip():
        return {}

    parsed = _json_from_text(raw_text)
    if isinstance(parsed, dict):
        if "bootstrap_json" in parsed:
            ok, bootstrap, _ = _parse_bootstrap(parsed.get("bootstrap_json"))
            return {"bootstrap_json": bootstrap if ok else parsed.get("bootstrap_json")}
        return {"bootstrap_json": parsed}

    return {}


# ---------------------------------------------------------------------------
# Evaluator 1: schema_validity
# ---------------------------------------------------------------------------

def schema_validity(run, example) -> dict:
    inputs = _safe_get_inputs(example)
    missing_inputs = REQUIRED_INPUT_KEYS - set(inputs.keys())
    if missing_inputs:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"missing input key(s): {sorted(missing_inputs)}",
        }

    out = _safe_get_outputs(run)
    if out is None:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": "outputs missing or not JSON object",
        }

    present = set(out.keys())
    if present != REQUIRED_OUTPUT_KEYS:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"output key mismatch -- missing={sorted(REQUIRED_OUTPUT_KEYS-present)} extra={sorted(present-REQUIRED_OUTPUT_KEYS)}",
        }

    ok, bootstrap, raw = _parse_bootstrap(out.get("bootstrap_json"))
    if not ok:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"bootstrap_json is not clean JSON object; sample={raw[:120]!r}",
        }

    missing = BOOTSTRAP_REQUIRED_KEYS - set(bootstrap.keys())
    extra = set(bootstrap.keys()) - BOOTSTRAP_REQUIRED_KEYS
    if missing or extra:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"bootstrap key mismatch -- missing={sorted(missing)} extra={sorted(extra)}",
        }

    if not isinstance(bootstrap.get("opening_summary"), str) or not bootstrap["opening_summary"].strip():
        return {"key": "schema_validity", "score": 0.0, "comment": "opening_summary must be non-empty string"}

    suggestions = bootstrap.get("suggestions")
    if not isinstance(suggestions, list) or len(suggestions) != 4:
        return {"key": "schema_validity", "score": 0.0, "comment": "suggestions must contain exactly 4 items"}

    for idx, suggestion in enumerate(suggestions):
        if not isinstance(suggestion, dict) or set(suggestion.keys()) != {"label", "prompt"}:
            return {"key": "schema_validity", "score": 0.0, "comment": f"suggestion {idx} must contain label/prompt only"}
        if not isinstance(suggestion.get("label"), str) or not suggestion["label"].strip():
            return {"key": "schema_validity", "score": 0.0, "comment": f"suggestion {idx}.label empty"}
        if not isinstance(suggestion.get("prompt"), str) or not suggestion["prompt"].strip():
            return {"key": "schema_validity", "score": 0.0, "comment": f"suggestion {idx}.prompt empty"}

    recs = bootstrap.get("studio_recommendations")
    if not isinstance(recs, list) or len(recs) != 4:
        return {"key": "schema_validity", "score": 0.0, "comment": "studio_recommendations must contain exactly 4 items"}

    for idx, rec in enumerate(recs):
        if not isinstance(rec, dict) or set(rec.keys()) != {"type", "reason", "auto_generate"}:
            return {"key": "schema_validity", "score": 0.0, "comment": f"studio recommendation {idx} must contain type/reason/auto_generate only"}
        if rec.get("type") not in VALID_STUDIO_TYPES:
            return {"key": "schema_validity", "score": 0.0, "comment": f"invalid studio type at {idx}: {rec.get('type')!r}"}
        if not isinstance(rec.get("reason"), str) or _word_count(rec["reason"]) < 4:
            return {"key": "schema_validity", "score": 0.0, "comment": f"studio recommendation {idx}.reason too thin"}
        if not isinstance(rec.get("auto_generate"), bool):
            return {"key": "schema_validity", "score": 0.0, "comment": f"studio recommendation {idx}.auto_generate must be boolean"}

    text = _flatten_bootstrap_text(bootstrap)
    if _contains_any(text, BANNED_PATTERNS | INTERNAL_LEAKS):
        return {"key": "schema_validity", "score": 0.0, "comment": "bootstrap_json contains banned/internal phrase"}

    return {"key": "schema_validity", "score": 1.0, "comment": "schema valid"}


# ---------------------------------------------------------------------------
# Evaluator 2: opening_structure
# ---------------------------------------------------------------------------

def opening_structure(run, example) -> dict:
    bootstrap = _get_bootstrap(_safe_get_outputs(run))
    if bootstrap is None:
        return {
            "key": "opening_structure",
            "score": 0.0,
            "comment": "bootstrap_json missing/malformed",
            "hard_rule_violated": False,
        }

    opening = bootstrap.get("opening_summary", "")
    issues = []
    hard = False

    for marker in OPENING_REQUIRED_MARKERS:
        if marker not in opening:
            issues.append(f"missing_marker:{marker}")
            hard = True

    key_topics = _opening_section_text(opening, "### Key topics")
    exam_highlights = _opening_section_text(opening, "### Exam highlights")
    clarity = _opening_section_text(opening, "### Ask me for full clarity")

    key_topic_bullets = _count_bullets(key_topics)
    exam_bullets = _count_bullets(exam_highlights)
    numbered = _count_numbered(clarity)

    if not (3 <= key_topic_bullets <= 5):
        issues.append(f"key_topics_bullet_count={key_topic_bullets}_expected_3-5")
    if not (2 <= exam_bullets <= 4):
        issues.append(f"exam_highlights_bullet_count={exam_bullets}_expected_2-4")
    if numbered != 3:
        issues.append(f"ask_me_for_full_clarity_count={numbered}_expected_3")

    # Key topic bullets should use bold key term formatting.
    if key_topic_bullets and len(re.findall(r"^\s*[-*]\s+\*\*[^*]+\*\*", key_topics, flags=re.MULTILINE)) < key_topic_bullets:
        issues.append("not_all_key_topic_bullets_start_with_bold_key_term")

    words = _word_count(opening)
    if words < 140 or words > 330:
        issues.append(f"opening_summary_length_outside_broad_band:{words}_words")

    if hard:
        return {"key": "opening_structure", "score": 0.0, "comment": "; ".join(issues[:10]), "hard_rule_violated": True}
    if issues:
        return {"key": "opening_structure", "score": 0.5, "comment": "; ".join(issues[:10]), "hard_rule_violated": False}

    return {"key": "opening_structure", "score": 1.0, "comment": "opening summary structure passed", "hard_rule_violated": False}


# ---------------------------------------------------------------------------
# Evaluator 3: suggestions_unique
# ---------------------------------------------------------------------------

def suggestions_unique(run, example) -> dict:
    bootstrap = _get_bootstrap(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)

    if bootstrap is None:
        return {"key": "suggestions_unique", "score": 0.0, "comment": "bootstrap_json missing/malformed", "hard_rule_violated": False}

    suggestions = bootstrap.get("suggestions", [])
    if not isinstance(suggestions, list) or len(suggestions) != 4:
        return {"key": "suggestions_unique", "score": 0.0, "comment": "suggestions must contain exactly 4 items", "hard_rule_violated": True}

    labels = [str(s.get("label", "")) for s in suggestions if isinstance(s, dict)]
    prompts = [str(s.get("prompt", "")) for s in suggestions if isinstance(s, dict)]

    issues = []
    hard = False

    if len(set(_norm(l) for l in labels)) != 4:
        issues.append("duplicate_suggestion_labels")
        hard = True
    if len(set(_norm(p) for p in prompts)) != 4:
        issues.append("duplicate_suggestion_prompts")
        hard = True

    for label in labels:
        if len(label) > 28:
            issues.append(f"label_too_long:{label[:32]!r}")
        if _norm(label) in GENERIC_SUGGESTION_LABELS:
            issues.append(f"generic_label:{label!r}")

    chapter = str(inputs.get("chapter_title", ""))
    concept = str(inputs.get("concept", ""))
    scope_terms = _content_tokens(chapter + " " + concept + " " + str(inputs.get("ncert_context", "")))
    prompt_hits = 0
    for prompt in prompts:
        if _content_tokens(prompt) & scope_terms:
            prompt_hits += 1

    if prompt_hits < 3:
        issues.append(f"only_{prompt_hits}_suggestions_are_scope_specific")

    if hard:
        return {"key": "suggestions_unique", "score": 0.0, "comment": "; ".join(issues), "hard_rule_violated": True}
    if issues:
        return {"key": "suggestions_unique", "score": 0.5, "comment": "; ".join(issues), "hard_rule_violated": False}

    return {"key": "suggestions_unique", "score": 1.0, "comment": "suggestion chips unique and scope-specific", "hard_rule_violated": False}


# ---------------------------------------------------------------------------
# Evaluator 4: studio_pair
# ---------------------------------------------------------------------------

def studio_pair(run, example) -> dict:
    bootstrap = _get_bootstrap(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)

    if bootstrap is None:
        return {"key": "studio_pair", "score": 0.0, "comment": "bootstrap_json missing/malformed", "hard_rule_violated": False}

    recs = bootstrap.get("studio_recommendations", [])
    if not isinstance(recs, list) or len(recs) != 4:
        return {"key": "studio_pair", "score": 0.0, "comment": "studio_recommendations must contain exactly 4 items", "hard_rule_violated": True}

    types = [r.get("type") for r in recs if isinstance(r, dict)]
    auto_types = [r.get("type") for r in recs if isinstance(r, dict) and r.get("auto_generate") is True]

    issues = []
    hard = False

    if set(types) != VALID_STUDIO_TYPES or len(types) != 4:
        issues.append(f"studio types must be exactly all four tools, got={types}")
        hard = True

    if len(auto_types) != 2:
        issues.append(f"exactly_two_auto_generate_required_got={len(auto_types)}")
        hard = True

    for rec in recs:
        reason = str(rec.get("reason", "")) if isinstance(rec, dict) else ""
        if _word_count(reason) < 4:
            issues.append(f"thin_reason_for_{rec.get('type') if isinstance(rec, dict) else 'unknown'}")
        if not (_content_tokens(reason) & _content_tokens(str(inputs.get("chapter_title", "")) + " " + str(inputs.get("concept", "")) + " " + str(inputs.get("ncert_context", "")))):
            issues.append(f"reason_may_be_generic_for_{rec.get('type') if isinstance(rec, dict) else 'unknown'}")

    subject = _norm(inputs.get("subject_label", ""))
    preferred = SUBJECT_STUDIO_PREFERENCES.get(subject, set())
    if preferred and not (set(auto_types) & preferred):
        issues.append(f"auto_generate_pair_may_not_be_subject_aware:auto={auto_types},preferred~={sorted(preferred)}")

    if hard:
        return {"key": "studio_pair", "score": 0.0, "comment": "; ".join(issues[:10]), "hard_rule_violated": True}
    if issues:
        return {"key": "studio_pair", "score": 0.5, "comment": "; ".join(issues[:10]), "hard_rule_violated": False}

    return {"key": "studio_pair", "score": 1.0, "comment": "studio recommendation contract passed", "hard_rule_violated": False}


# ---------------------------------------------------------------------------
# Evaluator 5: ncert_grounding_code
# ---------------------------------------------------------------------------

def ncert_grounding_code(run, example) -> dict:
    bootstrap = _get_bootstrap(_safe_get_outputs(run))
    ref = _safe_get_reference(example)
    inputs = _safe_get_inputs(example)

    if bootstrap is None:
        return {"key": "ncert_grounding_code", "score": 0.0, "comment": "bootstrap_json missing/malformed", "hard_rule_violated": False}

    context = str(inputs.get("ncert_context", ""))
    chapter = str(inputs.get("chapter_title", ""))
    concept = str(inputs.get("concept", ""))
    gold = _get_gold_bootstrap(ref)
    gold_text = _flatten_bootstrap_text(gold)
    text = _flatten_bootstrap_text(bootstrap)
    opening = str(bootstrap.get("opening_summary", ""))

    if _word_count(context) < 5:
        # Thin context: should avoid confident specifics.
        if _word_count(opening) > 180 and not _contains_any(opening, {"known", "explore next", "context is thin", "available context"}):
            return {
                "key": "ncert_grounding_code",
                "score": 0.0,
                "comment": "thin NCERT context but opening summary is over-specific",
                "hard_rule_violated": True,
            }

    allowed = (
        _specific_terms(context)
        | _specific_terms(chapter)
        | _specific_terms(concept)
        | _specific_terms(gold_text)
    )
    produced = _specific_terms(text)

    unsupported = sorted([
        t for t in produced
        if t not in allowed
        and t not in GENERIC_WORDS
        and not any(t in a or a in t for a in allowed if len(a) >= 4)
    ])

    numeric_or_formula_bad = [t for t in unsupported if re.search(r"\d|=|[ρΔθΩμ]", t)]
    if numeric_or_formula_bad:
        return {
            "key": "ncert_grounding_code",
            "score": 0.0,
            "comment": f"unsupported numeric/formula/symbol content: {numeric_or_formula_bad[:5]}",
            "hard_rule_violated": True,
        }

    if len(unsupported) >= 10:
        return {
            "key": "ncert_grounding_code",
            "score": 0.0,
            "comment": f"many unsupported terms/facts: {unsupported[:10]}",
            "hard_rule_violated": True,
        }

    context_overlap = _jaccard(opening, context)
    gold_overlap = _jaccard(text, gold_text) if gold_text else 0.0

    if context_overlap >= 0.14 or gold_overlap >= 0.22:
        return {
            "key": "ncert_grounding_code",
            "score": 1.0,
            "comment": f"grounded; context_overlap={context_overlap:.2f} gold_overlap={gold_overlap:.2f}",
            "hard_rule_violated": False,
        }

    if unsupported:
        return {
            "key": "ncert_grounding_code",
            "score": 0.5,
            "comment": f"possible unsupported terms: {unsupported[:7]}",
            "hard_rule_violated": False,
        }

    return {
        "key": "ncert_grounding_code",
        "score": 1.0,
        "comment": f"grounding acceptable; context_overlap={context_overlap:.2f} gold_overlap={gold_overlap:.2f}",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 6: variation_subject_behavior
# ---------------------------------------------------------------------------

def variation_subject_behavior(run, example) -> dict:
    bootstrap = _get_bootstrap(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)
    variation = _safe_get_variation(example)

    if bootstrap is None:
        return {"key": "variation_subject_behavior", "score": 0.0, "comment": "bootstrap_json missing/malformed"}

    text = _flatten_bootstrap_text(bootstrap)
    opening = str(bootstrap.get("opening_summary", ""))
    issues = []

    cues = VARIATION_CUES.get(variation, set())
    if cues and not _contains_any(text, cues):
        issues.append(f"variation_cue_missing:{variation}")

    subject = _norm(inputs.get("subject_label", ""))
    if subject in {"mathematics", "maths", "physics", "chemistry"}:
        context = str(inputs.get("ncert_context", ""))
        if re.search(r"[=²³^√]|\\frac|\bformula\b|\bderive\b", context + " " + str(inputs.get("chapter_title", "")), flags=re.IGNORECASE):
            if not re.search(r"[=²³^√]|\\frac|\bformula\b|\bderive\b", opening, flags=re.IGNORECASE):
                issues.append("formula_heavy_scope_not_reflected_in_opening")

    if subject == "biology" and variation in {"neet", "conceptual", "ncert_strict"}:
        if not _contains_any(text, {"term", "definition", "process", "classification", "function", "structure"}):
            issues.append("biology_tutor_payload_lacks_term/process_focus")

    if str(inputs.get("concept", "")).strip():
        concept = str(inputs.get("concept", ""))
        if _jaccard(text, concept) < 0.08 and _norm(concept) not in _norm(text):
            issues.append("focus_concept_not_reflected")

    if issues:
        hard = any(x == "focus_concept_not_reflected" for x in issues)
        return {"key": "variation_subject_behavior", "score": 0.0 if hard else 0.5, "comment": "; ".join(issues)}

    return {"key": "variation_subject_behavior", "score": 1.0, "comment": "variation and subject behavior checks passed"}


# ---------------------------------------------------------------------------
# Evaluator 7: required LLM judge
# ---------------------------------------------------------------------------

def make_required_llm_bootstrap_judge(judge_llm: Callable[[str], str]):
    def required_llm_bootstrap_judge(run, example) -> dict:
        bootstrap = _get_bootstrap(_safe_get_outputs(run))
        inputs = _safe_get_inputs(example)
        ref = _safe_get_reference(example)

        if bootstrap is None:
            return {
                "key": "required_llm_bootstrap_judge",
                "score": 0.0,
                "comment": "bootstrap_json missing/malformed",
                "hard_rule_violated": True,
                "judge_available": False,
            }

        gold = _get_gold_bootstrap(ref)
        prompt = f"""
You are evaluating ScholarSync's Tutor Notebook Bootstrap agent.

Evaluate the candidate ONLY against:
- class/subject/chapter/concept scope,
- NCERT context,
- gold/reference bootstrap if provided.

Return ONLY valid JSON:
{{
  "opening_quality_score": <0.0 to 1.0>,
  "ncert_grounding_score": <0.0 to 1.0>,
  "suggestion_quality_score": <0.0 to 1.0>,
  "studio_ranking_score": <0.0 to 1.0>,
  "format_score": <0.0 to 1.0>,
  "comment": "<short reason, max 45 words>"
}}

Scoring guidance:
- opening_quality_score: useful first notebook message with Summary, Key topics, Exam highlights, clarity questions.
- ncert_grounding_score: factual claims trace to NCERT context and chapter/concept scope.
- suggestion_quality_score: four chips are specific, useful, non-duplicate.
- studio_ranking_score: all four Studio tools are present; exactly two auto_generate tools are subject/chapter appropriate.
- format_score: JSON schema, Markdown section structure, no fences/prose.

Inputs:
Class: {inputs.get("class_num", "")}
Subject: {inputs.get("subject_label", "")}
Chapter no: {inputs.get("chapter_no", "")}
Chapter title: {inputs.get("chapter_title", "")}
Concept: {inputs.get("concept", "")}

NCERT context:
{inputs.get("ncert_context", "")}

Gold/reference bootstrap:
{json.dumps(gold, ensure_ascii=False) if gold else ""}

Candidate bootstrap:
{json.dumps(bootstrap, ensure_ascii=False)}
""".strip()

        try:
            raw = judge_llm(prompt)
        except Exception as exc:
            return {
                "key": "required_llm_bootstrap_judge",
                "score": 0.0,
                "comment": f"judge call failed: {exc}",
                "hard_rule_violated": True,
                "judge_available": False,
            }

        parsed = _json_from_text(raw)
        if not parsed:
            return {
                "key": "required_llm_bootstrap_judge",
                "score": 0.0,
                "comment": f"judge returned invalid JSON: {str(raw)[:160]}",
                "hard_rule_violated": True,
                "judge_available": False,
            }

        opening = _coerce_score(parsed.get("opening_quality_score"))
        grounding = _coerce_score(parsed.get("ncert_grounding_score"))
        suggestions = _coerce_score(parsed.get("suggestion_quality_score"))
        studio = _coerce_score(parsed.get("studio_ranking_score"))
        fmt = _coerce_score(parsed.get("format_score"))
        comment = str(parsed.get("comment", "")).strip()

        score = round(
            (0.25 * opening)
            + (0.30 * grounding)
            + (0.18 * suggestions)
            + (0.17 * studio)
            + (0.10 * fmt),
            3,
        )
        hard = grounding < 0.65 or opening < 0.60 or fmt < 0.70

        return {
            "key": "required_llm_bootstrap_judge",
            "score": score,
            "comment": (
                f"opening={opening:.2f} grounding={grounding:.2f} suggestions={suggestions:.2f} "
                f"studio={studio:.2f} format={fmt:.2f} | {comment}"
            ),
            "opening_quality_score": opening,
            "ncert_grounding_score": grounding,
            "suggestion_quality_score": suggestions,
            "studio_ranking_score": studio,
            "format_score": fmt,
            "hard_rule_violated": hard,
            "judge_available": True,
        }

    return required_llm_bootstrap_judge


def build_per_example_evaluators(judge_llm: Callable[[str], str]) -> list[Callable]:
    if judge_llm is None or not callable(judge_llm):
        raise ValueError("Agent 23 evaluation requires judge_llm. Use build_per_example_evaluators(judge_llm).")

    return [
        schema_validity,
        opening_structure,
        suggestions_unique,
        studio_pair,
        ncert_grounding_code,
        variation_subject_behavior,
        make_required_llm_bootstrap_judge(judge_llm),
    ]


# ---------------------------------------------------------------------------
# Summary evaluator
# ---------------------------------------------------------------------------

def tutor_notebook_bootstrap_severity_summary(runs: list, examples: list) -> dict:
    if len(runs) != len(examples):
        return {
            "key": "tutor_notebook_bootstrap_severity_summary",
            "score": 0.0,
            "comment": f"runs/examples length mismatch ({len(runs)} vs {len(examples)})",
            "ship_recommendation": "BLOCK",
        }

    tier_0 = []
    tier_1 = 0
    tier_1_applicable = 0
    variation_totals = {}
    variation_passes = {}

    for run, example in zip(runs, examples):
        variation = _safe_get_variation(example)
        variation_totals[variation] = variation_totals.get(variation, 0) + 1

        schema = schema_validity(run, example)
        if schema["score"] == 0.0:
            tier_0.append({"example_id": getattr(example, "id", None), "reason": f"schema_validity failed: {schema['comment']}"})
            continue

        opening = opening_structure(run, example)
        suggestions = suggestions_unique(run, example)
        studio = studio_pair(run, example)
        grounding = ncert_grounding_code(run, example)
        variation_result = variation_subject_behavior(run, example)
        llm = _extract_required_llm_feedback(run)

        for result in (opening, suggestions, studio, grounding):
            if result.get("hard_rule_violated"):
                tier_0.append({"example_id": getattr(example, "id", None), "reason": f"{result['key']} hard failure: {result['comment']}"})

        if variation_result["score"] == 0.0:
            tier_0.append({"example_id": getattr(example, "id", None), "reason": f"variation_subject_behavior failed: {variation_result['comment']}"})

        if llm is not None:
            if llm.get("hard_rule_violated") or llm.get("score", 0.0) < 0.68:
                tier_0.append({"example_id": getattr(example, "id", None), "reason": f"LLM judge hard failure: {llm.get('comment', '')}"})
            elif llm.get("score", 1.0) < 0.82:
                tier_1 += 1
                tier_1_applicable += 1

        tier_1_applicable += 6
        for result in (opening, suggestions, studio, grounding, variation_result):
            if result["score"] < 1.0:
                tier_1 += 1

        llm_ok = True if llm is None else llm.get("score", 0.0) >= 0.82
        if (
            opening["score"] == 1.0
            and suggestions["score"] == 1.0
            and studio["score"] == 1.0
            and grounding["score"] == 1.0
            and variation_result["score"] == 1.0
            and llm_ok
        ):
            variation_passes[variation] = variation_passes.get(variation, 0) + 1

    tier_1_rate = tier_1 / tier_1_applicable if tier_1_applicable else 0.0
    per_variation = {v: round(variation_passes.get(v, 0) / total, 3) for v, total in variation_totals.items()}

    recommendation = "BLOCK" if tier_0 else ("REVIEW" if tier_1_rate > 0.18 else "OK")

    return {
        "key": "tutor_notebook_bootstrap_severity_summary",
        "score": 0.0 if tier_0 else round(1.0 - tier_1_rate, 3),
        "comment": (
            f"ship_recommendation={recommendation} | "
            f"tier_0_blocking_count={len(tier_0)} | "
            f"tier_1_review_rate={tier_1_rate:.3f} | "
            f"llm_judge_required_via_build_per_example_evaluators=True"
        ),
        "tier_0_blocking_count": len(tier_0),
        "tier_0_blocking_examples": tier_0,
        "tier_1_review_rate": round(tier_1_rate, 3),
        "per_variation_pass_rate": per_variation,
        "ship_recommendation": recommendation,
    }


def _extract_required_llm_feedback(run) -> Optional[dict]:
    for attr in ["feedback", "feedback_stats", "feedback_results", "evaluator_results"]:
        try:
            val = getattr(run, attr, None)
        except Exception:
            continue
        if isinstance(val, dict):
            if val.get("key") == "required_llm_bootstrap_judge":
                return val
            maybe = val.get("required_llm_bootstrap_judge")
            if isinstance(maybe, dict):
                return maybe
            if isinstance(maybe, (int, float)):
                return {
                    "key": "required_llm_bootstrap_judge",
                    "score": float(maybe),
                    "comment": "score extracted from run feedback mapping",
                    "hard_rule_violated": float(maybe) < 0.68,
                }
        if isinstance(val, list):
            for item in val:
                if isinstance(item, dict) and item.get("key") == "required_llm_bootstrap_judge":
                    return item
    return None


# ---------------------------------------------------------------------------
# Public registries
# ---------------------------------------------------------------------------

PER_EXAMPLE_EVALUATORS_CODE_ONLY = [
    schema_validity,
    opening_structure,
    suggestions_unique,
    studio_pair,
    ncert_grounding_code,
    variation_subject_behavior,
]

PER_EXAMPLE_EVALUATORS = None

SUMMARY_EVALUATORS = [tutor_notebook_bootstrap_severity_summary]
