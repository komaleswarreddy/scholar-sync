"""
Validate compiled chat prompts before they are sent to the LLM.

Ensures critical instruction blocks were not stripped or corrupted during template rendering.
"""

from __future__ import annotations

from typing import Tuple

from config.settings import settings


def validate_rag_compiled_prompt(
    full_prompt: str,
    *,
    has_substantive_context: bool,
    tutor_strict_ncert_only: bool,
    chat_global_fallback: bool,
    policy_block_injected: bool,
) -> Tuple[bool, str]:
    """
    Returns (ok, failure_reason). failure_reason is a short machine-readable tag if not ok.
    """
    fp = full_prompt or ""
    if len(fp.strip()) < 80:
        return False, "compiled_prompt_too_short"

    if "## Grounding rules" not in fp and "## Retrieval pipeline" not in fp:
        return False, "missing_grounding_or_retrieval_section"

    if has_substantive_context:
        if "Context evidence" not in fp and "context evidence" not in fp.lower():
            return False, "missing_context_evidence_section"

    if tutor_strict_ncert_only and "NCERT" not in fp:
        return False, "missing_ncert_tutor_instructions"

    if chat_global_fallback and "general knowledge" not in fp.lower():
        return False, "missing_global_fallback_instructions"

    if policy_block_injected and getattr(settings, "ENABLE_CHAT_POLICY_YAML", True):
        if "Central response policy" not in fp:
            return False, "missing_central_response_policy"

    return True, ""


def validate_direct_chat_prompt(full_prompt: str) -> Tuple[bool, str]:
    fp = full_prompt or ""
    if len(fp.strip()) < 60:
        return False, "direct_chat_prompt_too_short"
    if "ScholarSync" not in fp:
        return False, "missing_scholarsync_identity"
    if "no document retrieval" not in fp.lower():
        return False, "missing_no_retrieval_instruction"
    return True, ""
