"""
Chat API Endpoints

Handles RAG-based chat with streaming responses.
Uses Gemini 1.5 Flash for context-heavy tasks.
Task C: Chat History - Save and load chat history.
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import json
import uuid

from app.core.database import get_db
from app.core.config import settings
from app.schemas.chat import (
    ChatRequest,
    ChatCreateRequest,
    ChatUpdateRequest,
    ChatResponse,
    ChatListItemResponse,
    ChatListResponse,
    MessageResponse,
    MessageCreateRequest,
)
from typing import Optional
from pydantic import BaseModel, Field
from app.services.rag import RAGService
from app.services.chat import ChatService
from app.models.chat import Chat, Message

router = APIRouter()


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

    try:
        service = RAGService(db, tenant_id, user_id)
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
            async for event in service.stream_chat(
                message=request_body.message,
                history=request_body.history,
                active_source_ids=request_body.active_source_ids,
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
    from app.core.config import settings
    
    if settings.ENVIRONMENT != "development":
        raise HTTPException(status_code=403, detail="Debug endpoint only available in development")
    
    tenant_id = request.state.tenant_id
    user_id = getattr(request.state, "user_id", None)
    
    # Get all chats for tenant (regardless of user)
    from app.models.chat import Chat
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
    chats = await service.list_chats(limit=limit, offset=offset)
    
    # If no chats found, check if there are any chats for this tenant at all
    if len(chats) == 0:
        from app.models.chat import Chat
        all_tenant_chats_result = await db.execute(
            select(Chat)
            .where(Chat.tenant_id == uuid.UUID(tenant_id))
        )
        all_tenant_chats = list(all_tenant_chats_result.scalars().all())
        if all_tenant_chats:
            print(f"[WARNING] list_chats - No chats found for user {user_id}, but {len(all_tenant_chats)} chats exist for tenant {tenant_id}")
            print(f"[WARNING] list_chats - Sample user_ids in tenant chats: {[c.user_id for c in all_tenant_chats[:5]]}")
    
    # Get message count for each chat
    chat_items = []
    for chat in chats:
        message_count_result = await db.execute(
            select(func.count(Message.id))
            .where(Message.chat_id == chat.id)
        )
        message_count = message_count_result.scalar() or 0
        
        chat_items.append(
            ChatListItemResponse(
                id=str(chat.id),
                title=chat.title,
                created_at=chat.created_at,
                message_count=message_count,
            )
        )
    
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
        
        message = await service.add_message(
            chat_id=chat_id,
            role=request_body.role,
            content=request_body.content,
            citations=citations_dict,
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


class MessageFeedbackRequest(BaseModel):
    """Request to update message feedback."""
    feedback: Optional[str] = Field(None, description="Feedback: 'thumbs_up', 'thumbs_down', or None")


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
