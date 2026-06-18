"""Problem Solver API schemas."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ProblemSolverSessionCreateRequest(BaseModel):
    notebook_id: str
    problem_text: str = Field(min_length=1)
    input_type: str = Field(default="text")
    source_refs: Optional[List[Dict[str, Any]]] = None


class ProblemSolverExtractRequest(BaseModel):
    normalized_text: str = Field(min_length=1)


class ProblemSolverExtractFromSourceRequest(BaseModel):
    source_id: str = Field(min_length=1)


class ProblemSolverModeRequest(BaseModel):
    solving_mode: str


class ProblemSolverCheckpointRequest(BaseModel):
    checkpoint_number: int = Field(ge=1, le=2)
    selected_option: str


class ProblemSolverFollowUpRequest(BaseModel):
    action: str
    user_follow_up: Optional[str] = None


class ProblemSolverSessionResponse(BaseModel):
    session_id: str
    notebook_id: str
    state: str
    problem_text: Optional[str] = None
    problem_text_normalized: Optional[str] = None
    input_type: str = "text"
    source_refs: List[Dict[str, Any]] = Field(default_factory=list)
    problem_dna: Optional[Dict[str, Any]] = None
    solving_mode: Optional[str] = None
    interaction_count: int = 0
    last_response: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
