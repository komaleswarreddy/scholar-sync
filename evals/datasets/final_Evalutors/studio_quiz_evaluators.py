"""
studio_quiz_evaluators.py

LangSmith custom evaluators for Agent 11: Studio Quiz Generator.

Agent role:
- Generates a JSON quiz from retrieved source excerpts.
- Production pairs the shared Studio system prompt (#10) with the quiz task prompt.
- Custom instructions override default question count and difficulty.

Production dependencies:
- Inputs:
    context: str
    custom_instructions: str
- Output:
    quiz_json: {
        "title": str,
        "questions": [
            {
                "question": str,
                "options": list[str],
                "correct_answer": str,
                "explanation": str
            }
        ]
    }
- Depends on retrieved Studio context. Studio retrieval may use Query Rewriter (#2)
  upstream, and the prompt is wrapped by Studio System JSON (#10), but this
  evaluator should only require context + custom_instructions.

Design choice:
- Code-first, not LLM/hybrid.
- Criticality: Tier 2, student-facing Studio output.
- The major failures are deterministic:
  schema, question count, option count, correct_answer in options, duplicate
  distractors, placeholder options, custom override compliance, no-source behavior,
  grounding, and multi-source coverage.
- Avoid an LLM judge here to prevent overfitting/cost. Deeper answer semantics are
  already judged in Agent 7; Studio quiz structure can be measured cheaply.

LangSmith usage:
    from studio_quiz_evaluators import PER_EXAMPLE_EVALUATORS, SUMMARY_EVALUATORS

    client.evaluate(
        target_fn,
        data="nbm-prompt-studio_quiz",
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

REQUIRED_KEYS = {"quiz_json"}
ALLOWED_KEYS = {"quiz_json"}

QUIZ_REQUIRED_KEYS = {"title", "questions"}
QUESTION_REQUIRED_KEYS = {"question", "options", "correct_answer", "explanation"}

DEFAULT_MIN_QUESTIONS = 5
DEFAULT_MAX_QUESTIONS = 7

VALID_DIFFICULTIES = {"easy", "medium", "hard"}

PLACEHOLDER_OPTION_PATTERNS = {
    "option a", "option b", "option c", "option d",
    "all of the above", "none of the above", "choose this", "correct answer",
    "dummy", "placeholder", "sample option",
}

NO_SOURCE_VARIATIONS = {"no_source", "empty_context"}
MULTI_SOURCE_VARIATIONS = {"multi_source"}

BANNED_PATTERNS = {
    "as an ai language model",
    "i cannot access",
    "i don't have access",
}

EMPTY_CONTEXT_MARKERS = {
    "", "none", "n/a", "no context", "empty", "not provided",
}

GENERIC_WORDS = {
    "quiz", "questions", "question", "options", "answer", "correct", "explanation",
    "title", "choose", "which", "what", "why", "how", "following", "context",
    "source", "sources", "chapter", "student", "students", "learn", "term",
    "definition", "concept", "formula", "medium", "easy", "hard", "mcq", "mcqs",
    "true", "false", "because", "refers", "describes", "states", "given",
    "above", "below",
}

EASY_CUES = {
    "define", "identify", "recall", "what is", "which of the following",
}

HARD_CUES = {
    "infer", "apply", "analyze", "reason", "best explains", "why would",
    "which conclusion", "predict", "compare",
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
        "it", "as", "by", "from", "source", "context", "excerpt", "quiz",
        "question", "questions", "option", "options", "answer", "explanation",
        "correct", "following", "which", "what",
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


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def _is_empty_context(context: str) -> bool:
    return _norm(context) in EMPTY_CONTEXT_MARKERS or _word_count(context) < 3


def _parse_quiz(value: Any) -> tuple[bool, Optional[dict], str]:
    """
    Accepts already parsed dict or JSON string.
    Rejects markdown fences / trailing prose through json.loads behavior.
    """
    if isinstance(value, dict):
        return True, value, json.dumps(value, ensure_ascii=False)

    if not isinstance(value, str):
        return False, None, str(value)

    raw = value.strip()
    if not raw:
        return False, None, raw
    if "```" in raw:
        return False, None, raw

    try:
        parsed = json.loads(raw)
    except Exception:
        return False, None, raw

    return (True, parsed, raw) if isinstance(parsed, dict) else (False, None, raw)


def _get_quiz(out: Optional[dict]) -> Optional[dict]:
    if not isinstance(out, dict):
        return None
    ok, parsed, _ = _parse_quiz(out.get("quiz_json"))
    return parsed if ok else None


def _get_gold_quiz(ref: Optional[dict]) -> Optional[dict]:
    if not isinstance(ref, dict):
        return None
    ok, parsed, _ = _parse_quiz(ref.get("quiz_json"))
    return parsed if ok else None


def _questions(quiz: Optional[dict]) -> list[dict]:
    if not isinstance(quiz, dict):
        return []
    qs = quiz.get("questions")
    return qs if isinstance(qs, list) else []


def _flatten_quiz_text(quiz: Optional[dict]) -> str:
    if not isinstance(quiz, dict):
        return ""
    try:
        return json.dumps(quiz, ensure_ascii=False)
    except Exception:
        return str(quiz)


def _extract_requested_count(custom: str) -> Optional[int]:
    text = _norm(custom)
    patterns = [
        r"\bexactly\s+(\d+)\b",
        r"\b(\d+)\s*mcq",
        r"\b(\d+)\s*questions?\b",
        r"\bmake\s+(\d+)\b",
        r"\bgenerate\s+(\d+)\b",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return int(m.group(1))
    return None


def _extract_requested_difficulty(custom: str) -> Optional[str]:
    text = _norm(custom)
    for d in VALID_DIFFICULTIES:
        if re.search(rf"\b{d}\b", text):
            return d
    return None


def _extract_focus_terms(custom: str) -> set[str]:
    text = _norm(custom)
    # Terms after focus/on/about only. Avoid broad extraction that overfits.
    terms = set()
    for m in re.findall(r"(?:focus|only|on|about)\s+([a-zA-Z0-9Ωμ°/+=∩∪^²³(). -]{3,80})", custom, flags=re.IGNORECASE):
        segment = re.split(r"[,;—-]|difficulty|medium|easy|hard|\d+\s*mcq", m, flags=re.IGNORECASE)[0]
        for tok in _content_tokens(segment):
            if tok not in GENERIC_WORDS:
                terms.add(tok)
    return terms


def _detect_source_markers(context: str) -> set[str]:
    """
    Supports contexts that include source markers like [source: X], Source 1, File: abc.pdf.
    Falls back to empty set if no explicit markers are present.
    """
    markers = set()
    for p in [
        r"\[source[:\s]+([^\]]+)\]",
        r"\bsource\s*(\d+)\b",
        r"\bfile[:\s]+([A-Za-z0-9_.-]+\.pdf)\b",
        r"\bsource_pdf[:\s]+([A-Za-z0-9_.-]+\.pdf)\b",
    ]:
        for m in re.findall(p, context or "", flags=re.IGNORECASE):
            markers.add(_norm(m))
    return markers


def _specific_terms(text: str) -> set[str]:
    """
    Conservative factual-term extraction for grounding.
    """
    found = set()

    # formulas
    for m in re.findall(r"\b[A-Za-zρΔ][A-Za-z0-9_]*\s*=\s*[^.;,\n]+", text or ""):
        found.add(_norm(m))

    # numbers / values
    for m in re.findall(r"\b\d+(?:\.\d+)?\b", text or ""):
        found.add(_norm(m))

    # symbols
    for m in re.findall(r"[ρΔθΩμ][A-Za-z0-9_/*+^²³·=-]*", text or ""):
        found.add(_norm(m))

    # multi-word capitalized terms
    for m in re.findall(r"\b[A-Z][a-z]+(?:'s)?(?:\s+[A-Z][a-z]+(?:'s)?)+\b", text or ""):
        found.add(_norm(m))

    # content tokens
    for tok in _content_tokens(text or ""):
        if tok not in GENERIC_WORDS and len(tok) > 3:
            found.add(tok)

    return found


def _list_from_mapping(mapping: Optional[dict], key: str) -> list[str]:
    if not isinstance(mapping, dict):
        return []
    val = mapping.get(key)
    if isinstance(val, list):
        return [str(x) for x in val if str(x).strip()]
    return []


def parse_model_response_to_outputs(raw_text: str) -> dict:
    """
    Defensive parser for raw model text.
    Returns {"quiz_json": parsed_or_raw_json_string} when possible, else {}.
    """
    if not isinstance(raw_text, str) or not raw_text.strip():
        return {}

    raw = raw_text.strip()
    if "```" in raw:
        fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if fence:
            raw = fence.group(1).strip()
        else:
            return {}

    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return {"quiz_json": parsed}
    except Exception:
        # Try extracting the first JSON object if prose was added.
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                parsed = json.loads(m.group(0))
                if isinstance(parsed, dict):
                    return {"quiz_json": parsed}
            except Exception:
                pass

    return {}


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

    ok, quiz, raw = _parse_quiz(out.get("quiz_json"))
    if not ok:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"quiz_json is not a valid clean JSON object; sample={raw[:120]!r}",
        }

    quiz_keys = set(quiz.keys())
    missing_quiz = QUIZ_REQUIRED_KEYS - quiz_keys
    if missing_quiz:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"quiz missing required key(s): {sorted(missing_quiz)}",
        }

    if not isinstance(quiz.get("title"), str) or not quiz["title"].strip():
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": "quiz.title must be a non-empty string",
        }

    qs = quiz.get("questions")
    if not isinstance(qs, list):
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": "quiz.questions must be a list",
        }

    # For no-source cases, [] may be acceptable; structure check handles it.
    for idx, q in enumerate(qs):
        if not isinstance(q, dict):
            return {
                "key": "schema_validity",
                "score": 0.0,
                "comment": f"question {idx} is not an object",
            }

        missing_q = QUESTION_REQUIRED_KEYS - set(q.keys())
        if missing_q:
            return {
                "key": "schema_validity",
                "score": 0.0,
                "comment": f"question {idx} missing key(s): {sorted(missing_q)}",
            }

        if not isinstance(q.get("question"), str) or not q["question"].strip():
            return {
                "key": "schema_validity",
                "score": 0.0,
                "comment": f"question {idx}.question must be a non-empty string",
            }

        options = q.get("options")
        if not isinstance(options, list) or not all(isinstance(o, str) and o.strip() for o in options):
            return {
                "key": "schema_validity",
                "score": 0.0,
                "comment": f"question {idx}.options must be a non-empty list of strings",
            }

        if not isinstance(q.get("correct_answer"), str) or not q["correct_answer"].strip():
            return {
                "key": "schema_validity",
                "score": 0.0,
                "comment": f"question {idx}.correct_answer must be a non-empty string",
            }

        if q["correct_answer"] not in options:
            return {
                "key": "schema_validity",
                "score": 0.0,
                "comment": f"question {idx}.correct_answer is not exactly one of options",
            }

        if not isinstance(q.get("explanation"), str) or not q["explanation"].strip():
            return {
                "key": "schema_validity",
                "score": 0.0,
                "comment": f"question {idx}.explanation must be a non-empty string",
            }

    return {
        "key": "schema_validity",
        "score": 1.0,
        "comment": "schema valid",
    }


# ---------------------------------------------------------------------------
# Evaluator 2: question_count_match
# ---------------------------------------------------------------------------

def question_count_match(run, example) -> dict:
    out = _safe_get_outputs(run)
    ref = _safe_get_reference(example)
    inputs = _safe_get_inputs(example)
    variation = _safe_get_variation(example)

    quiz = _get_quiz(out)
    if quiz is None:
        return {
            "key": "question_count_match",
            "score": 0.0,
            "comment": "quiz_json missing/malformed",
            "hard_rule_violated": False,
        }

    qs = _questions(quiz)
    context = str(inputs.get("context", ""))
    custom = str(inputs.get("custom_instructions", ""))
    requested = _extract_requested_count(custom)
    gold_quiz = _get_gold_quiz(ref)
    gold_count = len(_questions(gold_quiz)) if gold_quiz else None

    if variation in NO_SOURCE_VARIATIONS or _is_empty_context(context):
        if len(qs) == 0:
            return {
                "key": "question_count_match",
                "score": 1.0,
                "comment": "no-source case safely returned zero questions",
                "hard_rule_violated": False,
            }
        return {
            "key": "question_count_match",
            "score": 0.0,
            "comment": f"no-source/empty-context case produced {len(qs)} question(s)",
            "hard_rule_violated": True,
        }

    expected = requested if requested is not None else gold_count

    if expected is not None:
        if len(qs) == expected:
            return {
                "key": "question_count_match",
                "score": 1.0,
                "comment": f"question count matched expected={expected}",
                "hard_rule_violated": False,
            }
        return {
            "key": "question_count_match",
            "score": 0.0,
            "comment": f"question count mismatch: expected={expected}, got={len(qs)}",
            "hard_rule_violated": True,
        }

    if DEFAULT_MIN_QUESTIONS <= len(qs) <= DEFAULT_MAX_QUESTIONS:
        return {
            "key": "question_count_match",
            "score": 1.0,
            "comment": f"default question count acceptable: {len(qs)}",
            "hard_rule_violated": False,
        }

    return {
        "key": "question_count_match",
        "score": 0.5,
        "comment": f"question count outside default 5-7 range: {len(qs)}",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 3: options_quality
# ---------------------------------------------------------------------------

def options_quality(run, example) -> dict:
    out = _safe_get_outputs(run)
    inputs = _safe_get_inputs(example)
    variation = _safe_get_variation(example)

    quiz = _get_quiz(out)
    if quiz is None:
        return {
            "key": "options_quality",
            "score": 0.0,
            "comment": "quiz_json missing/malformed",
            "hard_rule_violated": False,
        }

    qs = _questions(quiz)
    context = str(inputs.get("context", ""))

    if variation in NO_SOURCE_VARIATIONS or _is_empty_context(context):
        return {
            "key": "options_quality",
            "score": 1.0 if len(qs) == 0 else 0.0,
            "comment": "no-source case",
            "hard_rule_violated": bool(len(qs) != 0),
        }

    issues = []

    for idx, q in enumerate(qs):
        options = q.get("options", []) if isinstance(q, dict) else []
        if not isinstance(options, list):
            issues.append(f"q{idx}_options_not_list")
            continue

        if not (2 <= len(options) <= 4):
            issues.append(f"q{idx}_option_count_{len(options)}")

        norm_options = [_norm(o) for o in options]
        if len(set(norm_options)) != len(norm_options):
            issues.append(f"q{idx}_duplicate_options")

        if any(o in PLACEHOLDER_OPTION_PATTERNS for o in norm_options):
            issues.append(f"q{idx}_placeholder_option")

        # If source supports enough material, 4 options preferred for MCQ.
        if _word_count(context) >= 25 and len(options) < 4:
            issues.append(f"q{idx}_fewer_than_4_options_with_sufficient_context")

        # Distractors should not be trivially identical/near-identical to correct answer.
        correct = _norm(q.get("correct_answer", ""))
        near_dupes = [o for o in norm_options if o != correct and _jaccard(o, correct) > 0.85]
        if near_dupes:
            issues.append(f"q{idx}_distractor_near_duplicate_of_correct")

    if issues:
        hard = any(
            "duplicate" in x or "placeholder" in x or "not_list" in x or "option_count" in x
            for x in issues
        )
        return {
            "key": "options_quality",
            "score": 0.0 if hard else 0.5,
            "comment": "; ".join(issues[:8]),
            "hard_rule_violated": hard,
        }

    return {
        "key": "options_quality",
        "score": 1.0,
        "comment": "options quality checks passed",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 4: custom_instruction_compliance
# ---------------------------------------------------------------------------

def custom_instruction_compliance(run, example) -> dict:
    """
    Checks only concrete custom instructions: count, difficulty, focus terms, language cue.
    Avoids overfitting to exact wording.
    """
    out = _safe_get_outputs(run)
    inputs = _safe_get_inputs(example)

    quiz = _get_quiz(out)
    if quiz is None:
        return {
            "key": "custom_instruction_compliance",
            "score": 0.0,
            "comment": "quiz_json missing/malformed",
        }

    qs = _questions(quiz)
    custom = str(inputs.get("custom_instructions", ""))
    quiz_text = _flatten_quiz_text(quiz)

    issues = []

    requested_count = _extract_requested_count(custom)
    if requested_count is not None and len(qs) != requested_count:
        issues.append(f"requested_count_{requested_count}_got_{len(qs)}")

    requested_difficulty = _extract_requested_difficulty(custom)
    if requested_difficulty:
        q_text = " ".join(q.get("question", "") for q in qs if isinstance(q, dict))
        if requested_difficulty == "easy":
            # Easy should be mostly recall/identify, not heavily inference-based.
            if _contains_any(q_text, HARD_CUES) and not _contains_any(q_text, EASY_CUES):
                issues.append("easy_requested_but_questions_look_reasoning_heavy")
        elif requested_difficulty == "hard":
            # Hard should not be only ultra-short recall.
            avg_q_words = sum(_word_count(q.get("question", "")) for q in qs if isinstance(q, dict)) / max(1, len(qs))
            if avg_q_words < 4 and not _contains_any(q_text, HARD_CUES):
                issues.append("hard_requested_but_questions_look_too_shallow")
        # Medium is broad; do not overfit.

    focus_terms = _extract_focus_terms(custom)
    if focus_terms:
        missing_focus = [t for t in focus_terms if t not in _tokens(quiz_text)]
        # If most focus terms are missing, fail. One missing term may be wording variance.
        if len(missing_focus) >= max(1, len(focus_terms) // 2 + 1):
            issues.append(f"focus_terms_not_reflected:{missing_focus[:5]}")

    # Language cue: if custom says Hindi allowed, don't require Hindi; if it says
    # "in Hindi", require some Devanagari.
    if re.search(r"\bin\s+hindi\b|हिंदी|हिन्दी", custom, flags=re.IGNORECASE):
        if not re.search(r"[\u0900-\u097F]", quiz_text):
            issues.append("hindi_requested_but_no_devanagari_detected")

    if issues:
        hard = any(x.startswith(("requested_count", "focus_terms", "hindi_requested")) for x in issues)
        return {
            "key": "custom_instruction_compliance",
            "score": 0.0 if hard else 0.5,
            "comment": "; ".join(issues),
        }

    return {
        "key": "custom_instruction_compliance",
        "score": 1.0,
        "comment": "custom instruction checks passed",
    }


# ---------------------------------------------------------------------------
# Evaluator 5: grounding
# ---------------------------------------------------------------------------

def grounding(run, example) -> dict:
    """
    Questions, correct answers, and explanations should be grounded in context/gold.
    This is a conservative code gate.
    """
    out = _safe_get_outputs(run)
    ref = _safe_get_reference(example)
    inputs = _safe_get_inputs(example)
    variation = _safe_get_variation(example)

    quiz = _get_quiz(out)
    if quiz is None:
        return {
            "key": "grounding",
            "score": 0.0,
            "comment": "quiz_json missing/malformed",
            "hard_rule_violated": False,
        }

    context = str(inputs.get("context", ""))
    if variation in NO_SOURCE_VARIATIONS or _is_empty_context(context):
        return {
            "key": "grounding",
            "score": 1.0 if len(_questions(quiz)) == 0 else 0.0,
            "comment": "no-source grounding case",
            "hard_rule_violated": bool(len(_questions(quiz)) != 0),
        }

    gold_quiz = _get_gold_quiz(ref)
    quiz_text = _flatten_quiz_text(quiz)
    gold_text = _flatten_quiz_text(gold_quiz)

    allowed_terms = _specific_terms(context) | _specific_terms(gold_text) | _specific_terms(str(inputs.get("custom_instructions", "")))
    output_terms = _specific_terms(quiz_text)

    unsupported = sorted([
        t for t in output_terms
        if t not in allowed_terms
        and t not in GENERIC_WORDS
        and not any(t in a or a in t for a in allowed_terms if len(a) >= 4)
    ])

    numeric_or_formula_bad = [t for t in unsupported if re.search(r"\d|=|[ρΔθΩμ]", t)]
    if numeric_or_formula_bad:
        return {
            "key": "grounding",
            "score": 0.0,
            "comment": f"unsupported numeric/formula/symbol content: {numeric_or_formula_bad[:5]}",
            "hard_rule_violated": True,
        }

    overlap_context = _jaccard(quiz_text, context)
    overlap_gold = _jaccard(quiz_text, gold_text) if gold_text else 0.0

    if len(unsupported) >= 8:
        return {
            "key": "grounding",
            "score": 0.0,
            "comment": f"many unsupported terms/facts: {unsupported[:10]}",
            "hard_rule_violated": True,
        }

    if overlap_context >= 0.18 or overlap_gold >= 0.25:
        return {
            "key": "grounding",
            "score": 1.0,
            "comment": f"grounded; context_overlap={overlap_context:.2f} gold_overlap={overlap_gold:.2f}",
            "hard_rule_violated": False,
        }

    if unsupported:
        return {
            "key": "grounding",
            "score": 0.5,
            "comment": f"possible unsupported terms: {unsupported[:6]}",
            "hard_rule_violated": False,
        }

    return {
        "key": "grounding",
        "score": 1.0,
        "comment": f"grounding acceptable; context_overlap={overlap_context:.2f} gold_overlap={overlap_gold:.2f}",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 6: coverage_and_diversity
# ---------------------------------------------------------------------------

def coverage_and_diversity(run, example) -> dict:
    """
    Checks that quiz is not repetitive and covers scope reasonably.
    """
    out = _safe_get_outputs(run)
    inputs = _safe_get_inputs(example)
    variation = _safe_get_variation(example)

    quiz = _get_quiz(out)
    if quiz is None:
        return {
            "key": "coverage_and_diversity",
            "score": 0.0,
            "comment": "quiz_json missing/malformed",
        }

    qs = _questions(quiz)
    context = str(inputs.get("context", ""))

    if variation in NO_SOURCE_VARIATIONS or _is_empty_context(context):
        return {
            "key": "coverage_and_diversity",
            "score": 1.0 if len(qs) == 0 else 0.0,
            "comment": "no-source case",
        }

    if len(qs) <= 1:
        return {
            "key": "coverage_and_diversity",
            "score": 1.0,
            "comment": "single-question quiz; diversity not applicable",
        }

    question_texts = [q.get("question", "") for q in qs if isinstance(q, dict)]
    duplicate_pairs = []
    for i in range(len(question_texts)):
        for j in range(i + 1, len(question_texts)):
            if _jaccard(question_texts[i], question_texts[j]) >= 0.75:
                duplicate_pairs.append((i, j))

    if duplicate_pairs:
        return {
            "key": "coverage_and_diversity",
            "score": 0.0,
            "comment": f"near-duplicate questions detected: {duplicate_pairs[:5]}",
        }

    # Multi-source: if explicit source markers exist, quiz should mention concepts from
    # more than one source. Do not require "Source 1" labels in the question.
    if variation in MULTI_SOURCE_VARIATIONS:
        source_markers = _detect_source_markers(context)
        if len(source_markers) >= 2:
            # Simple proxy: split context around source markers and ensure at least 2 parts
            # have token overlap with quiz.
            chunks = re.split(r"\[source[:\s]+[^\]]+\]|\bsource\s*\d+\b|\bfile[:\s]+[A-Za-z0-9_.-]+\.pdf", context, flags=re.IGNORECASE)
            covered = 0
            quiz_text = _flatten_quiz_text(quiz)
            for ch in chunks:
                if _word_count(ch) >= 5 and _jaccard(quiz_text, ch) >= 0.08:
                    covered += 1
            if covered < 2:
                return {
                    "key": "coverage_and_diversity",
                    "score": 0.5,
                    "comment": "multi-source context detected but quiz appears concentrated in one source",
                }

    return {
        "key": "coverage_and_diversity",
        "score": 1.0,
        "comment": "coverage/diversity checks passed",
    }


# ---------------------------------------------------------------------------
# Summary evaluator
# ---------------------------------------------------------------------------

def studio_quiz_severity_summary(runs: list, examples: list) -> dict:
    """
    BLOCK:
    - invalid schema
    - wrong question count when custom count/gold count exists
    - no-source hallucination
    - correct_answer not in options
    - duplicate/placeholder options
    - unsupported numeric/formula facts

    REVIEW:
    - weak difficulty/focus compliance
    - possible grounding weakness
    - coverage/diversity weakness
    """
    if len(runs) != len(examples):
        return {
            "key": "studio_quiz_severity_summary",
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

        count = question_count_match(run, example)
        options = options_quality(run, example)
        custom = custom_instruction_compliance(run, example)
        ground = grounding(run, example)
        coverage = coverage_and_diversity(run, example)

        for result in (count, options, ground):
            if result.get("hard_rule_violated"):
                tier_0.append({
                    "example_id": getattr(example, "id", None),
                    "reason": f"{result['key']} hard failure: {result['comment']}",
                })

        # Custom count/focus mismatch can be blocking if score=0.
        if custom["score"] == 0.0 and any(x in custom["comment"] for x in ["requested_count", "focus_terms", "hindi_requested"]):
            tier_0.append({
                "example_id": getattr(example, "id", None),
                "reason": f"custom instruction hard failure: {custom['comment']}",
            })

        tier_1_applicable += 5
        if count["score"] < 1.0:
            tier_1 += 1
        if options["score"] < 1.0:
            tier_1 += 1
        if custom["score"] < 1.0:
            tier_1 += 1
        if ground["score"] < 1.0:
            tier_1 += 1
        if coverage["score"] < 1.0:
            tier_1 += 1

        if (
            count["score"] == 1.0
            and options["score"] == 1.0
            and custom["score"] == 1.0
            and ground["score"] == 1.0
            and coverage["score"] == 1.0
        ):
            variation_passes[variation] = variation_passes.get(variation, 0) + 1

    tier_1_rate = (tier_1 / tier_1_applicable) if tier_1_applicable else 0.0

    per_variation_pass_rate = {
        v: round(variation_passes.get(v, 0) / total, 3)
        for v, total in variation_totals.items()
    }

    if tier_0:
        recommendation = "BLOCK"
    elif tier_1_rate > 0.18:
        recommendation = "REVIEW"
    else:
        recommendation = "OK"

    return {
        "key": "studio_quiz_severity_summary",
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
    question_count_match,
    options_quality,
    custom_instruction_compliance,
    grounding,
    coverage_and_diversity,
]

SUMMARY_EVALUATORS = [
    studio_quiz_severity_summary,
]
