import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.interview_session import InterviewSession
    from app.models.session_question import SessionQuestion


class VideoEvaluation(Base):
    __tablename__ = "video_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id"),
        nullable=False,
    )

    session_question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("session_questions.id"),
        nullable=False,
        unique=True,
    )

    overall_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    camera_engagement_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    facial_engagement_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    posture_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    head_movement_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    body_movement_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    visual_presence_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    composure_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    frame_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    analyzed_frame_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    face_detection_ratio: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    camera_engagement_ratio: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    average_face_size_ratio: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    head_movement_variance: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    posture_stability: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    eye_contact: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    facial_expression: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    posture: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    head_movement: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    gestures: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    body_language: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    attentiveness: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    visual_confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    eye_contact_percentage: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    face_visibility_percentage: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    gesture_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    head_movement_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

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

    session: Mapped["InterviewSession"] = relationship()

    session_question: Mapped["SessionQuestion"] = relationship(
        back_populates="video_evaluation",
    )