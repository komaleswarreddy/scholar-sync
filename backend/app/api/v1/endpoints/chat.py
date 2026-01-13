"""
Chat API Endpoints

Handles RAG-based chat with streaming responses.
Uses Gemini 1.5 Flash for context-heavy tasks.
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.core.database import get_db
from app.core.config import settings
from app.schemas.chat import ChatRequest, ChatStreamEvent
from app.services.rag import RAGService

router = APIRouter()


@router.post("/stream")
async def stream_chat(
    request_body: ChatRequest,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Stream chat response with RAG.
    
    Process:
    1. Embed user query
    2. Query Pinecone with tenant namespace and source filters
    3. Retrieve top K chunks
    4. Construct prompt with context
    5. Stream response from Gemini 1.5 Flash
    
    Returns:
        Server-Sent Events stream with chunks and citations
    """
    tenant_id = request.state.tenant_id
    user_id = request.headers.get("X-User-ID")  # From Clerk JWT
    
    # For development: use default user if not provided
    if not user_id:
        if settings.ENVIRONMENT == "development":
            user_id = "dev-user-123"
        else:
            raise HTTPException(status_code=401, detail="User ID required")
    
    service = RAGService(db, tenant_id, user_id)
    
    async def generate_stream():
        """Generator for SSE stream."""
        try:
            async for event in service.stream_chat(
                message=request_body.message,
                history=request_body.history,
                active_source_ids=request_body.active_source_ids,
            ):
                # Properly serialize data to JSON
                event_data = json.dumps(event['data'], ensure_ascii=False)
                yield f"event: {event['event']}\n"
                yield f"data: {event_data}\n\n"
        except Exception as e:
            import traceback
            print(f"❌ SSE stream error: {type(e).__name__}: {str(e)}")
            print(f"❌ Traceback: {traceback.format_exc()}")
            error_data = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"event: error\n"
            yield f"data: {error_data}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )

from fastapi import APIRouter

router = APIRouter()

@router.get("/ping")
def ping():
    return {"message": "chat route working"}

