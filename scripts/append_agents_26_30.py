#!/usr/bin/env python3
"""Append Agents 26-30 to Complete_Agent_DataSet.md."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "Reference dataset" / "Complete_Agent_DataSet.md"
FRAGMENT = ROOT / "scripts" / "agents_26_30_rag_source.md"
AGENT26_MARKER = "\n## 26. Document Sketch Agent"


def strip_evaluators(text: str) -> str:
    return re.sub(r"\n\*\*Evaluators:\*\*[^\n]*", "", text)


def update_header(text: str) -> str:
    text = text.replace("refined twenty-five-agent", "refined thirty-agent")
    text = text.replace("refined **twenty-five-agent**", "refined **thirty-agent**")
    text = text.replace("all twenty-five agents (1–6 and 8–25)", "all thirty agents (1–6 and 8–30)")
    text = text.replace("all twenty-five agents (1-6 and 8-25)", "all thirty agents (1-6 and 8-30)")

    old_intro = (
        "Agents 1–6 cover routing, retrieval, policy, and direct chat; Agents 8–16 cover chat summarization, "
        "hallucination guard retry, Studio system JSON, Studio generators (quiz, flashcards, mind map, slide deck), "
        "and legacy Studio regression agents; Agents 17–22 cover Problem Solver DNA analysis and coach modes; "
        "Agents 23–24 cover Tutor Mode bootstrap and follow-up questions; Agent 25 covers source question extraction "
        "from uploaded exam PDFs."
    )
    new_intro = (
        "Agents 1–6 cover routing, retrieval, policy, and direct chat; Agents 8–16 cover chat summarization, "
        "hallucination guard retry, Studio system JSON, Studio generators (quiz, flashcards, mind map, slide deck), "
        "and legacy Studio regression agents; Agents 17–22 cover Problem Solver DNA analysis and coach modes; "
        "Agents 23–24 cover Tutor Mode bootstrap and follow-up questions; Agent 25 covers source question extraction; "
        "Agents 26–28 cover RAG ingestion (document sketch, NCERT sketch, chunk contextualization); "
        "Agents 29–30 cover whole-file map-reduce summarization."
    )
    if old_intro in text:
        text = text.replace(old_intro, new_intro)

    old_dedup = (
        "**Global dedup rule:** no input string (`query`, `user_request`, `draft_answer`, `message`, "
        "`old_conversation`, `context`, `task_instruction`, `answer`, `custom_instructions`, "
        "`problem_text_normalized`, `student_attempt`, `action`, `document_text`, `user_message`, "
        "`assistant_message`, `ncert_context`, etc.) in any agent may match a normalized input "
        "from another agent. Every example across all twenty-five agents (1–6 and 8–25) must be unique."
    )
    new_dedup = (
        "**Global dedup rule:** no input string (`query`, `user_request`, `draft_answer`, `message`, "
        "`old_conversation`, `context`, `task_instruction`, `answer`, `custom_instructions`, "
        "`problem_text_normalized`, `student_attempt`, `action`, `document_text`, `header`, `whole_document`, "
        "`chunk_content`, `parts`, `user_message`, `assistant_message`, `ncert_context`, `section_summaries`, "
        "`target_context_tokens`, `target_summary_tokens`, `target_concept_terms`, etc.) in any agent may match "
        "a normalized input from another agent. Every example across all thirty agents (1–6 and 8–30) must be unique."
    )
    if old_dedup in text:
        text = text.replace(old_dedup, new_dedup)

    old_quotas = (
        "**Per-agent quotas:** Intent Classifier 63; Query Rewriter 56; Query Decomposer 48; Scope Narrower 25; "
        "Chat Policy Block 25 (~50% pass/fail); Direct Chat 25; Chat Summarizer 20; Hallucination Guard 15 (~50% rewrite/pass); "
        "Studio System JSON 15; Studio Quiz 25; Studio Flashcards 22; Studio Mind Map 24; Studio Slide Deck 22; "
        "Studio Fallback Legacy 15; Studio Context Embedding Legacy 15; Problem DNA Analyzer 30; Explain From Basics 30; "
        "Show Best Approach 30; Show Missing Idea 30; Help Me Solve It 30; Problem Solver Follow-up 15; "
        "Tutor Notebook Bootstrap 15; Tutor Follow-up Questions 30; Source Question Extraction 30. "
        "Agent 7 (RAG Chat Response) skipped. **Minimum 15 examples** per agent 8–16, 17–21, 23–25; Agent 22 Tier-2 baseline 15."
    )
    new_quotas = (
        "**Per-agent quotas:** Intent Classifier 63; Query Rewriter 56; Query Decomposer 48; Scope Narrower 25; "
        "Chat Policy Block 25 (~50% pass/fail); Direct Chat 25; Chat Summarizer 20; Hallucination Guard 15 (~50% rewrite/pass); "
        "Studio System JSON 15; Studio Quiz 25; Studio Flashcards 22; Studio Mind Map 24; Studio Slide Deck 22; "
        "Studio Fallback Legacy 15; Studio Context Embedding Legacy 15; Problem DNA Analyzer 30; Explain From Basics 30; "
        "Show Best Approach 30; Show Missing Idea 30; Help Me Solve It 30; Problem Solver Follow-up 15; "
        "Tutor Notebook Bootstrap 15; Tutor Follow-up Questions 30; Source Question Extraction 30; "
        "Document Sketch 13; NCERT Document Sketch 13; Chunk Contextualization 13; "
        "Whole File Map Summarizer 13; Whole File Reduce 13. "
        "Agent 7 (RAG Chat Response) skipped. **Minimum 15 examples** per agent 8–16, 17–21, 23–25; Agents 26–30 use 13 examples each; Agent 22 Tier-2 baseline 15."
    )
    old_quotas_15 = (
        "**Per-agent quotas:** Intent Classifier 63; Query Rewriter 56; Query Decomposer 48; Scope Narrower 25; "
        "Chat Policy Block 25 (~50% pass/fail); Direct Chat 25; Chat Summarizer 20; Hallucination Guard 15 (~50% rewrite/pass); "
        "Studio System JSON 15; Studio Quiz 25; Studio Flashcards 22; Studio Mind Map 24; Studio Slide Deck 22; "
        "Studio Fallback Legacy 15; Studio Context Embedding Legacy 15; Problem DNA Analyzer 30; Explain From Basics 30; "
        "Show Best Approach 30; Show Missing Idea 30; Help Me Solve It 30; Problem Solver Follow-up 15; "
        "Tutor Notebook Bootstrap 15; Tutor Follow-up Questions 30; Source Question Extraction 30; "
        "Document Sketch 15; NCERT Document Sketch 15; Chunk Contextualization 15; "
        "Whole File Map Summarizer 15; Whole File Reduce 15. "
        "Agent 7 (RAG Chat Response) skipped. **Minimum 15 examples** per agent 8–16, 17–21, 23–30; Agent 22 Tier-2 baseline 15."
    )
    if old_quotas_15 in text:
        text = text.replace(old_quotas_15, new_quotas)

    return text


def main() -> None:
    if not FRAGMENT.exists():
        raise SystemExit(f"Missing {FRAGMENT}. Run generate_agents_26_30.py first.")
    text = MD.read_text(encoding="utf-8")
    text = update_header(text)
    if AGENT26_MARKER in text:
        text = text[: text.index(AGENT26_MARKER)].rstrip()
    fragment = strip_evaluators(FRAGMENT.read_text(encoding="utf-8"))
    combined = text + "\n\n" + fragment + "\n"
    MD.write_text(combined, encoding="utf-8")
    print(f"Appended Agents 26-30 to {MD}")
    print(f"Total lines: {len(combined.splitlines())}")


if __name__ == "__main__":
    main()
