import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


if TYPE_CHECKING:
    from app.models.interview_session import InterviewSession
    from app.models.question import QuestionBank
    from app.models.answer_evaluation import AnswerEvaluation
    from app.models.audio_evaluation import AudioEvaluation
    from app.models.nlp_evaluation import NLPEvaluation
    from app.models.video_evaluation import VideoEvaluation


class SessionQuestion(Base):
    __tablename__ = "session_questions"

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

    question_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    question_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    source: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    source_question_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("question_bank.id"),
        nullable=True,
    )

    parent_session_question_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("session_questions.id"),
        nullable=True,
    )

    video_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    transcript_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    transcript_whisper: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    transcript_source: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    transcript_languages: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    transcript_confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    time_taken_seconds: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    asked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    answered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ---------------------------------------------------------
    # Relationships
    # ---------------------------------------------------------

    session: Mapped["InterviewSession"] = relationship(
        back_populates="questions",
    )

    source_question: Mapped["QuestionBank | None"] = relationship(
        foreign_keys=[source_question_id],
    )

    parent_session_question: Mapped["SessionQuestion | None"] = relationship(
        remote_side=[id],
        foreign_keys=[parent_session_question_id],
    )

    evaluation: Mapped["AnswerEvaluation | None"] = relationship(
        back_populates="session_question",
        uselist=False,
        cascade="all, delete-orphan",
    )

    audio_evaluation: Mapped["AudioEvaluation | None"] = relationship(
        back_populates="session_question",
        uselist=False,
        cascade="all, delete-orphan",
    )

    nlp_evaluation: Mapped["NLPEvaluation | None"] = relationship(
        back_populates="session_question",
        uselist=False,
        cascade="all, delete-orphan",
    )

    video_evaluation: Mapped["VideoEvaluation | None"] = relationship(
        back_populates="session_question",
        uselist=False,
        cascade="all, delete-orphan",
    )