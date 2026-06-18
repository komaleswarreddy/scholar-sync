"""Guided Problem Solver API routes."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.schemas.problem_solver import (
    ProblemSolverCheckpointRequest,
    ProblemSolverExtractFromSourceRequest,
    ProblemSolverExtractRequest,
    ProblemSolverFollowUpRequest,
    ProblemSolverModeRequest,
    ProblemSolverSessionCreateRequest,
    ProblemSolverSessionResponse,
)
from config.settings import settings
from packages.core.database.connection import get_db
from packages.core.services.problem_solver_service import ProblemSolverService

router = APIRouter()


def _require_enabled() -> None:
    if not getattr(settings, "ENABLE_PROBLEM_SOLVER", False):
        raise HTTPException(status_code=404, detail="Problem Solver is not enabled")


def _get_context(request: Request):
    _require_enabled()
    tenant_id = getattr(request.state, "tenant_id", None)
    user_id = getattr(request.state, "user_id", None)
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Tenant context not found")
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")
    return tenant_id, user_id


@router.post("/sessions", response_model=ProblemSolverSessionResponse)
async def create_session(
    body: ProblemSolverSessionCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    tenant_id, user_id = _get_context(request)
    service = ProblemSolverService(db, str(tenant_id), user_id)
    data = await service.create_session(
        notebook_id=body.notebook_id,
        problem_text=body.problem_text,
        input_type=body.input_type,
        source_refs=body.source_refs,
    )
    return ProblemSolverSessionResponse(**data)


@router.get("/sessions/active/{notebook_id}")
async def get_active_session(
    notebook_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    tenant_id, user_id = _get_context(request)
    service = ProblemSolverService(db, str(tenant_id), user_id)
    data = await service.get_active_for_notebook(notebook_id)
    if not data:
        return JSONResponse(status_code=200, content=None)
    return ProblemSolverSessionResponse(**data)


@router.get("/sessions/{session_id}", response_model=ProblemSolverSessionResponse)
async def get_session(
    session_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    tenant_id, user_id = _get_context(request)
    service = ProblemSolverService(db, str(tenant_id), user_id)
    data = await service.get_session(session_id)
    return ProblemSolverSessionResponse(**data)


@router.post("/extract-from-source")
async def extract_from_source(
    body: ProblemSolverExtractFromSourceRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    tenant_id, user_id = _get_context(request)
    service = ProblemSolverService(db, str(tenant_id), user_id)
    normalized_text = await service.extract_text_from_source(body.source_id)
    return {"normalized_text": normalized_text}


@router.post("/sessions/{session_id}/extract", response_model=ProblemSolverSessionResponse)
async def extract_session_text(
    session_id: str,
    body: ProblemSolverExtractRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    tenant_id, user_id = _get_context(request)
    service = ProblemSolverService(db, str(tenant_id), user_id)
    data = await service.set_extracted_text(session_id, body.normalized_text)
    return ProblemSolverSessionResponse(**data)


@router.post("/sessions/{session_id}/mode", response_model=ProblemSolverSessionResponse)
async def select_mode(
    session_id: str,
    body: ProblemSolverModeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    tenant_id, user_id = _get_context(request)
    service = ProblemSolverService(db, str(tenant_id), user_id)
    data = await service.select_mode(session_id, body.solving_mode)
    return ProblemSolverSessionResponse(**data)


@router.post("/sessions/{session_id}/respond", response_model=ProblemSolverSessionResponse)
async def respond(
    session_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    tenant_id, user_id = _get_context(request)
    service = ProblemSolverService(db, str(tenant_id), user_id)
    data = await service.respond(session_id)
    return ProblemSolverSessionResponse(**data)


@router.post("/sessions/{session_id}/respond/stream")
async def respond_stream(
    session_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    tenant_id, user_id = _get_context(request)
    service = ProblemSolverService(db, str(tenant_id), user_id)

    async def generate():
        try:
            async for event in service.stream_respond(session_id):
                event_data = json.dumps(event["data"], ensure_ascii=False)
                yield f"event: {event['event']}\n"
                yield f"data: {event_data}\n\n"
        except Exception as e:
            error_data = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"event: error\n"
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.post("/sessions/{session_id}/checkpoint", response_model=ProblemSolverSessionResponse)
async def submit_checkpoint(
    session_id: str,
    body: ProblemSolverCheckpointRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    tenant_id, user_id = _get_context(request)
    service = ProblemSolverService(db, str(tenant_id), user_id)
    data = await service.submit_checkpoint(
        session_id,
        body.checkpoint_number,
        body.selected_option,
    )
    return ProblemSolverSessionResponse(**data)


@router.post("/sessions/{session_id}/follow-up")
async def follow_up(
    session_id: str,
    body: ProblemSolverFollowUpRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    tenant_id, user_id = _get_context(request)
    service = ProblemSolverService(db, str(tenant_id), user_id)
    return await service.follow_up(session_id, body.action, body.user_follow_up)


@router.post("/sessions/reset/{notebook_id}")
async def reset_notebook_session(
    notebook_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    tenant_id, user_id = _get_context(request)
    service = ProblemSolverService(db, str(tenant_id), user_id)
    return await service.reset_session(notebook_id)
