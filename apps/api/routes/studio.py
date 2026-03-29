# app/api/v1/endpoints/studio.py

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.ext.asyncio import AsyncSession
import traceback
import json
import uuid

from packages.core.database.connection import get_db
from packages.core.services.studio_service import StudioService
from packages.core.monitoring.pipeline_trace import get_pipeline_trace_store
from apps.api.schemas.studio import StudioRequest

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
        print(f"[STUDIO ENDPOINT] Source IDs count: {len(request_body.source_ids) if request_body.source_ids else 0}")
        
        # Additional validation
        if not request_body.source_ids or len(request_body.source_ids) == 0:
            raise HTTPException(
                status_code=400,
                detail="At least one source ID is required. Please select at least one source document."
            )
        
        service = StudioService(db, tenant_id, user_id)

        trace_id = str(uuid.uuid4())
        store = get_pipeline_trace_store()
        store.start_trace(trace_id, str(tenant_id), str(user_id or ""))
        success = False
        try:
            result = await service.generate(
                task_type=request_body.task_type,
                source_ids=request_body.source_ids,
                custom_instructions=request_body.custom_instructions,
                retrieval_focus=request_body.retrieval_focus,
                report_format=request_body.report_format,
            )
            success = True
            payload = dict(result) if isinstance(result, dict) else {"result": result}
            payload["trace_id"] = trace_id
            print(
                f"[STUDIO ENDPOINT] Generation successful, result keys: {list(payload.keys())}"
            )
            print(
                f"[PIPELINE_TRACE] studio trace_id={trace_id} "
                f"(analytics/pipeline?trace_id={trace_id})"
            )
            return JSONResponse(content=payload)
        finally:
            store.finalize_trace(trace_id, success=success)
    except HTTPException:
        # Re-raise HTTPException as-is (FastAPI will handle it)
        raise
    except RequestValidationError as e:
        # Pydantic validation errors (FastAPI returns 422, but we'll handle it here for logging)
        error_details = e.errors()
        error_msg = f"Validation error: {json.dumps(error_details, indent=2)}"
        print(f"[STUDIO ENDPOINT] RequestValidationError: {error_msg}")
        print(f"[STUDIO ENDPOINT] Request body received: task_type={getattr(request_body, 'task_type', 'N/A')}, source_ids={getattr(request_body, 'source_ids', 'N/A')}")
        # Extract user-friendly message
        if error_details:
            first_error = error_details[0]
            field = first_error.get('loc', ['unknown'])[-1]
            message = first_error.get('msg', 'Validation failed')
            user_msg = f"Invalid request: {field} - {message}"
        else:
            user_msg = "Invalid request format. Please check your request parameters."
        # Re-raise as 422 (FastAPI standard for validation errors)
        raise HTTPException(status_code=422, detail=user_msg)
    except ValueError as e:
        # API key configuration errors or content validation errors
        error_msg = str(e)
        print(f"[STUDIO ENDPOINT] ValueError: {error_msg}")
        print(f"[STUDIO ENDPOINT] ValueError traceback: {traceback.format_exc()}")
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
