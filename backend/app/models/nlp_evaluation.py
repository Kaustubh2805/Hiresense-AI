import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.session_question import SessionQuestion


class NLPEvaluation(Base):
    __tablename__ = "nlp_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    session_question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("session_questions.id"),
        nullable=False,
        unique=True,
    )

    # ---------------------------------------------------------
    # Overall NLP communication score
    # ---------------------------------------------------------

    overall_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    # ---------------------------------------------------------
    # NLP communication scores: 1-10
    # ---------------------------------------------------------

    vocabulary_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    vocabulary_diversity_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    repetition_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    grammar_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    sentence_structure_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    english_consistency_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    code_switching_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    communication_clarity_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # ---------------------------------------------------------
    # Measurable linguistic features
    # ---------------------------------------------------------

    word_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    unique_word_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    vocabulary_diversity: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    average_word_length: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    sentence_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    average_sentence_length: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # ---------------------------------------------------------
    # Hindi / Hinglish detection
    # ---------------------------------------------------------

    hindi_word_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    hindi_word_ratio: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    hindi_words: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    english_word_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    english_word_ratio: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    english_words: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    code_switching_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    code_switching_ratio: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    dominant_language: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    language_switching_examples: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    word_language_identification: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ---------------------------------------------------------
    # Grammar analysis
    # ---------------------------------------------------------

    grammar_error_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    grammar_errors: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    grammar_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    quality_level: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    confidence_level: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    quality_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ---------------------------------------------------------
    # Analysis state
    # ---------------------------------------------------------

    analysis_status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="pending",
        server_default="pending",
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    analyzed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ---------------------------------------------------------
    # Relationship
    # ---------------------------------------------------------

    session_question: Mapped["SessionQuestion"] = relationship(
        back_populates="nlp_evaluation",
    )