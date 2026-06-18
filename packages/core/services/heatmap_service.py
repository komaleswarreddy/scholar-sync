"""Notebook concept heatmap helpers."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

HeatmapCell = str
DEFAULT_HEATMAP: List[HeatmapCell] = ["empty"] * 40


def normalize_heatmap(settings: Optional[Dict[str, Any]]) -> List[HeatmapCell]:
    raw = (settings or {}).get("heatmap")
    if not isinstance(raw, list):
        return list(DEFAULT_HEATMAP)
    cells: List[HeatmapCell] = []
    allowed = {"strong", "good", "average", "weak", "empty"}
    for item in raw[:40]:
        cells.append(item if item in allowed else "empty")
    while len(cells) < 40:
        cells.append("empty")
    return cells


def score_ratio_from_quiz_content(content: Any) -> Optional[float]:
    if not isinstance(content, dict):
        return None
    data = content.get("data") if isinstance(content.get("data"), dict) else content
    if not isinstance(data, dict):
        return None
    score = data.get("score")
    total = data.get("total") or data.get("total_questions")
    if isinstance(score, (int, float)) and isinstance(total, (int, float)) and total > 0:
        return float(score) / float(total)
    correct = data.get("correct")
    questions = data.get("questions")
    if isinstance(correct, (int, float)) and isinstance(questions, list) and questions:
        return float(correct) / float(len(questions))
    return None


def level_from_ratio(ratio: float) -> HeatmapCell:
    if ratio >= 0.8:
        return "strong"
    if ratio >= 0.65:
        return "good"
    if ratio >= 0.5:
        return "average"
    return "weak"


def update_heatmap_on_quiz(settings: Optional[Dict[str, Any]], content: Any) -> Dict[str, Any]:
    merged = dict(settings or {})
    ratio = score_ratio_from_quiz_content(content)
    if ratio is None:
        return merged
    heatmap = normalize_heatmap(merged)
    level = level_from_ratio(ratio)
    for idx, cell in enumerate(heatmap):
        if cell in ("empty", "weak", "average"):
            heatmap[idx] = level
            break
    merged["heatmap"] = heatmap
    return merged
