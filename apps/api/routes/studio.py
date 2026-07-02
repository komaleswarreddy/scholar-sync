# app/api/v1/endpoints/studio.py

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import traceback
import json
import uuid

from packages.core.database.connection import get_db
from packages.core.database.models.source import Source
from packages.core.services.studio_service import StudioService
from packages.core.monitoring.pipeline_trace import get_pipeline_trace_store
from apps.api.schemas.studio import StudioRequest
from apps.api.utils.safe_errors import safe_detail

router = APIRouter()


async def _validate_studio_source_ids(
    db: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
    source_ids: List[str],
) -> List[str]:
    """Ensure requested sources belong to the authenticated user (STU / GEN-10 guardrail)."""
    requested_uuid_ids = []
    for sid in source_ids or []:
        try:
            requested_uuid_ids.append(uuid.UUID(str(sid)))
        except (ValueError, TypeError, AttributeError):
            continue
    if not requested_uuid_ids:
        return []
    tenant_uuid = uuid.UUID(str(tenant_id))
    result = await db.execute(
        select(Source.id).where(
            Source.tenant_id == tenant_uuid,
            Source.user_id == str(user_id),
            Source.id.in_(requested_uuid_ids),
        )
    )
    allowed = set(result.scalars().all())
    validated = [str(sid) for sid in requested_uuid_ids if sid in allowed]
    if not validated:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Access denied",
                "message": "No selected sources are accessible for this user.",
            },
        )
    return validated

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
        print(f"[STUDIO ENDPOINT] context_mode={getattr(request_body, 'context_mode', 'sources_only')}")
        print(f"[STUDIO ENDPOINT] Source IDs: {request_body.source_ids}")
        print(f"[STUDIO ENDPOINT] Source IDs count: {len(request_body.source_ids) if request_body.source_ids else 0}")
        
        validated_source_ids = list(request_body.source_ids or [])
        if request_body.source_ids and user_id:
            validated_source_ids = await _validate_studio_source_ids(
                db,
                tenant_id=str(tenant_id),
                user_id=str(user_id),
                source_ids=list(request_body.source_ids),
            )

        service = StudioService(db, tenant_id, user_id)

        trace_id = str(uuid.uuid4())
        store = get_pipeline_trace_store()
        store.start_trace(trace_id, str(tenant_id), str(user_id or ""))
        success = False
        try:
            result = await service.generate(
                task_type=request_body.task_type,
                source_ids=validated_source_ids,
                custom_instructions=request_body.custom_instructions,
                retrieval_focus=request_body.retrieval_focus,
                context_mode=request_body.context_mode,
                chat_transcript=request_body.chat_transcript,
                selection_text=request_body.selection_text,
                include_ncert_global=bool(request_body.include_ncert_global),
                ncert_class=request_body.ncert_class,
                ncert_subject=request_body.ncert_subject,
                ncert_chapter_no=request_body.ncert_chapter_no,
                ncert_chapter_name=request_body.ncert_chapter_name,
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
        # JSON parsing errors — log detail, return generic message.
        raise HTTPException(
            status_code=500,
            detail=safe_detail(e, "Failed to parse AI response"),
        )
    except Exception as e:
        # Log the full error for debugging (handled inside safe_detail).
        error_msg = str(e)
        # Configuration problems must NOT echo provider/API-key text to the client.
        if "API key" in error_msg or "not configured" in error_msg:
            safe_detail(e, "Studio configuration error")
            raise HTTPException(
                status_code=400,
                detail="Server configuration error. Please contact an administrator.",
            )
        raise HTTPException(
            status_code=500,
            detail=safe_detail(e, f"Failed to generate {request_body.task_type}"),
        )
