"""
Chat API Endpoints

Handles RAG-based chat with streaming responses.
Uses Gemini 1.5 Flash for context-heavy tasks.
Task C: Chat History - Save and load chat history.
"""

from fastapi import APIRouter, Depends, Request, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError, OperationalError
import asyncio
import json
import uuid

from packages.core.database.connection import get_db
from config.settings import settings
from apps.api.schemas.chat import (
    ChatRequest,
    ChatCreateRequest,
    ChatUpdateRequest,
    ChatResponse,
    ChatListItemResponse,
    ChatListResponse,
    MessageResponse,
    MessageCreateRequest,
)
from typing import List, Optional
from pydantic import BaseModel, Field
from packages.core.services.chat_service import ChatService
from packages.core.database.models.chat import Chat
from packages.core.database.models.source import Source
from packages.core.database.models.ncert_global import NcertGlobalDocument
from packages.core.langgraph.chat_graph import LangGraphChatPipeline
from packages.core.services.ncert_global_service import load_ncert_subjects_by_class

router = APIRouter()

from packages.core.memory.chat_summary_button import (
    CHAT_SUMMARY_PREFIX as _CHAT_SUMMARY_PREFIX,
    filter_out_prior_summaries,
    format_conversation_lines,
)


@router.get("/ncert-filters")
async def get_ncert_filters(
    request: Request,
    db: AsyncSession = Depends(get_db),
    class_num: Optional[int] = Query(None, ge=6, le=10),
    subject: Optional[str] = Query(None),
):
    """Return available NCERT tutor filters for class / subject / chapter selectors."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID required")

    fallback_subjects = await asyncio.to_thread(load_ncert_subjects_by_class)
    result = {
        "classes": [6, 7, 8, 9, 10],
        "subjects_by_class": {
            str(int(k)): [str(v).strip().lower() for v in vals]
            for k, vals in (fallback_subjects or {}).items()
        },
        "chapters": [],
    }

    try:
        namespace = getattr(settings, "NCERT_GLOBAL_PINECONE_NAMESPACE", "NcertDataGlobal")
        normalized_subject = (subject or "").strip().lower() or None

        subject_stmt = select(
            NcertGlobalDocument.class_num,
            NcertGlobalDocument.subject,
        ).where(
            NcertGlobalDocument.pinecone_namespace == namespace,
            NcertGlobalDocument.status.in_(("indexed", "completed")),
        )

        subject_rows = (
            await asyncio.wait_for(db.execute(subject_stmt), timeout=8.0)
        ).all()
        subjects_by_class = {str(c): [] for c in result["classes"]}
        for class_value, subject_value in subject_rows:
            class_key = str(int(class_value))
            subject_slug = str(subject_value or "").strip().lower()
            if class_key in subjects_by_class and subject_slug:
                subjects_by_class[class_key].append(subject_slug)
        for class_key in list(subjects_by_class.keys()):
            deduped = sorted(set(subjects_by_class[class_key]))
            if deduped:
                subjects_by_class[class_key] = deduped
        if any(subjects_by_class.values()):
            result["subjects_by_class"] = subjects_by_class

        if class_num is not None or normalized_subject:
            chapter_stmt = select(
                NcertGlobalDocument.chapter_no,
                NcertGlobalDocument.chapter_name,
                NcertGlobalDocument.title,
            ).where(
                NcertGlobalDocument.pinecone_namespace == namespace,
                NcertGlobalDocument.status.in_(("indexed", "completed")),
            )
            if class_num is not None:
                chapter_stmt = chapter_stmt.where(NcertGlobalDocument.class_num == class_num)
            if normalized_subject:
                chapter_stmt = chapter_stmt.where(NcertGlobalDocument.subject == normalized_subject)

            chapter_rows = (
                await asyncio.wait_for(db.execute(chapter_stmt), timeout=8.0)
            ).all()
            chapters = []
            seen = set()
            for chapter_no, chapter_name, title in chapter_rows:
                key = (
                    int(chapter_no) if chapter_no is not None else None,
                    str(chapter_name or "").strip().lower(),
                    str(title or "").strip().lower(),
                )
                if key in seen:
                    continue
                seen.add(key)
                chapters.append(
                    {
                        "chapter_no": int(chapter_no) if chapter_no is not None else None,
                        "chapter_name": str(chapter_name or "").strip() or None,
                        "title": str(title or "").strip() or None,
                    }
                )

            chapters.sort(
                key=lambda item: (
                    item["chapter_no"] is None,
                    item["chapter_no"] if item["chapter_no"] is not None else 10**9,
                    (item["chapter_name"] or item["title"] or "").lower(),
                )
            )
            result["chapters"] = chapters
    except Exception as exc:
        print(f"[NCERT_FILTERS] Falling back to static tutor filters: {type(exc).__name__}: {exc}")

    return result


@router.post("/stream")
async def stream_chat(
    request_body: ChatRequest,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Stream chat response with RAG.
    """
    tenant_id = request.state.tenant_id
    user_id = getattr(request.state, "user_id", None)

    # User ID should already be set by middleware (from JWT token or dev fallback)
    if not user_id:
        # This should rarely happen as middleware handles it, but keep as safety check
        raise HTTPException(status_code=401, detail="User ID required")
    
    include_ncert = bool(getattr(request_body, "include_ncert_global", False)) and getattr(
        settings, "ENABLE_NCERT_GLOBAL_IN_CHAT", False
    )
    
    # DEBUG: Log checkbox state received from frontend
    print(f"[API_CHAT_STREAM] include_ncert_global from request={getattr(request_body, 'include_ncert_global', False)}")
    print(f"[API_CHAT_STREAM] ENABLE_NCERT_GLOBAL_IN_CHAT setting={getattr(settings, 'ENABLE_NCERT_GLOBAL_IN_CHAT', False)}")
    print(f"[API_CHAT_STREAM] include_ncert (final)={include_ncert}")
    print(f"[API_CHAT_STREAM] active_source_ids={request_body.active_source_ids}")
    
    # DEBUG: Log NCERT tutor mode filters if present
    if include_ncert:
        print(f"[TUTOR_MODE_REQUEST] ncert_class={request_body.ncert_class}")
        print(f"[TUTOR_MODE_REQUEST] ncert_subject={request_body.ncert_subject}")
        print(f"[TUTOR_MODE_REQUEST] ncert_chapter_no={request_body.ncert_chapter_no}")
        print(f"[TUTOR_MODE_REQUEST] ncert_chapter_name={request_body.ncert_chapter_name}")
        print(f"[TUTOR_MODE_REQUEST] query='{request_body.message[:100]}...'" if len(request_body.message) > 100 else f"[TUTOR_MODE_REQUEST] query='{request_body.message}'")

    # Require at least one of: user-selected sources OR NCERT global (when enabled).
    if (
        not request_body.active_source_ids or len(request_body.active_source_ids) == 0
    ) and not include_ncert:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "No source selected",
                "message": "Please select at least one document source before asking a question, or enable NCERT global knowledge.",
            },
        )

    # Security: active_source_ids must belong to the authenticated user (same tenant namespace).
    # This is required because Pinecone namespace is tenant-scoped; we rely on source ownership
    # (source.user_id) for per-user isolation.
    requested_source_ids = list(request_body.active_source_ids or [])
    requested_uuid_ids = []
    for sid in requested_source_ids:
        try:
            requested_uuid_ids.append(uuid.UUID(sid))
        except (ValueError, TypeError, AttributeError):
            continue

    validated_source_ids: List[str] = []
    if requested_uuid_ids:
        tenant_uuid = uuid.UUID(tenant_id)
        allowed_uuid_ids = await db.execute(
            select(Source.id)
            .where(
                Source.tenant_id == tenant_uuid,
                Source.user_id == user_id,
                Source.id.in_(requested_uuid_ids),
            )
        )
        allowed_source_uuid_set = set(allowed_uuid_ids.scalars().all())
        validated_source_ids = [str(sid) for sid in requested_uuid_ids if sid in allowed_source_uuid_set]
        if not validated_source_ids:
            raise HTTPException(
                status_code=403,
                detail={"error": "Access denied", "message": "No selected sources are accessible for this user."},
            )

    if bool(getattr(request_body, "force_whole_file_map_reduce", False)) and len(validated_source_ids) != 1:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Invalid request",
                "message": "force_whole_file_map_reduce requires exactly one selected source.",
            },
        )

    # Phase 4: Rate Limiting & Debounce
    if settings.USE_SESSION_MEMORY and settings.ENABLE_RATE_LIMITING:
        from packages.core.memory import RateLimiter
        
        # Create rate limiter (singleton pattern - could be improved with global instance)
        rate_limiter = RateLimiter(
            max_requests_per_minute=settings.RATE_LIMIT_REQUESTS_PER_MINUTE,
            debounce_seconds=settings.RATE_LIMIT_DEBOUNCE_SECONDS,
            max_requests_per_hour=500
        )
        
        rate_check = rate_limiter.check_rate_limit(user_id, request_body.message, tenant_id)
        if not rate_check["allowed"]:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "message": rate_check.get("message", "Please wait before sending another request"),
                    "retry_after": rate_check.get("retry_after", 0)
                }
            )
    
    # Track regenerate attempts if this is a regenerate (same message as last assistant message)
    # Check if this looks like a regenerate by checking history
    is_regenerate = False
    if request_body.history and len(request_body.history) >= 2:
        # If last two messages are user message followed by assistant, and current message matches last user message
        last_messages = request_body.history[-2:]
        # ChatMessage is a Pydantic model, access attributes directly
        if (last_messages[0].role == "user" and 
            last_messages[1].role == "assistant" and
            last_messages[0].content == request_body.message):
            is_regenerate = True
    
    if is_regenerate:
        from packages.core.monitoring.metrics import get_metrics_collector
        metrics = get_metrics_collector()
        # Try to get chat_id from history if available
        chat_id = None
        message_id = None
        if request_body.history:
            # ChatMessage is a Pydantic model, access attributes directly
            last_assistant = next((m for m in reversed(request_body.history) if m.role == "assistant"), None)
            if last_assistant:
                # ChatMessage doesn't have an 'id' field, so message_id will be None
                # This is fine - we're just tracking that a regenerate was attempted
                message_id = getattr(last_assistant, 'id', None)
        
        try:
            if hasattr(metrics, "record_regenerate_attempt"):
                metrics.record_regenerate_attempt(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    chat_id=chat_id,
                    message_id=message_id,
                )
        except Exception as e:
            # Analytics should never break chat streaming.
            print(f"[WARNING] Failed to record regenerate attempt metric: {e}")

    try:
        service = LangGraphChatPipeline(tenant_id=tenant_id, user_id=user_id, db=db)
    except Exception as e:
        import traceback
        error_msg = f"Failed to initialize RAG service: {str(e)}"
        print(f"[ERROR] {error_msg}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=error_msg + ". Please check API key configuration (Gemini, Pinecone)."
        )

    async def generate_stream():
        """Generator for SSE stream."""
        try:
            # Convert ChatMessage objects to dictionaries for RAG service
            history_dicts = [
                {"role": msg.role, "content": msg.content}
                for msg in request_body.history
            ]
            
            async for event in service.stream(
                message=request_body.message,
                history=history_dicts,
                active_source_ids=validated_source_ids,
                include_ncert_global=include_ncert,
                ncert_class=request_body.ncert_class,
                ncert_subject=request_body.ncert_subject,
                ncert_chapter_no=request_body.ncert_chapter_no,
                ncert_chapter_name=request_body.ncert_chapter_name,
                force_whole_file_map_reduce=bool(
                    getattr(request_body, "force_whole_file_map_reduce", False)
                ),
            ):
                try:
                    event_data = json.dumps(event['data'], ensure_ascii=False)
                    yield f"event: {event['event']}\n"
                    yield f"data: {event_data}\n\n"
                except Exception as e:
                    import traceback
                    print(f"[ERROR] Failed to serialize event: {type(e).__name__}: {str(e)}")
                    print(traceback.format_exc())
                    error_data = json.dumps({"error": "Failed to serialize event data"}, ensure_ascii=False)
                    yield f"event: error\n"
                    yield f"data: {error_data}\n\n"
                    break
        except Exception as e:
            import traceback
            print(f"[ERROR] SSE stream error: {type(e).__name__}: {str(e)}")
            print(traceback.format_exc())
            try:
                error_data = json.dumps({"error": str(e)}, ensure_ascii=False)
                yield f"event: error\n"
                yield f"data: {error_data}\n\n"
            except Exception as json_error:
                # If we can't even serialize the error, send a simple message
                print(f"[ERROR] Failed to serialize error message: {json_error}")
                yield f"event: error\n"
                yield f"data: {{\"error\": \"An error occurred during streaming\"}}\n\n"

    try:
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )
    except Exception as e:
        import traceback
        print(f"[ERROR] Failed to create streaming response: {type(e).__name__}: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start streaming: {str(e)}"
        )


@router.get("/ping")
def ping():
    return {"message": "chat route working"}


@router.get("/debug/chats")
async def debug_chats(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Debug endpoint to check chat data (development only)."""
    from config.settings import settings
    
    if settings.ENVIRONMENT != "development":
        raise HTTPException(status_code=403, detail="Debug endpoint only available in development")
    
    tenant_id = request.state.tenant_id
    user_id = getattr(request.state, "user_id", None)
    
    # Get all chats for tenant (regardless of user)
    from packages.core.database.models.chat import Chat
    result = await db.execute(
        select(Chat)
        .where(Chat.tenant_id == tenant_id)
        .order_by(Chat.created_at.desc())
        .limit(20)
    )
    all_chats = result.scalars().all()
    
    return {
        "tenant_id": str(tenant_id),
        "user_id": user_id,
        "total_chats_in_tenant": len(list(all_chats)),
        "chats": [
            {
                "id": str(chat.id),
                "user_id": chat.user_id,
                "title": chat.title,
                "created_at": str(chat.created_at),
                "matches_current_user": chat.user_id == user_id,
            }
            for chat in all_chats
        ]
    }


# Task C: Chat History Endpoints

@router.post("", response_model=ChatResponse)
async def create_chat(
    request_body: ChatCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Create a new chat session."""
    tenant_id = request.state.tenant_id
    user_id = getattr(request.state, "user_id", None)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    service = ChatService(db, tenant_id, user_id)
    chat = await service.create_chat(title=request_body.title)
    
    return ChatResponse(
        id=str(chat.id),
        title=chat.title,
        created_at=chat.created_at,
        messages=[],
    )


@router.get("", response_model=ChatListResponse)
async def list_chats(
    request: Request,
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    """List all chats for the current user."""
    tenant_id = request.state.tenant_id
    user_id = getattr(request.state, "user_id", None)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    service = ChatService(db, tenant_id, user_id)
    chats_with_counts = await service.list_chats_with_message_counts(limit=limit, offset=offset)

    chat_items = [
        ChatListItemResponse(
            id=str(chat.id),
            title=chat.title,
            created_at=chat.created_at,
            message_count=message_count,
        )
        for chat, message_count in chats_with_counts
    ]

    return ChatListResponse(chats=chat_items)


@router.get("/{chat_id}", response_model=ChatResponse)
async def get_chat(
    chat_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Get a chat with all its messages."""
    tenant_id = request.state.tenant_id
    user_id = getattr(request.state, "user_id", None)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    try:
        service = ChatService(db, tenant_id, user_id)
        chat = await service.get_chat(chat_id)
        
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        # Convert messages to response format
        messages = []
        # Handle case where chat.messages might be None or empty
        if chat.messages:
            for msg in sorted(chat.messages, key=lambda m: m.created_at):
                try:
                    # Safely get feedback - handle case where column might not exist yet
                    feedback_value = None
                    try:
                        feedback_value = getattr(msg, 'feedback', None)
                    except (AttributeError, KeyError):
                        # Column doesn't exist in database yet
                        feedback_value = None
                    
                    messages.append(
                        MessageResponse(
                            id=str(msg.id),
                            role=msg.role,
                            content=msg.content,
                            citations=msg.citations or [],
                            feedback=feedback_value,
                            created_at=msg.created_at,
                        )
                    )
                except Exception as e:
                    import traceback
                    print(f"[ERROR] Failed to convert message {msg.id if hasattr(msg, 'id') else 'unknown'}: {type(e).__name__}: {str(e)}")
                    print(traceback.format_exc())
                    # Continue with other messages even if one fails
                    continue
        
        return ChatResponse(
            id=str(chat.id),
            title=chat.title,
            created_at=chat.created_at,
            messages=messages,
        )
    except HTTPException:
        raise
    except ValueError as e:
        # Handle database schema errors (e.g., missing feedback column)
        error_msg = str(e)
        if 'database schema' in error_msg.lower() or 'feedback' in error_msg.lower():
            raise HTTPException(
                status_code=500,
                detail=error_msg
            )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        error_msg = f"Failed to get chat {chat_id}: {type(e).__name__}: {str(e)}"
        print(f"[ERROR] {error_msg}")
        print(traceback.format_exc())
        # Provide more helpful error message if it's a database column issue
        if 'feedback' in str(e).lower() or 'column' in str(e).lower() or 'does not exist' in str(e).lower():
            error_detail = f"Database schema issue: The 'feedback' column is missing from the messages table. Please run: ALTER TABLE messages ADD COLUMN IF NOT EXISTS feedback VARCHAR;"
        else:
            error_detail = str(e)
        raise HTTPException(status_code=500, detail=f"Failed to get chat: {error_detail}")


@router.patch("/{chat_id}", response_model=ChatResponse)
async def update_chat(
    chat_id: str,
    request_body: ChatUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Update chat title."""
    tenant_id = request.state.tenant_id
    user_id = getattr(request.state, "user_id", None)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    if not request_body.title:
        raise HTTPException(status_code=400, detail="Title is required")
    
    service = ChatService(db, tenant_id, user_id)
    chat = await service.update_chat_title(chat_id, request_body.title)
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # Get messages
    chat_with_messages = await service.get_chat(chat_id)
    messages = []
    for msg in sorted(chat_with_messages.messages, key=lambda m: m.created_at):
        feedback_value = getattr(msg, 'feedback', None)
        messages.append(
            MessageResponse(
                id=str(msg.id),
                role=msg.role,
                content=msg.content,
                citations=msg.citations or [],
                feedback=feedback_value,
                created_at=msg.created_at,
            )
        )
    
    return ChatResponse(
        id=str(chat.id),
        title=chat.title,
        created_at=chat.created_at,
        messages=messages,
    )


@router.delete("/{chat_id}")
async def delete_chat(
    chat_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Delete a chat and all its messages."""
    tenant_id = request.state.tenant_id
    user_id = getattr(request.state, "user_id", None)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    try:
        service = ChatService(db, tenant_id, user_id)
        deleted = await service.delete_chat(chat_id)
        
        if not deleted:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        return {"message": "Chat deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"[ERROR] Failed to delete chat {chat_id}: {type(e).__name__}: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to delete chat: {str(e)}")


@router.post("/{chat_id}/messages", response_model=MessageResponse)
async def add_message(
    chat_id: str,
    request_body: MessageCreateRequest,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """Add a message to a chat."""
    tenant_id = request.state.tenant_id
    user_id = getattr(request.state, "user_id", None)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    if request_body.role not in ['user', 'assistant']:
        raise HTTPException(status_code=400, detail="Role must be 'user' or 'assistant'")
    
    service = ChatService(db, tenant_id, user_id)
    try:
        # Convert citations to dict format for storage
        citations_dict = [
            {
                "source_id": c.source_id,
                "chunk_id": c.chunk_id,
                "text": c.text,
                "page_number": c.page_number,
                "score": c.score,
            }
            if hasattr(c, 'source_id')
            else c  # Already a dict
            for c in request_body.citations
        ]
        
        message = await asyncio.wait_for(
            service.add_message(
                chat_id=chat_id,
                role=request_body.role,
                content=request_body.content,
                citations=citations_dict,
            ),
            timeout=30.0,
        )
        
        return MessageResponse(
            id=str(message.id),
            role=message.role,
            content=message.content,
            citations=message.citations or [],
            feedback=message.feedback,
            created_at=message.created_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (OperationalError, DBAPIError, TimeoutError, asyncio.TimeoutError):
        raise HTTPException(
            status_code=503,
            detail="Message persistence unavailable (database timeout). Please retry.",
        )


class MessageFeedbackRequest(BaseModel):
    """Request to update message feedback."""
    feedback: Optional[str] = Field(None, description="Feedback: 'thumbs_up', 'thumbs_down', or None")


@router.delete("/{chat_id}/messages")
async def delete_all_messages(
    chat_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Delete all messages in a chat (used for summarization)."""
    tenant_id = request.state.tenant_id
    user_id = getattr(request.state, "user_id", None)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    service = ChatService(db, tenant_id, user_id)
    try:
        deleted_count = await service.delete_all_messages(chat_id)
        return {"message": f"Deleted {deleted_count} messages", "deleted_count": deleted_count}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        import traceback
        print(f"[ERROR] Failed to delete messages for chat {chat_id}: {type(e).__name__}: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to delete messages: {str(e)}")


@router.post("/{chat_id}/summarize", response_model=MessageResponse)
async def summarize_chat_so_far(
    chat_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Summarize all messages in the current chat and append the summary as a new assistant message.

    - Does NOT delete existing messages.
    - Repeated calls summarize the full conversation up to that point (excluding prior summary messages).
    """
    tenant_id = request.state.tenant_id
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID required")

    service = ChatService(db, tenant_id, user_id)
    chat = await service.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    msgs = list(chat.messages or [])
    pairs = [(m.role, m.content) for m in msgs]
    pairs = filter_out_prior_summaries(pairs)
    if not pairs:
        raise HTTPException(status_code=400, detail="No messages to summarize")

    # Build plain conversation transcript for LLM summarization.
    old_conversation = format_conversation_lines(pairs)

    from packages.core.prompts import load_prompt

    summary_prompt = load_prompt(
        "chat/chat_summarizer_prompt.j2",
        old_conversation=old_conversation,
    )

    try:
        from packages.core.llm import get_llm_client, get_model_for_task

        provider, model = get_model_for_task("chat")
        llm_client = get_llm_client(provider=provider, model=model, temperature=0.3)
        resp = await llm_client.generate(
            prompt=summary_prompt,
            temperature=0.3,
            max_tokens=220,
            tenant_id=tenant_id,
            user_id=user_id,
            feature_tag="chat_summarize_button",
        )
        summary = (resp.content or "").strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to summarize chat: {type(e).__name__}: {e}")

    if not summary:
        raise HTTPException(status_code=500, detail="Failed to summarize chat: empty summary")

    summary_content = f"{_CHAT_SUMMARY_PREFIX}\n\n{summary}"
    try:
        saved = await service.add_message(
            chat_id=chat_id,
            role="assistant",
            content=summary_content,
            citations=[],
        )
        return MessageResponse(
            id=str(saved.id),
            role=saved.role,
            content=saved.content,
            citations=saved.citations or [],
            feedback=saved.feedback,
            created_at=saved.created_at,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save summary message: {type(e).__name__}: {e}")


@router.patch("/messages/{message_id}/feedback", response_model=MessageResponse)
async def update_message_feedback(
    message_id: str,
    request_body: MessageFeedbackRequest,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """Update feedback for a message."""
    tenant_id = request.state.tenant_id
    user_id = getattr(request.state, "user_id", None)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID required")
    
    service = ChatService(db, tenant_id, user_id)
    try:
        message = await service.update_message_feedback(
            message_id=message_id,
            feedback=request_body.feedback,
        )
        
        if not message:
            raise HTTPException(status_code=404, detail="Message not found or access denied")
        
        return MessageResponse(
            id=str(message.id),
            role=message.role,
            content=message.content,
            citations=message.citations or [],
            feedback=message.feedback,
            created_at=message.created_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
