#!/usr/bin/env python3
"""Append Agents 17-22 to Complete_Agent_DataSet.md and update header."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "Reference dataset" / "Complete_Agent_DataSet.md"
FRAGMENT = ROOT / "scripts" / "agents_17_22_problem_solver.md"
AGENT17_MARKER = "\n## 17. Problem DNA Analyzer"


def strip_evaluators(text: str) -> str:
    return re.sub(r"\n\*\*Evaluators:\*\*[^\n]*", "", text)


def update_header(text: str) -> str:
    text = text.replace("uhave t#", "#")
    text = text.replace("refined sixteen-agent", "refined twenty-two-agent")
    text = text.replace("refined **sixteen-agent**", "refined **twenty-two-agent**")
    text = text.replace("all sixteen agents (1–6 and 8–16)", "all twenty-two agents (1–6 and 8–22)")
    text = text.replace("all sixteen agents (1-6 and 8-16)", "all twenty-two agents (1-6 and 8-22)")

    old_intro = (
        "Agents 1–6 cover routing, retrieval, policy, and direct chat; Agents 8–16 cover chat summarization, "
        "hallucination guard retry, Studio system JSON, Studio generators (quiz, flashcards, mind map, slide deck), "
        "and legacy Studio regression agents."
    )
    new_intro = (
        "Agents 1–6 cover routing, retrieval, policy, and direct chat; Agents 8–16 cover chat summarization, "
        "hallucination guard retry, Studio system JSON, Studio generators (quiz, flashcards, mind map, slide deck), "
        "and legacy Studio regression agents; Agents 17–22 cover Problem Solver DNA analysis and coach modes "
        "(explain from basics, best approach, missing idea, guided solve, follow-up)."
    )
    if old_intro in text:
        text = text.replace(old_intro, new_intro)

    old_dedup = (
        "**Global dedup rule:** no input string (`query`, `user_request`, `draft_answer`, `message`, "
        "`old_conversation`, `context`, `task_instruction`, `answer`, `custom_instructions`, etc.) in any agent "
        "may match a normalized input from another agent. Every example across all sixteen agents (1–6 and 8–16) must be unique."
    )
    new_dedup = (
        "**Global dedup rule:** no input string (`query`, `user_request`, `draft_answer`, `message`, "
        "`old_conversation`, `context`, `task_instruction`, `answer`, `custom_instructions`, "
        "`problem_text_normalized`, `student_attempt`, `action`, etc.) in any agent may match a normalized input "
        "from another agent. Every example across all twenty-two agents (1–6 and 8–22) must be unique."
    )
    if old_dedup in text:
        text = text.replace(old_dedup, new_dedup)

    old_quotas = (
        "**Per-agent quotas:** Intent Classifier 63; Query Rewriter 56; Query Decomposer 48; Scope Narrower 25; "
        "Chat Policy Block 25 (~50% pass/fail); Direct Chat 25; Chat Summarizer 20; Hallucination Guard 15 (~50% rewrite/pass); "
        "Studio System JSON 15; Studio Quiz 25; Studio Flashcards 22; Studio Mind Map 24; Studio Slide Deck 22; "
        "Studio Fallback Legacy 15; Studio Context Embedding Legacy 15. Agent 7 (RAG Chat Response) skipped. "
        "**Minimum 15 examples** per agent 8–16 (industry baseline)."
    )
    new_quotas = (
        "**Per-agent quotas:** Intent Classifier 63; Query Rewriter 56; Query Decomposer 48; Scope Narrower 25; "
        "Chat Policy Block 25 (~50% pass/fail); Direct Chat 25; Chat Summarizer 20; Hallucination Guard 15 (~50% rewrite/pass); "
        "Studio System JSON 15; Studio Quiz 25; Studio Flashcards 22; Studio Mind Map 24; Studio Slide Deck 22; "
        "Studio Fallback Legacy 15; Studio Context Embedding Legacy 15; Problem DNA Analyzer 30; Explain From Basics 30; "
        "Show Best Approach 30; Show Missing Idea 30; Help Me Solve It 30; Problem Solver Follow-up 15. "
        "Agent 7 (RAG Chat Response) skipped. **Minimum 15 examples** per agent 8–16 and 17–21; Agent 22 Tier-2 baseline 15."
    )
    if old_quotas in text:
        text = text.replace(old_quotas, new_quotas)

    return text


def main() -> None:
    if not FRAGMENT.exists():
        raise SystemExit(f"Missing fragment: {FRAGMENT}. Run generate_agents_17_22_problem_solver.py first.")
    text = MD.read_text(encoding="utf-8")
    text = update_header(text)
    if AGENT17_MARKER in text:
        text = text[: text.index(AGENT17_MARKER)].rstrip()
    fragment = strip_evaluators(FRAGMENT.read_text(encoding="utf-8"))
    combined = text + "\n\n" + fragment + "\n"
    MD.write_text(combined, encoding="utf-8")
    print(f"Appended Agents 17-22 to {MD}")
    print(f"Total lines: {len(combined.splitlines())}")


if __name__ == "__main__":
    main()
