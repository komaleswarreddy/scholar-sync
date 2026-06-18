"""
Studio output structure validators (STU-06..08, schema layer).

Separate from content-correctness (STU-01/02/04/05) which requires human review.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ValidationResult:
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    tag: str = "structure-error"

    def assert_valid(self, *, prefix: str = "") -> None:
        if not self.valid:
            msg = "; ".join(self.errors) or "validation failed"
            raise AssertionError(f"{prefix}[structure-error] {msg}".strip())


def validate_quiz_schema(data: Any) -> ValidationResult:
    errors: List[str] = []
    if not isinstance(data, dict):
        return ValidationResult(False, errors=["quiz data must be a dict"])
    questions = data.get("questions")
    if not isinstance(questions, list) or len(questions) < 1:
        errors.append("quiz must have at least one question")
    else:
        for i, q in enumerate(questions):
            if not isinstance(q, dict):
                errors.append(f"question[{i}] must be a dict")
                continue
            if not str(q.get("question") or "").strip():
                errors.append(f"question[{i}] missing question text")
            options = q.get("options")
            if not isinstance(options, list) or len(options) < 2:
                errors.append(f"question[{i}] must have at least 2 options")
            elif len(options) > 4:
                errors.append(f"question[{i}] has more than 4 options")
            correct = str(q.get("correct_answer") or "").strip()
            if not correct:
                errors.append(f"question[{i}] missing correct_answer")
            elif isinstance(options, list) and correct not in options:
                errors.append(f"question[{i}] correct_answer not in options")
    return ValidationResult(len(errors) == 0, errors=errors)


def validate_flashcards_schema(data: Any) -> ValidationResult:
    errors: List[str] = []
    cards: List[Any]
    if isinstance(data, list):
        cards = data
    elif isinstance(data, dict):
        cards = data.get("cards") or data.get("flashcards") or []
        if not isinstance(cards, list):
            cards = []
    else:
        return ValidationResult(False, errors=["flashcards data must be list or dict"])

    if len(cards) < 1:
        errors.append("flashcards must have at least one card")
    for i, card in enumerate(cards):
        if not isinstance(card, dict):
            errors.append(f"card[{i}] must be a dict")
            continue
        front = str(card.get("front") or "").strip()
        back = str(card.get("back") or "").strip()
        if not front:
            errors.append(f"card[{i}] missing front")
        if not back:
            errors.append(f"card[{i}] missing back")
        if front and back and front.lower() == back.lower():
            errors.append(f"card[{i}] front and back are identical (possible swap)")
    return ValidationResult(len(errors) == 0, errors=errors)


def _extract_markdown_headings(content: str) -> List[str]:
    headings: List[str] = []
    for line in (content or "").splitlines():
        m = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
        if m:
            headings.append(m.group(2).strip().lower())
    return headings


def validate_mind_map_structure(content: str, *, min_nodes: int = 2) -> ValidationResult:
    errors: List[str] = []
    warnings: List[str] = []
    text = (content or "").strip()
    if not text:
        return ValidationResult(False, errors=["mind map content is empty"])

    headings = _extract_markdown_headings(text)
    bullet_lines = [ln for ln in text.splitlines() if ln.strip().startswith(("-", "*", "•"))]
    list_items = len(bullet_lines)
    node_count = max(len(headings), list_items, 1)

    if node_count < min_nodes and list_items < min_nodes:
        errors.append(f"mind map has fewer than {min_nodes} structural nodes")

    if headings:
        seen = set()
        for h in headings:
            if h in seen:
                errors.append(f"duplicate heading node: {h}")
            seen.add(h)

    if not headings and list_items < 1:
        warnings.append("no markdown headings or bullet nodes detected")

    return ValidationResult(len(errors) == 0, errors=errors, warnings=warnings)


def validate_report(content: str, *, require_heading: bool = True) -> ValidationResult:
    errors: List[str] = []
    warnings: List[str] = []
    text = (content or "").strip()
    if not text:
        return ValidationResult(False, errors=["report content is empty"])
    if len(text) < 100:
        warnings.append("report content is very short")
    if require_heading and not re.search(r"^#{1,3}\s+\S", text, re.MULTILINE):
        errors.append("report must contain at least one markdown heading")
    has_citation = bool(
        re.search(r"\[\[source:|\[source:|citation|according to the (source|document|chapter)", text, re.I)
    )
    if not has_citation:
        warnings.append("no source attribution markers detected in report")
    return ValidationResult(len(errors) == 0, errors=errors, warnings=warnings)


def _split_slides(content: str) -> List[Dict[str, Any]]:
    text = (content or "").strip()
    if not text:
        return []
    if "---" in text:
        raw_slides = re.split(r"\n---+\n", text)
    else:
        raw_slides = re.split(r"(?=^##\s+)", text, flags=re.MULTILINE)
    slides: List[Dict[str, Any]] = []
    for chunk in raw_slides:
        chunk = chunk.strip()
        if not chunk:
            continue
        lines = chunk.splitlines()
        title = ""
        body_lines: List[str] = []
        for line in lines:
            if line.startswith("#"):
                if not title:
                    title = re.sub(r"^#+\s*", "", line).strip()
                else:
                    body_lines.append(line)
            else:
                body_lines.append(line)
        slides.append({"title": title, "body": "\n".join(body_lines).strip()})
    return slides


def validate_slide_deck(content: str) -> ValidationResult:
    errors: List[str] = []
    slides = _split_slides(content)
    if not slides:
        return ValidationResult(False, errors=["slide deck has no slides"])
    for i, slide in enumerate(slides):
        if not slide.get("title"):
            errors.append(f"slide[{i}] missing title")
        body = slide.get("body") or ""
        if not body.strip():
            errors.append(f"slide[{i}] missing content block")
    return ValidationResult(len(errors) == 0, errors=errors)


def validate_infographic_data(data: Any) -> ValidationResult:
    errors: List[str] = []
    if not isinstance(data, dict):
        return ValidationResult(False, errors=["infographic_data must be a dict"])
    if not str(data.get("title") or "").strip():
        errors.append("infographic missing title")
    sections = data.get("sections")
    if not isinstance(sections, list) or len(sections) < 1:
        errors.append("infographic must have at least one section")
    return ValidationResult(len(errors) == 0, errors=errors)


def validate_studio_output(payload: Dict[str, Any]) -> ValidationResult:
    """Dispatch validator by task_type in a generate() response payload."""
    task_type = payload.get("task_type")
    if task_type == "quiz":
        return validate_quiz_schema(payload.get("data"))
    if task_type == "flashcards":
        return validate_flashcards_schema(payload.get("data"))
    if task_type == "mind_map":
        return validate_mind_map_structure(payload.get("content") or "")
    if task_type == "report":
        return validate_report(payload.get("content") or "")
    if task_type == "slide_deck":
        return validate_slide_deck(payload.get("content") or "")
    if task_type == "infographic":
        return validate_infographic_data(payload.get("infographic_data"))
    return ValidationResult(True, warnings=[f"no validator for task_type={task_type}"])
