#!/usr/bin/env python3
"""Splice rebalanced Query Rewriter, Decomposer, and Scope Narrower sections."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "Reference dataset" / "ScholarSync_Intent_Classifier_Refined (1).md"
PARTS = ROOT / "scripts" / "rebalance_sections"


def replace_between(text: str, start: str, end: str, body: str) -> str:
    i = text.index(start)
    j = text.index(end, i)
    return text[:i] + body + text[j:]


def main() -> None:
    text = MD.read_text(encoding="utf-8")
    rewriter = (PARTS / "query_rewriter.md").read_text(encoding="utf-8")
    decomposer = (PARTS / "query_decomposer.md").read_text(encoding="utf-8")
    narrower = (PARTS / "scope_narrower.md").read_text(encoding="utf-8")

    text = replace_between(
        text,
        "### Evaluation examples (56)\n",
        "\n---\n\n---\n\n## 3. Query Decomposer Agent (Refined)",
        "### Evaluation examples (56)\n\n" + rewriter + "\n---\n\n---\n\n## 3. Query Decomposer Agent (Refined)",
    )
    text = replace_between(
        text,
        "### Evaluation examples (48)\n",
        "\n\n\n\n## 4. Scope Narrower Agent (Refined)",
        "### Evaluation examples (48)\n\n" + decomposer + "\n\n\n\n## 4. Scope Narrower Agent (Refined)",
    )
    text = replace_between(
        text,
        "### Evaluation examples (25)\n",
        "\n---\n",
        "### Evaluation examples (25)\n\n" + narrower + "\n---\n",
    )
    MD.write_text(text, encoding="utf-8")
    verify(MD.read_text(encoding="utf-8"))


def verify(text: str) -> None:
    queries = re.findall(r"\*\*Query:\*\*\s*\n(.+?)(?=\n\n|\n\*\*)", text, re.S)
    norms = [re.sub(r"\s+", " ", q.strip().lower()) for q in queries]
    dups = {q for q in norms if norms.count(q) > 1}
    pdfs = [
        "kebo106", "kebo107", "kebo110", "lebo105",
        "kech104", "kech106", "kech203", "lech103", "lech104", "lech105", "lech203",
        "kemh105", "kemh107", "kemh111", "lemh205", "lemh207",
        "keph105", "keph106", "leph103", "leph201",
    ]
    missing = [p for p in pdfs if f"source_pdf_{p}" not in text]
    for agent, count in [
        ("intent_classifier", text.count("intent_classifier-")),
        ("query_rewriter", text.count("query_rewriter-")),
        ("query_decomposer", text.count("query_decomposer-")),
        ("scope_narrower", text.count("scope_narrower-")),
    ]:
        print(f"{agent}: {count}")
    print("duplicate queries:", len(dups))
    if dups:
        for d in sorted(dups)[:5]:
            print("  dup:", d[:80])
    print("missing source_pdf tags:", missing)


if __name__ == "__main__":
    main()
