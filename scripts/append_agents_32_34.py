#!/usr/bin/env python3
"""Append Agents 32-34 to Complete_Agent_DataSet.md.

After any append_agents_26_30.py regen, re-run this script so Agents 32-34 are not stripped.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "Reference dataset" / "Complete_Agent_DataSet.md"
FRAGMENT = ROOT / "scripts" / "agents_32_34_source_upload.md"
AGENT32_MARKER = "\n## 32. Image OCR Agent"


def strip_evaluators(text: str) -> str:
    return re.sub(r"\n\*\*Evaluators:\*\*[^\n]*", "", text)


def update_header(text: str) -> str:
    text = text.replace("refined thirty-agent", "refined thirty-three-agent")
    text = text.replace("refined **thirty-agent**", "refined **thirty-three-agent**")
    text = text.replace("all thirty agents (1–6 and 8–30)", "all thirty-three agents (1–6, 8–30, 32–34)")
    text = text.replace("all thirty agents (1-6 and 8-30)", "all thirty-three agents (1-6, 8-30, 32-34)")

    old_intro = (
        "Agents 1–6 cover routing, retrieval, policy, and direct chat; Agents 8–16 cover chat summarization, "
        "hallucination guard retry, Studio system JSON, Studio generators (quiz, flashcards, mind map, slide deck), "
        "and legacy Studio regression agents; Agents 17–22 cover Problem Solver DNA analysis and coach modes; "
        "Agents 23–24 cover Tutor Mode bootstrap and follow-up questions; Agent 25 covers source question extraction; "
        "Agents 26–28 cover RAG ingestion (document sketch, NCERT sketch, chunk contextualization); "
        "Agents 29–30 cover whole-file map-reduce summarization."
    )
    new_intro = (
        "Agents 1–6 cover routing, retrieval, policy, and direct chat; Agents 8–16 cover chat summarization, "
        "hallucination guard retry, Studio system JSON, Studio generators (quiz, flashcards, mind map, slide deck), "
        "and legacy Studio regression agents; Agents 17–22 cover Problem Solver DNA analysis and coach modes; "
        "Agents 23–24 cover Tutor Mode bootstrap and follow-up questions; Agent 25 covers source question extraction; "
        "Agents 26–28 cover RAG ingestion (document sketch, NCERT sketch, chunk contextualization); "
        "Agents 29–30 cover whole-file map-reduce summarization; "
        "Agents 32–33 cover vision OCR on uploaded exam pages; Agent 34 covers guardrail refusal templates."
    )
    if old_intro in text:
        text = text.replace(old_intro, new_intro)

    old_dedup = (
        "**Global dedup rule:** no input string (`query`, `user_request`, `draft_answer`, `message`, "
        "`old_conversation`, `context`, `task_instruction`, `answer`, `custom_instructions`, "
        "`problem_text_normalized`, `student_attempt`, `action`, `document_text`, `header`, `whole_document`, "
        "`chunk_content`, `parts`, `user_message`, `assistant_message`, `ncert_context`, `section_summaries`, "
        "`target_context_tokens`, `target_summary_tokens`, `target_concept_terms`, etc.) in any agent may match "
        "a normalized input from another agent. Every example across all thirty agents (1–6 and 8–30) must be unique."
    )
    new_dedup = (
        "**Global dedup rule:** no input string (`query`, `user_request`, `draft_answer`, `message`, "
        "`old_conversation`, `context`, `task_instruction`, `answer`, `custom_instructions`, "
        "`problem_text_normalized`, `student_attempt`, `action`, `document_text`, `header`, `whole_document`, "
        "`chunk_content`, `parts`, `user_message`, `assistant_message`, `ncert_context`, `section_summaries`, "
        "`pdf_source`, `page_number`, `extracted_text`, `labels_text`, `scenario`, `refusal_reason`, etc.) "
        "in any agent may match a normalized input from another agent. "
        "Every example across all thirty-three agents (1–6, 8–30, 32–34) must be unique."
    )
    if old_dedup in text:
        text = text.replace(old_dedup, new_dedup)

    old_quotas = (
        "Document Sketch 13; NCERT Document Sketch 13; Chunk Contextualization 13; "
        "Whole File Map Summarizer 13; Whole File Reduce 13. "
        "Agent 7 (RAG Chat Response) skipped. **Minimum 15 examples** per agent 8–16, 17–21, 23–25; "
        "Agents 26–30 use 13 examples each; Agent 22 Tier-2 baseline 15."
    )
    new_quotas = (
        "Document Sketch 13; NCERT Document Sketch 13; Chunk Contextualization 13; "
        "Whole File Map Summarizer 13; Whole File Reduce 13; Image OCR 13; Diagram Label OCR 13; "
        "Refusal Templates 13. "
        "Agent 7 (RAG Chat Response) skipped; Agent 31 (map template) removed as duplicate of Agent 29. "
        "**Minimum 15 examples** per agent 8–16, 17–21, 23–25; Agents 26–30 and 32–34 use 13 each; Agent 22 Tier-2 baseline 15."
    )
    if old_quotas in text:
        text = text.replace(old_quotas, new_quotas)

    return text


def main() -> None:
    if not FRAGMENT.exists():
        raise SystemExit(f"Missing {FRAGMENT}. Run generate_agents_32_34.py first.")
    text = MD.read_text(encoding="utf-8")
    text = update_header(text)
    if AGENT32_MARKER in text:
        text = text[: text.index(AGENT32_MARKER)].rstrip()
    fragment = strip_evaluators(FRAGMENT.read_text(encoding="utf-8"))
    combined = text + "\n\n" + fragment + "\n"
    MD.write_text(combined, encoding="utf-8")
    print(f"Appended Agents 32-34 to {MD}")
    print(f"Total lines: {len(combined.splitlines())}")


if __name__ == "__main__":
    main()
