"""
Studio API Endpoints

Handles generative tasks (quiz, flashcards, mind maps, etc.).
Routes to optimal model based on task type (Smart Router).
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.studio import StudioRequest
from app.services.studio import StudioService

router = APIRouter()


@router.post("/generate")
async def generate_studio_content(
    request_body: StudioRequest,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate Studio content based on task type.
    
    Smart Routing:
    - quiz, flashcards, mind_map, slide_deck -> GPT-4o-mini (structured output)
    - report, infographic -> Gemini 1.5 Flash (content-heavy)
    
    Returns:
        JSON response with generated content
    """
    tenant_id = request.state.tenant_id
    
    service = StudioService(db, tenant_id)
    
    result = await service.generate(
        task_type=request_body.task_type,
        source_ids=request_body.source_ids,
        custom_instructions=request_body.custom_instructions,
    )
    
    return JSONResponse(content=result)


