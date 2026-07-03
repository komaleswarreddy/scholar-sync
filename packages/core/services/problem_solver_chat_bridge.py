"""Bridge Problem Solver sessions to Chat/Message rows for IIL feedback."""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.database.models.chat import Chat, Message
from packages.core.database.models.problem_solver import ProblemSolverSession
from packages.core.database.models.problem_solver_chat import ProblemSolverSessionChat
from packages.core.iil.pipeline_hook import schedule_interaction_log
from packages.core.iil.trace_payload import PipelineTracePayload


def _response_to_markdown(response: Dict[str, Any]) -> str:
    parts: list[str] = []
    title = response.get("title")
    if title:
        parts.append(f"## {title}")
    for section in response.get("sections") or []:
        if not isinstance(section, dict):
            continue
        heading = section.get("heading")
        body = section.get("bodyMarkdown") or section.get("body") or ""
        if heading:
            parts.append(f"### {heading}")
        if body:
            parts.append(str(body))
    final_answer = response.get("finalAnswer")
    if final_answer:
        parts.append(f"**Final answer:** {final_answer}")
    return "\n\n".join(parts).strip()


async def ensure_session_chat(
    db: AsyncSession,
    session: ProblemSolverSession,
    *,
    tenant_id: str,
    user_id: str,
) -> Chat:
    """Return linked Chat for a problem solver session, creating if needed."""
    link_result = await db.execute(
        select(ProblemSolverSessionChat).where(
            ProblemSolverSessionChat.session_id == session.id,
        )
    )
    link = link_result.scalar_one_or_none()
    if link:
        chat_result = await db.execute(select(Chat).where(Chat.id == link.chat_id))
        chat = chat_result.scalar_one_or_none()
        if chat:
            return chat

    chat = Chat(
        tenant_id=uuid.UUID(tenant_id),
        user_id=user_id,
        notebook_id=session.notebook_id,
        title=(session.problem_text_normalized or session.problem_text or "Problem Solver")[:80],
    )
    db.add(chat)
    await db.flush()
    db.add(
        ProblemSolverSessionChat(
            session_id=session.id,
            chat_id=chat.id,
        )
    )
    await db.flush()
    return chat


async def persist_ps_assistant_turn(
    db: AsyncSession,
    session: ProblemSolverSession,
    response: Dict[str, Any],
    *,
    tenant_id: str,
    user_id: str,
) -> Optional[Message]:
    """Persist PS mode response as assistant Message and schedule InteractionLog."""
    content = _response_to_markdown(response)
    if not content:
        return None

    chat = await ensure_session_chat(db, session, tenant_id=tenant_id, user_id=user_id)
    message = Message(
        chat_id=chat.id,
        role="assistant",
        content=content,
        citations=[],
    )
    db.add(message)
    await db.flush()

    schedule_interaction_log(
        str(message.id),
        tenant_id,
        user_id,
        trace=PipelineTracePayload(
            query_text=session.problem_text_normalized or session.problem_text or "",
            notebook_id=str(session.notebook_id),
            response_token_count=len(content.split()),
            grounding_mode="problem_solver",
        ),
    )
    response["assistant_message_id"] = str(message.id)
    return message
