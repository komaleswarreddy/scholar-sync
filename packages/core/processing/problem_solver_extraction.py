"""Problem-solver text extraction helpers (corruption detect, diagram merge)."""

from __future__ import annotations

import re

CORRUPTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("empty_parens", re.compile(r"\(\s+and\s+\)|\(\s+\)", re.I)),
    ("missing_masses", re.compile(r"masses\s+kg\s+and\s+kg", re.I)),
    ("missing_g", re.compile(r"take\s+m/s\s*\)", re.I)),
    ("bare_mcq", re.compile(r"\(1\)\s*\(2\)\s*\(3\)\s*\(4\)\s*$")),
    ("missing_mu", re.compile(r"coefficient\s+friction\s+\.", re.I)),
    ("missing_accel", re.compile(r"acceleration\s+of\s*,", re.I)),
    ("block_no_label", re.compile(r"block\s+is\s+positioned|block\s+and\s+remain", re.I)),
]

FIGURE_HINTS = re.compile(
    r"figure below|shown in (?:the )?figure|as shown in|picture below|graph below|"
    r"in the following figure|refer to (?:the )?figure|see (?:the )?figure|"
    r"in the diagram below|shown in (?:the )?diagram|given (?:in )?the figure|"
    r"from the figure|observe (?:the )?figure",
    re.I,
)

SPATIAL_SETUP_RE = re.compile(
    r"semi-?circular|bead\s+[A-Z]|sliding on|parallel plate capacitor|"
    r"ray diagram|conducting loop|equilateral triangle|coordinate graph|"
    r"food pyramid|replica plating|prism of angle|shown in figure|"
    r"cut out from the disc|wire loop|optical bench|"
    r"lens|mirror|pulley|inclined plane|massless thread|"
    r"string\s*\([A-Z]|horizontal string|vertical string|"
    r"bar graph|plasmid|benzene ring|capacitor with|"
    r"disc of mass|uniform circular disc",
    re.I,
)

# Vision model often describes text-only pages as "diagrams" — reject these.
TEXT_ONLY_DIAGRAM_RE = re.compile(
    r"purely textual|no diagrams? or figures?|does not include any diagrams?|"
    r"does not contain any (visible )?diagrams?|no visible diagrams?|"
    r"no visual components|purely algebraic without graphical|solely textual|"
    r"content is purely textual|image shows a text block|the text presents|"
    r"text-based question|text presents a (problem|question|chemistry question)|"
    r"there are no visible components|i'm unable to assist|unable to assist|"
    r"focus is solely on the .{0,40}(inquiry|question)",
    re.I,
)

VISUAL_DIAGRAM_RE = re.compile(
    r"diagram (depicts|illustrates|features|shows|consists|presents)|figure[- ]?\d|graph titled|"
    r"bar graph|coordinate graph|food pyramid|pulley|benzene ring|plasmid|"
    r"blocks? labeled|cube labeled|equilateral triangle|capacitor|"
    r"overlapping ovals|thread connects|spatial layout|wireframe|"
    r"labeled components|replica plating|ray diagram|circuit|"
    r"semi-?circular|bead[s]?|horizontal (line|string|segment)|vertical (line|string|segment)|"
    r"arc|angle of|potentiometer|plates? of|mica sheet|arrow|"
    r"illustration depicts|the figure is",
    re.I,
)

DIAGRAM_BLOCK_RE = re.compile(r"\[Diagram:\s*([^\]]*)\]", re.I)
NO_DIAGRAM_MARKERS = frozenset({"no_diagram", "no diagram", "no figure", "text only"})

# MCQ option tails — require ≥2 consecutive markers to avoid stripping sub-parts like (i).
_MCQ_JEE_MULTILINE = re.compile(
    r"(\n\s*[1-4][\.\)]\s+.+"
    r"(?:\n\s*[2-4][\.\)]\s+.+){1,3}"
    r"\s*)$",
    re.DOTALL,
)
_MCQ_JEE_INLINE = re.compile(
    r"(\s[1-4][\.\)]\s+.+"
    r"(?:\s[2-4][\.\)]\s+.+){1,3}"
    r")\s*$",
    re.DOTALL,
)
_MCQ_PAREN_INLINE = re.compile(
    r"(\([1-4]\)\s+.+"
    r"(?:\s+\([2-4]\)\s+.+){1,3}"
    r")\s*$",
    re.DOTALL,
)
_MCQ_ALPHA_MULTILINE = re.compile(
    r"(\n\s*[A-D][\.\)]\s+.+"
    r"(?:\n\s*[B-D][\.\)]\s+.+){1,3}"
    r"\s*)$",
    re.DOTALL | re.IGNORECASE,
)
_DIAGRAM_OPTION_LEAK = re.compile(
    r"(?:labels?\s+\(1\).*?\(4\).*?(?:with )?values?\s*:\s*)|"
    r"(?:\([1-4]\)\s*[^,\.\]]+(?:\s*,\s*|\s+and\s+)(?:\([2-4]\)\s*[^,\.\]]+){1,3})",
    re.I | re.DOTALL,
)


def detect_corruption(text: str) -> list[str]:
    flags: list[str] = []
    for name, pat in CORRUPTION_PATTERNS:
        if pat.search(text or ""):
            flags.append(name)
    if re.search(r"cube\s*\(\s*\)", text or "", re.I):
        flags.append("empty_cube_label")
    if re.search(r"blocks\s*\(\s+and\s+\)", text or "", re.I):
        flags.append("missing_block_labels")
    return list(dict.fromkeys(flags))


def needs_vision_retry(text: str, has_image: bool) -> bool:
    if has_image:
        return True
    return bool(detect_corruption(text))


def strip_diagram_blocks(text: str) -> str:
    """Remove all [Diagram: ...] blocks from problem text."""
    stem = DIAGRAM_BLOCK_RE.sub("", text or "")
    stem = re.sub(r"\n{3,}", "\n\n", stem)
    stem = re.sub(r"\n*;\s*;\s*$", "", stem).strip()
    return stem.strip()


def question_references_diagram(text: str, has_image: bool = False) -> bool:
    """True when the problem stem explicitly refers to a figure/diagram."""
    stem = strip_diagram_blocks(text or "")
    return bool(FIGURE_HINTS.search(stem))


def problem_likely_needs_diagram(text: str) -> bool:
    """True when the stem describes a spatial/geometric setup needing a figure."""
    stem = strip_diagram_blocks(text or "")
    if question_references_diagram(stem):
        return True
    return bool(SPATIAL_SETUP_RE.search(stem))


def _diagram_inner(desc: str) -> str:
    inner = (desc or "").strip()
    if inner.lower().startswith("[diagram:"):
        match = DIAGRAM_BLOCK_RE.search(inner)
        inner = match.group(1).strip() if match else inner[10:].rstrip("]").strip()
    return " ".join(inner.split()).strip()


def is_meaningful_diagram_description(desc: str) -> bool:
    """Return True only when a vision/OCR snippet describes a real figure."""
    inner = _diagram_inner(desc)
    if not inner or inner.lower() in NO_DIAGRAM_MARKERS:
        return False
    if len(inner) < 20:
        return False
    if TEXT_ONLY_DIAGRAM_RE.search(inner):
        return False
    if VISUAL_DIAGRAM_RE.search(inner):
        return True
    spatial_words = ("top", "bottom", "left", "right", "vertical", "horizontal", "connected")
    if sum(1 for w in spatial_words if w in inner.lower()) >= 2:
        return True
    return False


def split_diagram_blocks(desc: str) -> list[str]:
    """Split combined page-level diagram text into individual descriptions."""
    if not (desc or "").strip():
        return []
    raw = desc.strip()
    blocks = [_diagram_inner(block) for block in DIAGRAM_BLOCK_RE.findall(raw)]
    if not blocks:
        inner = _diagram_inner(raw)
        return [inner] if inner and is_meaningful_diagram_description(inner) else []
    return [block for block in blocks if block and is_meaningful_diagram_description(block)]


def _extract_label_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    stem = strip_diagram_blocks(text or "")
    for match in re.finditer(r"\b(?:point|bead|block)\s+([A-Z])\b", stem, re.I):
        tokens.add(match.group(1).upper())
    for match in re.finditer(r"\(([A-Z](?:\s+[A-Z])*)\)", stem):
        for letter in match.group(1).split():
            if len(letter) == 1 and letter.isalpha():
                tokens.add(letter.upper())
    for match in re.finditer(r"\bbead\s+([PQRSABCK])\b", stem, re.I):
        tokens.add(match.group(1).upper())
    return tokens


def _topic_keywords(text: str) -> set[str]:
    lower = strip_diagram_blocks(text or "").lower()
    keywords = {
        "semi-circular",
        "semicircular",
        "bead",
        "potentiometer",
        "capacitor",
        "triangle",
        "prism",
        "lens",
        "pulley",
        "equilibrium",
        "plasmid",
        "pyramid",
        "graph",
        "benzene",
        "disc",
        "solenoid",
        "bubble",
        "swimming pool",
    }
    return {kw for kw in keywords if kw.replace("-", "") in lower.replace("-", "")}


def _diagram_mismatch_penalty(problem_text: str, block: str) -> int:
    stem = strip_diagram_blocks(problem_text).lower()
    block_lower = block.lower()
    penalty = 0
    if "bead" in stem and "bead" not in block_lower:
        penalty += 12
    if ("semi-circular" in stem or "semicircular" in stem) and "semi" not in block_lower:
        penalty += 12
    if "potentiometer" in stem and "potentiometer" not in block_lower:
        penalty += 12
    if "capacitor" in stem and "capacitor" not in block_lower:
        penalty += 12
    if "equilateral triangle" in stem and "triangle" not in block_lower:
        penalty += 10
    if "prism" in stem and "prism" not in block_lower:
        penalty += 10
    if "bead" in stem and "block labeled" in block_lower:
        penalty += 8
  # Optics vs circuit bleed
    if any(w in stem for w in ("lens", "spherical interface", "refractive", "magnification")) and any(
        w in block_lower for w in ("circuit", "led", "diode", "resistor", "power supply")
    ):
        penalty += 15
    # Biology graph topic mismatches
    if any(w in stem for w in ("species richness", "bar graph", "mammal", "region i")) and any(
        w in block_lower for w in ("nicotine", "smoking", "cigarette")
    ):
        penalty += 15
    if any(w in stem for w in ("nicotine", "smoking", "cigarette", "puff")) and any(
        w in block_lower for w in ("barnacle", "intertidal", "chthamalus", "balanus")
    ):
        penalty += 15
    if any(w in stem for w in ("barnacle", "intertidal", "distribution")) and any(
        w in block_lower for w in ("nicotine", "smoking")
    ):
        penalty += 15
    # Venn vs unrelated shapes
    if any(w in stem for w in ("venn", "overlapping oval", "sets a, b and c")) and any(
        w in block_lower for w in ("food pyramid", "linear programming", "coordinate graph")
    ):
        penalty += 15
    if "ladder" in stem or "pole" in stem:
        if "barnacle" in block_lower or "nicotine" in block_lower:
            penalty += 15
    return penalty


def is_verified_diagram_problem(problem_text: str) -> bool:
    """True when problem text has a meaningful, stem-consistent [Diagram:] block."""
    text = (problem_text or "").strip()
    if "[diagram:" not in text.lower():
        return False
    blocks = DIAGRAM_BLOCK_RE.findall(text)
    if not blocks:
        return False
    for block in blocks:
        if not is_meaningful_diagram_description(block):
            return False
        if _diagram_mismatch_penalty(text, block) >= 12:
            return False
    stem = strip_diagram_blocks(text)
    if re.search(r"based on the above information", stem, re.I) and not blocks:
        return False
    if question_references_diagram(stem) and not blocks:
        return False
    return True


def normalize_diagram_option_order(text: str) -> str:
    """Ensure stem → [Diagram] → options when all three are present."""
    body = (text or "").strip()
    if "[diagram:" not in body.lower():
        return body
    blocks = DIAGRAM_BLOCK_RE.findall(body)
    if not blocks:
        return body
    stem_only = strip_diagram_blocks(body)
    stem_part, options = extract_mcq_options(stem_only)
    if not options:
        return body
    diagram = blocks[0] if len(blocks) == 1 else "; ".join(blocks)
    return assemble_problem_text(stem_part, diagram, options)


def sanitize_problem_diagrams(problem_text: str) -> str:
    """Remove invalid [Diagram:] blocks; keep only verified attachments."""
    text = normalize_diagram_option_order((problem_text or "").strip())
    if "[diagram:" not in text.lower():
        return text
    stem = strip_diagram_blocks(text)
    blocks = DIAGRAM_BLOCK_RE.findall(text)
    kept: list[str] = []
    for block in blocks:
        candidate = f"{stem}\n\n[Diagram: {block}]"
        if is_meaningful_diagram_description(block) and _diagram_mismatch_penalty(candidate, block) < 12:
            kept.append(block)
    if not kept:
        return strip_diagram_blocks(text).strip()
    stem_part, options = extract_mcq_options(stem)
    if len(kept) == 1:
        merged = f"{stem_part.strip()}\n\n[Diagram: {kept[0]}]".strip()
    else:
        joined = "; ".join(f"[Diagram: {b}]" for b in kept)
        merged = f"{stem_part.strip()}\n\n{joined}".strip()
    if options:
        merged = f"{merged}\n\n{options.strip()}".strip()
    return merged.strip()


def pick_diagram_for_question(problem_text: str, diagram_desc: str) -> str:
    """Pick the diagram block that best matches a specific question on a shared page."""
    blocks = split_diagram_blocks(diagram_desc)
    if not blocks:
        return ""
    if len(blocks) == 1:
        block = blocks[0]
        if _diagram_mismatch_penalty(problem_text, block) >= 12:
            return ""
        return block

    labels = _extract_label_tokens(problem_text)
    topics = _topic_keywords(problem_text)
    best_block = ""
    best_score = -1
    for block in blocks:
        score = 0
        block_lower = block.lower()
        for label in labels:
            if re.search(rf"\b{re.escape(label)}\b", block, re.I):
                score += 4
        for topic in topics:
            if topic.replace("-", "") in block_lower.replace("-", ""):
                score += 6
        if is_meaningful_diagram_description(block):
            score += 1
        score -= _diagram_mismatch_penalty(problem_text, block)
        if score > best_score:
            best_score = score
            best_block = block

    if best_score > 0:
        return best_block
    return ""


def filter_diagram_description(desc: str) -> str:
    """Keep only meaningful diagram snippets; drop text-only vision noise."""
    blocks = split_diagram_blocks(desc)
    if not blocks:
        return ""
    return blocks[0] if len(blocks) == 1 else "; ".join(blocks)


def should_attach_diagram(
    problem_text: str,
    diagram_desc: str,
    *,
    page_has_images: bool = False,
) -> bool:
    """Attach [Diagram: ...] for real figures that belong to this question."""
    picked = pick_diagram_for_question(problem_text, diagram_desc)
    if not picked:
        return False
    stem = strip_diagram_blocks(problem_text or "")
    if question_references_diagram(stem):
        return True
    if problem_likely_needs_diagram(stem):
        return True
    if page_has_images and _extract_label_tokens(stem) and any(
        re.search(rf"\b{re.escape(label)}\b", picked, re.I) for label in _extract_label_tokens(stem)
    ):
        return True
    return False


def extract_mcq_options(text: str) -> tuple[str, str]:
    """Split stem and MCQ options block (preserves source numbering style)."""
    body = (text or "").strip()
    if not body:
        return "", ""

    for pattern in (_MCQ_JEE_MULTILINE, _MCQ_JEE_INLINE, _MCQ_PAREN_INLINE, _MCQ_ALPHA_MULTILINE):
        match = pattern.search(body)
        if match:
            options = match.group(1).strip()
            stem = body[: match.start()].rstrip()
            if stem and len(options) >= 8:
                return stem, options
    return body, ""


def strip_options_from_diagram(desc: str) -> tuple[str, str]:
    """Remove MCQ option text leaked into a vision diagram description."""
    inner = _diagram_inner(desc)
    if not inner:
        return "", ""

    values_match = re.search(r"with values?\s*:\s*(.+?)\s*\.?\s*$", inner, re.I)
    if values_match:
        options_raw = values_match.group(1).strip().rstrip(".")
        cleaned = inner[: values_match.start()].strip()
        cleaned = re.sub(
            r"labels?\s+\(1\)\s*,\s*\(2\)\s*,\s*\(3\)\s*,\s*and\s*\(4\)\s*are positioned[^.]*\.?",
            "",
            cleaned,
            flags=re.I,
        )
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" ,;.")
        options = re.sub(r"\s+and\s+", " ", options_raw)
        options = re.sub(r"\s*,\s*", " ", options).strip()
        if cleaned and len(cleaned) >= 20 and options:
            return cleaned, options

    leak = _DIAGRAM_OPTION_LEAK.search(inner)
    if not leak:
        return inner, ""

    leaked_text = leak.group(0).strip()
    cleaned = (inner[: leak.start()] + inner[leak.end() :]).strip()
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"\.\s*\.", ".", cleaned).strip(" ,;.")

    options = ""
    paren_opts = _MCQ_PAREN_INLINE.search(f" {leaked_text}")
    if paren_opts:
        options = paren_opts.group(1).strip()
    else:
        jee_opts = _MCQ_JEE_INLINE.search(f" {leaked_text}")
        if jee_opts:
            options = jee_opts.group(1).strip()

    if not cleaned or len(cleaned) < 20:
        return inner, options
    return cleaned, options


def assemble_problem_text(stem: str, diagram_block: str, options: str) -> str:
    """Enforce order: stem → [Diagram] → options."""
    parts: list[str] = []
    if (stem or "").strip():
        parts.append(stem.strip())
    if (diagram_block or "").strip():
        block = diagram_block.strip()
        if not block.lower().startswith("[diagram:"):
            block = f"[Diagram: {block}]"
        parts.append(block)
    if (options or "").strip():
        parts.append(options.strip())
    return "\n\n".join(parts).strip()


def finalize_problem_text(
    problem_text: str,
    diagram_desc: str,
    *,
    page_has_images: bool = False,
) -> str:
    """Stem → diagram → options; no diagram keeps inline options unchanged."""
    base = strip_diagram_blocks(problem_text or "")
    stem_part, options = extract_mcq_options(base)

    picked = pick_diagram_for_question(stem_part, diagram_desc)
    if not picked or not should_attach_diagram(stem_part, picked, page_has_images=page_has_images):
        return sanitize_problem_diagrams(base)

    picked_clean, diagram_options = strip_options_from_diagram(picked)
    if not picked_clean:
        return sanitize_problem_diagrams(base)

    final_options = options or diagram_options
    merged = assemble_problem_text(stem_part, picked_clean, final_options)
    return sanitize_problem_diagrams(merged)


def merge_problem_and_diagram(problem_text: str, diagram_desc: str, *, page_has_images: bool = False) -> str:
    return finalize_problem_text(problem_text, diagram_desc, page_has_images=page_has_images)


def clean_problem_text_diagrams(
    problem_text: str,
    diagram_desc: str = "",
    *,
    page_has_images: bool = False,
) -> str:
    """Strip bogus diagram blocks and re-attach only when appropriate."""
    stem = strip_diagram_blocks(problem_text or "")
    combined_desc = diagram_desc or " ".join(DIAGRAM_BLOCK_RE.findall(problem_text or ""))
    merged = merge_problem_and_diagram(stem, combined_desc, page_has_images=page_has_images)
    return sanitize_problem_diagrams(merged)


def reconcile_text_layers(text_layer: str, vision_text: str) -> str:
    """Pick best page text from PDF layer vs vision OCR."""
    raw = (text_layer or "").strip()
    vis = (vision_text or "").strip()
    if not vis:
        return raw
    if not raw:
        return vis
    raw_flags = detect_corruption(raw)
    vis_flags = detect_corruption(vis)
    if raw_flags and not vis_flags:
        return vis
    if vis_flags and not raw_flags:
        return raw
    if len(vis) > len(raw) * 0.65:
        return vis
    return raw if len(raw) >= len(vis) else vis


def format_diagram_block(diagram_context: str) -> str:
    """Normalize diagram OCR snippet to [Diagram: ...] block."""
    ctx = (diagram_context or "").strip()
    if not ctx:
        return ""
    if ctx.lower().startswith("diagram context:"):
        ctx = ctx.split(":", 1)[1].strip()
    if ctx.lower().startswith("[diagram:"):
        return ctx
    return f"[Diagram: {ctx}]"
