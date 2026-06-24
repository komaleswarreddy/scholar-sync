#!/usr/bin/env python3
"""Patch Agent 14 section in Complete_Agent_DataSet.md without touching Agents 17-22."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "Reference dataset" / "Complete_Agent_DataSet.md"
FRAGMENT = ROOT / "scripts" / "agent14_studio_slide_deck.md"

START = "## 14. Studio Slide Deck Generator"
END = "## 15. Studio Fallback Task Prompt (Legacy)"


def main() -> int:
    if not FRAGMENT.exists():
        raise SystemExit(f"Missing {FRAGMENT}. Run generate_agents_8_16_fragments.py first.")
    text = MD.read_text(encoding="utf-8")
    start = text.find(START)
    end = text.find(END)
    if start < 0 or end < 0:
        raise SystemExit("Could not find Agent 14/15 section markers in Complete_Agent_DataSet.md")
    fragment = FRAGMENT.read_text(encoding="utf-8").strip()
    combined = text[:start] + fragment + "\n\n" + text[end:]
    MD.write_text(combined, encoding="utf-8")
    print(f"Patched Agent 14 in {MD}")
    print(f"Total lines: {len(combined.splitlines())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
