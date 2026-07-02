"""
studio_fallback_legacy_evaluators.py

LangSmith custom evaluators for Agent 15: Studio Fallback Legacy.

Agent role:
- Regression safety net when a primary Studio task `.j2` template is missing.
- It is NOT the happy path. Normal Studio uses Agent 10 + one of Agents 11–14.
- This fallback must still produce a complete, parseable artifact instead of
  crashing or returning a vague one-line outline.

Production dependencies:
- Inputs:
    task_type: str     # one of quiz | flashcards | mind_map | slide_deck
    context: str       # retrieved excerpt, may be empty
    custom_instructions: optional str at runtime
- Output:
    output: str        # full JSON string or Markdown body

Task-specific output contract:
- quiz       -> JSON object with title + questions[]
- flashcards -> JSON array of {"front", "back"} cards
- mind_map   -> Markdown only
- slide_deck -> Markdown only

Design choice:
- Code-first, not LLM/hybrid.
- Criticality: Tier 2 regression safety net. It matters because missing Studio
  templates should degrade gracefully, but the task is still deterministic:
  task_type shape, parseability, no-crash behavior, grounding, empty-context
  behavior, and artifact completeness.
- Do not add an LLM judge here; that would overfit a fallback path and duplicate
  deeper Studio evaluations already handled by Agents 11–14.

LangSmith usage:
    from studio_fallback_legacy_evaluators import PER_EXAMPLE_EVALUATORS, SUMMARY_EVALUATORS

    client.evaluate(
        target_fn,
        data="nbm-prompt-studio_fallback_legacy",
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

REQUIRED_KEYS = {"output"}
ALLOWED_KEYS = {"output"}

VALID_TASK_TYPES = {"quiz", "flashcards", "mind_map", "slide_deck"}

EMPTY_CONTEXT_MARKERS = {"", "none", "n/a", "no context", "empty", "not provided"}

JSON_TASKS = {"quiz", "flashcards"}
MARKDOWN_TASKS = {"mind_map", "slide_deck"}

BANNED_FENCES = "```"

INTERNAL_LEAKS = {
    "legacy fallback mode",
    "filenotfounderror",
    "file not found",
    "missing template",
    "fallback_task_prompt",
    "studioservice",
    "_load_prompt_template",
    "j2 template",
    "prompt file",
}

VAGUE_FAILURE_PHRASES = {
    "i cannot generate",
    "i can't generate",
    "not enough information",
    "please provide context",
    "unable to create",
    "cannot access",
    "i don't have access",
}

BANNED_PATTERNS = {
    "as an ai language model",
}

SOURCE_CLAIM_PATTERNS = [
    r"\bpage\s+\d+\b",
    r"\[page\s*\d+\]",
    r"\bcitation\b",
    r"\bfigure\s+\d+\b",
    r"\bsource\s+says\b",
]

GENERIC_STUDY_TERMS = {
    "study", "review", "practice", "self-testing", "self testing", "flashcards",
    "cornell", "notes", "summary", "revise", "recall", "schedule", "planner",
    "active recall", "spaced repetition", "key takeaways", "conclusion",
}

GENERIC_WORDS = {
    "quiz", "question", "questions", "option", "options", "answer", "correct",
    "explanation", "flashcard", "flashcards", "front", "back", "mind", "map",
    "slide", "slides", "deck", "title", "bullet", "bullets", "source", "context",
    "study", "review", "practice", "student", "students", "chapter", "concept",
    "definition", "formula", "key", "takeaway", "takeaways", "summary",
}

NO_SOURCE_VARIATIONS = {"no_source", "empty_context"}

QUIZ_REQUIRED = {"title", "questions"}
QUESTION_REQUIRED = {"question", "options", "correct_answer", "explanation"}
FLASHCARD_REQUIRED = {"front", "back"}

MIN_QUIZ_QUESTIONS = 3
MAX_QUIZ_QUESTIONS = 7
MIN_FLASHCARDS = 3
MAX_FLASHCARDS = 8
MIN_SLIDES = 3
MAX_SLIDES = 6


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
        "it", "as", "by", "from", "source", "context", "excerpt", "question",
        "answer", "option", "slide", "card", "front", "back", "title",
        "bullet", "bullets",
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
    return any(re.search(p, text or "", flags=re.IGNORECASE) for p in patterns)


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def _is_empty_context(context: str) -> bool:
    return _norm(context) in EMPTY_CONTEXT_MARKERS or _word_count(context) < 3


def _get_task_type(inputs: dict) -> str:
    return _norm(inputs.get("task_type", ""))


def _get_output(out: Optional[dict]) -> Optional[str]:
    if not isinstance(out, dict):
        return None
    val = out.get("output")
    return val if isinstance(val, str) else None


def _get_gold_output(ref: Optional[dict]) -> str:
    if not isinstance(ref, dict):
        return ""
    val = ref.get("output", "")
    return val if isinstance(val, str) else str(val)


def _parse_clean_json(raw: str) -> tuple[bool, Any, str]:
    if not isinstance(raw, str):
        return False, None, str(raw)
    text = raw.strip()
    if not text:
        return False, None, text
    if BANNED_FENCES in text:
        return False, None, text
    try:
        parsed = json.loads(text)
    except Exception:
        return False, None, text
    return True, parsed, text


def _quiz_valid(parsed: Any) -> tuple[bool, str]:
    if not isinstance(parsed, dict):
        return False, "quiz output must be a JSON object"

    missing = QUIZ_REQUIRED - set(parsed.keys())
    if missing:
        return False, f"quiz missing keys: {sorted(missing)}"

    if not isinstance(parsed.get("title"), str) or not parsed["title"].strip():
        return False, "quiz.title must be non-empty string"

    questions = parsed.get("questions")
    if not isinstance(questions, list):
        return False, "quiz.questions must be a list"

    for idx, q in enumerate(questions):
        if not isinstance(q, dict):
            return False, f"question {idx} is not an object"

        missing_q = QUESTION_REQUIRED - set(q.keys())
        if missing_q:
            return False, f"question {idx} missing keys: {sorted(missing_q)}"

        options = q.get("options")
        if not isinstance(options, list) or len(options) != 4 or not all(isinstance(o, str) and o.strip() for o in options):
            return False, f"question {idx}.options must contain exactly 4 non-empty strings"

        if q.get("correct_answer") not in options:
            return False, f"question {idx}.correct_answer must exactly match one option"

        if not isinstance(q.get("question"), str) or not q["question"].strip():
            return False, f"question {idx}.question empty"

        if not isinstance(q.get("explanation"), str) or not q["explanation"].strip():
            return False, f"question {idx}.explanation empty"

    return True, "quiz schema valid"


def _flashcards_valid(parsed: Any) -> tuple[bool, str]:
    if not isinstance(parsed, list):
        return False, "flashcards output must be a JSON array"

    for idx, card in enumerate(parsed):
        if not isinstance(card, dict):
            return False, f"card {idx} is not an object"

        missing = FLASHCARD_REQUIRED - set(card.keys())
        if missing:
            return False, f"card {idx} missing keys: {sorted(missing)}"

        for key in FLASHCARD_REQUIRED:
            if not isinstance(card.get(key), str) or not card[key].strip():
                return False, f"card {idx}.{key} must be non-empty string"

    return True, "flashcards schema valid"


def _heading_lines(md: str) -> list[str]:
    return [l for l in (md or "").splitlines() if re.match(r"^\s{0,3}#{1,6}\s+\S+", l)]


def _bullet_lines(md: str) -> list[str]:
    return [l for l in (md or "").splitlines() if re.match(r"^\s*[-*]\s+\S+", l)]


def _mind_map_valid(md: str) -> tuple[bool, str]:
    headings = _heading_lines(md)
    bullets = _bullet_lines(md)

    h1 = [h for h in headings if re.match(r"^\s{0,3}#\s+\S+", h)]
    h2_or_h3 = [h for h in headings if re.match(r"^\s{0,3}#{2,3}\s+\S+", h)]

    if len(h1) != 1:
        return False, "mind_map must have exactly one # hub heading"
    if not h2_or_h3 and len(bullets) < 2:
        return False, "mind_map needs branch headings or bullets"
    if len(bullets) < 2:
        return False, "mind_map needs at least two bullets"

    return True, "mind_map markdown shape valid"


def _slide_deck_sections(md: str) -> list[dict]:
    lines = (md or "").splitlines()
    starts = []
    for i, line in enumerate(lines):
        if re.match(r"^\s{0,3}#\s+slide\s*\d+\s*[:.)-]?\s+\S+", line, flags=re.IGNORECASE):
            starts.append(i)

    sections = []
    for pos, start in enumerate(starts):
        end = starts[pos + 1] if pos + 1 < len(starts) else len(lines)
        title = re.sub(r"^\s{0,3}#\s+slide\s*\d+\s*[:.)-]?\s*", "", lines[start], flags=re.IGNORECASE).strip()
        body = lines[start + 1:end]
        bullets = []
        for line in body:
            m = re.match(r"^\s*[-*]\s+(.+)$", line)
            if m:
                bullets.append(m.group(1).strip())
        sections.append({"title": title, "bullets": bullets})
    return sections


def _slide_deck_valid(md: str) -> tuple[bool, str]:
    sections = _slide_deck_sections(md)
    if not sections:
        return False, "slide_deck must use # Slide N: Title headings"

    for idx, slide in enumerate(sections):
        if not slide["title"]:
            return False, f"slide {idx} missing title"
        if len(slide["bullets"]) < 1:
            return False, f"slide {idx} must have at least one bullet"
        if len(slide["bullets"]) > 7:
            return False, f"slide {idx} has more than 7 bullets"

    last_title = _norm(sections[-1]["title"])
    if "conclusion" not in last_title and "takeaway" not in last_title:
        return False, "final slide should be conclusion/key takeaways"

    return True, "slide_deck markdown shape valid"


def _flatten_artifact_text(task_type: str, output: str) -> str:
    ok, parsed, _ = _parse_clean_json(output)
    if ok:
        try:
            return json.dumps(parsed, ensure_ascii=False)
        except Exception:
            return str(parsed)
    return output


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


def _expected_count_range(task_type: str, context: str) -> tuple[int, int]:
    if task_type == "quiz":
        return MIN_QUIZ_QUESTIONS, MAX_QUIZ_QUESTIONS
    if task_type == "flashcards":
        return MIN_FLASHCARDS, MAX_FLASHCARDS
    if task_type == "slide_deck":
        return MIN_SLIDES, MAX_SLIDES
    return 0, 999


def _artifact_count(task_type: str, output: str) -> int:
    ok, parsed, _ = _parse_clean_json(output)
    if task_type == "quiz" and ok and isinstance(parsed, dict):
        qs = parsed.get("questions")
        return len(qs) if isinstance(qs, list) else 0
    if task_type == "flashcards" and ok and isinstance(parsed, list):
        return len(parsed)
    if task_type == "slide_deck":
        return len(_slide_deck_sections(output))
    if task_type == "mind_map":
        return len(_heading_lines(output)) + len(_bullet_lines(output))
    return 0


def parse_model_response_to_outputs(raw_text: str) -> dict:
    """
    Defensive parser for target functions that return raw artifact text.
    The fallback output key is always `output`.
    """
    if not isinstance(raw_text, str):
        return {}
    text = raw_text.strip()
    if not text:
        return {"output": ""}
    return {"output": text}


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

    output = out.get("output")
    if not isinstance(output, str):
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"output must be string, got {type(output).__name__}",
        }

    if not output.strip():
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": "output is empty",
        }

    return {
        "key": "schema_validity",
        "score": 1.0,
        "comment": "schema valid",
    }


# ---------------------------------------------------------------------------
# Evaluator 2: task_type_honored
# ---------------------------------------------------------------------------

def task_type_honored(run, example) -> dict:
    out = _safe_get_outputs(run)
    inputs = _safe_get_inputs(example)

    output = _get_output(out)
    task_type = _get_task_type(inputs)

    if output is None:
        return {
            "key": "task_type_honored",
            "score": 0.0,
            "comment": "output missing/non-string",
            "hard_rule_violated": False,
        }

    if task_type not in VALID_TASK_TYPES:
        return {
            "key": "task_type_honored",
            "score": 0.0,
            "comment": f"invalid or missing task_type={task_type!r}",
            "hard_rule_violated": True,
        }

    if BANNED_FENCES in output:
        return {
            "key": "task_type_honored",
            "score": 0.0,
            "comment": "output contains markdown code fence",
            "hard_rule_violated": True,
        }

    if task_type == "quiz":
        ok, parsed, raw = _parse_clean_json(output)
        if not ok:
            return {
                "key": "task_type_honored",
                "score": 0.0,
                "comment": f"quiz must be clean JSON object; sample={raw[:120]!r}",
                "hard_rule_violated": True,
            }
        valid, msg = _quiz_valid(parsed)
        return {
            "key": "task_type_honored",
            "score": 1.0 if valid else 0.0,
            "comment": msg,
            "hard_rule_violated": not valid,
        }

    if task_type == "flashcards":
        ok, parsed, raw = _parse_clean_json(output)
        if not ok:
            return {
                "key": "task_type_honored",
                "score": 0.0,
                "comment": f"flashcards must be clean JSON array; sample={raw[:120]!r}",
                "hard_rule_violated": True,
            }
        valid, msg = _flashcards_valid(parsed)
        return {
            "key": "task_type_honored",
            "score": 1.0 if valid else 0.0,
            "comment": msg,
            "hard_rule_violated": not valid,
        }

    # Markdown-only tasks must not be parseable JSON.
    json_ok, _, _ = _parse_clean_json(output)
    if json_ok:
        return {
            "key": "task_type_honored",
            "score": 0.0,
            "comment": f"{task_type} must be Markdown only, not JSON",
            "hard_rule_violated": True,
        }

    valid, msg = _mind_map_valid(output) if task_type == "mind_map" else _slide_deck_valid(output)
    return {
        "key": "task_type_honored",
        "score": 1.0 if valid else 0.0,
        "comment": msg,
        "hard_rule_violated": not valid,
    }


# ---------------------------------------------------------------------------
# Evaluator 3: artifact_completeness
# ---------------------------------------------------------------------------

def artifact_completeness(run, example) -> dict:
    out = _safe_get_outputs(run)
    inputs = _safe_get_inputs(example)

    output = _get_output(out)
    task_type = _get_task_type(inputs)
    context = str(inputs.get("context", ""))

    if output is None:
        return {
            "key": "artifact_completeness",
            "score": 0.0,
            "comment": "output missing/non-string",
            "hard_rule_violated": False,
        }

    # Fallback should be complete, not a vague one-line outline.
    if _word_count(output) < 18 and not (task_type in JSON_TASKS and output.strip() in {"[]", "{}"}):
        return {
            "key": "artifact_completeness",
            "score": 0.0,
            "comment": "output is too short; likely vague outline rather than complete artifact",
            "hard_rule_violated": True,
        }

    if _contains_any(output, INTERNAL_LEAKS):
        return {
            "key": "artifact_completeness",
            "score": 0.0,
            "comment": "output leaks fallback/template internals",
            "hard_rule_violated": True,
        }

    # Empty context is still expected to produce small artifacts for quiz/flashcards/slide_deck,
    # and explicit insufficient-source artifact for mind_map.
    count = _artifact_count(task_type, output)

    if task_type in {"quiz", "flashcards", "slide_deck"}:
        low, high = _expected_count_range(task_type, context)
        if not (low <= count <= high):
            return {
                "key": "artifact_completeness",
                "score": 0.0 if count < low else 0.5,
                "comment": f"{task_type} item count outside fallback range {low}-{high}: got={count}",
                "hard_rule_violated": count < low,
            }

    if task_type == "mind_map":
        if _is_empty_context(context):
            if not _contains_any(output, {"insufficient source", "not enough source", "provide source", "source text"}):
                return {
                    "key": "artifact_completeness",
                    "score": 0.0,
                    "comment": "empty-context mind_map should explicitly signal insufficient source text",
                    "hard_rule_violated": True,
                }
        elif count < 5:
            return {
                "key": "artifact_completeness",
                "score": 0.0,
                "comment": f"mind_map too small to be complete: node_count={count}",
                "hard_rule_violated": True,
            }

    return {
        "key": "artifact_completeness",
        "score": 1.0,
        "comment": f"complete fallback artifact detected; item_count={count}",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 4: grounding_and_empty_context
# ---------------------------------------------------------------------------

def grounding_and_empty_context(run, example) -> dict:
    out = _safe_get_outputs(run)
    ref = _safe_get_reference(example)
    inputs = _safe_get_inputs(example)
    variation = _safe_get_variation(example)

    output = _get_output(out)
    task_type = _get_task_type(inputs)
    context = str(inputs.get("context", ""))
    gold = _get_gold_output(ref)

    if output is None:
        return {
            "key": "grounding_and_empty_context",
            "score": 0.0,
            "comment": "output missing/non-string",
            "hard_rule_violated": False,
        }

    flat = _flatten_artifact_text(task_type, output)

    if _contains_any(flat, BANNED_PATTERNS):
        return {
            "key": "grounding_and_empty_context",
            "score": 0.0,
            "comment": "output contains banned self-reference phrase",
            "hard_rule_violated": True,
        }

    if _regex_any(flat, SOURCE_CLAIM_PATTERNS) and not _regex_any(context + "\n" + gold, SOURCE_CLAIM_PATTERNS):
        return {
            "key": "grounding_and_empty_context",
            "score": 0.0,
            "comment": "output invented page/figure/citation/source claim",
            "hard_rule_violated": True,
        }

    empty = variation in NO_SOURCE_VARIATIONS or _is_empty_context(context)

    if empty:
        # Empty context behavior differs by task:
        # quiz/flashcards/slide_deck may produce small general study-skills artifacts.
        # mind_map should honestly signal insufficient source.
        if task_type == "mind_map":
            safe = _contains_any(flat, {"insufficient source", "not enough source", "provide source", "source text"})
            return {
                "key": "grounding_and_empty_context",
                "score": 1.0 if safe else 0.0,
                "comment": "empty-context mind_map handled safely" if safe else "empty-context mind_map lacks insufficient-source signal",
                "hard_rule_violated": not safe,
            }

        generic_ok = _contains_any(flat, GENERIC_STUDY_TERMS)
        # Avoid chapter-specific invented facts when context is empty. A small general artifact is allowed.
        suspicious_domain_terms = _specific_terms(flat) - _specific_terms(gold) - _specific_terms(" ".join(GENERIC_STUDY_TERMS))
        suspicious_domain_terms = {t for t in suspicious_domain_terms if t not in GENERIC_WORDS and not re.fullmatch(r"\d+", t)}

        if generic_ok and len(suspicious_domain_terms) <= 4:
            return {
                "key": "grounding_and_empty_context",
                "score": 1.0,
                "comment": "empty context safely produced small general artifact",
                "hard_rule_violated": False,
            }

        return {
            "key": "grounding_and_empty_context",
            "score": 0.0,
            "comment": f"empty context produced likely unsupported domain-specific content: {sorted(suspicious_domain_terms)[:8]}",
            "hard_rule_violated": True,
        }

    # Non-empty context: facts should come from context/gold/custom task.
    allowed = _specific_terms(context) | _specific_terms(gold) | _specific_terms(task_type)
    produced = _specific_terms(flat)

    unsupported = sorted([
        t for t in produced
        if t not in allowed
        and t not in GENERIC_WORDS
        and not any(t in a or a in t for a in allowed if len(a) >= 4)
    ])

    numeric_or_formula_bad = [t for t in unsupported if re.search(r"\d|=|[ρΔθΩμ]", t)]
    if numeric_or_formula_bad:
        return {
            "key": "grounding_and_empty_context",
            "score": 0.0,
            "comment": f"unsupported numeric/formula/symbol content: {numeric_or_formula_bad[:5]}",
            "hard_rule_violated": True,
        }

    if len(unsupported) >= 8:
        return {
            "key": "grounding_and_empty_context",
            "score": 0.0,
            "comment": f"many unsupported terms/facts: {unsupported[:10]}",
            "hard_rule_violated": True,
        }

    ctx_overlap = _jaccard(flat, context)
    gold_overlap = _jaccard(flat, gold) if gold else 0.0

    if ctx_overlap >= 0.15 or gold_overlap >= 0.24:
        return {
            "key": "grounding_and_empty_context",
            "score": 1.0,
            "comment": f"grounded; context_overlap={ctx_overlap:.2f} gold_overlap={gold_overlap:.2f}",
            "hard_rule_violated": False,
        }

    if unsupported:
        return {
            "key": "grounding_and_empty_context",
            "score": 0.5,
            "comment": f"possible unsupported terms: {unsupported[:6]}",
            "hard_rule_violated": False,
        }

    return {
        "key": "grounding_and_empty_context",
        "score": 1.0,
        "comment": f"grounding acceptable; context_overlap={ctx_overlap:.2f} gold_overlap={gold_overlap:.2f}",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 5: fallback_gracefulness
# ---------------------------------------------------------------------------

def fallback_gracefulness(run, example) -> dict:
    """
    Regression check: fallback should degrade gracefully, not expose internals,
    crash, or produce a refusal instead of an artifact.
    """
    out = _safe_get_outputs(run)
    inputs = _safe_get_inputs(example)

    output = _get_output(out)
    task_type = _get_task_type(inputs)
    context = str(inputs.get("context", ""))

    if output is None:
        return {
            "key": "fallback_gracefulness",
            "score": 0.0,
            "comment": "output missing/non-string",
            "hard_rule_violated": False,
        }

    issues = []
    hard = False

    if _contains_any(output, INTERNAL_LEAKS):
        issues.append("internal_fallback_or_template_leak")
        hard = True

    if BANNED_FENCES in output:
        issues.append("contains_code_fence")
        hard = True

    # Vague refusal is only acceptable for empty-context mind_map. For other tasks,
    # fallback should still create a small general artifact.
    if _contains_any(output, VAGUE_FAILURE_PHRASES):
        if not (task_type == "mind_map" and _is_empty_context(context)):
            issues.append("vague_failure_instead_of_artifact")
            hard = True

    if "traceback" in _norm(output) or "error:" in _norm(output):
        issues.append("crash_or_error_text_leaked")
        hard = True

    if hard:
        return {
            "key": "fallback_gracefulness",
            "score": 0.0,
            "comment": "; ".join(issues),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "fallback_gracefulness",
            "score": 0.5,
            "comment": "; ".join(issues),
            "hard_rule_violated": False,
        }

    return {
        "key": "fallback_gracefulness",
        "score": 1.0,
        "comment": "fallback graceful/no-crash checks passed",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 6: gold_alignment
# ---------------------------------------------------------------------------

def gold_alignment(run, example) -> dict:
    """
    Lightweight reference alignment. Not exact-match; fallback outputs may vary
    but should stay in the same neighborhood as gold.
    """
    out = _safe_get_outputs(run)
    ref = _safe_get_reference(example)

    output = _get_output(out)
    gold = _get_gold_output(ref)

    if output is None or not gold:
        return {
            "key": "gold_alignment",
            "score": 1.0,
            "comment": "gold unavailable or output missing; neutral pass handled by schema",
        }

    score = _jaccard(output, gold)

    if score >= 0.22:
        return {
            "key": "gold_alignment",
            "score": 1.0,
            "comment": f"aligned with gold; overlap={score:.2f}",
        }

    if score >= 0.12:
        return {
            "key": "gold_alignment",
            "score": 0.5,
            "comment": f"partially aligned with gold; overlap={score:.2f}",
        }

    return {
        "key": "gold_alignment",
        "score": 0.0,
        "comment": f"weak gold alignment; overlap={score:.2f}",
    }


# ---------------------------------------------------------------------------
# Summary evaluator
# ---------------------------------------------------------------------------

def studio_fallback_legacy_severity_summary(runs: list, examples: list) -> dict:
    """
    BLOCK:
    - invalid output key/string
    - task type shape mismatch
    - JSON/Markdown parse failure
    - no-source unsafe artifact
    - fallback internals / crash leakage
    - too-small/vague artifact
    - unsupported formulas/numbers or many unsupported facts

    REVIEW:
    - count/range weakness
    - possible unsupported terms
    - weak gold alignment
    """
    if len(runs) != len(examples):
        return {
            "key": "studio_fallback_legacy_severity_summary",
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

        task = task_type_honored(run, example)
        complete = artifact_completeness(run, example)
        ground = grounding_and_empty_context(run, example)
        grace = fallback_gracefulness(run, example)
        align = gold_alignment(run, example)

        for result in (task, complete, ground, grace):
            if result.get("hard_rule_violated"):
                tier_0.append({
                    "example_id": getattr(example, "id", None),
                    "reason": f"{result['key']} hard failure: {result['comment']}",
                })

        tier_1_applicable += 5
        if task["score"] < 1.0:
            tier_1 += 1
        if complete["score"] < 1.0:
            tier_1 += 1
        if ground["score"] < 1.0:
            tier_1 += 1
        if grace["score"] < 1.0:
            tier_1 += 1
        if align["score"] < 1.0:
            tier_1 += 1

        if (
            task["score"] == 1.0
            and complete["score"] == 1.0
            and ground["score"] == 1.0
            and grace["score"] == 1.0
            and align["score"] == 1.0
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
        "key": "studio_fallback_legacy_severity_summary",
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
    task_type_honored,
    artifact_completeness,
    grounding_and_empty_context,
    fallback_gracefulness,
    gold_alignment,
]

SUMMARY_EVALUATORS = [
    studio_fallback_legacy_severity_summary,
]
