
"""
studio_slide_deck_evaluators.py

LangSmith custom evaluators for Agent 14: Studio Slide Deck Generator.

Agent role:
- Generates a slide deck from retrieved source excerpts.
- Inputs: context, custom_instructions.
- Output: slide_deck_markdown (Markdown only — matches the dataset contract).
- Agent 10 handles the shared Studio format wrapper; this evaluator focuses on
  slide-deck-specific structure, grounding, and instruction compliance.

Design choice:
- Code-first, not LLM/hybrid.
- Rationale: slide decks are student-facing, but the key risks are highly checkable:
  schema, slide count, bullet structure, no-source fabrication, overlong slides,
  unsupported facts, custom count/focus misses, and source balance.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional


OUTPUT_KEYS = {"slide_deck_markdown"}

NO_SOURCE_VARIATIONS = {"no_source", "empty_context"}
THIN_SOURCE_VARIATIONS = {"thin_source"}
MULTI_SOURCE_VARIATIONS = {"multi_source"}

EMPTY_CONTEXT_MARKERS = {"", "none", "n/a", "no context", "empty", "not provided"}

BANNED_PATTERNS = {
    "as an ai language model",
    "i cannot access",
    "i don't have access",
}

INTERNAL_FORMAT_LEAKS = {
    "slide_deck_markdown",
    "slide_deck_json",
    "json_output",
    "markdown_output",
    "schema",
    "valid json",
}

PLACEHOLDER_PATTERNS = {
    "slide title",
    "bullet 1",
    "bullet 2",
    "content here",
    "placeholder",
    "sample slide",
    "title here",
}

GENERIC_WORDS = {
    "slide", "slides", "deck", "title", "bullets", "bullet", "speaker",
    "notes", "presentation", "present", "topic", "context", "source",
    "sources", "chapter", "student", "students", "using", "based",
    "following", "given", "excerpt", "important", "summary", "overview",
    "introduction", "conclusion", "key", "points", "point",
}

DEFAULT_MIN_SLIDES = 5
DEFAULT_MAX_SLIDES = 8
MAX_BULLETS_PER_SLIDE = 6
MIN_BULLETS_PER_CONTENT_SLIDE = 2
MAX_BULLET_WORDS = 18
MAX_SLIDE_DECK_WORDS_DEFAULT = 420


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
        "it", "as", "by", "from", "source", "context", "excerpt", "slide",
        "slides", "deck", "title", "bullet", "bullets", "speaker", "notes",
        "presentation", "key", "point", "points",
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


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def _is_empty_context(context: str) -> bool:
    return _norm(context) in EMPTY_CONTEXT_MARKERS or _word_count(context) < 3


def _get_output_mode_and_payload(out: Optional[dict]) -> tuple[str, Any]:
    if not isinstance(out, dict):
        return "", None
    if "slide_deck_markdown" in out:
        return "markdown", out.get("slide_deck_markdown")
    return "", None


def _get_text(out: Optional[dict]) -> str:
    mode, payload = _get_output_mode_and_payload(out)
    if mode == "markdown" and isinstance(payload, str):
        return payload
    return ""


def _get_gold_text(ref: Optional[dict]) -> str:
    if not isinstance(ref, dict):
        return ""
    return _get_text(ref)


def _markdown_slide_sections(md: str) -> list[dict]:
    lines = (md or "").splitlines()
    heading_re = re.compile(r"^\s{0,3}#{1,3}\s+(.+?)\s*$")
    slide_indices = []
    for idx, line in enumerate(lines):
        m = heading_re.match(line)
        if m and re.search(r"\bslide\s*\d+\b", m.group(1), flags=re.IGNORECASE):
            slide_indices.append(idx)
    if not slide_indices:
        h2 = [i for i, line in enumerate(lines) if re.match(r"^\s{0,3}##\s+\S+", line)]
        slide_indices = h2 if h2 else []
        if not slide_indices:
            all_h = [i for i, line in enumerate(lines) if heading_re.match(line)]
            slide_indices = all_h[1:] if len(all_h) > 1 else all_h

    sections = []
    for pos, start in enumerate(slide_indices):
        end = slide_indices[pos + 1] if pos + 1 < len(slide_indices) else len(lines)
        title = heading_re.match(lines[start]).group(1).strip()
        title = re.sub(r"^slide\s*\d+\s*[:.)-]?\s*", "", title, flags=re.IGNORECASE).strip() or title
        bullets, paragraphs = [], []
        for line in lines[start + 1:end]:
            if not line.strip():
                continue
            bm = re.match(r"^\s*[-*]\s+(.+)$", line)
            if bm:
                bullets.append(bm.group(1).strip())
            elif not re.match(r"^\s{0,3}#{1,6}\s+", line):
                paragraphs.append(line.strip())
        sections.append({"title": title, "bullets": bullets, "paragraphs": paragraphs})
    return sections


def _slide_sections(out_or_ref: Optional[dict]) -> list[dict]:
    mode, payload = _get_output_mode_and_payload(out_or_ref)
    if mode == "markdown" and isinstance(payload, str):
        return _markdown_slide_sections(payload)
    return []


def _extract_requested_count(custom: str) -> Optional[int]:
    text = _norm(custom)
    for p in [
        r"\bexactly\s+(\d+)\s+slides?\b",
        r"\b(\d+)\s+slides?\b",
        r"\bmake\s+(\d+)\b",
        r"\bgenerate\s+(\d+)\b",
    ]:
        m = re.search(p, text)
        if m:
            return int(m.group(1))
    return None


def _extract_focus_terms(custom: str) -> set[str]:
    terms = set()
    for m in re.findall(r"(?:focus|only|on|about|center(?:ed)? on)\s+([a-zA-Z0-9Ωμ°/+=∩∪^²³(). -]{3,100})", custom, flags=re.IGNORECASE):
        segment = re.split(r"[,;—-]|slides?|class|audience|style|\d+", m, flags=re.IGNORECASE)[0]
        for tok in _content_tokens(segment):
            tok = tok.strip(" .,:;:-_")
            if tok and tok not in GENERIC_WORDS:
                terms.add(tok)
    return terms


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


def _detect_source_markers(context: str) -> set[str]:
    markers = set()
    for p in [
        r"\[source[:\s]+([^\]]+)\]",
        r"\bsource\s*(\d+)\b",
        r"\bfile[:\s]+([A-Za-z0-9_.-]+\.pdf)\b",
        r"\bsource_pdf[:\s]+([A-Za-z0-9_.-]+\.pdf)\b",
    ]:
        for m in re.findall(p, context or "", flags=re.IGNORECASE):
            markers.add(_norm(m))
    return markers


def parse_model_response_to_outputs(raw_text: str) -> dict:
    if not isinstance(raw_text, str):
        return {}
    text = raw_text.strip()
    if not text:
        return {"slide_deck_markdown": ""}
    # Markdown-only contract: if the model wrapped the deck in a JSON object with a
    # slide_deck_markdown string, unwrap it; otherwise treat the raw text as Markdown.
    if "```" not in text:
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict) and isinstance(parsed.get("slide_deck_markdown"), str):
                return {"slide_deck_markdown": parsed["slide_deck_markdown"]}
        except Exception:
            pass
    return {"slide_deck_markdown": text}


def schema_validity(run, example) -> dict:
    out = _safe_get_outputs(run)
    if out is None:
        return {"key": "schema_validity", "score": 0.0, "comment": "outputs missing or not a JSON object"}
    present = set(out.keys())
    if len(present & OUTPUT_KEYS) != 1:
        return {"key": "schema_validity", "score": 0.0, "comment": "slide_deck_markdown must be present"}
    extra = present - OUTPUT_KEYS
    if extra:
        return {"key": "schema_validity", "score": 0.0, "comment": f"unexpected output key(s): {sorted(extra)}"}

    mode, payload = _get_output_mode_and_payload(out)
    if mode == "markdown":
        if not isinstance(payload, str) or not payload.strip():
            return {"key": "schema_validity", "score": 0.0, "comment": "slide_deck_markdown must be a non-empty string"}
    else:
        return {"key": "schema_validity", "score": 0.0, "comment": "unrecognized output mode"}

    return {"key": "schema_validity", "score": 1.0, "comment": f"schema valid ({mode})"}


def slide_count_match(run, example) -> dict:
    out = _safe_get_outputs(run)
    ref = _safe_get_reference(example)
    inputs = _safe_get_inputs(example)
    variation = _safe_get_variation(example)
    sections = _slide_sections(out)
    context = str(inputs.get("context", ""))
    custom = str(inputs.get("custom_instructions", ""))
    text = _get_text(out)

    if variation in NO_SOURCE_VARIATIONS or _is_empty_context(context):
        safe_message = _word_count(text) <= 40 and _contains_any(text, {"no source", "not enough source", "provide source", "empty context"})
        if len(sections) == 0 or safe_message:
            return {"key": "slide_count_match", "score": 1.0, "comment": "no-source case safely avoided slide generation", "hard_rule_violated": False}
        return {"key": "slide_count_match", "score": 0.0, "comment": f"no-source/empty-context case produced {len(sections)} slide(s)", "hard_rule_violated": True}

    requested = _extract_requested_count(custom)
    gold_sections = _slide_sections(ref) if isinstance(ref, dict) else []
    gold_count = len(gold_sections) if gold_sections else None
    expected = requested if requested is not None else gold_count
    if expected is not None:
        if len(sections) == expected:
            return {"key": "slide_count_match", "score": 1.0, "comment": f"slide count matched expected={expected}", "hard_rule_violated": False}
        return {"key": "slide_count_match", "score": 0.0, "comment": f"slide count mismatch: expected={expected}, got={len(sections)}", "hard_rule_violated": True}

    if DEFAULT_MIN_SLIDES <= len(sections) <= DEFAULT_MAX_SLIDES:
        return {"key": "slide_count_match", "score": 1.0, "comment": f"default slide count acceptable: {len(sections)}", "hard_rule_violated": False}
    return {"key": "slide_count_match", "score": 0.5, "comment": f"slide count outside default {DEFAULT_MIN_SLIDES}-{DEFAULT_MAX_SLIDES} range: {len(sections)}", "hard_rule_violated": False}


def presentation_structure_quality(run, example) -> dict:
    out = _safe_get_outputs(run)
    inputs = _safe_get_inputs(example)
    variation = _safe_get_variation(example)
    text = _get_text(out)
    sections = _slide_sections(out)
    context = str(inputs.get("context", ""))

    if variation in NO_SOURCE_VARIATIONS or _is_empty_context(context):
        safe = _word_count(text) <= 40 and _contains_any(text, {"no source", "not enough source", "provide source", "empty context"})
        return {"key": "presentation_structure_quality", "score": 1.0 if safe else 0.0, "comment": "no-source case", "hard_rule_violated": not safe}

    issues, hard = [], False
    if "```" in text:
        issues.append("contains_code_fence"); hard = True
    if _contains_any(text, BANNED_PATTERNS | INTERNAL_FORMAT_LEAKS):
        issues.append("contains_banned_or_internal_phrase"); hard = True
    if _contains_any(text, PLACEHOLDER_PATTERNS):
        issues.append("contains_placeholder_slide_content"); hard = True
    if not sections:
        issues.append("no_slide_sections_detected"); hard = True

    titles = []
    for idx, slide in enumerate(sections):
        title = str(slide.get("title", "")).strip()
        bullets = slide.get("bullets", [])
        paragraphs = slide.get("paragraphs", [])
        if not title:
            issues.append(f"slide_{idx}_missing_title"); hard = True
        titles.append(_norm(title))

        is_edge_slide = idx == 0 or idx == len(sections) - 1
        if not is_edge_slide and len(bullets) < MIN_BULLETS_PER_CONTENT_SLIDE:
            issues.append(f"slide_{idx}_too_few_bullets:{len(bullets)}")
        if len(bullets) > MAX_BULLETS_PER_SLIDE:
            issues.append(f"slide_{idx}_too_many_bullets:{len(bullets)}")
        for b_idx, bullet in enumerate(bullets):
            bw = _word_count(bullet)
            if bw > MAX_BULLET_WORDS:
                issues.append(f"slide_{idx}_bullet_{b_idx}_too_long:{bw}_words")
        for p_idx, para in enumerate(paragraphs):
            if _word_count(para) > 35:
                issues.append(f"slide_{idx}_paragraph_{p_idx}_too_long_for_slide")

    duplicate_titles = sorted({t for t in titles if t and titles.count(t) > 1})
    if duplicate_titles:
        issues.append(f"duplicate_slide_titles:{duplicate_titles[:5]}"); hard = True

    if issues:
        return {"key": "presentation_structure_quality", "score": 0.0 if hard else 0.5, "comment": "; ".join(issues[:12]), "hard_rule_violated": hard}
    return {"key": "presentation_structure_quality", "score": 1.0, "comment": "presentation structure checks passed", "hard_rule_violated": False}


def custom_instruction_compliance(run, example) -> dict:
    out = _safe_get_outputs(run)
    inputs = _safe_get_inputs(example)
    text = _get_text(out)
    sections = _slide_sections(out)
    custom = str(inputs.get("custom_instructions", ""))
    issues = []

    requested_count = _extract_requested_count(custom)
    if requested_count is not None and len(sections) != requested_count:
        issues.append(f"requested_slides_{requested_count}_got_{len(sections)}")

    focus_terms = _extract_focus_terms(custom)
    if focus_terms:
        deck_tokens = {tok.strip(" .,:;:-_") for tok in _tokens(text)}
        missing_focus = [t for t in focus_terms if t not in deck_tokens]
        if len(missing_focus) >= max(1, len(focus_terms) // 2 + 1):
            issues.append(f"focus_terms_not_reflected:{missing_focus[:5]}")

    m = re.search(r"\bclass\s*(\d{1,2})\b|\bgrade\s*(\d{1,2})\b", custom, flags=re.IGNORECASE)
    if m:
        requested_class = next(g for g in m.groups() if g)
        if requested_class not in text:
            issues.append(f"class_or_grade_cue_not_reflected:{requested_class}")

    if re.search(r"\bin\s+hindi\b|हिंदी|हिन्दी", custom, flags=re.IGNORECASE):
        if not re.search(r"[\u0900-\u097F]", text):
            issues.append("hindi_requested_but_no_devanagari_detected")

    if re.search(r"\bexam\b|\bneet\b|\bjee\b|\bcbse\b", custom, flags=re.IGNORECASE):
        if not re.search(r"\bexam\b|\bneet\b|\bjee\b|\bcbse\b|\bquestion\b|\bremember\b|\bkey point\b", text, flags=re.IGNORECASE):
            issues.append("exam_style_requested_but_not_reflected")

    if issues:
        hard = any(x.startswith(("requested_slides", "focus_terms", "hindi_requested")) for x in issues)
        return {"key": "custom_instruction_compliance", "score": 0.0 if hard else 0.5, "comment": "; ".join(issues)}
    return {"key": "custom_instruction_compliance", "score": 1.0, "comment": "custom instruction checks passed"}


def grounding(run, example) -> dict:
    out = _safe_get_outputs(run)
    ref = _safe_get_reference(example)
    inputs = _safe_get_inputs(example)
    variation = _safe_get_variation(example)
    text = _get_text(out)
    context = str(inputs.get("context", ""))

    if variation in NO_SOURCE_VARIATIONS or _is_empty_context(context):
        safe = _word_count(text) <= 40 and _contains_any(text, {"no source", "not enough source", "provide source", "empty context"})
        return {"key": "grounding", "score": 1.0 if safe else 0.0, "comment": "no-source grounding case", "hard_rule_violated": not safe}

    gold = _get_gold_text(ref)
    allowed_terms = _specific_terms(context) | _specific_terms(gold) | _specific_terms(str(inputs.get("custom_instructions", "")))
    output_terms = _specific_terms(text)

    unsupported = sorted([
        t for t in output_terms
        if t not in allowed_terms
        and t not in GENERIC_WORDS
        and not any(t in a or a in t for a in allowed_terms if len(a) >= 4)
    ])

    numeric_or_formula_bad = [t for t in unsupported if re.search(r"\d|=|[ρΔθΩμ]", t)]
    if numeric_or_formula_bad:
        return {"key": "grounding", "score": 0.0, "comment": f"unsupported numeric/formula/symbol content: {numeric_or_formula_bad[:5]}", "hard_rule_violated": True}
    if len(unsupported) >= 10:
        return {"key": "grounding", "score": 0.0, "comment": f"many unsupported terms/facts: {unsupported[:10]}", "hard_rule_violated": True}

    overlap_context = _jaccard(text, context)
    overlap_gold = _jaccard(text, gold) if gold else 0.0
    if overlap_context >= 0.16 or overlap_gold >= 0.24:
        return {"key": "grounding", "score": 1.0, "comment": f"grounded; context_overlap={overlap_context:.2f} gold_overlap={overlap_gold:.2f}", "hard_rule_violated": False}
    if unsupported:
        return {"key": "grounding", "score": 0.5, "comment": f"possible unsupported terms: {unsupported[:7]}", "hard_rule_violated": False}
    return {"key": "grounding", "score": 1.0, "comment": f"grounding acceptable; context_overlap={overlap_context:.2f} gold_overlap={overlap_gold:.2f}", "hard_rule_violated": False}


def coverage_and_length_balance(run, example) -> dict:
    out = _safe_get_outputs(run)
    inputs = _safe_get_inputs(example)
    variation = _safe_get_variation(example)
    text = _get_text(out)
    context = str(inputs.get("context", ""))

    if variation in NO_SOURCE_VARIATIONS or _is_empty_context(context):
        return {"key": "coverage_and_length_balance", "score": 1.0 if _word_count(text) <= 40 else 0.0, "comment": "no-source case"}

    wc = _word_count(text)
    max_words = 240 if variation in THIN_SOURCE_VARIATIONS else MAX_SLIDE_DECK_WORDS_DEFAULT
    issues = []
    if wc > max_words:
        issues.append(f"too_long:{wc}_words")
    if variation in THIN_SOURCE_VARIATIONS and _word_count(context) <= 35 and wc > max(120, _word_count(context) * 6):
        issues.append(f"thin_source_over_expanded:context_words={_word_count(context)} output_words={wc}")

    if variation in MULTI_SOURCE_VARIATIONS:
        markers = _detect_source_markers(context)
        if len(markers) >= 2:
            chunks = re.split(r"\[source[:\s]+[^\]]+\]|\bsource\s*\d+\b|\bfile[:\s]+[A-Za-z0-9_.-]+\.pdf", context, flags=re.IGNORECASE)
            covered = sum(1 for ch in chunks if _word_count(ch) >= 5 and _jaccard(text, ch) >= 0.08)
            if covered < 2:
                issues.append("multi_source_context_but_one_source_coverage")

    sections = _slide_sections(out)
    if len(sections) >= 3:
        titles = [s.get("title", "") for s in sections]
        similar_pairs = []
        for i in range(len(titles)):
            for j in range(i + 1, len(titles)):
                if _jaccard(titles[i], titles[j]) >= 0.75:
                    similar_pairs.append((i, j))
        if similar_pairs:
            issues.append(f"near_duplicate_slide_titles:{similar_pairs[:5]}")

    if issues:
        hard = any(x.startswith("thin_source_over_expanded") for x in issues)
        return {"key": "coverage_and_length_balance", "score": 0.0 if hard else 0.5, "comment": "; ".join(issues)}
    return {"key": "coverage_and_length_balance", "score": 1.0, "comment": f"coverage/length checks passed ({wc} words)"}


def studio_slide_deck_severity_summary(runs: list, examples: list) -> dict:
    if len(runs) != len(examples):
        return {
            "key": "studio_slide_deck_severity_summary",
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
            tier_0.append({"example_id": getattr(example, "id", None), "reason": f"schema_validity failed: {schema['comment']}"})
            continue

        count = slide_count_match(run, example)
        structure = presentation_structure_quality(run, example)
        custom = custom_instruction_compliance(run, example)
        ground = grounding(run, example)
        coverage = coverage_and_length_balance(run, example)

        for result in (count, structure, ground):
            if result.get("hard_rule_violated"):
                tier_0.append({"example_id": getattr(example, "id", None), "reason": f"{result['key']} hard failure: {result['comment']}"})

        if custom["score"] == 0.0 and any(x in custom["comment"] for x in ["requested_slides", "focus_terms", "hindi_requested"]):
            tier_0.append({"example_id": getattr(example, "id", None), "reason": f"custom instruction hard failure: {custom['comment']}"})

        tier_1_applicable += 5
        for result in (count, structure, custom, ground, coverage):
            if result["score"] < 1.0:
                tier_1 += 1

        if all(result["score"] == 1.0 for result in (count, structure, custom, ground, coverage)):
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
        "key": "studio_slide_deck_severity_summary",
        "score": 0.0 if tier_0 else round(1.0 - tier_1_rate, 3),
        "comment": f"ship_recommendation={recommendation} | tier_0_blocking_count={len(tier_0)} | tier_1_review_rate={tier_1_rate:.3f}",
        "tier_0_blocking_count": len(tier_0),
        "tier_0_blocking_examples": tier_0,
        "tier_1_review_rate": round(tier_1_rate, 3),
        "per_variation_pass_rate": per_variation_pass_rate,
        "ship_recommendation": recommendation,
    }


PER_EXAMPLE_EVALUATORS = [
    schema_validity,
    slide_count_match,
    presentation_structure_quality,
    custom_instruction_compliance,
    grounding,
    coverage_and_length_balance,
]

SUMMARY_EVALUATORS = [
    studio_slide_deck_severity_summary,
]
