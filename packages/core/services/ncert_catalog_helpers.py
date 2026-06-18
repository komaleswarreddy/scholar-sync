"""Shared NCERT catalog parsing and subject mapping."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

CHAPTER_FILENAME_RE = re.compile(r"^Ch(\d+)\s*-\s*(.+)\.pdf$", re.IGNORECASE)

SUBJECT_ICONS: Dict[str, str] = {
    "mathematics": "calculator",
    "science": "flask",
    "physics": "atom",
    "chemistry": "flask",
    "biology": "leaf",
    "history": "landmark",
    "geography": "globe",
    "civics-polity": "scale",
    "economics": "coins",
}


def parse_class_num(class_label: str) -> int:
    digits = re.sub(r"[^0-9]", "", class_label or "")
    if not digits:
        raise ValueError(f"Invalid class label: {class_label!r}")
    return int(digits)


def parse_chapter_from_filename(filename: str) -> Tuple[int, str]:
    name = (filename or "").strip()
    match = CHAPTER_FILENAME_RE.match(name)
    if not match:
        raise ValueError(f"Cannot parse chapter from filename: {filename!r}")
    return int(match.group(1)), match.group(2).strip()


def subject_key_from_row(subject: str, subsubject: Optional[str]) -> str:
    subj = (subject or "").strip()
    ss = (subsubject or "").strip()
    if subj == "Mathematics":
        return "mathematics"
    if subj == "Science":
        return "science"
    if subj == "Social Science":
        mapping = {
            "History": "history",
            "Geography": "geography",
            "Civics-Polity": "civics-polity",
            "Economics": "economics",
        }
        if ss in mapping:
            return mapping[ss]
        return re.sub(r"[^a-z0-9]+", "-", ss.lower()).strip("-") or "social-science"
    return re.sub(r"[^a-z0-9]+", "-", subj.lower()).strip("-") or "unknown"


def subject_slug_from_row(subject: str) -> str:
    subj = (subject or "").strip()
    if subj in ("Mathematics", "Science"):
        return subj.lower().replace(" ", "_")
    if subj == "Social Science":
        return "social_science"
    return re.sub(r"[^a-z0-9]+", "_", subj.lower()).strip("_")


def subject_display_label(subject_key: str, subsubject: Optional[str] = None) -> str:
    labels = {
        "mathematics": "Mathematics",
        "science": "Science",
        "physics": "Physics",
        "chemistry": "Chemistry",
        "biology": "Biology",
        "history": "History · Social Science",
        "geography": "Geography · Social Science",
        "civics-polity": "Civics · Social Science",
        "economics": "Economics · Social Science",
    }
    if subject_key in labels:
        return labels[subject_key]
    if subsubject:
        return f"{subsubject} · Social Science"
    return subject_key.replace("-", " ").title()


def resolve_pdf_path(csv_path: str, pdf_root: Optional[Path]) -> str:
    raw = (csv_path or "").strip()
    if not pdf_root:
        return raw
    marker = "class 12"
    idx = raw.replace("\\", "/").find(marker)
    if idx >= 0:
        rel = raw.replace("\\", "/")[idx + len(marker) + 1 :]
        return str((pdf_root / rel).resolve())
    return str((pdf_root / Path(raw).name).resolve())


def concepts_from_sketch(sketch: Optional[Dict[str, Any]]) -> list[str]:
    if not isinstance(sketch, dict):
        return []
    raw = sketch.get("concepts") or []
    out: list[str] = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str) and item.strip():
                out.append(item.strip())
            elif isinstance(item, dict):
                label = (item.get("name") or item.get("label") or item.get("title") or "").strip()
                if label:
                    out.append(label)
    return out[:30]


def topic_summary_from_sketch(sketch: Optional[Dict[str, Any]]) -> Optional[str]:
    if not isinstance(sketch, dict):
        return None
    for key in ("topic_summary", "summary", "chapter_summary", "overview"):
        val = sketch.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    title = (sketch.get("chapter_title") or "").strip()
    sections = sketch.get("main_sections") or []
    if title and isinstance(sections, list) and sections:
        parts = []
        for sec in sections[:3]:
            if isinstance(sec, str) and sec.strip():
                parts.append(sec.strip())
            elif isinstance(sec, dict):
                name = (sec.get("title") or sec.get("name") or "").strip()
                if name:
                    parts.append(name)
        if parts:
            return f"{title}: " + "; ".join(parts)
    return title or None
