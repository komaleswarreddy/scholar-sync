#!/usr/bin/env python3
"""Append Agents 8-16 to Complete_Agent_DataSet.md and update header."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "Reference dataset" / "Complete_Agent_DataSet.md"

FRAGMENTS = [
    ROOT / "scripts" / "agent8_chat_summarizer.md",
    ROOT / "scripts" / "agent9_hallucination_guard.md",
    ROOT / "scripts" / "agent10_studio_system_json.md",
    ROOT / "scripts" / "agent11_studio_quiz.md",
    ROOT / "scripts" / "agent12_studio_flashcards.md",
    ROOT / "scripts" / "agent13_studio_mind_map.md",
    ROOT / "scripts" / "agent14_studio_slide_deck.md",
    ROOT / "scripts" / "agents15_16_studio_legacy.md",
]

AGENT8_MARKER = "\n## 8. Chat Summarizer Agent"


def strip_evaluators(text: str) -> str:
    return re.sub(r"\n\*\*Evaluators:\*\*[^\n]*", "", text)


def update_header(text: str) -> str:
    text = text.replace(
        "refined six-agent",
        "refined sixteen-agent",
    )
    text = text.replace(
        "refined **six-agent**",
        "refined **sixteen-agent**",
    )
    old_intro = (
        "with subject-balanced examples grounded in all 20 NCERT PDFs in the Class 11–12 catalog."
    )
    new_intro = (
        "with subject-balanced examples grounded in all 20 NCERT PDFs in the Class 11–12 catalog. "
        "Agents 1–6 cover routing, retrieval, policy, and direct chat; Agents 8–16 cover chat summarization, "
        "hallucination guard retry, Studio system JSON, Studio generators (quiz, flashcards, mind map, slide deck), "
        "and legacy Studio regression agents."
    )
    if old_intro in text and new_intro not in text:
        text = text.replace(old_intro, new_intro)

    old_dedup = (
        "**Global dedup rule:** no `user_request`, `draft_answer`, or `message` string in Agents 5–6 "
        "may match any normalized `Query:` from Agents 1–4. Every example across all six agents must be unique."
    )
    new_dedup = (
        "**Global dedup rule:** no input string (`query`, `user_request`, `draft_answer`, `message`, "
        "`old_conversation`, `context`, `task_instruction`, `answer`, `custom_instructions`, etc.) in any agent "
        "may match a normalized input from another agent. Every example across all sixteen agents (1–6 and 8–16) must be unique."
    )
    if old_dedup in text:
        text = text.replace(old_dedup, new_dedup)

    quota_patterns = [
        (
            "**Per-agent quotas:** Intent Classifier academic pool ~11/subject; Query Rewriter 12/subject; Query Decomposer 12/subject; Scope Narrower 6–7/subject; Chat Policy Block 25 examples (~50% pass / 50% fail); Direct Chat 25 examples (product/navigation focused, non-RAG).",
            None,
        ),
        (
            "**Per-agent quotas:** Intent Classifier 63; Query Rewriter 56; Query Decomposer 48; Scope Narrower 25; "
            "Chat Policy Block 25 (~50% pass/fail); Direct Chat 25; Chat Summarizer 20; Hallucination Guard 12 (~50% rewrite/pass); "
            "Studio System JSON 10; Studio Quiz 25; Studio Flashcards 22; Studio Mind Map 24; Studio Slide Deck 22; "
            "Studio Fallback Legacy 8; Studio Context Embedding Legacy 8. Agent 7 (RAG Chat Response) skipped.",
            None,
        ),
    ]
    new_quotas = (
        "**Per-agent quotas:** Intent Classifier 63; Query Rewriter 56; Query Decomposer 48; Scope Narrower 25; "
        "Chat Policy Block 25 (~50% pass/fail); Direct Chat 25; Chat Summarizer 20; Hallucination Guard 15 (~50% rewrite/pass); "
        "Studio System JSON 15; Studio Quiz 25; Studio Flashcards 22; Studio Mind Map 24; Studio Slide Deck 22; "
        "Studio Fallback Legacy 15; Studio Context Embedding Legacy 15. Agent 7 (RAG Chat Response) skipped. "
        "**Minimum 15 examples** per agent 8–16 (industry baseline)."
    )
    for old, _ in quota_patterns:
        if old in text:
            text = text.replace(old, new_quotas)
            break
    else:
        if "**Per-agent quotas:**" in text and new_quotas not in text:
            text = re.sub(r"\*\*Per-agent quotas:\*\*[^\n]+", new_quotas, text, count=1)

    return text


def remove_duplicate_decomposer_header(text: str) -> str:
    pattern = r"(## 3\. Query Decomposer Agent \(Refined\)\s*\n\n---\s*\n\n)## 3\. Query Decomposer Agent \(Refined\)\s*\n\n---\s*\n\n"
    return re.sub(pattern, r"\1", text, count=1)


def main() -> None:
    text = MD.read_text(encoding="utf-8")
    text = update_header(text)
    text = remove_duplicate_decomposer_header(text)

    if AGENT8_MARKER in text:
        text = text[: text.index(AGENT8_MARKER)].rstrip()

    parts = [text]
    for frag in FRAGMENTS:
        content = strip_evaluators(frag.read_text(encoding="utf-8"))
        parts.append(content)

    combined = "\n\n".join(parts) + "\n"
    MD.write_text(combined, encoding="utf-8")
    print(f"Appended {len(FRAGMENTS)} agent sections to {MD}")
    print(f"Total lines: {len(combined.splitlines())}")


if __name__ == "__main__":
    main()
