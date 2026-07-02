"""
source_question_extraction_evaluators.py

LangSmith custom evaluators for Agent 25: Source Question Extraction.

Agent role:
- Parses uploaded exam/homework PDF text into structured question sections.
- This output is used by source upload / Problem Solver workflows to identify
  questions cleanly from noisy OCR or PDF text.
- It may receive direct PDF text extraction or upstream OCR text from Agent 32.

Production dependencies:
- Inputs:
    document_text: str
- Output:
    sections_json: {
      "sections": [
        {
          "label": str | null,
          "questions": [
            {
              "number": int,
              "preview": str,        # <= 120 chars
              "fullText": str,       # complete question wording
              "pageHint": str | int | null,
              "confidence": "high" | "low"
            }
          ]
        }
      ]
    }

Design choice:
- Hybrid by default.
- Code gates verify deterministic extraction properties:
  JSON schema, section labels, question count/numbering against gold and/or
  document evidence, preview length, fullText overlap, footer/answer-key noise,
  no hallucinated questions, and confidence calibration.
- Required LLM judge verifies semantic question-boundary correctness:
  whether fullText includes the complete question, sub-parts, OR branches,
  assertion/reason pairs, MCQ options, and uncertainty from truncated OCR.
- Tier 1 because bad extraction corrupts downstream source upload and Problem
  Solver flows.

LangSmith usage:
    from source_question_extraction_evaluators import (
        build_per_example_evaluators,
        SUMMARY_EVALUATORS,
    )

    evaluators = build_per_example_evaluators(judge_llm)

Judge callable:
    judge_llm(prompt: str) -> str

Judge must return JSON:
{
  "question_boundary_score": 0.0-1.0,
  "full_text_completeness_score": 0.0-1.0,
  "no_hallucination_score": 0.0-1.0,
  "section_label_score": 0.0-1.0,
  "confidence_calibration_score": 0.0-1.0,
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

REQUIRED_INPUT_KEYS = {"document_text"}
REQUIRED_OUTPUT_KEYS = {"sections_json"}

ROOT_REQUIRED_KEYS = {"sections"}
SECTION_REQUIRED_KEYS = {"label", "questions"}
QUESTION_REQUIRED_KEYS = {"number", "preview", "fullText", "pageHint", "confidence"}

VALID_CONFIDENCE = {"high", "low"}
MAX_PREVIEW_CHARS = 120
MAX_PREVIEW_WORDS = 22
MIN_FULLTEXT_WORDS = 4

BANNED_PATTERNS = {
    "as an ai language model",
    "i cannot access",
    "placeholder",
    "todo",
    "lorem ipsum",
    "sections_json",
    "valid json",
    "schema",
    ".j2",
    "system prompt",
}

FOOTER_NOISE_PATTERNS = {
    "footer scan artifact",
    "page footer",
    "printed by",
    "downloaded from",
    "turn over",
    "copyright",
    "all rights reserved",
    "question bank",
    "testing question bank",
    "each question carries",
    "select the most appropriate option",
    "general instructions",
}

ANSWER_KEY_PATTERNS = {
    "answer key",
    "answers:",
    "solutions:",
    "marking scheme",
    "correct option",
}

SECTION_LABEL_PATTERNS = [
    r"\bsection\s+([a-z])\b",
    r"\bsection\s+([ivxlcdm]+)\b",
    r"\bpart\s+([a-z])\b",
]

QUESTION_START_PATTERNS = [
    r"\bQ\.?\s*(\d{1,3})\b",
    r"\bQuestion\s+(\d{1,3})\b",
    r"^\s*(\d{1,3})[.)]\s+",
]

MCQ_OPTION_PATTERN = r"\(\s*[A-Da-d]\s*\)|^[A-Da-d][.)]\s+"
ASSERTION_REASON_TERMS = {"assertion", "reason", "statement i", "statement ii"}
TRUNCATION_CUES = {"...", "continued", "continues", "truncated", "cut off"}


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
    return set(re.findall(r"[a-zA-Z0-9ΩμρΔθ°/+=∩∪^²³().-]+", _norm(text)))


def _content_tokens(text: str) -> set[str]:
    stop = {
        "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with",
        "is", "are", "was", "were", "be", "been", "being", "this", "that",
        "it", "as", "by", "from", "question", "questions", "section", "page",
        "find", "calculate", "define", "explain", "given", "which", "what",
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


def _parse_sections(value: Any) -> tuple[bool, Optional[dict], str]:
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


def _get_sections_json(out: Optional[dict]) -> Optional[dict]:
    if not isinstance(out, dict):
        return None
    ok, parsed, _ = _parse_sections(out.get("sections_json"))
    return parsed if ok else None


def _get_gold_sections_json(ref: Optional[dict]) -> Optional[dict]:
    if not isinstance(ref, dict):
        return None
    ok, parsed, _ = _parse_sections(ref.get("sections_json"))
    return parsed if ok else None


def _sections(obj: Optional[dict]) -> list[dict]:
    if not isinstance(obj, dict):
        return []
    sections = obj.get("sections")
    return sections if isinstance(sections, list) else []


def _questions(obj: Optional[dict]) -> list[dict]:
    qs = []
    for sec in _sections(obj):
        if isinstance(sec, dict) and isinstance(sec.get("questions"), list):
            qs.extend(q for q in sec["questions"] if isinstance(q, dict))
    return qs


def _question_numbers(obj: Optional[dict]) -> list[int]:
    nums = []
    for q in _questions(obj):
        n = q.get("number")
        if isinstance(n, int) and not isinstance(n, bool):
            nums.append(n)
    return nums


def _questions_by_number(obj: Optional[dict]) -> dict[int, dict]:
    out = {}
    for q in _questions(obj):
        n = q.get("number")
        if isinstance(n, int) and not isinstance(n, bool):
            out[n] = q
    return out


def _flatten_sections_text(obj: Optional[dict]) -> str:
    if not isinstance(obj, dict):
        return ""
    try:
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return str(obj)


def _extract_question_starts(document_text: str) -> list[int]:
    starts = []
    for pattern in QUESTION_START_PATTERNS:
        for m in re.finditer(pattern, document_text or "", flags=re.IGNORECASE | re.MULTILINE):
            try:
                starts.append(int(m.group(1)))
            except Exception:
                continue
    # Preserve first occurrence order while deduping.
    seen = set()
    ordered = []
    for n in starts:
        if n not in seen:
            seen.add(n)
            ordered.append(n)
    return ordered


def _extract_section_labels(document_text: str) -> list[str]:
    labels = []
    for pattern in SECTION_LABEL_PATTERNS:
        for m in re.finditer(pattern, document_text or "", flags=re.IGNORECASE):
            token = str(m.group(1)).upper()
            if len(token) <= 6:
                labels.append(f"Section {token}")
    seen = set()
    ordered = []
    for label in labels:
        if label not in seen:
            seen.add(label)
            ordered.append(label)
    return ordered


def _preview_from_full(full_text: str) -> str:
    text = re.sub(r"\s+", " ", full_text or "").strip()
    return text[:MAX_PREVIEW_CHARS].strip()


def _has_mcq_options(text: str) -> bool:
    return len(re.findall(MCQ_OPTION_PATTERN, text or "", flags=re.IGNORECASE | re.MULTILINE)) >= 2


def _contains_assertion_reason(text: str) -> bool:
    return _contains_any(text, ASSERTION_REASON_TERMS)


def _is_truncated_like(text: str) -> bool:
    stripped = str(text or "").strip()
    if not stripped:
        return False
    return (
        stripped.endswith(("...", "…"))
        or stripped.endswith((" and", " or", " if", "then", "where", "with", "of"))
        or _contains_any(stripped, TRUNCATION_CUES)
    )


def _confidence_should_be_low(question: dict, document_text: str, gold_q: Optional[dict] = None) -> bool:
    if isinstance(gold_q, dict) and gold_q.get("confidence") == "low":
        return True

    full = str(question.get("fullText", ""))
    number = question.get("number")

    if _is_truncated_like(full):
        return True

    # If output question number isn't clearly present in document, boundary is uncertain.
    if isinstance(number, int) and number not in _extract_question_starts(document_text):
        return True

    # OR branches and subparts can be boundary-uncertain when short.
    if _contains_any(full, {" or ", "\nOR\n", "(a)", "(b)", "(i)", "(ii)"}) and _word_count(full) < 18:
        return True

    return False


def _confidence_should_be_high(question: dict, document_text: str) -> bool:
    full = str(question.get("fullText", ""))
    number = question.get("number")
    if _is_truncated_like(full):
        return False
    if isinstance(number, int) and number in _extract_question_starts(document_text):
        return _jaccard(full, document_text) >= 0.12 or _norm(full) in _norm(document_text)
    return False


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
    """
    Defensive parser for raw model responses.
    Accepts:
      - {"sections": [...]}
      - {"sections_json": {"sections": [...]}}
    """
    if not isinstance(raw_text, str) or not raw_text.strip():
        return {}

    parsed = _json_from_text(raw_text)
    if not isinstance(parsed, dict):
        return {}

    if "sections_json" in parsed:
        ok, sections_json, _ = _parse_sections(parsed["sections_json"])
        return {"sections_json": sections_json if ok else parsed["sections_json"]}

    if "sections" in parsed:
        return {"sections_json": parsed}

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

    ok, sections_json, raw = _parse_sections(out.get("sections_json"))
    if not ok:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"sections_json is not a clean JSON object; sample={raw[:120]!r}",
        }

    missing_root = ROOT_REQUIRED_KEYS - set(sections_json.keys())
    extra_root = set(sections_json.keys()) - ROOT_REQUIRED_KEYS
    if missing_root or extra_root:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"root key mismatch -- missing={sorted(missing_root)} extra={sorted(extra_root)}",
        }

    sections = sections_json.get("sections")
    if not isinstance(sections, list):
        return {"key": "schema_validity", "score": 0.0, "comment": "sections must be a list"}

    for s_idx, sec in enumerate(sections):
        if not isinstance(sec, dict):
            return {"key": "schema_validity", "score": 0.0, "comment": f"section {s_idx} is not object"}

        missing_sec = SECTION_REQUIRED_KEYS - set(sec.keys())
        extra_sec = set(sec.keys()) - SECTION_REQUIRED_KEYS
        if missing_sec or extra_sec:
            return {
                "key": "schema_validity",
                "score": 0.0,
                "comment": f"section {s_idx} key mismatch -- missing={sorted(missing_sec)} extra={sorted(extra_sec)}",
            }

        label = sec.get("label")
        if label is not None and not isinstance(label, str):
            return {"key": "schema_validity", "score": 0.0, "comment": f"section {s_idx}.label must be string or null"}

        qs = sec.get("questions")
        if not isinstance(qs, list):
            return {"key": "schema_validity", "score": 0.0, "comment": f"section {s_idx}.questions must be list"}

        for q_idx, q in enumerate(qs):
            if not isinstance(q, dict):
                return {"key": "schema_validity", "score": 0.0, "comment": f"question {s_idx}.{q_idx} is not object"}

            missing_q = QUESTION_REQUIRED_KEYS - set(q.keys())
            extra_q = set(q.keys()) - QUESTION_REQUIRED_KEYS
            if missing_q or extra_q:
                return {
                    "key": "schema_validity",
                    "score": 0.0,
                    "comment": f"question {s_idx}.{q_idx} key mismatch -- missing={sorted(missing_q)} extra={sorted(extra_q)}",
                }

            if not isinstance(q.get("number"), int) or isinstance(q.get("number"), bool):
                return {"key": "schema_validity", "score": 0.0, "comment": f"question {s_idx}.{q_idx}.number must be int"}

            if not isinstance(q.get("preview"), str) or not q["preview"].strip():
                return {"key": "schema_validity", "score": 0.0, "comment": f"question {s_idx}.{q_idx}.preview empty"}
            if len(q["preview"]) > MAX_PREVIEW_CHARS:
                return {"key": "schema_validity", "score": 0.0, "comment": f"question {s_idx}.{q_idx}.preview exceeds {MAX_PREVIEW_CHARS} chars"}

            if not isinstance(q.get("fullText"), str) or _word_count(q["fullText"]) < MIN_FULLTEXT_WORDS:
                return {"key": "schema_validity", "score": 0.0, "comment": f"question {s_idx}.{q_idx}.fullText missing/thin"}

            page_hint = q.get("pageHint")
            if page_hint is not None and not isinstance(page_hint, (str, int)):
                return {"key": "schema_validity", "score": 0.0, "comment": f"question {s_idx}.{q_idx}.pageHint must be str/int/null"}

            if q.get("confidence") not in VALID_CONFIDENCE:
                return {"key": "schema_validity", "score": 0.0, "comment": f"question {s_idx}.{q_idx}.confidence invalid: {q.get('confidence')!r}"}

    text = _flatten_sections_text(sections_json)
    if _contains_any(text, BANNED_PATTERNS):
        return {"key": "schema_validity", "score": 0.0, "comment": "sections_json contains banned/internal phrase"}

    return {"key": "schema_validity", "score": 1.0, "comment": "schema valid"}


# ---------------------------------------------------------------------------
# Evaluator 2: question_count_and_numbers
# ---------------------------------------------------------------------------

def question_count_and_numbers(run, example) -> dict:
    pred = _get_sections_json(_safe_get_outputs(run))
    gold = _get_gold_sections_json(_safe_get_reference(example))
    inputs = _safe_get_inputs(example)

    if pred is None:
        return {
            "key": "question_count_and_numbers",
            "score": 0.0,
            "comment": "sections_json missing/malformed",
            "hard_rule_violated": False,
        }

    pred_nums = _question_numbers(pred)
    gold_nums = _question_numbers(gold)
    doc_nums = _extract_question_starts(str(inputs.get("document_text", "")))

    issues = []
    hard = False

    if len(pred_nums) != len(set(pred_nums)):
        issues.append("duplicate_question_numbers")
        hard = True

    if gold_nums:
        missing = [n for n in gold_nums if n not in pred_nums]
        extra = [n for n in pred_nums if n not in gold_nums]

        if missing:
            issues.append(f"missing_gold_numbers:{missing[:10]}")
            hard = True
        if extra:
            issues.append(f"extra_numbers_not_in_gold:{extra[:10]}")
            hard = True

        if len(pred_nums) != len(gold_nums):
            issues.append(f"question_count_mismatch:pred={len(pred_nums)} gold={len(gold_nums)}")
            hard = True

    elif doc_nums:
        # Without gold, use document starts as softer guide because OCR can be noisy.
        missing_doc = [n for n in doc_nums if n not in pred_nums]
        if len(missing_doc) >= 2:
            issues.append(f"many_document_question_numbers_missing:{missing_doc[:10]}")
            hard = True
        elif missing_doc:
            issues.append(f"possible_missing_document_number:{missing_doc}")

    if hard:
        return {
            "key": "question_count_and_numbers",
            "score": 0.0,
            "comment": "; ".join(issues),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "question_count_and_numbers",
            "score": 0.5,
            "comment": "; ".join(issues),
            "hard_rule_violated": False,
        }

    return {
        "key": "question_count_and_numbers",
        "score": 1.0,
        "comment": f"question numbers/count pass: {pred_nums}",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 3: section_labeling
# ---------------------------------------------------------------------------

def section_labeling(run, example) -> dict:
    pred = _get_sections_json(_safe_get_outputs(run))
    gold = _get_gold_sections_json(_safe_get_reference(example))
    inputs = _safe_get_inputs(example)

    if pred is None:
        return {"key": "section_labeling", "score": 0.0, "comment": "sections_json missing/malformed"}

    pred_labels = [sec.get("label") for sec in _sections(pred) if isinstance(sec, dict)]
    gold_labels = [sec.get("label") for sec in _sections(gold)] if gold else []
    doc_labels = _extract_section_labels(str(inputs.get("document_text", "")))

    issues = []

    if gold_labels:
        if pred_labels != gold_labels:
            issues.append(f"section_labels_mismatch:pred={pred_labels},gold={gold_labels}")
    elif doc_labels:
        non_null_pred = [l for l in pred_labels if l is not None]
        if not non_null_pred:
            issues.append(f"document_has_section_labels_but_output_null:{doc_labels[:5]}")
        else:
            matched = any(_jaccard(str(p), str(d)) >= 0.4 or _norm(p) == _norm(d) for p in non_null_pred for d in doc_labels)
            if not matched:
                issues.append(f"section_labels_not_matching_document:pred={pred_labels},doc={doc_labels[:5]}")
    else:
        # No section header => single section label null.
        if len(pred_labels) == 1 and pred_labels[0] is None:
            pass
        elif all(l is None for l in pred_labels):
            pass
        else:
            issues.append(f"no_document_section_header_but_non_null_label:{pred_labels}")

    if issues:
        hard = any("mismatch" in x for x in issues)
        return {"key": "section_labeling", "score": 0.0 if hard else 0.5, "comment": "; ".join(issues)}

    return {"key": "section_labeling", "score": 1.0, "comment": "section labeling passed"}


# ---------------------------------------------------------------------------
# Evaluator 4: full_text_completeness_code
# ---------------------------------------------------------------------------

def full_text_completeness_code(run, example) -> dict:
    pred = _get_sections_json(_safe_get_outputs(run))
    gold = _get_gold_sections_json(_safe_get_reference(example))
    inputs = _safe_get_inputs(example)

    if pred is None:
        return {
            "key": "full_text_completeness_code",
            "score": 0.0,
            "comment": "sections_json missing/malformed",
            "hard_rule_violated": False,
        }

    doc = str(inputs.get("document_text", ""))
    pred_by_num = _questions_by_number(pred)
    gold_by_num = _questions_by_number(gold)

    issues = []
    hard = False

    for num, pq in pred_by_num.items():
        full = str(pq.get("fullText", ""))
        preview = str(pq.get("preview", ""))

        if len(preview) > MAX_PREVIEW_CHARS:
            issues.append(f"Q{num}_preview_too_long")
            hard = True

        if _word_count(preview) > MAX_PREVIEW_WORDS:
            issues.append(f"Q{num}_preview_too_wordy")

        if preview and _jaccard(preview, full) < 0.08:
            issues.append(f"Q{num}_preview_not_derived_from_fullText")

        gq = gold_by_num.get(num)
        if isinstance(gq, dict):
            gold_full = str(gq.get("fullText", ""))
            overlap = _jaccard(full, gold_full)
            if overlap < 0.45 and _norm(full) not in _norm(gold_full) and _norm(gold_full) not in _norm(full):
                issues.append(f"Q{num}_fullText_low_gold_overlap={overlap:.2f}")
                hard = True

            # If gold includes MCQ options or assertion/reason, prediction should too.
            if _has_mcq_options(gold_full) and not _has_mcq_options(full):
                issues.append(f"Q{num}_missing_mcq_options")
                hard = True
            if _contains_assertion_reason(gold_full) and not _contains_assertion_reason(full):
                issues.append(f"Q{num}_missing_assertion_reason_pair")
                hard = True
            if _contains_any(gold_full, {"(a)", "(b)", "(i)", "(ii)", " or "}) and _jaccard(full, gold_full) < 0.65:
                issues.append(f"Q{num}_may_miss_subparts_or_OR_branch")
        else:
            # Without gold, fullText should still be traceable to doc.
            trace = _jaccard(full, doc)
            if trace < 0.10 and _norm(full) not in _norm(doc):
                issues.append(f"Q{num}_fullText_not_traceable_to_document={trace:.2f}")
                hard = True

        if _contains_any(full, FOOTER_NOISE_PATTERNS):
            issues.append(f"Q{num}_contains_footer_or_instruction_noise")
        if _contains_any(full, ANSWER_KEY_PATTERNS):
            issues.append(f"Q{num}_contains_answer_key_or_solution_noise")
            hard = True

    if hard:
        return {
            "key": "full_text_completeness_code",
            "score": 0.0,
            "comment": "; ".join(issues[:12]),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "full_text_completeness_code",
            "score": 0.5,
            "comment": "; ".join(issues[:12]),
            "hard_rule_violated": False,
        }

    return {
        "key": "full_text_completeness_code",
        "score": 1.0,
        "comment": "fullText/preview completeness checks passed",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 5: no_hallucination_boundaries
# ---------------------------------------------------------------------------

def no_hallucination_boundaries(run, example) -> dict:
    pred = _get_sections_json(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)
    ref = _safe_get_reference(example)
    gold = _get_gold_sections_json(ref)

    if pred is None:
        return {
            "key": "no_hallucination_boundaries",
            "score": 0.0,
            "comment": "sections_json missing/malformed",
            "hard_rule_violated": False,
        }

    doc = str(inputs.get("document_text", ""))
    gold_text = _flatten_sections_text(gold)
    allowed_text = doc + "\n" + gold_text

    issues = []
    hard = False

    for q in _questions(pred):
        num = q.get("number")
        full = str(q.get("fullText", ""))

        # Full question should be drawn from source/gold, not invented.
        trace = max(_jaccard(full, doc), _jaccard(full, gold_text))
        if trace < 0.10 and _norm(full) not in _norm(allowed_text):
            issues.append(f"Q{num}_low_source_trace={trace:.2f}")
            hard = True

        # Do not merge adjacent numbered questions into one fullText.
        other_numbers = [n for n in _extract_question_starts(full) if n != num]
        if other_numbers:
            issues.append(f"Q{num}_may_merge_other_question_numbers:{other_numbers[:5]}")
            hard = True

        # Should not include instructions-only page lines or footer noise.
        if _contains_any(full, FOOTER_NOISE_PATTERNS | ANSWER_KEY_PATTERNS):
            issues.append(f"Q{num}_includes_non_question_noise")
            hard = True

    # If all output numbers are absent from document and gold, likely hallucination.
    pred_nums = set(_question_numbers(pred))
    doc_nums = set(_extract_question_starts(doc))
    gold_nums = set(_question_numbers(gold))
    if pred_nums and not (pred_nums & (doc_nums | gold_nums)):
        issues.append(f"all_predicted_numbers_absent_from_document_and_gold:{sorted(pred_nums)[:10]}")
        hard = True

    if hard:
        return {
            "key": "no_hallucination_boundaries",
            "score": 0.0,
            "comment": "; ".join(issues[:10]),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "no_hallucination_boundaries",
            "score": 0.5,
            "comment": "; ".join(issues[:10]),
            "hard_rule_violated": False,
        }

    return {
        "key": "no_hallucination_boundaries",
        "score": 1.0,
        "comment": "no hallucinated/merged/noisy question boundaries detected",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 6: confidence_calibration
# ---------------------------------------------------------------------------

def confidence_calibration(run, example) -> dict:
    pred = _get_sections_json(_safe_get_outputs(run))
    gold = _get_gold_sections_json(_safe_get_reference(example))
    inputs = _safe_get_inputs(example)

    if pred is None:
        return {"key": "confidence_calibration", "score": 0.0, "comment": "sections_json missing/malformed", "hard_rule_violated": False}

    doc = str(inputs.get("document_text", ""))
    gold_by_num = _questions_by_number(gold)
    issues = []
    hard = False

    for q in _questions(pred):
        num = q.get("number")
        conf = q.get("confidence")
        gold_q = gold_by_num.get(num)

        if isinstance(gold_q, dict):
            gold_conf = gold_q.get("confidence")
            if gold_conf in VALID_CONFIDENCE and conf != gold_conf:
                # Gold low predicted high is worse than high predicted low.
                if gold_conf == "low" and conf == "high":
                    issues.append(f"Q{num}_overconfident:gold_low_pred_high")
                    hard = True
                else:
                    issues.append(f"Q{num}_confidence_mismatch:pred={conf},gold={gold_conf}")

        low_expected = _confidence_should_be_low(q, doc, gold_q)
        high_expected = _confidence_should_be_high(q, doc)

        if low_expected and conf == "high":
            issues.append(f"Q{num}_should_be_low_due_to_uncertain_boundary")
            hard = True

        if high_expected and conf == "low" and not (isinstance(gold_q, dict) and gold_q.get("confidence") == "low"):
            issues.append(f"Q{num}_possibly_underconfident")

    if hard:
        return {
            "key": "confidence_calibration",
            "score": 0.0,
            "comment": "; ".join(issues[:12]),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "confidence_calibration",
            "score": 0.5,
            "comment": "; ".join(issues[:12]),
            "hard_rule_violated": False,
        }

    return {
        "key": "confidence_calibration",
        "score": 1.0,
        "comment": "confidence calibration checks passed",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 7: required LLM judge
# ---------------------------------------------------------------------------

def make_required_llm_source_extraction_judge(judge_llm: Callable[[str], str]):
    def required_llm_source_extraction_judge(run, example) -> dict:
        pred = _get_sections_json(_safe_get_outputs(run))
        gold = _get_gold_sections_json(_safe_get_reference(example))
        inputs = _safe_get_inputs(example)

        if pred is None:
            return {
                "key": "required_llm_source_extraction_judge",
                "score": 0.0,
                "comment": "sections_json missing/malformed",
                "hard_rule_violated": True,
                "judge_available": False,
            }

        prompt = f"""
You are evaluating ScholarSync's Source Question Extraction agent.

Evaluate whether the candidate extraction correctly parses uploaded exam/homework text into structured question sections.

Return ONLY valid JSON:
{{
  "question_boundary_score": <0.0 to 1.0>,
  "full_text_completeness_score": <0.0 to 1.0>,
  "no_hallucination_score": <0.0 to 1.0>,
  "section_label_score": <0.0 to 1.0>,
  "confidence_calibration_score": <0.0 to 1.0>,
  "comment": "<short reason, max 45 words>"
}}

Scoring guidance:
- question_boundary_score: detects all numbered questions and separates them correctly.
- full_text_completeness_score: includes all needed wording, subparts, OR branches, assertion/reason, and MCQ options.
- no_hallucination_score: no invented questions; ignores footers, answer keys, headers, and instructions-only text.
- section_label_score: section labels match document headers; null when no section header.
- confidence_calibration_score: "low" is used for uncertain/truncated OCR boundaries; "high" for clear complete questions.

Document text:
{inputs.get("document_text", "")}

Gold/reference sections_json:
{json.dumps(gold, ensure_ascii=False) if gold else ""}

Candidate sections_json:
{json.dumps(pred, ensure_ascii=False)}
""".strip()

        try:
            raw = judge_llm(prompt)
        except Exception as exc:
            return {
                "key": "required_llm_source_extraction_judge",
                "score": 0.0,
                "comment": f"judge call failed: {exc}",
                "hard_rule_violated": True,
                "judge_available": False,
            }

        parsed = _json_from_text(raw)
        if not parsed:
            return {
                "key": "required_llm_source_extraction_judge",
                "score": 0.0,
                "comment": f"judge returned invalid JSON: {str(raw)[:160]}",
                "hard_rule_violated": True,
                "judge_available": False,
            }

        boundary = _coerce_score(parsed.get("question_boundary_score"))
        complete = _coerce_score(parsed.get("full_text_completeness_score"))
        no_hallucination = _coerce_score(parsed.get("no_hallucination_score"))
        section = _coerce_score(parsed.get("section_label_score"))
        confidence = _coerce_score(parsed.get("confidence_calibration_score"))
        comment = str(parsed.get("comment", "")).strip()

        score = round(
            (0.25 * boundary)
            + (0.30 * complete)
            + (0.25 * no_hallucination)
            + (0.10 * section)
            + (0.10 * confidence),
            3,
        )

        hard = boundary < 0.70 or complete < 0.70 or no_hallucination < 0.80

        return {
            "key": "required_llm_source_extraction_judge",
            "score": score,
            "comment": (
                f"boundary={boundary:.2f} complete={complete:.2f} no_hallucination={no_hallucination:.2f} "
                f"section={section:.2f} confidence={confidence:.2f} | {comment}"
            ),
            "question_boundary_score": boundary,
            "full_text_completeness_score": complete,
            "no_hallucination_score": no_hallucination,
            "section_label_score": section,
            "confidence_calibration_score": confidence,
            "hard_rule_violated": hard,
            "judge_available": True,
        }

    return required_llm_source_extraction_judge


def build_per_example_evaluators(judge_llm: Callable[[str], str]) -> list[Callable]:
    if judge_llm is None or not callable(judge_llm):
        raise ValueError("Agent 25 evaluation requires judge_llm. Use build_per_example_evaluators(judge_llm).")

    return [
        schema_validity,
        question_count_and_numbers,
        section_labeling,
        full_text_completeness_code,
        no_hallucination_boundaries,
        confidence_calibration,
        make_required_llm_source_extraction_judge(judge_llm),
    ]


# ---------------------------------------------------------------------------
# Summary evaluator
# ---------------------------------------------------------------------------

def source_question_extraction_severity_summary(runs: list, examples: list) -> dict:
    if len(runs) != len(examples):
        return {
            "key": "source_question_extraction_severity_summary",
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

        count = question_count_and_numbers(run, example)
        labels = section_labeling(run, example)
        full = full_text_completeness_code(run, example)
        no_hall = no_hallucination_boundaries(run, example)
        conf = confidence_calibration(run, example)
        llm = _extract_required_llm_feedback(run)

        for result in (count, full, no_hall, conf):
            if result.get("hard_rule_violated"):
                tier_0.append({"example_id": getattr(example, "id", None), "reason": f"{result['key']} hard failure: {result['comment']}"})

        if labels["score"] == 0.0:
            tier_0.append({"example_id": getattr(example, "id", None), "reason": f"section_labeling failed: {labels['comment']}"})

        if llm is not None:
            if llm.get("hard_rule_violated") or llm.get("score", 0.0) < 0.72:
                tier_0.append({"example_id": getattr(example, "id", None), "reason": f"LLM judge hard failure: {llm.get('comment', '')}"})
            elif llm.get("score", 1.0) < 0.86:
                tier_1 += 1
                tier_1_applicable += 1

        tier_1_applicable += 6
        for result in (count, labels, full, no_hall, conf):
            if result["score"] < 1.0:
                tier_1 += 1

        llm_ok = True if llm is None else llm.get("score", 0.0) >= 0.86
        if (
            count["score"] == 1.0
            and labels["score"] == 1.0
            and full["score"] == 1.0
            and no_hall["score"] == 1.0
            and conf["score"] == 1.0
            and llm_ok
        ):
            variation_passes[variation] = variation_passes.get(variation, 0) + 1

    tier_1_rate = tier_1 / tier_1_applicable if tier_1_applicable else 0.0
    per_variation = {v: round(variation_passes.get(v, 0) / total, 3) for v, total in variation_totals.items()}

    recommendation = "BLOCK" if tier_0 else ("REVIEW" if tier_1_rate > 0.12 else "OK")

    return {
        "key": "source_question_extraction_severity_summary",
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
            if val.get("key") == "required_llm_source_extraction_judge":
                return val
            maybe = val.get("required_llm_source_extraction_judge")
            if isinstance(maybe, dict):
                return maybe
            if isinstance(maybe, (int, float)):
                return {
                    "key": "required_llm_source_extraction_judge",
                    "score": float(maybe),
                    "comment": "score extracted from run feedback mapping",
                    "hard_rule_violated": float(maybe) < 0.72,
                }
        if isinstance(val, list):
            for item in val:
                if isinstance(item, dict) and item.get("key") == "required_llm_source_extraction_judge":
                    return item
    return None


# ---------------------------------------------------------------------------
# Public registries
# ---------------------------------------------------------------------------

PER_EXAMPLE_EVALUATORS_CODE_ONLY = [
    schema_validity,
    question_count_and_numbers,
    section_labeling,
    full_text_completeness_code,
    no_hallucination_boundaries,
    confidence_calibration,
]

PER_EXAMPLE_EVALUATORS = None

SUMMARY_EVALUATORS = [source_question_extraction_severity_summary]
