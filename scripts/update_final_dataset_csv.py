#!/usr/bin/env python3
"""Regenerate Reference dataset/final_Dataset_CSV.csv from live production prompts."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "packages/core/prompts/templates"
OUT = ROOT / "Reference dataset" / "final_Dataset_CSV.csv"
EXISTING = OUT


def read_file(rel: str) -> str:
    p = ROOT / rel
    return p.read_text(encoding="utf-8").strip() if p.is_file() else ""


def read_j2(name: str) -> str:
    p = TEMPLATES / name
    return p.read_text(encoding="utf-8").strip() if p.is_file() else ""


def combine(system: str, user: str) -> str:
    parts = []
    if system.strip():
        parts.append(f"SYSTEM:\n{system.strip()}")
    if user.strip():
        parts.append(f"USER/TASK TEMPLATE:\n{user.strip()}")
    return "\n\n".join(parts)

# Metadata columns preserved from prior CSV (by S.no); prompts always refreshed from codebase.
METADATA_BY_SNO: dict[int, dict[str, str]] = {
    1: {
        "Category": "Routing",
        "Input type": "Text input: user query + optional conversation history",
        "Output type": "Structured JSON object with intent, confidence, and reasoning",
        "Student-facing?": "No",
        "Security-sensitive?": "Yes",
        "Needs retrieval?": "No",
        "Needs source grounding?": "No",
        "Needs JSON/schema?": "Yes",
        "Complexity level C0–C5": "C1 — Intent routing / classification",
        "Failure impact: Low/Medium/High/Critical": "Critical",
    },
    2: {
        "Category": "Retrieval",
        "Input type": "Text input: user query + optional conversation transcript",
        "Output type": "Structured JSON object with queries[], confidence, and reasoning",
        "Student-facing?": "No",
        "Security-sensitive?": "Yes",
        "Needs retrieval?": "No",
        "Needs source grounding?": "No",
        "Needs JSON/schema?": "Yes",
        "Complexity level C0–C5": "C2 — Retrieval optimization",
        "Failure impact: Low/Medium/High/Critical": "High",
    },
    3: {
        "Category": "Retrieval",
        "Input type": "Text input: user query + max_sub_queries parameter",
        "Output type": "Structured JSON object with primary_concept and sub_queries[]",
        "Student-facing?": "No",
        "Security-sensitive?": "No",
        "Needs retrieval?": "No",
        "Needs source grounding?": "No",
        "Needs JSON/schema?": "Yes",
        "Complexity level C0–C5": "C2 — Query decomposition",
        "Failure impact: Low/Medium/High/Critical": "Medium",
    },
    4: {
        "Category": "Retrieval",
        "Input type": "Text input: latest user query + optional conversation context",
        "Output type": "Structured JSON object with key_terms, focused_query, and max_chunks",
        "Student-facing?": "No",
        "Security-sensitive?": "No",
        "Needs retrieval?": "No",
        "Needs source grounding?": "No",
        "Needs JSON/schema?": "Yes",
        "Complexity level C0–C5": "C2 — Retrieval optimization",
        "Failure impact: Low/Medium/High/Critical": "High",
    },
    5: {
        "Category": "Generation",
        "Input type": "Static YAML policy/config block + runtime setting such as STUDENT_AGE_TIER",
        "Output type": "No standalone output; constrains downstream student-facing natural-language responses",
        "Student-facing?": "Yes — indirectly controls student-facing generation",
        "Security-sensitive?": "Yes",
        "Needs retrieval?": "No",
        "Needs source grounding?": "Yes — indirectly, because it enforces evidence-grounded behavior in RAG answers",
        "Needs JSON/schema?": "No",
        "Complexity level C0–C5": "C0 — Deterministic/static policy configuration",
        "Failure impact: Low/Medium/High/Critical": "Critical",
    },
    6: {
        "Category": "Generation",
        "Input type": "Text input: current user message + optional compressed chat summary + optional recent conversation transcript",
        "Output type": "Student-facing natural-language Markdown response",
        "Student-facing?": "Yes",
        "Security-sensitive?": "No",
        "Needs retrieval?": "No",
        "Needs source grounding?": "No",
        "Needs JSON/schema?": "No",
        "Complexity level C0–C5": "C1 — Simple conversational generation",
        "Failure impact: Low/Medium/High/Critical": "Medium",
    },
    7: {
        "Category": "Generation",
        "Input type": "Text input: current user message + retrieved document context chunks + retrieval metadata + classified intent + prior conversation/rolling summary + central chat policy block + runtime flags",
        "Output type": "Student-facing natural-language Markdown response grounded in retrieved document context",
        "Student-facing?": "Yes",
        "Security-sensitive?": "Yes",
        "Needs retrieval?": "Yes",
        "Needs source grounding?": "Yes",
        "Needs JSON/schema?": "No",
        "Complexity level C0–C5": "C4 — High-stakes grounded generation",
        "Failure impact: Low/Medium/High/Critical": "Critical",
    },
    8: {
        "Category": "Generation",
        "Input type": "Text input: older conversation history / chat transcript",
        "Output type": "Structured Markdown summary with fixed section headings",
        "Student-facing?": "Yes — indirectly/student-reviewable",
        "Security-sensitive?": "No",
        "Needs retrieval?": "No",
        "Needs source grounding?": "No",
        "Needs JSON/schema?": "No",
        "Complexity level C0–C5": "C2 — Summarization / conversation compression",
        "Failure impact: Low/Medium/High/Critical": "Medium",
    },
    9: {
        "Category": "Generation",
        "Input type": "List of unsupported sentences detected post-generation + full RAG prompt for retry",
        "Output type": "Revised student-facing Markdown answer, through the RAG response generator retry",
        "Student-facing?": "Yes — indirectly controls the final student-facing answer",
        "Security-sensitive?": "Yes",
        "Needs retrieval?": "Yes — indirectly, because it depends on the already retrieved context evidence",
        "Needs source grounding?": "Yes",
        "Needs JSON/schema?": "No",
        "Complexity level C0–C5": "C0 if treated as a static prompt suffix; C4 if treated as a separate retry-generation agent",
        "Failure impact: Low/Medium/High/Critical": "Critical",
    },
    10: {
        "Category": "Studio",
        "Input type": "N/A (system role only)",
        "Output type": "Constrains LLM to valid JSON or Markdown per studio task",
        "Student-facing?": "Yes",
        "Security-sensitive?": "No",
        "Needs retrieval?": "Usually no — depends on whether the studio task is source-based",
        "Needs source grounding?": "Yes, when generating from uploaded/source content; otherwise no",
        "Needs JSON/schema?": "Yes",
        "Complexity level C0–C5": "C3 — Structured educational content generation",
        "Failure impact: Low/Medium/High/Critical": "High",
    },
    11: {
        "Category": "Studio",
        "Input type": "Text input: retrieved source excerpts + retrieval query notes + optional custom user instructions",
        "Output type": "Structured JSON quiz object with title, questions, options, correct_answer, and explanation",
        "Student-facing?": "Yes",
        "Security-sensitive?": "No",
        "Needs retrieval?": "Yes",
        "Needs source grounding?": "Yes",
        "Needs JSON/schema?": "Yes",
        "Complexity level C0–C5": "C3 — Structured educational content generation",
        "Failure impact: Low/Medium/High/Critical": "High",
    },
    12: {
        "Category": "Studio",
        "Input type": "Text input: retrieved source excerpts + selected source count + optional custom instructions",
        "Output type": "Structured JSON array of flashcard objects with front and back fields",
        "Student-facing?": "Yes",
        "Security-sensitive?": "No",
        "Needs retrieval?": "Yes",
        "Needs source grounding?": "Yes",
        "Needs JSON/schema?": "Yes",
        "Complexity level C0–C5": "C3 — Structured educational content generation",
        "Failure impact: Low/Medium/High/Critical": "High",
    },
    13: {
        "Category": "Studio",
        "Input type": "Text input: retrieved source excerpts + selected source count + optional custom instructions",
        "Output type": "Student-facing Markdown mind map outline",
        "Student-facing?": "Yes",
        "Security-sensitive?": "No",
        "Needs retrieval?": "Yes",
        "Needs source grounding?": "Yes",
        "Needs JSON/schema?": "No",
        "Complexity level C0–C5": "C3 — Structured educational content generation and synthesis",
        "Failure impact: Low/Medium/High/Critical": "High",
    },
    14: {
        "Category": "Studio",
        "Input type": "Text input: retrieved source excerpts + retrieval query notes + optional custom user instructions such as slide count, language, topic focus, or format preferences",
        "Output type": "Student-facing Markdown slide deck outline with numbered slide headings and bullet-based slide content",
        "Student-facing?": "Yes",
        "Security-sensitive?": "No",
        "Needs retrieval?": "Yes",
        "Needs source grounding?": "Yes",
        "Needs JSON/schema?": "No",
        "Complexity level C0–C5": "C4 — High-complexity structured educational generation",
        "Failure impact: Low/Medium/High/Critical": "High",
    },
    15: {
        "Category": "Studio",
        "Input type": "Text input: task_type + optional source/context content",
        "Output type": "Student-facing quiz/flashcards/mind_map/slide_deck artifact depending on task_type",
        "Student-facing?": "Yes",
        "Security-sensitive?": "No",
        "Needs retrieval?": "Conditional",
        "Needs source grounding?": "Yes, when context is provided",
        "Needs JSON/schema?": "Yes",
        "Complexity level C0–C5": "C3 — Structured educational content generation",
        "Failure impact: Low/Medium/High/Critical": "High",
    },
    16: {
        "Category": "Studio",
        "Input type": "Static text string used as a broad retrieval/embedding query",
        "Output type": "No LLM-generated output; produces/reuses a fixed query phrase for retrieval",
        "Student-facing?": "No",
        "Security-sensitive?": "No",
        "Needs retrieval?": "No — it is used for retrieval, but does not need retrieval itself",
        "Needs source grounding?": "No",
        "Needs JSON/schema?": "No",
        "Complexity level C0–C5": "C0 — Static deterministic retrieval query/config",
        "Failure impact: Low/Medium/High/Critical": "Medium",
    },
}

# Fill remaining agents 17-34 from existing CSV if present
def _load_existing_metadata() -> dict[int, dict[str, str]]:
    meta_keys = [
        "Category",
        "Input type",
        "Output type",
        "Student-facing?",
        "Security-sensitive?",
        "Needs retrieval?",
        "Needs source grounding?",
        "Needs JSON/schema?",
        "Complexity level C0–C5",
        "Failure impact: Low/Medium/High/Critical",
        "Model 1",
        "Input Token Cost (per 1 million)",
        "Output Token Cost",
        "Model 2",
        "Input Token Cost",
        "Output Token Cost",
        "Model 3",
        "Input Token Cost",
        "Output Token Cost",
        "Why this model",
    ]
    if not EXISTING.is_file():
        return {}
    with EXISTING.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    out: dict[int, dict[str, str]] = {}
    for r in rows:
        sno = int(r["S.no"])
        out[sno] = {k: r.get(k, "") for k in meta_keys}
        if sno in METADATA_BY_SNO:
            out[sno].update(METADATA_BY_SNO[sno])
        if out[sno].get("Category") == "Genration":
            out[sno]["Category"] = "Generation"
    return out


def build_prompt_rows() -> list[dict[str, str]]:
    studio_sys = read_j2("studio/system_educational_json_markdown.j2")
    hall_suffix = (
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

    specs: list[tuple[int, str, str, str, str]] = [
        (
            1,
            "Intent Classifier Agent",
            "Chat RAG routing",
            "Classifies user message intent (question, summary, security_block, etc.) to route the LangGraph chat pipeline.",
            combine(read_j2("agents/intent_classifier_system.j2"), read_j2("agents/intent_classifier_user.j2")),
        ),
        (
            2,
            "Query Rewriter Agent",
            "Retrieval optimization",
            "Rewrites user queries into search-optimized variants for vector/hybrid retrieval.",
            combine(read_j2("agents/query_rewriter_system.j2"), read_j2("agents/query_rewriter_user.j2")),
        ),
        (
            3,
            "Query Decomposer Agent",
            "Complex query splitting (optional)",
            "Breaks complex queries into primary concept and sub-queries when feature-flagged.",
            'SYSTEM:\nReturn JSON only: {"primary_concept": string, "sub_queries": string[]}.\n\n'
            "USER:\nDecompose this query into a primary concept and up to N short sub-queries optimized for document retrieval.",
        ),
        (
            4,
            "Scope Narrower Agent",
            "Retrieval scope control",
            "Extracts key terms, focused query, and suggested max_chunks for retrieval.",
            combine(read_j2("agents/scope_narrower_system.j2"), read_j2("agents/scope_narrower_user.j2")),
        ),
        (
            5,
            "Chat Policy Block (YAML)",
            "Central tone & safety policy",
            "Deployment-wide student-facing rules injected into RAG prompts when ENABLE_CHAT_POLICY_YAML is true.",
            read_file("packages/core/prompts/policies/chat_policy.default.yaml"),
        ),
        (
            6,
            "Direct Chat Agent (ScholarSync)",
            "Non-RAG conversational turns",
            "Handles greetings, thanks, and small talk when no document retrieval is needed.",
            read_j2("chat/direct_chat.j2"),
        ),
        (
            7,
            "RAG Chat Response Generator",
            "Grounded chat answers",
            "Main ScholarSync tutor response when document context is retrieved; enforces grounding, markdown structure, tutor blocks.",
            read_j2("chat/rag_prompt.j2"),
        ),
        (
            8,
            "Chat Summarizer Agent",
            "Long conversation compression",
            "Summarizes older chat turns into structured Markdown for memory compression.",
            read_j2("chat/chat_summarizer_prompt.j2"),
        ),
        (
            9,
            "Hallucination Guard Retry Suffix",
            "Answer grounding retry",
            "Appended to RAG prompt on retry when unsupported sentences detected post-generation.",
            hall_suffix,
        ),
        (
            10,
            "Studio System Prompt (JSON tasks)",
            "Studio shared system role",
            "Shared system instructions for structured JSON studio outputs (quiz, flashcards, mind map, slide deck).",
            studio_sys,
        ),
        (
            11,
            "Studio Quiz Generator",
            "Studio quiz",
            "Generates multiple-choice quiz JSON from retrieved source excerpts.",
            combine(studio_sys, read_j2("studio/quiz_prompt.j2")),
        ),
        (
            12,
            "Studio Flashcards Generator",
            "Studio flashcards",
            "Builds spaced-review flashcard deck JSON from selected sources.",
            combine(studio_sys, read_j2("studio/flashcards_prompt.j2")),
        ),
        (
            13,
            "Studio Mind Map Generator",
            "Studio mind map",
            "Produces hub-and-spoke mind map as Markdown from source excerpts.",
            combine(studio_sys, read_j2("studio/mind_map_prompt.j2")),
        ),
        (
            14,
            "Studio Slide Deck Generator",
            "Studio slides",
            "Creates narrative slide deck outline in Markdown with story arc.",
            combine(studio_sys, read_j2("studio/slide_deck_prompt.j2")),
        ),
        (
            15,
            "Studio Fallback Task Prompt (Legacy)",
            "Generic studio fallback",
            "Self-contained fallback when primary Studio task J2 is missing.",
            read_j2("studio/fallback_task_prompt.j2"),
        ),
        (
            16,
            "Studio Context Embedding Query (Legacy)",
            "Studio retrieval query",
            "Fallback embedding query builder; live path uses STUDIO_BROAD_RETRIEVAL_QUERIES + Query Rewriter.",
            read_j2("studio/context_embedding_query.j2"),
        ),
        (
            17,
            "Problem DNA Analyzer",
            "Problem Solver intake",
            "Classifies problem subject/chapter/difficulty and internal expert solution.",
            read_j2("problem_solver/dna.j2"),
        ),
        (
            18,
            "Explain From Basics Coach",
            "Problem Solver mode",
            "Full step-by-step explanation from fundamentals.",
            read_j2("problem_solver/explain_from_basics.j2"),
        ),
        (
            19,
            "Show Best Approach Coach",
            "Problem Solver mode",
            "Exam-optimized solution method with LaTeX math rules.",
            read_j2("problem_solver/show_best_approach.j2"),
        ),
        (
            20,
            "Show Missing Idea Coach",
            "Problem Solver mode",
            "Reveals key unlock without full solution (partial reveal).",
            read_j2("problem_solver/show_missing_idea.j2"),
        ),
        (
            21,
            "Help Me Solve It Coach",
            "Problem Solver guided mode",
            "Scaffolded hints and checkpoints without immediate final answer.",
            read_j2("problem_solver/help_me_solve_it.j2"),
        ),
        (
            22,
            "Problem Solver Follow-up Handler",
            "Problem Solver continuation",
            "Handles follow-up actions (similar problem, reveal, etc.).",
            read_j2("problem_solver/follow_up.j2"),
        ),
        (
            23,
            "Tutor Notebook Bootstrap Agent",
            "Tutor mode onboarding",
            "Generates opening summary, suggestion chips, and studio recommendations for NCERT tutor notebooks.",
            combine("Return valid JSON only.", read_j2("tutor/notebook_bootstrap.j2")),
        ),
        (
            24,
            "Tutor Follow-up Questions Agent",
            "Tutor chat directionality",
            "Suggests 3 contextual follow-up questions after each tutor exchange.",
            combine("Return valid JSON only.", read_j2("tutor/follow_up_questions.j2")),
        ),
        (
            25,
            "Source Question Extraction Agent",
            "PDF question parsing",
            "Parses exam/homework PDF text into structured question sections.",
            read_j2("source_questions/extract.j2"),
        ),
        (
            26,
            "Document Sketch Agent",
            "Contextual retrieval indexing",
            "Builds compact JSON document sketch for chunk contextualization during ingestion.",
            combine("Return JSON only. Do not include markdown fences.", read_j2("rag/document_sketch.j2")),
        ),
        (
            27,
            "NCERT Document Sketch Agent",
            "NCERT ingestion indexing",
            "NCERT-specific document sketch for contextual retrieval on NCERT PDFs.",
            combine("Return JSON only. Do not include markdown fences.", read_j2("rag/ncert_document_sketch.j2")),
        ),
        (
            28,
            "Chunk Contextualization Agent",
            "Per-chunk index enrichment",
            "Situates each chunk within whole document for better retrieval.",
            combine("Return JSON only. Do not include markdown fences.", read_j2("rag/chunk_contextualization.j2")),
        ),
        (
            29,
            "Whole File Map Summarizer",
            "Full-document summary (map phase)",
            "Summarizes document parts in batches before final reduce answer.",
            map_inline,
        ),
        (
            30,
            "Whole File Reduce Agent",
            "Full-document summary (reduce phase)",
            "Synthesizes final user-facing answer from all map-phase section summaries.",
            read_j2("rag/whole_file_reduce_prompt.j2"),
        ),
        (
            32,
            "Image OCR Agent",
            "Upload text extraction",
            "Extracts readable text from uploaded document images.",
            (
                "Extract all readable text from this document image exactly as written. "
                "Preserve math notation, question numbers, and line breaks. "
                "Return only the extracted text with no commentary."
            ),
        ),
        (
            33,
            "Diagram Label OCR Agent",
            "Diagram figure extraction",
            "Extracts English labels and flow hints from textbook diagrams.",
            (
                "You are reading a textbook diagram or circuit figure. "
                "Extract short English-only labels, variable names, and directional flow hints. "
                "Ignore Hindi/non-English text. Return plain text only."
            ),
        ),
        (
            34,
            "Refusal Templates (Guardrails)",
            "Safety refusal responses",
            "Pre-written safe refusal messages when input/output blocked (not LLM-generated).",
            (
                "Template strings per RefusalReason: INAPPROPRIATE_CONTENT, OUT_OF_SCOPE, "
                "ACADEMIC_ONLY, SAFETY_VIOLATION, PROMPT_INJECTION, PII_DETECTED, "
                "ACADEMIC_INTEGRITY, GENERAL — see refusal_templates.py for full text."
            ),
        ),
    ]

    existing_meta = _load_existing_metadata()
    rows: list[dict[str, str]] = []
    for sno, agent, func, desc, prompt in specs:
        meta = existing_meta.get(sno, {})
        row = {
            "S.no": str(sno),
            "Category": meta.get("Category", ""),
            "Agent": agent,
            "Functionality": func,
            "Simple Description (What is the purpose)": desc,
            "System Prompt": prompt,
            "Input type": meta.get("Input type", ""),
            "Output type": meta.get("Output type", ""),
            "Student-facing?": meta.get("Student-facing?", ""),
            "Security-sensitive?": meta.get("Security-sensitive?", ""),
            "Needs retrieval?": meta.get("Needs retrieval?", ""),
            "Needs source grounding?": meta.get("Needs source grounding?", ""),
            "Needs JSON/schema?": meta.get("Needs JSON/schema?", ""),
            "Complexity level C0–C5": meta.get("Complexity level C0–C5", ""),
            "Failure impact: Low/Medium/High/Critical": meta.get(
                "Failure impact: Low/Medium/High/Critical", ""
            ),
            "Model 1": meta.get("Model 1", ""),
            "Input Token Cost (per 1 million)": meta.get("Input Token Cost (per 1 million)", ""),
            "Output Token Cost": meta.get("Output Token Cost", ""),
            "Model 2": meta.get("Model 2", ""),
            "Input Token Cost": meta.get("Input Token Cost", ""),
            "Output Token Cost": meta.get("Output Token Cost", ""),
            "Model 3": meta.get("Model 3", ""),
            "Input Token Cost": meta.get("Input Token Cost", ""),
            "Output Token Cost": meta.get("Output Token Cost", ""),
            "Why this model": meta.get("Why this model", ""),
        }
        rows.append(row)
    return rows


def main() -> None:
    fieldnames = [
        "S.no",
        "Category",
        "Agent",
        "Functionality",
        "Simple Description (What is the purpose)",
        "System Prompt",
        "Input type",
        "Output type",
        "Student-facing?",
        "Security-sensitive?",
        "Needs retrieval?",
        "Needs source grounding?",
        "Needs JSON/schema?",
        "Complexity level C0–C5",
        "Failure impact: Low/Medium/High/Critical",
        "Model 1",
        "Input Token Cost (per 1 million)",
        "Output Token Cost",
        "Model 2",
        "Input Token Cost",
        "Output Token Cost",
        "Model 3",
        "Input Token Cost",
        "Output Token Cost",
        "Why this model",
    ]
    rows = build_prompt_rows()
    with OUT.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {OUT}")


if __name__ == "__main__":
    main()
