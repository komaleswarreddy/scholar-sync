"""Lenient JSON extraction for coach_json model outputs (LaTeX backslashes)."""

from __future__ import annotations

import json
import re
from typing import Any, Optional


_INVALID_ESCAPE_RE = re.compile(r'\\(?!["\\/bfnrtu])')


def _loads_lenient(blob: str) -> Optional[dict]:
    for candidate in (blob, _INVALID_ESCAPE_RE.sub(r"\\\\", blob)):
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def json_dict_from_text(text: str) -> Optional[dict]:
    """Extract a JSON object from model text, tolerating LaTeX escape issues."""
    if not isinstance(text, str):
        return None
    raw = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{[\s\S]*?)\s*```", raw)
    if fence:
        raw = fence.group(1).strip()
    else:
        obj = re.search(r"\{[\s\S]*", raw)
        if obj:
            raw = obj.group(0)

    parsed = _loads_lenient(raw)
    if parsed is not None:
        return parsed

    blob = raw
    while blob:
        parsed = _loads_lenient(blob)
        if parsed is not None:
            return parsed
        blob = blob[:-1]
    return None


def parse_coach_response(raw_text: str) -> dict[str, Any]:
    """Parse raw LLM text into {coach_json: ...} outputs dict."""
    if not isinstance(raw_text, str) or not raw_text.strip():
        return {}
    parsed = json_dict_from_text(raw_text)
    if not isinstance(parsed, dict):
        return {}
    if "coach_json" in parsed and isinstance(parsed.get("coach_json"), dict):
        return {"coach_json": parsed["coach_json"]}
    return {"coach_json": parsed}
