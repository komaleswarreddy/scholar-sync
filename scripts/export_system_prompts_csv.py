"""Export all system prompts / agent prompts to Current_System_Prompts.csv."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "packages/core/prompts/templates"


def read_file(rel: str) -> str:
    p = ROOT / rel
    if p.is_file():
        return p.read_text(encoding="utf-8").strip()
    return ""


def read_j2(name: str) -> str:
    p = TEMPLATES / name
    if p.is_file():
        return p.read_text(encoding="utf-8").strip()
    return ""


def combine(system: str, user: str) -> str:
    parts = []
    if system.strip():
        parts.append(f"SYSTEM:\n{system.strip()}")
    if user.strip():
        parts.append(f"USER/TASK TEMPLATE:\n{user.strip()}")
    return "\n\n".join(parts)


rows: list[dict[str, str]] = []


def add(
    sno: int,
    agent: str,
    functionality: str,
    desc: str,
    system_prompt: str,
    io: str,
    deps: str,
    file_name: str,
    status: str = "Active",
) -> None:
    rows.append(
        {
            "S.no": str(sno),
            "Agent": agent,
            "Functionality": functionality,
            "Simple Description (What is the purpose)": desc,
            "System Prompt": system_prompt,
            "Inputs/Outputs": io,
            "Any Dependencies": deps,
            "File Name in Code Base": file_name,
            "Status": status,
        }
    )


# --- CHAT / RAG AGENTS ---
add(
    1,
    "Intent Classifier Agent",
    "Chat RAG routing",
    "Classifies user message intent (question, summary, security_block, etc.) to route the LangGraph chat pipeline.",
    combine(read_j2("agents/intent_classifier_system.j2"), read_j2("agents/intent_classifier_user.j2")),
    "Input: user query + optional conversation history. Output: JSON {intent, confidence, reasoning}.",
    "packages/core/rag/agents/intent_classifier.py; OpenAI JSON mode; get_model_for_task(intent_classifier)",
    "packages/core/prompts/templates/agents/intent_classifier_system.j2 (+ intent_classifier_user.j2)",
)

add(
    2,
    "Query Rewriter Agent",
    "Retrieval optimization",
    "Rewrites user queries into search-optimized variants for vector/hybrid retrieval.",
    combine(read_j2("agents/query_rewriter_system.j2"), read_j2("agents/query_rewriter_user.j2")),
    "Input: query + conversation transcript. Output: JSON {queries[], confidence, reasoning}.",
    "packages/core/rag/agents/query_rewriter.py; feature_tag=query_rewriter",
    "packages/core/prompts/templates/agents/query_rewriter_system.j2 (+ query_rewriter_user.j2)",
)

add(
    3,
    "Scope Narrower Agent",
    "Retrieval scope control",
    "Extracts key terms, focused query, and suggested max_chunks for retrieval.",
    combine(read_j2("agents/scope_narrower_system.j2"), read_j2("agents/scope_narrower_user.j2")),
    "Input: query + optional conversation. Output: JSON {key_terms, focused_query, max_chunks}.",
    "packages/core/rag/agents/scope_narrower.py",
    "packages/core/prompts/templates/agents/scope_narrower_system.j2 (+ scope_narrower_user.j2)",
)

add(
    4,
    "Query Decomposer Agent",
    "Complex query splitting (optional)",
    "Breaks complex queries into primary concept and sub-queries when feature-flagged.",
    'SYSTEM:\nReturn JSON only: {"primary_concept": string, "sub_queries": string[]}.\n\n'
    "USER:\nDecompose this query into a primary concept and up to N short sub-queries optimized for document retrieval.",
    "Input: query, max_sub_queries. Output: JSON {primary_concept, sub_queries}.",
    "packages/core/rag/agents/query_decomposer.py; ENABLE_QUERY_DECOMPOSITION; get_model_for_task(query_decomposer)",
    "packages/core/rag/agents/query_decomposer.py (inline prompts)",
)

add(
    5,
    "RAG Chat Response Generator",
    "Grounded chat answers",
    "Main ScholarSync tutor response when document context is retrieved; enforces grounding, markdown structure, tutor blocks.",
    read_j2("chat/rag_prompt.j2"),
    "Input: context chunks, user message, retrieval metadata, chat history, policy block, intent. Output: Markdown answer streamed via SSE.",
    "packages/core/langgraph/chat_graph.py (_node_generate); build_chat_policy_block(); Pinecone retriever; hallucination_guard retry",
    "packages/core/prompts/templates/chat/rag_prompt.j2",
)

add(
    6,
    "Direct Chat Agent (ScholarSync)",
    "Non-RAG conversational turns",
    "Handles greetings, thanks, and small talk when no document retrieval is needed.",
    read_j2("chat/direct_chat.j2"),
    "Input: message, conversation transcript, rolling summary. Output: brief Markdown reply (no source claims).",
    "packages/core/langgraph/chat_graph.py (_node_direct_chat); feature_tag=chat_langgraph_direct",
    "packages/core/prompts/templates/chat/direct_chat.j2",
)

add(
    7,
    "Chat Policy Block (YAML)",
    "Central tone & safety policy",
    "Deployment-wide student-facing rules injected into RAG prompts when ENABLE_CHAT_POLICY_YAML is true.",
    read_file("packages/core/prompts/policies/chat_policy.default.yaml"),
    "Input: STUDENT_AGE_TIER setting. Output: Markdown policy block merged into rag_prompt.j2.",
    "packages/core/knowledge/policy_loader.py (build_chat_policy_block); config/settings.py",
    "packages/core/prompts/policies/chat_policy.default.yaml",
)

add(
    8,
    "Chat Summarizer Agent",
    "Long conversation compression",
    "Summarizes older chat turns into structured Markdown for memory compression.",
    read_j2("chat/chat_summarizer_prompt.j2"),
    "Input: old_conversation text. Output: Markdown summary with fixed section headings.",
    "packages/core/memory/chat_summarizer.py; apps/api/routes/chat.py; feature_tag=chat_summarizer",
    "packages/core/prompts/templates/chat/chat_summarizer_prompt.j2",
)

add(
    9,
    "Hallucination Guard Retry Suffix",
    "Answer grounding retry",
    "Appended to RAG prompt on retry when unsupported sentences detected post-generation.",
    (
        "Grounding instruction (hallucination guard):\n"
        "- Remove, soften, or label as `General knowledge:` any sentence not directly supported by the Context evidence.\n"
        "- Prefer restating the evidence using the same terms as the excerpts.\n"
        "- Do not add new specific numbers, names, dates, or quotes unless they appear in the evidence.\n"
        "+ optional list of unsupported sentences"
    ),
    "Input: unsupported_sentences list. Output: suffix string appended to full_prompt for retry LLM call.",
    "packages/core/rag/hallucination_guard.py (strict_retry_suffix); chat_graph.py",
    "packages/core/rag/hallucination_guard.py",
)

# --- STUDIO ---
studio_sys_json = read_j2("studio/system_educational_json_markdown.j2")

add(
    10,
    "Studio System Prompt (JSON tasks)",
    "Studio shared system role",
    "Shared system instructions for structured JSON studio outputs (quiz, flashcards, mind map, slide deck).",
    studio_sys_json,
    "Input: N/A (system role). Output: constrains LLM to valid JSON or Markdown per task.",
    "packages/core/services/studio_service.py (_generate_structured_task)",
    "packages/core/prompts/templates/studio/system_educational_json_markdown.j2",
)

studio_tasks = [
    (
        "Studio Quiz Generator",
        "Studio quiz",
        "Generates multiple-choice quiz JSON from retrieved source excerpts.",
        "studio/quiz_prompt.j2",
        "Input: context, custom_instructions, retrieval_queries_note. Output: JSON {title, questions[]}.",
        "studio_service._generate_structured_task + system_educational_json_markdown.j2",
        studio_sys_json,
    ),
    (
        "Studio Flashcards Generator",
        "Studio flashcards",
        "Builds spaced-review flashcard deck JSON from selected sources.",
        "studio/flashcards_prompt.j2",
        "Input: context, selected_source_count, custom_instructions. Output: JSON array [{front, back}].",
        "studio_service._generate_structured_task",
        studio_sys_json,
    ),
    (
        "Studio Mind Map Generator",
        "Studio mind map",
        "Produces hub-and-spoke mind map as Markdown from source excerpts.",
        "studio/mind_map_prompt.j2",
        "Input: context, selected_source_count. Output: Markdown mind map.",
        "studio_service._generate_structured_task",
        studio_sys_json,
    ),
    (
        "Studio Slide Deck Generator",
        "Studio slides",
        "Creates narrative slide deck outline in Markdown with story arc.",
        "studio/slide_deck_prompt.j2",
        "Input: context, custom_instructions. Output: Markdown slides.",
        "studio_service._generate_structured_task",
        studio_sys_json,
    ),
]

for idx, (agent, func, desc, tpl, io, deps, sys_p) in enumerate(studio_tasks, start=11):
    add(
        idx,
        agent,
        func,
        desc,
        combine(sys_p, read_j2(tpl)),
        io,
        deps,
        f"packages/core/prompts/templates/{tpl}",
    )

add(
    15,
    "Studio Fallback Task Prompt (Legacy)",
    "Generic studio fallback",
    "Self-contained fallback when primary Studio task J2 is missing.",
    read_j2("studio/fallback_task_prompt.j2"),
    "Input: task_type, context, custom_instructions. Output: full quiz/flashcards/mind_map/slide_deck artifact.",
    "studio_service._load_prompt_template on FileNotFoundError; pairs with Agent 10 system prompt",
    "packages/core/prompts/templates/studio/fallback_task_prompt.j2",
    status="Fallback (wired on FileNotFoundError)",
)

add(
    16,
    "Studio Context Embedding Query (Legacy)",
    "Studio retrieval query",
    "Fallback embedding query builder; live path uses STUDIO_BROAD_RETRIEVAL_QUERIES + Query Rewriter.",
    read_j2("studio/context_embedding_query.j2"),
    "Input: studio_task, source_title, topic, retrieval_focus. Output: embedding_query string.",
    "Not loaded by studio_service; eval/regression and future dynamic embedding path",
    "packages/core/prompts/templates/studio/context_embedding_query.j2",
    status="Fallback (not wired in live retrieval)",
)

# --- PROBLEM SOLVER ---
ps_modes = [
    (
        "Problem DNA Analyzer",
        "Problem Solver intake",
        "Classifies problem subject/chapter/difficulty and internal expert solution.",
        "problem_solver/dna.j2",
        "Input: problem_text, scope, ncert_context. Output: JSON problem DNA + expert_solution_internal.",
        "problem_solver_service.py; feature_tag=problem_solver_dna",
    ),
    (
        "Explain From Basics Coach",
        "Problem Solver mode",
        "Full step-by-step explanation from fundamentals.",
        "problem_solver/explain_from_basics.j2",
        "Input: problem_text, ncert_context. Output: JSON sections + finalAnswer.",
        "problem_solver_service._run_mode",
    ),
    (
        "Show Best Approach Coach",
        "Problem Solver mode",
        "Exam-optimized solution method with LaTeX math rules.",
        "problem_solver/show_best_approach.j2",
        "Input: problem_text, ncert_context. Output: JSON sections.",
        "problem_solver_service._run_mode",
    ),
    (
        "Show Missing Idea Coach",
        "Problem Solver mode",
        "Reveals key unlock without full solution (partial reveal).",
        "problem_solver/show_missing_idea.j2",
        "Input: problem_text. Output: JSON with revealLevel=partial.",
        "problem_solver_service._run_mode",
    ),
    (
        "Help Me Solve It Coach",
        "Problem Solver guided mode",
        "Scaffolded hints and checkpoints without immediate final answer.",
        "problem_solver/help_me_solve_it.j2",
        "Input: problem_text, interaction_count, checkpoint. Output: JSON hints/checkpoints.",
        "problem_solver_service._run_mode",
    ),
    (
        "Problem Solver Follow-up Handler",
        "Problem Solver continuation",
        "Handles follow-up actions (similar problem, reveal, etc.).",
        "problem_solver/follow_up.j2",
        "Input: action, problem_text, solving_mode. Output: JSON follow-up sections.",
        "problem_solver_service._handle_follow_up",
    ),
]

for j, (agent, func, desc, tpl, io, deps) in enumerate(ps_modes, start=17):
    add(j, agent, func, desc, read_j2(tpl), io, deps, f"packages/core/prompts/templates/{tpl}")

# --- TUTOR ---
add(
    23,
    "Tutor Notebook Bootstrap Agent",
    "Tutor mode onboarding",
    "Generates opening summary, suggestion chips, and studio recommendations for NCERT tutor notebooks.",
    combine("Return valid JSON only.", read_j2("tutor/notebook_bootstrap.j2")),
    "Input: class, subject, chapter, concept, ncert_context. Output: JSON bootstrap payload.",
    "tutor_notebook_bootstrap_service.py; feature_tag=tutor_notebook_bootstrap",
    "packages/core/prompts/templates/tutor/notebook_bootstrap.j2",
)

add(
    24,
    "Tutor Follow-up Questions Agent",
    "Tutor chat directionality",
    "Suggests 3 contextual follow-up questions after each tutor exchange.",
    combine("Return valid JSON only.", read_j2("tutor/follow_up_questions.j2")),
    "Input: scope, user_message, assistant_message. Output: JSON {follow_ups: string[3]}.",
    "tutor_notebook_bootstrap_service.py; feature_tag=tutor_follow_ups",
    "packages/core/prompts/templates/tutor/follow_up_questions.j2",
)

# --- INGESTION / RAG INDEX ---
add(
    25,
    "Source Question Extraction Agent",
    "PDF question parsing",
    "Parses exam/homework PDF text into structured question sections.",
    read_j2("source_questions/extract.j2"),
    "Input: document_text. Output: JSON {sections: [{label, questions[]}]}.",
    "source_question_extraction_service.py; feature_tag=source_question_extract",
    "packages/core/prompts/templates/source_questions/extract.j2",
)

add(
    26,
    "Document Sketch Agent",
    "Contextual retrieval indexing",
    "Builds compact JSON document sketch for chunk contextualization during ingestion.",
    combine(
        "Return JSON only. Do not include markdown fences.",
        read_j2("rag/document_sketch.j2"),
    ),
    "Input: header, document_text. Output: JSON document sketch.",
    "document_sketcher.py",
    "packages/core/prompts/templates/rag/document_sketch.j2",
)

add(
    27,
    "NCERT Document Sketch Agent",
    "NCERT ingestion indexing",
    "NCERT-specific document sketch for contextual retrieval on NCERT PDFs.",
    combine(
        "Return JSON only. Do not include markdown fences.",
        read_j2("rag/ncert_document_sketch.j2"),
    ),
    "Input: header, document_text. Output: JSON document sketch.",
    "document_sketcher.py (NCERT path)",
    "packages/core/prompts/templates/rag/ncert_document_sketch.j2",
)

add(
    28,
    "Chunk Contextualization Agent",
    "Per-chunk index enrichment",
    "Situates each chunk within whole document for better retrieval.",
    combine(
        "Return JSON only. Do not include markdown fences.",
        read_j2("rag/chunk_contextualization.j2"),
    ),
    "Input: whole_document, chunk_content, token targets. Output: JSON chunk metadata.",
    "contextualizer.py",
    "packages/core/prompts/templates/rag/chunk_contextualization.j2",
)

add(
    29,
    "Whole File Map Summarizer",
    "Full-document summary (map phase)",
    "Summarizes document parts in batches before final reduce answer.",
    (
        "You are summarizing parts of a document for a later full-document summary.\n"
        "For each Part below, write EXACTLY ONE concise sentence capturing its main idea.\n"
        "Number your lines Part 1, Part 2, ... matching the order below.\n"
        "Do not add an introduction or conclusion."
    ),
    "Input: batched chunk excerpts. Output: numbered one-sentence summaries per part.",
    "whole_file_map_reduce.py (_map_batch_summarize); feature_tag=whole_file_map",
    "packages/core/rag/whole_file_map_reduce.py (inline in _map_batch_summarize)",
)

add(
    30,
    "Whole File Reduce Agent",
    "Full-document summary (reduce phase)",
    "Synthesizes final user-facing answer from all map-phase section summaries.",
    read_j2("rag/whole_file_reduce_prompt.j2"),
    "Input: user_message, section_summaries. Output: structured Markdown answer.",
    "whole_file_map_reduce.py (_reduce_summaries); feature_tag=whole_file_reduce",
    "packages/core/prompts/templates/rag/whole_file_reduce_prompt.j2",
)

# --- VISION OCR ---
add(
    32,
    "Image OCR Agent",
    "Upload text extraction",
    "Extracts readable text from uploaded document images.",
    (
        "Extract all readable text from this document image exactly as written. "
        "Preserve math notation, question numbers, and line breaks. "
        "Return only the extracted text with no commentary."
    ),
    "Input: image bytes (vision model). Output: plain extracted text.",
    "packages/core/processing/image_ocr.py; get_model_for_task(vision)",
    "packages/core/processing/image_ocr.py (_OCR_PROMPT)",
)

add(
    33,
    "Diagram Label OCR Agent",
    "Diagram figure extraction",
    "Extracts English labels and flow hints from textbook diagrams.",
    (
        "You are reading a textbook diagram or circuit figure. "
        "Extract short English-only labels, variable names, and directional flow hints. "
        "Ignore Hindi/non-English text. Return plain text only."
    ),
    "Input: diagram image. Output: plain text labels/flow hints.",
    "packages/core/processing/image_ocr.py (_DIAGRAM_PROMPT)",
    "packages/core/processing/image_ocr.py (_DIAGRAM_PROMPT)",
)

# --- GUARDRAILS ---
add(
    34,
    "Refusal Templates (Guardrails)",
    "Safety refusal responses",
    "Pre-written safe refusal messages when input/output blocked (not LLM-generated).",
    (
        "Template strings per RefusalReason: INAPPROPRIATE_CONTENT, OUT_OF_SCOPE, "
        "ACADEMIC_ONLY, SAFETY_VIOLATION, PROMPT_INJECTION, PII_DETECTED, "
        "ACADEMIC_INTEGRITY, GENERAL — see refusal_templates.py for full text."
    ),
    "Input: RefusalReason + optional context. Output: safe refusal string to user.",
    "packages/core/security/refusal_templates.py; SafetyFilter; injection_detector; chat_graph",
    "packages/core/security/refusal_templates.py",
    status="Active (template strings, not LLM)",
)

def frontend_rows() -> list[dict[str, str]]:
    """User/custom_instructions builders in apps/web (not backend system prompts)."""
    fe: list[dict[str, str]] = []

    def fe_add(
        sno: int,
        agent: str,
        functionality: str,
        desc: str,
        prompt: str,
        io: str,
        deps: str,
        file_name: str,
    ) -> None:
        fe.append(
            {
                "S.no": str(sno),
                "Agent": agent,
                "Functionality": functionality,
                "Simple Description (What is the purpose)": desc,
                "System Prompt": prompt,
                "Inputs/Outputs": io,
                "Any Dependencies": deps,
                "File Name in Code Base": file_name,
                "Status": "Frontend (custom_instructions / user message)",
            }
        )

    fe_add(
        1,
        "Studio Slide Deck Instructions Builder",
        "Studio UI → custom_instructions",
        "Dynamic slide-deck rules sent as custom_instructions before backend Jinja runs.",
        "See buildSlideDeckInstructions() — format, audience, tone, length, language, bullets, story arc, topic focus.",
        "Input: SlideDeckSpec. Output: custom_instructions on POST /api/v1/studio/generate.",
        "StudioGenerationContext; apiClient.generateStudio",
        "apps/web/src/components/studio/StudioSuite.tsx (buildSlideDeckInstructions)",
    )
    fe_add(
        2,
        "Studio Quiz Instructions Builder",
        "Studio UI → custom_instructions",
        "Quiz count, difficulty, topic-focus rules for studio generation.",
        "See buildQuizInstructions() — question count range, difficulty, topic/scope, JSON format.",
        "Input: QuizSpec. Output: custom_instructions.",
        "StudioSuite.tsx",
        "apps/web/src/components/studio/StudioSuite.tsx (buildQuizInstructions)",
    )
    fe_add(
        3,
        "Studio Mind Map Instructions Builder",
        "Studio UI → custom_instructions",
        "Multi-source mind-map scope rules.",
        "See buildMindMapInstructions() — single vs N sources, hub/branch structure.",
        "Input: selectedSourceCount. Output: custom_instructions.",
        "StudioSuite.tsx",
        "apps/web/src/components/studio/StudioSuite.tsx (buildMindMapInstructions)",
    )
    fe_add(
        4,
        "Studio Flashcards Instructions Builder",
        "Studio UI → custom_instructions",
        "Flashcard deck scope and coverage rules.",
        "See buildFlashcardInstructions() — front/back grounding, multi-source fairness.",
        "Input: selectedSourceCount. Output: custom_instructions.",
        "StudioSuite.tsx",
        "apps/web/src/components/studio/StudioSuite.tsx (buildFlashcardInstructions)",
    )
    fe_add(
        5,
        "Studio Selection Context Instruction",
        "Selection-only studio generation",
        "Restricts studio generation to highlighted chat excerpt.",
        "Use only the excerpt below as factual context. Do not rely on other chat or documents.",
        "Input: selectionText. Output: custom_instructions + selection_text, context_mode=selection_only.",
        "NotebookChatSelectionPopover; ChatStudioSelectionToolbar",
        "apps/web/src/components/chat/NotebookChatSelectionPopover.tsx; ChatStudioSelectionToolbar.tsx",
    )
    fe_add(
        6,
        "Chat Post-Upload Summary Trigger",
        "Auto whole-file summary",
        "User message auto-sent after source ingestion to trigger map-reduce.",
        "Summarize the entire document I just added.",
        "Input: new sourceId. Output: POST /api/v1/chat/stream with force_whole_file_map_reduce.",
        "ChatInterface.tsx",
        "apps/web/src/components/chat/ChatInterface.tsx (POST_UPLOAD_SUMMARY_PROMPT)",
    )
    fe_add(
        7,
        "Chat Suggestion Chip Templates",
        "Notebook chat starters",
        "Pre-filled user messages for main-topics and summarize chips.",
        "What are the main topics covered in {sources}? / Summarize the key points from {sources}.",
        "Input: source titles/count. Output: message to chat stream.",
        "ChatInput.tsx; overridden by tutorSuggestions from API when present",
        "apps/web/src/components/chat/ChatInput.tsx",
    )
    fe_add(
        8,
        "Problem Solver Checkpoint Fallbacks",
        "UI-only MCQ labels",
        "Fallback checkpoint prompt text when API omits prompt field.",
        "Which idea should we use first? / Which equation should we use next?",
        "Input: partial checkpoint from API. Output: normalized UI object.",
        "problem-solver-utils.ts",
        "apps/web/src/lib/problem-solver-utils.ts",
    )
    return fe


fieldnames = [
    "S.no",
    "Agent",
    "Functionality",
    "Simple Description (What is the purpose)",
    "System Prompt",
    "Inputs/Outputs",
    "Any Dependencies",
    "File Name in Code Base",
    "Status",
]

out_path = ROOT / "Current_System_Prompts.csv"
with out_path.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
    writer.writeheader()
    writer.writerows(rows)

fe_rows = frontend_rows()
fe_path = ROOT / "Frontend_Instruction_Builders.csv"
with fe_path.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
    writer.writeheader()
    writer.writerows(fe_rows)

try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    header_fill = PatternFill("solid", fgColor="1F4E79")
    header_font = Font(bold=True, color="FFFFFF")
    widths = [6, 28, 22, 36, 80, 40, 45, 55, 22]

    for sheet_name, sheet_rows in (
        ("Backend System Prompts", rows),
        ("Frontend Instruction Builders", fe_rows),
    ):
        ws = wb.active if sheet_name == "Backend System Prompts" else wb.create_sheet(sheet_name)
        if sheet_name == "Backend System Prompts":
            ws.title = sheet_name
        for c, h in enumerate(fieldnames, 1):
            cell = ws.cell(row=1, column=c, value=h)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(wrap_text=True, vertical="top")
        for r, row in enumerate(sheet_rows, 2):
            for c, h in enumerate(fieldnames, 1):
                cell = ws.cell(row=r, column=c, value=row.get(h, ""))
                cell.alignment = Alignment(wrap_text=True, vertical="top")
        for i, w in enumerate(widths[: len(fieldnames)], 1):
            ws.column_dimensions[get_column_letter(i)].width = w
        ws.freeze_panes = "A2"

    xlsx_path = ROOT / "Current_System_Prompts.xlsx"
    wb.save(xlsx_path)
    print(f"Wrote {xlsx_path}")
except ImportError:
    print("openpyxl not installed; skipped XLSX")

print(f"Wrote {len(rows)} backend rows to {out_path}")
print(f"Wrote {len(fe_rows)} frontend rows to {fe_path}")
