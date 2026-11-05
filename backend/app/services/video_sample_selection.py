from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SessionQuestion

MAX_VIDEO_SAMPLES = 5


@dataclass
class VideoSample:
    session_question_id: UUID
    question_order: int
    video_url: str
    duration: float
    session_id: UUID | None = None

    @property
    def duration_seconds(self) -> float:
        return self.duration


def select_video_samples(
    db: Session,
    session_id: UUID,
) -> list[VideoSample]:
    """
    Select up to five recorded answers for video analysis.

    Selection priority:
    1. Longest recorded answer
    2. Most moderate-duration recorded answer

    A video is considered valid when:
    - video_url exists
    - video_url is non-empty
    - the answer has a positive duration

    Duration is read from the stored answer duration first.
    If duration is unavailable, the video is still considered
    only when a valid numeric duration can be obtained from
    the recorded answer metadata.
    """

    questions = db.scalars(
        select(SessionQuestion)
        .where(
            SessionQuestion.session_id == session_id,
            SessionQuestion.answered_at.is_not(None),
        )
        .order_by(SessionQuestion.question_order.asc())
    ).all()

    recorded_answers: list[VideoSample] = []

    for question in questions:
        video_url = getattr(question, "video_url", None)

        if not video_url:
            continue

        duration_value = getattr(
            question,
            "time_taken_seconds",
            None,
        )

        try:
            duration = float(duration_value)
        except (TypeError, ValueError):
            duration = 0.0

        if duration <= 0:
            print(
                "[VIDEO-SAMPLE-SELECTION] "
                f"Skipping question={question.id} "
                f"because time_taken_seconds is invalid: "
                f"{duration_value}"
            )
            continue

        recorded_answers.append(
            VideoSample(
                session_question_id=question.id,
                question_order=question.question_order,
                video_url=video_url,
                duration=duration,
                session_id=getattr(question, "session_id", session_id),
            )
        )

    if not recorded_answers:
        return []

    # Keep the existing representative choices, then add evenly spread
    # answers so short interviews still use every available recording.
    longest = max(
        recorded_answers,
        key=lambda sample: sample.duration,
    )
    remaining = [
        sample
        for sample in recorded_answers
        if sample.session_question_id != longest.session_question_id
    ]
    selected = [longest]
    if remaining:
        sorted_remaining = sorted(remaining, key=lambda sample: sample.duration)
        middle_index = len(sorted_remaining) // 2
        if len(sorted_remaining) % 2 == 0:
            target_duration = (
                sorted_remaining[middle_index - 1].duration
                + sorted_remaining[middle_index].duration
            ) / 2.0
        else:
            target_duration = sorted_remaining[middle_index].duration
        selected.append(
            min(remaining, key=lambda sample: abs(sample.duration - target_duration))
        )

    if len(recorded_answers) > len(selected) and len(selected) < MAX_VIDEO_SAMPLES:
        selected_ids = {sample.session_question_id for sample in selected}
        temporal_remaining = sorted(
            (
                sample for sample in recorded_answers
                if sample.session_question_id not in selected_ids
            ),
            key=lambda sample: sample.question_order,
        )
        slots = min(MAX_VIDEO_SAMPLES - len(selected), len(temporal_remaining))
        for index in range(slots):
            position = round((index + 1) * (len(temporal_remaining) + 1) / (slots + 1)) - 1
            selected.append(temporal_remaining[position])
        selected_ids = {sample.session_question_id for sample in selected}
        if len(selected) < MAX_VIDEO_SAMPLES:
            selected.extend(
                sample for sample in temporal_remaining
                if sample.session_question_id not in selected_ids
            )
            selected = selected[:MAX_VIDEO_SAMPLES]

    samples = sorted(selected, key=lambda sample: sample.question_order)

    print(
        "[VIDEO-SAMPLE-SELECTION] "
        f"Selected {len(samples)} of {len(recorded_answers)} available samples: "
        + ", ".join(
            f"question={sample.question_order} duration={sample.duration:.2f}s"
            for sample in samples
        )
    )

    return samples