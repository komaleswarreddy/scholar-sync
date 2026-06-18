"""Infer NCERT subject from problem text (content-first, scope-aware)."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

# NCERT catalog keys used in Pinecone filters.
SCIENCE_BRANCH_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "physics": (
        "accelerat",
        "velocity",
        "speed",
        "motion",
        "km/h",
        "m/s",
        "newton",
        "force",
        "friction",
        "gravity",
        "displacement",
        "uniform",
        "kinematic",
        "projectile",
        "momentum",
        "circuit",
        "volt",
        "ampere",
        "ohm",
        "resistance",
        "lens",
        "mirror",
        "refraction",
        "reflection",
        "wave",
        "sound",
        "light",
        "thunder",
        "lightning",
        "rest to",
        "distance covered",
        "car ",
        "train ",
        "ball ",
    ),
    "chemistry": (
        "mole",
        "acid",
        "base",
        "react",
        "balance the",
        "chemical equation",
        "compound",
        "element",
        "periodic",
        "oxidation",
        "reduction",
        "avogadro",
        "valency",
        "ionic",
        "covalent",
        "ph ",
        "salt",
    ),
    "biology": (
        "cell",
        "organism",
        "photosynthesis",
        "ecosystem",
        "respiration",
        "chromosome",
        "gene",
        "tissue",
        "species",
        "digestion",
        "heart",
        "blood",
    ),
}

MATH_KEYWORDS: Tuple[str, ...] = (
    "quadratic",
    "polynomial",
    "x²",
    "x^2",
    "integrate",
    "derivative",
    "differentiat",
    "triangle",
    "circle",
    "probability",
    "statistics",
    "mean",
    "median",
    "factor",
    "theorem",
    "geometry",
    "algebra",
    "arithmetic progression",
    "ap ",
    "gp ",
    "sin ",
    "cos ",
    "tan ",
    "trigonometr",
    "coordinate",
    "roots of",
    "find x",
    "solve for x",
)

SOCIAL_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "history": ("dynasty", "empire", "revolt", "independence", "colonial", "mughal", "british"),
    "geography": ("latitude", "longitude", "climate", "soil", "plateau", "monsoon", "river"),
    "civics-polity": ("democracy", "constitution", "parliament", "fundamental rights", "election"),
    "economics": ("gdp", "inflation", "demand", "supply", "budget", "tax", "scarcity"),
}

DISPLAY_BY_KEY = {
    "mathematics": "Mathematics",
    "science": "Science",
    "history": "History",
    "geography": "Geography",
    "civics-polity": "Civics",
    "economics": "Economics",
}

DISPLAY_BY_SCIENCE_BRANCH = {
    "physics": "Physics",
    "chemistry": "Chemistry",
    "biology": "Biology",
}


def _count_hits(text: str, keywords: Tuple[str, ...]) -> int:
    lowered = text.lower()
    return sum(1 for kw in keywords if kw in lowered)


def infer_problem_subject(
    problem_text: str,
    allowed_subject_keys: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Content-first subject inference.

    Returns subject_key (NCERT catalog), subject (UI display), science_branch, score, confidence.
    """
    allowed = [str(k).strip().lower() for k in (allowed_subject_keys or []) if str(k).strip()]
    text = (problem_text or "").strip()
    if not text:
        return {
            "subject_key": allowed[0] if allowed else "science",
            "subject": DISPLAY_BY_KEY.get(allowed[0], "Science") if allowed else "Science",
            "science_branch": None,
            "score": 0,
            "confidence": "low",
        }

    scores: Dict[str, int] = {}

    math_score = _count_hits(text, MATH_KEYWORDS)
    if math_score:
        scores["mathematics"] = math_score

    for branch, keywords in SCIENCE_BRANCH_KEYWORDS.items():
        hit = _count_hits(text, keywords)
        if hit:
            scores[f"science:{branch}"] = hit

    for key, keywords in SOCIAL_KEYWORDS.items():
        hit = _count_hits(text, keywords)
        if hit:
            scores[key] = hit

    # Prefer science branches over bare science bucket.
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best_key, best_score = ranked[0] if ranked else ("", 0)
    second_score = ranked[1][1] if len(ranked) > 1 else 0

    subject_key: str
    science_branch: Optional[str] = None
    if best_key.startswith("science:"):
        science_branch = best_key.split(":", 1)[1]
        subject_key = "science"
    elif best_key:
        subject_key = best_key
    elif allowed:
        subject_key = allowed[0]
    else:
        subject_key = "science"

    # Respect notebook scope when inference is weak or tied.
    if allowed and subject_key not in allowed:
        if "science" in allowed and subject_key == "science":
            pass
        elif best_score <= second_score + 1:
            subject_key = allowed[0]
            science_branch = None
        else:
            # Strong content signal outside scope — keep inferred key for DNA/RAG accuracy.
            pass

    if subject_key == "science" and not science_branch:
        branch_scores = {
            branch: _count_hits(text, kws) for branch, kws in SCIENCE_BRANCH_KEYWORDS.items()
        }
        science_branch = max(branch_scores, key=branch_scores.get) if any(branch_scores.values()) else "physics"

    if subject_key == "science" and science_branch:
        subject_display = DISPLAY_BY_SCIENCE_BRANCH.get(science_branch, "Science")
    else:
        subject_display = DISPLAY_BY_KEY.get(subject_key, subject_key.replace("-", " ").title())

    confidence = "low"
    if best_score >= 3 and best_score >= second_score + 2:
        confidence = "high"
    elif best_score >= 2 and best_score > second_score:
        confidence = "medium"

    return {
        "subject_key": subject_key,
        "subject": subject_display,
        "science_branch": science_branch,
        "score": best_score,
        "confidence": confidence,
    }


def normalize_dna_subject(
    dna: Dict[str, Any],
    problem_text: str,
    scope: Dict[str, Any],
) -> Dict[str, Any]:
    """Align LLM DNA subject with content-first inference when the model drifts."""
    allowed = list(scope.get("subject_keys") or [])
    inference = infer_problem_subject(problem_text, allowed)
    out = dict(dna or {})

    llm_subject = str(out.get("subject") or "").strip().lower()
    inferred_display = inference["subject"]
    inferred_key = inference["subject_key"]

    math_like_llm = llm_subject in {"mathematics", "math", "maths"}
    science_like_inferred = inferred_key == "science" or inferred_display in {
        "Physics",
        "Chemistry",
        "Biology",
    }

    should_override = (
        inference["confidence"] in {"high", "medium"}
        and (
            (math_like_llm and science_like_inferred)
            or (inferred_key == "mathematics" and not math_like_llm and inference["confidence"] == "high")
        )
    )

    if should_override or not llm_subject:
        out["subject"] = inferred_display
        out["subject_key"] = inferred_key
        if inference.get("science_branch"):
            out["science_branch"] = inference["science_branch"]
    else:
        out.setdefault("subject_key", inferred_key)

    return out
