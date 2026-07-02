"""
Shared helpers for formatting chat history into LLM prompts (retrieval agents).
"""

from typing import Any, Dict, List, Optional, Tuple

_ROLE_LABELS = {"user": "User", "assistant": "Assistant", "system": "System"}


def format_conversation_transcript(
    messages: Optional[List[Dict[str, Any]]],
    *,
    max_messages: int = 12,
    max_chars_per_message: int = 1200,
) -> str:
    """
    Build a compact transcript for retrieval agents (user + assistant + system).

    Uses the last `max_messages` turns, trims each message body for token safety.
    """
    if not messages:
        return ""
    tail = messages[-max_messages:]
    lines: List[str] = []
    for msg in tail:
        role = str(msg.get("role") or "user").lower()
        label = _ROLE_LABELS.get(role, role)
        content = msg.get("content", "")
        if content is None:
            content = ""
        text = str(content).strip()
        if not text:
            continue
        if len(text) > max_chars_per_message:
            text = text[: max_chars_per_message - 3] + "..."
        lines.append(f"{label}: {text}")
    return "\n".join(lines)


def _is_rolling_summary_message(msg: Dict[str, Any]) -> bool:
    """Backward-compatible alias."""
    return is_rolling_summary_message(msg)


def is_rolling_summary_message(msg: Dict[str, Any]) -> bool:
    """True for ChatSummarizer-injected system summary rows."""
    if not isinstance(msg, dict):
        return False
    if msg.get("is_summary"):
        return True
    role = str(msg.get("role", "")).lower()
    content = (msg.get("content") or "").lower()
    return role == "system" and "previous conversation summary" in content


def extract_rolling_chat_summary(messages: Optional[List[Dict[str, Any]]]) -> str:
    """Concatenate rolling summary text from memory pruning / ChatSummarizer."""
    if not messages:
        return ""
    parts: List[str] = []
    for msg in messages:
        if _is_rolling_summary_message(msg):
            t = (msg.get("content") or "").strip()
            if t:
                parts.append(t)
    return "\n\n".join(parts).strip()


def split_summary_and_transcript_for_prompt(
    messages: Optional[List[Dict[str, Any]]],
    *,
    max_messages: int = 16,
    max_chars_per_message: int = 900,
) -> Tuple[str, str]:
    """
    Rolling summary (if any) separate from user/assistant transcript to avoid duplication in the prompt.
    """
    summary = extract_rolling_chat_summary(messages)
    filtered = [m for m in (messages or []) if not _is_rolling_summary_message(m)]
    transcript = format_conversation_transcript(
        filtered,
        max_messages=max_messages,
        max_chars_per_message=max_chars_per_message,
    )
    return summary, (transcript or "").strip()


def format_routing_hints_section(
    *,
    scope: Optional[str] = None,
    requires_retrieval: Optional[bool] = None,
    requires_attachment: Optional[bool] = None,
) -> str:
    """Advisory routing hints from IntentClassifier for retrieval agents (prompt-only)."""
    lines: List[str] = []
    scope_s = (scope or "").strip().lower()
    if scope_s and scope_s != "unspecified":
        lines.append(f"- Retrieval scope hint: `{scope_s}`")
    if requires_retrieval is not None:
        lines.append(
            f"- Requires source retrieval: `{'yes' if requires_retrieval else 'no'}` "
            "(advisory — optimize queries accordingly; do not refuse to rewrite)."
        )
    if requires_attachment is not None:
        lines.append(
            f"- User expects attached sources: `{'yes' if requires_attachment else 'no'}` "
            "(advisory — prefer source-grounded phrasing when yes)."
        )
    if not lines:
        return ""
    return "## Routing hints (from intent classifier — advisory only)\n" + "\n".join(lines) + "\n\n"
