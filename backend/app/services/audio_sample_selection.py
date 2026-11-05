from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.session_question import SessionQuestion


@dataclass
class AudioSample:
    session_question_id: UUID
    question_order: int
    source: str
    question_text: str
    video_url: str
    transcript_text: str | None
    time_taken_seconds: int | None
    sample_type: str


def select_audio_samples(
    db: Session,
    session_id: UUID,
) -> list[AudioSample]:
    """
    Select representative answered recordings from an interview session.

    We currently select three samples:

    1. baseline:
       The first answered baseline question.

    2. normal:
       A technical answer whose duration is closest to the
       median technical-answer duration.

    3. long:
       The longest answered technical/follow-up answer.

    Only questions with an uploaded video are considered.
    """

    questions = (
        db.query(SessionQuestion)
        .filter(
            SessionQuestion.session_id == session_id,
            SessionQuestion.video_url.isnot(None),
        )
        .order_by(SessionQuestion.question_order.asc())
        .all()
    )

    if not questions:
        return []

    samples: list[AudioSample] = []

    # ---------------------------------------------------------
    # 1. Baseline sample
    # ---------------------------------------------------------

    baseline_question = next(
        (
            question
            for question in questions
            if question.source == "baseline"
        ),
        None,
    )

    if baseline_question:
        samples.append(
            AudioSample(
                session_question_id=baseline_question.id,
                question_order=baseline_question.question_order,
                source=baseline_question.source,
                question_text=baseline_question.question_text,
                video_url=baseline_question.video_url,
                transcript_text=baseline_question.transcript_text,
                time_taken_seconds=baseline_question.time_taken_seconds,
                sample_type="baseline",
            )
        )

    # ---------------------------------------------------------
    # Technical samples
    # ---------------------------------------------------------

    technical_questions = [
        question
        for question in questions
        if question.source in {"bank", "ai_followup"}
        and question.time_taken_seconds is not None
    ]

    if not technical_questions:
        return samples

    # ---------------------------------------------------------
    # 2. Long / difficult sample
    # ---------------------------------------------------------

    longest_question = max(
        technical_questions,
        key=lambda question: question.time_taken_seconds or 0,
    )

    samples.append(
        AudioSample(
            session_question_id=longest_question.id,
            question_order=longest_question.question_order,
            source=longest_question.source,
            question_text=longest_question.question_text,
            video_url=longest_question.video_url,
            transcript_text=longest_question.transcript_text,
            time_taken_seconds=longest_question.time_taken_seconds,
            sample_type="long",
        )
    )

    # ---------------------------------------------------------
    # 3. Normal / representative sample
    # ---------------------------------------------------------

    durations = sorted(
        question.time_taken_seconds
        for question in technical_questions
        if question.time_taken_seconds is not None
    )

    middle_index = len(durations) // 2
    median_duration = durations[middle_index]

    normal_candidates = [
        question
        for question in technical_questions
        if question.id != longest_question.id
    ]

    if normal_candidates:
        normal_question = min(
            normal_candidates,
            key=lambda question: abs(
                (question.time_taken_seconds or 0)
                - median_duration
            ),
        )

        samples.append(
            AudioSample(
                session_question_id=normal_question.id,
                question_order=normal_question.question_order,
                source=normal_question.source,
                question_text=normal_question.question_text,
                video_url=normal_question.video_url,
                transcript_text=normal_question.transcript_text,
                time_taken_seconds=normal_question.time_taken_seconds,
                sample_type="normal",
            )
        )

    return samples