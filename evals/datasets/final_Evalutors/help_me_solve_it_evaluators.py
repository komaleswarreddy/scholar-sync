"""
help_me_solve_it_evaluators.py

LangSmith custom evaluators for Agent 21: Help Me Solve It Coach.

Agent role:
- One of the mutually exclusive Problem Solver coach modes after Agent 17.
- Interactive guided solving:
  - interaction_count = 0: initial hints + checkpoint 1 MCQ; no final answer.
  - interaction_count = 1: feedback on checkpoint 1 + checkpoint 2; no final answer.
  - interaction_count >= 2: final reveal with both checkpoint histories and full solution.
- Must preserve prior checkpoints and avoid premature answer leakage.

Production dependencies:
- Required dataset inputs:
    problem_text_normalized: str
    interaction_count: int
    ncert_context: str
    student_choice: optional str
- Optional runtime dependency inputs:
    prior_response: dict | str
    checkpoint_number: int | str
    problem_dna: dict
    expert_solution_internal: dict
- Output:
    coach_json: dict

Design choice:
- Hybrid by default.
- Code gates enforce branching, schema, checkpoint quality, no premature answer,
  cumulative context/history preservation, final reveal contract, LaTeX/unit hygiene.
- Required LLM judge evaluates the semantic quality of hints, checkpoint options,
  feedback, solution correctness, and NCERT alignment.
- Tier 1 because this is interactive and student-facing. The most critical failure
  is revealing the answer too early or losing checkpoint context.

LangSmith usage:
    from help_me_solve_it_evaluators import (
        build_per_example_evaluators,
        SUMMARY_EVALUATORS,
    )

    evaluators = build_per_example_evaluators(judge_llm)

Judge callable:
    judge_llm(prompt: str) -> str

Judge must return JSON:
{
  "guided_pedagogy_score": 0.0-1.0,
  "checkpoint_quality_score": 0.0-1.0,
  "branch_safety_score": 0.0-1.0,
  "solution_correctness_score": 0.0-1.0,
  "ncert_alignment_score": 0.0-1.0,
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

REQUIRED_INPUT_KEYS = {"problem_text_normalized", "interaction_count", "ncert_context"}
REQUIRED_OUTPUT_KEYS = {"coach_json"}

COMMON_REQUIRED_KEYS = {"interactionCount", "title", "sections", "revealLevel", "followUpButtons"}

COUNT0_REQUIRED_KEYS = COMMON_REQUIRED_KEYS | {"checkpoint", "checkpointHistory"}
COUNT1_REQUIRED_KEYS = COMMON_REQUIRED_KEYS | {"checkpoint", "checkpointHistory"}
COUNT2_REQUIRED_KEYS = COMMON_REQUIRED_KEYS | {"checkpointHistory", "finalAnswer"}

COUNT0_DISALLOWED_KEYS = {"finalAnswer"}
COUNT1_DISALLOWED_KEYS = {"finalAnswer"}
COUNT2_DISALLOWED_KEYS = {"checkpoint"}

COUNT0_HEADINGS = ["Problem decode", "Hint 1", "Hint 2"]
COUNT1_HEADINGS = ["Problem decode", "Hint 1", "Hint 2", "Feedback on your choice"]
COUNT2_MIN_HEADINGS = {
    "Problem decode",
    "Hint 1",
    "Hint 2",
    "Solution walkthrough",
}

COUNT2_FEEDBACK_HEADINGS = {"Feedback on checkpoint 1", "Feedback on checkpoint 2", "Feedback on your choice"}

FINAL_FOLLOWUP_ACTIONS = {
    "SHOW_NEXT_HINT",
    "REVEAL_SOLUTION",
    "SHOW_BEST_APPROACH",
    "GIVE_SIMILAR_PROBLEM",
}

OPTION_IDS = ["A", "B", "C", "D"]

BANNED_PATTERNS = {
    "as an ai language model",
    "i cannot access",
    "i don't have access",
    "placeholder",
    "todo",
    "completed answer",
    "stub",
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

FINAL_ANSWER_PHRASES = {
    "final answer is",
    "therefore the answer is",
    "so the answer is",
    "hence the answer is",
    "the correct option is",
    "option a is correct",
    "option b is correct",
    "option c is correct",
    "option d is correct",
    "complete solution",
    "full solution",
}

LATEX_UNIT_PATTERN = r"\\text\{[^}]+\}"

VARIATION_EXPECTATIONS = {
    "numerical": {"expects_math": True, "expects_units": True},
    "jee": {"expects_math": True, "expects_exam_pattern": True},
    "neet": {"expects_option_logic": True},
    "multi_part": {"expects_cumulative_steps": True},
    "cbse": {"expects_board_style": True},
    "proof": {"expects_derivation_hint": True},
    "diagram": {"expects_diagram_awareness": True},
    "ncert_strict": {"expects_ncert_terms": True},
    "conceptual": {"expects_conceptual_hint": True},
    "case_study": {"expects_context_reading": True},
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
        "it", "as", "by", "from", "problem", "question", "answer", "section",
        "given", "find", "ncert", "context", "hint", "checkpoint", "option",
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


def _section_headings(coach: Optional[dict]) -> list[str]:
    return [str(s.get("heading", "")).strip() for s in _sections(coach) if isinstance(s, dict)]


def _section_text(coach: Optional[dict]) -> str:
    return " ".join(str(s.get("bodyMarkdown", "")) for s in _sections(coach) if isinstance(s, dict))


def _flatten_coach_text(coach: Optional[dict]) -> str:
    if not isinstance(coach, dict):
        return ""
    try:
        return json.dumps(coach, ensure_ascii=False)
    except Exception:
        return str(coach)


def _input_count(inputs: dict) -> int:
    try:
        return int(inputs.get("interaction_count", 0))
    except Exception:
        return 0


def _branch(count: int) -> str:
    if count <= 0:
        return "count0"
    if count == 1:
        return "count1"
    return "count2"


def _coach_count(coach: dict) -> Optional[int]:
    try:
        return int(coach.get("interactionCount"))
    except Exception:
        return None


def _checkpoint_options(checkpoint: Any) -> list[dict]:
    if not isinstance(checkpoint, dict):
        return []
    opts = checkpoint.get("options")
    return opts if isinstance(opts, list) else []


def _checkpoint_valid_shape(checkpoint: Any, expected_number: int | None = None) -> tuple[bool, str]:
    if not isinstance(checkpoint, dict):
        return False, "checkpoint must be object"

    if expected_number is not None:
        try:
            number = int(checkpoint.get("number"))
        except Exception:
            return False, "checkpoint.number invalid"
        if number != expected_number:
            return False, f"checkpoint.number expected {expected_number}, got {number}"

    prompt = checkpoint.get("prompt")
    if not isinstance(prompt, str) or _word_count(prompt) < 4:
        return False, "checkpoint.prompt must be substantive string"

    opts = _checkpoint_options(checkpoint)
    if len(opts) != 4:
        return False, f"checkpoint.options must have 4 options, got {len(opts)}"

    ids = []
    labels = []
    for idx, option in enumerate(opts):
        if not isinstance(option, dict):
            return False, f"option {idx} is not object"
        oid = option.get("id")
        label = option.get("label")
        if oid not in OPTION_IDS:
            return False, f"option {idx}.id invalid: {oid!r}"
        if not isinstance(label, str) or _word_count(label) < 2:
            return False, f"option {idx}.label too thin"
        ids.append(oid)
        labels.append(_norm(label))

    if ids != OPTION_IDS:
        return False, f"checkpoint option ids must be A-D in order, got {ids}"

    if len(set(labels)) != 4:
        return False, "checkpoint option labels must be unique"

    return True, "checkpoint shape valid"


def _history_valid_item(item: Any, expected_number: int | None = None, expected_choice: str | None = None) -> tuple[bool, str]:
    ok, msg = _checkpoint_valid_shape(item, expected_number)
    if not ok:
        return False, f"history checkpoint invalid: {msg}"

    if not isinstance(item, dict):
        return False, "history item not object"

    choice = item.get("studentChoice")
    if not isinstance(choice, str) or choice not in OPTION_IDS:
        return False, f"studentChoice invalid: {choice!r}"

    if expected_choice and choice != expected_choice:
        return False, f"studentChoice mismatch: expected {expected_choice}, got {choice}"

    selected = item.get("selectedLabel")
    if not isinstance(selected, str) or _word_count(selected) < 2:
        return False, "selectedLabel missing/thin"

    labels_by_id = {opt.get("id"): opt.get("label") for opt in _checkpoint_options(item)}
    if choice in labels_by_id and _jaccard(selected, str(labels_by_id[choice])) < 0.45 and _norm(selected) != _norm(labels_by_id[choice]):
        return False, "selectedLabel does not match chosen option label"

    feedback = item.get("feedbackMarkdown")
    if not isinstance(feedback, str) or _word_count(feedback) < 8:
        return False, "feedbackMarkdown missing/thin"

    return True, "history item valid"


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

    count = _input_count(inputs)
    branch = _branch(count)

    required = COUNT0_REQUIRED_KEYS if branch == "count0" else COUNT1_REQUIRED_KEYS if branch == "count1" else COUNT2_REQUIRED_KEYS
    disallowed = COUNT0_DISALLOWED_KEYS if branch == "count0" else COUNT1_DISALLOWED_KEYS if branch == "count1" else COUNT2_DISALLOWED_KEYS

    missing = required - set(coach.keys())
    if missing:
        return {"key": "schema_validity", "score": 0.0, "comment": f"coach_json missing keys for {branch}: {sorted(missing)}"}

    present_disallowed = disallowed & set(coach.keys())
    if present_disallowed:
        return {"key": "schema_validity", "score": 0.0, "comment": f"disallowed keys for {branch}: {sorted(present_disallowed)}"}

    if _coach_count(coach) != (0 if branch == "count0" else 1 if branch == "count1" else 2):
        return {"key": "schema_validity", "score": 0.0, "comment": f"interactionCount mismatch for {branch}: {coach.get('interactionCount')!r}"}

    if not isinstance(coach.get("title"), str) or not coach["title"].strip():
        return {"key": "schema_validity", "score": 0.0, "comment": "title must be non-empty string"}

    if not isinstance(coach.get("sections"), list) or not coach["sections"]:
        return {"key": "schema_validity", "score": 0.0, "comment": "sections must be non-empty list"}

    for idx, section in enumerate(coach["sections"]):
        if not isinstance(section, dict) or set(section.keys()) != {"heading", "bodyMarkdown"}:
            return {"key": "schema_validity", "score": 0.0, "comment": f"section {idx} must contain heading/bodyMarkdown only"}
        if not isinstance(section.get("heading"), str) or not section["heading"].strip():
            return {"key": "schema_validity", "score": 0.0, "comment": f"section {idx}.heading empty"}
        if not isinstance(section.get("bodyMarkdown"), str) or not section["bodyMarkdown"].strip():
            return {"key": "schema_validity", "score": 0.0, "comment": f"section {idx}.bodyMarkdown empty"}

    if branch in {"count0", "count1"} and coach.get("revealLevel") != "hint":
        return {"key": "schema_validity", "score": 0.0, "comment": f"{branch} revealLevel must be 'hint'"}

    if branch == "count2" and coach.get("revealLevel") != "full":
        return {"key": "schema_validity", "score": 0.0, "comment": "final branch revealLevel must be 'full'"}

    if not isinstance(coach.get("followUpButtons"), list):
        return {"key": "schema_validity", "score": 0.0, "comment": "followUpButtons must be list"}

    if branch in {"count0", "count1"} and coach.get("followUpButtons") != []:
        return {"key": "schema_validity", "score": 0.0, "comment": f"{branch} followUpButtons must be empty list"}

    if branch == "count2":
        actions = {b.get("action") for b in coach.get("followUpButtons", []) if isinstance(b, dict)}
        if actions != FINAL_FOLLOWUP_ACTIONS:
            return {"key": "schema_validity", "score": 0.0, "comment": f"final followUp action set mismatch: {sorted(actions)}"}
        if not isinstance(coach.get("finalAnswer"), str) or not coach["finalAnswer"].strip():
            return {"key": "schema_validity", "score": 0.0, "comment": "finalAnswer required in final branch"}

    text = _flatten_coach_text(coach)
    if _contains_any(text, BANNED_PATTERNS | INTERNAL_LEAKS):
        return {"key": "schema_validity", "score": 0.0, "comment": "coach_json contains banned/internal phrase"}

    return {"key": "schema_validity", "score": 1.0, "comment": "schema valid"}


# ---------------------------------------------------------------------------
# Evaluator 2: interaction_branch_contract
# ---------------------------------------------------------------------------

def interaction_branch_contract(run, example) -> dict:
    coach = _get_coach(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)

    if coach is None:
        return {"key": "interaction_branch_contract", "score": 0.0, "comment": "coach_json missing/malformed", "hard_rule_violated": False}

    count = _input_count(inputs)
    branch = _branch(count)
    headings = _section_headings(coach)
    issues = []
    hard = False

    if branch == "count0":
        if headings != COUNT0_HEADINGS:
            issues.append(f"count0 headings mismatch:{headings}")
            hard = True
        ok, msg = _checkpoint_valid_shape(coach.get("checkpoint"), expected_number=1)
        if not ok:
            issues.append(msg)
            hard = True
        if coach.get("checkpointHistory") != []:
            issues.append("count0 checkpointHistory must be []")
            hard = True

    elif branch == "count1":
        if headings != COUNT1_HEADINGS:
            issues.append(f"count1 headings mismatch:{headings}")
            hard = True
        history = coach.get("checkpointHistory")
        if not isinstance(history, list) or len(history) != 1:
            issues.append("count1 checkpointHistory must contain exactly 1 item")
            hard = True
        else:
            expected_choice = str(inputs.get("student_choice", "")).strip() or None
            ok, msg = _history_valid_item(history[0], expected_number=1, expected_choice=expected_choice)
            if not ok:
                issues.append(msg)
                hard = True
        ok, msg = _checkpoint_valid_shape(coach.get("checkpoint"), expected_number=2)
        if not ok:
            issues.append(msg)
            hard = True
        feedback = _section_text({"sections": [s for s in _sections(coach) if s.get("heading") == "Feedback on your choice"]})
        choice = str(inputs.get("student_choice", "")).strip()
        if choice and choice not in feedback:
            issues.append("feedback section does not name student_choice")
            hard = True

    else:
        heading_set = set(headings)
        if not COUNT2_MIN_HEADINGS.issubset(heading_set):
            issues.append(f"final branch missing required headings: {sorted(COUNT2_MIN_HEADINGS-heading_set)}")
            hard = True
        if len(heading_set & COUNT2_FEEDBACK_HEADINGS) < 2:
            issues.append("final branch must include feedback for both checkpoints")
            hard = True
        history = coach.get("checkpointHistory")
        if not isinstance(history, list) or len(history) != 2:
            issues.append("final branch checkpointHistory must contain exactly 2 items")
            hard = True
        else:
            ok1, msg1 = _history_valid_item(history[0], expected_number=1)
            ok2, msg2 = _history_valid_item(history[1], expected_number=2, expected_choice=str(inputs.get("student_choice", "")).strip() or None)
            if not ok1:
                issues.append(f"history1:{msg1}")
                hard = True
            if not ok2:
                issues.append(f"history2:{msg2}")
                hard = True

    if hard:
        return {"key": "interaction_branch_contract", "score": 0.0, "comment": "; ".join(issues[:10]), "hard_rule_violated": True}
    if issues:
        return {"key": "interaction_branch_contract", "score": 0.5, "comment": "; ".join(issues[:10]), "hard_rule_violated": False}
    return {"key": "interaction_branch_contract", "score": 1.0, "comment": f"{branch} contract passed", "hard_rule_violated": False}


# ---------------------------------------------------------------------------
# Evaluator 3: no_premature_answer
# ---------------------------------------------------------------------------

def no_premature_answer(run, example) -> dict:
    coach = _get_coach(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)
    ref = _safe_get_reference(example)

    if coach is None:
        return {"key": "no_premature_answer", "score": 0.0, "comment": "coach_json missing/malformed", "hard_rule_violated": False}

    count = _input_count(inputs)
    branch = _branch(count)
    text = _section_text(coach)
    expert_final = _expert_final_answer(inputs)

    if branch == "count2":
        # Final branch should reveal answer.
        final = str(coach.get("finalAnswer", ""))
        if not final.strip():
            return {"key": "no_premature_answer", "score": 0.0, "comment": "final branch missing finalAnswer", "hard_rule_violated": True}
        return {"key": "no_premature_answer", "score": 1.0, "comment": "final branch correctly reveals answer", "hard_rule_violated": False}

    issues = []
    hard = False

    if "finalAnswer" in coach:
        issues.append("finalAnswer present before final reveal")
        hard = True

    if _contains_any(text, FINAL_ANSWER_PHRASES):
        issues.append("explicit final-answer phrase before final reveal")
        hard = True

    final_vals = _extract_numbers_units(expert_final)
    text_vals = _extract_numbers_units(text)

    # If no expert final answer is supplied, fall back to gold reference if it contains a final branch.
    gold = _get_gold_coach(ref)
    if not final_vals and isinstance(gold, dict):
        final_vals = _extract_numbers_units(str(gold.get("finalAnswer", "")))

    leaked = []
    for val in final_vals:
        # Avoid false positives for givens/common coefficients.
        if val in {"0", "1", "2", "3", "4", "5", "10"}:
            continue
        if any(val in tv or tv in val for tv in text_vals):
            leaked.append(val)

    if leaked:
        issues.append(f"likely_final_value_leaked:{sorted(set(leaked))[:5]}")
        hard = True

    if re.search(r"\b(option|choice)\s+[abcd]\b|\b[abcd]\s+is\s+correct\b", text, flags=re.IGNORECASE):
        issues.append("likely_final_option_leaked")
        hard = True

    if hard:
        return {"key": "no_premature_answer", "score": 0.0, "comment": "; ".join(issues[:8]), "hard_rule_violated": True}
    return {"key": "no_premature_answer", "score": 1.0, "comment": "no premature answer detected", "hard_rule_violated": False}


# ---------------------------------------------------------------------------
# Evaluator 4: checkpoint_quality
# ---------------------------------------------------------------------------

def checkpoint_quality(run, example) -> dict:
    coach = _get_coach(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)

    if coach is None:
        return {"key": "checkpoint_quality", "score": 0.0, "comment": "coach_json missing/malformed"}

    count = _input_count(inputs)
    branch = _branch(count)

    if branch == "count2":
        return {"key": "checkpoint_quality", "score": 1.0, "comment": "final branch has no active checkpoint; history checked separately"}

    checkpoint = coach.get("checkpoint")
    ok, msg = _checkpoint_valid_shape(checkpoint, expected_number=1 if branch == "count0" else 2)
    if not ok:
        return {"key": "checkpoint_quality", "score": 0.0, "comment": msg}

    prompt = str(checkpoint.get("prompt", ""))
    options = _checkpoint_options(checkpoint)
    labels = [str(o.get("label", "")) for o in options]

    issues = []

    # Option A should be concept-correct per prompt contract. Code cannot prove correctness,
    # but it can require A to be substantive and not a placeholder/generic filler.
    if _word_count(labels[0]) < 3 or _contains_any(labels[0], {"all of the above", "none of the above", "placeholder", "answer"}):
        issues.append("option A is too thin/generic to be concept-correct")

    # Distractors should be plausible, not nonsense.
    bad_labels = [i for i, label in enumerate(labels) if _contains_any(label, {"banana", "random", "irrelevant", "placeholder", "dummy"})]
    if bad_labels:
        issues.append(f"implausible distractor labels at indexes {bad_labels}")

    # Checkpoint prompt/options should be problem-specific.
    problem = str(inputs.get("problem_text_normalized", ""))
    if _jaccard(prompt + " " + " ".join(labels), problem) < 0.04:
        issues.append("checkpoint appears weakly problem-specific")

    if issues:
        hard = any("placeholder" in x or "implausible" in x for x in issues)
        return {"key": "checkpoint_quality", "score": 0.0 if hard else 0.5, "comment": "; ".join(issues)}
    return {"key": "checkpoint_quality", "score": 1.0, "comment": "checkpoint options are structured and plausible"}


# ---------------------------------------------------------------------------
# Evaluator 5: cumulative_context_and_alignment
# ---------------------------------------------------------------------------

def cumulative_context_and_alignment(run, example) -> dict:
    coach = _get_coach(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)

    if coach is None:
        return {"key": "cumulative_context_and_alignment", "score": 0.0, "comment": "coach_json missing/malformed", "hard_rule_violated": False}

    count = _input_count(inputs)
    branch = _branch(count)
    text = _flatten_coach_text(coach)
    problem = str(inputs.get("problem_text_normalized", ""))
    context = str(inputs.get("ncert_context", ""))
    dna = inputs.get("problem_dna") if isinstance(inputs.get("problem_dna"), dict) else {}
    expert_text = _expert_solution_text(inputs)

    issues = []
    hard = False

    problem_overlap = _jaccard(text, problem)
    context_overlap = _jaccard(text, context) if context.strip() else 0.0
    dna_terms = ""
    dna_overlap = 0.0

    if dna:
        dna_terms = " ".join([
            str(dna.get("chapter", "")),
            " ".join(dna.get("conceptTags", [])) if isinstance(dna.get("conceptTags"), list) else "",
            str(dna.get("questionType", "")),
            str(dna.get("examSkill", "")),
        ])
        dna_overlap = _jaccard(text, dna_terms) if dna_terms.strip() else 0.0

    # Early hint branches may not repeat the full stem. Accept alignment through
    # the problem itself, NCERT context, or DNA concept terms.
    if max(problem_overlap, context_overlap, dna_overlap) < 0.06:
        issues.append(
            f"weak_problem_context_dna_alignment:p={problem_overlap:.2f},c={context_overlap:.2f},dna={dna_overlap:.2f}"
        )

    if branch in {"count1", "count2"}:
        prior = inputs.get("prior_response")
        if prior:
            prior_text = json.dumps(prior, ensure_ascii=False) if isinstance(prior, dict) else str(prior)
            # Must preserve at least checkpoint prompt/options from previous response.
            if _jaccard(text, prior_text) < 0.08:
                issues.append("weak_prior_response_preservation")

        history = coach.get("checkpointHistory")
        if not isinstance(history, list) or len(history) < (1 if branch == "count1" else 2):
            issues.append("checkpointHistory missing/incomplete")
            hard = True

    # Final branch should align with expert solution.
    if branch == "count2" and expert_text.strip():
        if _jaccard(text, expert_text) < 0.06:
            coach_nums = _extract_numbers_units(text)
            expert_nums = _extract_numbers_units(expert_text)
            numeric_aligned = bool(coach_nums and expert_nums and any(a in b or b in a for a in coach_nums for b in expert_nums))
            if not numeric_aligned:
                issues.append("weak_expert_solution_alignment_in_final_reveal")
                hard = True

    if hard:
        return {"key": "cumulative_context_and_alignment", "score": 0.0, "comment": "; ".join(issues[:10]), "hard_rule_violated": True}
    if issues:
        return {"key": "cumulative_context_and_alignment", "score": 0.5, "comment": "; ".join(issues[:10]), "hard_rule_violated": False}
    return {"key": "cumulative_context_and_alignment", "score": 1.0, "comment": "context/DNA/history alignment checks passed", "hard_rule_violated": False}


# ---------------------------------------------------------------------------
# Evaluator 6: latex_and_variation_behavior
# ---------------------------------------------------------------------------

def latex_and_variation_behavior(run, example) -> dict:
    coach = _get_coach(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)
    variation = _safe_get_variation(example)

    if coach is None:
        return {"key": "latex_and_variation_behavior", "score": 0.0, "comment": "coach_json missing/malformed", "hard_rule_violated": False}

    text = _flatten_coach_text(coach)
    problem = str(inputs.get("problem_text_normalized", ""))
    issues = []
    hard = False

    latex_issues = _bad_latex(text)
    if latex_issues:
        issues.extend(latex_issues)
        hard = True

    exp = VARIATION_EXPECTATIONS.get(variation, {})
    problem_has_math = bool(re.search(r"[$=^_]|[ρΔθΩμ]|\\frac|\d+\s*(?:Ω|V|A|m/s|mol|cm|kg|J|N|pm|eV)", problem))

    if exp.get("expects_math") and problem_has_math and not (_formula_like(text) or "$" in text):
        issues.append("math problem but formula/math formatting missing")

    if exp.get("expects_units") and re.search(r"\d", problem) and not re.search(LATEX_UNIT_PATTERN + r"|Ω|V|A|mol|cm|kg|J|N|pm|eV", text):
        issues.append("unit formatting/cue missing")

    if exp.get("expects_option_logic") and not _contains_any(text, {"option", "choice", "statement", "assertion", "reason", "eliminate"}):
        issues.append("NEET option/assertion reasoning cue missing")

    if exp.get("expects_exam_pattern") and not _contains_any(text, {"pattern", "shortcut", "direct", "exam", "trigger"}):
        issues.append("JEE/exam pattern cue missing")

    if exp.get("expects_cumulative_steps") and _input_count(inputs) >= 2 and _word_count(text) < 80:
        issues.append("multi_part final response too thin")

    if exp.get("expects_derivation_hint") and not _contains_any(text, {"derive", "show", "prove", "relationship", "start from"}):
        issues.append("proof derivation hint missing")

    if exp.get("expects_diagram_awareness") and not _contains_any(text, {"diagram", "figure", "graph", "ray", "shown", "label", "axis"}):
        issues.append("diagram awareness missing")

    if exp.get("expects_ncert_terms") and not _contains_any(text, {"ncert", "definition", "principle", "standard", "textbook"}):
        issues.append("NCERT-strict wording cue missing")

    if exp.get("expects_conceptual_hint") and not _contains_any(text, {"concept", "why", "because", "principle", "meaning"}):
        issues.append("conceptual hint cue missing")

    if exp.get("expects_context_reading") and not _contains_any(text, {"case", "passage", "given", "data", "statement"}):
        issues.append("case-study reading cue missing")

    if hard:
        return {"key": "latex_and_variation_behavior", "score": 0.0, "comment": "; ".join(issues[:10]), "hard_rule_violated": True}
    if issues:
        return {"key": "latex_and_variation_behavior", "score": 0.5, "comment": "; ".join(issues[:10]), "hard_rule_violated": False}
    return {"key": "latex_and_variation_behavior", "score": 1.0, "comment": "LaTeX and variation behavior checks passed", "hard_rule_violated": False}


# ---------------------------------------------------------------------------
# Evaluator 7: required LLM judge
# ---------------------------------------------------------------------------

def make_required_llm_help_me_solve_judge(judge_llm: Callable[[str], str]):
    def required_llm_help_me_solve_judge(run, example) -> dict:
        coach = _get_coach(_safe_get_outputs(run))
        inputs = _safe_get_inputs(example)
        ref = _safe_get_reference(example)

        if coach is None:
            return {
                "key": "required_llm_help_me_solve_judge",
                "score": 0.0,
                "comment": "coach_json missing/malformed",
                "hard_rule_violated": True,
                "judge_available": False,
            }

        gold = _get_gold_coach(ref)
        prompt = f"""
You are evaluating ScholarSync's Help Me Solve It interactive coach.

Evaluate the candidate ONLY against:
- the problem,
- interaction_count branch,
- student_choice/prior_response if supplied,
- NCERT context,
- optional Problem DNA / expert solution,
- gold/reference coach if supplied.

Return ONLY valid JSON:
{{
  "guided_pedagogy_score": <0.0 to 1.0>,
  "checkpoint_quality_score": <0.0 to 1.0>,
  "branch_safety_score": <0.0 to 1.0>,
  "solution_correctness_score": <0.0 to 1.0>,
  "ncert_alignment_score": <0.0 to 1.0>,
  "comment": "<short reason, max 45 words>"
}}

Scoring guidance:
- guided_pedagogy_score: hints/feedback guide the student without doing too much.
- checkpoint_quality_score: checkpoint options are plausible and concept-correct; A should be the concept-correct option.
- branch_safety_score: interaction_count 0-1 does not reveal final answer; count 2+ gives full solution.
- solution_correctness_score: final solution is correct when final branch; for hint branches, score based on correctness of hints/checkpoints.
- ncert_alignment_score: concepts/formulas match NCERT context or gold.

Problem:
{inputs.get("problem_text_normalized", "")}

Interaction count:
{inputs.get("interaction_count", "")}

Student choice:
{inputs.get("student_choice", "")}

NCERT context:
{inputs.get("ncert_context", "")}

Prior response:
{json.dumps(inputs.get("prior_response", ""), ensure_ascii=False)}

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
                "key": "required_llm_help_me_solve_judge",
                "score": 0.0,
                "comment": f"judge call failed: {exc}",
                "hard_rule_violated": True,
                "judge_available": False,
            }

        parsed = _json_from_text(raw)
        if not parsed:
            return {
                "key": "required_llm_help_me_solve_judge",
                "score": 0.0,
                "comment": f"judge returned invalid JSON: {str(raw)[:160]}",
                "hard_rule_violated": True,
                "judge_available": False,
            }

        pedagogy = _coerce_score(parsed.get("guided_pedagogy_score"))
        checkpoint = _coerce_score(parsed.get("checkpoint_quality_score"))
        safety = _coerce_score(parsed.get("branch_safety_score"))
        solution = _coerce_score(parsed.get("solution_correctness_score"))
        ncert = _coerce_score(parsed.get("ncert_alignment_score"))
        comment = str(parsed.get("comment", "")).strip()

        score = round(
            (0.24 * pedagogy)
            + (0.22 * checkpoint)
            + (0.24 * safety)
            + (0.18 * solution)
            + (0.12 * ncert),
            3,
        )

        hard = safety < 0.80 or checkpoint < 0.65 or solution < 0.60 or ncert < 0.55

        return {
            "key": "required_llm_help_me_solve_judge",
            "score": score,
            "comment": (
                f"pedagogy={pedagogy:.2f} checkpoint={checkpoint:.2f} safety={safety:.2f} "
                f"solution={solution:.2f} ncert={ncert:.2f} | {comment}"
            ),
            "guided_pedagogy_score": pedagogy,
            "checkpoint_quality_score": checkpoint,
            "branch_safety_score": safety,
            "solution_correctness_score": solution,
            "ncert_alignment_score": ncert,
            "hard_rule_violated": hard,
            "judge_available": True,
        }

    return required_llm_help_me_solve_judge


def build_per_example_evaluators(judge_llm: Callable[[str], str]) -> list[Callable]:
    if judge_llm is None or not callable(judge_llm):
        raise ValueError("Agent 21 evaluation requires judge_llm. Use build_per_example_evaluators(judge_llm).")
    return [
        schema_validity,
        interaction_branch_contract,
        no_premature_answer,
        checkpoint_quality,
        cumulative_context_and_alignment,
        latex_and_variation_behavior,
        make_required_llm_help_me_solve_judge(judge_llm),
    ]


# ---------------------------------------------------------------------------
# Summary evaluator
# ---------------------------------------------------------------------------

def help_me_solve_it_severity_summary(runs: list, examples: list) -> dict:
    if len(runs) != len(examples):
        return {
            "key": "help_me_solve_it_severity_summary",
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

        branch = interaction_branch_contract(run, example)
        premature = no_premature_answer(run, example)
        checkpoint = checkpoint_quality(run, example)
        context = cumulative_context_and_alignment(run, example)
        latex = latex_and_variation_behavior(run, example)
        llm = _extract_required_llm_feedback(run)

        for result in (branch, premature, context, latex):
            if result.get("hard_rule_violated"):
                tier_0.append({"example_id": getattr(example, "id", None), "reason": f"{result['key']} hard failure: {result['comment']}"})

        if checkpoint["score"] == 0.0 and _input_count(_safe_get_inputs(example)) < 2:
            tier_0.append({"example_id": getattr(example, "id", None), "reason": f"checkpoint_quality failed: {checkpoint['comment']}"})

        if llm is not None:
            if llm.get("hard_rule_violated") or llm.get("score", 0.0) < 0.70:
                tier_0.append({"example_id": getattr(example, "id", None), "reason": f"LLM judge hard failure: {llm.get('comment', '')}"})
            elif llm.get("score", 1.0) < 0.84:
                tier_1 += 1
                tier_1_applicable += 1

        tier_1_applicable += 6
        for result in (branch, premature, checkpoint, context, latex):
            if result["score"] < 1.0:
                tier_1 += 1

        llm_ok = True if llm is None else llm.get("score", 0.0) >= 0.84
        if (
            branch["score"] == 1.0
            and premature["score"] == 1.0
            and checkpoint["score"] == 1.0
            and context["score"] == 1.0
            and latex["score"] == 1.0
            and llm_ok
        ):
            variation_passes[variation] = variation_passes.get(variation, 0) + 1

    tier_1_rate = tier_1 / tier_1_applicable if tier_1_applicable else 0.0
    per_variation = {v: round(variation_passes.get(v, 0) / total, 3) for v, total in variation_totals.items()}

    recommendation = "BLOCK" if tier_0 else ("REVIEW" if tier_1_rate > 0.15 else "OK")

    return {
        "key": "help_me_solve_it_severity_summary",
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
            if val.get("key") == "required_llm_help_me_solve_judge":
                return val
            maybe = val.get("required_llm_help_me_solve_judge")
            if isinstance(maybe, dict):
                return maybe
            if isinstance(maybe, (int, float)):
                return {
                    "key": "required_llm_help_me_solve_judge",
                    "score": float(maybe),
                    "comment": "score extracted from run feedback mapping",
                    "hard_rule_violated": float(maybe) < 0.70,
                }
        if isinstance(val, list):
            for item in val:
                if isinstance(item, dict) and item.get("key") == "required_llm_help_me_solve_judge":
                    return item
    return None


# ---------------------------------------------------------------------------
# Public registries
# ---------------------------------------------------------------------------

PER_EXAMPLE_EVALUATORS_CODE_ONLY = [
    schema_validity,
    interaction_branch_contract,
    no_premature_answer,
    checkpoint_quality,
    cumulative_context_and_alignment,
    latex_and_variation_behavior,
]

PER_EXAMPLE_EVALUATORS = None

SUMMARY_EVALUATORS = [help_me_solve_it_severity_summary]
