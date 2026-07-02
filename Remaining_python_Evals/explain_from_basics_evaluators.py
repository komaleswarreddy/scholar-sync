"""
explain_from_basics_evaluators.py

LangSmith custom evaluators for Agent 18: Explain From Basics Coach.

Agent role:
- First selectable coach mode after Agent 17 Problem DNA Analyzer.
- Provides a full beginner-friendly walkthrough for a solved problem.
- Must reveal the full answer and solution, but in a structured educational way.

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
        {"heading": "Question Understanding", "bodyMarkdown": "..."},
        {"heading": "Given Information", "bodyMarkdown": "..."},
        {"heading": "What to Find", "bodyMarkdown": "..."},
        {"heading": "Concept Needed", "bodyMarkdown": "..."},
        {"heading": "Formula/Principle", "bodyMarkdown": "..."},
        {"heading": "Step-by-step Solution", "bodyMarkdown": "..."},
        {"heading": "Final Answer", "bodyMarkdown": "..."},
        {"heading": "Key Learning", "bodyMarkdown": "..."}
      ],
      "finalAnswer": str,
      "revealLevel": "full",
      "followUpButtons": [
        {"label": str, "action": str}
      ]
    }

Evaluator design:
- Hybrid by default.
- Code gates verify schema, section completeness, reveal level, final answer
  consistency, dependency alignment, LaTeX hygiene, no placeholders, and grounding.
- Required LLM judge verifies semantic correctness, NCERT alignment, beginner
  pedagogy, and solution validity.
- This is Tier 1 because it is student-facing and depends on Agent 17 DNA/expert
  solution. A wrong full solution is a critical product failure.

LangSmith usage:
    from explain_from_basics_evaluators import (
        build_per_example_evaluators,
        SUMMARY_EVALUATORS,
    )

    evaluators = build_per_example_evaluators(judge_llm)

Judge callable:
    judge_llm(prompt: str) -> str

Judge must return JSON:
{
  "solution_correctness_score": 0.0-1.0,
  "ncert_alignment_score": 0.0-1.0,
  "beginner_pedagogy_score": 0.0-1.0,
  "format_compliance_score": 0.0-1.0,
  "comment": "short reason"
}
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Optional


REQUIRED_INPUT_KEYS = {"problem_text_normalized", "ncert_context"}
REQUIRED_OUTPUT_KEYS = {"coach_json"}

REQUIRED_TOP_KEYS = {"title", "sections", "finalAnswer", "revealLevel", "followUpButtons"}

REQUIRED_HEADINGS = [
    "Question Understanding",
    "Given Information",
    "What to Find",
    "Concept Needed",
    "Formula/Principle",
    "Step-by-step Solution",
    "Final Answer",
    "Key Learning",
]

REQUIRED_ACTIONS = {
    "SHOW_SHORTER_VERSION",
    "SHOW_BEST_APPROACH",
    "GIVE_SIMILAR_PROBLEM",
    "EXPLAIN_CONCEPT_AGAIN",
    "START_TUTOR_SESSION",
}

SECTION_MIN_WORDS = {
    "Question Understanding": 8,
    "Given Information": 6,
    "What to Find": 5,
    "Concept Needed": 8,
    "Formula/Principle": 6,
    "Step-by-step Solution": 25,
    "Final Answer": 3,
    "Key Learning": 8,
}

BANNED_PATTERNS = {
    "as an ai language model",
    "i cannot access",
    "i don't have access",
    "not enough context",
    "restating the problem",
    "placeholder",
    "todo",
    "lorem ipsum",
}

INTERNAL_LEAKS = {
    "expert_solution_internal",
    "problem_dna",
    "guard",
    "coach_json",
    "jinja",
    ".j2",
    "system prompt",
}

VARIATION_EXPECTATIONS = {
    "numerical": {"expects_steps": True, "expects_formula": True},
    "jee": {"expects_steps": True, "expects_formula": True},
    "neet": {"expects_steps": True, "expects_option": True},
    "cbse": {"expects_steps": True},
    "proof": {"expects_derivation": True},
    "diagram": {"expects_diagram_awareness": True},
    "conceptual": {"expects_concept": True},
    "case_study": {"expects_contextual_reading": True},
    "multi_part": {"expects_steps": True},
}

LATEX_ALLOWED_PATTERNS = [
    r"\$[^$]+\$",
    r"\\\[[\s\S]+?\\\]",
    r"\\\([\s\S]+?\\\)",
]

SUMMARY_MAX_WORDS = 0  # no summary field in Agent 18


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
        "step", "solution", "given", "find", "ncert", "context",
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
    sec = coach.get("sections")
    return sec if isinstance(sec, list) else []


def _section_map(coach: Optional[dict]) -> dict[str, str]:
    m = {}
    for sec in _sections(coach):
        if isinstance(sec, dict):
            h = str(sec.get("heading", "")).strip()
            b = str(sec.get("bodyMarkdown", "")).strip()
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


def _has_latex(text: str) -> bool:
    return any(re.search(p, text or "") for p in LATEX_ALLOWED_PATTERNS)


def _bad_latex(text: str) -> list[str]:
    issues = []
    if text.count("$") % 2 != 0:
        issues.append("unbalanced_dollar_math")
    if text.count("\\[") != text.count("\\]"):
        issues.append("unbalanced_display_math")
    if text.count("\\(") != text.count("\\)"):
        issues.append("unbalanced_inline_math")
    # Common bad escaped unicode issue is not checked; keep format permissive.
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
        return {"key": "schema_validity", "score": 0.0, "comment": f"missing input key(s): {sorted(missing_inputs)}"}

    out = _safe_get_outputs(run)
    if out is None:
        return {"key": "schema_validity", "score": 0.0, "comment": "outputs missing or not JSON object"}

    present = set(out.keys())
    if present != REQUIRED_OUTPUT_KEYS:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"output key mismatch -- missing={sorted(REQUIRED_OUTPUT_KEYS-present)} extra={sorted(present-REQUIRED_OUTPUT_KEYS)}",
        }

    ok, coach, raw = _parse_coach(out.get("coach_json"))
    if not ok:
        return {"key": "schema_validity", "score": 0.0, "comment": f"coach_json is not clean JSON object; sample={raw[:120]!r}"}

    missing = REQUIRED_TOP_KEYS - set(coach.keys())
    if missing:
        return {"key": "schema_validity", "score": 0.0, "comment": f"coach_json missing keys: {sorted(missing)}"}

    if not isinstance(coach.get("title"), str) or not coach["title"].strip():
        return {"key": "schema_validity", "score": 0.0, "comment": "title must be non-empty string"}

    if coach.get("revealLevel") != "full":
        return {"key": "schema_validity", "score": 0.0, "comment": f"revealLevel must be 'full', got {coach.get('revealLevel')!r}"}

    if not isinstance(coach.get("finalAnswer"), str) or not coach["finalAnswer"].strip():
        return {"key": "schema_validity", "score": 0.0, "comment": "finalAnswer must be non-empty string"}

    sections = coach.get("sections")
    if not isinstance(sections, list) or len(sections) != 8:
        return {"key": "schema_validity", "score": 0.0, "comment": "sections must be list of exactly 8 items"}

    headings = []
    for idx, sec in enumerate(sections):
        if not isinstance(sec, dict):
            return {"key": "schema_validity", "score": 0.0, "comment": f"section {idx} is not object"}
        if set(sec.keys()) != {"heading", "bodyMarkdown"}:
            return {"key": "schema_validity", "score": 0.0, "comment": f"section {idx} must have heading/bodyMarkdown only"}
        if not isinstance(sec.get("heading"), str) or not sec["heading"].strip():
            return {"key": "schema_validity", "score": 0.0, "comment": f"section {idx}.heading empty"}
        if not isinstance(sec.get("bodyMarkdown"), str) or not sec["bodyMarkdown"].strip():
            return {"key": "schema_validity", "score": 0.0, "comment": f"section {idx}.bodyMarkdown empty"}
        headings.append(sec["heading"])

    if headings != REQUIRED_HEADINGS:
        return {"key": "schema_validity", "score": 0.0, "comment": f"section headings/order mismatch: {headings}"}

    buttons = coach.get("followUpButtons")
    if not isinstance(buttons, list) or len(buttons) != 5:
        return {"key": "schema_validity", "score": 0.0, "comment": "followUpButtons must contain exactly 5 buttons"}
    actions = set()
    for idx, b in enumerate(buttons):
        if not isinstance(b, dict) or not isinstance(b.get("label"), str) or not isinstance(b.get("action"), str):
            return {"key": "schema_validity", "score": 0.0, "comment": f"button {idx} invalid"}
        actions.add(b["action"])
    if actions != REQUIRED_ACTIONS:
        return {"key": "schema_validity", "score": 0.0, "comment": f"followUp action set mismatch: {sorted(actions)}"}

    text = _flatten_coach_text(coach)
    if _contains_any(text, BANNED_PATTERNS | INTERNAL_LEAKS):
        return {"key": "schema_validity", "score": 0.0, "comment": "coach_json contains banned/internal phrase"}

    return {"key": "schema_validity", "score": 1.0, "comment": "schema valid"}


# ---------------------------------------------------------------------------
# Evaluator 2: section_completeness
# ---------------------------------------------------------------------------

def section_completeness(run, example) -> dict:
    coach = _get_coach(_safe_get_outputs(run))
    if coach is None:
        return {"key": "section_completeness", "score": 0.0, "comment": "coach_json missing/malformed", "hard_rule_violated": False}

    sec = _section_map(coach)
    issues = []
    for heading in REQUIRED_HEADINGS:
        body = sec.get(heading, "")
        wc = _word_count(body)
        if wc < SECTION_MIN_WORDS[heading]:
            issues.append(f"{heading}:too_short_{wc}_words")

    step_text = sec.get("Step-by-step Solution", "")
    if len(re.findall(r"(^|\n)\s*(?:\d+\.|-|\*)\s+", step_text)) < 2 and _word_count(step_text) < 45:
        issues.append("step_by_step_not_really_stepwise")

    final_section = sec.get("Final Answer", "")
    final_answer_value = str(coach.get("finalAnswer", ""))
    final_nums = _extract_numbers_units(final_answer_value)
    section_nums = _extract_numbers_units(final_section)
    numeric_reflected = bool(final_nums and section_nums and any(a in b or b in a for a in final_nums for b in section_nums))
    if _jaccard(final_section, final_answer_value) < 0.15 and _norm(final_answer_value) not in _norm(final_section) and not numeric_reflected:
        issues.append("finalAnswer_not_reflected_in_Final_Answer_section")

    if issues:
        hard = any("too_short" in x and ("Step-by-step" in x or "Final Answer" in x) for x in issues)
        return {
            "key": "section_completeness",
            "score": 0.0 if hard else 0.5,
            "comment": "; ".join(issues[:10]),
            "hard_rule_violated": hard,
        }

    return {"key": "section_completeness", "score": 1.0, "comment": "all eight sections are substantive", "hard_rule_violated": False}


# ---------------------------------------------------------------------------
# Evaluator 3: final_answer_consistency
# ---------------------------------------------------------------------------

def final_answer_consistency(run, example) -> dict:
    coach = _get_coach(_safe_get_outputs(run))
    ref = _safe_get_reference(example)
    inputs = _safe_get_inputs(example)

    if coach is None:
        return {"key": "final_answer_consistency", "score": 0.0, "comment": "coach_json missing/malformed", "hard_rule_violated": False}

    final = _final_answer_text(coach)
    gold = _gold_final_answer(ref)
    expert = _expert_final_answer(inputs)

    sec = _section_map(coach)
    final_section = sec.get("Final Answer", "")

    issues = []
    hard = False

    if not final.strip():
        issues.append("missing_finalAnswer")
        hard = True

    if _jaccard(final, final_section) < 0.12 and _norm(final) not in _norm(final_section):
        issues.append("finalAnswer_not_consistent_with_final_section")
        hard = True

    # Numeric answer agreement when gold/expert exists.
    final_vals = _extract_numbers_units(final)
    gold_vals = _extract_numbers_units(gold)
    expert_vals = _extract_numbers_units(expert)

    reference_vals = gold_vals or expert_vals
    if reference_vals and final_vals:
        if not any(rv in fv or fv in rv for rv in reference_vals for fv in final_vals):
            issues.append(f"numeric_final_answer_mismatch:pred={sorted(final_vals)[:4]},ref={sorted(reference_vals)[:4]}")
            hard = True
    elif gold and _jaccard(final, gold) < 0.12:
        issues.append("finalAnswer_low_gold_overlap")

    if hard:
        return {"key": "final_answer_consistency", "score": 0.0, "comment": "; ".join(issues), "hard_rule_violated": True}

    if issues:
        return {"key": "final_answer_consistency", "score": 0.5, "comment": "; ".join(issues), "hard_rule_violated": False}

    return {"key": "final_answer_consistency", "score": 1.0, "comment": "final answer is consistent", "hard_rule_violated": False}


# ---------------------------------------------------------------------------
# Evaluator 4: ncert_and_dependency_alignment_code
# ---------------------------------------------------------------------------

def ncert_and_dependency_alignment_code(run, example) -> dict:
    coach = _get_coach(_safe_get_outputs(run))
    ref = _safe_get_reference(example)
    inputs = _safe_get_inputs(example)

    if coach is None:
        return {"key": "ncert_and_dependency_alignment_code", "score": 0.0, "comment": "coach_json missing/malformed", "hard_rule_violated": False}

    problem = str(inputs.get("problem_text_normalized", ""))
    context = str(inputs.get("ncert_context", ""))
    dna = inputs.get("problem_dna") if isinstance(inputs.get("problem_dna"), dict) else {}
    gold = _get_gold_coach(ref)
    gold_text = _flatten_coach_text(gold)
    text = _flatten_coach_text(coach)

    issues = []
    hard = False

    # Must be connected to the actual problem.
    if _jaccard(text, problem) < 0.08 and _jaccard(text, gold_text) < 0.15:
        issues.append("weak_problem_alignment")

    # If NCERT context exists, concept/formula sections should overlap with it.
    sec = _section_map(coach)
    concept_formula = sec.get("Concept Needed", "") + " " + sec.get("Formula/Principle", "")
    if context.strip():
        cf_overlap = _jaccard(concept_formula, context)
        total_overlap = _jaccard(text, context)
        if cf_overlap < 0.08 and total_overlap < 0.10 and not gold_text:
            issues.append(f"weak_ncert_context_alignment:cf={cf_overlap:.2f},total={total_overlap:.2f}")

    # Optional DNA dependency: chapter/concepts should be reflected when present.
    if dna:
        dna_terms = " ".join([
            str(dna.get("chapter", "")),
            " ".join(dna.get("conceptTags", [])) if isinstance(dna.get("conceptTags"), list) else "",
        ])
        if dna_terms.strip() and _jaccard(text, dna_terms) < 0.06:
            issues.append("weak_problem_dna_term_alignment")

        expert = dna.get("expert_solution_internal")
        if isinstance(expert, dict):
            expert_text = " ".join([
                str(expert.get("final_answer", "")),
                " ".join(expert.get("key_steps", [])) if isinstance(expert.get("key_steps"), list) else "",
                str(expert.get("method_name", "")),
            ])
            if expert_text.strip() and _jaccard(text, expert_text) < 0.08:
                coach_nums = _extract_numbers_units(text)
                expert_nums = _extract_numbers_units(expert_text)
                numeric_aligned = bool(coach_nums and expert_nums and any(a in b or b in a for a in coach_nums for b in expert_nums))
                if not numeric_aligned:
                    issues.append("weak_expert_solution_alignment")

    # Formula hallucination guard: if answer introduces formulas, at least some should be in context/gold/problem.
    formulas = _formula_like(text)
    allowed_formula_text = " ".join([problem, context, gold_text])
    if formulas and _formula_like(allowed_formula_text):
        unsupported = [f for f in formulas if not any(_jaccard(f, af) >= 0.25 or f in af or af in f for af in _formula_like(allowed_formula_text))]
        if len(unsupported) >= 3:
            issues.append(f"unsupported_formula_like_content:{unsupported[:3]}")
            hard = True

    if hard:
        return {"key": "ncert_and_dependency_alignment_code", "score": 0.0, "comment": "; ".join(issues), "hard_rule_violated": True}
    if issues:
        return {"key": "ncert_and_dependency_alignment_code", "score": 0.5, "comment": "; ".join(issues), "hard_rule_violated": False}

    return {"key": "ncert_and_dependency_alignment_code", "score": 1.0, "comment": "NCERT/dependency alignment checks passed", "hard_rule_violated": False}


# ---------------------------------------------------------------------------
# Evaluator 5: latex_and_variation_behavior
# ---------------------------------------------------------------------------

def latex_and_variation_behavior(run, example) -> dict:
    coach = _get_coach(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)
    variation = _safe_get_variation(example)

    if coach is None:
        return {"key": "latex_and_variation_behavior", "score": 0.0, "comment": "coach_json missing/malformed"}

    text = _flatten_coach_text(coach)
    problem = str(inputs.get("problem_text_normalized", ""))
    sec = _section_map(coach)
    issues = []

    latex_issues = _bad_latex(text)
    issues.extend(latex_issues)

    problem_has_math = bool(re.search(r"\\\(|\\\[|[$=^_]|[ρΔθΩμ]|\\frac|\d+\s*(?:Ω|V|A|m/s|mol|cm|kg|J|N|pm)", problem))
    if problem_has_math and not (_has_latex(text) or _formula_like(text)):
        issues.append("math_problem_but_no_latex_or_formula_formatting")

    exp = VARIATION_EXPECTATIONS.get(variation, {})
    if exp.get("expects_steps") and _word_count(sec.get("Step-by-step Solution", "")) < 35:
        issues.append("variation_expects_steps_but_solution_too_short")
    if exp.get("expects_formula") and not _formula_like(sec.get("Formula/Principle", "") + " " + sec.get("Step-by-step Solution", "")):
        issues.append("variation_expects_formula_but_formula_missing")
    if exp.get("expects_derivation") and not _contains_any(text, {"derive", "therefore", "hence", "show that", "prove"}):
        issues.append("proof_variation_missing_derivation_language")
    if exp.get("expects_diagram_awareness") and not _contains_any(text, {"diagram", "figure", "graph", "ray", "shown"}):
        issues.append("diagram_variation_missing_diagram_awareness")
    if exp.get("expects_option") and not re.search(r"\b(option|correct answer|choice)\b", text, flags=re.IGNORECASE):
        issues.append("mcq_variation_missing_option_language")
    if exp.get("expects_concept") and _word_count(sec.get("Concept Needed", "")) < 15:
        issues.append("conceptual_variation_concept_section_thin")

    if issues:
        hard = any(x in {"unbalanced_dollar_math", "unbalanced_display_math", "unbalanced_inline_math"} for x in issues)
        return {"key": "latex_and_variation_behavior", "score": 0.0 if hard else 0.5, "comment": "; ".join(issues[:8])}

    return {"key": "latex_and_variation_behavior", "score": 1.0, "comment": "LaTeX and variation behavior checks passed"}


# ---------------------------------------------------------------------------
# Evaluator 6: required_llm_explain_basics_judge
# ---------------------------------------------------------------------------

def make_required_llm_explain_basics_judge(judge_llm: Callable[[str], str]):
    def required_llm_explain_basics_judge(run, example) -> dict:
        coach = _get_coach(_safe_get_outputs(run))
        ref = _safe_get_reference(example)
        inputs = _safe_get_inputs(example)

        if coach is None:
            return {
                "key": "required_llm_explain_basics_judge",
                "score": 0.0,
                "comment": "coach_json missing/malformed",
                "hard_rule_violated": True,
                "judge_available": False,
            }

        gold = _get_gold_coach(ref)
        prompt = f"""
You are evaluating ScholarSync's Explain From Basics Coach for Indian Class 11-12/JEE/NEET/CBSE problem solving.

Evaluate the candidate answer ONLY against:
- the problem,
- NCERT context,
- optional Problem DNA / expert solution,
- gold/reference answer if provided.

Return ONLY valid JSON:
{{
  "solution_correctness_score": <0.0 to 1.0>,
  "ncert_alignment_score": <0.0 to 1.0>,
  "beginner_pedagogy_score": <0.0 to 1.0>,
  "format_compliance_score": <0.0 to 1.0>,
  "comment": "<short reason, max 45 words>"
}}

Scoring guidance:
- solution_correctness_score: steps and final answer are correct.
- ncert_alignment_score: facts/formulas/principles are grounded in NCERT context or gold.
- beginner_pedagogy_score: starts from basics, explains givens, concept, formula, steps, and learning clearly.
- format_compliance_score: follows 8 sections, full reveal, readable Markdown/LaTeX.

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
                "key": "required_llm_explain_basics_judge",
                "score": 0.0,
                "comment": f"judge call failed: {exc}",
                "hard_rule_violated": True,
                "judge_available": False,
            }

        parsed = _json_from_text(raw)
        if not parsed:
            return {
                "key": "required_llm_explain_basics_judge",
                "score": 0.0,
                "comment": f"judge returned invalid JSON: {str(raw)[:160]}",
                "hard_rule_violated": True,
                "judge_available": False,
            }

        sol = _coerce_score(parsed.get("solution_correctness_score"))
        ncert = _coerce_score(parsed.get("ncert_alignment_score"))
        pedagogy = _coerce_score(parsed.get("beginner_pedagogy_score"))
        fmt = _coerce_score(parsed.get("format_compliance_score"))
        comment = str(parsed.get("comment", "")).strip()

        score = round((0.40 * sol) + (0.25 * ncert) + (0.25 * pedagogy) + (0.10 * fmt), 3)
        hard = sol < 0.65 or ncert < 0.60 or fmt < 0.70

        return {
            "key": "required_llm_explain_basics_judge",
            "score": score,
            "comment": f"solution={sol:.2f} ncert={ncert:.2f} pedagogy={pedagogy:.2f} format={fmt:.2f} | {comment}",
            "solution_correctness_score": sol,
            "ncert_alignment_score": ncert,
            "beginner_pedagogy_score": pedagogy,
            "format_compliance_score": fmt,
            "hard_rule_violated": hard,
            "judge_available": True,
        }

    return required_llm_explain_basics_judge


def build_per_example_evaluators(judge_llm: Callable[[str], str]) -> list[Callable]:
    if judge_llm is None or not callable(judge_llm):
        raise ValueError("Agent 18 evaluation requires judge_llm. Use build_per_example_evaluators(judge_llm).")
    return [
        schema_validity,
        section_completeness,
        final_answer_consistency,
        ncert_and_dependency_alignment_code,
        latex_and_variation_behavior,
        make_required_llm_explain_basics_judge(judge_llm),
    ]


# ---------------------------------------------------------------------------
# Summary evaluator
# ---------------------------------------------------------------------------

def explain_from_basics_severity_summary(runs: list, examples: list) -> dict:
    if len(runs) != len(examples):
        return {
            "key": "explain_from_basics_severity_summary",
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

        completeness = section_completeness(run, example)
        final = final_answer_consistency(run, example)
        align = ncert_and_dependency_alignment_code(run, example)
        latex = latex_and_variation_behavior(run, example)
        llm = _extract_required_llm_feedback(run)

        for result in (completeness, final, align):
            if result.get("hard_rule_violated"):
                tier_0.append({"example_id": getattr(example, "id", None), "reason": f"{result['key']} hard failure: {result['comment']}"})

        if latex["score"] == 0.0:
            tier_0.append({"example_id": getattr(example, "id", None), "reason": f"latex_and_variation_behavior failed: {latex['comment']}"})

        if llm is not None:
            if llm.get("hard_rule_violated") or llm.get("score", 0.0) < 0.68:
                tier_0.append({"example_id": getattr(example, "id", None), "reason": f"LLM judge hard failure: {llm.get('comment', '')}"})
            elif llm.get("score", 1.0) < 0.82:
                tier_1 += 1
                tier_1_applicable += 1

        tier_1_applicable += 5
        for result in (completeness, final, align, latex):
            if result["score"] < 1.0:
                tier_1 += 1

        llm_ok = True if llm is None else llm.get("score", 0.0) >= 0.82
        if completeness["score"] == final["score"] == align["score"] == latex["score"] == 1.0 and llm_ok:
            variation_passes[variation] = variation_passes.get(variation, 0) + 1

    tier_1_rate = tier_1 / tier_1_applicable if tier_1_applicable else 0.0
    per_variation = {v: round(variation_passes.get(v, 0) / total, 3) for v, total in variation_totals.items()}

    recommendation = "BLOCK" if tier_0 else ("REVIEW" if tier_1_rate > 0.15 else "OK")

    return {
        "key": "explain_from_basics_severity_summary",
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
            if val.get("key") == "required_llm_explain_basics_judge":
                return val
            maybe = val.get("required_llm_explain_basics_judge")
            if isinstance(maybe, dict):
                return maybe
            if isinstance(maybe, (int, float)):
                return {
                    "key": "required_llm_explain_basics_judge",
                    "score": float(maybe),
                    "comment": "score extracted from run feedback mapping",
                    "hard_rule_violated": float(maybe) < 0.68,
                }
        if isinstance(val, list):
            for item in val:
                if isinstance(item, dict) and item.get("key") == "required_llm_explain_basics_judge":
                    return item
    return None


PER_EXAMPLE_EVALUATORS_CODE_ONLY = [
    schema_validity,
    section_completeness,
    final_answer_consistency,
    ncert_and_dependency_alignment_code,
    latex_and_variation_behavior,
]

PER_EXAMPLE_EVALUATORS = None

SUMMARY_EVALUATORS = [explain_from_basics_severity_summary]
