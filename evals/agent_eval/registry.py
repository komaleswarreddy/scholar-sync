"""Agent registry: dataset paths, evaluator modules, judge requirements."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "evals" / "datasets" / "prompt_tiered" / "manifest.json"
EVALUATORS_DIR = ROOT / "evals" / "datasets" / "final_Evalutors"
PROMPT_VERSIONS_DIR = Path(__file__).resolve().parent / "prompt_versions"

# xlsx "Agent" column -> dataset_id
XLSX_AGENT_NAME_TO_ID: Dict[str, str] = {
    "Query Rewriter Agent": "query_rewriter",
    "Query Decomposer Agent": "query_decomposer",
    "Scope Narrower Agent": "scope_narrower",
    "Chat Policy Block (YAML)": "chat_policy_block",
    "Direct Chat Agent (ScholarSync)": "direct_chat",
    "RAG Chat Response Generator": "rag_chat_response_generator",
    "Chat Summarizer Agent": "chat_summarizer",
    "Hallucination Guard Retry Suffix": "hallucination_guard_retry",
    "Studio System Prompt (JSON tasks)": "studio_system_json",
    "Studio Quiz Generator": "studio_quiz",
    "Studio Flashcards Generator": "studio_flashcards",
    "Studio Mind Map Generator": "studio_mind_map",
    "Studio Slide Deck Generator": "studio_slide_deck",
    "Studio Fallback Task Prompt (Legacy)": "studio_fallback_legacy",
    "Problem DNA Analyzer": "problem_dna_analyzer",
    "Explain From Basics Coach": "explain_from_basics",
    "Show Best Approach Coach": "show_best_approach",
    "Show Missing Idea Coach": "show_missing_idea",
    "Help Me Solve It Coach": "help_me_solve_it",
    "Problem Solver Follow-up Handler": "problem_solver_followup",
    "Tutor Notebook Bootstrap Agent": "tutor_notebook_bootstrap",
    "Tutor Follow-up Questions Agent": "tutor_follow_up_questions",
    "Source Question Extraction Agent": "source_question_extraction",
    "Image OCR Agent": "image_ocr",
    "Diagram Label OCR Agent": "diagram_label_ocr",
    "Document Sketch Agent": "document_sketch",
    "NCERT Document Sketch Agent": "ncert_document_sketch",
    "Chunk Contextualization Agent": "chunk_contextualization",
    "Whole File Map Summarizer": "whole_file_map_summarizer",
    "Whole File Reduce Agent": "whole_file_reduce",
}

AGENT_EVALUATOR_FILES: Dict[str, str] = {
    "query_rewriter": "query_rewriter.py",
    "query_decomposer": "query_decomposer.py",
    "scope_narrower": "scope_narrower.py",
    "chat_policy_block": "chat_policy_block_evaluators.py",
    "direct_chat": "direct_chat_evaluators.py",
    "rag_chat_response_generator": "rag_chat_response_generator_evaluators.py",
    "chat_summarizer": "chat_summarizer_evaluators.py",
    "hallucination_guard_retry": "hallucination_guard_retry_evaluators.py",
    "studio_system_json": "studio_system_json_evaluators.py",
    "studio_quiz": "studio_quiz_evaluators.py",
    "studio_flashcards": "studio_flashcards_evaluators.py",
    "studio_mind_map": "studio_mind_map_evaluators.py",
    "studio_slide_deck": "studio_slide_deck_evaluators.py",
    "studio_fallback_legacy": "studio_fallback_legacy_evaluators.py",
    "problem_dna_analyzer": "problem_dna_analyzer_evaluators.py",
    "explain_from_basics": "explain_from_basics_evaluators.py",
    "show_best_approach": "show_best_approach_evaluators.py",
    "show_missing_idea": "show_missing_idea_evaluators.py",
    "help_me_solve_it": "help_me_solve_it_evaluators.py",
    "problem_solver_followup": "problem_solver_followup_evaluators.py",
    "tutor_notebook_bootstrap": "tutor_notebook_bootstrap_evaluators.py",
    "tutor_follow_up_questions": "tutor_follow_up_questions_evaluators.py",
    "source_question_extraction": "source_question_extraction_evaluators.py",
    "image_ocr": "image_ocr_evaluators.py",
    "diagram_label_ocr": "diagram_label_ocr_evaluators.py",
    "document_sketch": "document_sketch_evaluators.py",
    "ncert_document_sketch": "ncert_document_sketch_evaluators.py",
    "chunk_contextualization": "chunk_contextualization_evaluators.py",
    "whole_file_map_summarizer": "whole_file_map_summarizer_evaluators.py",
    "whole_file_reduce": "whole_file_reduce_evaluators.py",
}

# Agents whose evaluator module exposes build_per_example_evaluators(judge_llm)
AGENTS_REQUIRING_JUDGE = frozenset(
    {
        "rag_chat_response_generator",
        "problem_dna_analyzer",
        "explain_from_basics",
        "show_best_approach",
        "show_missing_idea",
        "help_me_solve_it",
        "problem_solver_followup",
        "tutor_notebook_bootstrap",
        "tutor_follow_up_questions",
        "source_question_extraction",
        "whole_file_map_summarizer",
        "whole_file_reduce",
    }
)

# Fallback when xlsx has N/A models but eval still needs an LLM target
DEFAULT_FALLBACK_MODELS = [
    {"provider": "openai", "model": "gpt-5.4-mini"},
    {"provider": "anthropic", "model": "claude-haiku-4-5"},
]


@dataclass(frozen=True)
class AgentSpec:
    agent_id: str
    dataset_path: Path
    evaluator_path: Path
    prompt_dir: Path
    input_keys: List[str]
    output_keys: List[str]
    example_count: int
    requires_judge: bool
    xlsx_agent_name: str


def _load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def get_agent_spec(agent_id: str) -> AgentSpec:
    manifest = _load_manifest()
    entry = next((d for d in manifest.get("datasets") or [] if d["dataset_id"] == agent_id), None)
    if entry is None:
        raise KeyError(f"Unknown agent_id {agent_id!r}")

    evaluator_file = AGENT_EVALUATOR_FILES.get(agent_id)
    if not evaluator_file:
        raise KeyError(f"No evaluator mapping for {agent_id!r}")

    dataset_path = ROOT / entry["path"]
    ds_doc = json.loads(dataset_path.read_text(encoding="utf-8"))
    langsmith = ds_doc.get("langsmith") or {}

    xlsx_name = next((k for k, v in XLSX_AGENT_NAME_TO_ID.items() if v == agent_id), agent_id)

    return AgentSpec(
        agent_id=agent_id,
        dataset_path=dataset_path,
        evaluator_path=EVALUATORS_DIR / evaluator_file,
        prompt_dir=PROMPT_VERSIONS_DIR / agent_id,
        input_keys=list(langsmith.get("input_keys") or []),
        output_keys=list(langsmith.get("output_keys") or []),
        example_count=int(entry.get("actual_examples") or 0),
        requires_judge=agent_id in AGENTS_REQUIRING_JUDGE,
        xlsx_agent_name=xlsx_name,
    )


def list_scope_agents() -> List[str]:
    from evals.agent_eval.config import SCOPE_AGENT_IDS

    return list(SCOPE_AGENT_IDS)
