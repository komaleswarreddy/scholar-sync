"""IIL entities: interaction logs, feedback, curation, derived artifacts, templates."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from packages.core.database.connection import Base


class InteractionLog(Base):
    """Structured analytics overlay per assistant message (spec §3.2)."""

    __tablename__ = "interaction_logs"
    __table_args__ = (
        UniqueConstraint("message_id", name="uq_interaction_logs_message_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=True, index=True)
    problem_solver_step_id = Column(
        UUID(as_uuid=True),
        ForeignKey("problem_solver_steps.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id", ondelete="CASCADE"), nullable=True, index=True)
    notebook_id = Column(UUID(as_uuid=True), ForeignKey("notebooks.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    user_tier = Column(String, nullable=False, default="student")
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    query_text = Column(Text, nullable=False, default="")
    query_intent = Column(String, nullable=True)
    concept_node_id = Column(UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True, index=True)
    conversation_position = Column(Integer, nullable=False, default=1)
    is_followup = Column(Boolean, nullable=False, default=False)
    chain_depth = Column(Integer, nullable=False, default=1)

    chunks_retrieved = Column(JSONB, nullable=False, default=list)
    retrieval_strategy = Column(String, nullable=True)
    kb_hit = Column(Boolean, nullable=False, default=False)
    derived_hit = Column(Boolean, nullable=False, default=False)
    fallback_triggered = Column(Boolean, nullable=False, default=False)

    response_token_count = Column(Integer, nullable=False, default=0)
    citations_count = Column(Integer, nullable=False, default=0)
    grounding_mode = Column(String, nullable=False, default="strict")
    out_of_kb_indicator = Column(Boolean, nullable=False, default=False)
    latency_ms = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    message = relationship("Message", backref="interaction_log", uselist=False)
    concept_node = relationship("Concept", backref="interaction_logs")
    curation_candidate = relationship("CurationCandidate", back_populates="interaction_log", uselist=False)


class InteractionFeedback(Base):
    """Tiered per-message feedback signals (spec §2.4)."""

    __tablename__ = "interaction_feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=True, index=True)
    problem_solver_step_id = Column(
        UUID(as_uuid=True),
        ForeignKey("problem_solver_steps.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    user_id = Column(String, nullable=False, index=True)
    user_tier = Column(String, nullable=False)
    signal_type = Column(String, nullable=False, index=True)
    concept_node_id = Column(UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True, index=True)
    dimension_tag = Column(String, nullable=True)
    free_text = Column(Text, nullable=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    message = relationship("Message", backref="interaction_feedback")
    concept_node = relationship("Concept", backref="interaction_feedback")


class CurationCandidate(Base):
    """Flagged high-value interaction for human review (spec §4.5)."""

    __tablename__ = "curation_candidates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interaction_log_id = Column(
        UUID(as_uuid=True),
        ForeignKey("interaction_logs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    feedback_id = Column(
        UUID(as_uuid=True),
        ForeignKey("interaction_feedback.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    concept_node_id = Column(UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    source_type = Column(String, nullable=False, default="interaction_chain")
    candidate_score = Column(Integer, nullable=False, default=0)
    scoring_signals = Column(JSONB, nullable=False, default=dict)
    status = Column(String, nullable=False, default="pending", index=True)
    reviewed_by = Column(String, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    interaction_log = relationship("InteractionLog", back_populates="curation_candidate")
    feedback = relationship("InteractionFeedback", backref="curation_candidates")
    artifact = relationship("DerivedKnowledgeArtifact", back_populates="candidate", uselist=False)


class DerivedKnowledgeArtifact(Base):
    """Curated supplementary knowledge for derived retrieval (spec §4.6)."""

    __tablename__ = "derived_knowledge_artifacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(
        UUID(as_uuid=True),
        ForeignKey("curation_candidates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    concept_node_id = Column(UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    dimension_tags = Column(ARRAY(String), nullable=False, default=list)
    content = Column(Text, nullable=False)
    source_interaction_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=False, default=list)
    source_user_tier = Column(String, nullable=True)
    confidence_score = Column(SmallInteger(), nullable=True)
    embedding_id = Column(String, nullable=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    candidate = relationship("CurationCandidate", back_populates="artifact")
    concept_node = relationship("Concept", backref="derived_artifacts")


class ExplorationTemplate(Base):
    """Captured expert questioning patterns per concept (spec §5.2)."""

    __tablename__ = "exploration_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    concept_node_id = Column(UUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    source_chain_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=False, default=list)
    source_user_tier = Column(String, nullable=False)
    dimension_sequence = Column(ARRAY(String), nullable=False, default=list)
    template_prompts = Column(JSONB, nullable=False, default=list)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    concept_node = relationship("Concept", backref="exploration_templates")
