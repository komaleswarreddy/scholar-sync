# app/api/v1/endpoints/studio.py

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
import traceback
import json

from app.core.database import get_db
from app.services.studio import StudioService
from app.schemas.studio import StudioRequest

router = APIRouter()

@router.post("/generate")
async def generate_studio_content(
    request_body: StudioRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        tenant_id = request.state.tenant_id
        user_id = getattr(request.state, 'user_id', None)
        print(f"[STUDIO ENDPOINT] Generating {request_body.task_type} for tenant {tenant_id}, user {user_id}")
        print(f"[STUDIO ENDPOINT] Source IDs: {request_body.source_ids}")
        
        service = StudioService(db, tenant_id, user_id)

        result = await service.generate(
            task_type=request_body.task_type,
            source_ids=request_body.source_ids,
            custom_instructions=request_body.custom_instructions,
        )

        print(f"[STUDIO ENDPOINT] Generation successful, result keys: {list(result.keys()) if isinstance(result, dict) else 'not a dict'}")
        return JSONResponse(content=result)
    except ValueError as e:
        # API key configuration errors
        error_msg = str(e)
        print(f"[STUDIO ENDPOINT] ValueError: {error_msg}")
        raise HTTPException(status_code=400, detail=error_msg)
    except json.JSONDecodeError as e:
        # JSON parsing errors
        error_msg = f"Failed to parse AI response as JSON: {str(e)}"
        print(f"[STUDIO ENDPOINT] JSONDecodeError: {error_msg}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_msg)
    except Exception as e:
        # Log the full error for debugging
        error_type = type(e).__name__
        error_msg = str(e)
        print(f"[STUDIO ENDPOINT] Error: {error_type}: {error_msg}")
        print(traceback.format_exc())
        # Return user-friendly error message with more context
        if "API key" in error_msg or "not configured" in error_msg:
            raise HTTPException(
                status_code=400,
                detail=f"Configuration error: {error_msg}. Please check your API keys in the backend .env file."
            )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate {request_body.task_type}: {error_msg}"
        )
