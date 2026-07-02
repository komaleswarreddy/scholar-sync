"""
problem_dna_analyzer_evaluators.py

LangSmith custom evaluators for Agent 17: Problem DNA Analyzer.

Agent role:
- Mandatory first step in Problem Solver.
- Produces dna_json used by Agents 18-22.
- Because this is Tier 1 and expert_solution_internal can poison every coach,
  the main evaluator bundle is hybrid by default: deterministic gates + required
  LLM semantic judge.

Use:
    from problem_dna_analyzer_evaluators import build_per_example_evaluators, SUMMARY_EVALUATORS
    evaluators = build_per_example_evaluators(judge_llm)

judge_llm(prompt: str) -> str must return JSON:
{
  "classification_score": 0.0-1.0,
  "expert_solution_score": 0.0-1.0,
  "summary_safety_score": 0.0-1.0,
  "difficulty_time_score": 0.0-1.0,
  "comment": "short reason"
}
"""

from __future__ import annotations

import json
import math
import re
from typing import Any, Callable, Optional

REQUIRED_INPUT_KEYS = {"problem_text_normalized", "ncert_context", "class_num", "subject_labels"}
REQUIRED_OUTPUT_KEYS = {"dna_json"}
DNA_REQUIRED_KEYS = {
    "subject", "chapter", "conceptTags", "difficulty", "expectedTimeMinutes",
    "questionType", "examSkill", "confidence", "problem_dna_summary",
    "expert_solution_internal",
}
EXPERT_REQUIRED_KEYS = {"final_answer", "key_steps", "method_name"}
VALID_DIFFICULTIES = {"Easy", "Medium", "Hard", "Unknown"}
VALID_QUESTION_TYPES = {"Numerical", "Conceptual", "Diagram", "Proof", "MCQ", "Mixed"}
VALID_SUBJECTS = {"Physics", "Chemistry", "Biology", "Mathematics", "Maths", "Science", "Unknown"}
SUMMARY_MAX_WORDS = 35

SUBJECT_CANONICAL = {"math": "mathematics", "maths": "mathematics"}
SUBJECT_KEY_HINTS = {
    "physics": {"velocity", "acceleration", "force", "mass", "work", "energy", "power", "current", "voltage", "resistance", "ohm", "charge", "electric", "magnetic", "lens", "mirror", "ray", "optics", "torque", "momentum", "joule", "newton", "coulomb", "ampere", "volt", "kg", "m/s"},
    "chemistry": {"mole", "molar", "equilibrium", "acid", "base", "ph", "reaction", "oxidation", "reduction", "electrode", "emf", "cell potential", "coordination", "ligand", "compound", "benzene", "alkane", "alkene", "bond", "hybridisation", "faraday", "nernst"},
    "biology": {"dna", "rna", "gene", "protein", "enzyme", "cell", "mitosis", "meiosis", "photosynthesis", "respiration", "species", "biodiversity", "tissue", "xylem", "phloem", "root", "stem", "leaf", "organism", "prokaryote", "translation", "transcription"},
    "mathematics": {"integral", "differentiate", "derivative", "equation", "probability", "matrix", "determinant", "vector", "line", "plane", "parabola", "ellipse", "hyperbola", "binomial", "inequality", "prove", "theorem", "function", "limit"},
}
QUESTION_TYPE_HINTS = {
    "Numerical": {"calculate", "find", "determine", "value", "unit", "given", "if", "ohm", "volt", "ampere", "cm", "kg", "mol"},
    "Conceptual": {"explain", "why", "reason", "concept", "describe", "meaning", "state"},
    "Diagram": {"diagram", "graph", "ray diagram", "bar graph", "figure", "shown below", "labelled", "image", "chart"},
    "Proof": {"prove", "show that", "derive", "hence prove", "deduce"},
    "MCQ": {"choose", "which of the following", "assertion", "reason", "option", "(a)", "(b)", "(c)", "(d)"},
}
TIME_BANDS = {"Easy": (1, 5), "Medium": (4, 15), "Hard": (8, 35), "Unknown": (1, 30)}
BANNED_PATTERNS = {"as an ai language model", "i cannot access", "i don't have access", "not enough context"}


def _safe_get_outputs(run) -> Optional[dict]:
    try:
        return run.outputs if isinstance(run.outputs, dict) else None
    except Exception:
        return None


def _safe_get_inputs(example) -> dict:
    try:
        return example.inputs if isinstance(example.inputs, dict) else {}
    except Exception:
        return {}


def _safe_get_reference(example) -> Optional[dict]:
    try:
        return example.outputs if isinstance(example.outputs, dict) else None
    except Exception:
        return None


def _safe_get_metadata(example) -> dict:
    try:
        return example.metadata if isinstance(example.metadata, dict) else {}
    except Exception:
        return {}


def _safe_get_variation(example) -> str:
    return str(_safe_get_metadata(example).get("variation", "unknown"))


def _norm(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9Ωμ°/+=∩∪^²³().-]+", _norm(text)))


def _content_tokens(text: str) -> set[str]:
    stop = {"the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with", "is", "are", "was", "were", "be", "this", "that", "it", "as", "by", "from", "problem", "question", "answer", "find", "calculate", "given", "class", "ncert", "context"}
    return {t for t in _tokens(text) if len(t) > 2 and t not in stop}


def _jaccard(a: str, b: str) -> float:
    ta, tb = _content_tokens(a), _content_tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _contains_any(text: str, needles) -> bool:
    t = _norm(text)
    return any(_norm(n) in t for n in needles)


def _canonical_subject(s: str) -> str:
    n = _norm(s)
    return SUBJECT_CANONICAL.get(n, n)


def _parse_dna(value: Any) -> tuple[bool, Optional[dict], str]:
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


def _get_dna(out: Optional[dict]) -> Optional[dict]:
    if not isinstance(out, dict):
        return None
    ok, parsed, _ = _parse_dna(out.get("dna_json"))
    return parsed if ok else None


def _get_gold_dna(ref: Optional[dict]) -> Optional[dict]:
    if not isinstance(ref, dict):
        return None
    ok, parsed, _ = _parse_dna(ref.get("dna_json"))
    return parsed if ok else None


def _flatten_dna_text(dna: Optional[dict]) -> str:
    try:
        return json.dumps(dna or {}, ensure_ascii=False)
    except Exception:
        return str(dna)


def _extract_numbers_and_units(text: str) -> set[str]:
    vals = set()
    for m in re.findall(r"[-+]?\d+(?:\.\d+)?(?:\s*[×x]\s*10\^?[-+]?\d+)?\s*(?:[a-zA-ZΩμ°/%²³^-]+)?", text or ""):
        m = re.sub(r"\s+", " ", m.strip())
        if m:
            vals.add(_norm(m))
    return vals


def _infer_subject_from_problem(problem: str, labels: Any = None) -> Optional[str]:
    p = _norm(problem)
    scores = {subj: sum(1 for h in hints if _norm(h) in p) for subj, hints in SUBJECT_KEY_HINTS.items()}
    best_subj, best_score = max(scores.items(), key=lambda kv: kv[1])
    if best_score <= 0:
        return None
    if isinstance(labels, list):
        label_subjects = {_canonical_subject(str(x)) for x in labels}
    elif isinstance(labels, str):
        label_subjects = {_canonical_subject(x) for x in re.split(r"[,;/|]", labels)}
    else:
        label_subjects = set()
    if label_subjects and best_subj not in label_subjects and best_score < 2:
        return None
    return best_subj


def _infer_question_type(problem: str) -> Optional[str]:
    p = _norm(problem)
    scores = {qt: sum(1 for h in hints if _norm(h) in p) for qt, hints in QUESTION_TYPE_HINTS.items()}
    if scores.get("Diagram", 0) > 0:
        return "Diagram"
    if scores.get("MCQ", 0) > 0:
        return "MCQ"
    if scores.get("Proof", 0) > 0:
        return "Proof"
    if scores.get("Numerical", 0) >= 2:
        return "Numerical"
    if scores.get("Conceptual", 0) > 0:
        return "Conceptual"
    return None


def _expected_difficulty(problem: str, variation: str) -> Optional[str]:
    wc = _word_count(problem)
    p = _norm(problem)
    if variation in {"jee", "proof", "multi_part"}:
        return "Hard"
    if variation in {"neet", "case_study"}:
        return "Medium"
    if "derive" in p or "prove" in p:
        return "Hard"
    if wc >= 70:
        return "Medium"
    if _infer_question_type(problem) == "Numerical" and len(_extract_numbers_and_units(problem)) >= 3:
        return "Medium"
    return None


def _difficulty_close(pred: str, expected: str) -> bool:
    order = {"Easy": 0, "Medium": 1, "Hard": 2, "Unknown": 1}
    return abs(order.get(pred, 1) - order.get(expected, 1)) <= 1


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
        if "dna_json" in parsed:
            ok, dna, _ = _parse_dna(parsed.get("dna_json"))
            return {"dna_json": dna if ok else parsed.get("dna_json")}
        return {"dna_json": parsed}
    return {}


# ---------------------------------------------------------------------------
# Per-example evaluators
# ---------------------------------------------------------------------------

def schema_validity(run, example) -> dict:
    inputs = _safe_get_inputs(example)
    missing_inputs = REQUIRED_INPUT_KEYS - set(inputs.keys())
    if missing_inputs:
        return {"key": "schema_validity", "score": 0.0, "comment": f"missing required input key(s): {sorted(missing_inputs)}"}

    out = _safe_get_outputs(run)
    if out is None:
        return {"key": "schema_validity", "score": 0.0, "comment": "outputs missing or not a JSON object"}
    if set(out.keys()) != REQUIRED_OUTPUT_KEYS:
        return {"key": "schema_validity", "score": 0.0, "comment": f"output key mismatch: got={sorted(out.keys())}"}

    ok, dna, raw = _parse_dna(out.get("dna_json"))
    if not ok:
        return {"key": "schema_validity", "score": 0.0, "comment": f"dna_json is not clean JSON object; sample={raw[:120]!r}"}

    missing = DNA_REQUIRED_KEYS - set(dna.keys())
    if missing:
        return {"key": "schema_validity", "score": 0.0, "comment": f"dna_json missing keys: {sorted(missing)}"}

    for key in ["subject", "chapter", "examSkill", "problem_dna_summary"]:
        if not isinstance(dna.get(key), str) or not dna[key].strip():
            return {"key": "schema_validity", "score": 0.0, "comment": f"{key} must be non-empty string"}

    if not isinstance(dna.get("conceptTags"), list) or not dna["conceptTags"] or not all(isinstance(x, str) and x.strip() for x in dna["conceptTags"]):
        return {"key": "schema_validity", "score": 0.0, "comment": "conceptTags must be non-empty list[str]"}
    if dna.get("difficulty") not in VALID_DIFFICULTIES:
        return {"key": "schema_validity", "score": 0.0, "comment": f"invalid difficulty={dna.get('difficulty')!r}"}
    if dna.get("questionType") not in VALID_QUESTION_TYPES:
        return {"key": "schema_validity", "score": 0.0, "comment": f"invalid questionType={dna.get('questionType')!r}"}
    if isinstance(dna.get("expectedTimeMinutes"), bool) or not isinstance(dna.get("expectedTimeMinutes"), int):
        return {"key": "schema_validity", "score": 0.0, "comment": "expectedTimeMinutes must be int"}
    conf = dna.get("confidence")
    if isinstance(conf, bool) or not isinstance(conf, (int, float)) or not 0 <= float(conf) <= 1:
        return {"key": "schema_validity", "score": 0.0, "comment": "confidence must be number in [0,1]"}
    if _word_count(dna.get("problem_dna_summary", "")) > SUMMARY_MAX_WORDS:
        return {"key": "schema_validity", "score": 0.0, "comment": "problem_dna_summary too long"}

    expert = dna.get("expert_solution_internal")
    if not isinstance(expert, dict):
        return {"key": "schema_validity", "score": 0.0, "comment": "expert_solution_internal must be object"}
    missing_expert = EXPERT_REQUIRED_KEYS - set(expert.keys())
    if missing_expert:
        return {"key": "schema_validity", "score": 0.0, "comment": f"expert_solution_internal missing keys: {sorted(missing_expert)}"}
    if not isinstance(expert.get("final_answer"), str) or not expert["final_answer"].strip():
        return {"key": "schema_validity", "score": 0.0, "comment": "expert final_answer must be non-empty string"}
    if not isinstance(expert.get("key_steps"), list) or not expert["key_steps"] or not all(isinstance(x, str) and x.strip() for x in expert["key_steps"]):
        return {"key": "schema_validity", "score": 0.0, "comment": "expert key_steps must be non-empty list[str]"}
    if not isinstance(expert.get("method_name"), str) or not expert["method_name"].strip():
        return {"key": "schema_validity", "score": 0.0, "comment": "expert method_name must be non-empty string"}
    if _contains_any(_flatten_dna_text(dna), BANNED_PATTERNS):
        return {"key": "schema_validity", "score": 0.0, "comment": "contains banned refusal/self-reference pattern"}
    return {"key": "schema_validity", "score": 1.0, "comment": "schema valid"}


def classification_match(run, example) -> dict:
    dna = _get_dna(_safe_get_outputs(run))
    gold = _get_gold_dna(_safe_get_reference(example))
    inputs = _safe_get_inputs(example)
    if dna is None or gold is None:
        return {"key": "classification_match", "score": 0.0, "comment": "dna/gold missing", "hard_rule_violated": False}

    issues, hard = [], False
    pred_subject = _canonical_subject(dna.get("subject", ""))
    gold_subject = _canonical_subject(gold.get("subject", ""))
    if pred_subject != gold_subject:
        issues.append(f"subject_mismatch pred={dna.get('subject')!r} gold={gold.get('subject')!r}")
        hard = True

    inferred = _infer_subject_from_problem(str(inputs.get("problem_text_normalized", "")), inputs.get("subject_labels"))
    if inferred and pred_subject != inferred:
        issues.append(f"subject_conflicts_with_problem_content pred={pred_subject} inferred={inferred}")
        hard = True

    chapter_overlap = _jaccard(str(dna.get("chapter", "")), str(gold.get("chapter", "")))
    if _norm(dna.get("chapter", "")) != _norm(gold.get("chapter", "")) and chapter_overlap < 0.35:
        issues.append(f"chapter_low_overlap={chapter_overlap:.2f}")

    concept_overlap = _jaccard(" ".join(dna.get("conceptTags", [])), " ".join(gold.get("conceptTags", [])))
    if concept_overlap < 0.18:
        issues.append(f"conceptTags_low_overlap={concept_overlap:.2f}")

    pred_qtype, gold_qtype = dna.get("questionType"), gold.get("questionType")
    if pred_qtype != gold_qtype and "Mixed" not in {pred_qtype, gold_qtype}:
        issues.append(f"questionType_mismatch pred={pred_qtype!r} gold={gold_qtype!r}")

    if hard:
        return {"key": "classification_match", "score": 0.0, "comment": "; ".join(issues), "hard_rule_violated": True}
    if issues:
        return {"key": "classification_match", "score": 0.5, "comment": "; ".join(issues), "hard_rule_violated": False}
    return {"key": "classification_match", "score": 1.0, "comment": f"classification matched; chapter_overlap={chapter_overlap:.2f} concept_overlap={concept_overlap:.2f}", "hard_rule_violated": False}


def no_answer_in_summary(run, example) -> dict:
    dna = _get_dna(_safe_get_outputs(run))
    gold = _get_gold_dna(_safe_get_reference(example))
    if dna is None:
        return {"key": "no_answer_in_summary", "score": 0.0, "comment": "dna missing", "hard_rule_violated": False}

    summary = str(dna.get("problem_dna_summary", ""))
    expert = dna.get("expert_solution_internal", {}) if isinstance(dna.get("expert_solution_internal"), dict) else {}
    final_answer = str(expert.get("final_answer", ""))
    gold_final = ""
    if isinstance(gold, dict) and isinstance(gold.get("expert_solution_internal"), dict):
        gold_final = str(gold["expert_solution_internal"].get("final_answer", ""))

    final_values = _extract_numbers_and_units(final_answer) | _extract_numbers_and_units(gold_final)
    leaked = []
    for val in final_values:
        if val and val not in {"1", "2", "3", "4", "5", "10"} and val in _norm(summary):
            leaked.append(val)
    if final_answer and _word_count(final_answer) <= 8 and _norm(final_answer) in _norm(summary):
        leaked.append(_norm(final_answer))

    if leaked:
        return {"key": "no_answer_in_summary", "score": 0.0, "comment": f"summary leaks final answer/value: {sorted(set(leaked))[:5]}", "hard_rule_violated": True}
    return {"key": "no_answer_in_summary", "score": 1.0, "comment": "summary does not leak final answer", "hard_rule_violated": False}


def difficulty_time_calibration(run, example) -> dict:
    dna = _get_dna(_safe_get_outputs(run))
    gold = _get_gold_dna(_safe_get_reference(example))
    inputs = _safe_get_inputs(example)
    variation = _safe_get_variation(example)
    if dna is None:
        return {"key": "difficulty_time_calibration", "score": 0.0, "comment": "dna missing"}

    issues = []
    difficulty = dna.get("difficulty")
    expected_time = dna.get("expectedTimeMinutes")
    if isinstance(gold, dict):
        gd = gold.get("difficulty")
        if gd in VALID_DIFFICULTIES and not _difficulty_close(difficulty, gd):
            issues.append(f"difficulty_far_from_gold pred={difficulty} gold={gd}")
        gt = gold.get("expectedTimeMinutes")
        if isinstance(gt, int) and isinstance(expected_time, int):
            if abs(expected_time - gt) > max(5, math.ceil(gt * 0.6)):
                issues.append(f"expected_time_far_from_gold pred={expected_time} gold={gt}")

    inferred = _expected_difficulty(str(inputs.get("problem_text_normalized", "")), variation)
    if inferred and not _difficulty_close(difficulty, inferred):
        issues.append(f"difficulty_conflicts_with_problem_shape pred={difficulty} expected~={inferred}")
    if isinstance(expected_time, int):
        lo, hi = TIME_BANDS.get(difficulty, (1, 30))
        if not lo <= expected_time <= hi:
            issues.append(f"time_outside_{difficulty}_band {expected_time} not {lo}-{hi}")

    if issues:
        hard = any(x.startswith(("difficulty_far", "time_outside")) for x in issues)
        return {"key": "difficulty_time_calibration", "score": 0.0 if hard else 0.5, "comment": "; ".join(issues)}
    return {"key": "difficulty_time_calibration", "score": 1.0, "comment": "difficulty/time calibration passed"}


def expert_solution_integrity_code(run, example) -> dict:
    dna = _get_dna(_safe_get_outputs(run))
    gold = _get_gold_dna(_safe_get_reference(example))
    inputs = _safe_get_inputs(example)
    if dna is None or not isinstance(dna.get("expert_solution_internal"), dict):
        return {"key": "expert_solution_integrity_code", "score": 0.0, "comment": "expert_solution_internal missing", "hard_rule_violated": False}

    expert = dna["expert_solution_internal"]
    final_answer = str(expert.get("final_answer", ""))
    key_steps = expert.get("key_steps", [])
    method = str(expert.get("method_name", ""))
    issues, hard = [], False
    if _word_count(final_answer) > 45:
        issues.append("final_answer_too_verbose")
    if not isinstance(key_steps, list) or len(key_steps) < 2:
        issues.append("too_few_key_steps")
        hard = True
    if _word_count(method) > 10:
        issues.append("method_name_too_verbose")

    problem = str(inputs.get("problem_text_normalized", ""))
    context = str(inputs.get("ncert_context", ""))
    solution_text = " ".join([final_answer, " ".join(map(str, key_steps)), method])
    rel_problem = _jaccard(solution_text, problem)
    rel_context = _jaccard(solution_text, context)
    if rel_problem < 0.05 and rel_context < 0.05:
        issues.append(f"solution_weakly_related_to_problem_context p={rel_problem:.2f} c={rel_context:.2f}")

    if isinstance(gold, dict) and isinstance(gold.get("expert_solution_internal"), dict):
        gold_final = str(gold["expert_solution_internal"].get("final_answer", ""))
        pred_vals = _extract_numbers_and_units(final_answer)
        gold_vals = _extract_numbers_and_units(gold_final)
        if pred_vals and gold_vals and not any(g in p or p in g for g in gold_vals for p in pred_vals):
            issues.append(f"final_answer_numeric_mismatch pred={sorted(pred_vals)[:4]} gold={sorted(gold_vals)[:4]}")
            hard = True
        elif gold_final and not pred_vals and not gold_vals and _jaccard(final_answer, gold_final) < 0.12:
            issues.append("final_answer_low_gold_overlap")

    if hard:
        return {"key": "expert_solution_integrity_code", "score": 0.0, "comment": "; ".join(issues), "hard_rule_violated": True}
    if issues:
        return {"key": "expert_solution_integrity_code", "score": 0.5, "comment": "; ".join(issues), "hard_rule_violated": False}
    return {"key": "expert_solution_integrity_code", "score": 1.0, "comment": "expert solution code checks passed", "hard_rule_violated": False}


def make_required_llm_dna_judge(judge_llm: Callable[[str], str]):
    def required_llm_dna_judge(run, example) -> dict:
        dna = _get_dna(_safe_get_outputs(run))
        gold = _get_gold_dna(_safe_get_reference(example))
        inputs = _safe_get_inputs(example)
        if dna is None:
            return {"key": "required_llm_dna_judge", "score": 0.0, "comment": "dna_json missing/malformed", "hard_rule_violated": True, "judge_available": False}

        prompt = f"""
You are evaluating ScholarSync's Problem DNA Analyzer for Class 11-12 Indian NCERT/JEE/NEET/CBSE problem solving.

Grade the candidate DNA using only the normalized problem, NCERT context if present, subject labels as allowed scope, and gold/reference DNA.
Return ONLY valid JSON with exactly these keys:
{{
  "classification_score": <0.0 to 1.0>,
  "expert_solution_score": <0.0 to 1.0>,
  "summary_safety_score": <0.0 to 1.0>,
  "difficulty_time_score": <0.0 to 1.0>,
  "comment": "<short reason, max 45 words>"
}}

Problem:
{inputs.get('problem_text_normalized', '')}

NCERT context:
{inputs.get('ncert_context', '')}

Class:
{inputs.get('class_num', '')}

Subject labels:
{inputs.get('subject_labels', '')}

Gold/reference DNA:
{json.dumps(gold, ensure_ascii=False) if gold else ''}

Candidate DNA:
{json.dumps(dna, ensure_ascii=False)}
""".strip()
        try:
            raw = judge_llm(prompt)
        except Exception as exc:
            return {"key": "required_llm_dna_judge", "score": 0.0, "comment": f"judge call failed: {exc}", "hard_rule_violated": True, "judge_available": False}
        parsed = _json_from_text(raw)
        if not parsed:
            return {"key": "required_llm_dna_judge", "score": 0.0, "comment": f"judge returned invalid JSON: {str(raw)[:160]}", "hard_rule_violated": True, "judge_available": False}

        classification = _coerce_score(parsed.get("classification_score"))
        expert = _coerce_score(parsed.get("expert_solution_score"))
        summary = _coerce_score(parsed.get("summary_safety_score"))
        difficulty = _coerce_score(parsed.get("difficulty_time_score"))
        score = round((0.35 * classification) + (0.35 * expert) + (0.15 * summary) + (0.15 * difficulty), 3)
        hard = classification < 0.65 or expert < 0.65 or summary < 0.75
        comment = str(parsed.get("comment", "")).strip()
        return {
            "key": "required_llm_dna_judge",
            "score": score,
            "comment": f"classification={classification:.2f} expert={expert:.2f} summary={summary:.2f} difficulty={difficulty:.2f} | {comment}",
            "classification_score": classification,
            "expert_solution_score": expert,
            "summary_safety_score": summary,
            "difficulty_time_score": difficulty,
            "hard_rule_violated": hard,
            "judge_available": True,
        }
    return required_llm_dna_judge


def build_per_example_evaluators(judge_llm: Callable[[str], str]) -> list[Callable]:
    if judge_llm is None or not callable(judge_llm):
        raise ValueError("Agent 17 evaluation requires judge_llm. Use build_per_example_evaluators(judge_llm).")
    return [
        schema_validity,
        classification_match,
        no_answer_in_summary,
        difficulty_time_calibration,
        expert_solution_integrity_code,
        make_required_llm_dna_judge(judge_llm),
    ]


def _extract_required_llm_feedback(run) -> Optional[dict]:
    for attr in ["feedback", "feedback_stats", "feedback_results", "evaluator_results"]:
        try:
            val = getattr(run, attr, None)
        except Exception:
            continue
        if isinstance(val, dict):
            if val.get("key") == "required_llm_dna_judge":
                return val
            maybe = val.get("required_llm_dna_judge")
            if isinstance(maybe, dict):
                return maybe
            if isinstance(maybe, (int, float)):
                return {"key": "required_llm_dna_judge", "score": float(maybe), "comment": "score from run feedback", "hard_rule_violated": float(maybe) < 0.65}
        if isinstance(val, list):
            for item in val:
                if isinstance(item, dict) and item.get("key") == "required_llm_dna_judge":
                    return item
    return None


def problem_dna_severity_summary(runs: list, examples: list) -> dict:
    if len(runs) != len(examples):
        return {"key": "problem_dna_severity_summary", "score": 0.0, "comment": f"runs/examples length mismatch ({len(runs)} vs {len(examples)})", "ship_recommendation": "BLOCK"}

    tier_0, tier_1, tier_1_applicable = [], 0, 0
    variation_totals, variation_passes = {}, {}

    for run, example in zip(runs, examples):
        variation = _safe_get_variation(example)
        variation_totals[variation] = variation_totals.get(variation, 0) + 1

        schema = schema_validity(run, example)
        if schema["score"] == 0.0:
            tier_0.append({"example_id": getattr(example, "id", None), "reason": f"schema_validity failed: {schema['comment']}"})
            continue

        classification = classification_match(run, example)
        leak = no_answer_in_summary(run, example)
        diff = difficulty_time_calibration(run, example)
        expert = expert_solution_integrity_code(run, example)
        llm_judge = _extract_required_llm_feedback(run)

        for result in (classification, leak, expert):
            if result.get("hard_rule_violated"):
                tier_0.append({"example_id": getattr(example, "id", None), "reason": f"{result['key']} hard failure: {result['comment']}"})
        if diff["score"] == 0.0:
            tier_0.append({"example_id": getattr(example, "id", None), "reason": f"difficulty_time_calibration failed: {diff['comment']}"})
        if llm_judge is not None:
            if llm_judge.get("hard_rule_violated") or llm_judge.get("score", 0.0) < 0.65:
                tier_0.append({"example_id": getattr(example, "id", None), "reason": f"LLM DNA judge hard failure: {llm_judge.get('comment', '')}"})
            elif llm_judge.get("score", 1.0) < 0.82:
                tier_1 += 1
                tier_1_applicable += 1

        tier_1_applicable += 4
        for result in (classification, leak, diff, expert):
            if result["score"] < 1.0:
                tier_1 += 1

        llm_ok = True if llm_judge is None else llm_judge.get("score", 0.0) >= 0.82
        if classification["score"] == leak["score"] == diff["score"] == expert["score"] == 1.0 and llm_ok:
            variation_passes[variation] = variation_passes.get(variation, 0) + 1

    tier_1_rate = tier_1 / tier_1_applicable if tier_1_applicable else 0.0
    per_variation_pass_rate = {v: round(variation_passes.get(v, 0) / total, 3) for v, total in variation_totals.items()}
    if tier_0:
        recommendation = "BLOCK"
    elif tier_1_rate > 0.15:
        recommendation = "REVIEW"
    else:
        recommendation = "OK"
    return {
        "key": "problem_dna_severity_summary",
        "score": 0.0 if tier_0 else round(1.0 - tier_1_rate, 3),
        "comment": f"ship_recommendation={recommendation} | tier_0_blocking_count={len(tier_0)} | tier_1_review_rate={tier_1_rate:.3f} | llm_judge_required_via_build_per_example_evaluators=True",
        "tier_0_blocking_count": len(tier_0),
        "tier_0_blocking_examples": tier_0,
        "tier_1_review_rate": round(tier_1_rate, 3),
        "per_variation_pass_rate": per_variation_pass_rate,
        "ship_recommendation": recommendation,
    }


PER_EXAMPLE_EVALUATORS_CODE_ONLY = [
    schema_validity,
    classification_match,
    no_answer_in_summary,
    difficulty_time_calibration,
    expert_solution_integrity_code,
]
PER_EXAMPLE_EVALUATORS = None
SUMMARY_EVALUATORS = [problem_dna_severity_summary]
