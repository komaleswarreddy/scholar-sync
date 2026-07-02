"""
image_ocr_evaluators.py

LangSmith custom evaluators for Agent 32: Image OCR.

Agent role:
- Converts image uploads, scanned PDF page renders, and problem-solver page images
  into plain document text.
- Feeds the source text pipeline, especially Agent 25 Source Question Extraction.
- It is full-page / scan transcription, not diagram-specific label extraction
  (Agent 33 handles figure/diagram labels).

Production dependencies:
- Inputs may include either:
    image_bytes / image_data / image_base64 / image_url / pdf_page_render
  OR the production PDF render fields:
    pdf_source, page_number, render_dpi
- Output:
    extracted_text: str

Dependency note:
- Agent 32 is independent at call time.
- Agent 25 may consume its extracted_text as document_text.
- Agent 32 is bypassed for native text PDFs / non-image uploads.
- Agent 33 is parallel for embedded figure label OCR, not a dependency.

Evaluator design:
- Code-first, not hybrid.
- Criticality: Tier 2. It is not a reasoning generator, but it is a hard upstream
  dependency for scanned/image source pipelines.
- OCR quality is best evaluated with deterministic reference-text metrics:
  normalized character similarity, word recall, number/formula retention,
  question-number retention, layout cue retention, and hallucination checks.
- No required LLM judge. A judge is less reliable than direct text comparison for OCR.

LangSmith usage:
    from image_ocr_evaluators import PER_EXAMPLE_EVALUATORS, SUMMARY_EVALUATORS

    client.evaluate(
        target_fn,
        data="nbm-prompt-image_ocr",
        evaluators=PER_EXAMPLE_EVALUATORS,
        summary_evaluators=SUMMARY_EVALUATORS,
    )

Recommended gold/reference output:
    {"extracted_text": "..."}
"""

from __future__ import annotations

import base64
import json
import re
import difflib
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REQUIRED_OUTPUT_KEYS = {"extracted_text"}

ACCEPTED_IMAGE_INPUT_KEYS = {
    "image_bytes",
    "image_data",
    "image_base64",
    "image_url",
    "pdf_page_render",
    "file_bytes",
    "file_data",
}

ACCEPTED_PDF_RENDER_KEYS = {"pdf_source", "page_number", "render_dpi"}

OPTIONAL_CONTEXT_INPUT_KEYS = {
    "expected_language",
    "source_type",
    "page_hint",
    "ocr_mode",
}

BANNED_PATTERNS = {
    "as an ai language model",
    "i cannot access",
    "i don't have access",
    "unable to read the image",
    "sorry",
    "placeholder",
    "todo",
    "lorem ipsum",
    "extracted_text",
    "valid json",
    "system prompt",
    ".j2",
    "jinja",
}

HELPFUL_REWRITE_CUES = {
    "the answer is",
    "solution:",
    "therefore the answer",
    "here is the explanation",
    "step-by-step",
    "to solve this",
    "we need to",
}

IMAGE_METADATA_CUES = {
    "image shows",
    "there is a",
    "appears to be",
    "looks like",
    "photo of",
    "screenshot of",
}

MAX_OUTPUT_WORDS_WITHOUT_GOLD = 2500
MIN_OUTPUT_CHARS_DEFAULT = 3

CHAR_SIMILARITY_BLOCK_THRESHOLD = 0.70
CHAR_SIMILARITY_REVIEW_THRESHOLD = 0.84

WORD_RECALL_BLOCK_THRESHOLD = 0.65
WORD_RECALL_REVIEW_THRESHOLD = 0.80

NUMBER_RECALL_BLOCK_THRESHOLD = 0.85
MATH_RECALL_BLOCK_THRESHOLD = 0.75
QUESTION_NUMBER_RECALL_BLOCK_THRESHOLD = 0.90

LAYOUT_RECALL_REVIEW_THRESHOLD = 0.55

COMMON_OCR_CONFUSIONS = str.maketrans({
    "O": "0",
    "o": "0",
    "I": "1",
    "l": "1",
    "|": "1",
    "S": "5",
})

NOISE_LINES = {
    "scan artifact",
    "page footer",
    "downloaded from",
    "printed by",
    "copyright",
    "all rights reserved",
    "watermark",
}

QUESTION_NUMBER_PATTERNS = [
    r"\bQ\.?\s*(\d{1,3})\b",
    r"\bQuestion\s+(\d{1,3})\b",
    r"^\s*(\d{1,3})[.)]\s+",
]

OPTION_MARKER_PATTERN = r"\(\s*[A-Da-d]\s*\)|^[A-Da-d][.)]\s+"

MATH_SYMBOL_PATTERN = r"[=+\-×*/^²³√∑∫πΩμρΔθλαβγ≤≥≈≠∞]|\\frac|\\sqrt|[A-Za-z]\s*=\s*[^.;,\n]+"

UNIT_PATTERN = r"\b\d+(?:\.\d+)?\s*(?:V|A|Ω|m/s|mol|cm|mm|m|kg|g|J|N|pm|eV|K|T|Hz|s|sec|marks?)\b"


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


def _norm_ocr(text: Any) -> str:
    raw = "" if text is None else str(text)
    raw = raw.replace("−", "-").replace("–", "-").replace("—", "-")
    raw = raw.replace("×", "x").replace("·", ".")
    raw = raw.replace("⁻", "-").replace("²", "2").replace("³", "3")
    raw = re.sub(r"\s+", " ", raw.strip().lower())
    return raw


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9ΩμρΔθ°/+=∩∪^²³().-]+", _norm_ocr(text))


def _content_tokens(text: str) -> set[str]:
    stop = {
        "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with",
        "is", "are", "was", "were", "be", "been", "being", "this", "that",
        "it", "as", "by", "from", "image", "page", "text", "question",
    }
    return {t for t in _tokens(text) if len(t) > 1 and t not in stop}


def _contains_any(text: str, needles) -> bool:
    t = _norm(text)
    return any(_norm(n) in t for n in needles)


def _get_extracted_text(out: Optional[dict]) -> Optional[str]:
    if not isinstance(out, dict):
        return None
    value = out.get("extracted_text")
    return value if isinstance(value, str) and value.strip() else None


def _get_gold_text(ref: Optional[dict]) -> str:
    if not isinstance(ref, dict):
        return ""
    value = ref.get("extracted_text")
    return value if isinstance(value, str) else ""


def _char_similarity(pred: str, gold: str) -> float:
    a = _norm_ocr(pred)
    b = _norm_ocr(gold)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def _word_recall(pred: str, gold: str) -> float:
    pred_tokens = _content_tokens(pred)
    gold_tokens = _content_tokens(gold)
    if not gold_tokens:
        return 1.0 if not pred_tokens else 0.0
    return len(pred_tokens & gold_tokens) / len(gold_tokens)


def _number_like(text: str) -> list[str]:
    values = []
    for m in re.findall(r"[-+]?\d+(?:\.\d+)?(?:\s*[×x]\s*10\^?[-+]?\d+)?\s*(?:[A-Za-zΩμ°/%²³^-]+)?", text or ""):
        cleaned = re.sub(r"\s+", "", m.strip().translate(COMMON_OCR_CONFUSIONS)).lower()
        if cleaned:
            values.append(cleaned)
    return values


def _recall_list(pred_items: list[str], gold_items: list[str]) -> float:
    if not gold_items:
        return 1.0
    pred_set = set(pred_items)
    hits = 0
    for item in set(gold_items):
        if item in pred_set:
            hits += 1
        else:
            # Loose partial match for OCR spacing/unit differences.
            if any(item in p or p in item for p in pred_set if len(item) >= 2 and len(p) >= 2):
                hits += 1
    return hits / len(set(gold_items))


def _math_items(text: str) -> list[str]:
    found = []
    for pattern in [MATH_SYMBOL_PATTERN, UNIT_PATTERN]:
        for m in re.findall(pattern, text or "", flags=re.IGNORECASE | re.MULTILINE):
            if isinstance(m, tuple):
                m = " ".join(x for x in m if x)
            cleaned = _norm_ocr(m)
            if cleaned and len(cleaned) <= 80:
                found.append(cleaned)
    return found


def _question_numbers(text: str) -> list[str]:
    nums = []
    for pattern in QUESTION_NUMBER_PATTERNS:
        for m in re.finditer(pattern, text or "", flags=re.IGNORECASE | re.MULTILINE):
            nums.append(str(int(m.group(1))))
    # Preserve order/dedupe.
    out = []
    seen = set()
    for n in nums:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def _option_markers(text: str) -> list[str]:
    markers = []
    for m in re.finditer(OPTION_MARKER_PATTERN, text or "", flags=re.IGNORECASE | re.MULTILINE):
        markers.append(_norm_ocr(m.group(0)))
    return markers


def _layout_cues(text: str) -> set[str]:
    cues = set()
    if re.search(r"^\s*section\s+[a-zivx]+", text or "", flags=re.IGNORECASE | re.MULTILINE):
        cues.add("section_header")
    if re.search(r"^\s*(?:[-*]|\d+[.)])\s+", text or "", flags=re.MULTILINE):
        cues.add("list_items")
    if _question_numbers(text):
        cues.add("question_numbers")
    if len(_option_markers(text)) >= 2:
        cues.add("mcq_options")
    if _contains_any(text, {"assertion", "reason"}):
        cues.add("assertion_reason")
    if _contains_any(text, {"or", "\nOR\n"}):
        cues.add("or_branch")
    if re.search(r"\|.+\|", text or "") or re.search(r"\btable\b", text or "", flags=re.IGNORECASE):
        cues.add("table")
    if re.search(r"\bfigure\b|\bdiagram\b|\bgraph\b", text or "", flags=re.IGNORECASE):
        cues.add("figure_ref")
    return cues


def _layout_recall(pred: str, gold: str) -> float:
    gold_cues = _layout_cues(gold)
    if not gold_cues:
        return 1.0
    pred_cues = _layout_cues(pred)
    return len(pred_cues & gold_cues) / len(gold_cues)


def _has_source_input(inputs: dict) -> bool:
    if any(k in inputs and inputs.get(k) not in (None, "") for k in ACCEPTED_IMAGE_INPUT_KEYS):
        return True
    if "pdf_source" in inputs and "page_number" in inputs:
        return True
    return False


def _binary_size_hint(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, bytes):
        return len(value)
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return 0
        # Approximate base64 payload if it looks like base64.
        if len(raw) > 64 and re.fullmatch(r"[A-Za-z0-9+/=\s]+", raw[:200]):
            try:
                return len(base64.b64decode(raw, validate=False))
            except Exception:
                return len(raw)
        return len(raw)
    return 1


def _source_payload_size(inputs: dict) -> int:
    total = 0
    for key in ACCEPTED_IMAGE_INPUT_KEYS:
        total += _binary_size_hint(inputs.get(key))
    return total


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
    Defensive parser for raw OCR agent responses.
    Accepts:
      - {"extracted_text": "..."}
      - raw plain text
    """
    if not isinstance(raw_text, str):
        return {}

    parsed = _json_from_text(raw_text)
    if isinstance(parsed, dict) and isinstance(parsed.get("extracted_text"), str):
        return {"extracted_text": parsed["extracted_text"]}

    return {"extracted_text": raw_text.strip()}


# ---------------------------------------------------------------------------
# Evaluator 1: schema_validity
# ---------------------------------------------------------------------------

def schema_validity(run, example) -> dict:
    inputs = _safe_get_inputs(example)
    if not _has_source_input(inputs):
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": "missing OCR source input; expected image bytes/data/url/render OR pdf_source+page_number",
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

    text = _get_extracted_text(out)
    if text is None:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": "extracted_text must be a non-empty string",
        }

    if text.strip().startswith("{") or text.strip().startswith("["):
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": "extracted_text should be plain text, not JSON",
        }

    if "```" in text:
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": "extracted_text must not be wrapped in code fences",
        }

    if _contains_any(text, BANNED_PATTERNS):
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": "extracted_text contains banned/internal/refusal phrase",
        }

    if _word_count(text) > MAX_OUTPUT_WORDS_WITHOUT_GOLD and not _get_gold_text(_safe_get_reference(example)):
        return {
            "key": "schema_validity",
            "score": 0.5,
            "comment": f"extracted_text unusually long without gold: {_word_count(text)} words",
        }

    return {"key": "schema_validity", "score": 1.0, "comment": "schema valid"}


# ---------------------------------------------------------------------------
# Evaluator 2: text_similarity
# ---------------------------------------------------------------------------

def text_similarity(run, example) -> dict:
    pred = _get_extracted_text(_safe_get_outputs(run))
    gold = _get_gold_text(_safe_get_reference(example))

    if pred is None:
        return {
            "key": "text_similarity",
            "score": 0.0,
            "comment": "extracted_text missing/malformed",
            "hard_rule_violated": False,
        }

    if not gold:
        # No gold: cannot measure true OCR accuracy; fall back to non-empty.
        if len(pred.strip()) < MIN_OUTPUT_CHARS_DEFAULT:
            return {
                "key": "text_similarity",
                "score": 0.0,
                "comment": "no gold supplied and extracted_text is too short",
                "hard_rule_violated": True,
            }
        return {
            "key": "text_similarity",
            "score": 1.0,
            "comment": "no gold supplied; skipped reference similarity",
            "hard_rule_violated": False,
        }

    char_sim = _char_similarity(pred, gold)
    word_rec = _word_recall(pred, gold)

    if char_sim < CHAR_SIMILARITY_BLOCK_THRESHOLD or word_rec < WORD_RECALL_BLOCK_THRESHOLD:
        return {
            "key": "text_similarity",
            "score": 0.0,
            "comment": f"low OCR similarity: char={char_sim:.3f}, word_recall={word_rec:.3f}",
            "hard_rule_violated": True,
            "char_similarity": round(char_sim, 3),
            "word_recall": round(word_rec, 3),
        }

    if char_sim < CHAR_SIMILARITY_REVIEW_THRESHOLD or word_rec < WORD_RECALL_REVIEW_THRESHOLD:
        return {
            "key": "text_similarity",
            "score": 0.5,
            "comment": f"partial OCR similarity: char={char_sim:.3f}, word_recall={word_rec:.3f}",
            "hard_rule_violated": False,
            "char_similarity": round(char_sim, 3),
            "word_recall": round(word_rec, 3),
        }

    return {
        "key": "text_similarity",
        "score": 1.0,
        "comment": f"OCR similarity passed: char={char_sim:.3f}, word_recall={word_rec:.3f}",
        "hard_rule_violated": False,
        "char_similarity": round(char_sim, 3),
        "word_recall": round(word_rec, 3),
    }


# ---------------------------------------------------------------------------
# Evaluator 3: numbers_math_retention
# ---------------------------------------------------------------------------

def numbers_math_retention(run, example) -> dict:
    pred = _get_extracted_text(_safe_get_outputs(run))
    gold = _get_gold_text(_safe_get_reference(example))

    if pred is None:
        return {
            "key": "numbers_math_retention",
            "score": 0.0,
            "comment": "extracted_text missing/malformed",
            "hard_rule_violated": False,
        }

    if not gold:
        return {
            "key": "numbers_math_retention",
            "score": 1.0,
            "comment": "no gold supplied; skipped numeric/math retention",
            "hard_rule_violated": False,
        }

    pred_nums = _number_like(pred)
    gold_nums = _number_like(gold)
    num_recall = _recall_list(pred_nums, gold_nums)

    pred_math = _math_items(pred)
    gold_math = _math_items(gold)
    math_recall = _recall_list(pred_math, gold_math)

    issues = []
    hard = False

    if gold_nums and num_recall < NUMBER_RECALL_BLOCK_THRESHOLD:
        issues.append(f"number_recall_low={num_recall:.3f}")
        hard = True

    if gold_math and math_recall < MATH_RECALL_BLOCK_THRESHOLD:
        issues.append(f"math_symbol_formula_recall_low={math_recall:.3f}")
        hard = True

    if hard:
        return {
            "key": "numbers_math_retention",
            "score": 0.0,
            "comment": "; ".join(issues),
            "hard_rule_violated": True,
            "number_recall": round(num_recall, 3),
            "math_recall": round(math_recall, 3),
        }

    if issues:
        return {
            "key": "numbers_math_retention",
            "score": 0.5,
            "comment": "; ".join(issues),
            "hard_rule_violated": False,
            "number_recall": round(num_recall, 3),
            "math_recall": round(math_recall, 3),
        }

    return {
        "key": "numbers_math_retention",
        "score": 1.0,
        "comment": f"numbers/math retained: number={num_recall:.3f}, math={math_recall:.3f}",
        "hard_rule_violated": False,
        "number_recall": round(num_recall, 3),
        "math_recall": round(math_recall, 3),
    }


# ---------------------------------------------------------------------------
# Evaluator 4: question_layout_retention
# ---------------------------------------------------------------------------

def question_layout_retention(run, example) -> dict:
    pred = _get_extracted_text(_safe_get_outputs(run))
    gold = _get_gold_text(_safe_get_reference(example))

    if pred is None:
        return {
            "key": "question_layout_retention",
            "score": 0.0,
            "comment": "extracted_text missing/malformed",
            "hard_rule_violated": False,
        }

    if not gold:
        return {
            "key": "question_layout_retention",
            "score": 1.0,
            "comment": "no gold supplied; skipped layout retention",
            "hard_rule_violated": False,
        }

    pred_qnums = _question_numbers(pred)
    gold_qnums = _question_numbers(gold)
    qnum_recall = _recall_list(pred_qnums, gold_qnums)

    pred_options = _option_markers(pred)
    gold_options = _option_markers(gold)
    option_recall = _recall_list(pred_options, gold_options)

    layout_rec = _layout_recall(pred, gold)

    issues = []
    hard = False

    if gold_qnums and qnum_recall < QUESTION_NUMBER_RECALL_BLOCK_THRESHOLD:
        issues.append(f"question_number_recall_low={qnum_recall:.3f}")
        hard = True

    if gold_options and option_recall < 0.75:
        issues.append(f"mcq_option_marker_recall_low={option_recall:.3f}")
        hard = True

    if layout_rec < LAYOUT_RECALL_REVIEW_THRESHOLD:
        issues.append(f"layout_cue_recall_low={layout_rec:.3f}")

    if hard:
        return {
            "key": "question_layout_retention",
            "score": 0.0,
            "comment": "; ".join(issues),
            "hard_rule_violated": True,
            "question_number_recall": round(qnum_recall, 3),
            "option_recall": round(option_recall, 3),
            "layout_recall": round(layout_rec, 3),
        }

    if issues:
        return {
            "key": "question_layout_retention",
            "score": 0.5,
            "comment": "; ".join(issues),
            "hard_rule_violated": False,
            "question_number_recall": round(qnum_recall, 3),
            "option_recall": round(option_recall, 3),
            "layout_recall": round(layout_rec, 3),
        }

    return {
        "key": "question_layout_retention",
        "score": 1.0,
        "comment": f"question/layout retained: qnums={qnum_recall:.3f}, options={option_recall:.3f}, layout={layout_rec:.3f}",
        "hard_rule_violated": False,
        "question_number_recall": round(qnum_recall, 3),
        "option_recall": round(option_recall, 3),
        "layout_recall": round(layout_rec, 3),
    }


# ---------------------------------------------------------------------------
# Evaluator 5: no_helpful_rewrite_or_hallucination
# ---------------------------------------------------------------------------

def no_helpful_rewrite_or_hallucination(run, example) -> dict:
    pred = _get_extracted_text(_safe_get_outputs(run))
    gold = _get_gold_text(_safe_get_reference(example))

    if pred is None:
        return {
            "key": "no_helpful_rewrite_or_hallucination",
            "score": 0.0,
            "comment": "extracted_text missing/malformed",
            "hard_rule_violated": False,
        }

    issues = []
    hard = False

    if _contains_any(pred, HELPFUL_REWRITE_CUES):
        # OCR should transcribe, not solve. Only allow if gold also contains it.
        if not gold or not _contains_any(gold, HELPFUL_REWRITE_CUES):
            issues.append("OCR appears to add solution/explanation wording")
            hard = True

    if _contains_any(pred, IMAGE_METADATA_CUES):
        if not gold or not _contains_any(gold, IMAGE_METADATA_CUES):
            issues.append("OCR describes the image instead of transcribing text")
            hard = True

    if _contains_any(pred, NOISE_LINES):
        # If noise exists in gold, OCR may faithfully capture it, but downstream
        # pipeline usually benefits from retaining document text. Mark review only.
        if gold and _contains_any(gold, NOISE_LINES):
            issues.append("OCR includes source footer/noise text from image")
        else:
            issues.append("OCR introduced footer/noise text")
            hard = True

    if gold:
        pred_terms = _content_tokens(pred)
        gold_terms = _content_tokens(gold)
        extra_terms = pred_terms - gold_terms
        # Be conservative: short extra terms can be OCR confusion, not hallucination.
        suspicious = [t for t in extra_terms if len(t) >= 7 and not any(_char_similarity(t, g) > 0.70 for g in gold_terms)]
        if len(suspicious) >= 12:
            issues.append(f"many_suspicious_extra_terms:{suspicious[:8]}")
            hard = True
        elif len(suspicious) >= 5:
            issues.append(f"possible_extra_terms:{suspicious[:8]}")

    if hard:
        return {
            "key": "no_helpful_rewrite_or_hallucination",
            "score": 0.0,
            "comment": "; ".join(issues[:10]),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "no_helpful_rewrite_or_hallucination",
            "score": 0.5,
            "comment": "; ".join(issues[:10]),
            "hard_rule_violated": False,
        }

    return {
        "key": "no_helpful_rewrite_or_hallucination",
        "score": 1.0,
        "comment": "no solve/explanation/image-description hallucination detected",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 6: scan_bypass_and_empty_behavior
# ---------------------------------------------------------------------------

def scan_bypass_and_empty_behavior(run, example) -> dict:
    pred = _get_extracted_text(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)
    gold = _get_gold_text(_safe_get_reference(example))
    variation = _safe_get_variation(example)

    if pred is None:
        return {
            "key": "scan_bypass_and_empty_behavior",
            "score": 0.0,
            "comment": "extracted_text missing/malformed",
        }

    issues = []

    source_type = _norm(inputs.get("source_type", "")) or _norm(variation)
    payload_size = _source_payload_size(inputs)

    # Native text PDFs should bypass this agent; if evaluated anyway, flag as review
    # rather than block because datasets may include synthetic text proxies.
    if "native_text_pdf" in source_type or "native-text" in source_type:
        issues.append("Agent 32 should normally be bypassed for native text PDFs")

    # Blank/low-text gold should produce conservative short output.
    if gold and _word_count(gold) <= 2:
        if _word_count(pred) > 15:
            issues.append("blank_or_nearly_blank_gold_but_predicted_long_text")
            return {"key": "scan_bypass_and_empty_behavior", "score": 0.0, "comment": "; ".join(issues)}
        return {"key": "scan_bypass_and_empty_behavior", "score": 1.0, "comment": "blank/low-text behavior passed"}

    if payload_size == 0 and not ("pdf_source" in inputs and "page_number" in inputs):
        issues.append("no source payload size available")

    if _word_count(pred) < 2 and gold and _word_count(gold) >= 5:
        issues.append("non-empty gold but OCR output nearly empty")
        return {"key": "scan_bypass_and_empty_behavior", "score": 0.0, "comment": "; ".join(issues)}

    if issues:
        return {"key": "scan_bypass_and_empty_behavior", "score": 0.5, "comment": "; ".join(issues)}

    return {"key": "scan_bypass_and_empty_behavior", "score": 1.0, "comment": "bypass/empty-source behavior acceptable"}


# ---------------------------------------------------------------------------
# Summary evaluator
# ---------------------------------------------------------------------------

def image_ocr_severity_summary(runs: list, examples: list) -> dict:
    """
    BLOCK:
    - malformed output / wrong key
    - missing source input
    - low reference similarity
    - poor number/math/question-number retention
    - OCR solves/explains/describes image instead of transcribing
    - non-empty gold but empty output

    REVIEW:
    - partial similarity
    - weak layout cue retention
    - footer noise copied through
    - native text PDF should have bypassed OCR
    """
    if len(runs) != len(examples):
        return {
            "key": "image_ocr_severity_summary",
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

        sim = text_similarity(run, example)
        math = numbers_math_retention(run, example)
        layout = question_layout_retention(run, example)
        no_rewrite = no_helpful_rewrite_or_hallucination(run, example)
        empty = scan_bypass_and_empty_behavior(run, example)

        for result in (sim, math, layout, no_rewrite):
            if result.get("hard_rule_violated"):
                tier_0.append({"example_id": getattr(example, "id", None), "reason": f"{result['key']} hard failure: {result['comment']}"})

        if empty["score"] == 0.0:
            tier_0.append({"example_id": getattr(example, "id", None), "reason": f"scan_bypass_and_empty_behavior failed: {empty['comment']}"})

        tier_1_applicable += 6
        for result in (schema, sim, math, layout, no_rewrite, empty):
            if result["score"] < 1.0:
                tier_1 += 1

        if (
            schema["score"] == 1.0
            and sim["score"] == 1.0
            and math["score"] == 1.0
            and layout["score"] == 1.0
            and no_rewrite["score"] == 1.0
            and empty["score"] == 1.0
        ):
            variation_passes[variation] = variation_passes.get(variation, 0) + 1

    tier_1_rate = tier_1 / tier_1_applicable if tier_1_applicable else 0.0
    per_variation = {v: round(variation_passes.get(v, 0) / total, 3) for v, total in variation_totals.items()}

    recommendation = "BLOCK" if tier_0 else ("REVIEW" if tier_1_rate > 0.18 else "OK")

    return {
        "key": "image_ocr_severity_summary",
        "score": 0.0 if tier_0 else round(1.0 - tier_1_rate, 3),
        "comment": (
            f"ship_recommendation={recommendation} | "
            f"tier_0_blocking_count={len(tier_0)} | "
            f"tier_1_review_rate={tier_1_rate:.3f} | "
            f"evaluator_type=code_first_tier2_reference_metrics"
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
    text_similarity,
    numbers_math_retention,
    question_layout_retention,
    no_helpful_rewrite_or_hallucination,
    scan_bypass_and_empty_behavior,
]

SUMMARY_EVALUATORS = [image_ocr_severity_summary]
