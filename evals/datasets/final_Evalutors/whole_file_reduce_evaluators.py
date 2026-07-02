"""
whole_file_reduce_evaluators.py

LangSmith custom evaluators for Agent 30: Whole File Reduce.

Agent role:
- REDUCE step in whole-file map-reduce summarization.
- Converts Agent 29 map_summaries / concatenated section_summaries into a final
  student-facing Markdown answer for a whole-document summary request.

Production dependencies:
- Inputs:
    user_message: str
    section_summaries: str | list[str]  # output of Agent 29, usually concatenated
- Output:
    final_answer: str  # student-facing Markdown

Dependency note:
- Agent 30 has a hard dependency on Agent 29.
- It must not run if Agent 29 is skipped or fails.
- Agents 29–30 activate only for:
    single active source + whole-document summary intent + USE_WHOLE_FILE_MAP_REDUCE=True.
- When map-reduce succeeds, standard retrieval/RAG chunk retrieval is bypassed.
- When map-reduce fails, runtime falls back to normal Retrieval → RAG.

Evaluator design:
- Hybrid by default.
- Code gates enforce deterministic REDUCE contract:
  input/output keys, non-empty section summaries, Markdown answer, no map-reduce
  internals, grounding against section_summaries, coverage across multiple map
  summaries, no unsupported formulas/numbers/named facts, user request alignment,
  and suitable whole-document summary structure.
- Required LLM judge evaluates semantic synthesis quality and final-answer usefulness.
- Tier 2 because it is student-facing, but it is a summarization reduce step rather
  than a core problem-solving answerer. It should be stricter than Tier 3 ingestion
  helpers and lighter than Agent 7 RAG answer generator.

LangSmith usage:
    from whole_file_reduce_evaluators import (
        build_per_example_evaluators,
        SUMMARY_EVALUATORS,
    )

    evaluators = build_per_example_evaluators(judge_llm)

Judge callable:
    judge_llm(prompt: str) -> str

Judge must return JSON:
{
  "groundedness_score": 0.0-1.0,
  "coverage_score": 0.0-1.0,
  "synthesis_quality_score": 0.0-1.0,
  "user_request_alignment_score": 0.0-1.0,
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

REQUIRED_INPUT_KEYS = {"user_message", "section_summaries"}
REQUIRED_OUTPUT_KEYS = {"final_answer"}

MIN_FINAL_WORDS = 45
MAX_FINAL_WORDS_DEFAULT = 900

BANNED_PATTERNS = {
    "as an ai language model",
    "i cannot access",
    "i don't have access",
    "not enough context",
    "placeholder",
    "todo",
    "lorem ipsum",
    "final_answer",
    "valid json",
    "system prompt",
    ".j2",
    "jinja",
}

INTERNAL_LEAKS = {
    "map-reduce",
    "map_summaries",
    "section_summaries",
    "agent 29",
    "agent 30",
    "reduce step",
    "pipeline",
    "langsmith",
    "pinecone",
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

GENERIC_SUMMARY_SENTENCES = {
    "this document discusses important concepts.",
    "this file contains useful information.",
    "the document covers key topics for students.",
    "this source is about the chapter and its concepts.",
}

GENERIC_WORDS = {
    "the", "and", "with", "from", "this", "that", "document", "chapter",
    "notes", "question", "questions", "answer", "answers", "summary",
    "topic", "topics", "concept", "concepts", "important", "student",
    "students", "study", "material", "section", "page", "class",
    "source", "text", "contains", "covers", "includes", "part",
    "chunk", "excerpt", "paragraph", "information", "content",
    "file", "overall", "main", "key", "point", "points",
}

REQUEST_SHORT_CUES = {
    "short", "brief", "concise", "quick", "in short", "summarize briefly",
    "crisp", "one paragraph",
}

REQUEST_DETAILED_CUES = {
    "detailed", "complete", "full", "thorough", "elaborate", "comprehensive",
    "in detail", "explain fully",
}

REQUEST_BULLET_CUES = {
    "bullet", "points", "list", "key points", "outline",
}

REQUEST_EXAM_CUES = {
    "exam", "boards", "cbse", "jee", "neet", "important for exam",
    "marks", "revision",
}

MARKDOWN_STRUCTURE_CUES = {
    "##", "-", "*", "1.", "**",
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
    return set(re.findall(r"[a-zA-Z0-9ΩμρΔθ°/+=∩∪^²³().-]+", _norm(text)))


def _content_tokens(text: str) -> set[str]:
    stop = {
        "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with",
        "is", "are", "was", "were", "be", "been", "being", "this", "that",
        "it", "as", "by", "from", "document", "chapter", "source", "text",
        "contains", "covers", "includes", "summary", "part", "chunk", "excerpt",
        "section", "question", "overall", "main", "key", "point", "points",
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


def _section_summaries_text(value: Any) -> str:
    if isinstance(value, list):
        return "\n".join(str(x) for x in value if str(x).strip())
    return str(value or "")


def _section_summary_items(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]

    text = str(value or "").strip()
    if not text:
        return []

    # Prefer line-separated map output. Fall back to sentence chunks.
    lines = [
        re.sub(r"^\s*(?:[-*]|\d+[.)])\s+", "", line).strip()
        for line in text.splitlines()
        if line.strip()
    ]
    if len(lines) >= 2:
        return lines

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    return sentences if len(sentences) >= 2 else [text]


def _parse_final_answer(value: Any) -> tuple[bool, str]:
    if isinstance(value, str):
        return bool(value.strip()), value.strip()
    return False, ""


def _get_final_answer(out: Optional[dict]) -> Optional[str]:
    if not isinstance(out, dict):
        return None
    ok, text = _parse_final_answer(out.get("final_answer"))
    return text if ok else None


def _get_gold_final_answer(ref: Optional[dict]) -> str:
    if not isinstance(ref, dict):
        return ""
    ok, text = _parse_final_answer(ref.get("final_answer"))
    return text if ok else ""


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


def _looks_like_markdown(text: str) -> bool:
    if any(cue in text for cue in MARKDOWN_STRUCTURE_CUES):
        return True
    # Plain paragraphs are acceptable for short user requests.
    return _word_count(text) >= 45 and "\n" in text


def _heading_count(text: str) -> int:
    return len(re.findall(r"^\s*#{1,4}\s+", text or "", flags=re.MULTILINE))


def _bullet_count(text: str) -> int:
    return len(re.findall(r"^\s*(?:[-*]|\d+[.)])\s+", text or "", flags=re.MULTILINE))


def _compression_ratio(answer: str, section_text: str) -> float:
    denom = max(1, _word_count(section_text))
    return _word_count(answer) / denom


def parse_model_response_to_outputs(raw_text: str) -> dict:
    """
    Defensive parser for raw model response.
    Accepts:
      - {"final_answer": "..."}
      - raw markdown as the final answer
    """
    if not isinstance(raw_text, str) or not raw_text.strip():
        return {}

    parsed = _json_from_text(raw_text)
    if isinstance(parsed, dict) and isinstance(parsed.get("final_answer"), str):
        return {"final_answer": parsed["final_answer"]}

    return {"final_answer": raw_text.strip()}


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

    if not isinstance(inputs.get("user_message"), str) or not inputs.get("user_message", "").strip():
        return {"key": "schema_validity", "score": 0.0, "comment": "user_message must be non-empty string"}

    section_text = _section_summaries_text(inputs.get("section_summaries"))
    if _word_count(section_text) < 8:
        return {"key": "schema_validity", "score": 0.0, "comment": "section_summaries missing/thin; Agent 30 requires Agent 29 output"}

    out = _safe_get_outputs(run)
    if out is None:
        return {"key": "schema_validity", "score": 0.0, "comment": "outputs missing or not JSON object"}

    present = set(out.keys())
    if not REQUIRED_OUTPUT_KEYS.issubset(present):
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"output missing required key(s): got={sorted(present)}",
        }

    final = _get_final_answer(out)
    if final is None:
        return {"key": "schema_validity", "score": 0.0, "comment": "final_answer must be non-empty string"}

    wc = _word_count(final)
    if wc < MIN_FINAL_WORDS:
        return {"key": "schema_validity", "score": 0.5, "comment": f"final_answer may be too thin: {wc} words"}

    if wc > MAX_FINAL_WORDS_DEFAULT:
        return {"key": "schema_validity", "score": 0.5, "comment": f"final_answer too long for reduce summary: {wc} words"}

    if "```" in final:
        return {"key": "schema_validity", "score": 0.0, "comment": "final_answer must not be wrapped in code fences"}

    if final.strip().startswith("{") or final.strip().startswith("["):
        return {"key": "schema_validity", "score": 0.0, "comment": "final_answer should be Markdown, not JSON"}

    if _contains_any(final, BANNED_PATTERNS | INTERNAL_LEAKS):
        return {"key": "schema_validity", "score": 0.0, "comment": "final_answer contains banned/internal phrase"}

    return {"key": "schema_validity", "score": 1.0, "comment": "schema valid"}


# ---------------------------------------------------------------------------
# Evaluator 2: dependency_integrity
# ---------------------------------------------------------------------------

def dependency_integrity(run, example) -> dict:
    final = _get_final_answer(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)

    if final is None:
        return {
            "key": "dependency_integrity",
            "score": 0.0,
            "comment": "final_answer missing/malformed",
            "hard_rule_violated": False,
        }

    section_text = _section_summaries_text(inputs.get("section_summaries"))
    items = _section_summary_items(inputs.get("section_summaries"))

    issues = []
    hard = False

    if len(items) == 0:
        issues.append("no_map_summaries_detected")
        hard = True

    if len(items) >= 2:
        covered = 0
        low_indexes = []
        for idx, item in enumerate(items):
            overlap = _jaccard(final, item)
            if overlap >= 0.05 or any(tok in _norm(final) for tok in list(_content_tokens(item))[:5]):
                covered += 1
            else:
                low_indexes.append(idx)

        # The reduce answer should cover most map summaries, but can compress.
        required = max(1, int(len(items) * 0.55))
        if covered < required:
            issues.append(f"weak_coverage_of_map_summaries:covered={covered}/{len(items)} low={low_indexes[:8]}")
            hard = True

    if _jaccard(final, section_text) < 0.08:
        issues.append(f"weak_overall_dependency_on_section_summaries:{_jaccard(final, section_text):.2f}")
        hard = True

    if hard:
        return {
            "key": "dependency_integrity",
            "score": 0.0,
            "comment": "; ".join(issues),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "dependency_integrity",
            "score": 0.5,
            "comment": "; ".join(issues),
            "hard_rule_violated": False,
        }

    return {
        "key": "dependency_integrity",
        "score": 1.0,
        "comment": "final answer depends on Agent 29 section_summaries",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 3: grounded_no_hallucination
# ---------------------------------------------------------------------------

def grounded_no_hallucination(run, example) -> dict:
    final = _get_final_answer(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)
    ref = _safe_get_reference(example)

    if final is None:
        return {
            "key": "grounded_no_hallucination",
            "score": 0.0,
            "comment": "final_answer missing/malformed",
            "hard_rule_violated": False,
        }

    section_text = _section_summaries_text(inputs.get("section_summaries"))
    user = str(inputs.get("user_message", ""))
    gold = _get_gold_final_answer(ref)
    allowed = "\n".join([section_text, user, gold])

    issues = []
    hard = False

    allowed_terms = _specific_terms(allowed)
    produced_terms = _specific_terms(final)

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

    if len(unsupported) >= 10:
        issues.append(f"many_unsupported_terms:{unsupported[:10]}")
        hard = True
    elif unsupported:
        issues.append(f"possible_unsupported_terms:{unsupported[:7]}")

    if _contains_any(final, FOOTER_NOISE):
        issues.append("footer/web/noise included in final answer")
        hard = True

    if _contains_any(final, ANSWER_KEY_NOISE) and not _contains_any(allowed, ANSWER_KEY_NOISE):
        issues.append("answer-key/solution wording introduced without source support")
        hard = True

    if _norm(final) in GENERIC_SUMMARY_SENTENCES:
        issues.append("generic_summary_sentence")
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
        "comment": "final answer is grounded in section_summaries",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 4: synthesis_and_markdown_quality
# ---------------------------------------------------------------------------

def synthesis_and_markdown_quality(run, example) -> dict:
    final = _get_final_answer(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)

    if final is None:
        return {
            "key": "synthesis_and_markdown_quality",
            "score": 0.0,
            "comment": "final_answer missing/malformed",
            "hard_rule_violated": False,
        }

    section_text = _section_summaries_text(inputs.get("section_summaries"))
    user = str(inputs.get("user_message", ""))

    issues = []
    hard = False

    if not _looks_like_markdown(final):
        issues.append("answer_not_markdown_or_structured_text")

    headings = _heading_count(final)
    bullets = _bullet_count(final)

    if _contains_any(user, REQUEST_BULLET_CUES) and bullets < 3:
        issues.append("user_asked_for_points_but_bullets_missing")

    if _contains_any(user, REQUEST_DETAILED_CUES) and _word_count(final) < 120:
        issues.append("user_asked_detailed_but_answer_too_short")

    if _contains_any(user, REQUEST_SHORT_CUES) and _word_count(final) > 220:
        issues.append("user_asked_short_but_answer_too_long")
        hard = True

    if not _contains_any(user, REQUEST_SHORT_CUES):
        # Whole-document summaries should normally have at least a simple structure.
        if headings == 0 and bullets < 3 and _word_count(section_text) >= 100:
            issues.append("whole_document_summary_lacks_structure")

    # It should synthesize, not merely paste every map summary.
    ratio = _compression_ratio(final, section_text)
    if _word_count(section_text) >= 150 and ratio > 0.80:
        issues.append(f"answer_may_paste_map_summaries_ratio={ratio:.2f}")
        hard = True
    elif _word_count(section_text) >= 100 and ratio > 0.65:
        issues.append(f"weak_reduce_compression_ratio={ratio:.2f}")

    # Avoid listing "part 1/part 2" unless user asks for section-wise summary.
    if re.search(r"\b(part|chunk|map summary)\s+\d+\b", final, flags=re.IGNORECASE):
        if not _contains_any(user, {"section-wise", "part-wise", "by section"}):
            issues.append("exposes_map_or_chunk_structure_to_student")

    if hard:
        return {
            "key": "synthesis_and_markdown_quality",
            "score": 0.0,
            "comment": "; ".join(issues),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "synthesis_and_markdown_quality",
            "score": 0.5,
            "comment": "; ".join(issues),
            "hard_rule_violated": False,
        }

    return {
        "key": "synthesis_and_markdown_quality",
        "score": 1.0,
        "comment": "Markdown structure and reduce synthesis checks passed",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 5: user_request_alignment
# ---------------------------------------------------------------------------

def user_request_alignment(run, example) -> dict:
    final = _get_final_answer(_safe_get_outputs(run))
    inputs = _safe_get_inputs(example)

    if final is None:
        return {"key": "user_request_alignment", "score": 0.0, "comment": "final_answer missing/malformed"}

    user = str(inputs.get("user_message", ""))
    section_text = _section_summaries_text(inputs.get("section_summaries"))

    issues = []

    # Summary intent should be honored by not answering a single narrow question only.
    if _contains_any(user, {"whole", "entire", "full document", "complete document", "summarize the document", "summary"}):
        # Need at least broad coverage terms from multiple section summaries.
        if _jaccard(final, section_text) < 0.10:
            issues.append("whole_document_summary_request_not_broadly_addressed")

    if _contains_any(user, REQUEST_EXAM_CUES):
        if not _contains_any(final, {"exam", "important", "revision", "question", "asked", "marks", "practice", "key point"}):
            issues.append("exam_or_revision_angle_missing")

    if _contains_any(user, {"teach", "explain", "understand"}):
        if not _contains_any(final, {"means", "because", "helps", "idea", "concept", "understand"}):
            issues.append("teaching_explanation_angle_missing")

    # If user asks for source-only answer / no outside knowledge, answer should not claim outside info.
    if _contains_any(user, {"only from", "use only", "source only", "uploaded file"}):
        if _contains_any(final, {"outside", "in general", "beyond the document", "commonly"}):
            issues.append("source_only_request_may_use_outside_framing")

    if issues:
        hard = any("source_only" in x for x in issues)
        return {
            "key": "user_request_alignment",
            "score": 0.0 if hard else 0.5,
            "comment": "; ".join(issues),
        }

    return {"key": "user_request_alignment", "score": 1.0, "comment": "user request alignment passed"}


# ---------------------------------------------------------------------------
# Evaluator 6: gold_alignment
# ---------------------------------------------------------------------------

def gold_alignment(run, example) -> dict:
    final = _get_final_answer(_safe_get_outputs(run))
    ref = _safe_get_reference(example)
    gold = _get_gold_final_answer(ref)

    if final is None:
        return {"key": "gold_alignment", "score": 0.0, "comment": "final_answer missing/malformed"}

    if not gold:
        return {"key": "gold_alignment", "score": 1.0, "comment": "no gold final_answer supplied; skipped"}

    overlap = _jaccard(final, gold)

    final_terms = _specific_terms(final)
    gold_terms = _specific_terms(gold)
    if gold_terms:
        term_recall = len(final_terms & gold_terms) / max(1, len(gold_terms))
    else:
        term_recall = overlap

    if overlap < 0.12 and term_recall < 0.25:
        return {
            "key": "gold_alignment",
            "score": 0.0,
            "comment": f"low gold alignment overlap={overlap:.2f}, term_recall={term_recall:.2f}",
        }

    if overlap < 0.22 or term_recall < 0.45:
        return {
            "key": "gold_alignment",
            "score": 0.5,
            "comment": f"partial gold alignment overlap={overlap:.2f}, term_recall={term_recall:.2f}",
        }

    return {
        "key": "gold_alignment",
        "score": 1.0,
        "comment": f"gold alignment passed overlap={overlap:.2f}, term_recall={term_recall:.2f}",
    }


# ---------------------------------------------------------------------------
# Evaluator 7: required LLM judge
# ---------------------------------------------------------------------------

def make_required_llm_reduce_judge(judge_llm: Callable[[str], str]):
    def required_llm_reduce_judge(run, example) -> dict:
        final = _get_final_answer(_safe_get_outputs(run))
        inputs = _safe_get_inputs(example)
        ref = _safe_get_reference(example)

        if final is None:
            return {
                "key": "required_llm_reduce_judge",
                "score": 0.0,
                "comment": "final_answer missing/malformed",
                "hard_rule_violated": True,
                "judge_available": False,
            }

        section_summaries = _section_summaries_text(inputs.get("section_summaries"))
        gold = _get_gold_final_answer(ref)

        prompt = f"""
You are evaluating ScholarSync's Whole File Reduce summarizer.

Evaluate the final answer ONLY against:
- user message,
- Agent 29 section_summaries,
- gold/reference final answer if supplied.

Return ONLY valid JSON:
{{
  "groundedness_score": <0.0 to 1.0>,
  "coverage_score": <0.0 to 1.0>,
  "synthesis_quality_score": <0.0 to 1.0>,
  "user_request_alignment_score": <0.0 to 1.0>,
  "format_score": <0.0 to 1.0>,
  "comment": "<short reason, max 45 words>"
}}

Scoring guidance:
- groundedness_score: no facts, formulas, numbers, or claims beyond section_summaries/gold.
- coverage_score: covers the whole document, not only the first or last map summary.
- synthesis_quality_score: integrates summaries into a coherent student-facing whole-file summary.
- user_request_alignment_score: follows length/style/angle asked by user.
- format_score: clean Markdown; no JSON, no map-reduce internals, no citations invented.

User message:
{inputs.get("user_message", "")}

Agent 29 section_summaries:
{section_summaries}

Gold/reference final answer:
{gold}

Candidate final_answer:
{final}
""".strip()

        try:
            raw = judge_llm(prompt)
        except Exception as exc:
            return {
                "key": "required_llm_reduce_judge",
                "score": 0.0,
                "comment": f"judge call failed: {exc}",
                "hard_rule_violated": False,
                "judge_available": False,
            }

        parsed = _json_from_text(raw)
        if not parsed:
            return {
                "key": "required_llm_reduce_judge",
                "score": 0.0,
                "comment": f"judge returned invalid JSON: {str(raw)[:160]}",
                "hard_rule_violated": False,
                "judge_available": False,
            }

        grounded = _coerce_score(parsed.get("groundedness_score"))
        coverage = _coerce_score(parsed.get("coverage_score"))
        synthesis = _coerce_score(parsed.get("synthesis_quality_score"))
        user_align = _coerce_score(parsed.get("user_request_alignment_score"))
        fmt = _coerce_score(parsed.get("format_score"))
        comment = str(parsed.get("comment", "")).strip()

        score = round(
            (0.30 * grounded)
            + (0.25 * coverage)
            + (0.20 * synthesis)
            + (0.15 * user_align)
            + (0.10 * fmt),
            3,
        )

        hard = grounded < 0.70 or coverage < 0.65 or synthesis < 0.60 or fmt < 0.65

        return {
            "key": "required_llm_reduce_judge",
            "score": score,
            "comment": (
                f"grounded={grounded:.2f} coverage={coverage:.2f} synthesis={synthesis:.2f} "
                f"user_align={user_align:.2f} format={fmt:.2f} | {comment}"
            ),
            "groundedness_score": grounded,
            "coverage_score": coverage,
            "synthesis_quality_score": synthesis,
            "user_request_alignment_score": user_align,
            "format_score": fmt,
            "hard_rule_violated": hard,
            "judge_available": True,
        }

    return required_llm_reduce_judge


def build_per_example_evaluators(judge_llm: Callable[[str], str]) -> list[Callable]:
    if judge_llm is None or not callable(judge_llm):
        raise ValueError("Agent 30 evaluation requires judge_llm. Use build_per_example_evaluators(judge_llm).")

    return [
        schema_validity,
        dependency_integrity,
        grounded_no_hallucination,
        synthesis_and_markdown_quality,
        user_request_alignment,
        gold_alignment,
        make_required_llm_reduce_judge(judge_llm),
    ]


# ---------------------------------------------------------------------------
# Summary evaluator
# ---------------------------------------------------------------------------

def whole_file_reduce_severity_summary(runs: list, examples: list) -> dict:
    """
    BLOCK:
    - invalid schema / wrong output key
    - missing/thin section_summaries dependency
    - weak dependency on Agent 29 summaries
    - unsupported formulas/numbers/named facts
    - source-only request violation
    - exposes map-reduce internals
    - LLM judge hard failure

    REVIEW:
    - weak structure
    - partial gold alignment
    - weak compression/synthesis
    - minor possible unsupported terms
    """
    if len(runs) != len(examples):
        return {
            "key": "whole_file_reduce_severity_summary",
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

        dep = dependency_integrity(run, example)
        grounded = grounded_no_hallucination(run, example)
        synth = synthesis_and_markdown_quality(run, example)
        user = user_request_alignment(run, example)
        gold = gold_alignment(run, example)
        llm = _extract_required_llm_feedback(run)

        for result in (dep, grounded, synth):
            if result.get("hard_rule_violated"):
                tier_0.append({"example_id": getattr(example, "id", None), "reason": f"{result['key']} hard failure: {result['comment']}"})

        if user["score"] == 0.0:
            tier_0.append({"example_id": getattr(example, "id", None), "reason": f"user_request_alignment failed: {user['comment']}"})

        if gold["score"] == 0.0:
            tier_0.append({"example_id": getattr(example, "id", None), "reason": f"gold_alignment failed: {gold['comment']}"})

        if llm is not None:
            if llm.get("hard_rule_violated") or llm.get("score", 0.0) < 0.72:
                tier_0.append({"example_id": getattr(example, "id", None), "reason": f"LLM judge hard failure: {llm.get('comment', '')}"})
            elif llm.get("score", 1.0) < 0.86:
                tier_1 += 1
                tier_1_applicable += 1

        tier_1_applicable += 7
        for result in (schema, dep, grounded, synth, user, gold):
            if result["score"] < 1.0:
                tier_1 += 1

        llm_ok = True if llm is None else llm.get("score", 0.0) >= 0.86
        if (
            schema["score"] == 1.0
            and dep["score"] == 1.0
            and grounded["score"] == 1.0
            and synth["score"] == 1.0
            and user["score"] == 1.0
            and gold["score"] == 1.0
            and llm_ok
        ):
            variation_passes[variation] = variation_passes.get(variation, 0) + 1

    tier_1_rate = tier_1 / tier_1_applicable if tier_1_applicable else 0.0
    per_variation = {v: round(variation_passes.get(v, 0) / total, 3) for v, total in variation_totals.items()}

    recommendation = "BLOCK" if tier_0 else ("REVIEW" if tier_1_rate > 0.16 else "OK")

    return {
        "key": "whole_file_reduce_severity_summary",
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
            if val.get("key") == "required_llm_reduce_judge":
                return val
            maybe = val.get("required_llm_reduce_judge")
            if isinstance(maybe, dict):
                return maybe
            if isinstance(maybe, (int, float)):
                return {
                    "key": "required_llm_reduce_judge",
                    "score": float(maybe),
                    "comment": "score extracted from run feedback mapping",
                    "hard_rule_violated": float(maybe) < 0.72,
                }
        if isinstance(val, list):
            for item in val:
                if isinstance(item, dict) and item.get("key") == "required_llm_reduce_judge":
                    return item
    return None


# ---------------------------------------------------------------------------
# Public registries
# ---------------------------------------------------------------------------

PER_EXAMPLE_EVALUATORS_CODE_ONLY = [
    schema_validity,
    dependency_integrity,
    grounded_no_hallucination,
    synthesis_and_markdown_quality,
    user_request_alignment,
    gold_alignment,
]

PER_EXAMPLE_EVALUATORS = None

SUMMARY_EVALUATORS = [whole_file_reduce_severity_summary]
