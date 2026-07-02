"""
show_missing_idea_evaluators.py

LangSmith custom evaluators for Agent 20: Show Missing Idea Coach.

Agent role:
- One of the mutually exclusive coach modes after Agent 17 Problem DNA Analyzer.
- Reveals the key conceptual unlock, but NOT the full solution by default.
- Helps the student see what they are missing without solving everything.

Production dependencies:
- Required dataset inputs:
    problem_text_normalized: str
    ncert_context: str
- Optional runtime dependency inputs:
    problem_dna: dict
    expert_solution_internal: dict
- Output:
    coach_json: {
      "title": str,
      "sections": [
        {"heading": "The Missing Idea", "bodyMarkdown": "..."},
        {"heading": "Why It Feels Tricky", "bodyMarkdown": "..."},
        {"heading": "Correct Mental Model", "bodyMarkdown": "..."},
        {"heading": "How to Start", "bodyMarkdown": "..."},
        {"heading": "Where Most Students Get Stuck", "bodyMarkdown": "..."}
      ],
      "revealLevel": "partial",
      "followUpButtons": [
        {"label": str, "action": str}
      ]
    }

Hard behavior:
- `finalAnswer` should NOT be present.
- `revealLevel` must be `partial`.
- It may give a starting equation / mental model / first step.
- It must not provide the full numeric answer, final option, full derivation, or complete step-by-step solution.

Evaluator design:
- Hybrid by default.
- Code gates verify schema, five-section completeness, partial reveal, no final
  answer leakage, trap specificity, NCERT/DNA alignment, LaTeX hygiene, and
  variation behavior.
- Required LLM judge verifies semantic quality of the missing idea, whether it is
  the actual unlock, and whether the response avoids full-solution leakage.
- Tier 1 because it is student-facing and depends on Agent 17. Premature answer
  leakage would break the intended guided-learning workflow.

LangSmith usage:
    from show_missing_idea_evaluators import (
        build_per_example_evaluators,
        SUMMARY_EVALUATORS,
    )

    evaluators = build_per_example_evaluators(judge_llm)

Judge callable:
    judge_llm(prompt: str) -> str

Judge must return JSON:
{
  "missing_idea_quality_score": 0.0-1.0,
  "partial_reveal_safety_score": 0.0-1.0,
  "ncert_alignment_score": 0.0-1.0,
  "student_trap_specificity_score": 0.0-1.0,
  "format_compliance_score": 0.0-1.0,
  "comment": "short reason"
}
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Optional


# ---------------------------------------------------------------------------
# Contract constants
# ---------------------------------------------------------------------------

REQUIRED_INPUT_KEYS = {"problem_text_normalized", "ncert_context"}
REQUIRED_OUTPUT_KEYS = {"coach_json"}

REQUIRED_TOP_KEYS = {
    "title",
    "sections",
    "revealLevel",
    "followUpButtons",
}

DISALLOWED_TOP_KEYS = {"finalAnswer"}

REQUIRED_HEADINGS = [
    "The Missing Idea",
    "Why It Feels Tricky",
    "Correct Mental Model",
    "How to Start",
    "Where Most Students Get Stuck",
]

REQUIRED_ACTIONS = {
    "REVEAL_SOLUTION",
    "SHOW_BEST_APPROACH",
    "GIVE_SIMILAR_PROBLEM",
    "EXPLAIN_CONCEPT_AGAIN",
    "START_TUTOR_SESSION",
}

SECTION_MIN_WORDS = {
    "The Missing Idea": 10,
    "Why It Feels Tricky": 10,
    "Correct Mental Model": 12,
    "How to Start": 8,
    "Where Most Students Get Stuck": 10,
}

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
    "expert_solution_internal",
    "problem_dna",
    "coach_json",
    "jinja",
    ".j2",
    "system prompt",
    "guard",
}

FULL_SOLUTION_PHRASES = {
    "final answer is",
    "therefore the answer is",
    "so the answer is",
    "hence the answer is",
    "complete solution",
    "full solution",
    "step-by-step solution",
    "the correct option is",
    "option a is correct",
    "option b is correct",
    "option c is correct",
    "option d is correct",
}

MISSING_IDEA_CUES = {
    "missing idea",
    "key idea",
    "unlock",
    "mental model",
    "look for",
    "notice",
    "recognize",
    "connect",
    "instead of",
    "the trick is",
    "conceptual",
    "principle",
}

TRAP_CUES = {
    "students",
    "get stuck",
    "mistake",
    "trap",
    "confuse",
    "assume",
    "forget",
    "ignore",
    "wrong path",
    "common error",
    "usually",
}

START_CUES = {
    "start",
    "first",
    "write",
    "identify",
    "mark",
    "draw",
    "set up",
    "use",
    "begin",
}

VARIATION_EXPECTATIONS = {
    "numerical": {"expects_formula_start": True, "no_final_numeric": True},
    "jee": {"expects_pattern": True, "no_final_numeric": True},
    "neet": {"expects_option_caution": True, "no_final_option": True},
    "cbse": {"expects_board_concept": True},
    "proof": {"expects_derivation_unlock": True},
    "diagram": {"expects_diagram_awareness": True},
    "ncert_strict": {"expects_ncert_language": True},
    "conceptual": {"expects_mental_model": True},
    "case_study": {"expects_contextual_reading": True},
    "multi_part": {"expects_multi_step_unlock": True},
}

MAX_TOTAL_WORDS_DEFAULT = 420


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
        "it", "as", "by", "from", "problem", "question", "answer", "section",
        "given", "find", "ncert", "context", "idea", "missing", "student",
        "students",
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


def _parse_coach(value: Any) -> tuple[bool, Optional[dict], str]:
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


def _get_coach(out: Optional[dict]) -> Optional[dict]:
    if not isinstance(out, dict):
        return None
    ok, parsed, _ = _parse_coach(out.get("coach_json"))
    return parsed if ok else None


def _get_gold_coach(ref: Optional[dict]) -> Optional[dict]:
    if not isinstance(ref, dict):
        return None
    ok, parsed, _ = _parse_coach(ref.get("coach_json"))
    return parsed if ok else None


def _sections(coach: Optional[dict]) -> list[dict]:
    if not isinstance(coach, dict):
        return []
    sections = coach.get("sections")
    return sections if isinstance(sections, list) else []


def _section_map(coach: Optional[dict]) -> dict[str, str]:
    m = {}
    for section in _sections(coach):
        if isinstance(section, dict):
            h = str(section.get("heading", "")).strip()
            b = str(section.get("bodyMarkdown", "")).strip()
            if h:
                m[h] = b
    return m


def _flatten_coach_text(coach: Optional[dict]) -> str:
    if not isinstance(coach, dict):
        return ""
    try:
        return json.dumps(coach, ensure_ascii=False)
    except Exception:
        return str(coach)


def _extract_numbers_units(text: str) -> set[str]:
    vals = set()
    for m in re.findall(r"[-+]?\d+(?:\.\d+)?(?:\s*[×x]\s*10\^?[-+]?\d+)?\s*(?:[a-zA-ZΩμ°/%²³^-]+)?", text or ""):
        val = re.sub(r"\s+", " ", m.strip())
        if val:
            vals.add(_norm(val))
    return vals


def _formula_like(text: str) -> set[str]:
    found = set()
    for p in [
        r"\b[A-Za-zρΔ][A-Za-z0-9_]*\s*=\s*[^.;,\n]+",
        r"\\frac\{[^}]+\}\{[^}]+\}",
        r"\b[A-Za-z]\^?\d+\b",
        r"\b[0-9]+/[0-9]+\b",
        r"[ρΔθΩμ][A-Za-z0-9_/*+^²³·=-]*",
    ]:
        for m in re.findall(p, text or ""):
            found.add(_norm(m))
    return found


def _has_latex_or_formula(text: str) -> bool:
    return bool("$" in text or "\\(" in text or "\\[" in text or _formula_like(text))


def _bad_latex(text: str) -> list[str]:
    issues = []
    if text.count("$") % 2 != 0:
        issues.append("unbalanced_dollar_math")
    if text.count("\\[") != text.count("\\]"):
        issues.append("unbalanced_display_math")
    if text.count("\\(") != text.count("\\)"):
        issues.append("unbalanced_inline_math")
    return issues


def _expert_final_answer(inputs: dict) -> str:
    expert = inputs.get("expert_solution_internal")
    if isinstance(expert, dict):
        return str(expert.get("final_answer", ""))
    dna = inputs.get("problem_dna")
    if isinstance(dna, dict):
        ex = dna.get("expert_solution_internal")
        if isinstance(ex, dict):
            return str(ex.get("final_answer", ""))
    return ""


def _expert_solution_text(inputs: dict) -> str:
    expert = inputs.get("expert_solution_internal")
    if not isinstance(expert, dict):
        dna = inputs.get("problem_dna")
        if isinstance(dna, dict) and isinstance(dna.get("expert_solution_internal"), dict):
            expert = dna["expert_solution_internal"]
        else:
            expert = {}
    return " ".join([
        str(expert.get("final_answer", "")),
        " ".join(expert.get("key_steps", [])) if isinstance(expert.get("key_steps"), list) else "",
        str(expert.get("method_name", "")),
    ])


def _gold_text(ref: Optional[dict]) -> str:
    gold = _get_gold_coach(ref)
    return _flatten_coach_text(gold)


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


def _has_full_derivation(text: str) -> bool:
    step_markers = len(re.findall(r"(^|\n)\s*(?:\d+\.|-|\*)\s+", text))
    equals_chain = len(re.findall(r"=", text))
    therefore_markers = len(re.findall(r"\btherefore\b|\bhence\b|\bso\b", text, flags=re.IGNORECASE))
    return step_markers >= 3 and (equals_chain >= 2 or therefore_markers >= 2)


def parse_model_response_to_outputs(raw_text: str) -> dict:
    if not isinstance(raw_text, str) or not raw_text.strip():
        return {}
    parsed = _json_from_text(raw_text)
    if isinstance(parsed, dict):
        if "coach_json" in parsed:
            ok, coach, _ = _parse_coach(parsed.get("coach_json"))
            return {"coach_json": coach if ok else parsed.get("coach_json")}
        return {"coach_json": parsed}
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

    ok, coach, raw = _parse_coach(out.get("coach_json"))
    if not ok:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"coach_json is not clean JSON object; sample={raw[:120]!r}",
        }

    if DISALLOWED_TOP_KEYS & set(coach.keys()):
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"partial-reveal output must not include keys: {sorted(DISALLOWED_TOP_KEYS & set(coach.keys()))}",
        }

    missing = REQUIRED_TOP_KEYS - set(coach.keys())
    if missing:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"coach_json missing keys: {sorted(missing)}",
        }

    if not isinstance(coach.get("title"), str) or not coach["title"].strip():
        return {"key": "schema_validity", "score": 0.0, "comment": "title must be non-empty string"}

    if coach.get("revealLevel") != "partial":
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"revealLevel must be 'partial', got {coach.get('revealLevel')!r}",
        }

    sections = coach.get("sections")
    if not isinstance(sections, list) or len(sections) != 5:
        return {"key": "schema_validity", "score": 0.0, "comment": "sections must be list of exactly 5 items"}

    headings = []
    for idx, section in enumerate(sections):
        if not isinstance(section, dict):
            return {"key": "schema_validity", "score": 0.0, "comment": f"section {idx} is not object"}
        if set(section.keys()) != {"heading", "bodyMarkdown"}:
            return {"key": "schema_validity", "score": 0.0, "comment": f"section {idx} must have heading/bodyMarkdown only"}
        heading = section.get("heading")
        body = section.get("bodyMarkdown")
        if not isinstance(heading, str) or not heading.strip():
            return {"key": "schema_validity", "score": 0.0, "comment": f"section {idx}.heading empty"}
        if not isinstance(body, str) or not body.strip():
            return {"key": "schema_validity", "score": 0.0, "comment": f"section {idx}.bodyMarkdown empty"}
        headings.append(heading)

    if headings != REQUIRED_HEADINGS:
        return {"key": "schema_validity", "score": 0.0, "comment": f"section headings/order mismatch: {headings}"}

    buttons = coach.get("followUpButtons")
    if not isinstance(buttons, list) or len(buttons) != 5:
        return {"key": "schema_validity", "score": 0.0, "comment": "followUpButtons must contain exactly 5 buttons"}

    actions = set()
    for idx, button in enumerate(buttons):
        if not isinstance(button, dict) or not isinstance(button.get("label"), str) or not isinstance(button.get("action"), str):
            return {"key": "schema_validity", "score": 0.0, "comment": f"button {idx} invalid"}
        actions.add(button["action"])

    if actions != REQUIRED_ACTIONS:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"followUp action set mismatch: {sorted(actions)}",
        }

    text = _flatten_coach_text(coach)
    if _contains_any(text, BANNED_PATTERNS | INTERNAL_LEAKS):
        return {"key": "schema_validity", "score": 0.0, "comment": "coach_json contains banned/internal phrase"}

    return {"key": "schema_validity", "score": 1.0, "comment": "schema valid"}


# ---------------------------------------------------------------------------
# Evaluator 2: section_unlock_quality_code
# ---------------------------------------------------------------------------

def section_unlock_quality_code(run, example) -> dict:
    coach = _get_coach(_safe_get_outputs(run))
    if coach is None:
        return {
            "key": "section_unlock_quality_code",
            "score": 0.0,
            "comment": "coach_json missing/malformed",
            "hard_rule_violated": False,
        }

    sec = _section_map(coach)
    issues = []
    hard = False

    for heading in REQUIRED_HEADINGS:
        body = sec.get(heading, "")
        wc = _word_count(body)
        if wc < SECTION_MIN_WORDS[heading]:
            issues.append(f"{heading}:too_short_{wc}_words")
            if heading in {"The Missing Idea", "Correct Mental Model"}:
                hard = True

    if not _contains_any(sec.get("The Missing Idea", ""), MISSING_IDEA_CUES):
        issues.append("The Missing Idea lacks unlock/key-idea cue")
        hard = True

    if not _contains_any(sec.get("Correct Mental Model", ""), MISSING_IDEA_CUES | {"think", "model", "connect", "relationship", "principle"}):
        issues.append("Correct Mental Model lacks conceptual framing")

    if not _contains_any(sec.get("How to Start", ""), START_CUES):
        issues.append("How to Start lacks actionable first-step cue")

    if not _contains_any(sec.get("Where Most Students Get Stuck", ""), TRAP_CUES):
        issues.append("student trap is generic or not explicit")
        hard = True

    total_words = _word_count(_flatten_coach_text(coach))
    if total_words > MAX_TOTAL_WORDS_DEFAULT:
        issues.append(f"too_verbose_for_missing_idea:{total_words}_words")

    if hard:
        return {
            "key": "section_unlock_quality_code",
            "score": 0.0,
            "comment": "; ".join(issues[:10]),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "section_unlock_quality_code",
            "score": 0.5,
            "comment": "; ".join(issues[:10]),
            "hard_rule_violated": False,
        }

    return {
        "key": "section_unlock_quality_code",
        "score": 1.0,
        "comment": "five-section missing-idea structure is substantive",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 3: partial_reveal_safety_code
# ---------------------------------------------------------------------------

def partial_reveal_safety_code(run, example) -> dict:
    coach = _get_coach(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)
    ref = _safe_get_reference(example)

    if coach is None:
        return {
            "key": "partial_reveal_safety_code",
            "score": 0.0,
            "comment": "coach_json missing/malformed",
            "hard_rule_violated": False,
        }

    # Leakage checks should inspect student-facing section content only.
    # Button labels legitimately include actions like "Now show full solution".
    sec = _section_map(coach)
    text = " ".join(sec.values())
    expert_final = _expert_final_answer(inputs)
    gold_text = _gold_text(ref)

    issues = []
    hard = False

    if "finalAnswer" in coach:
        issues.append("finalAnswer key present in partial reveal mode")
        hard = True

    if _contains_any(text, FULL_SOLUTION_PHRASES):
        issues.append("contains explicit full-solution/final-answer phrase")
        hard = True

    # Numeric answer leakage: compare against expert final answer when present.
    final_vals = _extract_numbers_units(expert_final)
    text_vals = _extract_numbers_units(text)

    leaked = []
    for val in final_vals:
        # Avoid tiny common coefficients leaking false positives.
        if val in {"0", "1", "2", "3", "4", "5", "10"}:
            continue
        if any(val in t or t in val for t in text_vals):
            leaked.append(val)

    # If gold has allowed partial values, do not flag those.
    gold_vals = _extract_numbers_units(gold_text)
    leaked = [v for v in leaked if not any(v in g or g in v for g in gold_vals)]

    if leaked:
        issues.append(f"likely_final_numeric_answer_leaked:{sorted(set(leaked))[:5]}")
        hard = True

    # For MCQ-like final answers, block explicit option disclosure.
    if re.search(r"\b(option|choice)\s+[abcd]\b|\b[abcd]\s+is\s+correct\b", text, flags=re.IGNORECASE):
        issues.append("final_option_leaked")
        hard = True

    # Full derivation or full solution sequence is not appropriate.
    if _has_full_derivation(text):
        issues.append("appears_to_contain_full_derivation_or_complete_solution")
        hard = True

    if hard:
        return {
            "key": "partial_reveal_safety_code",
            "score": 0.0,
            "comment": "; ".join(issues[:8]),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "partial_reveal_safety_code",
            "score": 0.5,
            "comment": "; ".join(issues[:8]),
            "hard_rule_violated": False,
        }

    return {
        "key": "partial_reveal_safety_code",
        "score": 1.0,
        "comment": "partial reveal preserved; no final-answer leakage detected",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 4: ncert_and_dependency_alignment_code
# ---------------------------------------------------------------------------

def ncert_and_dependency_alignment_code(run, example) -> dict:
    coach = _get_coach(_safe_get_outputs(run))
    ref = _safe_get_reference(example)
    inputs = _safe_get_inputs(example)

    if coach is None:
        return {
            "key": "ncert_and_dependency_alignment_code",
            "score": 0.0,
            "comment": "coach_json missing/malformed",
            "hard_rule_violated": False,
        }

    problem = str(inputs.get("problem_text_normalized", ""))
    context = str(inputs.get("ncert_context", ""))
    dna = inputs.get("problem_dna") if isinstance(inputs.get("problem_dna"), dict) else {}
    gold_text = _gold_text(ref)
    text = _flatten_coach_text(coach)
    sec = _section_map(coach)

    issues = []
    hard = False

    if _jaccard(text, problem) < 0.08 and _jaccard(text, gold_text) < 0.15:
        issues.append("weak_problem_alignment")

    unlock_text = " ".join([
        sec.get("The Missing Idea", ""),
        sec.get("Correct Mental Model", ""),
        sec.get("How to Start", ""),
    ])

    if context.strip():
        unlock_ctx = _jaccard(unlock_text, context)
        total_ctx = _jaccard(text, context)
        if unlock_ctx < 0.06 and total_ctx < 0.10 and not gold_text:
            issues.append(f"weak_ncert_context_alignment:unlock={unlock_ctx:.2f},total={total_ctx:.2f}")

    if dna:
        dna_terms = " ".join([
            str(dna.get("chapter", "")),
            " ".join(dna.get("conceptTags", [])) if isinstance(dna.get("conceptTags"), list) else "",
            str(dna.get("questionType", "")),
            str(dna.get("examSkill", "")),
        ])
        if dna_terms.strip() and _jaccard(text, dna_terms) < 0.05:
            issues.append("weak_problem_dna_alignment")

        expert_text = _expert_solution_text(inputs)
        if expert_text.strip() and _jaccard(unlock_text, expert_text) < 0.05:
            # Missing idea should align with method/concepts, but not necessarily final answer.
            formula_aligned = bool(_formula_like(unlock_text) and _formula_like(expert_text))
            if not formula_aligned:
                issues.append("weak_expert_solution_unlock_alignment")

    formulas = _formula_like(text)
    allowed_formula_text = " ".join([problem, context, gold_text, _expert_solution_text(inputs)])
    allowed_formulas = _formula_like(allowed_formula_text)
    if formulas and allowed_formulas:
        unsupported = [f for f in formulas if not any(_jaccard(f, af) >= 0.25 or f in af or af in f for af in allowed_formulas)]
        if len(unsupported) >= 3:
            issues.append(f"unsupported_formula_like_content:{unsupported[:3]}")
            hard = True

    if hard:
        return {
            "key": "ncert_and_dependency_alignment_code",
            "score": 0.0,
            "comment": "; ".join(issues),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "ncert_and_dependency_alignment_code",
            "score": 0.5,
            "comment": "; ".join(issues),
            "hard_rule_violated": False,
        }

    return {
        "key": "ncert_and_dependency_alignment_code",
        "score": 1.0,
        "comment": "NCERT/DNA/expert unlock alignment checks passed",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 5: latex_and_variation_behavior
# ---------------------------------------------------------------------------

def latex_and_variation_behavior(run, example) -> dict:
    coach = _get_coach(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)
    variation = _safe_get_variation(example)

    if coach is None:
        return {
            "key": "latex_and_variation_behavior",
            "score": 0.0,
            "comment": "coach_json missing/malformed",
            "hard_rule_violated": False,
        }

    text = _flatten_coach_text(coach)
    problem = str(inputs.get("problem_text_normalized", ""))
    sec = _section_map(coach)
    issues = []
    hard = False

    latex_issues = _bad_latex(text)
    issues.extend(latex_issues)
    if latex_issues:
        hard = True

    problem_has_math = bool(re.search(r"\\\(|\\\[|[$=^_]|[ρΔθΩμ]|\\frac|\d+\s*(?:Ω|V|A|m/s|mol|cm|kg|J|N|pm|eV)", problem))
    if problem_has_math and not _has_latex_or_formula(text):
        issues.append("math_problem_but_no_latex_or_formula_formatting")

    exp = VARIATION_EXPECTATIONS.get(variation, {})
    unlock_text = " ".join([
        sec.get("The Missing Idea", ""),
        sec.get("Correct Mental Model", ""),
        sec.get("How to Start", ""),
        sec.get("Where Most Students Get Stuck", ""),
    ])

    if exp.get("expects_formula_start") and not _formula_like(unlock_text):
        issues.append("numerical_missing_starting_formula_or_relation")

    if exp.get("expects_pattern") and not _contains_any(unlock_text, {"pattern", "recognize", "trigger", "direct", "standard", "shortcut"}):
        issues.append("jee_pattern_unlock_missing")

    if exp.get("expects_option_caution") and not _contains_any(unlock_text, {"option", "choice", "statement", "eliminate", "assertion", "reason"}):
        issues.append("neet_option_or_statement_caution_missing")

    if exp.get("expects_board_concept") and not _contains_any(unlock_text, {"definition", "principle", "ncert", "board", "standard"}):
        issues.append("cbse_board_concept_cue_missing")

    if exp.get("expects_derivation_unlock") and not _contains_any(unlock_text, {"derive", "start from", "show", "prove", "relationship", "principle"}):
        issues.append("proof_derivation_unlock_missing")

    if exp.get("expects_diagram_awareness") and not _contains_any(unlock_text, {"diagram", "figure", "graph", "ray", "shown", "label", "axis"}):
        issues.append("diagram_awareness_missing")

    if exp.get("expects_ncert_language") and not _contains_any(unlock_text, {"ncert", "standard", "definition", "principle", "textbook"}):
        issues.append("ncert_strict_language_missing")

    if exp.get("expects_mental_model") and not _contains_any(sec.get("Correct Mental Model", ""), {"think", "model", "connect", "relationship", "principle", "because"}):
        issues.append("conceptual_mental_model_missing")

    if exp.get("expects_contextual_reading") and not _contains_any(unlock_text, {"passage", "case", "given", "data", "statement"}):
        issues.append("case_study_contextual_reading_missing")

    if exp.get("expects_multi_step_unlock") and not _contains_any(unlock_text, {"first", "then", "link", "chain", "step", "combine"}):
        issues.append("multi_part_unlock_sequence_missing")

    if hard:
        return {
            "key": "latex_and_variation_behavior",
            "score": 0.0,
            "comment": "; ".join(issues[:10]),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "latex_and_variation_behavior",
            "score": 0.5,
            "comment": "; ".join(issues[:10]),
            "hard_rule_violated": False,
        }

    return {
        "key": "latex_and_variation_behavior",
        "score": 1.0,
        "comment": "LaTeX and variation behavior checks passed",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 6: required LLM judge
# ---------------------------------------------------------------------------

def make_required_llm_missing_idea_judge(judge_llm: Callable[[str], str]):
    def required_llm_missing_idea_judge(run, example) -> dict:
        coach = _get_coach(_safe_get_outputs(run))
        ref = _safe_get_reference(example)
        inputs = _safe_get_inputs(example)

        if coach is None:
            return {
                "key": "required_llm_missing_idea_judge",
                "score": 0.0,
                "comment": "coach_json missing/malformed",
                "hard_rule_violated": True,
                "judge_available": False,
            }

        gold = _get_gold_coach(ref)
        prompt = f"""
You are evaluating ScholarSync's Show Missing Idea Coach for Indian Class 11-12/JEE/NEET/CBSE problem solving.

Evaluate the candidate ONLY against:
- the problem,
- NCERT context,
- optional Problem DNA / expert solution,
- gold/reference answer if provided.

Return ONLY valid JSON:
{{
  "missing_idea_quality_score": <0.0 to 1.0>,
  "partial_reveal_safety_score": <0.0 to 1.0>,
  "ncert_alignment_score": <0.0 to 1.0>,
  "student_trap_specificity_score": <0.0 to 1.0>,
  "format_compliance_score": <0.0 to 1.0>,
  "comment": "<short reason, max 45 words>"
}}

Scoring guidance:
- missing_idea_quality_score: identifies the real conceptual unlock, not a generic tip.
- partial_reveal_safety_score: does NOT reveal final answer/full solution by default.
- ncert_alignment_score: mental model and starting idea match NCERT context/gold.
- student_trap_specificity_score: trap is specific to this problem type.
- format_compliance_score: exactly five sections, revealLevel partial, no finalAnswer key.

Problem:
{inputs.get("problem_text_normalized", "")}

NCERT context:
{inputs.get("ncert_context", "")}

Problem DNA:
{json.dumps(inputs.get("problem_dna", {}), ensure_ascii=False)}

Expert solution internal:
{json.dumps(inputs.get("expert_solution_internal", {}), ensure_ascii=False)}

Gold/reference coach:
{json.dumps(gold, ensure_ascii=False) if gold else ""}

Candidate coach:
{json.dumps(coach, ensure_ascii=False)}
""".strip()

        try:
            raw = judge_llm(prompt)
        except Exception as exc:
            return {
                "key": "required_llm_missing_idea_judge",
                "score": 0.0,
                "comment": f"judge call failed: {exc}",
                "hard_rule_violated": True,
                "judge_available": False,
            }

        parsed = _json_from_text(raw)
        if not parsed:
            return {
                "key": "required_llm_missing_idea_judge",
                "score": 0.0,
                "comment": f"judge returned invalid JSON: {str(raw)[:160]}",
                "hard_rule_violated": True,
                "judge_available": False,
            }

        idea = _coerce_score(parsed.get("missing_idea_quality_score"))
        safety = _coerce_score(parsed.get("partial_reveal_safety_score"))
        ncert = _coerce_score(parsed.get("ncert_alignment_score"))
        trap = _coerce_score(parsed.get("student_trap_specificity_score"))
        fmt = _coerce_score(parsed.get("format_compliance_score"))
        comment = str(parsed.get("comment", "")).strip()

        score = round(
            (0.32 * idea)
            + (0.28 * safety)
            + (0.18 * ncert)
            + (0.15 * trap)
            + (0.07 * fmt),
            3,
        )
        hard = idea < 0.65 or safety < 0.80 or ncert < 0.60 or fmt < 0.70

        return {
            "key": "required_llm_missing_idea_judge",
            "score": score,
            "comment": (
                f"idea={idea:.2f} safety={safety:.2f} ncert={ncert:.2f} "
                f"trap={trap:.2f} format={fmt:.2f} | {comment}"
            ),
            "missing_idea_quality_score": idea,
            "partial_reveal_safety_score": safety,
            "ncert_alignment_score": ncert,
            "student_trap_specificity_score": trap,
            "format_compliance_score": fmt,
            "hard_rule_violated": hard,
            "judge_available": True,
        }

    return required_llm_missing_idea_judge


def build_per_example_evaluators(judge_llm: Callable[[str], str]) -> list[Callable]:
    if judge_llm is None or not callable(judge_llm):
        raise ValueError("Agent 20 evaluation requires judge_llm. Use build_per_example_evaluators(judge_llm).")
    return [
        schema_validity,
        section_unlock_quality_code,
        partial_reveal_safety_code,
        ncert_and_dependency_alignment_code,
        latex_and_variation_behavior,
        make_required_llm_missing_idea_judge(judge_llm),
    ]


# ---------------------------------------------------------------------------
# Summary evaluator
# ---------------------------------------------------------------------------

def show_missing_idea_severity_summary(runs: list, examples: list) -> dict:
    if len(runs) != len(examples):
        return {
            "key": "show_missing_idea_severity_summary",
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

        section = section_unlock_quality_code(run, example)
        safety = partial_reveal_safety_code(run, example)
        align = ncert_and_dependency_alignment_code(run, example)
        latex = latex_and_variation_behavior(run, example)
        llm = _extract_required_llm_feedback(run)

        for result in (section, safety, align, latex):
            if result.get("hard_rule_violated"):
                tier_0.append({"example_id": getattr(example, "id", None), "reason": f"{result['key']} hard failure: {result['comment']}"})

        if llm is not None:
            if llm.get("hard_rule_violated") or llm.get("score", 0.0) < 0.70:
                tier_0.append({"example_id": getattr(example, "id", None), "reason": f"LLM judge hard failure: {llm.get('comment', '')}"})
            elif llm.get("score", 1.0) < 0.84:
                tier_1 += 1
                tier_1_applicable += 1

        tier_1_applicable += 5
        for result in (section, safety, align, latex):
            if result["score"] < 1.0:
                tier_1 += 1

        llm_ok = True if llm is None else llm.get("score", 0.0) >= 0.84
        if section["score"] == safety["score"] == align["score"] == latex["score"] == 1.0 and llm_ok:
            variation_passes[variation] = variation_passes.get(variation, 0) + 1

    tier_1_rate = tier_1 / tier_1_applicable if tier_1_applicable else 0.0
    per_variation = {v: round(variation_passes.get(v, 0) / total, 3) for v, total in variation_totals.items()}

    recommendation = "BLOCK" if tier_0 else ("REVIEW" if tier_1_rate > 0.15 else "OK")

    return {
        "key": "show_missing_idea_severity_summary",
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
            if val.get("key") == "required_llm_missing_idea_judge":
                return val
            maybe = val.get("required_llm_missing_idea_judge")
            if isinstance(maybe, dict):
                return maybe
            if isinstance(maybe, (int, float)):
                return {
                    "key": "required_llm_missing_idea_judge",
                    "score": float(maybe),
                    "comment": "score extracted from run feedback mapping",
                    "hard_rule_violated": float(maybe) < 0.70,
                }
        if isinstance(val, list):
            for item in val:
                if isinstance(item, dict) and item.get("key") == "required_llm_missing_idea_judge":
                    return item
    return None


# ---------------------------------------------------------------------------
# Public registries
# ---------------------------------------------------------------------------

PER_EXAMPLE_EVALUATORS_CODE_ONLY = [
    schema_validity,
    section_unlock_quality_code,
    partial_reveal_safety_code,
    ncert_and_dependency_alignment_code,
    latex_and_variation_behavior,
]

PER_EXAMPLE_EVALUATORS = None

SUMMARY_EVALUATORS = [show_missing_idea_severity_summary]
