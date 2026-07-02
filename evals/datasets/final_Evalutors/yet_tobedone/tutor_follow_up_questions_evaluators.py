"""
tutor_follow_up_questions_evaluators.py

LangSmith custom evaluators for Agent 24: Tutor Follow-up Questions.

Agent role:
- Runs after a Tutor Notebook chat turn when follow-up suggestions are requested.
- Suggests exactly three next questions for the student.
- The questions must be specific to the latest exchange and give directionality:
  1) clarify/deepen,
  2) apply/practice,
  3) connect/exam-angle.

Production dependencies:
- Inputs:
    user_message: str
    assistant_message: str
    class_num: int | str
    subject_label: str
    chapter_no: int | str
    chapter_title: str
    concept: str
- Output:
    follow_ups: list[str]  # exactly 3, each <= 90 characters

Dependency note:
- Depends on Agent 23 Tutor Notebook session context + latest tutor chat turn.
- It does not directly consume bootstrap_json in the LangSmith dataset, but the
  class/chapter/concept metadata represents the active notebook scope.
- Latest exchange has priority when metadata is imperfect; do not overfit to
  metadata if the exchange clearly discusses a different concept.

Evaluator design:
- Hybrid by default.
- Code gates enforce deterministic contract:
  exact output shape, 3 questions, <=90 chars, no duplicates, question form,
  specificity to latest exchange, role mix, scope alignment, RAG-miss recovery,
  and variation behavior.
- Required LLM judge evaluates usefulness and semantic alignment of the follow-up
  questions. This is Tier 1 because these suggestions steer the next learning path.

LangSmith usage:
    from tutor_follow_up_questions_evaluators import (
        build_per_example_evaluators,
        SUMMARY_EVALUATORS,
    )

    evaluators = build_per_example_evaluators(judge_llm)

Judge callable:
    judge_llm(prompt: str) -> str

Judge must return JSON:
{
  "specificity_score": 0.0-1.0,
  "role_mix_score": 0.0-1.0,
  "scope_alignment_score": 0.0-1.0,
  "student_tone_score": 0.0-1.0,
  "rag_miss_recovery_score": 0.0-1.0,
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
    "user_message",
    "assistant_message",
    "class_num",
    "subject_label",
    "chapter_no",
    "chapter_title",
    "concept",
}

REQUIRED_OUTPUT_KEYS = {"follow_ups"}

MAX_FOLLOWUP_CHARS = 90
MIN_FOLLOWUP_WORDS = 5

GENERIC_FOLLOWUPS = {
    "tell me more",
    "can you explain more",
    "explain more",
    "can you give more details",
    "what else should i know",
    "can you summarize this",
    "can you explain this",
    "give me examples",
    "can you quiz me",
    "what is this",
    "why is it important",
}

BANNED_PATTERNS = {
    "as an ai language model",
    "i cannot access",
    "i don't have access",
    "placeholder",
    "todo",
    "lorem ipsum",
    "follow_up",
    "follow_ups",
    "json",
    "schema",
    "system prompt",
    ".j2",
    "jinja",
}

TEACHER_JARGON = {
    "metacognitive",
    "pedagogical",
    "taxonomy",
    "learning outcome",
    "rubric",
    "curriculum objective",
    "instructional strategy",
    "assessment criterion",
}

CLARIFY_CUES = {
    "why", "how", "explain", "what happens", "what does", "meaning",
    "difference", "role", "concept", "reason", "clarify", "understand",
    "intuition", "why does",
}

APPLY_CUES = {
    "calculate", "solve", "find", "practice", "apply", "use", "try",
    "example", "problem", "derive", "draw", "identify", "predict",
    "what if", "if", "given",
}

EXAM_CUES = {
    "exam", "cbse", "board", "neet", "jee", "marks", "mcq", "option",
    "assertion", "reason", "common mistake", "trick", "shortcut",
    "compare", "connect", "application", "asked", "important",
}

RAG_MISS_CUES = {
    "not found",
    "not in provided sources",
    "not covered",
    "couldn't find",
    "no source",
    "not available in the source",
    "provided sources",
}

RAG_MISS_RECOVERY_CUES = {
    "rephrase",
    "ask about",
    "source",
    "chapter",
    "ncert",
    "related",
    "subtopic",
    "which section",
    "can you check",
    "try asking",
}

VARIATION_CUES = {
    "typo": set(),
    "conversational": {"how", "why", "can", "would", "what"},
    "diagram": {"diagram", "figure", "ray", "draw", "label", "graph", "shown", "visual"},
    "cbse": {"board", "exam", "marks", "steps", "short answer", "long answer"},
    "neet": {"neet", "mcq", "option", "assertion", "reason", "biology"},
    "jee": {"jee", "application", "numerical", "calculate", "conceptual", "problem"},
    "multi_part": {"compare", "connect", "combine", "effect", "change", "case"},
    "conceptual": {"why", "how", "concept", "reason", "intuition", "meaning"},
    "case_study": {"case", "scenario", "apply", "example", "real life", "situation"},
    "ncert_strict": {"ncert", "textbook", "definition", "term", "chapter", "line"},
    "proof": {"prove", "derive", "show", "reasoning", "step"},
    "edge_not_found": RAG_MISS_RECOVERY_CUES,
    "numerical": {"calculate", "solve", "find", "value", "given", "formula"},
}

GENERIC_WORDS = {
    "question", "questions", "follow", "ups", "student", "students", "topic",
    "chapter", "class", "subject", "concept", "explain", "learn", "study",
    "practice", "exam", "ncert", "message", "assistant", "tutor",
}

SCIENCE_MATH_SYMBOLS = r"[ΩμρΔθ°=^²³√]|\\frac|\d+\s*(?:V|A|Ω|m/s|mol|cm|kg|J|N|pm|eV|K|T)"


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
    return set(re.findall(r"[a-zA-Z0-9ΩμρΔθ°/+=∩∪^²³().-]+", _norm(text)))


def _content_tokens(text: str) -> set[str]:
    stop = {
        "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with",
        "is", "are", "was", "were", "be", "been", "being", "this", "that",
        "it", "as", "by", "from", "can", "you", "your", "me", "my", "we",
        "what", "why", "how", "does", "do", "did", "would", "could", "should",
        "question", "answer", "student", "tutor", "assistant",
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


def _parse_followups(value: Any) -> tuple[bool, Optional[list[str]], str]:
    if isinstance(value, list):
        if all(isinstance(x, str) for x in value):
            return True, value, json.dumps(value, ensure_ascii=False)
        return False, None, str(value)

    if not isinstance(value, str):
        return False, None, str(value)

    raw = value.strip()
    if not raw or "```" in raw:
        return False, None, raw

    try:
        parsed = json.loads(raw)
    except Exception:
        return False, None, raw

    if isinstance(parsed, list) and all(isinstance(x, str) for x in parsed):
        return True, parsed, raw

    if isinstance(parsed, dict) and isinstance(parsed.get("follow_ups"), list):
        items = parsed.get("follow_ups")
        if all(isinstance(x, str) for x in items):
            return True, items, raw

    return False, None, raw


def _get_followups(out: Optional[dict]) -> Optional[list[str]]:
    if not isinstance(out, dict):
        return None
    ok, followups, _ = _parse_followups(out.get("follow_ups"))
    return followups if ok else None


def _get_gold_followups(ref: Optional[dict]) -> list[str]:
    if not isinstance(ref, dict):
        return []
    ok, followups, _ = _parse_followups(ref.get("follow_ups"))
    return followups if ok else []


def _all_followup_text(followups: Optional[list[str]]) -> str:
    if not isinstance(followups, list):
        return ""
    return " ".join(str(x) for x in followups)


def _is_question(text: str) -> bool:
    t = text.strip()
    if t.endswith("?"):
        return True
    return bool(re.match(r"^(what|why|how|can|could|would|which|when|where|do|does|did|is|are|should)\b", t, flags=re.IGNORECASE))


def _role_for_question(q: str) -> set[str]:
    roles = set()
    if _contains_any(q, CLARIFY_CUES):
        roles.add("clarify")
    if _contains_any(q, APPLY_CUES):
        roles.add("apply")
    if _contains_any(q, EXAM_CUES):
        roles.add("exam")
    return roles


def _exchange_scope_text(inputs: dict) -> str:
    return " ".join([
        str(inputs.get("user_message", "")),
        str(inputs.get("assistant_message", "")),
    ])


def _metadata_scope_text(inputs: dict) -> str:
    return " ".join([
        str(inputs.get("subject_label", "")),
        str(inputs.get("chapter_title", "")),
        str(inputs.get("concept", "")),
    ])


def _is_rag_miss(assistant_message: str) -> bool:
    return _contains_any(assistant_message, RAG_MISS_CUES)


def _nearly_repeats_user_question(q: str, user_message: str) -> bool:
    q_norm = _norm(q).rstrip("?")
    user_norm = _norm(user_message).rstrip("?")
    if not q_norm or not user_norm:
        return False
    if q_norm == user_norm:
        return True
    return _jaccard(q, user_message) >= 0.82 and abs(_word_count(q) - _word_count(user_message)) <= 5


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
    """
    Defensive parser for raw model response.
    Accepts either:
    - {"follow_ups": ["...", "...", "..."]}
    - a raw JSON array ["...", "...", "..."]
    """
    if not isinstance(raw_text, str) or not raw_text.strip():
        return {}

    raw = raw_text.strip()

    fence = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw, re.DOTALL)
    if fence:
        raw = fence.group(1).strip()

    try:
        parsed = json.loads(raw)
    except Exception:
        obj = re.search(r"\{.*\}", raw, re.DOTALL)
        if not obj:
            return {}
        try:
            parsed = json.loads(obj.group(0))
        except Exception:
            return {}

    if isinstance(parsed, dict) and isinstance(parsed.get("follow_ups"), list):
        return {"follow_ups": parsed["follow_ups"]}

    if isinstance(parsed, list):
        return {"follow_ups": parsed}

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

    ok, followups, raw = _parse_followups(out.get("follow_ups"))
    if not ok:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"follow_ups must be a clean list of strings; sample={raw[:120]!r}",
        }

    if len(followups) != 3:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"follow_ups must contain exactly 3 questions, got {len(followups)}",
        }

    for idx, q in enumerate(followups):
        if not isinstance(q, str) or not q.strip():
            return {
                "key": "schema_validity",
                "score": 0.0,
                "comment": f"follow_up {idx} must be non-empty string",
            }
        if len(q) > MAX_FOLLOWUP_CHARS:
            return {
                "key": "schema_validity",
                "score": 0.0,
                "comment": f"follow_up {idx} exceeds {MAX_FOLLOWUP_CHARS} chars: {len(q)}",
            }
        if _word_count(q) < MIN_FOLLOWUP_WORDS:
            return {
                "key": "schema_validity",
                "score": 0.5,
                "comment": f"follow_up {idx} may be too thin: {_word_count(q)} words",
            }
        if not _is_question(q):
            return {
                "key": "schema_validity",
                "score": 0.0,
                "comment": f"follow_up {idx} is not phrased as a question",
            }

    text = _all_followup_text(followups)
    if _contains_any(text, BANNED_PATTERNS):
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": "follow_ups contain banned/internal phrase",
        }

    return {"key": "schema_validity", "score": 1.0, "comment": "schema valid"}


# ---------------------------------------------------------------------------
# Evaluator 2: three_follow_ups
# ---------------------------------------------------------------------------

def three_follow_ups(run, example) -> dict:
    followups = _get_followups(_safe_get_outputs(run))
    if followups is None:
        return {
            "key": "three_follow_ups",
            "score": 0.0,
            "comment": "follow_ups missing/malformed",
            "hard_rule_violated": False,
        }

    issues = []
    hard = False

    if len(followups) != 3:
        issues.append(f"expected_3_followups_got_{len(followups)}")
        hard = True

    normalized = [_norm(q).rstrip("?") for q in followups]
    if len(set(normalized)) != len(normalized):
        issues.append("duplicate_followup_questions")
        hard = True

    for idx, q in enumerate(followups):
        if len(q) > MAX_FOLLOWUP_CHARS:
            issues.append(f"q{idx}_too_long:{len(q)}")
            hard = True
        if not _is_question(q):
            issues.append(f"q{idx}_not_question_form")
            hard = True
        if _contains_any(q, TEACHER_JARGON):
            issues.append(f"q{idx}_teacher_jargon")
        if _norm(q).rstrip("?") in GENERIC_FOLLOWUPS:
            issues.append(f"q{idx}_generic_question")
            hard = True

    if hard:
        return {
            "key": "three_follow_ups",
            "score": 0.0,
            "comment": "; ".join(issues),
            "hard_rule_violated": True,
        }
    if issues:
        return {
            "key": "three_follow_ups",
            "score": 0.5,
            "comment": "; ".join(issues),
            "hard_rule_violated": False,
        }

    return {
        "key": "three_follow_ups",
        "score": 1.0,
        "comment": "exactly three unique <=90-char questions",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 3: specificity
# ---------------------------------------------------------------------------

def specificity(run, example) -> dict:
    followups = _get_followups(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)

    if followups is None:
        return {
            "key": "specificity",
            "score": 0.0,
            "comment": "follow_ups missing/malformed",
            "hard_rule_violated": False,
        }

    user = str(inputs.get("user_message", ""))
    assistant = str(inputs.get("assistant_message", ""))
    exchange = _exchange_scope_text(inputs)
    metadata = _metadata_scope_text(inputs)
    full_scope = " ".join([exchange, metadata])

    issues = []
    hard = False

    for idx, q in enumerate(followups):
        if _nearly_repeats_user_question(q, user):
            issues.append(f"q{idx}_repeats_user_question")
            hard = True

        exchange_overlap = _jaccard(q, exchange)
        metadata_overlap = _jaccard(q, metadata)
        full_overlap = _jaccard(q, full_scope)

        # Latest exchange has priority; metadata can be imperfect. Passing either
        # exchange or active notebook metadata is acceptable.
        if max(exchange_overlap, metadata_overlap, full_overlap) < 0.06:
            issues.append(
                f"q{idx}_weak_specificity:exchange={exchange_overlap:.2f},metadata={metadata_overlap:.2f}"
            )

        # Avoid generic "follow-up template" questions even if one word overlaps.
        if _norm(q).rstrip("?") in GENERIC_FOLLOWUPS:
            issues.append(f"q{idx}_generic_template")
            hard = True

    # At least two of three should tie to the last exchange, not just broad metadata.
    exchange_specific_count = sum(1 for q in followups if _jaccard(q, exchange) >= 0.06)
    if exchange_specific_count < 2 and not _is_rag_miss(assistant):
        issues.append(f"only_{exchange_specific_count}_questions_specific_to_latest_exchange")

    if hard:
        return {
            "key": "specificity",
            "score": 0.0,
            "comment": "; ".join(issues[:8]),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "specificity",
            "score": 0.5,
            "comment": "; ".join(issues[:8]),
            "hard_rule_violated": False,
        }

    return {
        "key": "specificity",
        "score": 1.0,
        "comment": "follow-ups are specific and do not repeat the student question",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 4: mix_roles
# ---------------------------------------------------------------------------

def mix_roles(run, example) -> dict:
    followups = _get_followups(_safe_get_outputs(run))
    if followups is None:
        return {
            "key": "mix_roles",
            "score": 0.0,
            "comment": "follow_ups missing/malformed",
            "hard_rule_violated": False,
        }

    role_map = []
    all_roles = set()
    for q in followups:
        roles = _role_for_question(q)
        role_map.append(sorted(roles))
        all_roles |= roles

    missing_roles = {"clarify", "apply", "exam"} - all_roles

    if not missing_roles:
        return {
            "key": "mix_roles",
            "score": 1.0,
            "comment": f"role mix present: {role_map}",
            "hard_rule_violated": False,
        }

    # If two roles are strongly present, mark review not block.
    if len(missing_roles) == 1:
        return {
            "key": "mix_roles",
            "score": 0.5,
            "comment": f"one role missing: {sorted(missing_roles)}; role_map={role_map}",
            "hard_rule_violated": False,
        }

    return {
        "key": "mix_roles",
        "score": 0.0,
        "comment": f"role mix weak; missing={sorted(missing_roles)} role_map={role_map}",
        "hard_rule_violated": True,
    }


# ---------------------------------------------------------------------------
# Evaluator 5: scope_alignment
# ---------------------------------------------------------------------------

def scope_alignment(run, example) -> dict:
    followups = _get_followups(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)
    ref = _safe_get_reference(example)

    if followups is None:
        return {
            "key": "scope_alignment",
            "score": 0.0,
            "comment": "follow_ups missing/malformed",
            "hard_rule_violated": False,
        }

    text = _all_followup_text(followups)
    exchange = _exchange_scope_text(inputs)
    metadata = _metadata_scope_text(inputs)
    gold_text = _all_followup_text(_get_gold_followups(ref))

    exchange_overlap = _jaccard(text, exchange)
    metadata_overlap = _jaccard(text, metadata)
    gold_overlap = _jaccard(text, gold_text) if gold_text else 0.0

    issues = []

    # If metadata and exchange conflict, prefer exchange. This avoids punishing
    # production data where scope metadata can be stale or mismatched.
    meta_exchange_overlap = _jaccard(metadata, exchange)
    metadata_may_conflict = bool(metadata.strip() and exchange.strip() and meta_exchange_overlap < 0.03)

    if max(exchange_overlap, gold_overlap) < 0.08:
        issues.append(
            f"weak_latest_exchange_alignment:exchange={exchange_overlap:.2f},gold={gold_overlap:.2f}"
        )

    if not metadata_may_conflict:
        if metadata.strip() and metadata_overlap < 0.04 and gold_overlap < 0.12:
            issues.append(f"weak_metadata_scope_alignment:metadata={metadata_overlap:.2f}")

    # Concept, when present, should be reflected unless latest exchange clearly
    # moved to a nearby subtopic.
    concept = str(inputs.get("concept", "")).strip()
    if concept:
        concept_overlap = _jaccard(text, concept)
        if concept_overlap < 0.04 and _norm(concept) not in _norm(text) and exchange_overlap < 0.14:
            issues.append("active_concept_not_reflected")

    if issues:
        hard = any(x.startswith("weak_latest_exchange_alignment") for x in issues)
        return {
            "key": "scope_alignment",
            "score": 0.0 if hard else 0.5,
            "comment": "; ".join(issues),
            "hard_rule_violated": hard,
        }

    return {
        "key": "scope_alignment",
        "score": 1.0,
        "comment": (
            f"scope aligned; exchange={exchange_overlap:.2f} "
            f"metadata={metadata_overlap:.2f} gold={gold_overlap:.2f}"
        ),
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 6: rag_miss_and_variation_behavior
# ---------------------------------------------------------------------------

def rag_miss_and_variation_behavior(run, example) -> dict:
    followups = _get_followups(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)
    variation = _safe_get_variation(example)

    if followups is None:
        return {
            "key": "rag_miss_and_variation_behavior",
            "score": 0.0,
            "comment": "follow_ups missing/malformed",
            "hard_rule_violated": False,
        }

    text = _all_followup_text(followups)
    assistant = str(inputs.get("assistant_message", ""))
    user = str(inputs.get("user_message", ""))
    issues = []
    hard = False

    if _is_rag_miss(assistant):
        if not _contains_any(text, RAG_MISS_RECOVERY_CUES):
            issues.append("rag_miss_but_no_rephrase_or_related_source_recovery")
            hard = True

    cues = VARIATION_CUES.get(variation, set())
    if cues and not _contains_any(text, cues):
        issues.append(f"variation_cue_missing:{variation}")

    # Math/numerical exchanges should keep at least one applied question.
    if re.search(SCIENCE_MATH_SYMBOLS, user + " " + assistant) and variation in {"numerical", "jee", "cbse"}:
        if not _contains_any(text, {"calculate", "solve", "find", "value", "formula", "given"}):
            issues.append("math_exchange_but_no_applied_calculation_followup")

    if variation == "diagram" and not _contains_any(text, VARIATION_CUES["diagram"]):
        issues.append("diagram_variation_missing_visual_followup")

    if variation == "proof" and not _contains_any(text, VARIATION_CUES["proof"]):
        issues.append("proof_variation_missing_reasoning_followup")

    if variation == "ncert_strict" and not _contains_any(text, VARIATION_CUES["ncert_strict"]):
        issues.append("ncert_strict_variation_missing_ncert_tie")

    if hard:
        return {
            "key": "rag_miss_and_variation_behavior",
            "score": 0.0,
            "comment": "; ".join(issues[:8]),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "rag_miss_and_variation_behavior",
            "score": 0.5,
            "comment": "; ".join(issues[:8]),
            "hard_rule_violated": False,
        }

    return {
        "key": "rag_miss_and_variation_behavior",
        "score": 1.0,
        "comment": "RAG-miss and variation behavior checks passed",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 7: required LLM judge
# ---------------------------------------------------------------------------

def make_required_llm_followup_questions_judge(judge_llm: Callable[[str], str]):
    def required_llm_followup_questions_judge(run, example) -> dict:
        followups = _get_followups(_safe_get_outputs(run))
        inputs = _safe_get_inputs(example)
        ref = _safe_get_reference(example)

        if followups is None:
            return {
                "key": "required_llm_followup_questions_judge",
                "score": 0.0,
                "comment": "follow_ups missing/malformed",
                "hard_rule_violated": True,
                "judge_available": False,
            }

        gold = _get_gold_followups(ref)
        prompt = f"""
You are evaluating ScholarSync's Tutor Follow-up Questions agent.

Evaluate the candidate ONLY against:
- active tutor scope,
- latest student message,
- latest tutor answer,
- gold/reference follow-ups if provided.

Return ONLY valid JSON:
{{
  "specificity_score": <0.0 to 1.0>,
  "role_mix_score": <0.0 to 1.0>,
  "scope_alignment_score": <0.0 to 1.0>,
  "student_tone_score": <0.0 to 1.0>,
  "rag_miss_recovery_score": <0.0 to 1.0>,
  "comment": "<short reason, max 45 words>"
}}

Scoring guidance:
- specificity_score: questions are tied to the latest exchange, not generic templates.
- role_mix_score: includes clarify/deepen, apply/practice, and exam/connect angle.
- scope_alignment_score: fits class/subject/chapter/concept unless metadata conflicts with latest exchange.
- student_tone_score: natural student-friendly questions, no teacher jargon.
- rag_miss_recovery_score: if tutor said "not found", suggests rephrases/related NCERT subtopics; otherwise give 1.0 if no miss.

Scope:
Class: {inputs.get("class_num", "")}
Subject: {inputs.get("subject_label", "")}
Chapter no: {inputs.get("chapter_no", "")}
Chapter title: {inputs.get("chapter_title", "")}
Concept: {inputs.get("concept", "")}

Latest exchange:
Student: {inputs.get("user_message", "")}
Tutor: {inputs.get("assistant_message", "")}

Gold/reference follow-ups:
{json.dumps(gold, ensure_ascii=False) if gold else ""}

Candidate follow-ups:
{json.dumps(followups, ensure_ascii=False)}
""".strip()

        try:
            raw = judge_llm(prompt)
        except Exception as exc:
            return {
                "key": "required_llm_followup_questions_judge",
                "score": 0.0,
                "comment": f"judge call failed: {exc}",
                "hard_rule_violated": True,
                "judge_available": False,
            }

        parsed = _json_from_text(raw)
        if not parsed:
            return {
                "key": "required_llm_followup_questions_judge",
                "score": 0.0,
                "comment": f"judge returned invalid JSON: {str(raw)[:160]}",
                "hard_rule_violated": True,
                "judge_available": False,
            }

        specificity_score = _coerce_score(parsed.get("specificity_score"))
        role_mix_score = _coerce_score(parsed.get("role_mix_score"))
        scope_score = _coerce_score(parsed.get("scope_alignment_score"))
        tone_score = _coerce_score(parsed.get("student_tone_score"))
        rag_score = _coerce_score(parsed.get("rag_miss_recovery_score"))
        comment = str(parsed.get("comment", "")).strip()

        score = round(
            (0.30 * specificity_score)
            + (0.25 * role_mix_score)
            + (0.20 * scope_score)
            + (0.15 * tone_score)
            + (0.10 * rag_score),
            3,
        )

        hard = specificity_score < 0.65 or role_mix_score < 0.65 or scope_score < 0.55 or rag_score < 0.60

        return {
            "key": "required_llm_followup_questions_judge",
            "score": score,
            "comment": (
                f"specificity={specificity_score:.2f} mix={role_mix_score:.2f} "
                f"scope={scope_score:.2f} tone={tone_score:.2f} rag={rag_score:.2f} | {comment}"
            ),
            "specificity_score": specificity_score,
            "role_mix_score": role_mix_score,
            "scope_alignment_score": scope_score,
            "student_tone_score": tone_score,
            "rag_miss_recovery_score": rag_score,
            "hard_rule_violated": hard,
            "judge_available": True,
        }

    return required_llm_followup_questions_judge


def build_per_example_evaluators(judge_llm: Callable[[str], str]) -> list[Callable]:
    if judge_llm is None or not callable(judge_llm):
        raise ValueError("Agent 24 evaluation requires judge_llm. Use build_per_example_evaluators(judge_llm).")

    return [
        schema_validity,
        three_follow_ups,
        specificity,
        mix_roles,
        scope_alignment,
        rag_miss_and_variation_behavior,
        make_required_llm_followup_questions_judge(judge_llm),
    ]


# ---------------------------------------------------------------------------
# Summary evaluator
# ---------------------------------------------------------------------------

def tutor_follow_up_questions_severity_summary(runs: list, examples: list) -> dict:
    if len(runs) != len(examples):
        return {
            "key": "tutor_follow_up_questions_severity_summary",
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

        count = three_follow_ups(run, example)
        spec = specificity(run, example)
        roles = mix_roles(run, example)
        scope = scope_alignment(run, example)
        behavior = rag_miss_and_variation_behavior(run, example)
        llm = _extract_required_llm_feedback(run)

        for result in (count, spec, roles, scope, behavior):
            if result.get("hard_rule_violated"):
                tier_0.append({"example_id": getattr(example, "id", None), "reason": f"{result['key']} hard failure: {result['comment']}"})

        if llm is not None:
            if llm.get("hard_rule_violated") or llm.get("score", 0.0) < 0.70:
                tier_0.append({"example_id": getattr(example, "id", None), "reason": f"LLM judge hard failure: {llm.get('comment', '')}"})
            elif llm.get("score", 1.0) < 0.84:
                tier_1 += 1
                tier_1_applicable += 1

        tier_1_applicable += 6
        for result in (count, spec, roles, scope, behavior):
            if result["score"] < 1.0:
                tier_1 += 1

        llm_ok = True if llm is None else llm.get("score", 0.0) >= 0.84
        if (
            count["score"] == 1.0
            and spec["score"] == 1.0
            and roles["score"] == 1.0
            and scope["score"] == 1.0
            and behavior["score"] == 1.0
            and llm_ok
        ):
            variation_passes[variation] = variation_passes.get(variation, 0) + 1

    tier_1_rate = tier_1 / tier_1_applicable if tier_1_applicable else 0.0
    per_variation = {v: round(variation_passes.get(v, 0) / total, 3) for v, total in variation_totals.items()}

    recommendation = "BLOCK" if tier_0 else ("REVIEW" if tier_1_rate > 0.15 else "OK")

    return {
        "key": "tutor_follow_up_questions_severity_summary",
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
            if val.get("key") == "required_llm_followup_questions_judge":
                return val
            maybe = val.get("required_llm_followup_questions_judge")
            if isinstance(maybe, dict):
                return maybe
            if isinstance(maybe, (int, float)):
                return {
                    "key": "required_llm_followup_questions_judge",
                    "score": float(maybe),
                    "comment": "score extracted from run feedback mapping",
                    "hard_rule_violated": float(maybe) < 0.70,
                }
        if isinstance(val, list):
            for item in val:
                if isinstance(item, dict) and item.get("key") == "required_llm_followup_questions_judge":
                    return item
    return None


# ---------------------------------------------------------------------------
# Public registries
# ---------------------------------------------------------------------------

PER_EXAMPLE_EVALUATORS_CODE_ONLY = [
    schema_validity,
    three_follow_ups,
    specificity,
    mix_roles,
    scope_alignment,
    rag_miss_and_variation_behavior,
]

PER_EXAMPLE_EVALUATORS = None

SUMMARY_EVALUATORS = [tutor_follow_up_questions_severity_summary]
