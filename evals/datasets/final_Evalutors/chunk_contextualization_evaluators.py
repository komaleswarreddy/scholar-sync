"""
chunk_contextualization_evaluators.py

LangSmith custom evaluators for Agent 28: Chunk Contextualization.

Agent role:
- Runs per chunk during upload / NCERT indexing when contextual retrieval is enabled.
- Adds a compact, grounded contextual note so the chunk is more retrievable in Pinecone.
- It should NOT rewrite the chunk, summarize the whole document, or add unsupported facts.

Production dependencies:
- Inputs:
    whole_document: str
    chunk_content: str
    token targets: optional keys such as target_tokens, max_tokens,
                   min_tokens, min_context_tokens, max_context_tokens,
                   token_budget, contextualization_token_target
- Optional upstream:
    sketch_json from Agent 26 or Agent 27 may be represented inside whole_document,
    metadata, or an optional example input depending on runtime wiring.
- Output:
    contextualization_json: dict

Recommended flexible internal contract:
    contextualization_json can contain any one of these context fields:
      - contextualization
      - context
      - chunk_context
      - contextualized_context
      - contextualized_chunk
      - summary

    Optional helpful fields:
      - retrieval_keywords: list[str]
      - chunk_role: str
      - confidence: "high" | "low"

Why flexible internal keys:
- The architecture locks the output key as `contextualization_json`.
- The public flow does not lock a nested internal schema.
- The evaluator therefore validates the behavior without overfitting to one
  nested field name.

Dependency note:
- Agent 28 depends on raw whole_document plus chunk_content.
- It may consume Agent 26/27 sketch output, but must also work when sketches are
  bypassed and whole_document excerpt is the only context.
- It feeds Pinecone chunks and is bypassed when contextual retrieval is disabled.

Evaluator design:
- Code-first, not hybrid.
- Criticality: Tier 3 in the architecture, despite being index-time important.
- Main risks are deterministic enough:
  malformed JSON, bloated context, unsupported/invented facts, weak chunk link,
  restating/replacing the full chunk, ignoring token targets, using footer noise,
  or leaking prompt/schema internals.
- No required LLM judge. Add one later only if production failures show semantic
  boundary issues that code cannot catch.

LangSmith usage:
    from chunk_contextualization_evaluators import (
        PER_EXAMPLE_EVALUATORS,
        SUMMARY_EVALUATORS,
    )

    client.evaluate(
        target_fn,
        data="nbm-prompt-chunk_contextualization",
        evaluators=PER_EXAMPLE_EVALUATORS,
        summary_evaluators=SUMMARY_EVALUATORS,
    )
"""

from __future__ import annotations

import json
import math
import re
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REQUIRED_INPUT_KEYS = {"whole_document", "chunk_content"}
REQUIRED_OUTPUT_KEYS = {"contextualization_json"}

CONTEXT_FIELD_ALIASES = {
    "contextualization",
    "context",
    "chunk_context",
    "contextualized_context",
    "contextualized_chunk",
    "summary",
}

OPTIONAL_LIST_FIELDS = {"retrieval_keywords", "keywords", "key_terms"}
OPTIONAL_STRING_FIELDS = {"chunk_role", "section_hint", "source_hint", "confidence"}

VALID_CONFIDENCE = {"high", "low", "medium"}

TOKEN_TARGET_KEYS = {
    "target_tokens",
    "max_tokens",
    "min_tokens",
    "min_context_tokens",
    "max_context_tokens",
    "token_budget",
    "contextualization_token_target",
}

DEFAULT_MIN_CONTEXT_WORDS = 8
DEFAULT_MAX_CONTEXT_WORDS = 85

KEYWORDS_MIN = 0
KEYWORDS_MAX = 12

MAX_CHUNK_COPY_RATIO = 0.75
MAX_CONTEXT_TO_CHUNK_WORD_RATIO = 0.65

BANNED_PATTERNS = {
    "as an ai language model",
    "i cannot access",
    "i don't have access",
    "not enough context",
    "placeholder",
    "todo",
    "lorem ipsum",
    "contextualization_json",
    "valid json",
    "system prompt",
    ".j2",
    "jinja",
}

PROMPT_INTERNALS = {
    "token target",
    "max token",
    "min token",
    "input keys",
    "output keys",
    "schema",
    "json object",
    "return only",
    "do not reveal",
}

FOOTER_NOISE = {
    "downloaded from",
    "printed by",
    "copyright",
    "all rights reserved",
    "page footer",
    "turn over",
    "scanned by",
    "www.",
    "http://",
    "https://",
}

ANSWER_KEY_NOISE = {
    "answer key",
    "marking scheme",
    "solutions:",
    "correct option",
    "solution manual",
}

GENERIC_CONTEXTS = {
    "this chunk discusses important concepts from the document.",
    "this chunk is about key ideas in the source.",
    "this section contains useful information for study.",
    "this chunk provides educational content.",
    "this passage is from the uploaded document.",
}

GENERIC_WORDS = {
    "the", "and", "with", "from", "this", "that", "document", "chapter",
    "notes", "question", "questions", "answer", "answers", "summary",
    "topic", "topics", "concept", "concepts", "important", "student",
    "students", "study", "material", "section", "page", "class",
    "source", "text", "contains", "covers", "includes", "chunk",
    "context", "contextualization", "information", "content",
}

CHUNK_ROLE_CUES = {
    "definition", "formula", "example", "exercise", "derivation", "diagram",
    "table", "case", "question", "mcq", "summary", "procedure", "comparison",
    "application", "proof", "concept", "explanation",
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


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9ΩμρΔθ°/+=∩∪^²³().-]+", _norm(text)))


def _content_tokens(text: str) -> set[str]:
    stop = {
        "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with",
        "is", "are", "was", "were", "be", "been", "being", "this", "that",
        "it", "as", "by", "from", "document", "chapter", "source", "text",
        "contains", "covers", "includes", "summary", "chunk", "context",
        "contextualizes", "passage",
    }
    return {t for t in _tokens(text) if len(t) > 2 and t not in stop}


def _specific_terms(text: str) -> set[str]:
    found = set()

    for tok in _content_tokens(text or ""):
        if tok not in GENERIC_WORDS and len(tok) > 3:
            found.add(tok)

    for m in re.findall(r"\b[A-Za-zρΔ][A-Za-z0-9_]*\s*=\s*[^.;,\n]+", text or ""):
        found.add(_norm(m))

    for m in re.findall(r"\b[A-Z][a-z]+(?:'s)?(?:\s+[A-Z][a-z]+(?:'s)?)+\b", text or ""):
        found.add(_norm(m))

    for m in re.findall(r"[ρΔθΩμ][A-Za-z0-9_/*+^²³·=-]*", text or ""):
        found.add(_norm(m))

    return found


def _jaccard(a: str, b: str) -> float:
    ta, tb = _content_tokens(a), _content_tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _contains_any(text: str, needles) -> bool:
    t = _norm(text)
    return any(_norm(n) in t for n in needles)


def _parse_contextualization(value: Any) -> tuple[bool, Optional[dict], str]:
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


def _get_contextualization(out: Optional[dict]) -> Optional[dict]:
    if not isinstance(out, dict):
        return None
    ok, parsed, _ = _parse_contextualization(out.get("contextualization_json"))
    return parsed if ok else None


def _get_gold_contextualization(ref: Optional[dict]) -> Optional[dict]:
    if not isinstance(ref, dict):
        return None
    ok, parsed, _ = _parse_contextualization(ref.get("contextualization_json"))
    return parsed if ok else None


def _context_field_name(obj: Optional[dict]) -> Optional[str]:
    if not isinstance(obj, dict):
        return None
    for key in CONTEXT_FIELD_ALIASES:
        if key in obj and isinstance(obj.get(key), str) and obj.get(key).strip():
            return key
    return None


def _context_text(obj: Optional[dict]) -> str:
    key = _context_field_name(obj)
    if not key:
        return ""
    return str(obj.get(key, "")).strip()


def _keywords(obj: Optional[dict]) -> list[str]:
    if not isinstance(obj, dict):
        return []
    for key in OPTIONAL_LIST_FIELDS:
        val = obj.get(key)
        if isinstance(val, list) and all(isinstance(x, str) and x.strip() for x in val):
            return [str(x).strip() for x in val]
    return []


def _flatten_contextualization_text(obj: Optional[dict]) -> str:
    if not isinstance(obj, dict):
        return ""
    try:
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return str(obj)


def _parse_token_target(inputs: dict) -> tuple[Optional[int], Optional[int], Optional[int]]:
    """
    Returns (target, min_words, max_words).
    Token-to-word conversion is approximate and intentionally conservative.
    """
    values = {}

    for key in TOKEN_TARGET_KEYS:
        if key in inputs:
            try:
                val = int(inputs.get(key))
                if val > 0:
                    values[key] = val
            except Exception:
                pass

    target = values.get("contextualization_token_target") or values.get("target_tokens") or values.get("token_budget")
    max_tokens = values.get("max_context_tokens") or values.get("max_tokens") or values.get("token_budget")
    min_tokens = values.get("min_context_tokens") or values.get("min_tokens")

    # Approximate words from tokens: 1 word ≈ 1.3 tokens. Use loose bounds.
    target_words = int(target / 1.3) if target else None
    min_words = int(min_tokens / 1.5) if min_tokens else None
    max_words = int(max_tokens / 1.1) if max_tokens else None

    return target_words, min_words, max_words


def _allowed_text(inputs: dict, ref: Optional[dict]) -> str:
    gold = _get_gold_contextualization(ref)
    parts = [
        str(inputs.get("whole_document", "")),
        str(inputs.get("chunk_content", "")),
        json.dumps(inputs.get("sketch_json", ""), ensure_ascii=False) if isinstance(inputs.get("sketch_json"), dict) else str(inputs.get("sketch_json", "")),
        _flatten_contextualization_text(gold),
    ]
    return "\n".join(parts)


def _chunk_role_from_text(chunk: str) -> set[str]:
    roles = set()
    t = _norm(chunk)

    if re.search(r"\b[A-Za-zρΔ][A-Za-z0-9_]*\s*=", chunk or ""):
        roles.add("formula")
    if _contains_any(t, {"define", "definition", "is called", "refers to"}):
        roles.add("definition")
    if _contains_any(t, {"example", "for instance", "illustration"}):
        roles.add("example")
    if _contains_any(t, {"exercise", "question", "q.", "mcq", "choose"}):
        roles.add("exercise")
    if _contains_any(t, {"figure", "diagram", "ray", "graph", "table"}):
        roles.add("diagram")
    if _contains_any(t, {"therefore", "hence", "derive", "proof", "show that"}):
        roles.add("derivation")
    if _contains_any(t, {"compare", "difference", "similarity", "versus"}):
        roles.add("comparison")
    return roles


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


def parse_model_response_to_outputs(raw_text: str) -> dict:
    """
    Defensive parser for raw model response.
    Accepts:
      - {"contextualization_json": {...}}
      - {...} as the contextualization object itself
    """
    if not isinstance(raw_text, str) or not raw_text.strip():
        return {}

    parsed = _json_from_text(raw_text)
    if not isinstance(parsed, dict):
        return {}

    if "contextualization_json" in parsed:
        ok, ctx, _ = _parse_contextualization(parsed["contextualization_json"])
        return {"contextualization_json": ctx if ok else parsed["contextualization_json"]}

    return {"contextualization_json": parsed}


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

    ok, contextualization, raw = _parse_contextualization(out.get("contextualization_json"))
    if not ok:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"contextualization_json is not a clean JSON object; sample={raw[:120]!r}",
        }

    field = _context_field_name(contextualization)
    if not field:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"contextualization_json must include one non-empty context field from {sorted(CONTEXT_FIELD_ALIASES)}",
        }

    ctx = _context_text(contextualization)
    if _word_count(ctx) < DEFAULT_MIN_CONTEXT_WORDS:
        return {
            "key": "schema_validity",
            "score": 0.5,
            "comment": f"context field too thin: {_word_count(ctx)} words",
        }

    if _contains_any(_flatten_contextualization_text(contextualization), BANNED_PATTERNS | PROMPT_INTERNALS):
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": "contextualization_json contains banned/internal phrase",
        }

    # Optional fields should stay simple if present.
    for key, value in contextualization.items():
        if key in OPTIONAL_LIST_FIELDS:
            if not isinstance(value, list) or not all(isinstance(x, str) and x.strip() for x in value):
                return {"key": "schema_validity", "score": 0.0, "comment": f"{key} must be list[str] when present"}
            if len(value) > KEYWORDS_MAX:
                return {"key": "schema_validity", "score": 0.5, "comment": f"{key} too long: {len(value)} items"}
        elif key in OPTIONAL_STRING_FIELDS:
            if value is not None and not isinstance(value, str):
                return {"key": "schema_validity", "score": 0.0, "comment": f"{key} must be string/null when present"}
            if key == "confidence" and isinstance(value, str) and value not in VALID_CONFIDENCE:
                return {"key": "schema_validity", "score": 0.5, "comment": f"confidence should be one of {sorted(VALID_CONFIDENCE)}, got {value!r}"}
        elif key not in CONTEXT_FIELD_ALIASES:
            # Keep extras as review, not block, because nested schema is intentionally flexible.
            return {"key": "schema_validity", "score": 0.5, "comment": f"unexpected optional key: {key!r}"}

    return {
        "key": "schema_validity",
        "score": 1.0,
        "comment": f"schema valid using context field {field!r}",
    }


# ---------------------------------------------------------------------------
# Evaluator 2: token_budget_and_brevity
# ---------------------------------------------------------------------------

def token_budget_and_brevity(run, example) -> dict:
    ctx_obj = _get_contextualization(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)

    if ctx_obj is None:
        return {
            "key": "token_budget_and_brevity",
            "score": 0.0,
            "comment": "contextualization_json missing/malformed",
            "hard_rule_violated": False,
        }

    ctx = _context_text(ctx_obj)
    chunk = str(inputs.get("chunk_content", ""))
    wc = _word_count(ctx)
    target_words, min_words, max_words = _parse_token_target(inputs)

    issues = []
    hard = False

    lo = min_words or DEFAULT_MIN_CONTEXT_WORDS
    hi = max_words or DEFAULT_MAX_CONTEXT_WORDS

    if wc < lo:
        issues.append(f"context_too_short:{wc}_words_min~{lo}")
    if wc > hi:
        issues.append(f"context_too_long:{wc}_words_max~{hi}")
        hard = True

    chunk_wc = max(1, _word_count(chunk))
    # For very short chunks, the contextual note can naturally be similar in length.
    # Apply strict relative bloat only once the source chunk is long enough.
    if chunk_wc >= 60 and wc / chunk_wc > MAX_CONTEXT_TO_CHUNK_WORD_RATIO:
        issues.append(f"context_too_large_relative_to_chunk:{wc}/{chunk_wc}")
        hard = True

    if target_words:
        # Loose target band; do not overfit exact tokens.
        if abs(wc - target_words) > max(20, int(target_words * 0.70)):
            issues.append(f"context_far_from_token_target:words={wc},target_words~{target_words}")

    if _norm(ctx) in GENERIC_CONTEXTS:
        issues.append("generic_contextualization_text")
        hard = True

    if hard:
        return {
            "key": "token_budget_and_brevity",
            "score": 0.0,
            "comment": "; ".join(issues),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "token_budget_and_brevity",
            "score": 0.5,
            "comment": "; ".join(issues),
            "hard_rule_violated": False,
        }

    return {
        "key": "token_budget_and_brevity",
        "score": 1.0,
        "comment": f"context length acceptable: {wc} words",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 3: chunk_linkage
# ---------------------------------------------------------------------------

def chunk_linkage(run, example) -> dict:
    ctx_obj = _get_contextualization(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)

    if ctx_obj is None:
        return {
            "key": "chunk_linkage",
            "score": 0.0,
            "comment": "contextualization_json missing/malformed",
            "hard_rule_violated": False,
        }

    ctx = _context_text(ctx_obj)
    chunk = str(inputs.get("chunk_content", ""))
    whole = str(inputs.get("whole_document", ""))

    issues = []
    hard = False

    chunk_overlap = _jaccard(ctx, chunk)
    whole_overlap = _jaccard(ctx, whole)

    if max(chunk_overlap, whole_overlap) < 0.08:
        issues.append(f"weak_chunk_document_link:chunk={chunk_overlap:.2f},whole={whole_overlap:.2f}")
        hard = True

    # It should contextualize, not merely copy the chunk.
    if _word_count(chunk) >= 20:
        ctx_tokens = _content_tokens(ctx)
        chunk_tokens = _content_tokens(chunk)
        if ctx_tokens and chunk_tokens:
            copy_ratio = len(ctx_tokens & chunk_tokens) / max(1, len(ctx_tokens))
            if copy_ratio > MAX_CHUNK_COPY_RATIO and _word_count(ctx) > 25:
                issues.append(f"context_mostly_copies_chunk:copy_ratio={copy_ratio:.2f}")

    # Should include at least one broader context token from whole_document when possible.
    whole_only = _content_tokens(whole) - _content_tokens(chunk)
    if len(whole_only) >= 8:
        broader_hits = len(_content_tokens(ctx) & whole_only)
        if broader_hits == 0:
            issues.append("no_broader_document_context_terms")
        elif broader_hits == 1:
            issues.append("very_little_broader_document_context")

    if hard:
        return {
            "key": "chunk_linkage",
            "score": 0.0,
            "comment": "; ".join(issues),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "chunk_linkage",
            "score": 0.5,
            "comment": "; ".join(issues),
            "hard_rule_violated": False,
        }

    return {
        "key": "chunk_linkage",
        "score": 1.0,
        "comment": f"chunk/document linkage passed: chunk={chunk_overlap:.2f}, whole={whole_overlap:.2f}",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 4: grounding_and_no_new_facts
# ---------------------------------------------------------------------------

def grounding_and_no_new_facts(run, example) -> dict:
    ctx_obj = _get_contextualization(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)
    ref = _safe_get_reference(example)

    if ctx_obj is None:
        return {
            "key": "grounding_and_no_new_facts",
            "score": 0.0,
            "comment": "contextualization_json missing/malformed",
            "hard_rule_violated": False,
        }

    ctx_text = _flatten_contextualization_text(ctx_obj)
    allowed = _allowed_text(inputs, ref)

    issues = []
    hard = False

    allowed_terms = _specific_terms(allowed)
    produced_terms = _specific_terms(ctx_text)

    unsupported = sorted([
        t for t in produced_terms
        if t not in allowed_terms
        and t not in GENERIC_WORDS
        and not any(t in a or a in t for a in allowed_terms if len(a) >= 4)
    ])

    numeric_formula_bad = [t for t in unsupported if re.search(r"\d|=|[ρΔθΩμ]", t)]
    named_bad = [t for t in unsupported if " " in t and len(t) > 8]

    if numeric_formula_bad:
        issues.append(f"unsupported_numeric_formula_terms:{numeric_formula_bad[:5]}")
        hard = True
    if named_bad:
        issues.append(f"unsupported_named_terms:{named_bad[:5]}")
        hard = True
    if len(unsupported) >= 8:
        issues.append(f"many_unsupported_terms:{unsupported[:8]}")
        hard = True
    elif unsupported:
        issues.append(f"possible_unsupported_terms:{unsupported[:6]}")

    if _contains_any(ctx_text, FOOTER_NOISE | ANSWER_KEY_NOISE):
        issues.append("footer_or_answer_key_noise_in_contextualization")
        hard = True

    if hard:
        return {
            "key": "grounding_and_no_new_facts",
            "score": 0.0,
            "comment": "; ".join(issues[:10]),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "grounding_and_no_new_facts",
            "score": 0.5,
            "comment": "; ".join(issues[:10]),
            "hard_rule_violated": False,
        }

    return {
        "key": "grounding_and_no_new_facts",
        "score": 1.0,
        "comment": "no unsupported contextual facts detected",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 5: retrieval_utility
# ---------------------------------------------------------------------------

def retrieval_utility(run, example) -> dict:
    ctx_obj = _get_contextualization(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)

    if ctx_obj is None:
        return {
            "key": "retrieval_utility",
            "score": 0.0,
            "comment": "contextualization_json missing/malformed",
            "hard_rule_violated": False,
        }

    ctx = _context_text(ctx_obj)
    kws = _keywords(ctx_obj)
    chunk = str(inputs.get("chunk_content", ""))
    whole = str(inputs.get("whole_document", ""))
    sketch_text = json.dumps(inputs.get("sketch_json", ""), ensure_ascii=False) if isinstance(inputs.get("sketch_json"), dict) else str(inputs.get("sketch_json", ""))

    issues = []
    hard = False

    # Context should contain retrieval-significant terms, not just "this passage".
    ctx_specific = _specific_terms(ctx)
    if len(ctx_specific) < 3 and _word_count(chunk) >= 20:
        issues.append("context_has_too_few_specific_retrieval_terms")
        hard = True

    if kws:
        if len(kws) > KEYWORDS_MAX:
            issues.append(f"too_many_keywords:{len(kws)}")
        if len({_norm(k) for k in kws}) != len(kws):
            issues.append("duplicate_keywords")

        scope = " ".join([chunk, whole, sketch_text])
        keyword_hits = sum(1 for kw in kws if _jaccard(kw, scope) >= 0.05 or _norm(kw) in _norm(scope))
        if keyword_hits < max(1, min(4, len(kws) // 2)):
            issues.append(f"few_keywords_trace_to_chunk_or_document:{keyword_hits}/{len(kws)}")

    role = str(ctx_obj.get("chunk_role", "") or ctx_obj.get("section_hint", "") or "")
    inferred_roles = _chunk_role_from_text(chunk)
    if role and inferred_roles:
        if not any(r in _norm(role) for r in inferred_roles):
            issues.append(f"chunk_role_may_not_match_chunk:role={role!r},expected~={sorted(inferred_roles)}")

    if hard:
        return {
            "key": "retrieval_utility",
            "score": 0.0,
            "comment": "; ".join(issues),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "retrieval_utility",
            "score": 0.5,
            "comment": "; ".join(issues),
            "hard_rule_violated": False,
        }

    return {
        "key": "retrieval_utility",
        "score": 1.0,
        "comment": "contextualization is retrieval-useful",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 6: sketch_dependency_handling
# ---------------------------------------------------------------------------

def sketch_dependency_handling(run, example) -> dict:
    ctx_obj = _get_contextualization(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)

    if ctx_obj is None:
        return {
            "key": "sketch_dependency_handling",
            "score": 0.0,
            "comment": "contextualization_json missing/malformed",
        }

    ctx = _context_text(ctx_obj)
    sketch = inputs.get("sketch_json")
    whole = str(inputs.get("whole_document", ""))

    issues = []

    if isinstance(sketch, dict):
        sketch_text = json.dumps(sketch, ensure_ascii=False)
        sketch_overlap = _jaccard(ctx, sketch_text)
        chunk_overlap = _jaccard(ctx, str(inputs.get("chunk_content", "")))

        if sketch_overlap < 0.04 and chunk_overlap < 0.12:
            issues.append(f"sketch_present_but_not_used:sketch={sketch_overlap:.2f},chunk={chunk_overlap:.2f}")

        # Do not copy sketch wholesale; chunk-specific terms must still be present.
        if sketch_overlap > 0.55 and chunk_overlap < 0.08:
            issues.append("context_overuses_document_sketch_without_chunk_specificity")
    else:
        # When sketches are bypassed, context must still ground in raw whole_document.
        if whole.strip() and _jaccard(ctx, whole) < 0.08:
            issues.append("no_sketch_input_and_weak_whole_document_grounding")

    if issues:
        hard = any("without_chunk_specificity" in x for x in issues)
        return {
            "key": "sketch_dependency_handling",
            "score": 0.0 if hard else 0.5,
            "comment": "; ".join(issues),
        }

    return {
        "key": "sketch_dependency_handling",
        "score": 1.0,
        "comment": "sketch/no-sketch dependency handling passed",
    }


# ---------------------------------------------------------------------------
# Evaluator 7: empty_or_thin_chunk_behavior
# ---------------------------------------------------------------------------

def empty_or_thin_chunk_behavior(run, example) -> dict:
    ctx_obj = _get_contextualization(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)

    if ctx_obj is None:
        return {
            "key": "empty_or_thin_chunk_behavior",
            "score": 0.0,
            "comment": "contextualization_json missing/malformed",
            "hard_rule_violated": False,
        }

    chunk = str(inputs.get("chunk_content", ""))
    whole = str(inputs.get("whole_document", ""))
    ctx = _context_text(ctx_obj)

    issues = []
    hard = False

    if _word_count(chunk) < 8:
        # Thin chunks should be conservative and low confidence.
        if _word_count(ctx) > 35:
            issues.append(f"thin_chunk_context_too_expansive:{_word_count(ctx)}_words")
            hard = True

        confidence = str(ctx_obj.get("confidence", "")).lower()
        if confidence and confidence == "high":
            issues.append("thin_chunk_marked_high_confidence")
            hard = True

        if not _contains_any(ctx, {"brief", "fragment", "available", "appears", "limited", "short"}):
            issues.append("thin_chunk_not_marked_as_limited")

    if not whole.strip() and _word_count(ctx) > 25:
        issues.append("missing_whole_document_but_context_is_over_specific")
        hard = True

    if hard:
        return {
            "key": "empty_or_thin_chunk_behavior",
            "score": 0.0,
            "comment": "; ".join(issues),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "empty_or_thin_chunk_behavior",
            "score": 0.5,
            "comment": "; ".join(issues),
            "hard_rule_violated": False,
        }

    return {
        "key": "empty_or_thin_chunk_behavior",
        "score": 1.0,
        "comment": "empty/thin chunk behavior passed",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Summary evaluator
# ---------------------------------------------------------------------------

def chunk_contextualization_severity_summary(runs: list, examples: list) -> dict:
    """
    BLOCK:
    - invalid output key / malformed JSON
    - no context field
    - context too long for token budget
    - weak chunk/document linkage
    - unsupported numeric/formula/named facts
    - context copies sketch/whole document without chunk specificity
    - thin chunk over-specific hallucination

    REVIEW:
    - context a little short/generic
    - few retrieval terms
    - optional keyword/role weaknesses
    - weak sketch usage when sketch is present
    """
    if len(runs) != len(examples):
        return {
            "key": "chunk_contextualization_severity_summary",
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

        brevity = token_budget_and_brevity(run, example)
        linkage = chunk_linkage(run, example)
        grounding = grounding_and_no_new_facts(run, example)
        retrieval = retrieval_utility(run, example)
        sketch = sketch_dependency_handling(run, example)
        thin = empty_or_thin_chunk_behavior(run, example)

        for result in (brevity, linkage, grounding, retrieval, thin):
            if result.get("hard_rule_violated"):
                tier_0.append({"example_id": getattr(example, "id", None), "reason": f"{result['key']} hard failure: {result['comment']}"})

        if sketch["score"] == 0.0:
            tier_0.append({"example_id": getattr(example, "id", None), "reason": f"sketch_dependency_handling failed: {sketch['comment']}"})

        tier_1_applicable += 7
        for result in (schema, brevity, linkage, grounding, retrieval, sketch, thin):
            if result["score"] < 1.0:
                tier_1 += 1

        if (
            schema["score"] == 1.0
            and brevity["score"] == 1.0
            and linkage["score"] == 1.0
            and grounding["score"] == 1.0
            and retrieval["score"] == 1.0
            and sketch["score"] == 1.0
            and thin["score"] == 1.0
        ):
            variation_passes[variation] = variation_passes.get(variation, 0) + 1

    tier_1_rate = tier_1 / tier_1_applicable if tier_1_applicable else 0.0
    per_variation = {v: round(variation_passes.get(v, 0) / total, 3) for v, total in variation_totals.items()}

    recommendation = "BLOCK" if tier_0 else ("REVIEW" if tier_1_rate > 0.18 else "OK")

    return {
        "key": "chunk_contextualization_severity_summary",
        "score": 0.0 if tier_0 else round(1.0 - tier_1_rate, 3),
        "comment": (
            f"ship_recommendation={recommendation} | "
            f"tier_0_blocking_count={len(tier_0)} | "
            f"tier_1_review_rate={tier_1_rate:.3f} | "
            f"evaluator_type=code_first_tier3"
        ),
        "tier_0_blocking_count": len(tier_0),
        "tier_0_blocking_examples": tier_0,
        "tier_1_review_rate": round(tier_1_rate, 3),
        "per_variation_pass_rate": per_variation,
        "ship_recommendation": recommendation,
    }


# ---------------------------------------------------------------------------
# Public registries
# ---------------------------------------------------------------------------

PER_EXAMPLE_EVALUATORS = [
    schema_validity,
    token_budget_and_brevity,
    chunk_linkage,
    grounding_and_no_new_facts,
    retrieval_utility,
    sketch_dependency_handling,
    empty_or_thin_chunk_behavior,
]

SUMMARY_EVALUATORS = [chunk_contextualization_severity_summary]
