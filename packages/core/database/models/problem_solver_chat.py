"""Problem Solver session ↔ chat bridge for IIL feedback on PS surfaces."""

from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from packages.core.database.connection import Base


class ProblemSolverSessionChat(Base):
    """Links a problem solver session to a dedicated chat for Message-based IIL."""

    __tablename__ = "problem_solver_session_chats"

    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("problem_solver_sessions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    chat_id = Column(
        UUID(as_uuid=True),
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("ProblemSolverSession", backref="session_chat_link", uselist=False)
    chat = relationship("Chat", backref="problem_solver_session_link", uselist=False)
