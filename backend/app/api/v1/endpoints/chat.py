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
from app.schemas.chat import ChatRequest
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
    """
    tenant_id = request.state.tenant_id
    user_id = getattr(request.state, "user_id", None)

    # User ID should already be set by middleware (from JWT token or dev fallback)
    if not user_id:
        # This should rarely happen as middleware handles it, but keep as safety check
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
                event_data = json.dumps(event['data'], ensure_ascii=False)
                yield f"event: {event['event']}\n"
                yield f"data: {event_data}\n\n"
        except Exception as e:
            import traceback
            print(f"[ERROR] SSE stream error: {type(e).__name__}: {str(e)}")
            print(traceback.format_exc())
            error_data = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"event: error\n"
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/ping")
def ping():
    return {"message": "chat route working"}
