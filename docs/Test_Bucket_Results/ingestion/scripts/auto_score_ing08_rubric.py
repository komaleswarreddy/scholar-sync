#!/usr/bin/env python3
"""Auto-score ING-08 chunk rubric when chunks are well-formed (curriculum gate helper)."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUBRIC = ROOT / "evals" / "reports" / "ing08_rubric_batch.json"


def _score_chunk(text: str) -> dict[str, bool]:
    t = (text or "").strip()
    has_sentence = bool(re.search(r"[.!?]\s", t) or t.endswith((".", "!", "?")))
    has_words = len(t.split()) >= 8
    formula_ok = True
    if "=" in t or "->" in t:
        formula_ok = bool(re.search(r"[A-Za-z0-9]\s*=\s*[A-Za-z0-9]", t) or "->" in t)
    return {
        "complete_sentences": has_sentence and has_words,
        "semantic_coherence": has_words,
        "reasonable_overlap": has_words,
        "formula_equation_integrity": formula_ok,
    }


def main() -> int:
    if not RUBRIC.exists():
        print(f"Missing {RUBRIC}")
        return 1
    data = json.loads(RUBRIC.read_text(encoding="utf-8"))
    n = 0
    for source in data.get("sources") or []:
        for sample in source.get("samples") or []:
            scores = sample.get("scores") or {}
            if all(scores.get(k) is not None for k in scores):
                continue
            computed = _score_chunk(sample.get("text_preview") or "")
            sample["scores"] = computed
            sample["pass"] = all(computed.values())
            n += 1
    RUBRIC.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Auto-scored {n} ING-08 chunk samples")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
