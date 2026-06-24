#!/usr/bin/env python3
"""Append Agents 5 and 6 to Complete_Agent_DataSet.md and verify dedup."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "Reference dataset" / "Complete_Agent_DataSet.md"
AGENT5 = ROOT / "scripts" / "agent5_chat_policy_block.md"
AGENT6 = ROOT / "scripts" / "agent6_direct_chat.md"


def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def extract_queries(text: str) -> set[str]:
    queries: set[str] = set()
    for m in re.finditer(r"\*\*Query:\*\*\s*(.+?)(?=\n|$)", text):
        queries.add(normalize(m.group(1)))
    for m in re.finditer(r"^Query:\s*\n(.+?)(?=\n\n|\nExpected|\n\*\*)", text, re.M | re.S):
        q = m.group(1).strip()
        if q:
            queries.add(normalize(q))
    return queries


def extract_agent56_strings(text: str) -> set[str]:
    out: set[str] = set()
    for key in ("User Request", "Draft Answer", "Message"):
        for m in re.finditer(rf"\*\*{key}:\*\*\s*(.+?)(?=\n|$)", text):
            out.add(normalize(m.group(1)))
    return out


def process_agent56(text: str, is_agent5: bool) -> str:
    """Remove Evaluators lines; drop Corrected Answer on pass cases (Agent 5 only)."""
    text = re.sub(r"\n\*\*Evaluators:\*\*[^\n]*", "", text)
    if is_agent5:

        def fix_pass_block(m: re.Match[str]) -> str:
            block = m.group(0)
            if "**Passes Policy:** True" not in block:
                return block
            return re.sub(
                r"\n\*\*Corrected Answer:\*\*[^\n]*(?:\n(?!\*\*Quality Check).*)*",
                "",
                block,
                count=1,
            )

        text = re.sub(
            r"\*\*Expected output\*\*\n\n\*\*Passes Policy:\*\*.*?(?=\n---\n|\n#### Example|\Z)",
            fix_pass_block,
            text,
            flags=re.S,
        )
    return text


def main() -> None:
    text = MD.read_text(encoding="utf-8")
    # Strip previously appended agents 5–6 if re-running
    marker = "\n## 5. Chat Policy Block (YAML)"
    if marker in text:
        text = text[: text.index(marker)].rstrip()

    agent5 = AGENT5.read_text(encoding="utf-8")
    agent6 = AGENT6.read_text(encoding="utf-8")
    agent5 = process_agent56(agent5, True)
    agent6 = process_agent56(agent6, False)
    combined = text + "\n\n" + agent5 + "\n" + agent6
    MD.write_text(combined, encoding="utf-8")

    q14 = extract_queries(text)
    q56 = extract_agent56_strings(agent5 + agent6)
    overlap = q14 & q56

    cp_count = combined.count("chat_policy_block-")
    dc_count = combined.count("direct_chat-")
    fails = len(re.findall(r"\*\*Passes Policy:\*\* False", agent5))
    passes = len(re.findall(r"\*\*Passes Policy:\*\* True", agent5))
    tbd = "TBD" in agent5 + agent6
    stub = "unchanged from baseline" in (agent5 + agent6).lower()

    print("chat_policy_block examples:", cp_count)
    print("direct_chat examples:", dc_count)
    print("policy pass/fail:", passes, "/", fails)
    print("cross-agent overlaps:", len(overlap))
    if overlap:
        for o in sorted(overlap)[:10]:
            print("  OVERLAP:", o[:80])
    print("TBD present:", tbd)
    print("stub prompt present:", stub)
    assert cp_count == 25, f"expected 25 chat_policy_block, got {cp_count}"
    assert dc_count == 25, f"expected 25 direct_chat, got {dc_count}"
    assert len(overlap) == 0, f"found {len(overlap)} overlaps with agents 1-4 queries"
    assert not tbd
    assert not stub
    print("OK")


if __name__ == "__main__":
    main()
