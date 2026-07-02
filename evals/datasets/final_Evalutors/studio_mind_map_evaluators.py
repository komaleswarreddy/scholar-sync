"""
studio_mind_map_evaluators.py

LangSmith custom evaluators for Agent 13: Studio Mind Map Generator.

Agent role:
- Generates a structured mind map from retrieved source excerpts.
- Production pairs the shared Studio system prompt (#10) with the mind map task prompt.
- Custom instructions may override focus, depth, hierarchy, or output style.

Production dependencies:
- Inputs:
    context: str
    custom_instructions: str
- Output:
    mind_map_markdown: str

Recommended structure:
    # <Central Topic>

    - <Main Branch>
      - <Sub-branch>
        - <Leaf / detail>

or equivalent clean Markdown hierarchy.

- Depends on retrieved Studio context.
- Studio retrieval may use Query Rewriter (#2) upstream.
- Agent 13 is wrapped by Studio System JSON / format behavior (#10), but this
  evaluator should only require context + custom_instructions.

Design choice:
- Code-first, not LLM/hybrid.
- Criticality: Tier 2, student-facing Studio output.
- Mind maps need relationship quality, but most important failures are still
  checkable without an LLM judge:
  malformed markdown, no hierarchy, flat list, no central topic, weak grounding,
  unsupported terms, custom focus misses, duplicate branches, no-source fabrication,
  and over-expansion from thin sources.
- Avoid an LLM judge here to prevent overfitting/cost. Use Agent 7’s required LLM
  judge for final RAG semantic answer quality.

LangSmith usage:
    from studio_mind_map_evaluators import PER_EXAMPLE_EVALUATORS, SUMMARY_EVALUATORS

    client.evaluate(
        target_fn,
        data="nbm-prompt-studio_mind_map",
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

REQUIRED_KEYS = {"mind_map_markdown"}
ALLOWED_KEYS = {"mind_map_markdown"}

NO_SOURCE_VARIATIONS = {"no_source", "empty_context"}
THIN_SOURCE_VARIATIONS = {"thin_source"}
MULTI_SOURCE_VARIATIONS = {"multi_source"}

EMPTY_CONTEXT_MARKERS = {
    "", "none", "n/a", "no context", "empty", "not provided",
}

BANNED_PATTERNS = {
    "as an ai language model",
    "i cannot access",
    "i don't have access",
}

INTERNAL_FORMAT_LEAKS = {
    "mind_map_markdown",
    "json_output",
    "markdown_output",
    "schema",
    "valid json",
}

PLACEHOLDER_PATTERNS = {
    "main branch 1",
    "main branch 2",
    "sub branch",
    "sub-branch",
    "detail here",
    "topic here",
    "placeholder",
    "sample branch",
}

GENERIC_WORDS = {
    "mind", "map", "branch", "branches", "node", "nodes", "topic", "topics",
    "main", "sub", "leaf", "detail", "details", "concept", "concepts",
    "context", "source", "sources", "chapter", "student", "students",
    "using", "based", "following", "given", "excerpt", "important",
    "summary", "central", "hierarchy", "related", "relationship",
}

RELATIONSHIP_MARKERS = {
    "causes", "leads to", "results in", "depends on", "includes", "contains",
    "classified into", "types", "examples", "properties", "formula",
    "because", "therefore", "used for", "function", "role", "part of",
    "occurs", "produces", "uses", "absorbs", "forms", "helps",
}

MAX_WORDS_DEFAULT = 280
MIN_BRANCHES_DEFAULT = 3
MAX_BRANCHES_DEFAULT = 8
MIN_HIERARCHY_DEPTH = 2


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
        "it", "as", "by", "from", "source", "context", "excerpt", "mind",
        "map", "branch", "branches", "node", "nodes", "topic", "topics",
        "main", "sub", "central", "detail",
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


def _get_markdown(out: Optional[dict]) -> Optional[str]:
    if not isinstance(out, dict):
        return None
    val = out.get("mind_map_markdown")
    return val if isinstance(val, str) else None


def _get_gold_markdown(ref: Optional[dict]) -> str:
    if not isinstance(ref, dict):
        return ""
    val = ref.get("mind_map_markdown", "")
    return val if isinstance(val, str) else str(val)


def _markdown_lines(md: str) -> list[str]:
    return [line.rstrip() for line in (md or "").splitlines() if line.strip()]


def _heading_lines(md: str) -> list[str]:
    return [line for line in _markdown_lines(md) if re.match(r"^\s{0,3}#{1,6}\s+\S+", line)]


def _bullet_lines(md: str) -> list[str]:
    return [line for line in _markdown_lines(md) if re.match(r"^\s*[-*]\s+\S+", line)]


def _bullet_depth(line: str) -> int:
    # 2 spaces per nesting level; top bullet depth = 1.
    m = re.match(r"^(\s*)[-*]\s+", line)
    if not m:
        return 0
    return 1 + (len(m.group(1).replace("\t", "  ")) // 2)


def _max_bullet_depth(md: str) -> int:
    depths = [_bullet_depth(line) for line in _bullet_lines(md)]
    return max(depths) if depths else 0


def _top_level_branches(md: str) -> list[str]:
    return [
        re.sub(r"^\s*[-*]\s+", "", line).strip()
        for line in _bullet_lines(md)
        if _bullet_depth(line) == 1
    ]


def _all_nodes(md: str) -> list[str]:
    nodes = []
    for line in _heading_lines(md):
        nodes.append(re.sub(r"^\s{0,3}#{1,6}\s+", "", line).strip())
    for line in _bullet_lines(md):
        nodes.append(re.sub(r"^\s*[-*]\s+", "", line).strip())
    return [n for n in nodes if n]


def _extract_requested_depth(custom: str) -> Optional[int]:
    text = _norm(custom)
    patterns = [
        r"\bdepth\s*(\d+)\b",
        r"\b(\d+)\s*levels?\b",
        r"\b(\d+)\s*layers?\b",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return int(m.group(1))
    return None


def _extract_requested_branches(custom: str) -> Optional[int]:
    text = _norm(custom)
    patterns = [
        r"\bexactly\s+(\d+)\s+(?:branches|main branches)\b",
        r"\b(\d+)\s+(?:branches|main branches)\b",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return int(m.group(1))
    return None


def _extract_focus_terms(custom: str) -> set[str]:
    terms = set()
    for m in re.findall(r"(?:focus|only|on|about|center(?:ed)? on)\s+([a-zA-Z0-9Ωμ°/+=∩∪^²³(). -]{3,90})", custom, flags=re.IGNORECASE):
        segment = re.split(r"[,;—-]|depth|levels?|branches|layers?|\d+", m, flags=re.IGNORECASE)[0]
        for tok in _content_tokens(segment):
            if tok not in GENERIC_WORDS:
                terms.add(tok)
    return terms


def _specific_terms(text: str) -> set[str]:
    """
    Conservative factual-term extraction for grounding.
    """
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
    """
    Defensive parser for raw model text.
    If JSON contains mind_map_markdown, parse it. Otherwise wrap text as markdown.
    """
    if not isinstance(raw_text, str):
        return {}
    text = raw_text.strip()
    if not text:
        return {"mind_map_markdown": ""}

    if "```" in text:
        # Mind map output should not use fences. Still try to unwrap if JSON was fenced.
        fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fence:
            try:
                parsed = json.loads(fence.group(1))
                if isinstance(parsed, dict) and isinstance(parsed.get("mind_map_markdown"), str):
                    return {"mind_map_markdown": parsed["mind_map_markdown"]}
            except Exception:
                pass
        return {"mind_map_markdown": text}

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict) and isinstance(parsed.get("mind_map_markdown"), str):
            return {"mind_map_markdown": parsed["mind_map_markdown"]}
    except Exception:
        pass

    return {"mind_map_markdown": text}


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

    md = out.get("mind_map_markdown")
    if not isinstance(md, str):
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": f"mind_map_markdown must be string, got {type(md).__name__}",
        }

    if not md.strip():
        return {
            "key": "schema_validity",
            "score": 0.0,
            "comment": "mind_map_markdown is empty",
        }

    return {
        "key": "schema_validity",
        "score": 1.0,
        "comment": "schema valid",
    }


# ---------------------------------------------------------------------------
# Evaluator 2: markdown_mindmap_structure
# ---------------------------------------------------------------------------

def markdown_mindmap_structure(run, example) -> dict:
    out = _safe_get_outputs(run)
    inputs = _safe_get_inputs(example)
    variation = _safe_get_variation(example)

    md = _get_markdown(out)
    if md is None:
        return {
            "key": "markdown_mindmap_structure",
            "score": 0.0,
            "comment": "mind_map_markdown missing/non-string",
            "hard_rule_violated": False,
        }

    context = str(inputs.get("context", ""))

    if variation in NO_SOURCE_VARIATIONS or _is_empty_context(context):
        # Safe no-source message can be plain text, not necessarily hierarchy.
        if _word_count(md) <= 35 and _contains_any(md, {"no source", "not enough source", "provide source", "empty context"}):
            return {
                "key": "markdown_mindmap_structure",
                "score": 1.0,
                "comment": "no-source safe message accepted",
                "hard_rule_violated": False,
            }
        return {
            "key": "markdown_mindmap_structure",
            "score": 0.0,
            "comment": "no-source case produced unsupported mind map content",
            "hard_rule_violated": True,
        }

    issues = []
    hard = False

    if "```" in md:
        issues.append("contains_code_fence")
        hard = True

    if _contains_any(md, BANNED_PATTERNS | INTERNAL_FORMAT_LEAKS):
        issues.append("contains_banned_or_internal_phrase")
        hard = True

    if _contains_any(md, PLACEHOLDER_PATTERNS):
        issues.append("contains_placeholder_nodes")
        hard = True

    headings = _heading_lines(md)
    bullets = _bullet_lines(md)
    top = _top_level_branches(md)
    max_depth = _max_bullet_depth(md)

    if not headings:
        issues.append("missing_central_topic_heading")

    if len(bullets) < 3:
        issues.append("too_few_bullets_for_mind_map")
        hard = True

    if len(top) < MIN_BRANCHES_DEFAULT:
        issues.append(f"too_few_main_branches:{len(top)}")

    if len(top) > MAX_BRANCHES_DEFAULT:
        issues.append(f"too_many_main_branches:{len(top)}")

    if max_depth < MIN_HIERARCHY_DEPTH:
        issues.append(f"flat_map_depth_{max_depth}")
        hard = True

    # Avoid pure prose paragraphs without structure.
    non_structured_lines = [
        l for l in _markdown_lines(md)
        if not re.match(r"^\s{0,3}#{1,6}\s+\S+", l) and not re.match(r"^\s*[-*]\s+\S+", l)
    ]
    if len(non_structured_lines) > 3:
        issues.append("too_many_unstructured_lines")

    if hard:
        return {
            "key": "markdown_mindmap_structure",
            "score": 0.0,
            "comment": "; ".join(issues),
            "hard_rule_violated": True,
        }

    if issues:
        return {
            "key": "markdown_mindmap_structure",
            "score": 0.5,
            "comment": "; ".join(issues),
            "hard_rule_violated": False,
        }

    return {
        "key": "markdown_mindmap_structure",
        "score": 1.0,
        "comment": f"mind map structure passed; branches={len(top)} depth={max_depth}",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 3: hierarchy_and_relationship_quality
# ---------------------------------------------------------------------------

def hierarchy_and_relationship_quality(run, example) -> dict:
    """
    Checks that the map is not just a random list:
    - top-level branches are distinct
    - child nodes relate to parent nodes through overlap or relationship cues
    - map has some relationship wording where appropriate
    """
    out = _safe_get_outputs(run)
    inputs = _safe_get_inputs(example)
    variation = _safe_get_variation(example)

    md = _get_markdown(out)
    if md is None:
        return {
            "key": "hierarchy_and_relationship_quality",
            "score": 0.0,
            "comment": "mind_map_markdown missing/non-string",
        }

    context = str(inputs.get("context", ""))

    if variation in NO_SOURCE_VARIATIONS or _is_empty_context(context):
        return {
            "key": "hierarchy_and_relationship_quality",
            "score": 1.0 if _word_count(md) <= 35 else 0.0,
            "comment": "no-source case",
        }

    top = _top_level_branches(md)
    nodes = _all_nodes(md)

    issues = []

    # Top-level branches should not be near duplicates.
    for i in range(len(top)):
        for j in range(i + 1, len(top)):
            if _jaccard(top[i], top[j]) >= 0.75:
                issues.append(f"near_duplicate_main_branches:{i},{j}")
                break

    # Relationship marker is not mandatory for formula-heavy maps, but useful in concept maps.
    has_relationship_marker = _contains_any(md, RELATIONSHIP_MARKERS)
    context_has_relationships = _contains_any(context, RELATIONSHIP_MARKERS) or _word_count(context) >= 40
    if context_has_relationships and not has_relationship_marker:
        issues.append("relationship_markers_missing")

    # Detect excessive one-word branches.
    one_word_top = [b for b in top if _word_count(b) <= 1]
    if len(one_word_top) >= max(3, len(top) // 2 + 1):
        issues.append("too_many_one_word_main_branches")

    # Avoid duplicate nodes across the map.
    norm_nodes = [_norm(n) for n in nodes]
    duplicates = sorted({n for n in norm_nodes if norm_nodes.count(n) > 1 and len(n) > 3})
    if duplicates:
        issues.append(f"duplicate_nodes:{duplicates[:5]}")

    if issues:
        hard = any(x.startswith(("near_duplicate", "duplicate_nodes")) for x in issues)
        return {
            "key": "hierarchy_and_relationship_quality",
            "score": 0.0 if hard else 0.5,
            "comment": "; ".join(issues),
        }

    return {
        "key": "hierarchy_and_relationship_quality",
        "score": 1.0,
        "comment": "hierarchy/relationship checks passed",
    }


# ---------------------------------------------------------------------------
# Evaluator 4: custom_instruction_compliance
# ---------------------------------------------------------------------------

def custom_instruction_compliance(run, example) -> dict:
    out = _safe_get_outputs(run)
    inputs = _safe_get_inputs(example)

    md = _get_markdown(out)
    if md is None:
        return {
            "key": "custom_instruction_compliance",
            "score": 0.0,
            "comment": "mind_map_markdown missing/non-string",
        }

    custom = str(inputs.get("custom_instructions", ""))
    issues = []

    requested_depth = _extract_requested_depth(custom)
    if requested_depth is not None:
        actual_depth = _max_bullet_depth(md)
        # requested 3 levels means central topic + branch + leaf. Bullet depth 2 is acceptable.
        required_bullet_depth = max(1, requested_depth - 1)
        if actual_depth < required_bullet_depth:
            issues.append(f"requested_depth_{requested_depth}_actual_bullet_depth_{actual_depth}")

    requested_branches = _extract_requested_branches(custom)
    if requested_branches is not None:
        actual = len(_top_level_branches(md))
        if actual != requested_branches:
            issues.append(f"requested_branches_{requested_branches}_got_{actual}")

    focus_terms = _extract_focus_terms(custom)
    if focus_terms:
        md_tokens = _tokens(md)
        missing_focus = [t for t in focus_terms if t not in md_tokens]
        if len(missing_focus) >= max(1, len(focus_terms) // 2 + 1):
            issues.append(f"focus_terms_not_reflected:{missing_focus[:5]}")

    if re.search(r"\bin\s+hindi\b|हिंदी|हिन्दी", custom, flags=re.IGNORECASE):
        if not re.search(r"[\u0900-\u097F]", md):
            issues.append("hindi_requested_but_no_devanagari_detected")

    if issues:
        hard = any(x.startswith(("requested_depth", "requested_branches", "focus_terms", "hindi_requested")) for x in issues)
        return {
            "key": "custom_instruction_compliance",
            "score": 0.0 if hard else 0.5,
            "comment": "; ".join(issues),
        }

    return {
        "key": "custom_instruction_compliance",
        "score": 1.0,
        "comment": "custom instruction checks passed",
    }


# ---------------------------------------------------------------------------
# Evaluator 5: grounding
# ---------------------------------------------------------------------------

def grounding(run, example) -> dict:
    out = _safe_get_outputs(run)
    ref = _safe_get_reference(example)
    inputs = _safe_get_inputs(example)
    variation = _safe_get_variation(example)

    md = _get_markdown(out)
    if md is None:
        return {
            "key": "grounding",
            "score": 0.0,
            "comment": "mind_map_markdown missing/non-string",
            "hard_rule_violated": False,
        }

    context = str(inputs.get("context", ""))
    if variation in NO_SOURCE_VARIATIONS or _is_empty_context(context):
        safe = _word_count(md) <= 35 and _contains_any(md, {"no source", "not enough source", "provide source", "empty context"})
        return {
            "key": "grounding",
            "score": 1.0 if safe else 0.0,
            "comment": "no-source grounding case",
            "hard_rule_violated": not safe,
        }

    gold = _get_gold_markdown(ref)
    allowed_terms = (
        _specific_terms(context)
        | _specific_terms(gold)
        | _specific_terms(str(inputs.get("custom_instructions", "")))
    )
    output_terms = _specific_terms(md)

    unsupported = sorted([
        t for t in output_terms
        if t not in allowed_terms
        and t not in GENERIC_WORDS
        and not any(t in a or a in t for a in allowed_terms if len(a) >= 4)
    ])

    numeric_or_formula_bad = [t for t in unsupported if re.search(r"\d|=|[ρΔθΩμ]", t)]
    if numeric_or_formula_bad:
        return {
            "key": "grounding",
            "score": 0.0,
            "comment": f"unsupported numeric/formula/symbol content: {numeric_or_formula_bad[:5]}",
            "hard_rule_violated": True,
        }

    if len(unsupported) >= 8:
        return {
            "key": "grounding",
            "score": 0.0,
            "comment": f"many unsupported terms/facts: {unsupported[:10]}",
            "hard_rule_violated": True,
        }

    overlap_context = _jaccard(md, context)
    overlap_gold = _jaccard(md, gold) if gold else 0.0

    if overlap_context >= 0.16 or overlap_gold >= 0.24:
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
            "comment": f"possible unsupported terms: {unsupported[:6]}",
            "hard_rule_violated": False,
        }

    return {
        "key": "grounding",
        "score": 1.0,
        "comment": f"grounding acceptable; context_overlap={overlap_context:.2f} gold_overlap={overlap_gold:.2f}",
        "hard_rule_violated": False,
    }


# ---------------------------------------------------------------------------
# Evaluator 6: coverage_and_length_balance
# ---------------------------------------------------------------------------

def coverage_and_length_balance(run, example) -> dict:
    out = _safe_get_outputs(run)
    inputs = _safe_get_inputs(example)
    variation = _safe_get_variation(example)

    md = _get_markdown(out)
    if md is None:
        return {
            "key": "coverage_and_length_balance",
            "score": 0.0,
            "comment": "mind_map_markdown missing/non-string",
        }

    context = str(inputs.get("context", ""))

    if variation in NO_SOURCE_VARIATIONS or _is_empty_context(context):
        return {
            "key": "coverage_and_length_balance",
            "score": 1.0 if _word_count(md) <= 35 else 0.0,
            "comment": "no-source case",
        }

    wc = _word_count(md)
    max_words = 180 if variation in THIN_SOURCE_VARIATIONS else MAX_WORDS_DEFAULT
    issues = []

    if wc > max_words:
        issues.append(f"too_long:{wc}_words")

    if variation in THIN_SOURCE_VARIATIONS and _word_count(context) <= 30 and wc > max(80, _word_count(context) * 5):
        issues.append(f"thin_source_over_expanded:context_words={_word_count(context)} output_words={wc}")

    # Multi-source balance: if explicit source markers exist, map should cover at least two source chunks.
    if variation in MULTI_SOURCE_VARIATIONS:
        markers = _detect_source_markers(context)
        if len(markers) >= 2:
            chunks = re.split(
                r"\[source[:\s]+[^\]]+\]|\bsource\s*\d+\b|\bfile[:\s]+[A-Za-z0-9_.-]+\.pdf",
                context,
                flags=re.IGNORECASE,
            )
            covered = 0
            for ch in chunks:
                if _word_count(ch) >= 5 and _jaccard(md, ch) >= 0.08:
                    covered += 1
            if covered < 2:
                issues.append("multi_source_context_but_one_source_coverage")

    if issues:
        hard = any(x.startswith("thin_source_over_expanded") for x in issues)
        return {
            "key": "coverage_and_length_balance",
            "score": 0.0 if hard else 0.5,
            "comment": "; ".join(issues),
        }

    return {
        "key": "coverage_and_length_balance",
        "score": 1.0,
        "comment": f"coverage/length checks passed ({wc} words)",
    }


# ---------------------------------------------------------------------------
# Summary evaluator
# ---------------------------------------------------------------------------

def studio_mind_map_severity_summary(runs: list, examples: list) -> dict:
    """
    BLOCK:
    - invalid schema
    - no-source hallucination
    - code fences / internal format leakage
    - flat map / no hierarchy
    - placeholder nodes
    - unsupported numeric/formula facts
    - too many unsupported facts

    REVIEW:
    - weak relationship quality
    - custom depth/branch/focus miss
    - possible grounding weakness
    - coverage/length imbalance
    """
    if len(runs) != len(examples):
        return {
            "key": "studio_mind_map_severity_summary",
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

        structure = markdown_mindmap_structure(run, example)
        relation = hierarchy_and_relationship_quality(run, example)
        custom = custom_instruction_compliance(run, example)
        ground = grounding(run, example)
        coverage = coverage_and_length_balance(run, example)

        for result in (structure, ground):
            if result.get("hard_rule_violated"):
                tier_0.append({
                    "example_id": getattr(example, "id", None),
                    "reason": f"{result['key']} hard failure: {result['comment']}",
                })

        if custom["score"] == 0.0 and any(x in custom["comment"] for x in ["requested_depth", "requested_branches", "focus_terms", "hindi_requested"]):
            tier_0.append({
                "example_id": getattr(example, "id", None),
                "reason": f"custom instruction hard failure: {custom['comment']}",
            })

        tier_1_applicable += 5
        if structure["score"] < 1.0:
            tier_1 += 1
        if relation["score"] < 1.0:
            tier_1 += 1
        if custom["score"] < 1.0:
            tier_1 += 1
        if ground["score"] < 1.0:
            tier_1 += 1
        if coverage["score"] < 1.0:
            tier_1 += 1

        if (
            structure["score"] == 1.0
            and relation["score"] == 1.0
            and custom["score"] == 1.0
            and ground["score"] == 1.0
            and coverage["score"] == 1.0
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
        "key": "studio_mind_map_severity_summary",
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
    markdown_mindmap_structure,
    hierarchy_and_relationship_quality,
    custom_instruction_compliance,
    grounding,
    coverage_and_length_balance,
]

SUMMARY_EVALUATORS = [
    studio_mind_map_severity_summary,
]
