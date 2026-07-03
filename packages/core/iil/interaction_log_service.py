"""Create and update InteractionLog records."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.database.models.chat import Chat, Message
from packages.core.database.models.iil import InteractionLog
from packages.core.database.models.user import User
from packages.core.iil.concept_mapper import map_concept_from_notebook, map_concept_from_query
from packages.core.iil.enums import default_expertise_tier_for_role
from packages.core.iil.intent_classifier import classify_query_intent
from packages.core.iil.trace_payload import PipelineTracePayload

logger = logging.getLogger(__name__)


async def _resolve_user_tier(db: AsyncSession, user_id: str) -> str:
    try:
        uid = uuid.UUID(user_id)
        result = await db.execute(select(User).where(User.id == uid))
    except ValueError:
        result = await db.execute(
            select(User).where(User.clerk_user_id == user_id).limit(1)
        )
    user = result.scalar_one_or_none()
    if user and user.expertise_tier:
        return user.expertise_tier
    if user:
        return default_expertise_tier_for_role(user.role)
    return "student"


async def _previous_log_in_chat(
    db: AsyncSession, chat_id: uuid.UUID, before_position: int
) -> Optional[InteractionLog]:
    result = await db.execute(
        select(InteractionLog)
        .where(InteractionLog.chat_id == chat_id)
        .where(InteractionLog.conversation_position < before_position)
        .order_by(InteractionLog.conversation_position.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def _compute_chain(
    concept_node_id: Optional[uuid.UUID],
    prev: Optional[InteractionLog],
) -> tuple[bool, int]:
    if prev and concept_node_id and prev.concept_node_id == concept_node_id:
        return True, (prev.chain_depth or 1) + 1
    if prev and not concept_node_id and prev.is_followup:
        return True, (prev.chain_depth or 1) + 1
    return False, 1


async def _user_query_for_message(db: AsyncSession, message: Message) -> str:
    result = await db.execute(
        select(Message)
        .where(Message.chat_id == message.chat_id)
        .where(Message.role == "user")
        .where(Message.created_at <= message.created_at)
        .order_by(Message.created_at.desc())
        .limit(1)
    )
    user_msg = result.scalar_one_or_none()
    return (user_msg.content if user_msg else "") or ""


async def create_interaction_log(
    db: AsyncSession,
    *,
    message_id: str,
    tenant_id: str,
    user_id: str,
    trace: PipelineTracePayload,
) -> Optional[InteractionLog]:
    """Create InteractionLog for an assistant message."""
    try:
        msg_uuid = uuid.UUID(message_id)
        tenant_uuid = uuid.UUID(tenant_id)
    except ValueError:
        logger.warning("IIL: invalid message_id or tenant_id")
        return None

    existing = await db.execute(
        select(InteractionLog).where(InteractionLog.message_id == msg_uuid)
    )
    if existing.scalar_one_or_none():
        return None

    result = await db.execute(
        select(Message).where(Message.id == msg_uuid, Message.role == "assistant")
    )
    message = result.scalar_one_or_none()
    if not message:
        return None

    chat_result = await db.execute(select(Chat).where(Chat.id == message.chat_id))
    chat = chat_result.scalar_one_or_none()
    if not chat:
        return None

    pos_result = await db.execute(
        select(Message)
        .where(Message.chat_id == message.chat_id, Message.role == "assistant")
        .order_by(Message.created_at.asc())
    )
    assistant_msgs = pos_result.scalars().all()
    conversation_position = 1
    for i, m in enumerate(assistant_msgs, start=1):
        if m.id == message.id:
            conversation_position = i
            break

    query_text = trace.query_text or await _user_query_for_message(db, message)
    notebook_id = trace.notebook_id or (str(chat.notebook_id) if chat.notebook_id else None)

    concept_id = None
    if trace.concept_node_id:
        try:
            concept_id = uuid.UUID(trace.concept_node_id)
        except ValueError:
            concept_id = None
    if concept_id is None:
        concept_id = await map_concept_from_notebook(db, notebook_id)
    if concept_id is None:
        concept_id = await map_concept_from_query(db, query_text)

    prev = await _previous_log_in_chat(db, message.chat_id, conversation_position)
    is_followup, chain_depth = _compute_chain(concept_id, prev)

    user_tier = await _resolve_user_tier(db, user_id)
    query_intent = trace.classified_intent
    if not query_intent:
        query_intent = await classify_query_intent(query_text)

    nb_uuid = None
    if notebook_id:
        try:
            nb_uuid = uuid.UUID(notebook_id)
        except ValueError:
            nb_uuid = chat.notebook_id

    log = InteractionLog(
        message_id=msg_uuid,
        chat_id=message.chat_id,
        notebook_id=nb_uuid,
        user_id=user_id,
        user_tier=user_tier,
        tenant_id=tenant_uuid,
        query_text=query_text,
        query_intent=query_intent,
        concept_node_id=concept_id,
        conversation_position=conversation_position,
        is_followup=is_followup,
        chain_depth=chain_depth,
        chunks_retrieved=trace.chunks_retrieved or [],
        retrieval_strategy=trace.retrieval_strategy,
        kb_hit=trace.kb_hit,
        derived_hit=trace.derived_hit,
        fallback_triggered=trace.fallback_triggered,
        response_token_count=trace.response_token_count,
        citations_count=trace.citations_count,
        grounding_mode=trace.grounding_mode,
        out_of_kb_indicator=trace.out_of_kb_indicator,
        latency_ms=trace.latency_ms,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


def trace_from_debug(debug_trace: Optional[Dict[str, Any]], **kwargs: Any) -> PipelineTracePayload:
    """Build PipelineTracePayload from LangGraph/RAG debug_trace dict."""
    chunks: List[Dict[str, Any]] = []
    if debug_trace:
        final = debug_trace.get("final_chunks_sent_to_llm") or {}
        ids = final.get("ids") or debug_trace.get("after_rerank", {}).get("ids") or []
        scores = debug_trace.get("after_rerank", {}).get("scores") or []
        for i, cid in enumerate(ids):
            score = scores[i] if i < len(scores) else None
            chunks.append({
                "chunk_id": str(cid),
                "source_id": None,
                "relevance_score": score,
                "source_type": "kb",
            })
    return PipelineTracePayload(
        query_text=kwargs.get("query_text") or (debug_trace or {}).get("original_query") or "",
        chunks_retrieved=chunks,
        retrieval_strategy=kwargs.get("retrieval_strategy") or "hybrid",
        kb_hit=bool(chunks),
        derived_hit=kwargs.get("derived_hit", False),
        fallback_triggered=kwargs.get("fallback_triggered", False),
        response_token_count=kwargs.get("response_token_count", 0),
        citations_count=kwargs.get("citations_count", 0),
        grounding_mode=kwargs.get("grounding_mode", "strict"),
        out_of_kb_indicator=kwargs.get("out_of_kb_indicator", False),
        latency_ms=kwargs.get("latency_ms", 0),
        classified_intent=kwargs.get("classified_intent") or (debug_trace or {}).get("detected_intent"),
        concept_node_id=kwargs.get("concept_node_id"),
        notebook_id=kwargs.get("notebook_id"),
    )
