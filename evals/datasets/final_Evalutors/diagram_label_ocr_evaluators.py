"""
diagram_label_ocr_evaluators.py

LangSmith custom evaluators for Agent 33: Diagram Label OCR.

Agent role:
- Extracts text labels, symbols, numbers, axis labels, point labels, charge signs,
  component labels, graph labels, and figure annotations from embedded diagrams.
- It is diagram/figure-crop OCR, not full-page transcription.
- The output provides diagram label hints for source upload / problem parsing,
  especially when a question stem refers to "shown in the figure".

Production dependencies:
- Inputs may include:
    figure_crop / image_crop / image_bytes / image_data / image_base64 /
    image_url / embedded_image / pdf_figure_crop
  Optional context:
    page_text / surrounding_text / question_text / figure_caption /
    source_type / expected_language
- Output:
    labels_text: str

Dependency note:
- Agent 33 is parallel to Agent 32, not dependent on it.
- Agent 32 handles full page OCR; Agent 33 handles embedded figures only.
- Agent 25 may consume Agent 33 label hints along with document_text.
- Agent 33 is bypassed on text-only pages with no embedded figures.

Evaluator design:
- Code-first, not hybrid.
- Criticality: Tier 2. It is upstream for diagram-aware RAG/problem extraction,
  but OCR transcription is better evaluated with direct reference metrics than
  with an LLM judge.
- Main risks are deterministic:
  malformed output, full-page transcription instead of figure labels, missing
  diagram labels/symbols/numbers, losing +/- signs or coordinates, inventing
  labels, solving/explaining instead of transcribing, or running on text-only pages.
- No required LLM judge.

LangSmith usage:
    from diagram_label_ocr_evaluators import PER_EXAMPLE_EVALUATORS, SUMMARY_EVALUATORS

    client.evaluate(
        target_fn,
        data="nbm-prompt-diagram_label_ocr",
        evaluators=PER_EXAMPLE_EVALUATORS,
        summary_evaluators=SUMMARY_EVALUATORS,
    )

Recommended gold/reference output:
    {"labels_text": "..."}
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

REQUIRED_OUTPUT_KEYS = {"labels_text"}

ACCEPTED_FIGURE_INPUT_KEYS = {
    "figure_crop",
    "image_crop",
    "image_bytes",
    "image_data",
    "image_base64",
    "image_url",
    "embedded_image",
    "pdf_figure_crop",
    "crop_bytes",
    "crop_base64",
}

OPTIONAL_CONTEXT_KEYS = {
    "page_text",
    "surrounding_text",
    "question_text",
    "figure_caption",
    "source_type",
    "expected_language",
    "page_number",
    "bbox",
}

MIN_LABELS_CHARS_DEFAULT = 1
MAX_LABELS_WORDS_DEFAULT = 220
MAX_LABELS_TO_CONTEXT_RATIO = 0.70

CHAR_SIMILARITY_BLOCK_THRESHOLD = 0.60
CHAR_SIMILARITY_REVIEW_THRESHOLD = 0.76

TOKEN_RECALL_BLOCK_THRESHOLD = 0.65
TOKEN_RECALL_REVIEW_THRESHOLD = 0.80

NUMBER_RECALL_BLOCK_THRESHOLD = 0.85
SYMBOL_RECALL_BLOCK_THRESHOLD = 0.80
POINT_LABEL_RECALL_BLOCK_THRESHOLD = 0.85

BANNED_PATTERNS = {
    "as an ai language model",
    "i cannot access",
    "i don't have access",
    "unable to read the image",
    "sorry",
    "placeholder",
    "todo",
    "lorem ipsum",
    "labels_text",
    "valid json",
    "system prompt",
    ".j2",
    "jinja",
}

SOLVING_OR_EXPLANATION_CUES = {
    "the answer is",
    "therefore",
    "hence",
    "solution:",
    "to solve",
    "we need to",
    "using the formula",
    "step-by-step",
    "correct option",
    "option a",
    "option b",
    "option c",
    "option d",
}

FULL_PAGE_OR_STEM_CUES = {
    "find the",
    "calculate the",
    "which of the following",
    "answer the following",
    "question",
    "marks",
    "case study",
    "read the passage",
    "assertion",
    "reason",
}

SAFE_DIAGRAM_DESCRIPTION_CUES = {
    "left",
    "right",
    "top",
    "bottom",
    "axis",
    "axes",
    "line",
    "curve",
    "point",
    "arrow",
    "label",
    "figure",
    "graph",
}

TEXT_ONLY_BYPASS_CUES = {
    "text_only",
    "text-only",
    "native_text_pdf",
    "no_diagram",
    "no_figure",
    "plain_text",
}

COMMON_OCR_CONFUSIONS = str.maketrans({
    "O": "0",
    "o": "0",
    "I": "1",
    "l": "1",
    "|": "1",
    "S": "5",
})

GENERIC_WORDS = {
    "the", "and", "with", "from", "this", "that", "diagram", "figure",
    "image", "label", "labels", "text", "shows", "shown", "contains",
    "has", "left", "right", "top", "bottom", "point", "line", "arrow",
    "axis", "axes", "graph", "curve", "crop", "page",
}

MATH_SYMBOL_PATTERN = r"[=+\-±×*/^²³√∑∫πΩμρΔθλαβγ≤≥≈≠∞]|\\frac|\\sqrt|[A-Za-z]\s*=\s*[^.;,\n]+"
UNIT_PATTERN = r"\b\d+(?:\.\d+)?\s*(?:V|A|Ω|m/s|mol|cm|mm|m|kg|g|J|N|pm|eV|K|T|Hz|s|sec|°|µC|μC|C|M|atm|L)\b"
COORDINATE_PATTERN = r"\(\s*[-+]?\d+(?:\.\d+)?\s*,\s*[-+]?\d+(?:\.\d+)?\s*\)"
POINT_LABEL_PATTERN = r"\b[A-Z][A-Z0-9']?\b"
SUBSCRIPT_LABEL_PATTERN = r"\b[A-Za-z]+[_]?[0-9]+\b|[A-Za-z]_[0-9]+"
CHARGE_SIGN_PATTERN = r"[+-]\s*\d+(?:\.\d+)?\s*(?:µC|μC|C|e)?|[+-]\s*(?:q|Q|e)\b|\bpositive\b|\bnegative\b"
AXIS_LABEL_PATTERN = r"\b[xXyY][- ]?axis\b|\baxis\b|\btime\b|\bvoltage\b|\bcurrent\b|\btemperature\b|\bpressure\b|\bvolume\b"


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
    raw = raw.replace("µ", "μ")
    raw = re.sub(r"\s+", " ", raw.strip().lower())
    return raw


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def _line_count(text: str) -> int:
    return len([line for line in str(text or "").splitlines() if line.strip()])


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9ΩμρΔθ°/+=∩∪^²³().,'-]+", _norm_ocr(text))


def _content_tokens(text: str) -> set[str]:
    stop = {
        "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with",
        "is", "are", "was", "were", "be", "been", "being", "this", "that",
        "it", "as", "by", "from", "diagram", "figure", "image", "label",
        "labels", "shown", "shows",
    }
    return {t for t in _tokens(text) if len(t) > 1 and t not in stop}


def _contains_any(text: str, needles) -> bool:
    t = _norm(text)
    return any(_norm(n) in t for n in needles)


def _get_labels_text(out: Optional[dict]) -> Optional[str]:
    if not isinstance(out, dict):
        return None
    value = out.get("labels_text")
    return value if isinstance(value, str) and value.strip() else None


def _get_gold_labels(ref: Optional[dict]) -> str:
    if not isinstance(ref, dict):
        return ""
    value = ref.get("labels_text")
    return value if isinstance(value, str) else ""


def _char_similarity(pred: str, gold: str) -> float:
    a = _norm_ocr(pred)
    b = _norm_ocr(gold)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def _token_recall(pred: str, gold: str) -> float:
    pred_tokens = _content_tokens(pred)
    gold_tokens = _content_tokens(gold)
    if not gold_tokens:
        return 1.0 if not pred_tokens else 0.0
    return len(pred_tokens & gold_tokens) / len(gold_tokens)


def _recall_list(pred_items: list[str], gold_items: list[str]) -> float:
    if not gold_items:
        return 1.0
    pred_set = set(pred_items)
    hits = 0
    for item in set(gold_items):
        if item in pred_set:
            hits += 1
        else:
            if any(item in p or p in item or _char_similarity(item, p) > 0.78 for p in pred_set if len(item) >= 1 and len(p) >= 1):
                hits += 1
    return hits / len(set(gold_items))


def _number_like(text: str) -> list[str]:
    values = []
    for m in re.findall(r"[-+]?\d+(?:\.\d+)?(?:\s*[×x]\s*10\^?[-+]?\d+)?\s*(?:[A-Za-zΩμ°/%²³^-]+)?", text or ""):
        cleaned = re.sub(r"\s+", "", m.strip().translate(COMMON_OCR_CONFUSIONS)).lower().replace("µ", "μ")
        if cleaned:
            values.append(cleaned)
    values.extend([_norm_ocr(c) for c in re.findall(COORDINATE_PATTERN, text or "")])
    return values


def _math_symbols(text: str) -> list[str]:
    found = []
    for pattern in [MATH_SYMBOL_PATTERN, UNIT_PATTERN, CHARGE_SIGN_PATTERN, SUBSCRIPT_LABEL_PATTERN]:
        for m in re.findall(pattern, text or "", flags=re.IGNORECASE | re.MULTILINE):
            if isinstance(m, tuple):
                m = " ".join(x for x in m if x)
            cleaned = _norm_ocr(m)
            if cleaned and len(cleaned) <= 80:
                found.append(cleaned)
    return found


def _point_labels(text: str) -> list[str]:
    labels = []
    for m in re.findall(POINT_LABEL_PATTERN, text or ""):
        # Avoid treating common units/option markers as point labels when alone.
        if m in {"A", "B", "C", "D", "P", "Q", "R", "S", "O", "X", "Y"}:
            labels.append(m.lower())
        elif len(m) <= 2:
            labels.append(m.lower())
    for sub in re.findall(SUBSCRIPT_LABEL_PATTERN, text or ""):
        labels.append(_norm_ocr(sub))
    return labels


def _axis_labels(text: str) -> list[str]:
    found = []
    for m in re.findall(AXIS_LABEL_PATTERN, text or "", flags=re.IGNORECASE):
        found.append(_norm_ocr(m))
    # Also catch "x", "y" near graph/axis words.
    if _contains_any(text, {"axis", "graph", "curve"}):
        for m in re.findall(r"\b[xXyY]\b", text or ""):
            found.append(_norm_ocr(m))
    return found


def _diagram_terms(text: str) -> set[str]:
    terms = set()
    terms.update(_content_tokens(text))
    terms.update(_number_like(text))
    terms.update(_math_symbols(text))
    terms.update(_point_labels(text))
    terms.update(_axis_labels(text))
    return {t for t in terms if t and t not in GENERIC_WORDS}


def _has_source_input(inputs: dict) -> bool:
    return any(k in inputs and inputs.get(k) not in (None, "") for k in ACCEPTED_FIGURE_INPUT_KEYS)


def _binary_size_hint(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, bytes):
        return len(value)
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return 0
        if len(raw) > 64 and re.fullmatch(r"[A-Za-z0-9+/=\s]+", raw[:200]):
            try:
                return len(base64.b64decode(raw, validate=False))
            except Exception:
                return len(raw)
        return len(raw)
    return 1


def _source_payload_size(inputs: dict) -> int:
    return sum(_binary_size_hint(inputs.get(k)) for k in ACCEPTED_FIGURE_INPUT_KEYS)


def _context_text(inputs: dict) -> str:
    return "\n".join(
        str(inputs.get(k, ""))
        for k in ["page_text", "surrounding_text", "question_text", "figure_caption"]
        if str(inputs.get(k, "")).strip()
    )


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
    Defensive parser for raw diagram-label OCR responses.
    Accepts:
      - {"labels_text": "..."}
      - raw plain text
    """
    if not isinstance(raw_text, str):
        return {}

    parsed = _json_from_text(raw_text)
    if isinstance(parsed, dict) and isinstance(parsed.get("labels_text"), str):
        return {"labels_text": parsed["labels_text"]}

    return {"labels_text": raw_text.strip()}


# ---------------------------------------------------------------------------
# Evaluator 1: schema_validity
# ---------------------------------------------------------------------------

def schema_validity(run, example) -> dict:
    inputs = _safe_get_inputs(example)
    variation = _safe_get_variation(example)
    source_type = _norm(inputs.get("source_type", "")) + " " + _norm(variation)

    if not _has_source_input(inputs):
        if _contains_any(source_type, TEXT_ONLY_BYPASS_CUES):
            return {
                "key": "schema_validity",
                "score": 0.5,
                "comment": "text-only/no-figure case should normally bypass Agent 33",
            }
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": "missing figure source input; expected figure_crop/image_crop/embedded image",
        }

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

    text = _get_labels_text(out)
    if text is None:
        return {"key": "schema_validity", "score": 0.0, "comment": "labels_text must be a non-empty string"}

    if text.strip().startswith("{") or text.strip().startswith("["):
        return {"key": "schema_validity", "score": 0.0, "comment": "labels_text should be plain text, not JSON"}

    if "```" in text:
        return {"key": "schema_validity", "score": 0.0, "comment": "labels_text must not be wrapped in code fences"}

    if _contains_any(text, BANNED_PATTERNS):
        return {"key": "schema_validity", "score": 0.0, "comment": "labels_text contains banned/internal/refusal phrase"}

    if len(text.strip()) < MIN_LABELS_CHARS_DEFAULT:
        return {"key": "schema_validity", "score": 0.0, "comment": "labels_text too short"}

    return {"key": "schema_validity", "score": 1.0, "comment": "schema valid"}


# ---------------------------------------------------------------------------
# Evaluator 2: label_similarity
# ---------------------------------------------------------------------------

def label_similarity(run, example) -> dict:
    pred = _get_labels_text(_safe_get_outputs(run))
    gold = _get_gold_labels(_safe_get_reference(example))

    if pred is None:
        return {
            "key": "label_similarity",
            "score": 0.0,
            "comment": "labels_text missing/malformed",
            "hard_rule_violated": False,
        }

    if not gold:
        if len(pred.strip()) < MIN_LABELS_CHARS_DEFAULT:
            return {
                "key": "label_similarity",
                "score": 0.0,
                "comment": "no gold supplied and labels_text is empty/thin",
                "hard_rule_violated": True,
            }
        return {
            "key": "label_similarity",
            "score": 1.0,
            "comment": "no gold supplied; skipped reference similarity",
            "hard_rule_violated": False,
        }

    char_sim = _char_similarity(pred, gold)
    token_rec = _token_recall(pred, gold)

    if char_sim < CHAR_SIMILARITY_BLOCK_THRESHOLD and token_rec < TOKEN_RECALL_BLOCK_THRESHOLD:
        return {
            "key": "label_similarity",
            "score": 0.0,
            "comment": f"low diagram-label similarity: char={char_sim:.3f}, token_recall={token_rec:.3f}",
            "hard_rule_violated": True,
            "char_similarity": round(char_sim, 3),
            "token_recall": round(token_rec, 3),
        }

    if char_sim < CHAR_SIMILARITY_REVIEW_THRESHOLD or token_rec < TOKEN_RECALL_REVIEW_THRESHOLD:
        return {
            "key": "label_similarity",
            "score": 0.5,
            "comment": f"partial diagram-label similarity: char={char_sim:.3f}, token_recall={token_rec:.3f}",
            "hard_rule_violated": False,
            "char_similarity": round(char_sim, 3),
            "token_recall": round(token_rec, 3),
        }

    return {
        "key": "label_similarity",
        "score": 1.0,
        "comment": f"diagram-label similarity passed: char={char_sim:.3f}, token_recall={token_rec:.3f}",
        "hard_rule_violated": False,
        "char_similarity": round(char_sim, 3),
        "token_recall": round(token_rec, 3),
    }


# ---------------------------------------------------------------------------
# Evaluator 3: diagram_symbol_retention
# ---------------------------------------------------------------------------

def diagram_symbol_retention(run, example) -> dict:
    pred = _get_labels_text(_safe_get_outputs(run))
    gold = _get_gold_labels(_safe_get_reference(example))

    if pred is None:
        return {
            "key": "diagram_symbol_retention",
            "score": 0.0,
            "comment": "labels_text missing/malformed",
            "hard_rule_violated": False,
        }

    if not gold:
        return {
            "key": "diagram_symbol_retention",
            "score": 1.0,
            "comment": "no gold supplied; skipped symbol retention",
            "hard_rule_violated": False,
        }

    pred_nums = _number_like(pred)
    gold_nums = _number_like(gold)
    number_recall = _recall_list(pred_nums, gold_nums)

    pred_symbols = _math_symbols(pred)
    gold_symbols = _math_symbols(gold)
    symbol_recall = _recall_list(pred_symbols, gold_symbols)

    pred_points = _point_labels(pred)
    gold_points = _point_labels(gold)
    point_recall = _recall_list(pred_points, gold_points)

    pred_axes = _axis_labels(pred)
    gold_axes = _axis_labels(gold)
    axis_recall = _recall_list(pred_axes, gold_axes)

    issues = []
    hard = False

    if gold_nums and number_recall < NUMBER_RECALL_BLOCK_THRESHOLD:
        issues.append(f"number_or_unit_recall_low={number_recall:.3f}")
        hard = True

    if gold_symbols and symbol_recall < SYMBOL_RECALL_BLOCK_THRESHOLD:
        issues.append(f"symbol_formula_charge_recall_low={symbol_recall:.3f}")
        hard = True

    if gold_points and point_recall < POINT_LABEL_RECALL_BLOCK_THRESHOLD:
        issues.append(f"point_label_recall_low={point_recall:.3f}")
        hard = True

    if gold_axes and axis_recall < 0.75:
        issues.append(f"axis_label_recall_low={axis_recall:.3f}")
        hard = True

    if hard:
        return {
            "key": "diagram_symbol_retention",
            "score": 0.0,
            "comment": "; ".join(issues),
            "hard_rule_violated": True,
            "number_recall": round(number_recall, 3),
            "symbol_recall": round(symbol_recall, 3),
            "point_label_recall": round(point_recall, 3),
            "axis_recall": round(axis_recall, 3),
        }

    if issues:
        return {
            "key": "diagram_symbol_retention",
            "score": 0.5,
            "comment": "; ".join(issues),
            "hard_rule_violated": False,
            "number_recall": round(number_recall, 3),
            "symbol_recall": round(symbol_recall, 3),
            "point_label_recall": round(point_recall, 3),
            "axis_recall": round(axis_recall, 3),
        }

    return {
        "key": "diagram_symbol_retention",
        "score": 1.0,
        "comment": (
            f"diagram labels retained: numbers={number_recall:.3f}, symbols={symbol_recall:.3f}, "
            f"points={point_recall:.3f}, axes={axis_recall:.3f}"
        ),
        "hard_rule_violated": False,
        "number_recall": round(number_recall, 3),
        "symbol_recall": round(symbol_recall, 3),
        "point_label_recall": round(point_recall, 3),
        "axis_recall": round(axis_recall, 3),
    }


# ---------------------------------------------------------------------------
# Evaluator 4: figure_only_scope
# ---------------------------------------------------------------------------

def figure_only_scope(run, example) -> dict:
    pred = _get_labels_text(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)
    gold = _get_gold_labels(_safe_get_reference(example))

    if pred is None:
        return {
            "key": "figure_only_scope",
            "score": 0.0,
            "comment": "labels_text missing/malformed",
            "hard_rule_violated": False,
        }

    context = _context_text(inputs)
    wc = _word_count(pred)
    issues = []
    hard = False

    if wc > MAX_LABELS_WORDS_DEFAULT:
        issues.append(f"labels_text_too_long_for_figure_labels:{wc}_words")
        hard = True

    if context and _word_count(context) >= 30:
        ratio = wc / max(1, _word_count(context))
        # If predicted labels are too close to context length, likely copied page/stem.
        if ratio > MAX_LABELS_TO_CONTEXT_RATIO and wc > 60:
            issues.append(f"labels_text_may_copy_page_or_question_context:ratio={ratio:.2f}")
            hard = True

    if _contains_any(pred, FULL_PAGE_OR_STEM_CUES):
        # Allow if gold labels themselves include a word like "Question" in a figure, but rare.
        if not gold or not _contains_any(gold, FULL_PAGE_OR_STEM_CUES):
            issues.append("labels_text includes full-page/question-stem cues")
            hard = True

    # A figure label extraction may include positional hints, but should not become a paragraph.
    if _line_count(pred) > 25:
        issues.append(f"too_many_lines_for_embedded_figure_labels:{_line_count(pred)}")
        hard = True

    if hard:
        return {
            "key": "figure_only_scope",
            "score": 0.0,
            "comment": "; ".join(issues),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "figure_only_scope",
            "score": 0.5,
            "comment": "; ".join(issues),
            "hard_rule_violated": False,
        }

    return {
        "key": "figure_only_scope",
        "score": 1.0,
        "comment": "labels_text remains scoped to embedded figure labels",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 5: no_solving_or_hallucinated_labels
# ---------------------------------------------------------------------------

def no_solving_or_hallucinated_labels(run, example) -> dict:
    pred = _get_labels_text(_safe_get_outputs(run))
    gold = _get_gold_labels(_safe_get_reference(example))
    inputs = _safe_get_inputs(example)

    if pred is None:
        return {
            "key": "no_solving_or_hallucinated_labels",
            "score": 0.0,
            "comment": "labels_text missing/malformed",
            "hard_rule_violated": False,
        }

    issues = []
    hard = False

    if _contains_any(pred, SOLVING_OR_EXPLANATION_CUES):
        if not gold or not _contains_any(gold, SOLVING_OR_EXPLANATION_CUES):
            issues.append("diagram OCR appears to solve/explain instead of extracting labels")
            hard = True

    allowed = "\n".join([gold, _context_text(inputs)])
    if gold:
        pred_terms = _diagram_terms(pred)
        gold_terms = _diagram_terms(gold)
        extra_terms = pred_terms - gold_terms

        suspicious = [
            t for t in extra_terms
            if len(t) >= 3
            and t not in GENERIC_WORDS
            and not any(_char_similarity(t, g) > 0.75 for g in gold_terms)
        ]

        # Diagram labels are short, so hallucinated extras matter quickly.
        if len(suspicious) >= 8:
            issues.append(f"many_suspicious_extra_label_terms:{suspicious[:8]}")
            hard = True
        elif len(suspicious) >= 4:
            issues.append(f"possible_extra_label_terms:{suspicious[:6]}")

    elif allowed.strip():
        # Without gold, ensure labels can be traced to nearby context if context provides labels.
        context_terms = _diagram_terms(allowed)
        pred_terms = _diagram_terms(pred)
        if context_terms and pred_terms:
            trace = len(pred_terms & context_terms) / max(1, len(pred_terms))
            if trace < 0.20 and len(pred_terms) >= 5:
                issues.append(f"weak_trace_to_context_without_gold:{trace:.2f}")

    if hard:
        return {
            "key": "no_solving_or_hallucinated_labels",
            "score": 0.0,
            "comment": "; ".join(issues[:10]),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "no_solving_or_hallucinated_labels",
            "score": 0.5,
            "comment": "; ".join(issues[:10]),
            "hard_rule_violated": False,
        }

    return {
        "key": "no_solving_or_hallucinated_labels",
        "score": 1.0,
        "comment": "no solving/explanation or hallucinated label risk detected",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 6: bypass_and_empty_figure_behavior
# ---------------------------------------------------------------------------

def bypass_and_empty_figure_behavior(run, example) -> dict:
    pred = _get_labels_text(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)
    gold = _get_gold_labels(_safe_get_reference(example))
    variation = _safe_get_variation(example)

    if pred is None:
        return {
            "key": "bypass_and_empty_figure_behavior",
            "score": 0.0,
            "comment": "labels_text missing/malformed",
        }

    source_type = _norm(inputs.get("source_type", "")) + " " + _norm(variation)
    payload_size = _source_payload_size(inputs)

    issues = []
    hard = False

    if _contains_any(source_type, TEXT_ONLY_BYPASS_CUES):
        issues.append("text-only/no-figure page should normally bypass Agent 33")
        # If still run, output should be very short/conservative.
        if _word_count(pred) > 8:
            hard = True

    if gold and _word_count(gold) <= 2:
        if _word_count(pred) > 12:
            issues.append("blank_or_low-label_gold_but_predicted_many_labels")
            hard = True
        else:
            return {"key": "bypass_and_empty_figure_behavior", "score": 1.0, "comment": "blank/low-label behavior passed"}

    if payload_size == 0 and not _contains_any(source_type, TEXT_ONLY_BYPASS_CUES):
        issues.append("no figure payload size available")

    if _word_count(pred) < 1 and gold and _word_count(gold) >= 2:
        issues.append("non-empty gold but labels_text nearly empty")
        hard = True

    if hard:
        return {
            "key": "bypass_and_empty_figure_behavior",
            "score": 0.0,
            "comment": "; ".join(issues),
        }

    if issues:
        return {
            "key": "bypass_and_empty_figure_behavior",
            "score": 0.5,
            "comment": "; ".join(issues),
        }

    return {
        "key": "bypass_and_empty_figure_behavior",
        "score": 1.0,
        "comment": "bypass/empty-figure behavior acceptable",
    }


# ---------------------------------------------------------------------------
# Summary evaluator
# ---------------------------------------------------------------------------

def diagram_label_ocr_severity_summary(runs: list, examples: list) -> dict:
    """
    BLOCK:
    - malformed output / wrong key
    - missing figure source input
    - low gold similarity
    - missing numbers, charge signs, point labels, coordinates, or axes
    - full-page question transcription instead of figure labels
    - solving/explaining instead of extracting labels
    - text-only page with long hallucinated labels

    REVIEW:
    - partial gold similarity
    - weak trace to context without gold
    - output slightly verbose
    - no payload-size metadata
    """
    if len(runs) != len(examples):
        return {
            "key": "diagram_label_ocr_severity_summary",
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

        sim = label_similarity(run, example)
        symbols = diagram_symbol_retention(run, example)
        scope = figure_only_scope(run, example)
        no_hall = no_solving_or_hallucinated_labels(run, example)
        bypass = bypass_and_empty_figure_behavior(run, example)

        for result in (sim, symbols, scope, no_hall):
            if result.get("hard_rule_violated"):
                tier_0.append({"example_id": getattr(example, "id", None), "reason": f"{result['key']} hard failure: {result['comment']}"})

        if bypass["score"] == 0.0:
            tier_0.append({"example_id": getattr(example, "id", None), "reason": f"bypass_and_empty_figure_behavior failed: {bypass['comment']}"})

        tier_1_applicable += 6
        for result in (schema, sim, symbols, scope, no_hall, bypass):
            if result["score"] < 1.0:
                tier_1 += 1

        if (
            schema["score"] == 1.0
            and sim["score"] == 1.0
            and symbols["score"] == 1.0
            and scope["score"] == 1.0
            and no_hall["score"] == 1.0
            and bypass["score"] == 1.0
        ):
            variation_passes[variation] = variation_passes.get(variation, 0) + 1

    tier_1_rate = tier_1 / tier_1_applicable if tier_1_applicable else 0.0
    per_variation = {v: round(variation_passes.get(v, 0) / total, 3) for v, total in variation_totals.items()}

    recommendation = "BLOCK" if tier_0 else ("REVIEW" if tier_1_rate > 0.18 else "OK")

    return {
        "key": "diagram_label_ocr_severity_summary",
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
    label_similarity,
    diagram_symbol_retention,
    figure_only_scope,
    no_solving_or_hallucinated_labels,
    bypass_and_empty_figure_behavior,
]

SUMMARY_EVALUATORS = [diagram_label_ocr_severity_summary]
