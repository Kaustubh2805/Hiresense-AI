import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.session_question import SessionQuestion


class AudioEvaluation(Base):
    __tablename__ = "audio_evaluations"

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

    # -----------------------------------------------------
    # Overall score
    # 1-10 scale
    # -----------------------------------------------------

    overall_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # -----------------------------------------------------
    # Audio communication scores
    # Each score is on a 1-10 scale.
    # -----------------------------------------------------

    speaking_clarity: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    fluency: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    pace: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    volume: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    articulation: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    vocal_confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    filler_word_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    hesitation_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # -----------------------------------------------------
    # Raw measurable audio features
    # -----------------------------------------------------

    words_per_minute: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    filler_word_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    hesitation_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    pause_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    total_pause_seconds: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # -----------------------------------------------------
    # Analysis status
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Relationship
    # -----------------------------------------------------

    session_question: Mapped["SessionQuestion"] = relationship(
        back_populates="audio_evaluation",
    )