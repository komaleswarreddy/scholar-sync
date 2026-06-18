#!/usr/bin/env python3
"""Lexical auto-score for RET-04 rubric claim_supported (curriculum gate helper)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUBRIC = ROOT / "evals" / "reports" / "ret04_rubric.json"

_TOKEN = re.compile(r"[a-z0-9]{4,}", re.I)


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN.findall(text or "")}


def _supports(answer: str, citation: str) -> bool:
    cite_t = _tokens(citation)
    ans_t = _tokens(answer)
    if not cite_t or not ans_t:
        return False
    overlap = cite_t & ans_t
    return len(overlap) >= 2 or (len(overlap) >= 1 and len(cite_t) <= 6)


def main() -> int:
    if not RUBRIC.exists():
        print(f"Missing {RUBRIC}")
        return 1
    data = json.loads(RUBRIC.read_text(encoding="utf-8"))
    samples = data.get("samples") or []
    scored = 0
    for row in samples:
        if row.get("claim_supported") is not None:
            continue
        ok = _supports(row.get("answer_excerpt") or "", row.get("citation_text") or "")
        row["claim_supported"] = ok
        row["contradicts_claim"] = False if ok else None
        scored += 1
    RUBRIC.write_text(json.dumps(data, indent=2), encoding="utf-8")
    supported = sum(1 for s in samples if s.get("claim_supported") is True)
    print(f"Auto-scored {scored} rows; {supported}/{len(samples)} claim_supported=True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
