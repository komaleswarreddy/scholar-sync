#!/usr/bin/env python3
"""Verify final_Dataset_CSV.csv System Prompt column matches live production templates."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "packages/core/prompts/templates"
CSV_PATH = ROOT / "Reference dataset" / "final_Dataset_CSV.csv"


def read_j2(name: str) -> str:
    p = TEMPLATES / name
    return p.read_text(encoding="utf-8").strip() if p.is_file() else ""


def read_file(rel: str) -> str:
    p = ROOT / rel
    return p.read_text(encoding="utf-8").strip() if p.is_file() else ""


def combine(system: str, user: str) -> str:
    parts = []
    if system.strip():
        parts.append(f"SYSTEM:\n{system.strip()}")
    if user.strip():
        parts.append(f"USER/TASK TEMPLATE:\n{user.strip()}")
    return "\n\n".join(parts)


def expected_prompts() -> dict[str, str]:
    studio_sys = read_j2("studio/system_educational_json_markdown.j2")
    hall = (
        "Grounding instruction (hallucination guard):\n"
        "- Remove, soften, or label as `General knowledge:` any sentence not directly supported by the Context evidence.\n"
        "- Prefer restating the evidence using the same terms as the excerpts.\n"
        "- Do not add new specific numbers, names, dates, or quotes unless they appear in the evidence.\n"
        "+ optional list of unsupported sentences"
    )
    map_inline = (
        "You are summarizing parts of a document for a later full-document summary.\n"
        "For each Part below, write EXACTLY ONE concise sentence capturing its main idea.\n"
        "Number your lines Part 1, Part 2, ... matching the order below.\n"
        "Do not add an introduction or conclusion."
    )
    return {
        "Intent Classifier Agent": combine(
            read_j2("agents/intent_classifier_system.j2"),
            read_j2("agents/intent_classifier_user.j2"),
        ),
        "Query Rewriter Agent": combine(
            read_j2("agents/query_rewriter_system.j2"),
            read_j2("agents/query_rewriter_user.j2"),
        ),
        "Query Decomposer Agent": (
            'SYSTEM:\nReturn JSON only: {"primary_concept": string, "sub_queries": string[]}.\n\n'
            "USER:\nDecompose this query into a primary concept and up to N short sub-queries optimized for document retrieval."
        ),
        "Scope Narrower Agent": combine(
            read_j2("agents/scope_narrower_system.j2"),
            read_j2("agents/scope_narrower_user.j2"),
        ),
        "Chat Policy Block (YAML)": read_file("packages/core/prompts/policies/chat_policy.default.yaml"),
        "Direct Chat Agent (ScholarSync)": read_j2("chat/direct_chat.j2"),
        "RAG Chat Response Generator": read_j2("chat/rag_prompt.j2"),
        "Chat Summarizer Agent": read_j2("chat/chat_summarizer_prompt.j2"),
        "Hallucination Guard Retry Suffix": hall,
        "Studio System Prompt (JSON tasks)": studio_sys,
        "Studio Quiz Generator": combine(studio_sys, read_j2("studio/quiz_prompt.j2")),
        "Studio Flashcards Generator": combine(studio_sys, read_j2("studio/flashcards_prompt.j2")),
        "Studio Mind Map Generator": combine(studio_sys, read_j2("studio/mind_map_prompt.j2")),
        "Studio Slide Deck Generator": combine(studio_sys, read_j2("studio/slide_deck_prompt.j2")),
        "Studio Fallback Task Prompt (Legacy)": read_j2("studio/fallback_task_prompt.j2"),
        "Studio Context Embedding Query (Legacy)": read_j2("studio/context_embedding_query.j2"),
        "Problem DNA Analyzer": read_j2("problem_solver/dna.j2"),
        "Explain From Basics Coach": read_j2("problem_solver/explain_from_basics.j2"),
        "Show Best Approach Coach": read_j2("problem_solver/show_best_approach.j2"),
        "Show Missing Idea Coach": read_j2("problem_solver/show_missing_idea.j2"),
        "Help Me Solve It Coach": read_j2("problem_solver/help_me_solve_it.j2"),
        "Problem Solver Follow-up Handler": read_j2("problem_solver/follow_up.j2"),
        "Tutor Notebook Bootstrap Agent": combine("Return valid JSON only.", read_j2("tutor/notebook_bootstrap.j2")),
        "Tutor Follow-up Questions Agent": combine("Return valid JSON only.", read_j2("tutor/follow_up_questions.j2")),
        "Source Question Extraction Agent": read_j2("source_questions/extract.j2"),
        "Document Sketch Agent": combine(
            "Return JSON only. Do not include markdown fences.", read_j2("rag/document_sketch.j2")
        ),
        "NCERT Document Sketch Agent": combine(
            "Return JSON only. Do not include markdown fences.", read_j2("rag/ncert_document_sketch.j2")
        ),
        "Chunk Contextualization Agent": combine(
            "Return JSON only. Do not include markdown fences.", read_j2("rag/chunk_contextualization.j2")
        ),
        "Whole File Map Summarizer": map_inline,
        "Whole File Reduce Agent": read_j2("rag/whole_file_reduce_prompt.j2"),
        "Image OCR Agent": (
            "Extract all readable text from this document image exactly as written. "
            "Preserve math notation, question numbers, and line breaks. "
            "Return only the extracted text with no commentary."
        ),
        "Diagram Label OCR Agent": (
            "You are reading a textbook diagram or circuit figure. "
            "Extract short English-only labels, variable names, and directional flow hints. "
            "Ignore Hindi/non-English text. Return plain text only."
        ),
        "Refusal Templates (Guardrails)": (
            "Template strings per RefusalReason: INAPPROPRIATE_CONTENT, OUT_OF_SCOPE, "
            "ACADEMIC_ONLY, SAFETY_VIOLATION, PROMPT_INJECTION, PII_DETECTED, "
            "ACADEMIC_INTEGRITY, GENERAL — see refusal_templates.py for full text."
        ),
    }


def main() -> int:
    expected = expected_prompts()
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    failures = []
    for r in rows:
        agent = r["Agent"]
        if agent not in expected:
            failures.append(f"{r['S.no']} {agent}: no expected mapping")
            continue
        csv_p = (r.get("System Prompt") or "").strip()
        exp_p = expected[agent].strip()
        if csv_p != exp_p:
            failures.append(f"{r['S.no']} {agent}: mismatch (csv={len(csv_p)} exp={len(exp_p)})")
    if failures:
        print("FAILURES:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"OK: all {len(rows)} agents match production prompts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
