"""Lenient JSON extraction for coach_json model outputs (LaTeX backslashes)."""

from __future__ import annotations

import json
import re
from typing import Any, Optional


_INVALID_ESCAPE_RE = re.compile(r'\\(?!["\\/bfnrtu])')


def _extract_json_blob(text: str) -> str:
    raw = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{[\s\S]*)", raw, re.IGNORECASE)
    if fence:
        blob = fence.group(1)
        if "```" in blob:
            blob = blob.split("```", 1)[0]
        return blob.strip()
    obj = re.search(r"\{[\s\S]*", raw)
    return obj.group(0).strip() if obj else raw


def _escape_inner_quotes_in_json_strings(blob: str) -> str:
    """Escape double-quotes inside JSON string values (common in markdown coach_json)."""
    out: list[str] = []
    in_string = False
    escape = False
    for i, ch in enumerate(blob):
        if not in_string:
            out.append(ch)
            if ch == '"':
                in_string = True
            continue
        if escape:
            out.append(ch)
            escape = False
            continue
        if ch == "\\":
            out.append(ch)
            escape = True
            continue
        if ch == '"':
            j = i + 1
            while j < len(blob) and blob[j] in " \t\r\n":
                j += 1
            if j < len(blob) and blob[j] in ",:}]":
                out.append(ch)
                in_string = False
            else:
                out.append('\\"')
            continue
        out.append(ch)
    return "".join(out)


def _loads_lenient(blob: str) -> Optional[dict]:
    candidates = (
        blob,
        _escape_inner_quotes_in_json_strings(blob),
        _INVALID_ESCAPE_RE.sub(r"\\\\", blob),
        _INVALID_ESCAPE_RE.sub(
            r"\\\\", _escape_inner_quotes_in_json_strings(blob)
        ),
    )
    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
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
    raw = _extract_json_blob(text)

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
