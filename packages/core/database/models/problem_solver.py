"""Problem Solver session models."""

from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from packages.core.database.connection import Base


class ProblemSolverSession(Base):
    """A single problem-solving attempt within a notebook."""

    __tablename__ = "problem_solver_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    notebook_id = Column(UUID(as_uuid=True), ForeignKey("notebooks.id"), nullable=False, index=True)
    problem_text = Column(Text, nullable=True)
    problem_text_normalized = Column(Text, nullable=True)
    input_type = Column(String, nullable=False, default="text")
    source_refs = Column(JSONB, nullable=False, default=list)
    problem_dna = Column(JSONB, nullable=True)
    solving_mode = Column(String, nullable=True)
    state = Column(String, nullable=False, default="created")
    interaction_count = Column(Integer, nullable=False, default=0)
    expert_solution = Column(JSONB, nullable=True)
    last_response = Column(JSONB, nullable=True)
    trace_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    steps = relationship(
        "ProblemSolverStep",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ProblemSolverStep.created_at",
    )


class ProblemSolverStep(Base):
    """Append-only log of problem solver events."""

    __tablename__ = "problem_solver_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("problem_solver_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_type = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    step_metadata = Column("metadata", JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("ProblemSolverSession", back_populates="steps")
