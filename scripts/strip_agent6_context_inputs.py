#!/usr/bin/env python3
"""Remove chat_rolling_summary and conversation_transcript from Agent 6 dataset docs."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def strip_agent6_context_fields(text: str) -> str:
    text = re.sub(
        r"\* Input keys: `message`, `chat_rolling_summary`, `conversation_transcript`",
        "* Input keys: `message`",
        text,
    )
    text = re.sub(
        r"\n> ## Context blocks \(optional inputs\)\n(?:> .*\n)+",
        "\n",
        text,
    )
    # Remove documented user/task jinja block (summary + transcript); keep runtime note
    text = re.sub(
        r"\n\*User / task template:\*\n\n(?:> .*\n)+(?=\n\*Runtime template:\*)",
        "\n",
        text,
    )
    text = re.sub(r"\n\*\*Chat Rolling Summary:\*\*[^\n]*", "", text)
    text = re.sub(r"\n\*\*Conversation Transcript:\*\*[^\n]*", "", text)
    # Example 024 leftover transcript body (Student/Assistant lines after removed header)
    text = re.sub(
        r"(?m)^Student: How do I add my chemistry PDF\?\n\nAssistant: Use the Sources panel[^\n]*\n\n",
        "",
        text,
    )
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text


def main() -> None:
    complete = ROOT / "Reference dataset" / "Complete_Agent_DataSet.md"
    agent6 = ROOT / "scripts" / "agent6_direct_chat.md"

    raw = complete.read_text(encoding="utf-8")
    marker = "## 6. Direct Chat Agent"
    if marker in raw:
        idx = raw.index(marker)
        raw = raw[:idx] + strip_agent6_context_fields(raw[idx:])
        complete.write_text(raw, encoding="utf-8")

    agent6.write_text(strip_agent6_context_fields(agent6.read_text(encoding="utf-8")), encoding="utf-8")

    sec = raw[raw.index(marker) :]
    assert "Chat Rolling Summary" not in sec
    assert "Conversation Transcript" not in sec
    assert "chat_rolling_summary" not in sec
    assert "* Input keys: `message`" in sec
    print("OK — Agent 6 inputs simplified to message only")


if __name__ == "__main__":
    main()
