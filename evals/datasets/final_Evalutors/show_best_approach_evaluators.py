"""
show_best_approach_evaluators.py

LangSmith custom evaluators for Agent 19: Show Best Approach Coach.

Agent role:
- One of the mutually exclusive coach modes after Agent 17 Problem DNA Analyzer.
- Gives the fastest reliable exam-oriented method, not a from-basics explanation.
- Must reveal the full answer, but the emphasis is:
  pattern recognition, best method choice, efficient setup, clean solution,
  exam note, and when not to use the method.

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
        {"heading": "Problem Pattern", "bodyMarkdown": "..."},
        {"heading": "Best Method", "bodyMarkdown": "..."},
        {"heading": "Why This Fits", "bodyMarkdown": "..."},
        {"heading": "Efficient Setup", "bodyMarkdown": "..."},
        {"heading": "Clean Solution", "bodyMarkdown": "..."},
        {"heading": "Exam Note", "bodyMarkdown": "..."},
        {"heading": "When Not to Use", "bodyMarkdown": "..."}
      ],
      "finalAnswer": str,
      "revealLevel": "full",
      "followUpButtons": [
        {"label": str, "action": str}
      ]
    }

Evaluator design:
- Hybrid by default.
- Code gates verify schema, seven-section completeness, reveal level, final
  answer consistency, exam-efficiency cues, NCERT/DNA/expert alignment, LaTeX/unit
  hygiene, and variation behavior.
- Required LLM judge verifies semantic correctness, method efficiency, NCERT
  alignment, and exam strategy value.
- This is Tier 1 because it is student-facing and depends on Agent 17. A wrong
  "best method" can mis-train student problem-solving strategy.

LangSmith usage:
    from show_best_approach_evaluators import (
        build_per_example_evaluators,
        SUMMARY_EVALUATORS,
    )

    evaluators = build_per_example_evaluators(judge_llm)

Judge callable:
    judge_llm(prompt: str) -> str

Judge must return JSON:
{
  "solution_correctness_score": 0.0-1.0,
  "method_efficiency_score": 0.0-1.0,
  "ncert_alignment_score": 0.0-1.0,
  "exam_strategy_score": 0.0-1.0,
  "format_compliance_score": 0.0-1.0,
  "comment": "short reason"
}
"""

from __future__ import annotations

import json
import math
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
    "finalAnswer",
    "revealLevel",
    "followUpButtons",
}

REQUIRED_HEADINGS = [
    "Problem Pattern",
    "Best Method",
    "Why This Fits",
    "Efficient Setup",
    "Clean Solution",
    "Exam Note",
    "When Not to Use",
]

REQUIRED_ACTIONS = {
    "COMPARE_BASIC_METHOD",
    "EXPLAIN_WHY_WORKS",
    "GIVE_SIMILAR_PROBLEM",
    "SHOW_COMMON_MISTAKES",
    "START_TUTOR_SESSION",
}

SECTION_MIN_WORDS = {
    "Problem Pattern": 10,
    "Best Method": 8,
    "Why This Fits": 10,
    "Efficient Setup": 12,
    "Clean Solution": 15,
    "Exam Note": 8,
    "When Not to Use": 8,
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

METHOD_CUES = {
    "direct formula",
    "shortcut",
    "elimination",
    "standard result",
    "pattern",
    "fastest",
    "efficient",
    "exam",
    "direct substitution",
    "dimensional",
    "graph",
    "derive",
    "ncert",
    "method",
}

WHY_FITS_CUES = {
    "because",
    "fits",
    "works",
    "given",
    "asks",
    "pattern",
    "direct",
    "therefore",
    "suitable",
}

EXAM_NOTE_CUES = {
    "remember",
    "shortcut",
    "warning",
    "mistake",
    "unit",
    "sign",
    "exam",
    "trigger",
    "variation",
    "tip",
}

WHEN_NOT_CUES = {
    "not use",
    "fails",
    "only when",
    "unless",
    "exception",
    "assumption",
    "breakdown",
    "alternative",
    "special case",
}

VARIATION_EXPECTATIONS = {
    "numerical": {"expects_formula": True, "expects_units": True, "expects_efficiency": True},
    "jee": {"expects_formula": True, "expects_shortcut": True, "expects_efficiency": True},
    "neet": {"expects_option": True, "expects_elimination": True},
    "cbse": {"expects_board_style": True},
    "proof": {"expects_derivation": True},
    "diagram": {"expects_diagram_awareness": True},
    "ncert_strict": {"expects_ncert_language": True},
    "conceptual": {"expects_concept_reason": True},
    "case_study": {"expects_contextual_reading": True},
    "multi_part": {"expects_steps": True},
}

MAX_TOTAL_WORDS_DEFAULT = 700


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
        "step", "solution", "given", "find", "ncert", "context", "method",
        "approach",
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
    if not raw:
        return False, None, raw
    if "```" in raw:
        parsed = _json_from_text(raw)
        return (True, parsed, raw) if isinstance(parsed, dict) else (False, None, raw)
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
    return bool(
        "$" in text
        or "\\(" in text
        or "\\[" in text
        or _formula_like(text)
    )


def _bad_latex(text: str) -> list[str]:
    issues = []
    if text.count("$") % 2 != 0:
        issues.append("unbalanced_dollar_math")
    if text.count("\\[") != text.count("\\]"):
        issues.append("unbalanced_display_math")
    if text.count("\\(") != text.count("\\)"):
        issues.append("unbalanced_inline_math")
    return issues


def _final_answer_text(coach: Optional[dict]) -> str:
    if not isinstance(coach, dict):
        return ""
    return str(coach.get("finalAnswer", "")).strip()


def _gold_final_answer(ref: Optional[dict]) -> str:
    gold = _get_gold_coach(ref)
    return _final_answer_text(gold)


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


def _json_from_text(text: str) -> Optional[dict]:
    from evals.agent_eval.coach_json_parse import json_dict_from_text

    return json_dict_from_text(text)


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

    missing = REQUIRED_TOP_KEYS - set(coach.keys())
    if missing:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"coach_json missing keys: {sorted(missing)}",
        }

    if not isinstance(coach.get("title"), str) or not coach["title"].strip():
        return {"key": "schema_validity", "score": 0.0, "comment": "title must be non-empty string"}

    if coach.get("revealLevel") != "full":
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"revealLevel must be 'full', got {coach.get('revealLevel')!r}",
        }

    if not isinstance(coach.get("finalAnswer"), str) or not coach["finalAnswer"].strip():
        return {"key": "schema_validity", "score": 0.0, "comment": "finalAnswer must be non-empty string"}

    sections = coach.get("sections")
    if not isinstance(sections, list) or len(sections) != 7:
        return {"key": "schema_validity", "score": 0.0, "comment": "sections must be list of exactly 7 items"}

    headings = []
    for idx, section in enumerate(sections):
        if not isinstance(section, dict):
            return {"key": "schema_validity", "score": 0.0, "comment": f"section {idx} is not object"}
        if not {"heading", "bodyMarkdown"}.issubset(set(section.keys())):
            return {"key": "schema_validity", "score": 0.0, "comment": f"section {idx} missing heading/bodyMarkdown"}
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
# Evaluator 2: exam_strategy_structure
# ---------------------------------------------------------------------------

def exam_strategy_structure(run, example) -> dict:
    coach = _get_coach(_safe_get_outputs(run))
    if coach is None:
        return {
            "key": "exam_strategy_structure",
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
            if heading in {"Best Method", "Clean Solution"}:
                hard = True

    if not _contains_any(sec.get("Best Method", ""), METHOD_CUES):
        issues.append("Best Method lacks exam-method cue")
        hard = True

    if not _contains_any(sec.get("Why This Fits", ""), WHY_FITS_CUES):
        issues.append("Why This Fits does not justify method choice")

    if not _contains_any(sec.get("Exam Note", ""), EXAM_NOTE_CUES):
        issues.append("Exam Note lacks shortcut/warning/tip cue")

    if not _contains_any(sec.get("When Not to Use", ""), WHEN_NOT_CUES):
        issues.append("When Not to Use does not define limitation/exception")
        hard = True

    clean = sec.get("Clean Solution", "")
    if len(re.findall(r"(^|\n)\s*(?:\d+\.|-|\*)\s+", clean)) < 1 and _word_count(clean) < 35:
        issues.append("Clean Solution not stepwise enough")

    # Best approach should not become a long basics lecture.
    total_words = _word_count(_flatten_coach_text(coach))
    if total_words > MAX_TOTAL_WORDS_DEFAULT:
        issues.append(f"too_verbose_for_best_approach:{total_words}_words")

    if hard:
        return {
            "key": "exam_strategy_structure",
            "score": 0.0,
            "comment": "; ".join(issues[:10]),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "exam_strategy_structure",
            "score": 0.5,
            "comment": "; ".join(issues[:10]),
            "hard_rule_violated": False,
        }

    return {
        "key": "exam_strategy_structure",
        "score": 1.0,
        "comment": "seven-section exam strategy structure passed",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 3: final_answer_consistency
# ---------------------------------------------------------------------------

def final_answer_consistency(run, example) -> dict:
    coach = _get_coach(_safe_get_outputs(run))
    ref = _safe_get_reference(example)
    inputs = _safe_get_inputs(example)

    if coach is None:
        return {
            "key": "final_answer_consistency",
            "score": 0.0,
            "comment": "coach_json missing/malformed",
            "hard_rule_violated": False,
        }

    final = _final_answer_text(coach)
    sec = _section_map(coach)
    clean = sec.get("Clean Solution", "")
    final_section_text = clean + " " + final

    gold = _gold_final_answer(ref)
    expert = _expert_final_answer(inputs)
    ref_answer = gold or expert

    issues = []
    hard = False

    if not final:
        issues.append("missing_finalAnswer")
        hard = True

    # Must be reflected in clean solution.
    final_nums = _extract_numbers_units(final)
    clean_nums = _extract_numbers_units(clean)
    numeric_reflected = bool(final_nums and clean_nums and any(a in b or b in a for a in final_nums for b in clean_nums))
    if _jaccard(final, clean) < 0.10 and _norm(final) not in _norm(clean) and not numeric_reflected:
        issues.append("finalAnswer_not_reflected_in_clean_solution")
        hard = True

    # Must match gold/expert when available.
    ref_nums = _extract_numbers_units(ref_answer)
    if ref_answer and ref_nums and final_nums:
        if not any(r in f or f in r for r in ref_nums for f in final_nums):
            issues.append(f"numeric_final_answer_mismatch:pred={sorted(final_nums)[:4]},ref={sorted(ref_nums)[:4]}")
            hard = True
    elif ref_answer and _jaccard(final, ref_answer) < 0.12:
        issues.append("finalAnswer_low_reference_overlap")

    if hard:
        return {
            "key": "final_answer_consistency",
            "score": 0.0,
            "comment": "; ".join(issues),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "final_answer_consistency",
            "score": 0.5,
            "comment": "; ".join(issues),
            "hard_rule_violated": False,
        }

    return {
        "key": "final_answer_consistency",
        "score": 1.0,
        "comment": "final answer is consistent with clean solution/reference",
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
    gold = _get_gold_coach(ref)
    gold_text = _flatten_coach_text(gold)
    text = _flatten_coach_text(coach)
    sec = _section_map(coach)

    issues = []
    hard = False

    if _jaccard(text, problem) < 0.08 and _jaccard(text, gold_text) < 0.15:
        issues.append("weak_problem_alignment")

    # Best Method + Efficient Setup should align with NCERT/expert/DNA.
    strategy_text = " ".join([
        sec.get("Problem Pattern", ""),
        sec.get("Best Method", ""),
        sec.get("Why This Fits", ""),
        sec.get("Efficient Setup", ""),
    ])

    if context.strip():
        strat_ctx = _jaccard(strategy_text, context)
        total_ctx = _jaccard(text, context)
        if strat_ctx < 0.06 and total_ctx < 0.10 and not gold_text:
            issues.append(f"weak_ncert_context_alignment:strategy={strat_ctx:.2f},total={total_ctx:.2f}")

    if dna:
        dna_terms = " ".join([
            str(dna.get("chapter", "")),
            " ".join(dna.get("conceptTags", [])) if isinstance(dna.get("conceptTags"), list) else "",
            str(dna.get("questionType", "")),
            str(dna.get("examSkill", "")),
        ])
        if dna_terms.strip() and _jaccard(text, dna_terms) < 0.05:
            issues.append("weak_problem_dna_alignment")

        expert = dna.get("expert_solution_internal")
        if isinstance(expert, dict):
            expert_text = " ".join([
                str(expert.get("final_answer", "")),
                " ".join(expert.get("key_steps", [])) if isinstance(expert.get("key_steps"), list) else "",
                str(expert.get("method_name", "")),
            ])
            if expert_text.strip() and _jaccard(text, expert_text) < 0.06:
                coach_nums = _extract_numbers_units(text)
                expert_nums = _extract_numbers_units(expert_text)
                numeric_aligned = bool(coach_nums and expert_nums and any(a in b or b in a for a in coach_nums for b in expert_nums))
                if not numeric_aligned:
                    issues.append("weak_expert_solution_alignment")

    formulas = _formula_like(text)
    allowed_formula_text = " ".join([problem, context, gold_text])
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
        "comment": "NCERT/DNA/expert alignment checks passed",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 5: efficiency_latex_variation_behavior
# ---------------------------------------------------------------------------

def efficiency_latex_variation_behavior(run, example) -> dict:
    coach = _get_coach(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)
    variation = _safe_get_variation(example)

    if coach is None:
        return {
            "key": "efficiency_latex_variation_behavior",
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
    strategy_text = " ".join([
        sec.get("Best Method", ""),
        sec.get("Why This Fits", ""),
        sec.get("Efficient Setup", ""),
        sec.get("Exam Note", ""),
    ])

    if exp.get("expects_formula") and not _formula_like(strategy_text + " " + sec.get("Clean Solution", "")):
        issues.append("formula_expected_but_missing")

    if exp.get("expects_units") and re.search(r"\d", problem) and not re.search(r"\\text\{|Ω|V|A|mol|cm|kg|J|N|pm|eV", text):
        issues.append("unit_handling_expected_but_missing")

    if exp.get("expects_shortcut") and not _contains_any(strategy_text, {"shortcut", "fast", "efficient", "direct", "elimination", "standard result"}):
        issues.append("shortcut_efficiency_expected_but_not_reflected")

    if exp.get("expects_efficiency") and not _contains_any(strategy_text, METHOD_CUES):
        issues.append("efficiency_cues_missing")

    if exp.get("expects_option") and not re.search(r"\b(option|correct option|choice|eliminate)\b", text, flags=re.IGNORECASE):
        issues.append("mcq_option_language_missing")

    if exp.get("expects_elimination") and not _contains_any(strategy_text, {"eliminate", "option", "choice", "statement", "true", "false"}):
        issues.append("neet_mcq_elimination_or_statement_logic_missing")

    if exp.get("expects_derivation") and not _contains_any(text, {"derive", "therefore", "hence", "show that", "prove", "standard derivation"}):
        issues.append("proof_derivation_language_missing")

    if exp.get("expects_diagram_awareness") and not _contains_any(text, {"diagram", "figure", "graph", "ray", "shown", "label"}):
        issues.append("diagram_awareness_missing")

    if exp.get("expects_ncert_language") and not _contains_any(text, {"ncert", "standard", "definition", "principle", "textbook"}):
        issues.append("ncert_strict_language_missing")

    if exp.get("expects_concept_reason") and not _contains_any(sec.get("Why This Fits", "") + " " + sec.get("Exam Note", ""), {"because", "reason", "concept", "principle"}):
        issues.append("conceptual_reasoning_missing")

    if exp.get("expects_contextual_reading") and not _contains_any(sec.get("Problem Pattern", "") + " " + sec.get("Efficient Setup", ""), {"passage", "case", "given", "data", "statement"}):
        issues.append("case_study_contextual_reading_missing")

    if exp.get("expects_steps") and _word_count(sec.get("Clean Solution", "")) < 35:
        issues.append("multi_part_clean_solution_too_short")

    if hard:
        return {
            "key": "efficiency_latex_variation_behavior",
            "score": 0.0,
            "comment": "; ".join(issues[:10]),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "efficiency_latex_variation_behavior",
            "score": 0.5,
            "comment": "; ".join(issues[:10]),
            "hard_rule_violated": False,
        }

    return {
        "key": "efficiency_latex_variation_behavior",
        "score": 1.0,
        "comment": "efficiency, LaTeX, and variation behavior checks passed",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 6: required LLM judge
# ---------------------------------------------------------------------------

def make_required_llm_best_approach_judge(judge_llm: Callable[[str], str]):
    def required_llm_best_approach_judge(run, example) -> dict:
        coach = _get_coach(_safe_get_outputs(run))
        ref = _safe_get_reference(example)
        inputs = _safe_get_inputs(example)

        if coach is None:
            return {
                "key": "required_llm_best_approach_judge",
                "score": 0.0,
                "comment": "coach_json missing/malformed",
                "hard_rule_violated": True,
                "judge_available": False,
            }

        gold = _get_gold_coach(ref)
        prompt = f"""
You are evaluating ScholarSync's Show Best Approach Coach for Indian Class 11-12/JEE/NEET/CBSE problem solving.

Evaluate the candidate answer ONLY against:
- the problem,
- NCERT context,
- optional Problem DNA / expert solution,
- gold/reference answer if provided.

Return ONLY valid JSON:
{{
  "solution_correctness_score": <0.0 to 1.0>,
  "method_efficiency_score": <0.0 to 1.0>,
  "ncert_alignment_score": <0.0 to 1.0>,
  "exam_strategy_score": <0.0 to 1.0>,
  "format_compliance_score": <0.0 to 1.0>,
  "comment": "<short reason, max 45 words>"
}}

Scoring guidance:
- solution_correctness_score: final answer and clean solution are correct.
- method_efficiency_score: selected method is actually faster/reliable for exam use.
- ncert_alignment_score: formulas/principles match NCERT context or gold.
- exam_strategy_score: identifies pattern, why method fits, exam note, and when not to use.
- format_compliance_score: exactly seven sections, revealLevel full, readable Markdown/LaTeX.

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
                "key": "required_llm_best_approach_judge",
                "score": 0.0,
                "comment": f"judge call failed: {exc}",
                "hard_rule_violated": False,
                "judge_available": False,
            }

        parsed = _json_from_text(raw)
        if not parsed:
            return {
                "key": "required_llm_best_approach_judge",
                "score": 0.0,
                "comment": f"judge returned invalid JSON: {str(raw)[:160]}",
                "hard_rule_violated": False,
                "judge_available": False,
            }

        sol = _coerce_score(parsed.get("solution_correctness_score"))
        method = _coerce_score(parsed.get("method_efficiency_score"))
        ncert = _coerce_score(parsed.get("ncert_alignment_score"))
        strategy = _coerce_score(parsed.get("exam_strategy_score"))
        fmt = _coerce_score(parsed.get("format_compliance_score"))
        comment = str(parsed.get("comment", "")).strip()

        score = round(
            (0.32 * sol)
            + (0.25 * method)
            + (0.18 * ncert)
            + (0.18 * strategy)
            + (0.07 * fmt),
            3,
        )
        hard = sol < 0.65 or method < 0.65 or ncert < 0.60 or fmt < 0.70

        return {
            "key": "required_llm_best_approach_judge",
            "score": score,
            "comment": (
                f"solution={sol:.2f} method={method:.2f} ncert={ncert:.2f} "
                f"strategy={strategy:.2f} format={fmt:.2f} | {comment}"
            ),
            "solution_correctness_score": sol,
            "method_efficiency_score": method,
            "ncert_alignment_score": ncert,
            "exam_strategy_score": strategy,
            "format_compliance_score": fmt,
            "hard_rule_violated": hard,
            "judge_available": True,
        }

    return required_llm_best_approach_judge


def build_per_example_evaluators(judge_llm: Callable[[str], str]) -> list[Callable]:
    if judge_llm is None or not callable(judge_llm):
        raise ValueError("Agent 19 evaluation requires judge_llm. Use build_per_example_evaluators(judge_llm).")
    return [
        schema_validity,
        exam_strategy_structure,
        final_answer_consistency,
        ncert_and_dependency_alignment_code,
        efficiency_latex_variation_behavior,
        make_required_llm_best_approach_judge(judge_llm),
    ]


# ---------------------------------------------------------------------------
# Summary evaluator
# ---------------------------------------------------------------------------

def show_best_approach_severity_summary(runs: list, examples: list) -> dict:
    if len(runs) != len(examples):
        return {
            "key": "show_best_approach_severity_summary",
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

        strategy = exam_strategy_structure(run, example)
        final = final_answer_consistency(run, example)
        align = ncert_and_dependency_alignment_code(run, example)
        variation_behavior = efficiency_latex_variation_behavior(run, example)
        llm = _extract_required_llm_feedback(run)

        for result in (strategy, final, align, variation_behavior):
            if result.get("hard_rule_violated"):
                tier_0.append({"example_id": getattr(example, "id", None), "reason": f"{result['key']} hard failure: {result['comment']}"})

        if llm is not None and llm.get("judge_available", True):
            if llm.get("hard_rule_violated") or llm.get("score", 0.0) < 0.68:
                tier_0.append({"example_id": getattr(example, "id", None), "reason": f"LLM judge hard failure: {llm.get('comment', '')}"})
            elif llm.get("score", 1.0) < 0.82:
                tier_1 += 1
                tier_1_applicable += 1

        tier_1_applicable += 5
        for result in (strategy, final, align, variation_behavior):
            if result["score"] < 1.0:
                tier_1 += 1

        llm_ok = True if llm is None else llm.get("score", 0.0) >= 0.82
        if strategy["score"] == final["score"] == align["score"] == variation_behavior["score"] == 1.0 and llm_ok:
            variation_passes[variation] = variation_passes.get(variation, 0) + 1

    tier_1_rate = tier_1 / tier_1_applicable if tier_1_applicable else 0.0
    per_variation = {v: round(variation_passes.get(v, 0) / total, 3) for v, total in variation_totals.items()}

    recommendation = "BLOCK" if tier_0 else ("REVIEW" if tier_1_rate > 0.15 else "OK")

    return {
        "key": "show_best_approach_severity_summary",
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
            if val.get("key") == "required_llm_best_approach_judge":
                return val
            maybe = val.get("required_llm_best_approach_judge")
            if isinstance(maybe, dict):
                return maybe
            if isinstance(maybe, (int, float)):
                return {
                    "key": "required_llm_best_approach_judge",
                    "score": float(maybe),
                    "comment": "score extracted from run feedback mapping",
                    "hard_rule_violated": float(maybe) < 0.68,
                }
        if isinstance(val, list):
            for item in val:
                if isinstance(item, dict) and item.get("key") == "required_llm_best_approach_judge":
                    return item
    return None


# ---------------------------------------------------------------------------
# Public registries
# ---------------------------------------------------------------------------

PER_EXAMPLE_EVALUATORS_CODE_ONLY = [
    schema_validity,
    exam_strategy_structure,
    final_answer_consistency,
    ncert_and_dependency_alignment_code,
    efficiency_latex_variation_behavior,
]

PER_EXAMPLE_EVALUATORS = None

SUMMARY_EVALUATORS = [show_best_approach_severity_summary]
