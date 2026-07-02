"""
whole_file_map_summarizer_evaluators.py

LangSmith custom evaluators for Agent 29: Whole File Map Summarizer.

Agent role:
- MAP step in whole-file map-reduce summarization.
- Summarizes batched chunks / document excerpts from a single active source.
- Feeds Agent 30 Whole File Reduce.

Production dependencies:
- Inputs:
    parts: list[str]  # document excerpts / batched chunks from one active source
- Output:
    map_summaries: list[str]  # one concise sentence per part

Dependency note:
- Agent 29 depends on all retrieved/indexed chunks for exactly one active source.
- Agent 30 has a hard dependency on Agent 29's map_summaries.
- Agents 29–30 are only activated for whole-document summary intent + one source
  + USE_WHOLE_FILE_MAP_REDUCE=True.
- If map-reduce succeeds, normal retrieval / RAG chunk retrieval is bypassed.
- If map-reduce fails, the runtime falls back to normal Retrieval → RAG.

Evaluator design:
- Hybrid by default.
- Code gates enforce deterministic MAP contract:
  exact output key, one summary per input part, order/count preservation,
  concise one-sentence summaries, no markdown/bullets, grounded terms only,
  no cross-part mixing, no footer/answer-key leakage, no generic summaries.
- Required LLM judge evaluates semantic coverage, groundedness, and usefulness
  of the per-part summaries for downstream reduce.
- Tier 2: not student-facing final output, but a hard dependency for Agent 30.

LangSmith usage:
    from whole_file_map_summarizer_evaluators import (
        build_per_example_evaluators,
        SUMMARY_EVALUATORS,
    )

    evaluators = build_per_example_evaluators(judge_llm)

Judge callable:
    judge_llm(prompt: str) -> str

Judge must return JSON:
{
  "coverage_score": 0.0-1.0,
  "groundedness_score": 0.0-1.0,
  "one_to_one_score": 0.0-1.0,
  "reduce_usefulness_score": 0.0-1.0,
  "format_score": 0.0-1.0,
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

REQUIRED_INPUT_KEYS = {"parts"}
REQUIRED_OUTPUT_KEYS = {"map_summaries"}

MIN_SUMMARY_WORDS = 6
MAX_SUMMARY_WORDS = 42
MAX_SUMMARY_CHARS = 260

BANNED_PATTERNS = {
    "as an ai language model",
    "i cannot access",
    "i don't have access",
    "not enough context",
    "placeholder",
    "todo",
    "lorem ipsum",
    "map_summaries",
    "valid json",
    "system prompt",
    ".j2",
    "jinja",
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

GENERIC_SUMMARIES = {
    "this part discusses important concepts from the document.",
    "this section covers key points from the source.",
    "this excerpt contains useful information for the student.",
    "this part gives details about the topic.",
    "this chunk contains educational content.",
}

GENERIC_WORDS = {
    "the", "and", "with", "from", "this", "that", "document", "chapter",
    "notes", "question", "questions", "answer", "answers", "summary",
    "topic", "topics", "concept", "concepts", "important", "student",
    "students", "study", "material", "section", "page", "class",
    "source", "text", "contains", "covers", "includes", "part",
    "chunk", "excerpt", "paragraph", "information", "content",
}

TRUNCATION_CUES = {
    "continued",
    "continues",
    "truncated",
    "cut off",
    "...",
    "…",
}

SECTION_OR_PAGE_MARKERS = {
    "section",
    "chapter",
    "unit",
    "exercise",
    "example",
    "figure",
    "table",
    "case study",
    "mcq",
    "question",
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


def _sentence_count(text: str) -> int:
    # Simple but conservative; handles "V = IR." as one sentence.
    stripped = str(text or "").strip()
    if not stripped:
        return 0
    pieces = [p for p in re.split(r"(?<=[.!?])\s+", stripped) if p.strip()]
    return len(pieces)


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9ΩμρΔθ°/+=∩∪^²³().-]+", _norm(text)))


def _content_tokens(text: str) -> set[str]:
    stop = {
        "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with",
        "is", "are", "was", "were", "be", "been", "being", "this", "that",
        "it", "as", "by", "from", "document", "chapter", "source", "text",
        "contains", "covers", "includes", "summary", "part", "chunk", "excerpt",
        "section", "question",
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

    for m in re.findall(r"\b\d+(?:\.\d+)?\s*(?:V|A|Ω|m/s|mol|cm|kg|J|N|pm|eV|K|T|marks?)\b", text or "", flags=re.IGNORECASE):
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


def _strip_part_prefix(text: str) -> str:
    m = re.match(r"^\s*Part\s+\d+\s*:\s*(.+)", text, re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else text.strip()


def _summaries_from_part_keyed_dict(parsed: dict) -> Optional[list[str]]:
    part_items: list[tuple[int, str]] = []
    for key, val in parsed.items():
        m = re.match(r"^\s*Part\s+(\d+)\s*$", str(key), re.IGNORECASE)
        if m and isinstance(val, str) and val.strip():
            part_items.append((int(m.group(1)), _strip_part_prefix(val)))
    if not part_items:
        return None
    part_items.sort(key=lambda x: x[0])
    return [text for _, text in part_items]


def _normalize_summary_list(items: list[Any]) -> Optional[list[str]]:
    if not all(isinstance(x, str) for x in items):
        return None
    return [_strip_part_prefix(x) for x in items]


def _parse_summaries(value: Any) -> tuple[bool, Optional[list[str]], str]:
    if isinstance(value, list):
        normalized = _normalize_summary_list(value)
        if normalized is not None:
            return True, normalized, json.dumps(normalized, ensure_ascii=False)
        return False, None, str(value)

    if not isinstance(value, str):
        return False, None, str(value)

    raw = value.strip()
    if not raw or "```" in raw:
        return False, None, raw

    try:
        parsed = json.loads(raw)
    except Exception:
        parsed = None

    if isinstance(parsed, list):
        normalized = _normalize_summary_list(parsed)
        if normalized is not None:
            return True, normalized, raw

    if isinstance(parsed, dict):
        for key in ("map_summaries", "summaries"):
            items = parsed.get(key)
            if isinstance(items, list):
                normalized = _normalize_summary_list(items)
                if normalized is not None:
                    return True, normalized, raw
        part_keyed = _summaries_from_part_keyed_dict(parsed)
        if part_keyed:
            return True, part_keyed, raw

    # Fallback: parse "Part N: sentence" numbered format used in gold references
    part_summaries = []
    for line in raw.splitlines():
        m = re.match(r"^\s*Part\s+\d+\s*:\s*(.+)", line, re.IGNORECASE)
        if m:
            part_summaries.append(m.group(1).strip())
    if part_summaries:
        return True, part_summaries, raw

    return False, None, raw


def _get_summaries(out: Optional[dict]) -> Optional[list[str]]:
    if not isinstance(out, dict):
        return None
    ok, summaries, _ = _parse_summaries(out.get("map_summaries"))
    return summaries if ok else None


def _get_gold_summaries(ref: Optional[dict]) -> list[str]:
    if not isinstance(ref, dict):
        return []
    ok, summaries, _ = _parse_summaries(ref.get("map_summaries"))
    return summaries if ok else []


def _parts(inputs: dict) -> list[str]:
    value = inputs.get("parts")
    if isinstance(value, list):
        return [str(x) for x in value]
    # Defensive fallback; schema will fail, but helpers should not crash.
    return []


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


def _all_source_text(parts: list[str], ref: Optional[dict]) -> str:
    return "\n".join(parts + _get_gold_summaries(ref))


def _is_truncated_like(text: str) -> bool:
    stripped = str(text or "").strip()
    return (
        stripped.endswith(("...", "…"))
        or _contains_any(stripped, TRUNCATION_CUES)
    )


def parse_model_response_to_outputs(raw_text: str) -> dict:
    """
    Defensive parser for raw model response.
    Accepts:
      - {"map_summaries": ["...", "..."]}    (JSON object)
      - ["...", "..."]                        (raw JSON array)
      - "Part 1: sentence\nPart 2: ..."       (numbered format from v1/v2/v3 prompts)
    """
    if not isinstance(raw_text, str) or not raw_text.strip():
        return {}

    raw = raw_text.strip()

    # Strip code fences
    fence = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw, re.DOTALL)
    if fence:
        raw = fence.group(1).strip()

    def _outputs_from_parsed(parsed: Any) -> Optional[dict]:
        if isinstance(parsed, list):
            normalized = _normalize_summary_list(parsed)
            return {"map_summaries": normalized} if normalized else None
        if isinstance(parsed, dict):
            for key in ("map_summaries", "summaries"):
                items = parsed.get(key)
                if isinstance(items, list):
                    normalized = _normalize_summary_list(items)
                    if normalized:
                        return {"map_summaries": normalized}
            part_keyed = _summaries_from_part_keyed_dict(parsed)
            if part_keyed:
                return {"map_summaries": part_keyed}
        return None

    # Try JSON parse first (object or array)
    try:
        parsed = json.loads(raw)
        out = _outputs_from_parsed(parsed)
        if out:
            return out
    except Exception:
        pass

    # Try extracting a JSON object from inside the text
    obj = re.search(r"\{.*\}", raw, re.DOTALL)
    if obj:
        try:
            parsed = json.loads(obj.group(0))
            out = _outputs_from_parsed(parsed)
            if out:
                return out
        except Exception:
            pass

    # Parse "Part N: sentence" numbered format (output of v1/v2/v3 prompts)
    summaries = []
    for line in raw.splitlines():
        m = re.match(r"^\s*Part\s+\d+\s*:\s*(.+)", line, re.IGNORECASE)
        if m:
            summaries.append(m.group(1).strip())
    if summaries:
        return {"map_summaries": summaries}

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

    if not isinstance(inputs.get("parts"), list) or not all(isinstance(p, str) and p.strip() for p in inputs.get("parts", [])):
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": "parts must be a non-empty list[str]",
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

    ok, summaries, raw = _parse_summaries(out.get("map_summaries"))
    if not ok:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"map_summaries must be clean list[str]; sample={raw[:120]!r}",
        }

    if len(summaries) != len(inputs["parts"]):
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"one summary per part required: summaries={len(summaries)} parts={len(inputs['parts'])}",
        }

    for idx, summary in enumerate(summaries):
        if not isinstance(summary, str) or not summary.strip():
            return {"key": "schema_validity", "score": 0.0, "comment": f"summary {idx} must be non-empty string"}

        if "\n" in summary.strip():
            return {"key": "schema_validity", "score": 0.0, "comment": f"summary {idx} contains newline; expected one sentence"}

        if re.match(r"^\s*(?:[-*]|\d+[.)])\s+", summary):
            return {"key": "schema_validity", "score": 0.0, "comment": f"summary {idx} uses bullet/numbering"}

        wc = _word_count(summary)
        if wc < MIN_SUMMARY_WORDS or wc > MAX_SUMMARY_WORDS:
            return {
                "key": "schema_validity",
                "score": 0.5,
                "comment": f"summary {idx} length outside preferred band: {wc} words",
            }

        if len(summary) > MAX_SUMMARY_CHARS:
            return {
                "key": "schema_validity",
                "score": 0.5,
                "comment": f"summary {idx} exceeds preferred character cap: {len(summary)}",
            }

        # Allow abbreviations, but block clear multi-sentence paragraphs.
        if _sentence_count(summary) > 2:
            return {"key": "schema_validity", "score": 0.0, "comment": f"summary {idx} has too many sentences"}

    text = " ".join(summaries)
    if _contains_any(text, BANNED_PATTERNS):
        return {"key": "schema_validity", "score": 0.0, "comment": "map_summaries contain banned/internal phrase"}

    return {"key": "schema_validity", "score": 1.0, "comment": "schema valid"}


# ---------------------------------------------------------------------------
# Evaluator 2: one_to_one_mapping
# ---------------------------------------------------------------------------

def one_to_one_mapping(run, example) -> dict:
    summaries = _get_summaries(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)
    parts = _parts(inputs)

    if summaries is None:
        return {
            "key": "one_to_one_mapping",
            "score": 0.0,
            "comment": "map_summaries missing/malformed",
            "hard_rule_violated": False,
        }

    if len(summaries) != len(parts):
        return {
            "key": "one_to_one_mapping",
            "score": 0.0,
            "comment": f"summary/part count mismatch: {len(summaries)} vs {len(parts)}",
            "hard_rule_violated": True,
        }

    issues = []
    hard = False

    normalized = [_norm(s) for s in summaries]
    if len(set(normalized)) != len(normalized):
        issues.append("duplicate_map_summaries")
        hard = True

    for idx, (part, summary) in enumerate(zip(parts, summaries)):
        overlap = _jaccard(summary, part)

        # Some very short parts can be tricky; still need a minimal link.
        threshold = 0.08 if _word_count(part) >= 25 else 0.04
        if overlap < threshold:
            issues.append(f"summary_{idx}_weak_overlap_with_own_part:{overlap:.2f}")
            hard = True

        # Cross-part mixing: summary should align best with its own part, or at
        # least not much worse than another part.
        if len(parts) > 1:
            other_scores = [_jaccard(summary, p) for j, p in enumerate(parts) if j != idx]
            if other_scores and max(other_scores) > overlap + 0.10:
                issues.append(f"summary_{idx}_aligns_more_with_other_part:{max(other_scores):.2f}>{overlap:.2f}")
                hard = True

    if hard:
        return {
            "key": "one_to_one_mapping",
            "score": 0.0,
            "comment": "; ".join(issues[:10]),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "one_to_one_mapping",
            "score": 0.5,
            "comment": "; ".join(issues[:10]),
            "hard_rule_violated": False,
        }

    return {
        "key": "one_to_one_mapping",
        "score": 1.0,
        "comment": "one-to-one part summary mapping passed",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 3: grounded_no_hallucination
# ---------------------------------------------------------------------------

def grounded_no_hallucination(run, example) -> dict:
    summaries = _get_summaries(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)
    ref = _safe_get_reference(example)
    parts = _parts(inputs)

    if summaries is None:
        return {
            "key": "grounded_no_hallucination",
            "score": 0.0,
            "comment": "map_summaries missing/malformed",
            "hard_rule_violated": False,
        }

    allowed = _all_source_text(parts, ref)
    issues = []
    hard = False

    allowed_terms = _specific_terms(allowed)
    summary_text = " ".join(summaries)
    produced_terms = _specific_terms(summary_text)

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

    if _contains_any(summary_text, FOOTER_NOISE):
        issues.append("footer/web/noise included in summary")
        hard = True

    if _contains_any(summary_text, ANSWER_KEY_NOISE) and not _contains_any(allowed, ANSWER_KEY_NOISE):
        issues.append("answer-key/solution wording introduced without source support")
        hard = True

    if hard:
        return {
            "key": "grounded_no_hallucination",
            "score": 0.0,
            "comment": "; ".join(issues[:10]),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "grounded_no_hallucination",
            "score": 0.5,
            "comment": "; ".join(issues[:10]),
            "hard_rule_violated": False,
        }

    return {
        "key": "grounded_no_hallucination",
        "score": 1.0,
        "comment": "summaries are grounded with no unsupported facts detected",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 4: compression_and_reduce_usefulness
# ---------------------------------------------------------------------------

def compression_and_reduce_usefulness(run, example) -> dict:
    summaries = _get_summaries(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)
    parts = _parts(inputs)

    if summaries is None:
        return {
            "key": "compression_and_reduce_usefulness",
            "score": 0.0,
            "comment": "map_summaries missing/malformed",
            "hard_rule_violated": False,
        }

    issues = []
    hard = False

    source_words = sum(_word_count(p) for p in parts)
    summary_words = sum(_word_count(s) for s in summaries)

    if source_words > 0:
        compression_ratio = summary_words / source_words
        if source_words >= 150 and compression_ratio > 0.35:
            issues.append(f"weak_compression_ratio:{compression_ratio:.2f}")
            hard = True
        elif source_words >= 80 and compression_ratio > 0.50:
            issues.append(f"summary_too_expansive_ratio:{compression_ratio:.2f}")

    for idx, (part, summary) in enumerate(zip(parts, summaries)):
        if _norm(summary) in GENERIC_SUMMARIES:
            issues.append(f"summary_{idx}_generic_template")
            hard = True

        # Each map summary should include at least one specific retrieval/useful term.
        if len(_specific_terms(summary)) < 2 and _word_count(part) >= 25:
            issues.append(f"summary_{idx}_too_low_signal_for_reduce")

        # Preserve section/page/question cue when the part is structurally important.
        if _contains_any(part, SECTION_OR_PAGE_MARKERS):
            if not _contains_any(summary, SECTION_OR_PAGE_MARKERS) and _jaccard(summary, part) < 0.18:
                issues.append(f"summary_{idx}_may_drop_section_or_question_role")

        # Truncated input should be summarized conservatively.
        if _is_truncated_like(part) and not _contains_any(summary, {"truncated", "continued", "fragment", "excerpt", "partial"}):
            issues.append(f"summary_{idx}_truncated_part_not_marked_as_partial")

    if hard:
        return {
            "key": "compression_and_reduce_usefulness",
            "score": 0.0,
            "comment": "; ".join(issues[:10]),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "compression_and_reduce_usefulness",
            "score": 0.5,
            "comment": "; ".join(issues[:10]),
            "hard_rule_violated": False,
        }

    return {
        "key": "compression_and_reduce_usefulness",
        "score": 1.0,
        "comment": "summaries are compact and useful for reduce",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 5: gold_alignment
# ---------------------------------------------------------------------------

def gold_alignment(run, example) -> dict:
    summaries = _get_summaries(_safe_get_outputs(run))
    ref = _safe_get_reference(example)
    gold = _get_gold_summaries(ref)

    if summaries is None:
        return {"key": "gold_alignment", "score": 0.0, "comment": "map_summaries missing/malformed"}

    if not gold:
        return {"key": "gold_alignment", "score": 1.0, "comment": "no gold summaries supplied; skipped"}

    if len(summaries) != len(gold):
        return {
            "key": "gold_alignment",
            "score": 0.0,
            "comment": f"gold/pred length mismatch: pred={len(summaries)} gold={len(gold)}",
        }

    overlaps = [_jaccard(pred, ref_sum) for pred, ref_sum in zip(summaries, gold)]
    avg = sum(overlaps) / len(overlaps) if overlaps else 0.0
    low = [idx for idx, score in enumerate(overlaps) if score < 0.18]

    if avg < 0.20 or len(low) >= max(1, len(overlaps) // 2):
        return {
            "key": "gold_alignment",
            "score": 0.0,
            "comment": f"low gold alignment avg={avg:.2f}, low_indexes={low[:8]}",
        }

    if avg < 0.32 or low:
        return {
            "key": "gold_alignment",
            "score": 0.5,
            "comment": f"partial gold alignment avg={avg:.2f}, low_indexes={low[:8]}",
        }

    return {
        "key": "gold_alignment",
        "score": 1.0,
        "comment": f"gold alignment passed avg={avg:.2f}",
    }


# ---------------------------------------------------------------------------
# Evaluator 6: required LLM judge
# ---------------------------------------------------------------------------

def make_required_llm_map_summarizer_judge(judge_llm: Callable[[str], str]):
    def required_llm_map_summarizer_judge(run, example) -> dict:
        summaries = _get_summaries(_safe_get_outputs(run))
        inputs = _safe_get_inputs(example)
        ref = _safe_get_reference(example)
        parts = _parts(inputs)

        if summaries is None:
            return {
                "key": "required_llm_map_summarizer_judge",
                "score": 0.0,
                "comment": "map_summaries missing/malformed",
                "hard_rule_violated": True,
                "judge_available": False,
            }

        gold = _get_gold_summaries(ref)
        prompt = f"""
You are evaluating ScholarSync's Whole File Map Summarizer.

Evaluate the candidate map summaries ONLY against the input parts and gold summaries if provided.

Return ONLY valid JSON:
{{
  "coverage_score": <0.0 to 1.0>,
  "groundedness_score": <0.0 to 1.0>,
  "one_to_one_score": <0.0 to 1.0>,
  "reduce_usefulness_score": <0.0 to 1.0>,
  "format_score": <0.0 to 1.0>,
  "comment": "<short reason, max 45 words>"
}}

Scoring guidance:
- coverage_score: each summary preserves the main idea of its corresponding part.
- groundedness_score: no invented facts, numbers, formulas, headings, or claims.
- one_to_one_score: one summary per part, same order, no cross-part mixing.
- reduce_usefulness_score: summaries are compact but informative enough for a final whole-file reduce.
- format_score: concise one-sentence summaries; no bullets, markdown, or paragraphs.

Input parts:
{json.dumps(parts, ensure_ascii=False)}

Gold/reference map_summaries:
{json.dumps(gold, ensure_ascii=False) if gold else ""}

Candidate map_summaries:
{json.dumps(summaries, ensure_ascii=False)}
""".strip()

        try:
            raw = judge_llm(prompt)
        except Exception as exc:
            return {
                "key": "required_llm_map_summarizer_judge",
                "score": 0.0,
                "comment": f"judge call failed: {exc}",
                "hard_rule_violated": False,
                "judge_available": False,
            }

        parsed = _json_from_text(raw)
        if not parsed:
            return {
                "key": "required_llm_map_summarizer_judge",
                "score": 0.0,
                "comment": f"judge returned invalid JSON: {str(raw)[:160]}",
                "hard_rule_violated": False,
                "judge_available": False,
            }

        coverage = _coerce_score(parsed.get("coverage_score"))
        grounded = _coerce_score(parsed.get("groundedness_score"))
        one_to_one = _coerce_score(parsed.get("one_to_one_score"))
        usefulness = _coerce_score(parsed.get("reduce_usefulness_score"))
        fmt = _coerce_score(parsed.get("format_score"))
        comment = str(parsed.get("comment", "")).strip()

        score = round(
            (0.25 * coverage)
            + (0.30 * grounded)
            + (0.20 * one_to_one)
            + (0.17 * usefulness)
            + (0.08 * fmt),
            3,
        )

        hard = coverage < 0.65 or grounded < 0.75 or one_to_one < 0.70 or fmt < 0.65

        return {
            "key": "required_llm_map_summarizer_judge",
            "score": score,
            "comment": (
                f"coverage={coverage:.2f} grounded={grounded:.2f} one_to_one={one_to_one:.2f} "
                f"usefulness={usefulness:.2f} format={fmt:.2f} | {comment}"
            ),
            "coverage_score": coverage,
            "groundedness_score": grounded,
            "one_to_one_score": one_to_one,
            "reduce_usefulness_score": usefulness,
            "format_score": fmt,
            "hard_rule_violated": hard,
            "judge_available": True,
        }

    return required_llm_map_summarizer_judge


def build_per_example_evaluators(judge_llm: Callable[[str], str]) -> list[Callable]:
    if judge_llm is None or not callable(judge_llm):
        raise ValueError("Agent 29 evaluation requires judge_llm. Use build_per_example_evaluators(judge_llm).")

    return [
        schema_validity,
        one_to_one_mapping,
        grounded_no_hallucination,
        compression_and_reduce_usefulness,
        gold_alignment,
        make_required_llm_map_summarizer_judge(judge_llm),
    ]


# ---------------------------------------------------------------------------
# Summary evaluator
# ---------------------------------------------------------------------------

def whole_file_map_summarizer_severity_summary(runs: list, examples: list) -> dict:
    """
    BLOCK:
    - invalid schema / wrong key
    - summary count != part count
    - weak one-to-one mapping or cross-part mixing
    - unsupported numeric/formula/named facts
    - generic summaries
    - LLM judge hard failure

    REVIEW:
    - individual summary length outside band
    - partial gold alignment
    - weak compression/usefulness
    - minor possible unsupported terms
    """
    if len(runs) != len(examples):
        return {
            "key": "whole_file_map_summarizer_severity_summary",
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

        one_to_one = one_to_one_mapping(run, example)
        grounded = grounded_no_hallucination(run, example)
        compression = compression_and_reduce_usefulness(run, example)
        gold = gold_alignment(run, example)
        llm = _extract_required_llm_feedback(run)

        for result in (one_to_one, grounded, compression):
            if result.get("hard_rule_violated"):
                tier_0.append({"example_id": getattr(example, "id", None), "reason": f"{result['key']} hard failure: {result['comment']}"})

        if gold["score"] == 0.0:
            tier_0.append({"example_id": getattr(example, "id", None), "reason": f"gold_alignment failed: {gold['comment']}"})

        if llm is not None:
            if llm.get("hard_rule_violated") or llm.get("score", 0.0) < 0.72:
                tier_0.append({"example_id": getattr(example, "id", None), "reason": f"LLM judge hard failure: {llm.get('comment', '')}"})
            elif llm.get("score", 1.0) < 0.86:
                tier_1 += 1
                tier_1_applicable += 1

        tier_1_applicable += 6
        for result in (schema, one_to_one, grounded, compression, gold):
            if result["score"] < 1.0:
                tier_1 += 1

        llm_ok = True if llm is None else llm.get("score", 0.0) >= 0.86
        if (
            schema["score"] == 1.0
            and one_to_one["score"] == 1.0
            and grounded["score"] == 1.0
            and compression["score"] == 1.0
            and gold["score"] == 1.0
            and llm_ok
        ):
            variation_passes[variation] = variation_passes.get(variation, 0) + 1

    tier_1_rate = tier_1 / tier_1_applicable if tier_1_applicable else 0.0
    per_variation = {v: round(variation_passes.get(v, 0) / total, 3) for v, total in variation_totals.items()}

    recommendation = "BLOCK" if tier_0 else ("REVIEW" if tier_1_rate > 0.16 else "OK")

    return {
        "key": "whole_file_map_summarizer_severity_summary",
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
            if val.get("key") == "required_llm_map_summarizer_judge":
                return val
            maybe = val.get("required_llm_map_summarizer_judge")
            if isinstance(maybe, dict):
                return maybe
            if isinstance(maybe, (int, float)):
                return {
                    "key": "required_llm_map_summarizer_judge",
                    "score": float(maybe),
                    "comment": "score extracted from run feedback mapping",
                    "hard_rule_violated": float(maybe) < 0.72,
                }
        if isinstance(val, list):
            for item in val:
                if isinstance(item, dict) and item.get("key") == "required_llm_map_summarizer_judge":
                    return item
    return None


# ---------------------------------------------------------------------------
# Public registries
# ---------------------------------------------------------------------------

PER_EXAMPLE_EVALUATORS_CODE_ONLY = [
    schema_validity,
    one_to_one_mapping,
    grounded_no_hallucination,
    compression_and_reduce_usefulness,
    gold_alignment,
]

PER_EXAMPLE_EVALUATORS = None

SUMMARY_EVALUATORS = [whole_file_map_summarizer_severity_summary]
