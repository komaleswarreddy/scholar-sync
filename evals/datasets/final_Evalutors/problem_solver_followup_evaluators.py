"""
problem_solver_followup_evaluators.py

LangSmith custom evaluators for Agent 22: Problem Solver Follow-up Handler.

Agent role:
- Handles follow-up button actions after a Problem Solver coach session.
- Must continue the existing problem-solving session without losing the original
  problem context or previous solving mode.
- This is NOT a fresh coach generator. It is an action-specific continuation layer.

Production dependencies:
- Required inputs:
    action: str
    problem_text_normalized: str
    solving_mode: str
    user_follow_up: str
- Optional input:
    ncert_context: str
- Output:
    coach_json: {
      "title": str,
      "sections": [
        {"heading": "Follow-up", "bodyMarkdown": "..."}
      ],
      "finalAnswer": str | null,
      "revealLevel": "hint" | "full",
      "followUpButtons": [
        {"label": "Show best approach", "action": "SHOW_BEST_APPROACH"},
        {"label": "Give similar problem", "action": "GIVE_SIMILAR_PROBLEM"},
        {"label": "Start Tutor Session", "action": "START_TUTOR_SESSION"}
      ]
    }

Notes:
- Some production/gold traces may include optional legacy fields like `checkpoint`.
  The evaluator allows them but does not require them.
- Action semantics are more important than exact wording.

Evaluator design:
- Hybrid by default, but lighter than Agents 17–21.
- Code gates enforce deterministic behavior:
  schema, action slug compliance, reveal level, finalAnswer nullability, context
  retention, follow-up button stability, LaTeX hygiene, and no premature answer
  for hint actions.
- Required LLM judge evaluates semantic action quality and correctness/usefulness.
- Tier 2 because it is student-facing and action-sensitive, but it is a continuation
  handler rather than a core problem-solving coach.

LangSmith usage:
    from problem_solver_followup_evaluators import (
        build_per_example_evaluators,
        SUMMARY_EVALUATORS,
    )

    evaluators = build_per_example_evaluators(judge_llm)

Judge callable:
    judge_llm(prompt: str) -> str

Judge must return JSON:
{
  "action_compliance_score": 0.0-1.0,
  "context_retention_score": 0.0-1.0,
  "reveal_safety_score": 0.0-1.0,
  "correctness_or_usefulness_score": 0.0-1.0,
  "format_score": 0.0-1.0,
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

REQUIRED_INPUT_KEYS = {
    "action",
    "problem_text_normalized",
    "solving_mode",
    "user_follow_up",
}

REQUIRED_OUTPUT_KEYS = {"coach_json"}

REQUIRED_TOP_KEYS = {
    "title",
    "sections",
    "finalAnswer",
    "revealLevel",
    "followUpButtons",
}

ALLOWED_TOP_KEYS = REQUIRED_TOP_KEYS | {"checkpoint", "checkpointHistory"}

VALID_ACTIONS = {
    "SHOW_BEST_APPROACH",
    "GIVE_SIMILAR_PROBLEM",
    "START_TUTOR_SESSION",
    "SHOW_SHORTER_VERSION",
    "EXPLAIN_CONCEPT_AGAIN",
    "SHOW_NEXT_HINT",
    "REVEAL_SOLUTION",
}

VALID_SOLVING_MODES = {
    "EXPLAIN_FROM_BASICS",
    "SHOW_BEST_APPROACH",
    "SHOW_MISSING_IDEA",
    "HELP_ME_SOLVE_IT",
}

REQUIRED_FOLLOWUP_ACTIONS = {
    "SHOW_BEST_APPROACH",
    "GIVE_SIMILAR_PROBLEM",
    "START_TUTOR_SESSION",
}

ACTION_CUES = {
    "SHOW_BEST_APPROACH": {
        "best approach", "best method", "efficient", "shortcut", "exam", "method",
        "approach", "option", "analyze", "direct",
    },
    "GIVE_SIMILAR_PROBLEM": {
        "similar problem", "similar", "practice problem", "try this", "consider",
        "new problem", "related problem",
    },
    "START_TUTOR_SESSION": {
        "tutor", "session", "continue", "we can work", "guided", "understand",
        "let's", "step",
    },
    "SHOW_SHORTER_VERSION": {
        "short", "shorter", "brief", "concise", "summary", "quick", "in short",
    },
    "EXPLAIN_CONCEPT_AGAIN": {
        "concept", "explain", "again", "understand", "principle", "idea",
        "means", "why",
    },
    "SHOW_NEXT_HINT": {
        "hint", "next hint", "consider", "think", "start", "look at", "notice",
        "try",
    },
    "REVEAL_SOLUTION": {
        "solution", "answer", "final", "therefore", "hence", "solve", "steps",
    },
}

SOLVING_MODE_CUES = {
    "EXPLAIN_FROM_BASICS": {"basic", "basics", "from beginning", "concept", "explain"},
    "SHOW_BEST_APPROACH": {"best", "approach", "efficient", "method", "shortcut"},
    "SHOW_MISSING_IDEA": {"missing idea", "key idea", "unlock", "hint", "concept"},
    "HELP_ME_SOLVE_IT": {"hint", "checkpoint", "choice", "guided", "solve", "step"},
}

HINT_ACTIONS = {"SHOW_NEXT_HINT"}
FULL_ACTIONS = {
    "REVEAL_SOLUTION",
    "SHOW_BEST_APPROACH",
    "SHOW_SHORTER_VERSION",
    "EXPLAIN_CONCEPT_AGAIN",
    "START_TUTOR_SESSION",
}

# Similar problem follows previous mode: from partial missing-idea flow, it should
# generally stay hint-like; otherwise full is acceptable in the current dataset.
SIMILAR_PROBLEM_ACTION = "GIVE_SIMILAR_PROBLEM"

BANNED_PATTERNS = {
    "as an ai language model",
    "i cannot access",
    "i don't have access",
    "placeholder",
    "todo",
    "lorem ipsum",
}

INTERNAL_LEAKS = {
    "coach_json",
    "follow_up.j2",
    "jinja",
    ".j2",
    "system prompt",
    "problem_solver",
    "handle_follow_up",
    "runtime note",
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
}

LATEX_UNIT_PATTERN = r"\\text\{[^}]+\}"

MAX_BODY_WORDS = 450
MIN_BODY_WORDS = 18


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
        "given", "find", "ncert", "context", "follow", "up", "student",
        "clicked",
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


def _followup_body(coach: Optional[dict]) -> str:
    secs = _sections(coach)
    if not secs:
        return ""
    return str(secs[0].get("bodyMarkdown", "")) if isinstance(secs[0], dict) else ""


def _flatten_coach_text(coach: Optional[dict]) -> str:
    if not isinstance(coach, dict):
        return ""
    try:
        return json.dumps(coach, ensure_ascii=False)
    except Exception:
        return str(coach)


def _input_action(inputs: dict) -> str:
    return str(inputs.get("action", "")).strip()


def _input_mode(inputs: dict) -> str:
    return str(inputs.get("solving_mode", "")).strip()


def _expected_reveal(action: str, solving_mode: str) -> set[str]:
    if action == "SHOW_NEXT_HINT":
        return {"hint"}
    if action == "REVEAL_SOLUTION":
        return {"full"}
    if action == "GIVE_SIMILAR_PROBLEM":
        if solving_mode == "SHOW_MISSING_IDEA":
            return {"hint"}
        return {"full", "hint"}  # both are acceptable depending on product UX.
    if action in FULL_ACTIONS:
        return {"full"}
    return {"full", "hint"}


def _expected_final_answer_state(action: str, reveal_level: str) -> str:
    """
    Returns: "required", "null", or "flexible".
    """
    if action == "REVEAL_SOLUTION":
        return "required"
    if action in {"SHOW_NEXT_HINT", "GIVE_SIMILAR_PROBLEM"} or reveal_level == "hint":
        return "null"
    if action in {"SHOW_SHORTER_VERSION", "EXPLAIN_CONCEPT_AGAIN", "START_TUTOR_SESSION"}:
        return "flexible"
    if action == "SHOW_BEST_APPROACH":
        return "flexible"
    return "flexible"


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


def _gold_text(ref: Optional[dict]) -> str:
    gold = _get_gold_coach(ref)
    return _flatten_coach_text(gold)


def _gold_final(ref: Optional[dict]) -> Any:
    gold = _get_gold_coach(ref)
    if not isinstance(gold, dict):
        return None
    return gold.get("finalAnswer")


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

    action = _input_action(inputs)
    if action not in VALID_ACTIONS:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"invalid action={action!r}",
        }

    solving_mode = _input_mode(inputs)
    if solving_mode not in VALID_SOLVING_MODES:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"invalid solving_mode={solving_mode!r}",
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

    extra = set(coach.keys()) - ALLOWED_TOP_KEYS
    if extra:
        return {
            "key": "schema_validity",
            "score": 0.5,
            "comment": f"unexpected optional coach_json key(s): {sorted(extra)}",
        }

    if not isinstance(coach.get("title"), str) or not coach["title"].strip():
        return {"key": "schema_validity", "score": 0.0, "comment": "title must be non-empty string"}

    if coach.get("revealLevel") not in {"hint", "full"}:
        return {"key": "schema_validity", "score": 0.0, "comment": f"invalid revealLevel={coach.get('revealLevel')!r}"}

    sections = coach.get("sections")
    if not isinstance(sections, list) or len(sections) != 1:
        return {"key": "schema_validity", "score": 0.0, "comment": "sections must contain exactly one Follow-up section"}

    section = sections[0]
    if not isinstance(section, dict) or set(section.keys()) != {"heading", "bodyMarkdown"}:
        return {"key": "schema_validity", "score": 0.0, "comment": "Follow-up section must contain heading/bodyMarkdown only"}

    if section.get("heading") != "Follow-up":
        return {"key": "schema_validity", "score": 0.0, "comment": f"section heading must be 'Follow-up', got {section.get('heading')!r}"}

    if not isinstance(section.get("bodyMarkdown"), str) or not section["bodyMarkdown"].strip():
        return {"key": "schema_validity", "score": 0.0, "comment": "bodyMarkdown must be non-empty string"}

    final = coach.get("finalAnswer")
    if final is not None and not isinstance(final, str):
        return {"key": "schema_validity", "score": 0.0, "comment": "finalAnswer must be string or null"}

    buttons = coach.get("followUpButtons")
    if not isinstance(buttons, list) or len(buttons) != 3:
        return {"key": "schema_validity", "score": 0.0, "comment": "followUpButtons must contain exactly 3 buttons"}

    actions = set()
    for idx, button in enumerate(buttons):
        if not isinstance(button, dict) or not isinstance(button.get("label"), str) or not isinstance(button.get("action"), str):
            return {"key": "schema_validity", "score": 0.0, "comment": f"button {idx} invalid"}
        actions.add(button["action"])

    if actions != REQUIRED_FOLLOWUP_ACTIONS:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"followUp action set mismatch: {sorted(actions)}",
        }

    text = _flatten_coach_text(coach)
    if _contains_any(text, BANNED_PATTERNS | INTERNAL_LEAKS):
        return {"key": "schema_validity", "score": 0.0, "comment": "coach_json contains banned/internal phrase"}

    body_wc = _word_count(section["bodyMarkdown"])
    if body_wc < MIN_BODY_WORDS:
        return {"key": "schema_validity", "score": 0.5, "comment": f"bodyMarkdown is thin: {body_wc} words"}

    return {"key": "schema_validity", "score": 1.0, "comment": "schema valid"}


# ---------------------------------------------------------------------------
# Evaluator 2: action_compliance_code
# ---------------------------------------------------------------------------

def action_compliance_code(run, example) -> dict:
    coach = _get_coach(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)

    if coach is None:
        return {
            "key": "action_compliance_code",
            "score": 0.0,
            "comment": "coach_json missing/malformed",
            "hard_rule_violated": False,
        }

    action = _input_action(inputs)
    title_body = f"{coach.get('title', '')} {_followup_body(coach)}"

    if action not in VALID_ACTIONS:
        return {
            "key": "action_compliance_code",
            "score": 0.0,
            "comment": f"invalid action={action!r}",
            "hard_rule_violated": True,
        }

    cues = ACTION_CUES.get(action, set())
    if not _contains_any(title_body, cues):
        return {
            "key": "action_compliance_code",
            "score": 0.0,
            "comment": f"title/body do not reflect requested action={action}",
            "hard_rule_violated": True,
        }

    # Similar problem must be a new/reframed problem, not just a solution to the old one.
    if action == "GIVE_SIMILAR_PROBLEM":
        if not _contains_any(title_body, {"problem", "consider", "calculate", "find", "describe", "discuss"}):
            return {
                "key": "action_compliance_code",
                "score": 0.0,
                "comment": "GIVE_SIMILAR_PROBLEM does not appear to generate a practice problem",
                "hard_rule_violated": True,
            }

    # Show next hint should not be a full paragraph solution.
    if action == "SHOW_NEXT_HINT":
        if _word_count(_followup_body(coach)) > 120:
            return {
                "key": "action_compliance_code",
                "score": 0.5,
                "comment": "SHOW_NEXT_HINT is too long for a next hint",
                "hard_rule_violated": False,
            }

    return {
        "key": "action_compliance_code",
        "score": 1.0,
        "comment": f"action-specific cues found for {action}",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 3: reveal_level_and_answer_policy
# ---------------------------------------------------------------------------

def reveal_level_and_answer_policy(run, example) -> dict:
    coach = _get_coach(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)
    ref = _safe_get_reference(example)

    if coach is None:
        return {
            "key": "reveal_level_and_answer_policy",
            "score": 0.0,
            "comment": "coach_json missing/malformed",
            "hard_rule_violated": False,
        }

    action = _input_action(inputs)
    solving_mode = _input_mode(inputs)
    expected_reveals = _expected_reveal(action, solving_mode)
    actual_reveal = coach.get("revealLevel")

    issues = []
    hard = False

    if actual_reveal not in expected_reveals:
        issues.append(f"revealLevel mismatch for {action}/{solving_mode}: expected {sorted(expected_reveals)}, got {actual_reveal!r}")
        hard = True

    final_state = _expected_final_answer_state(action, str(actual_reveal))
    final = coach.get("finalAnswer")

    if final_state == "required" and (final is None or not str(final).strip()):
        issues.append("finalAnswer required for REVEAL_SOLUTION")
        hard = True

    if final_state == "null" and final is not None:
        issues.append(f"finalAnswer must be null for {action} with revealLevel={actual_reveal}")
        hard = True

    body = _followup_body(coach)

    if actual_reveal == "hint":
        if _contains_any(body, FINAL_ANSWER_PHRASES):
            issues.append("hint reveal contains explicit final-answer phrase")
            hard = True

        # If gold has a final answer, catch obvious leakage.
        gold_final = _gold_final(ref)
        if isinstance(gold_final, str) and gold_final.strip():
            body_vals = _extract_numbers_units(body)
            final_vals = _extract_numbers_units(gold_final)
            leaked = [
                v for v in final_vals
                if v not in {"0", "1", "2", "3", "4", "5", "10"}
                and any(v in b or b in v for b in body_vals)
            ]
            if leaked:
                issues.append(f"hint reveal leaks gold final value: {sorted(set(leaked))[:5]}")
                hard = True

    if hard:
        return {
            "key": "reveal_level_and_answer_policy",
            "score": 0.0,
            "comment": "; ".join(issues),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "reveal_level_and_answer_policy",
            "score": 0.5,
            "comment": "; ".join(issues),
            "hard_rule_violated": False,
        }

    return {
        "key": "reveal_level_and_answer_policy",
        "score": 1.0,
        "comment": "reveal level and finalAnswer policy passed",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 4: context_retention_code
# ---------------------------------------------------------------------------

def context_retention_code(run, example) -> dict:
    coach = _get_coach(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)
    ref = _safe_get_reference(example)

    if coach is None:
        return {
            "key": "context_retention_code",
            "score": 0.0,
            "comment": "coach_json missing/malformed",
        }

    problem = str(inputs.get("problem_text_normalized", ""))
    context = str(inputs.get("ncert_context", ""))
    solving_mode = _input_mode(inputs)
    action = _input_action(inputs)
    body = _followup_body(coach)
    title_body = f"{coach.get('title', '')} {body}"
    gold_text = _gold_text(ref)

    problem_overlap = _jaccard(title_body, problem)
    context_overlap = _jaccard(title_body, context) if context.strip() else 0.0
    gold_overlap = _jaccard(title_body, gold_text) if gold_text else 0.0

    issues = []

    # Similar-problem content can intentionally alter numbers/details; require conceptual neighborhood.
    if max(problem_overlap, context_overlap, gold_overlap) < (0.06 if action == "GIVE_SIMILAR_PROBLEM" else 0.08):
        issues.append(
            f"weak_problem_context_retention:p={problem_overlap:.2f},c={context_overlap:.2f},gold={gold_overlap:.2f}"
        )

    # Prior solving mode should be respected through tone/shape, not necessarily named.
    mode_cues = SOLVING_MODE_CUES.get(solving_mode, set())
    if mode_cues and not _contains_any(title_body, mode_cues):
        # Not hard: action can dominate, especially REVEAL_SOLUTION.
        if action not in {"REVEAL_SOLUTION", "SHOW_BEST_APPROACH"}:
            issues.append(f"weak_solving_mode_continuity:{solving_mode}")

    user_follow_up = str(inputs.get("user_follow_up", ""))
    if user_follow_up and action not in user_follow_up and _jaccard(user_follow_up, title_body) < 0.04:
        issues.append("weak_user_follow_up_reflection")

    if issues:
        hard = any(x.startswith("weak_problem_context_retention") for x in issues)
        return {
            "key": "context_retention_code",
            "score": 0.0 if hard else 0.5,
            "comment": "; ".join(issues),
        }

    return {
        "key": "context_retention_code",
        "score": 1.0,
        "comment": "problem context and prior mode continuity checks passed",
    }


# ---------------------------------------------------------------------------
# Evaluator 5: latex_and_formatting_code
# ---------------------------------------------------------------------------

def latex_and_formatting_code(run, example) -> dict:
    coach = _get_coach(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)

    if coach is None:
        return {
            "key": "latex_and_formatting_code",
            "score": 0.0,
            "comment": "coach_json missing/malformed",
            "hard_rule_violated": False,
        }

    text = _flatten_coach_text(coach)
    body = _followup_body(coach)
    problem = str(inputs.get("problem_text_normalized", ""))
    action = _input_action(inputs)

    issues = []
    hard = False

    latex_issues = _bad_latex(text)
    if latex_issues:
        issues.extend(latex_issues)
        hard = True

    # Very long body for a follow-up usually means it is trying to re-run the full coach.
    body_words = _word_count(body)
    if body_words > MAX_BODY_WORDS:
        issues.append(f"bodyMarkdown_too_long_for_follow_up:{body_words}_words")

    # Math-ish problem/answer should preserve formatting. Be permissive because some
    # biology follow-ups use prose.
    problem_has_math = bool(re.search(r"[$=^_]|[ρΔθΩμ]|\\frac|\d+\s*(?:Ω|V|A|m/s|mol|cm|kg|J|N|pm|eV|T|kV)", problem))
    body_has_math = bool(re.search(r"[$=^_]|[ρΔθΩμ]|\\frac|\d+\s*(?:Ω|V|A|m/s|mol|cm|kg|J|N|pm|eV|T|kV)", body))
    if problem_has_math and body_has_math:
        if not ("$" in body or "\\(" in body or "\\[" in body or _formula_like(body)):
            issues.append("math content present but not formatted as formula/LaTeX")

    # Units inside LaTeX should ideally use \\text{}; warn, not block.
    if "$" in body and re.search(r"\d+\s*(V|A|Ω|T|kg|cm|mol|J|N|eV)\b", body) and not re.search(LATEX_UNIT_PATTERN, body):
        issues.append("units may not be formatted with \\text{} inside math")

    if action == "SHOW_SHORTER_VERSION" and body_words > 220:
        issues.append(f"SHOW_SHORTER_VERSION is not short enough:{body_words}_words")

    if hard:
        return {
            "key": "latex_and_formatting_code",
            "score": 0.0,
            "comment": "; ".join(issues[:10]),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "latex_and_formatting_code",
            "score": 0.5,
            "comment": "; ".join(issues[:10]),
            "hard_rule_violated": False,
        }

    return {
        "key": "latex_and_formatting_code",
        "score": 1.0,
        "comment": "LaTeX/formatting checks passed",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 6: required LLM judge
# ---------------------------------------------------------------------------

def make_required_llm_followup_judge(judge_llm: Callable[[str], str]):
    def required_llm_followup_judge(run, example) -> dict:
        coach = _get_coach(_safe_get_outputs(run))
        inputs = _safe_get_inputs(example)
        ref = _safe_get_reference(example)

        if coach is None:
            return {
                "key": "required_llm_followup_judge",
                "score": 0.0,
                "comment": "coach_json missing/malformed",
                "hard_rule_violated": True,
                "judge_available": False,
            }

        gold = _get_gold_coach(ref)
        prompt = f"""
You are evaluating ScholarSync's Problem Solver Follow-up Handler.

Evaluate the candidate ONLY against:
- requested action,
- original problem,
- previous solving mode,
- user follow-up text,
- NCERT context when provided,
- gold/reference coach when provided.

Return ONLY valid JSON:
{{
  "action_compliance_score": <0.0 to 1.0>,
  "context_retention_score": <0.0 to 1.0>,
  "reveal_safety_score": <0.0 to 1.0>,
  "correctness_or_usefulness_score": <0.0 to 1.0>,
  "format_score": <0.0 to 1.0>,
  "comment": "<short reason, max 45 words>"
}}

Scoring guidance:
- action_compliance_score: output genuinely follows the action slug.
- context_retention_score: continues the original problem and previous mode without drifting.
- reveal_safety_score: hint/full and finalAnswer policy are appropriate for the action.
- correctness_or_usefulness_score: content is correct/useful; similar problems are genuinely similar; reveal solutions are correct.
- format_score: JSON shape, one Follow-up section, readable Markdown/LaTeX.

Action:
{inputs.get("action", "")}

Problem:
{inputs.get("problem_text_normalized", "")}

Previous solving mode:
{inputs.get("solving_mode", "")}

User follow-up:
{inputs.get("user_follow_up", "")}

NCERT context:
{inputs.get("ncert_context", "")}

Gold/reference coach:
{json.dumps(gold, ensure_ascii=False) if gold else ""}

Candidate coach:
{json.dumps(coach, ensure_ascii=False)}
""".strip()

        try:
            raw = judge_llm(prompt)
        except Exception as exc:
            return {
                "key": "required_llm_followup_judge",
                "score": 0.0,
                "comment": f"judge call failed: {exc}",
                "hard_rule_violated": True,
                "judge_available": False,
            }

        parsed = _json_from_text(raw)
        if not parsed:
            return {
                "key": "required_llm_followup_judge",
                "score": 0.0,
                "comment": f"judge returned invalid JSON: {str(raw)[:160]}",
                "hard_rule_violated": True,
                "judge_available": False,
            }

        action_score = _coerce_score(parsed.get("action_compliance_score"))
        context_score = _coerce_score(parsed.get("context_retention_score"))
        reveal_score = _coerce_score(parsed.get("reveal_safety_score"))
        usefulness_score = _coerce_score(parsed.get("correctness_or_usefulness_score"))
        format_score = _coerce_score(parsed.get("format_score"))
        comment = str(parsed.get("comment", "")).strip()

        score = round(
            (0.25 * action_score)
            + (0.20 * context_score)
            + (0.25 * reveal_score)
            + (0.22 * usefulness_score)
            + (0.08 * format_score),
            3,
        )

        hard = action_score < 0.65 or reveal_score < 0.75 or usefulness_score < 0.60 or format_score < 0.65

        return {
            "key": "required_llm_followup_judge",
            "score": score,
            "comment": (
                f"action={action_score:.2f} context={context_score:.2f} reveal={reveal_score:.2f} "
                f"usefulness={usefulness_score:.2f} format={format_score:.2f} | {comment}"
            ),
            "action_compliance_score": action_score,
            "context_retention_score": context_score,
            "reveal_safety_score": reveal_score,
            "correctness_or_usefulness_score": usefulness_score,
            "format_score": format_score,
            "hard_rule_violated": hard,
            "judge_available": True,
        }

    return required_llm_followup_judge


def build_per_example_evaluators(judge_llm: Callable[[str], str]) -> list[Callable]:
    if judge_llm is None or not callable(judge_llm):
        raise ValueError("Agent 22 evaluation requires judge_llm. Use build_per_example_evaluators(judge_llm).")

    return [
        schema_validity,
        action_compliance_code,
        reveal_level_and_answer_policy,
        context_retention_code,
        latex_and_formatting_code,
        make_required_llm_followup_judge(judge_llm),
    ]


# ---------------------------------------------------------------------------
# Summary evaluator
# ---------------------------------------------------------------------------

def problem_solver_followup_severity_summary(runs: list, examples: list) -> dict:
    if len(runs) != len(examples):
        return {
            "key": "problem_solver_followup_severity_summary",
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

        action = action_compliance_code(run, example)
        reveal = reveal_level_and_answer_policy(run, example)
        context = context_retention_code(run, example)
        fmt = latex_and_formatting_code(run, example)
        llm = _extract_required_llm_feedback(run)

        for result in (action, reveal, fmt):
            if result.get("hard_rule_violated"):
                tier_0.append({"example_id": getattr(example, "id", None), "reason": f"{result['key']} hard failure: {result['comment']}"})

        if context["score"] == 0.0:
            tier_0.append({"example_id": getattr(example, "id", None), "reason": f"context_retention_code failed: {context['comment']}"})

        if llm is not None:
            if llm.get("hard_rule_violated") or llm.get("score", 0.0) < 0.68:
                tier_0.append({"example_id": getattr(example, "id", None), "reason": f"LLM judge hard failure: {llm.get('comment', '')}"})
            elif llm.get("score", 1.0) < 0.82:
                tier_1 += 1
                tier_1_applicable += 1

        tier_1_applicable += 5
        for result in (action, reveal, context, fmt):
            if result["score"] < 1.0:
                tier_1 += 1

        llm_ok = True if llm is None else llm.get("score", 0.0) >= 0.82
        if action["score"] == reveal["score"] == context["score"] == fmt["score"] == 1.0 and llm_ok:
            variation_passes[variation] = variation_passes.get(variation, 0) + 1

    tier_1_rate = tier_1 / tier_1_applicable if tier_1_applicable else 0.0
    per_variation = {v: round(variation_passes.get(v, 0) / total, 3) for v, total in variation_totals.items()}

    recommendation = "BLOCK" if tier_0 else ("REVIEW" if tier_1_rate > 0.18 else "OK")

    return {
        "key": "problem_solver_followup_severity_summary",
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
            if val.get("key") == "required_llm_followup_judge":
                return val
            maybe = val.get("required_llm_followup_judge")
            if isinstance(maybe, dict):
                return maybe
            if isinstance(maybe, (int, float)):
                return {
                    "key": "required_llm_followup_judge",
                    "score": float(maybe),
                    "comment": "score extracted from run feedback mapping",
                    "hard_rule_violated": float(maybe) < 0.68,
                }
        if isinstance(val, list):
            for item in val:
                if isinstance(item, dict) and item.get("key") == "required_llm_followup_judge":
                    return item
    return None


# ---------------------------------------------------------------------------
# Public registries
# ---------------------------------------------------------------------------

PER_EXAMPLE_EVALUATORS_CODE_ONLY = [
    schema_validity,
    action_compliance_code,
    reveal_level_and_answer_policy,
    context_retention_code,
    latex_and_formatting_code,
]

PER_EXAMPLE_EVALUATORS = None

SUMMARY_EVALUATORS = [problem_solver_followup_severity_summary]
