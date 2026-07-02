"""
studio_system_json_evaluators.py

LangSmith custom evaluators for Agent 10: Studio System JSON.

Agent role:
- Shared Studio system wrapper for structured educational generation.
- Enforces format discipline:
  - JSON-only when the task instruction requests JSON.
  - Markdown-only when the task instruction requests Markdown.
- Does not independently decide the pedagogy; Agents 11–14 provide the paired
  task templates for quiz, flashcards, mind map, slide deck.

Production dependencies:
- Inputs:
    context: str
    task_instruction: str
- Outputs:
    json_output: Any    # for JSON tasks
    markdown_output: str # for Markdown tasks
- Depends on retrieved Studio context from vector store. Studio retrieval may
  use Query Rewriter (#2) upstream, but Agent 10 itself should only require
  `context` and `task_instruction`.

Design choice:
- Code-first, not LLM/hybrid.
- Criticality: Tier 3 but foundational for Studio format reliability.
- The major failures are deterministic:
  invalid JSON, wrong object/array shape, markdown fences, trailing prose,
  fabricated terms/numbers, empty-context fabrication, and markdown/JSON mode mix.
- Avoid an LLM judge here to prevent overfitting and extra cost. Content richness
  is evaluated more deeply in Agents 11–14.

LangSmith usage:
    from studio_system_json_evaluators import PER_EXAMPLE_EVALUATORS, SUMMARY_EVALUATORS

    client.evaluate(
        target_fn,
        data="nbm-prompt-studio_system_json",
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

ALLOWED_KEYS = {"json_output", "markdown_output"}

JSON_HINTS = {
    "json", "array", "object", "valid json", "{", "}", "[", "]",
}

MARKDOWN_HINTS = {
    "markdown", "mind map", "outline", "headings", "bullets", "slide deck",
}

BANNED_FENCE = "```"

BANNED_PATTERNS = {
    "as an ai language model",
    "i cannot access",
    "i don't have access",
}

EMPTY_CONTEXT_MARKERS = {
    "", "none", "n/a", "no context", "empty", "not provided",
}

NO_FABRICATION_SAFE_OUTPUTS = {
    "[]", "{}",
}

SUPPORTED_JSON_TYPES = (dict, list)

# Some common words that should not be treated as invented educational terms.
GENERIC_WORDS = {
    "return", "json", "array", "object", "objects", "keys", "valid", "only",
    "no", "markdown", "using", "excerpt", "context", "source", "content",
    "term", "definition", "formula", "quantity", "title", "summary",
    "sections", "section", "bullet", "bullets", "heading", "headings",
    "clean", "output", "exactly", "with", "each", "key", "pairs", "facts",
    "concept", "concepts", "question", "answer", "options", "correct",
    "student", "learner", "learners",
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


def _contains_any(text: str, needles) -> bool:
    t = _norm(text)
    return any(_norm(n) in t for n in needles)


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9Ωμ°/+=∩∪^²³().-]+", _norm(text)))


def _content_tokens(text: str) -> set[str]:
    stop = {
        "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with",
        "is", "are", "was", "were", "be", "been", "being", "this", "that",
        "it", "as", "by", "from", "source", "context", "excerpt", "return",
        "json", "markdown", "object", "array", "key", "keys", "valid",
    }
    return {t for t in _tokens(text) if len(t) > 2 and t not in stop}


def _jaccard(a: str, b: str) -> float:
    ta, tb = _content_tokens(a), _content_tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def _is_empty_context(context: str) -> bool:
    return _norm(context) in EMPTY_CONTEXT_MARKERS or _word_count(context) < 3


def _looks_like_json_task(task_instruction: str, variation: str = "") -> bool:
    t = _norm(task_instruction)
    if variation.startswith("json"):
        return True
    if "markdown" in t and "json" not in t:
        return False
    return any(h in t for h in JSON_HINTS)


def _looks_like_markdown_task(task_instruction: str, variation: str = "") -> bool:
    t = _norm(task_instruction)
    if variation == "markdown_only":
        return True
    return any(h in t for h in MARKDOWN_HINTS) and "json" not in t


def _serialize_output(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return str(value)


def _parse_json_output(value: Any) -> tuple[bool, Any, str]:
    """
    Returns (valid, parsed, raw_text).
    Accepts already-parsed dict/list or JSON string.
    Rejects markdown-fenced JSON and trailing prose.
    """
    if isinstance(value, SUPPORTED_JSON_TYPES):
        return True, value, json.dumps(value, ensure_ascii=False)

    if not isinstance(value, str):
        return False, None, str(value)

    raw = value.strip()
    if not raw:
        return False, None, raw

    if BANNED_FENCE in raw:
        return False, None, raw

    try:
        parsed = json.loads(raw)
    except Exception:
        return False, None, raw

    if not isinstance(parsed, SUPPORTED_JSON_TYPES):
        return False, parsed, raw

    # json.loads rejects trailing prose, so if parse passed, raw is clean.
    return True, parsed, raw


def _get_output_payload(out: dict) -> tuple[str, Any]:
    if "json_output" in out:
        return "json_output", out.get("json_output")
    if "markdown_output" in out:
        return "markdown_output", out.get("markdown_output")
    return "", None


def _flatten_json_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join([str(k) + " " + _flatten_json_text(v) for k, v in value.items()])
    if isinstance(value, list):
        return " ".join(_flatten_json_text(x) for x in value)
    return str(value)


def _extract_expected_count(task_instruction: str) -> Optional[int]:
    text = _norm(task_instruction)
    m = re.search(r"\bexactly\s+(\d+)\b", text)
    if m:
        return int(m.group(1))
    m = re.search(r"\bof\s+(\d+)\s+objects\b", text)
    if m:
        return int(m.group(1))
    m = re.search(r"\b(\d+)\s+(?:objects|items|terms|formulas|sections|cards|questions)\b", text)
    if m:
        return int(m.group(1))
    return None


def _extract_expected_keys(task_instruction: str) -> set[str]:
    text = task_instruction or ""
    keys = set()

    # patterns like keys term and definition
    for m in re.findall(r"keys?\s+([a-zA-Z0-9_,/\s{}-]+?)(?:\.|,| using| extracted| only|$)", text, flags=re.IGNORECASE):
        segment = re.sub(r"[{}]", " ", m)
        parts = re.split(r"\s*(?:,|and|/)\s*", segment)
        for p in parts:
            p = p.strip(" .:-_").lower()
            if p and len(p) <= 30 and p not in GENERIC_WORDS:
                keys.add(p)

    # patterns like {term, definition} or {formula and quantity}
    for m in re.findall(r"\{([^}]+)\}", text):
        parts = re.split(r"\s*(?:,|and|/)\s*", m)
        for p in parts:
            p = p.strip(" .:-_").lower()
            if p and len(p) <= 30 and p not in GENERIC_WORDS:
                keys.add(p)

    # common "with keys formula and quantity" without terminal punctuation
    if not keys:
        common = {"term", "definition", "formula", "quantity", "title", "summary", "sections"}
        for c in common:
            if re.search(rf"\b{re.escape(c)}\b", text, flags=re.IGNORECASE):
                keys.add(c)

    return keys


def _extract_specific_terms(text: str) -> set[str]:
    """
    Extract possible factual terms/numbers/formulas.
    This is a conservative hallucination screen, not a complete NER system.
    """
    if not text:
        return set()

    found = set()

    # formula-ish strings
    for m in re.findall(r"\b[A-Za-zρΔ][A-Za-z0-9_]*\s*=\s*[^.;,\n]+", text):
        found.add(_norm(m))

    # numbers / values
    for m in re.findall(r"\b\d+(?:\.\d+)?\b", text):
        found.add(_norm(m))

    # Greek/symbol-heavy physics/chemistry tokens
    for m in re.findall(r"[ρΔθΩμ][A-Za-z0-9_/*+^²³·=-]*", text):
        found.add(_norm(m))

    # multi-word capitalized terms
    for m in re.findall(r"\b[A-Z][a-z]+(?:'s)?(?:\s+[A-Z][a-z]+(?:'s)?)+\b", text):
        found.add(_norm(m))

    # key educational tokens, including named laws/theorems/entities
    for m in re.findall(r"\b[A-Za-z][A-Za-z0-9'’-]{3,}\b", text):
        token = _norm(m)
        if token not in GENERIC_WORDS and len(token) > 3:
            found.add(token)

    return found


def _value_items(parsed: Any) -> list[Any]:
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        return list(parsed.values())
    return []


def parse_model_response_to_outputs(raw_text: str) -> dict:
    """
    Defensive parser for raw model text.
    If it looks like JSON, wrap as json_output; otherwise markdown_output.
    """
    if not isinstance(raw_text, str):
        return {}
    text = raw_text.strip()
    if not text:
        return {"markdown_output": ""}

    valid, parsed, _ = _parse_json_output(text)
    if valid:
        return {"json_output": parsed}

    return {"markdown_output": text}


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
    if not present:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": "outputs object is empty",
        }

    extra = present - ALLOWED_KEYS
    if extra:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"unexpected output key(s): {sorted(extra)}",
        }

    if len(present & ALLOWED_KEYS) != 1:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": "exactly one of json_output or markdown_output must be present",
        }

    key, payload = _get_output_payload(out)

    if key == "markdown_output" and not isinstance(payload, str):
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": "markdown_output must be a string",
        }

    if key == "json_output":
        valid, _, raw = _parse_json_output(payload)
        if not valid:
            return {
                "key": "schema_validity",
                "score": 0.0,
                "comment": f"json_output is not valid clean JSON object/array; sample={raw[:120]!r}",
            }

    serialized = _serialize_output(payload)
    if not serialized.strip():
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"{key} is empty",
        }

    return {
        "key": "schema_validity",
        "score": 1.0,
        "comment": "schema valid",
    }


# ---------------------------------------------------------------------------
# Evaluator 2: format_discipline
# ---------------------------------------------------------------------------

def format_discipline(run, example) -> dict:
    """
    Ensures JSON tasks return JSON only and Markdown tasks return Markdown only.
    """
    out = _safe_get_outputs(run)
    inputs = _safe_get_inputs(example)
    variation = _safe_get_variation(example)

    if out is None:
        return {
            "key": "format_discipline",
            "score": 0.0,
            "comment": "outputs missing/malformed",
            "hard_rule_violated": False,
        }

    task = inputs.get("task_instruction", "")
    key, payload = _get_output_payload(out)
    raw = _serialize_output(payload)

    is_json_task = _looks_like_json_task(task, variation)
    is_markdown_task = _looks_like_markdown_task(task, variation)

    if BANNED_FENCE in raw:
        return {
            "key": "format_discipline",
            "score": 0.0,
            "comment": "output contains markdown code fence",
            "hard_rule_violated": True,
        }

    if _contains_any(raw, BANNED_PATTERNS):
        return {
            "key": "format_discipline",
            "score": 0.0,
            "comment": "output contains banned/preamble phrase",
            "hard_rule_violated": True,
        }

    if is_json_task:
        if key != "json_output":
            return {
                "key": "format_discipline",
                "score": 0.0,
                "comment": "JSON task did not return json_output",
                "hard_rule_violated": True,
            }
        valid, parsed, _ = _parse_json_output(payload)
        if not valid:
            return {
                "key": "format_discipline",
                "score": 0.0,
                "comment": "JSON task output is not valid clean JSON",
                "hard_rule_violated": True,
            }
        return {
            "key": "format_discipline",
            "score": 1.0,
            "comment": f"JSON format discipline passed ({type(parsed).__name__})",
            "hard_rule_violated": False,
        }

    if is_markdown_task:
        if key != "markdown_output":
            return {
                "key": "format_discipline",
                "score": 0.0,
                "comment": "Markdown task returned json_output instead of markdown_output",
                "hard_rule_violated": True,
            }
        # Markdown-only tasks should not be a JSON blob.
        valid, _, _ = _parse_json_output(payload)
        if valid:
            return {
                "key": "format_discipline",
                "score": 0.0,
                "comment": "Markdown task returned parseable JSON",
                "hard_rule_violated": True,
            }
        return {
            "key": "format_discipline",
            "score": 1.0,
            "comment": "Markdown format discipline passed",
            "hard_rule_violated": False,
        }

    # Unknown/ambiguous task: accept either key if clean.
    return {
        "key": "format_discipline",
        "score": 1.0,
        "comment": "task mode ambiguous; output key is clean",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 3: schema_shape_match
# ---------------------------------------------------------------------------

def schema_shape_match(run, example) -> dict:
    """
    Checks array/object shape, expected count, and expected object keys when stated.
    """
    out = _safe_get_outputs(run)
    inputs = _safe_get_inputs(example)
    variation = _safe_get_variation(example)

    if out is None:
        return {
            "key": "schema_shape_match",
            "score": 0.0,
            "comment": "outputs missing/malformed",
        }

    task = inputs.get("task_instruction", "")
    key, payload = _get_output_payload(out)

    if key == "markdown_output":
        if _looks_like_markdown_task(task, variation):
            # Basic markdown shape only; deeper content belongs to Agents 13–14.
            md = payload if isinstance(payload, str) else ""
            if not md.strip():
                return {
                    "key": "schema_shape_match",
                    "score": 0.0,
                    "comment": "markdown_output is empty",
                }
            return {
                "key": "schema_shape_match",
                "score": 1.0,
                "comment": "markdown task shape accepted",
            }
        return {
            "key": "schema_shape_match",
            "score": 0.5,
            "comment": "non-JSON output for task without clear markdown instruction",
        }

    valid, parsed, _ = _parse_json_output(payload)
    if not valid:
        return {
            "key": "schema_shape_match",
            "score": 0.0,
            "comment": "json_output invalid; cannot check shape",
        }

    t = _norm(task)
    issues = []

    if "array" in t and not isinstance(parsed, list):
        issues.append("expected_array_got_object")
    if "object" in t and "array" not in t and not isinstance(parsed, dict):
        issues.append("expected_object_got_array")

    expected_count = _extract_expected_count(task)
    if expected_count is not None and isinstance(parsed, list):
        if len(parsed) != expected_count:
            issues.append(f"count_mismatch_expected_{expected_count}_got_{len(parsed)}")

    expected_keys = _extract_expected_keys(task)
    if expected_keys:
        items = parsed if isinstance(parsed, list) else [parsed]
        dict_items = [x for x in items if isinstance(x, dict)]
        if not dict_items:
            issues.append("expected_dict_items_but_none_found")
        else:
            for idx, item in enumerate(dict_items[:10]):
                item_keys = {str(k).strip().lower() for k in item.keys()}
                missing = expected_keys - item_keys
                if missing:
                    issues.append(f"item_{idx}_missing_keys_{sorted(missing)}")
                    break

    if issues:
        hard = any(x.startswith(("expected_array", "expected_object", "count_mismatch", "expected_dict")) for x in issues)
        return {
            "key": "schema_shape_match",
            "score": 0.0 if hard else 0.5,
            "comment": "; ".join(issues),
        }

    return {
        "key": "schema_shape_match",
        "score": 1.0,
        "comment": "schema/count/key shape checks passed",
    }


# ---------------------------------------------------------------------------
# Evaluator 4: grounding
# ---------------------------------------------------------------------------

def grounding(run, example) -> dict:
    """
    Checks that substantive facts in output are supported by context or gold.
    This is a conservative code gate for Agent 10, not a rich pedagogy judge.
    """
    out = _safe_get_outputs(run)
    ref = _safe_get_reference(example)
    inputs = _safe_get_inputs(example)

    if out is None:
        return {
            "key": "grounding",
            "score": 0.0,
            "comment": "outputs missing/malformed",
            "hard_rule_violated": False,
        }

    context = inputs.get("context", "")
    key, payload = _get_output_payload(out)
    output_text = _flatten_json_text(payload) if key == "json_output" else _serialize_output(payload)

    gold_text = ""
    if isinstance(ref, dict):
        _, gold_payload = _get_output_payload(ref)
        gold_text = _flatten_json_text(gold_payload)

    if _is_empty_context(str(context)):
        # Empty-context behavior handled in separate evaluator.
        return {
            "key": "grounding",
            "score": 1.0,
            "comment": "empty context; grounding deferred to empty_context_behavior",
            "hard_rule_violated": False,
        }

    context_terms = _extract_specific_terms(str(context))
    gold_terms = _extract_specific_terms(gold_text)
    output_terms = _extract_specific_terms(output_text)

    allowed_terms = context_terms | gold_terms | _extract_specific_terms(str(inputs.get("task_instruction", "")))

    # Ignore generic keys/format terms.
    unsupported = sorted([
        t for t in output_terms
        if t not in allowed_terms
        and t not in GENERIC_WORDS
        and not any(t in a or a in t for a in allowed_terms if len(a) >= 4)
    ])

    # Allow a little language glue, but not fabricated terms/numbers.
    if len(unsupported) >= 5:
        return {
            "key": "grounding",
            "score": 0.0,
            "comment": f"multiple unsupported terms/facts detected: {unsupported[:10]}",
            "hard_rule_violated": True,
        }

    # Numeric/formula hallucination is more serious.
    numeric_or_formula_unsupported = [
        t for t in unsupported
        if re.search(r"\d|=|[ρΔθΩμ]", t)
    ]
    if numeric_or_formula_unsupported:
        return {
            "key": "grounding",
            "score": 0.0,
            "comment": f"unsupported number/formula/symbol detected: {numeric_or_formula_unsupported[:5]}",
            "hard_rule_violated": True,
        }

    overlap_context = _jaccard(output_text, str(context))
    overlap_gold = _jaccard(output_text, gold_text) if gold_text else 0.0

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
            "comment": f"possible unsupported terms: {unsupported[:5]}",
            "hard_rule_violated": False,
        }

    return {
        "key": "grounding",
        "score": 1.0,
        "comment": f"grounding acceptable; context_overlap={overlap_context:.2f} gold_overlap={overlap_gold:.2f}",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 5: empty_context_behavior
# ---------------------------------------------------------------------------

def empty_context_behavior(run, example) -> dict:
    """
    Empty context should not fabricate educational facts.
    Accepts [] / {} for JSON tasks or a short refusal/no-source message for Markdown.
    """
    out = _safe_get_outputs(run)
    inputs = _safe_get_inputs(example)
    variation = _safe_get_variation(example)

    if out is None:
        return {
            "key": "empty_context_behavior",
            "score": 0.0,
            "comment": "outputs missing/malformed",
            "hard_rule_violated": False,
        }

    context = str(inputs.get("context", ""))
    if variation != "empty_context" and not _is_empty_context(context):
        return {
            "key": "empty_context_behavior",
            "score": 1.0,
            "comment": "not an empty-context case",
            "hard_rule_violated": False,
        }

    key, payload = _get_output_payload(out)
    raw = _serialize_output(payload).strip()

    if key == "json_output":
        valid, parsed, _ = _parse_json_output(payload)
        if not valid:
            return {
                "key": "empty_context_behavior",
                "score": 0.0,
                "comment": "empty-context JSON task returned invalid JSON",
                "hard_rule_violated": True,
            }
        if parsed == [] or parsed == {}:
            return {
                "key": "empty_context_behavior",
                "score": 1.0,
                "comment": "empty context safely returned empty JSON structure",
                "hard_rule_violated": False,
            }
        # Non-empty JSON is dangerous if context is empty.
        return {
            "key": "empty_context_behavior",
            "score": 0.0,
            "comment": "empty context produced non-empty JSON content",
            "hard_rule_violated": True,
        }

    # Markdown task: should be short and honest.
    safe_refusal_markers = {
        "no source content", "not enough source", "cannot generate", "can't generate",
        "no context", "provided excerpt is empty", "please provide source",
    }
    if _word_count(raw) <= 35 and _contains_any(raw, safe_refusal_markers):
        return {
            "key": "empty_context_behavior",
            "score": 1.0,
            "comment": "empty context safely returned short no-source message",
            "hard_rule_violated": False,
        }

    return {
        "key": "empty_context_behavior",
        "score": 0.0,
        "comment": "empty context produced unsupported markdown content",
        "hard_rule_violated": True,
    }


# ---------------------------------------------------------------------------
# Evaluator 6: thin_source_minimality
# ---------------------------------------------------------------------------

def thin_source_minimality(run, example) -> dict:
    """
    Thin sources should produce minimal viable output, not padded invented content.
    """
    out = _safe_get_outputs(run)
    inputs = _safe_get_inputs(example)
    variation = _safe_get_variation(example)

    if out is None:
        return {
            "key": "thin_source_minimality",
            "score": 0.0,
            "comment": "outputs missing/malformed",
        }

    if variation != "thin_source":
        return {
            "key": "thin_source_minimality",
            "score": 1.0,
            "comment": "not a thin-source case",
        }

    context = str(inputs.get("context", ""))
    key, payload = _get_output_payload(out)
    output_text = _flatten_json_text(payload) if key == "json_output" else _serialize_output(payload)

    context_wc = _word_count(context)
    output_wc = _word_count(output_text)

    # Thin context should not explode into long explanations.
    if context_wc <= 25 and output_wc > max(80, context_wc * 6):
        return {
            "key": "thin_source_minimality",
            "score": 0.0,
            "comment": f"thin context over-expanded: context_words={context_wc}, output_words={output_wc}",
        }

    return {
        "key": "thin_source_minimality",
        "score": 1.0,
        "comment": f"thin-source output length acceptable: context_words={context_wc}, output_words={output_wc}",
    }


# ---------------------------------------------------------------------------
# Summary evaluator
# ---------------------------------------------------------------------------

def studio_system_json_severity_summary(runs: list, examples: list) -> dict:
    """
    BLOCK:
    - invalid schema
    - JSON/Markdown mode mismatch
    - fences/trailing non-JSON prose
    - wrong array/object/count shape
    - empty context fabrication
    - unsupported numbers/formulas/multiple facts

    REVIEW:
    - weak grounding / possible unsupported terms
    - thin-source over-expansion
    """
    if len(runs) != len(examples):
        return {
            "key": "studio_system_json_severity_summary",
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

        fmt = format_discipline(run, example)
        shape = schema_shape_match(run, example)
        ground = grounding(run, example)
        empty = empty_context_behavior(run, example)
        thin = thin_source_minimality(run, example)

        for result in (fmt, ground, empty):
            if result.get("hard_rule_violated"):
                tier_0.append({
                    "example_id": getattr(example, "id", None),
                    "reason": f"{result['key']} hard failure: {result['comment']}",
                })

        if shape["score"] == 0.0:
            tier_0.append({
                "example_id": getattr(example, "id", None),
                "reason": f"schema_shape_match failed: {shape['comment']}",
            })

        tier_1_applicable += 5
        if fmt["score"] < 1.0:
            tier_1 += 1
        if shape["score"] < 1.0:
            tier_1 += 1
        if ground["score"] < 1.0:
            tier_1 += 1
        if empty["score"] < 1.0:
            tier_1 += 1
        if thin["score"] < 1.0:
            tier_1 += 1

        if (
            fmt["score"] == 1.0
            and shape["score"] == 1.0
            and ground["score"] == 1.0
            and empty["score"] == 1.0
            and thin["score"] == 1.0
        ):
            variation_passes[variation] = variation_passes.get(variation, 0) + 1

    tier_1_rate = (tier_1 / tier_1_applicable) if tier_1_applicable else 0.0

    per_variation_pass_rate = {
        v: round(variation_passes.get(v, 0) / total, 3)
        for v, total in variation_totals.items()
    }

    if tier_0:
        recommendation = "BLOCK"
    elif tier_1_rate > 0.15:
        recommendation = "REVIEW"
    else:
        recommendation = "OK"

    return {
        "key": "studio_system_json_severity_summary",
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
    format_discipline,
    schema_shape_match,
    grounding,
    empty_context_behavior,
    thin_source_minimality,
]

SUMMARY_EVALUATORS = [
    studio_system_json_severity_summary,
]
